from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from backend.agent_client import run_agent_task
from backend.config import get_agent_timeout_seconds, get_buy_agent_max_retries
from backend.schemas import (
    AgentTaskRequest,
    PipelineStartRequest,
    SessionEvent,
    validate_agent_output,
    validate_agent_task_request,
)
from backend.session import session_manager

SELL_STEPS = (
    ("vision_agent", "vision_analysis"),
    ("ebay_sold_comps_agent", "ebay_sold_comps"),
    ("pricing_agent", "pricing"),
    ("depop_listing_agent", "depop_listing"),
)

BUY_STEPS = (
    ("depop_search_agent", "depop_search"),
    ("ebay_search_agent", "ebay_search"),
    ("mercari_search_agent", "mercari_search"),
    ("offerup_search_agent", "offerup_search"),
    ("ranking_agent", "ranking"),
    ("negotiation_agent", "negotiation"),
)

RETRYABLE_BUY_AGENT_SLUGS = {
    "depop_search_agent",
    "ebay_search_agent",
    "mercari_search_agent",
    "offerup_search_agent",
}


class PipelinePaused(Exception):
    def __init__(self, *, step_name: str, output: dict[str, Any], message: str | None = None) -> None:
        super().__init__(message or f"Pipeline paused at {step_name}")
        self.step_name = step_name
        self.output = output
        self.message = message or f"Pipeline paused at {step_name}"


def get_pipeline_steps() -> dict[str, list[dict[str, str]]]:
    return {
        "sell": [{"agent": agent_slug, "step": step_name} for agent_slug, step_name in SELL_STEPS],
        "buy": [{"agent": agent_slug, "step": step_name} for agent_slug, step_name in BUY_STEPS],
    }


async def publish(session_id: str, event_type: str, *, pipeline: str, step: str | None = None, data: dict | None = None) -> None:
    await session_manager.append_event(
        SessionEvent(
            session_id=session_id,
            event_type=event_type,
            pipeline=pipeline,
            step=step,
            data=data or {},
        )
    )


