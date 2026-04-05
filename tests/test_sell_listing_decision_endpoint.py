from __future__ import annotations

import asyncio

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
    assert response.json() == {"ok": True}
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
        json={"session_id": session.session_id, "decision": "abort"},
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
