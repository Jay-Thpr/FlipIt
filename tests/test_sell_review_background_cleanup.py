from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from backend import orchestrator
from backend.main import run_sell_review_cleanup_sweep
from backend.schemas import PipelineStartRequest, SellListingReviewState
from backend.session import session_manager


def _listing_output(*, ready_for_confirmation: bool, listing_status: str) -> dict[str, Any]:
    return {
        "agent": "depop_listing_agent",
        "display_name": "Depop Listing Agent",
        "summary": "Prepared a Depop listing draft",
        "title": "Nike hoodie",
        "description": "Draft",
        "suggested_price": 72.0,
        "category_path": "Men/Tops/Hoodies",
        "listing_status": listing_status,
        "ready_for_confirmation": ready_for_confirmation,
        "draft_status": "browser_use",
    }


@pytest.mark.asyncio
async def test_cleanup_sweep_expires_abandoned_paused_session(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="bg-expire-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {
        "pipeline": "sell",
        "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")},
    }
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        deadline_at="2020-01-01T00:00:00+00:00",
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

    await run_sell_review_cleanup_sweep()

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "failed"
    assert updated.error == "sell_listing_review_timeout"
    assert updated.sell_listing_review is None
    assert updated.result["outputs"]["depop_listing"]["listing_status"] == "expired"
    types = [e.event_type for e in updated.events]
    assert "listing_review_expired" in types
    assert "pipeline_failed" in types


@pytest.mark.asyncio
async def test_cleanup_sweep_skips_non_expired_review() -> None:
    await session_manager.reset()
    future = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    session = await session_manager.create_session(
        session_id="bg-future-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {
        "pipeline": "sell",
        "outputs": {"depop_listing": _listing_output(ready_for_confirmation=True, listing_status="ready_for_confirmation")},
    }
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation", deadline_at=future)

    await run_sell_review_cleanup_sweep()

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "paused"
    assert updated.sell_listing_review is not None


@pytest.mark.asyncio
async def test_cleanup_sweep_skips_buy_pipeline_sessions() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="bg-buy-session",
        pipeline="buy",
        request=PipelineStartRequest(input={"query": "shoes", "budget": 50.0}),
    )
    session.status = "running"

    await run_sell_review_cleanup_sweep()

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.status == "running"


@pytest.mark.asyncio
async def test_cleanup_sweep_no_sessions_is_safe() -> None:
    await session_manager.reset()
    await run_sell_review_cleanup_sweep()


@pytest.mark.asyncio
async def test_list_paused_sell_review_session_ids_only_lists_matching() -> None:
    await session_manager.reset()
    s1 = await session_manager.create_session(
        session_id="listed-paused",
        pipeline="sell",
        request=PipelineStartRequest(input={}),
    )
    s1.status = "paused"
    s1.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    s2 = await session_manager.create_session(
        session_id="listed-running",
        pipeline="sell",
        request=PipelineStartRequest(input={}),
    )
    s2.status = "running"
    s2.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    ids = await session_manager.list_paused_sell_review_session_ids()
    assert ids == ["listed-paused"]