def classify_error(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "timeout"
    if isinstance(exc, ValueError):
        return "validation"
    return "agent_execution"


def get_max_attempts(pipeline: str, agent_slug: str) -> int:
    if pipeline == "buy" and agent_slug in RETRYABLE_BUY_AGENT_SLUGS:
        return 1 + max(0, get_buy_agent_max_retries())
    return 1


async def execute_step(
    *,
    session_id: str,
    pipeline: str,
    agent_slug: str,
    step_name: str,
    task_request: AgentTaskRequest,
) -> dict:
    timeout_seconds = get_agent_timeout_seconds()
    max_attempts = get_max_attempts(pipeline, agent_slug)

    for attempt in range(1, max_attempts + 1):
        if attempt == 1:
            await publish(
                session_id,
                "agent_started",
                pipeline=pipeline,
                step=step_name,
                data={"agent_name": agent_slug, "attempt": attempt, "mode": pipeline},
            )
        else:
            await publish(
                session_id,
                "agent_retrying",
                pipeline=pipeline,
                step=step_name,
                data={"agent_name": agent_slug, "attempt": attempt, "max_attempts": max_attempts},
            )

        try:
            response = await asyncio.wait_for(run_agent_task(agent_slug, task_request), timeout=timeout_seconds)
            if response.status == "paused":
                raise PipelinePaused(step_name=step_name, output=response.output, message=response.error)
            if response.status != "completed":
                raise RuntimeError(response.error or f"{agent_slug} failed")
            return validate_agent_output(agent_slug, response.output)
        except Exception as exc:
            if isinstance(exc, PipelinePaused):
                raise
            error_category = classify_error(exc)
            await publish(
                session_id,
                "agent_error",
                pipeline=pipeline,
                step=step_name,
                data={
                    "agent_name": agent_slug,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "error": str(exc),
                    "category": error_category,
                },
            )
            if attempt >= max_attempts:
                raise

    raise RuntimeError(f"Unreachable retry state for {agent_slug}")


def build_context(request: PipelineStartRequest, outputs: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {"request_metadata": request.metadata, "pipeline_input": request.input}
    context.update(outputs)
    return context


def build_task_request(
    *,
    session_id: str,
    pipeline: str,
    request: PipelineStartRequest,
    agent_slug: str,
    step_name: str,
    outputs: dict[str, Any],
) -> AgentTaskRequest:
    return validate_agent_task_request(
        agent_slug,
        AgentTaskRequest(
            session_id=session_id,
            pipeline=pipeline,
            step=step_name,
            input={
                "original_input": deepcopy(request.input),
                "previous_outputs": deepcopy(outputs),
            },
            context=deepcopy(build_context(request, outputs)),
        ),
    )


async def run_pipeline_steps(
    *,
    session_id: str,
    pipeline: str,
    request: PipelineStartRequest,
    steps: tuple[tuple[str, str], ...],
    outputs: dict[str, Any],
) -> None:
    for agent_slug, step_name in steps:
        task_request = build_task_request(
            session_id=session_id,
            pipeline=pipeline,
            request=request,
            agent_slug=agent_slug,
            step_name=step_name,
            outputs=outputs,
        )
        validated_output = await execute_step(
            session_id=session_id,
            pipeline=pipeline,
            agent_slug=agent_slug,
            step_name=step_name,
            task_request=task_request,
        )
        outputs[step_name] = validated_output
        await publish(
            session_id,
            "agent_completed",
            pipeline=pipeline,
            step=step_name,
            data={
                "agent_name": agent_slug,
                "summary": validated_output.get("summary", ""),
                "output": validated_output,
            },
        )


async def run_pipeline(session_id: str, pipeline: str, request: PipelineStartRequest) -> None:
    steps = SELL_STEPS if pipeline == "sell" else BUY_STEPS
    await session_manager.update_status(session_id, status="running", result={})
    await publish(session_id, "pipeline_started", pipeline=pipeline, data={"input": request.input, "mode": pipeline})

    outputs: dict[str, Any] = {}

    try:
        await run_pipeline_steps(
            session_id=session_id,
            pipeline=pipeline,
            request=request,
            steps=steps,
            outputs=outputs,
        )
        result = {"pipeline": pipeline, "outputs": outputs}
        await session_manager.update_status(session_id, status="completed", result=result, error=None)
        await publish(session_id, "pipeline_complete", pipeline=pipeline, data={"mode": pipeline, **result})
    except PipelinePaused as exc:
        pending_result = {
            "pipeline": pipeline,
            "outputs": outputs,
            "pending": {
                "step": exc.step_name,
                **exc.output,
            },
        }
        await session_manager.update_status(session_id, status="awaiting_input", result=pending_result, error=None)
        await publish(
            session_id,
            "vision_low_confidence",
            pipeline=pipeline,
            step=exc.step_name,
            data=exc.output,
        )
    except Exception as exc:
        partial_result = {"pipeline": pipeline, "outputs": outputs}
        await session_manager.update_status(session_id, status="failed", error=str(exc), result=partial_result)
        await publish(
            session_id,
            "pipeline_failed",
            pipeline=pipeline,
            data={"mode": pipeline, "error": str(exc), "partial_result": partial_result},
        )


async def resume_sell_pipeline(session_id: str, corrected_item: dict[str, Any]) -> None:
    from backend.agents.vision_agent import build_corrected_vision_output

    session = await session_manager.get_session(session_id)
    if session is None:
        raise ValueError("Session not found")
    if session.pipeline != "sell":
        raise ValueError("Only sell sessions can be resumed")

    outputs = deepcopy((session.result or {}).get("outputs", {}))
    pending = deepcopy((session.result or {}).get("pending", {}))
    suggestion = pending.get("suggestion")

    vision_output = await build_corrected_vision_output(
        session.request.input,
        corrected_item,
        suggestion=suggestion if isinstance(suggestion, dict) else None,
    )
    outputs["vision_analysis"] = vision_output

    resumed_result = {
        "pipeline": "sell",
        "outputs": outputs,
    }
    await session_manager.update_status(session_id, status="running", result=resumed_result, error=None)
    await publish(
        session_id,
        "agent_completed",
        pipeline="sell",
        step="vision_analysis",
        data={
            "agent_name": "vision_agent",
            "summary": vision_output.get("summary", ""),
            "output": vision_output,
        },
    )

    try:
        await run_pipeline_steps(
            session_id=session_id,
            pipeline="sell",
            request=session.request,
            steps=SELL_STEPS[1:],
            outputs=outputs,
        )
        result = {"pipeline": "sell", "outputs": outputs}
        await session_manager.update_status(session_id, status="completed", result=result, error=None)
        await publish(session_id, "pipeline_complete", pipeline="sell", data={"mode": "sell", **result})
    except Exception as exc:
        partial_result = {"pipeline": "sell", "outputs": outputs}
        await session_manager.update_status(session_id, status="failed", error=str(exc), result=partial_result)
        await publish(
            session_id,
            "pipeline_failed",
            pipeline="sell",
            data={"mode": "sell", "error": str(exc), "partial_result": partial_result},
        )
