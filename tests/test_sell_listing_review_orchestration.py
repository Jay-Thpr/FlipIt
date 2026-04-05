from __future__ import annotations

import pytest

from backend.orchestrator import handle_sell_listing_decision, pause_sell_listing_for_review
from backend.schemas import PipelineStartRequest, SellListingReviewState
from backend.session import session_manager


def build_listing_output() -> dict[str, object]:
    return {
        "agent": "depop_listing_agent",
        "display_name": "Depop Listing Agent",
        "summary": "Prepared listing",
        "title": "Nike Hoodie - Good Condition",
        "description": "Prepared listing body",
        "suggested_price": 42.0,
        "category_path": "Men/Tops/Hoodies",
        "listing_status": "ready_for_confirmation",
        "ready_for_confirmation": True,
        "draft_status": "browser_use",
        "listing_preview": {
            "title": "Nike Hoodie - Good Condition",
            "description": "Prepared listing body",
            "price": 42.0,
        },
        "execution_mode": "browser_use",
        "browser_use_error": None,
        "browser_use": None,
    }


@pytest.mark.asyncio
async def test_pause_sell_listing_for_review_sets_paused_state_and_event() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-pause",
        pipeline="sell",
        request=PipelineStartRequest(input={"notes": "test"}),
    )
    session.status = "running"
    session.result = {"pipeline": "sell", "outputs": {"pricing": {"recommended_list_price": 42.0}}}

    await pause_sell_listing_for_review(session.session_id, build_listing_output())

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "paused"
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "ready_for_confirmation"
    assert updated.result["outputs"]["depop_listing"]["ready_for_confirmation"] is True
    assert updated.events[-1].event_type == "listing_review_required"
    assert updated.events[-1].step == "depop_listing"


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_confirm_submit_resumes_session() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-confirm",
        pipeline="sell",
        request=PipelineStartRequest(input={"notes": "test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": build_listing_output()}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    await handle_sell_listing_decision(session.session_id, "confirm_submit")

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "running"
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "submitting"
    assert [event.event_type for event in updated.events[-2:]] == [
        "pipeline_resumed",
        "listing_submit_requested",
    ]


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_revise_records_instructions_and_resumes() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-revise",
        pipeline="sell",
        request=PipelineStartRequest(input={"notes": "test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": build_listing_output()}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    await handle_sell_listing_decision(
        session.session_id,
        "revise",
        revision_instructions="Change the title to mention size medium.",
    )

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "running"
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "applying_revision"
    assert updated.sell_listing_review.revision_count == 1
    assert updated.sell_listing_review.revision_instructions == "Change the title to mention size medium."
    assert [event.event_type for event in updated.events[-2:]] == [
        "pipeline_resumed",
        "listing_revision_requested",
    ]
    assert updated.events[-1].data["revision_count"] == 1


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_abort_fails_session() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-abort",
        pipeline="sell",
        request=PipelineStartRequest(input={"notes": "test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": build_listing_output()}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    await handle_sell_listing_decision(session.session_id, "abort")

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "failed"
    assert updated.error == "Sell listing aborted by user"
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "aborted"
    assert [event.event_type for event in updated.events[-2:]] == [
        "listing_abort_requested",
        "pipeline_failed",
    ]
