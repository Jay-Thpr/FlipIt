from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from backend.agents.depop_listing_agent import abort_sell_listing, revise_sell_listing_for_review, submit_sell_listing
from backend.agent_client import run_agent_task
from backend.config import get_agent_timeout_seconds, get_buy_agent_max_retries
from backend.schemas import (
    AgentTaskRequest,
    PipelineStartRequest,
    SellListingReviewState,
    SessionEvent,
    normalize_vision_correction,
    utc_now_iso,
    validate_agent_output,
    validate_agent_task_request,
)
from backend.session import session_manager


class LowConfidencePause(Exception):
    """Pause sell pipeline after vision_low_confidence without marking the session failed."""


class SellListingReviewPause(Exception):
    """Pause sell pipeline while a listing is ready for user confirmation."""

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


def _get_sell_partial_result(outputs: dict[str, Any]) -> dict[str, Any]:
    return {"pipeline": "sell", "outputs": outputs}


def _update_sell_listing_output(
    outputs: dict[str, Any],
    *,
    listing_status: str,
    ready_for_confirmation: bool,
) -> None:
    listing_output = outputs.get("depop_listing")
    if not isinstance(listing_output, dict):
        return
    listing_output["listing_status"] = listing_status
    listing_output["ready_for_confirmation"] = ready_for_confirmation


def _merge_sell_listing_output(outputs: dict[str, Any], browser_use_result: dict[str, Any]) -> None:
    listing_output = outputs.get("depop_listing")
    if not isinstance(listing_output, dict):
        outputs["depop_listing"] = deepcopy(browser_use_result)
        return
    listing_output.update(browser_use_result)


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


async def pause_sell_listing_for_review(session_id: str, listing_output: dict[str, Any]) -> None:
    """Moves a sell session into a paused review state once a listing is ready to submit."""
    session = await session_manager.get_session(session_id)
    if session is None or session.pipeline != "sell":
        return

    outputs = deepcopy(session.result.get("outputs", {})) if session.result else {}
    outputs["depop_listing"] = listing_output
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        paused_at=utc_now_iso(),
    )
    await session_manager.update_status(
        session_id,
        status="paused",
        result={"pipeline": "sell", "outputs": outputs},
        error=None,
    )
    await publish(
        session_id,
        "listing_review_required",
        pipeline="sell",
        step="depop_listing",
        data={
            "message": "Review the prepared listing before final submission.",
            "listing_output": listing_output,
        },
    )


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

    raw_results = await asyncio.gather(
        *[run_one(slug, step) for slug, step in BUY_SEARCH_STEPS],
        return_exceptions=True,
    )
    completion_order = ("depop_search", "ebay_search", "mercari_search", "offerup_search")
    slug_by_step = {step: slug for slug, step in BUY_SEARCH_STEPS}
    display_by_step = {
        "depop_search": "Depop Search Agent",
        "ebay_search": "eBay Search Agent",
        "mercari_search": "Mercari Search Agent",
        "offerup_search": "OfferUp Search Agent",
    }
    by_step: dict[str, dict] = {}
    for result in raw_results:
        if isinstance(result, Exception):
            # execute_step already published agent_error; inject empty fallback output
            continue
        step_name, validated = result
        by_step[step_name] = validated

    for step_name in completion_order:
        agent_slug = slug_by_step[step_name]
        if step_name not in by_step:
            # Agent failed — substitute empty fallback so ranking can still run
            by_step[step_name] = {
                "agent": agent_slug,
                "display_name": display_by_step[step_name],
                "summary": f"{display_by_step[step_name]} failed — no results",
                "results": [],
                "execution_mode": "fallback",
                "browser_use_error": None,
                "browser_use": None,
            }
        validated_output = by_step[step_name]
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
                    await session_manager.update_status(session_id, status="paused", result=partial_result)
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

            if pipeline == "sell" and step_name == "depop_listing" and validated_output.get("ready_for_confirmation"):
                review_state = SellListingReviewState(
                    state="ready_for_confirmation",
                    paused_at=utc_now_iso(),
                )
                session = await session_manager.get_session(session_id)
                if session is not None:
                    session.sell_listing_review = review_state
                await session_manager.update_status(session_id, status="paused", result=partial_result)
                await publish(
                    session_id,
                    "listing_review_required",
                    pipeline="sell",
                    step="depop_listing",
                    data={
                        "platform": "depop",
                        "listing_status": validated_output.get("listing_status") or "ready_for_confirmation",
                        "ready_for_confirmation": True,
                        "output": validated_output,
                    },
                )
                raise SellListingReviewPause

        result = {"pipeline": pipeline, "outputs": outputs}
        await session_manager.update_status(session_id, status="completed", result=result)
        await publish(session_id, "pipeline_complete", pipeline=pipeline, data={"mode": pipeline, **result})
    except LowConfidencePause:
        # Session stays paused; client calls POST /sell/correct to resume.
        return
    except SellListingReviewPause:
        # Session stays paused; client calls POST /sell/listing-decision to continue.
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


