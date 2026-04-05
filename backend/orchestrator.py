from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.agents.depop_listing_agent import abort_sell_listing, revise_sell_listing_for_review, submit_sell_listing
from backend.agent_client import run_agent_task
from backend.config import get_agent_timeout_seconds, get_buy_agent_max_retries, is_fetch_enabled
from backend.fetch_runtime import build_buy_no_results_outputs, buy_search_results_are_empty, run_fetch_query
from backend.schemas import (
    AgentTaskRequest,
    PipelineStartRequest,
    SellListingReviewState,
    SessionEvent,
    normalize_vision_correction,
    validate_agent_output,
    validate_agent_task_request,
)
from backend.session import session_manager


class LowConfidencePause(Exception):
    """Pause sell pipeline after vision_low_confidence without marking the session failed."""


class SellListingReviewPause(Exception):
    """Pause sell pipeline while a listing is ready for user confirmation."""


SELL_LISTING_REVIEW_TIMEOUT_MINUTES = 15
SELL_LISTING_MAX_REVISIONS = 2

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


def _build_sell_listing_review_state(
    *,
    state: str,
    latest_decision: str | None = None,
    revision_instructions: str | None = None,
    revision_count: int = 0,
) -> SellListingReviewState:
    paused_at = datetime.now(timezone.utc)
    return SellListingReviewState(
        state=state,
        latest_decision=latest_decision,
        revision_instructions=revision_instructions,
        revision_count=revision_count,
        paused_at=paused_at.isoformat(),
        deadline_at=(paused_at + timedelta(minutes=SELL_LISTING_REVIEW_TIMEOUT_MINUTES)).isoformat(),
    )


def _refresh_sell_listing_review_pause(
    review: SellListingReviewState,
    *,
    state: str,
) -> SellListingReviewState:
    refreshed = _build_sell_listing_review_state(
        state=state,
        latest_decision=review.latest_decision,
        revision_instructions=review.revision_instructions,
        revision_count=review.revision_count,
    )
    return refreshed.model_copy(update={"step": review.step, "platform": review.platform})


def sell_listing_review_is_expired(review: SellListingReviewState) -> bool:
    if review.deadline_at is None:
        return False
    try:
        deadline = datetime.fromisoformat(review.deadline_at)
    except ValueError:
        return True
    return deadline <= datetime.now(timezone.utc)


def sell_listing_review_reached_revision_limit(review: SellListingReviewState) -> bool:
    return review.revision_count >= SELL_LISTING_MAX_REVISIONS


async def fail_sell_listing_review(
    session_id: str,
    *,
    error: str,
    event_type: str,
    event_data: dict[str, Any] | None = None,
) -> bool:
    session = await session_manager.get_session(session_id)
    if session is None or session.pipeline != "sell" or session.sell_listing_review is None:
        return False

    review = session.sell_listing_review
    step_name = review.step
    partial_result = deepcopy(session.result) if session.result else {"pipeline": "sell", "outputs": {}}
    outputs = partial_result.setdefault("outputs", {})
    cleanup_result: dict[str, Any] | None = None
    cleanup_error: str | None = None

    if review.state != "aborted":
        cleanup_result, cleanup_error, _ = await abort_sell_listing()
        if cleanup_result is not None:
            _merge_sell_listing_output(outputs, cleanup_result)
        if error == "sell_listing_review_timeout":
            _update_sell_listing_output(outputs, listing_status="expired", ready_for_confirmation=False)
        elif error == "sell_listing_revision_limit_reached":
            _update_sell_listing_output(outputs, listing_status="revision_limit_reached", ready_for_confirmation=False)
        else:
            _update_sell_listing_output(outputs, listing_status="failed", ready_for_confirmation=False)

    failed_review_state = review.model_copy(update={"state": "failed"})
    await session_manager.update_status(session_id, status="failed", error=error, result=partial_result)
    if cleanup_result is not None:
        await publish(
            session_id,
            "listing_review_cleanup_completed",
            pipeline="sell",
            step=step_name,
            data={"platform": review.platform, "output": outputs.get("depop_listing")},
        )
    elif cleanup_error is not None:
        await publish(
            session_id,
            "listing_review_cleanup_failed",
            pipeline="sell",
            step=step_name,
            data={"platform": review.platform, "error": cleanup_error},
        )
    await publish(
        session_id,
        event_type,
        pipeline="sell",
        step=step_name,
        data={
            **(event_data or {}),
            "platform": review.platform,
            "review_state": failed_review_state.model_dump(),
            "error": error,
        },
    )
    await publish(
        session_id,
        "pipeline_failed",
        pipeline="sell",
        step=step_name,
        data={"mode": "sell", "error": error, "partial_result": partial_result},
    )
    await session_manager.clear_sell_listing_review(session_id)
    return True


