from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import PipelineStartRequest, SellListingReviewState
from backend.session import session_manager

client = TestClient(app)


@pytest.mark.asyncio
async def test_sell_listing_decision_endpoint_dispatches_to_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-review-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    called = asyncio.Event()
    captured: dict[str, str | None] = {}

    async def fake_handle_sell_listing_decision(
        session_id: str,
        decision: str,
        *,
        revision_instructions: str | None = None,
    ) -> None:
        captured["session_id"] = session_id
        captured["decision"] = decision
        captured["revision_instructions"] = revision_instructions
        called.set()

    monkeypatch.setattr("backend.orchestrator.handle_sell_listing_decision", fake_handle_sell_listing_decision)

    response = client.post(
        "/sell/listing-decision",
        json={"session_id": session.session_id, "decision": "confirm_submit"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "accepted",
        "session_id": session.session_id,
        "pipeline": "sell",
        "decision": "confirm_submit",
        "session_status": "paused",
        "queued_action": "submit_listing",
        "review_state": {
            "state": "ready_for_confirmation",
            "step": "depop_listing",
            "platform": "depop",
            "latest_decision": None,
            "revision_instructions": None,
            "revision_count": 0,
            "paused_at": None,
            "deadline_at": None,
        },
        "revision_instructions": None,
    }
    await asyncio.wait_for(called.wait(), timeout=1.0)
    assert captured == {
        "session_id": session.session_id,
        "decision": "confirm_submit",
        "revision_instructions": None,
    }


@pytest.mark.asyncio
async def test_sell_listing_decision_endpoint_rejects_unknown_session() -> None:
    await session_manager.reset()

    response = client.post(
        "/sell/listing-decision",
        json={"session_id": "missing-session", "decision": "abort"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_sell_listing_decision_endpoint_requires_paused_review_session() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-running-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "running"

    response = client.post(
        "/sell/listing-decision",
        json={"session_id": session.session_id, "decision": "revise", "revision_instructions": "  Lower the price  "},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Session is not awaiting a sell listing decision"


@pytest.mark.asyncio
async def test_sell_listing_decision_endpoint_rejects_buy_session() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="buy-session",
        pipeline="buy",
        request=PipelineStartRequest(input={"query": "Nike hoodie", "budget": 60}),
    )

    response = client.post(
        "/sell/listing-decision",
        json={"session_id": session.session_id, "decision": "abort"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Session is not a sell pipeline"


@pytest.mark.asyncio
async def test_sell_listing_decision_endpoint_echoes_normalized_revision_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-revise-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    async def fake_handle_sell_listing_decision(
        session_id: str,
        decision: str,
        *,
        revision_instructions: str | None = None,
    ) -> None:
        return None

    monkeypatch.setattr("backend.orchestrator.handle_sell_listing_decision", fake_handle_sell_listing_decision)

    response = client.post(
        "/sell/listing-decision",
        json={"session_id": session.session_id, "decision": "revise", "revision_instructions": "  Lower the price  "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["decision"] == "revise"
    assert payload["queued_action"] == "apply_revision"
    assert payload["revision_instructions"] == "Lower the price"
    assert payload["review_state"]["revision_instructions"] is None


@pytest.mark.asyncio
async def test_get_result_expires_paused_sell_listing_review(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-expire-on-result-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.result = {
        "pipeline": "sell",
        "outputs": {
            "depop_listing": {
                "agent": "depop_listing_agent",
                "display_name": "Depop Listing Agent",
                "summary": "Prepared a Depop listing draft",
                "title": "Nike hoodie - Good Condition",
                "description": "Good prefilled draft",
                "suggested_price": 72.0,
                "category_path": "Men/Tops/Hoodies",
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "browser_use",
            }
        },
    }
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        deadline_at="2026-04-04T11:59:00+00:00",
    )

    async def fake_abort_sell_listing() -> tuple[dict[str, object], None, bool]:
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

    monkeypatch.setattr("backend.orchestrator.abort_sell_listing", fake_abort_sell_listing)

    response = client.get(f"/result/{session.session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error"] == "sell_listing_review_timeout"
    assert payload["sell_listing_review"] is None
    assert payload["result"]["outputs"]["depop_listing"]["listing_status"] == "expired"
    assert payload["result"]["outputs"]["depop_listing"]["ready_for_confirmation"] is False
    assert [event["event_type"] for event in payload["events"]][-3:] == [
        "listing_review_cleanup_completed",
        "listing_review_expired",
        "pipeline_failed",
    ]


@pytest.mark.asyncio
async def test_sell_listing_decision_endpoint_rejects_expired_paused_review_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-expired-review-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        paused_at=(datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(),
        deadline_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
    )

    called = False

    async def fake_handle_sell_listing_decision(
        session_id: str,
        decision: str,
        *,
        revision_instructions: str | None = None,
    ) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("backend.orchestrator.handle_sell_listing_decision", fake_handle_sell_listing_decision)

    response = client.post(
        "/sell/listing-decision",
        json={"session_id": session.session_id, "decision": "confirm_submit"},
    )

    assert response.status_code in {409, 410}
    assert "expired" in response.json()["detail"].lower()
    assert called is False


@pytest.mark.asyncio
async def test_sell_listing_decision_endpoint_rejects_revision_when_revision_budget_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-revision-limit-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    session.status = "paused"
    session.sell_listing_review = SellListingReviewState(
        state="ready_for_confirmation",
        revision_count=99,
    )

    called = False

    async def fake_handle_sell_listing_decision(
        session_id: str,
        decision: str,
        *,
        revision_instructions: str | None = None,
    ) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("backend.orchestrator.handle_sell_listing_decision", fake_handle_sell_listing_decision)

    response = client.post(
        "/sell/listing-decision",
        json={
            "session_id": session.session_id,
            "decision": "revise",
            "revision_instructions": "Lower the price by $5",
        },
    )

    assert response.status_code == 409
    assert "revision" in response.json()["detail"].lower()
    assert called is False
