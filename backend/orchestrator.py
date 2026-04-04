from __future__ import annotations

from copy import deepcopy

from backend.agent_client import run_agent_task
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
            await publish(session_id, "agent.started", pipeline=pipeline, step=step_name, data={"agent": agent_slug})
            response = await run_agent_task(agent_slug, task_request)
            if response.status != "completed":
                raise RuntimeError(response.error or f"{agent_slug} failed")
            validated_output = validate_agent_output(agent_slug, response.output)
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
        await session_manager.update_status(session_id, status="failed", error=str(exc))
        await publish(session_id, "pipeline.failed", pipeline=pipeline, data={"error": str(exc)})