async def expire_sell_listing_review_if_needed(session_id: str) -> bool:
    session = await session_manager.get_session(session_id)
    if session is None or session.pipeline != "sell":
        return False
    review = session.sell_listing_review
    if session.status != "paused" or review is None:
        return False
    if not sell_listing_review_is_expired(review):
        return False
    return await fail_sell_listing_review(
        session_id,
        error="sell_listing_review_timeout",
        event_type="listing_review_expired",
    )


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
            if is_fetch_enabled():
                fetch_result = await asyncio.wait_for(
                    run_fetch_query(agent_slug, task_request=task_request),
                    timeout=timeout_seconds,
                )
                return validate_agent_output(agent_slug, fetch_result)

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
    review_state = _build_sell_listing_review_state(state="ready_for_confirmation")
    await session_manager.update_sell_listing_review(session_id, review_state)
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
            "platform": "depop",
            "allowed_decisions": ["confirm_submit", "revise", "abort"],
            "review_state": review_state.model_dump(),
            "title": listing_output.get("title"),
            "description": listing_output.get("description"),
            "suggested_price": listing_output.get("suggested_price"),
            "category_path": listing_output.get("category_path"),
            "listing_status": listing_output.get("listing_status"),
            "ready_for_confirmation": listing_output.get("ready_for_confirmation"),
            "condition": listing_output.get("listing_preview", {}).get("condition")
            if isinstance(listing_output.get("listing_preview"), dict)
            else None,
            "form_screenshot_url": listing_output.get("form_screenshot_url"),
            "output": listing_output,
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
            if buy_search_results_are_empty(outputs):
                outputs.update(build_buy_no_results_outputs(buy_input=request.input, search_outputs=outputs))
                result = {"pipeline": pipeline, "outputs": outputs}
                await session_manager.update_status(session_id, status="completed", result=result)
                await publish(
                    session_id,
                    "buy_no_results",
                    pipeline="buy",
                    data={
                        "mode": "buy",
                        "query": request.input.get("query"),
                        "budget": request.input.get("budget"),
                        "result": result,
                    },
                )
                await publish(session_id, "pipeline_complete", pipeline="buy", data={"mode": pipeline, **result})
                return
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

            if pipeline == "sell" and step_name == "vision_analysis":
                await publish(
                    session_id,
                    "vision_result",
                    pipeline="sell",
                    step=step_name,
                    data={
                        "brand": validated_output.get("brand"),
                        "item_name": validated_output.get("detected_item"),
                        "model": validated_output.get("model"),
                        "condition": validated_output.get("condition"),
                        "confidence": validated_output.get("confidence"),
                        "clean_photo_url": validated_output.get("clean_photo_url"),
                        "search_query": validated_output.get("search_query"),
                    },
                )

            if pipeline == "sell" and step_name == "pricing":
                await publish(
                    session_id,
                    "pricing_result",
                    pipeline="sell",
                    step=step_name,
                    data={
                        "recommended_price": validated_output.get("recommended_list_price"),
                        "profit_margin": validated_output.get("expected_profit"),
                        "median_price": validated_output.get("median_sold_price"),
                        "trend": validated_output.get("trend"),
                        "velocity": validated_output.get("velocity"),
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
                review_state = _build_sell_listing_review_state(state="ready_for_confirmation")
                await session_manager.update_sell_listing_review(session_id, review_state)
                await session_manager.update_status(session_id, status="paused", result=partial_result)
                await publish(
                    session_id,
                    "listing_review_required",
                    pipeline="sell",
                    step="depop_listing",
                    data={
                        "platform": "depop",
                        "allowed_decisions": ["confirm_submit", "revise", "abort"],
                        "review_state": review_state.model_dump(),
                        "title": validated_output.get("title"),
                        "description": validated_output.get("description"),
                        "suggested_price": validated_output.get("suggested_price"),
                        "category_path": validated_output.get("category_path"),
                        "listing_status": validated_output.get("listing_status") or "ready_for_confirmation",
                        "ready_for_confirmation": True,
                        "condition": validated_output.get("listing_preview", {}).get("condition")
                        if isinstance(validated_output.get("listing_preview"), dict)
                        else None,
                        "form_screenshot_url": validated_output.get("form_screenshot_url"),
                        "output": validated_output,
                    },
                )
                raise SellListingReviewPause

        result = {"pipeline": pipeline, "outputs": outputs}
        await session_manager.update_status(session_id, status="completed", result=result)
        if pipeline == "buy":
            from backend.buy_writeback import write_back_buy_result
            await write_back_buy_result(
                session_id=session_id,
                user_id=request.user_id,
                outputs=outputs,
            )
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

    if sell_listing_review_is_expired(review):
        await fail_sell_listing_review(
            session_id,
            error="sell_listing_review_timeout",
            event_type="listing_review_expired",
        )
        return

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
        review_state = SellListingReviewState.model_validate(review)
        await session_manager.update_sell_listing_review(session_id, review_state)
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
            "listing_submission_approved",
            pipeline="sell",
            step=step_name,
            data={"decision": decision, "review_state": review_state.model_dump()},
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
            await session_manager.update_sell_listing_review(
                session_id,
                SellListingReviewState.model_validate({**review_state.model_dump(), "state": "failed"}),
            )
            await publish(
                session_id,
                "listing_submission_failed",
                pipeline="sell",
                step=step_name,
                data={"platform": review.platform, "error": browser_use_error},
            )
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
        await session_manager.clear_sell_listing_review(session_id)
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
        if sell_listing_review_reached_revision_limit(review):
            review.latest_decision = "revise"
            review.revision_instructions = revision_instructions
            await fail_sell_listing_review(
                session_id,
                error="sell_listing_revision_limit_reached",
                event_type="listing_revision_limit_reached",
                event_data={
                    "decision": decision,
                    "revision_count": review.revision_count,
                    "max_revisions": SELL_LISTING_MAX_REVISIONS,
                },
            )
            return
        review.state = "applying_revision"
        review.latest_decision = "revise"
        review.revision_instructions = revision_instructions
        review.revision_count += 1
        _update_sell_listing_output(outputs, listing_status="revision_requested", ready_for_confirmation=False)
        review_state = SellListingReviewState.model_validate(review)
        await session_manager.update_sell_listing_review(session_id, review_state)
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
                "revision_count": review_state.revision_count,
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
            await session_manager.update_sell_listing_review(
                session_id,
                SellListingReviewState.model_validate({**review_state.model_dump(), "state": "failed"}),
            )
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
        review_state = _refresh_sell_listing_review_pause(review, state="ready_for_confirmation")
        review = review_state
        await session_manager.update_sell_listing_review(session_id, review_state)
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
                "allowed_decisions": ["confirm_submit", "revise", "abort"],
                "review_state": review_state.model_dump(),
                "title": outputs.get("depop_listing", {}).get("title"),
                "description": outputs.get("depop_listing", {}).get("description"),
                "suggested_price": outputs.get("depop_listing", {}).get("suggested_price"),
                "category_path": outputs.get("depop_listing", {}).get("category_path"),
                "listing_status": outputs.get("depop_listing", {}).get("listing_status"),
                "ready_for_confirmation": outputs.get("depop_listing", {}).get("ready_for_confirmation"),
                "condition": outputs.get("depop_listing", {}).get("listing_preview", {}).get("condition")
                if isinstance(outputs.get("depop_listing", {}).get("listing_preview"), dict)
                else None,
                "form_screenshot_url": outputs.get("depop_listing", {}).get("form_screenshot_url"),
                "output": outputs.get("depop_listing"),
            },
        )
        return

    if decision == "abort":
        review.state = "aborted"
        review.latest_decision = "abort"
        review.revision_instructions = None
        _update_sell_listing_output(outputs, listing_status="aborted", ready_for_confirmation=False)
        review_state = SellListingReviewState.model_validate(review)
        await session_manager.update_sell_listing_review(session_id, review_state)
        session.error = None
        await session_manager.update_status(session_id, status="completed", result=partial_result)
        await publish(
            session_id,
            "listing_submission_aborted",
            pipeline="sell",
            step=step_name,
            data={"decision": decision, "review_state": review_state.model_dump()},
        )
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
        await session_manager.clear_sell_listing_review(session_id)
        await publish(
            session_id,
            "listing_aborted",
            pipeline="sell",
            step=step_name,
            data={"platform": review.platform},
        )
        await publish(session_id, "pipeline_complete", pipeline="sell", data={"mode": "sell", **partial_result})