async def handle_sell_listing_decision(
    session_id: str,
    decision: str,
    *,
    revision_instructions: str | None = None,
) -> None:
    """Transitions a paused sell session after a user confirms, revises, or aborts the listing."""
    session = await session_manager.get_session(session_id)
    if session is None or session.pipeline != "sell":
        return

    review = session.sell_listing_review
    if review is None or session.status != "paused":
        return

    step_name = review.step
    partial_result = deepcopy(session.result) if session.result else {"pipeline": "sell", "outputs": {}}
    outputs = partial_result.setdefault("outputs", {})

    await publish(
        session_id,
        "listing_decision_received",
        pipeline="sell",
        step=step_name,
        data={"decision": decision},
    )

    if decision == "confirm_submit":
        review.state = "submitting"
        review.latest_decision = "confirm_submit"
        review.revision_instructions = None
        _update_sell_listing_output(outputs, listing_status="submit_requested", ready_for_confirmation=False)
        session.sell_listing_review = SellListingReviewState.model_validate(review)
        session.error = None
        await session_manager.update_status(session_id, status="running", result=partial_result)
        await publish(
            session_id,
            "pipeline_resumed",
            pipeline="sell",
            step=step_name,
            data={"reason": "listing_confirmed"},
        )
        await publish(
            session_id,
            "listing_submit_requested",
            pipeline="sell",
            step=step_name,
            data={"decision": decision},
        )
        browser_use_result, browser_use_error, _ = await submit_sell_listing()
        if browser_use_result is None:
            await session_manager.update_status(session_id, status="failed", error=browser_use_error, result=partial_result)
            await publish(
                session_id,
                "pipeline_failed",
                pipeline="sell",
                step=step_name,
                data={"mode": "sell", "error": browser_use_error, "partial_result": partial_result},
            )
            return

        _merge_sell_listing_output(outputs, browser_use_result)
        review.state = "submitted"
        session.sell_listing_review = SellListingReviewState.model_validate(review)
        await session_manager.update_status(session_id, status="completed", result=partial_result, error=None)
        await publish(
            session_id,
            "listing_submitted",
            pipeline="sell",
            step=step_name,
            data={"platform": review.platform, "output": outputs.get("depop_listing")},
        )
        await publish(session_id, "pipeline_complete", pipeline="sell", data={"mode": "sell", **partial_result})
        return

    if decision == "revise":
        review.state = "applying_revision"
        review.latest_decision = "revise"
        review.revision_instructions = revision_instructions
        review.revision_count += 1
        _update_sell_listing_output(outputs, listing_status="revision_requested", ready_for_confirmation=False)
        session.sell_listing_review = SellListingReviewState.model_validate(review)
        session.error = None
        await session_manager.update_status(session_id, status="running", result=partial_result)
        await publish(
            session_id,
            "pipeline_resumed",
            pipeline="sell",
            step=step_name,
            data={"reason": "listing_revision_requested"},
        )
        await publish(
            session_id,
            "listing_revision_requested",
            pipeline="sell",
            step=step_name,
            data={
                "decision": decision,
                "revision_instructions": revision_instructions,
                "revision_count": review.revision_count,
            },
        )
        listing_output = outputs.get("depop_listing")
        if not isinstance(listing_output, dict):
            await session_manager.update_status(
                session_id,
                status="failed",
                error="missing_depop_listing_output",
                result=partial_result,
            )
            await publish(
                session_id,
                "pipeline_failed",
                pipeline="sell",
                step=step_name,
                data={"mode": "sell", "error": "missing_depop_listing_output", "partial_result": partial_result},
            )
            return
        browser_use_result, browser_use_error, _ = await revise_sell_listing_for_review(
            listing_output=listing_output,
            revision_instructions=revision_instructions or "",
        )
        if browser_use_result is None:
            await session_manager.update_status(session_id, status="failed", error=browser_use_error, result=partial_result)
            await publish(
                session_id,
                "pipeline_failed",
                pipeline="sell",
                step=step_name,
                data={"mode": "sell", "error": browser_use_error, "partial_result": partial_result},
            )
            return

        _merge_sell_listing_output(outputs, browser_use_result)
        review.state = "ready_for_confirmation"
        session.sell_listing_review = SellListingReviewState.model_validate(review)
        await session_manager.update_status(session_id, status="paused", result=partial_result, error=None)
        await publish(
            session_id,
            "listing_revision_applied",
            pipeline="sell",
            step=step_name,
            data={
                "platform": review.platform,
                "revision_count": review.revision_count,
                "output": outputs.get("depop_listing"),
            },
        )
        await publish(
            session_id,
            "listing_review_required",
            pipeline="sell",
            step=step_name,
            data={
                "platform": review.platform,
                "listing_status": outputs.get("depop_listing", {}).get("listing_status"),
                "ready_for_confirmation": outputs.get("depop_listing", {}).get("ready_for_confirmation"),
                "output": outputs.get("depop_listing"),
            },
        )
        return

    if decision == "abort":
        review.state = "aborted"
        review.latest_decision = "abort"
        review.revision_instructions = None
        _update_sell_listing_output(outputs, listing_status="aborted", ready_for_confirmation=False)
        session.sell_listing_review = SellListingReviewState.model_validate(review)
        session.error = None
        await session_manager.update_status(session_id, status="completed", result=partial_result)
        await publish(
            session_id,
            "listing_abort_requested",
            pipeline="sell",
            step=step_name,
            data={"decision": decision},
        )
        browser_use_result, _, _ = await abort_sell_listing()
        if browser_use_result is not None:
            _merge_sell_listing_output(outputs, browser_use_result)
            await session_manager.update_status(session_id, status="completed", result=partial_result, error=None)
        await publish(
            session_id,
            "listing_aborted",
            pipeline="sell",
            step=step_name,
            data={"platform": review.platform},
        )
        await publish(session_id, "pipeline_complete", pipeline="sell", data={"mode": "sell", **partial_result})
