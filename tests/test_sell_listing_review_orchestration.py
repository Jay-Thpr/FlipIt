from __future__ import annotations

from typing import Any

import pytest

from backend import orchestrator
from backend.schemas import AgentTaskResponse, PipelineStartRequest, SellListingReviewState
from backend.session import session_manager


def _vision_output() -> dict[str, Any]:
    return {
        "agent": "vision_agent",
        "display_name": "Vision Agent",
        "summary": "Detected a Nike hoodie in good condition",
        "detected_item": "Hoodie",
        "brand": "Nike",
        "category": "Men/Tops/Hoodies",
        "condition": "good",
        "confidence": 0.95,
    }


def _comps_output() -> dict[str, Any]:
    return {
        "agent": "ebay_sold_comps_agent",
        "display_name": "eBay Sold Comps Agent",
        "summary": "11 sold comps found",
        "median_sold_price": 58.0,
        "low_sold_price": 42.0,
        "high_sold_price": 79.0,
        "sample_size": 11,
    }


def _pricing_output() -> dict[str, Any]:
    return {
        "agent": "pricing_agent",
        "display_name": "Pricing Agent",
        "summary": "Recommended a competitive sell price",
        "recommended_list_price": 72.0,
        "expected_profit": 61.0,
        "pricing_confidence": 0.84,
    }


def _listing_output(*, ready_for_confirmation: bool, listing_status: str) -> dict[str, Any]:
    return {
        "agent": "depop_listing_agent",
        "display_name": "Depop Listing Agent",
        "summary": "Prepared a Depop listing draft",
        "title": "Nike hoodie - Good Condition",
        "description": "Good prefilled draft",
        "suggested_price": 72.0,
        "category_path": "Men/Tops/Hoodies",
        "listing_status": listing_status,
        "ready_for_confirmation": ready_for_confirmation,
        "draft_status": "browser_use",
    }


@pytest.mark.asyncio
async def test_sell_pipeline_pauses_when_listing_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()

    outputs_by_agent = {
        "vision_agent": _vision_output(),
        "ebay_sold_comps_agent": _comps_output(),
        "pricing_agent": _pricing_output(),
        "depop_listing_agent": _listing_output(
            ready_for_confirmation=True,
            listing_status="ready_for_confirmation",
        ),
    }

    async def fake_run_agent_task(agent_slug: str, request: Any) -> AgentTaskResponse:
        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="completed",
            output=outputs_by_agent[agent_slug],
        )

    monkeypatch.setattr(orchestrator, "run_agent_task", fake_run_agent_task)

    request = PipelineStartRequest(
        user_id="sell-user",
        input={"image_urls": ["https://example.com/item.jpg"], "notes": "Nike hoodie"},
        metadata={"source": "listing-review-pause-test"},
    )
    session_id = "sell-review-pause-session"
    await session_manager.create_session(session_id=session_id, pipeline="sell", request=request)

    await orchestrator.run_pipeline(session_id, "sell", request)

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.status == "paused"
    assert session.sell_listing_review is not None
    assert session.sell_listing_review.state == "ready_for_confirmation"
    depop_listing = session.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "ready_for_confirmation"
    assert depop_listing["ready_for_confirmation"] is True
    assert [event.event_type for event in session.events][-1] == "listing_review_required"
    assert "pipeline_complete" not in [event.event_type for event in session.events]


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_confirm_marks_session_running(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-confirm-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    await orchestrator.handle_sell_listing_decision(session.session_id, "confirm_submit")

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "running"
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "submitting"
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "submit_requested"
    assert depop_listing["ready_for_confirmation"] is False
    assert [event.event_type for event in updated.events][-3:] == [
        "listing_decision_received",
        "pipeline_resumed",
        "listing_submit_requested",
    ]


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_revise_marks_session_running(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-revise-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation", revision_count=1)

    await orchestrator.handle_sell_listing_decision(
        session.session_id,
        "revise",
        revision_instructions="Change the title and lower the price",
    )

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "running"
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "applying_revision"
    assert updated.sell_listing_review.revision_count == 2
    assert updated.sell_listing_review.revision_instructions == "Change the title and lower the price"
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "revision_requested"
    assert depop_listing["ready_for_confirmation"] is False
    assert [event.event_type for event in updated.events][-3:] == [
        "listing_decision_received",
        "pipeline_resumed",
        "listing_revision_requested",
    ]


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_abort_completes_session() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-abort-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    await orchestrator.handle_sell_listing_decision(session.session_id, "abort")

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "completed"
    assert updated.error is None
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "aborted"
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "aborted"
    assert depop_listing["ready_for_confirmation"] is False
    assert [event.event_type for event in updated.events][-4:] == [
        "listing_decision_received",
        "listing_abort_requested",
        "listing_aborted",
        "pipeline_complete",
    ]
