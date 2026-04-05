from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
async def test_handle_sell_listing_decision_confirm_submits_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-confirm-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    async def fake_submit_sell_listing() -> tuple[dict[str, Any], None, bool]:
        return (
            {
                "listing_status": "submitted",
                "ready_for_confirmation": False,
                "draft_status": "submitted",
                "form_screenshot_url": "artifact://submitted",
            },
            None,
            True,
        )

    monkeypatch.setattr(orchestrator, "submit_sell_listing", fake_submit_sell_listing)

    await orchestrator.handle_sell_listing_decision(session.session_id, "confirm_submit")

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "completed"
    assert updated.sell_listing_review is None
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "submitted"
    assert depop_listing["ready_for_confirmation"] is False
    assert [event.event_type for event in updated.events][-6:] == [
        "listing_decision_received",
        "pipeline_resumed",
        "listing_submission_approved",
        "listing_submit_requested",
        "listing_submitted",
        "pipeline_complete",
    ]


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_revise_reopens_review(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-revise-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation", revision_count=1)

    async def fake_revise_sell_listing_for_review(
        *,
        listing_output: dict[str, Any],
        revision_instructions: str,
    ) -> tuple[dict[str, Any], None, bool]:
        assert listing_output["title"] == "Nike hoodie - Good Condition"
        assert revision_instructions == "Change the title and lower the price"
        return (
            {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://revised-preview",
            },
            None,
            True,
        )

    monkeypatch.setattr(orchestrator, "revise_sell_listing_for_review", fake_revise_sell_listing_for_review)

    await orchestrator.handle_sell_listing_decision(
        session.session_id,
        "revise",
        revision_instructions="Change the title and lower the price",
    )

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "paused"
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.state == "ready_for_confirmation"
    assert updated.sell_listing_review.revision_count == 2
    assert updated.sell_listing_review.revision_instructions == "Change the title and lower the price"
    assert updated.sell_listing_review.paused_at is not None
    assert updated.sell_listing_review.deadline_at is not None
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "ready_for_confirmation"
    assert depop_listing["ready_for_confirmation"] is True
    assert [event.event_type for event in updated.events][-5:] == [
        "listing_decision_received",
        "pipeline_resumed",
        "listing_revision_requested",
        "listing_revision_applied",
        "listing_review_required",
    ]


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_revise_refreshes_review_window(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-revise-window-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    previous_paused_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    previous_deadline_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        revision_count=1,
        paused_at=previous_paused_at.isoformat(),
        deadline_at=previous_deadline_at.isoformat(),
    )

    async def fake_revise_sell_listing_for_review(
        *,
        listing_output: dict[str, Any],
        revision_instructions: str,
    ) -> tuple[dict[str, Any], None, bool]:
        return (
            {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://revised-preview",
            },
            None,
            True,
        )

    monkeypatch.setattr(orchestrator, "revise_sell_listing_for_review", fake_revise_sell_listing_for_review)

    await orchestrator.handle_sell_listing_decision(
        session.session_id,
        "revise",
        revision_instructions="Tighten description",
    )

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.sell_listing_review is not None
    assert updated.sell_listing_review.revision_count == 2
    assert updated.sell_listing_review.paused_at != previous_paused_at.isoformat()
    assert updated.sell_listing_review.deadline_at != previous_deadline_at.isoformat()
    paused_at = datetime.fromisoformat(updated.sell_listing_review.paused_at)
    deadline_at = datetime.fromisoformat(updated.sell_listing_review.deadline_at)
    assert deadline_at > paused_at
    assert deadline_at > previous_deadline_at


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_abort_completes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-abort-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    async def fake_abort_sell_listing() -> tuple[dict[str, Any], None, bool]:
        return (
            {
                "listing_status": "aborted",
                "ready_for_confirmation": False,
                "draft_status": "aborted",
                "form_screenshot_url": None,
            },
            None,
            True,
        )

    monkeypatch.setattr(orchestrator, "abort_sell_listing", fake_abort_sell_listing)

    await orchestrator.handle_sell_listing_decision(session.session_id, "abort")

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "completed"
    assert updated.error is None
    assert updated.sell_listing_review is None
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "aborted"
    assert depop_listing["ready_for_confirmation"] is False
    assert [event.event_type for event in updated.events][-5:] == [
        "listing_decision_received",
        "listing_submission_aborted",
        "listing_abort_requested",
        "listing_aborted",
        "pipeline_complete",
    ]


@pytest.mark.asyncio
async def test_fail_sell_listing_review_expires_and_cleans_up_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-expired-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        deadline_at="2026-04-04T11:59:00+00:00",
    )

    async def fake_abort_sell_listing() -> tuple[dict[str, Any], None, bool]:
        return (
            {
                "listing_status": "aborted",
                "ready_for_confirmation": False,
                "draft_status": "aborted",
                "form_screenshot_url": None,
            },
            None,
            True,
        )

    monkeypatch.setattr(orchestrator, "abort_sell_listing", fake_abort_sell_listing)

    expired = await orchestrator.expire_sell_listing_review_if_needed(session.session_id)

    updated = await session_manager.get_session(session.session_id)
    assert expired is True
    assert updated is not None
    assert updated.status == "failed"
    assert updated.error == "sell_listing_review_timeout"
    assert updated.sell_listing_review is None
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "expired"
    assert depop_listing["ready_for_confirmation"] is False
    assert [event.event_type for event in updated.events][-4:] == [
        "listing_review_cleanup_completed",
        "listing_review_expired",
        "pipeline_failed",
    ][-3:]


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_revise_at_limit_fails_and_cleans_up(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-limit-handler-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")}}
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        revision_count=orchestrator.SELL_LISTING_MAX_REVISIONS,
    )

    async def fake_abort_sell_listing() -> tuple[dict[str, Any], None, bool]:
        return (
            {
                "listing_status": "aborted",
                "ready_for_confirmation": False,
                "draft_status": "aborted",
                "form_screenshot_url": None,
            },
            None,
            True,
        )

    monkeypatch.setattr(orchestrator, "abort_sell_listing", fake_abort_sell_listing)

    await orchestrator.handle_sell_listing_decision(
        session.session_id,
        "revise",
        revision_instructions="Another change",
    )

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "failed"
    assert updated.error == "sell_listing_revision_limit_reached"
    assert updated.sell_listing_review is None
    depop_listing = updated.result["outputs"]["depop_listing"]
    assert depop_listing["listing_status"] == "revision_limit_reached"
    assert depop_listing["ready_for_confirmation"] is False
    assert [event.event_type for event in updated.events][-4:] == [
        "listing_decision_received",
        "listing_review_cleanup_completed",
        "listing_revision_limit_reached",
        "pipeline_failed",
    ]
