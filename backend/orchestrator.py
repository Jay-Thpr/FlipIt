from __future__ import annotations

import asyncio
from copy import deepcopy

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
            await publish(session_id, "agent.started", pipeline=pipeline, step=step_name, data={"agent": agent_slug, "attempt": attempt})
        else:
            await publish(
                session_id,
                "agent.retrying",
                pipeline=pipeline,
                step=step_name,
                data={"agent": agent_slug, "attempt": attempt, "max_attempts": max_attempts},
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
                "agent.failed",
                pipeline=pipeline,
                step=step_name,
                data={
                    "agent": agent_slug,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "error": str(exc),
                    "category": error_category,
                },
            )
            if attempt >= max_attempts:
                raise

    raise RuntimeError(f"Unreachable retry state for {agent_slug}")


async def run_pipeline(session_id: str, pipeline: str, request: PipelineStartRequest) -> None:
    steps = SELL_STEPS if pipeline == "sell" else BUY_STEPS
    await session_manager.update_status(session_id, status="running")
    await publish(session_id, "pipeline.started", pipeline=pipeline, data={"input": request.input})

    context: dict = {"request_metadata": request.metadata, "pipeline_input": request.input}
    outputs: dict = {}

    try:
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
            await publish(
                session_id,
                "agent.completed",
                pipeline=pipeline,
                step=step_name,
                data={"agent": agent_slug, "output": validated_output},
            )

        result = {"pipeline": pipeline, "outputs": outputs}
        await session_manager.update_status(session_id, status="completed", result=result)
        await publish(session_id, "pipeline.completed", pipeline=pipeline, data=result)
    except Exception as exc:
        partial_result = {"pipeline": pipeline, "outputs": outputs}
        await session_manager.update_status(session_id, status="failed", error=str(exc), result=partial_result)
        await publish(session_id, "pipeline.failed", pipeline=pipeline, data={"error": str(exc), "partial_result": partial_result})
