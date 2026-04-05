from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import PipelineStartRequest, SellListingReviewState
from backend.session import session_manager

client = TestClient(app)


@pytest.mark.asyncio
async def test_sell_listing_result_endpoint_preserves_paused_review_state() -> None:
    await session_manager.reset()
    now = datetime.now(timezone.utc)
    paused_at = (now - timedelta(minutes=5)).isoformat()
    deadline_at = (now + timedelta(hours=1)).isoformat()

    session = await session_manager.create_session(
        session_id="sell-paused-result-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        latest_decision="revise",
        revision_instructions="Lower the price",
        revision_count=2,
        paused_at=paused_at,
        deadline_at=deadline_at,
    )
    session.result = {
        "pipeline": "sell",
        "outputs": {
            "depop_listing": {
                "agent": "depop_listing_agent",
                "display_name": "Depop Listing Agent",
                "summary": "Paused for review",
                "title": "Vintage Hoodie",
                "description": "Blue hoodie in good condition",
                "suggested_price": 48.0,
                "category_path": "Men/Tops/Hoodies",
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
            }
        },
    }

    response = client.get(f"/result/{session.session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "paused"
    assert payload["sell_listing_review"] == {
        "state": "ready_for_confirmation",
        "step": "depop_listing",
        "platform": "depop",
        "latest_decision": "revise",
        "revision_instructions": "Lower the price",
        "revision_count": 2,
        "paused_at": paused_at,
        "deadline_at": deadline_at,
    }
    assert payload["result"]["outputs"]["depop_listing"]["ready_for_confirmation"] is True
    assert payload["result"]["outputs"]["depop_listing"]["listing_status"] == "ready_for_confirmation"


@pytest.mark.asyncio
async def test_session_manager_can_clear_sell_listing_review_state() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-clear-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )

    await session_manager.update_sell_listing_review(
        session.session_id,
        SellListingReviewState(state="ready_for_confirmation", revision_count=1),
    )
    await session_manager.clear_sell_listing_review(session.session_id)

    updated = await session_manager.get_session(session.session_id)
    assert updated is not None
    assert updated.sell_listing_review is None
