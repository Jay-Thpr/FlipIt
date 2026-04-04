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
    normalize_vision_correction,
    validate_agent_output,
    validate_agent_task_request,
)
from backend.session import session_manager


class LowConfidencePause(Exception):
    """Pause sell pipeline after vision_low_confidence without marking the session failed."""

SELL_STEPS = (
    ("vision_agent", "vision_analysis"),
    ("ebay_sold_comps_agent", "ebay_sold_comps"),
    ("pricing_agent", "pricing"),
    ("depop_listing_agent", "depop_listing"),
)

BUY_SEARCH_STEPS = (
    ("depop_search_agent", "depop_search"),
    ("ebay_search_agent", "ebay_search"),
    ("mercari_search_agent", "mercari_search"),
    ("offerup_search_agent", "offerup_search"),
)

BUY_STEPS = BUY_SEARCH_STEPS + (
    ("ranking_agent", "ranking"),
    ("negotiation_agent", "negotiation"),
)

RETRYABLE_BUY_AGENT_SLUGS = {
    "depop_search_agent",
    "ebay_search_agent",
    "mercari_search_agent",
    "offerup_search_agent",
}


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
            if response.status != "completed":
                raise RuntimeError(response.error or f"{agent_slug} failed")
            return validate_agent_output(agent_slug, response.output)
        except Exception as exc:
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


async def _run_buy_search_parallel(
    session_id: str,
    request: PipelineStartRequest,
    context: dict,
    outputs: dict,
) -> None:
    async def run_one(agent_slug: str, step_name: str) -> tuple[str, dict]:
        task_request = validate_agent_task_request(
            agent_slug,
            AgentTaskRequest(
                session_id=session_id,
                pipeline="buy",
                step=step_name,
                input={
                    "original_input": deepcopy(request.input),
                    "previous_outputs": {},
                },
                context=deepcopy(context),
            ),
        )
        validated = await execute_step(
            session_id=session_id,
            pipeline="buy",
            agent_slug=agent_slug,
            step_name=step_name,
            task_request=task_request,
        )
        return step_name, validated

    pairs = await asyncio.gather(*[run_one(slug, step) for slug, step in BUY_SEARCH_STEPS])
    completion_order = ("depop_search", "ebay_search", "mercari_search", "offerup_search")
    by_step = dict(pairs)
    for step_name in completion_order:
        validated_output = by_step[step_name]
        agent_slug = next(slug for slug, name in BUY_SEARCH_STEPS if name == step_name)
        outputs[step_name] = validated_output
        context[step_name] = validated_output
        partial_result = {"pipeline": "buy", "outputs": outputs}
        await session_manager.update_status(session_id, status="running", result=partial_result)
        await publish(
            session_id,
            "agent_completed",
            pipeline="buy",
            step=step_name,
            data={
                "agent_name": agent_slug,
                "summary": validated_output.get("summary", ""),
                "output": validated_output,
            },
        )


async def run_pipeline(session_id: str, pipeline: str, request: PipelineStartRequest) -> None:
    await session_manager.update_status(session_id, status="running")
    await publish(session_id, "pipeline_started", pipeline=pipeline, data={"input": request.input, "mode": pipeline})

    context: dict = {"request_metadata": request.metadata, "pipeline_input": request.input}
    outputs: dict = {}

    try:
        if pipeline == "buy":
            await _run_buy_search_parallel(session_id, request, context, outputs)
            steps = BUY_STEPS[len(BUY_SEARCH_STEPS) :]
        else:
            steps = SELL_STEPS

        for agent_slug, step_name in steps:
            task_request = validate_agent_task_request(
                agent_slug,
                AgentTaskRequest(
                    session_id=session_id,
                    pipeline=pipeline,
                    step=step_name,
                    input={
                        "original_input": deepcopy(request.input),
                        "previous_outputs": deepcopy(outputs),
                    },
                    context=deepcopy(context),
                ),
            )
            validated_output = await execute_step(
                session_id=session_id,
                pipeline=pipeline,
                agent_slug=agent_slug,
                step_name=step_name,
                task_request=task_request,
            )
            outputs[step_name] = validated_output
            context[step_name] = validated_output
            
            # Save partial result in case of pause to allow resume
            partial_result = {"pipeline": pipeline, "outputs": outputs}
            await session_manager.update_status(session_id, status="running", result=partial_result)

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

            # Check for vision_agent low confidence pause condition
            if pipeline == "sell" and step_name == "vision_analysis":
                confidence_score = validated_output.get("confidence", 1.0)
                if isinstance(confidence_score, (int, float)) and float(confidence_score) < 0.70:
                    await publish(
                        session_id,
                        "vision_low_confidence",
                        pipeline="sell",
                        step="vision_analysis",
                        data={
                            "suggestion": validated_output,
                            "message": (
                                f"Not sure — is this a {validated_output.get('brand', 'Unknown')} "
                                f"{validated_output.get('detected_item', 'item')}?"
                            ),
                        },
                    )
                    raise LowConfidencePause

        result = {"pipeline": pipeline, "outputs": outputs}
        await session_manager.update_status(session_id, status="completed", result=result)
        await publish(session_id, "pipeline_complete", pipeline=pipeline, data={"mode": pipeline, **result})
    except LowConfidencePause:
        # Session stays running; client calls POST /sell/correct to resume.
        return
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
    """Resumes the SELL pipeline after a user corrects a low-confidence vision identification."""
    session = await session_manager.get_session(session_id)
    if not session or not session.pipeline == "sell":
        return

    outputs = session.result.get("outputs", {}) if session.result else {}
    outputs["vision_analysis"] = normalize_vision_correction(corrected_item)
    await session_manager.update_status(session_id, status="running", result={"pipeline": "sell", "outputs": outputs})

    base_context: dict[str, Any] = {
        "request_metadata": session.request.metadata,
        "pipeline_input": session.request.input,
    }

    # Re-run starting from step 2 (skip vision_agent)
    remaining_steps = SELL_STEPS[1:]

    try:
        await publish(session_id, "pipeline_resumed", pipeline="sell")

        for agent_slug, step_name in remaining_steps:
            if step_name in outputs:
                continue

            task_request = validate_agent_task_request(
                agent_slug,
                AgentTaskRequest(
                    session_id=session_id,
                    pipeline="sell",
                    step=step_name,
                    input={
                        "original_input": deepcopy(session.request.input),
                        "previous_outputs": deepcopy(outputs),
                    },
                    context=deepcopy({**base_context, **outputs}),
                ),
            )
            validated_output = await execute_step(
                session_id=session_id,
                pipeline="sell",
                agent_slug=agent_slug,
                step_name=step_name,
                task_request=task_request,
            )
            outputs[step_name] = validated_output

            # Save progress incrementally
            partial_result = {"pipeline": "sell", "outputs": outputs}
            await session_manager.update_status(session_id, status="running", result=partial_result)

            await publish(
                session_id,
                "agent_completed",
                pipeline="sell",
                step=step_name,
                data={
                    "agent_name": agent_slug,
                    "summary": validated_output.get("summary", ""),
                    "output": validated_output,
                },
            )

        result = {"pipeline": "sell", "outputs": outputs}
        await session_manager.update_status(session_id, status="completed", result=result)
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
