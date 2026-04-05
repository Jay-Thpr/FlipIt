from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import (
    PipelineStartRequest,
    RunCorrectionRequest,
    RunSellListingDecisionRequest,
    SellListingReviewState,
    SessionEvent,
)
from backend.session import session_manager

client = TestClient(app)


def wait_for_terminal_result(client: TestClient, session_id: str, timeout: float = 3.0) -> dict:
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach a terminal state")


def test_item_scoped_run_start_and_latest_lookup(client: TestClient) -> None:
    response = client.post(
        "/items/item-123/sell/run",
        json={
            "user_id": "frontend-user",
            "input": {"image_urls": ["https://example.com/item.jpg"], "notes": "Nike tee"},
            "metadata": {"source": "frontend"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_id"] == "item-123"
    assert payload["run_id"] == payload["session_id"]
    assert payload["phase"] == "queued"
    assert payload["next_action"] == {"type": "wait", "payload": {}}
    assert payload["run_url"].endswith(f"/runs/{payload['run_id']}")

    terminal = wait_for_terminal_result(client, payload["run_id"])
    assert terminal["run_id"] == payload["run_id"]
    assert terminal["item_id"] == "item-123"
    assert terminal["phase"] == "completed"
    assert terminal["next_action"]["type"] == "show_result"

    latest = client.get("/items/item-123/runs/latest")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["run_id"] == payload["run_id"]
    assert latest_payload["item_id"] == "item-123"


@pytest.mark.asyncio
async def test_runs_endpoint_normalizes_paused_sell_correction_state() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="sell-correction-run",
        pipeline="sell",
        request=PipelineStartRequest(
            input={"image_urls": ["https://example.com/item.jpg"], "notes": "Unknown item"},
            metadata={"item_id": "item-correct-1"},
        ),
    )
    session.status = "paused"
    session.result = {
        "pipeline": "sell",
        "outputs": {
            "vision_analysis": {
                "agent": "vision_agent",
                "display_name": "Vision Agent",
                "summary": "Low confidence result",
                "detected_item": "hoodie",
                "brand": "Unknown",
                "category": "tops",
                "condition": "good",
                "confidence": 0.42,
            }
        },
    }
    session.events.append(
        SessionEvent(
            session_id=session.session_id,
            event_type="vision_low_confidence",
            pipeline="sell",
            step="vision_analysis",
            data={"message": "Please confirm the detected item."},
        )
    )

    response = client.get(f"/runs/{session.session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["phase"] == "awaiting_user_correction"
    assert payload["next_action"]["type"] == "submit_correction"
    assert payload["next_action"]["payload"]["message"] == "Please confirm the detected item."
    assert payload["next_action"]["payload"]["suggestion"]["confidence"] == 0.42
    assert payload["item_id"] == "item-correct-1"


@pytest.mark.asyncio
async def test_runs_endpoint_normalizes_buy_summary_and_result_source() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="buy-summary-run",
        pipeline="buy",
        request=PipelineStartRequest(
            input={"query": "Nike tee size M", "budget": 50},
            metadata={"item_id": "item-buy-1"},
        ),
    )
    session.status = "completed"
    session.result = {
        "pipeline": "buy",
        "outputs": {
            "depop_search": {
                "agent": "depop_search_agent",
                "display_name": "Depop Search Agent",
                "summary": "Found Depop listings",
                "results": [
                    {
                        "platform": "depop",
                        "title": "Vintage Nike tee",
                        "price": 38.0,
                        "url": "https://depop.example/1",
                        "condition": "good",
                        "seller": "seller-1",
                        "seller_score": 4,
                        "posted_at": "2026-04-05T10:00:00+00:00",
                    }
                ],
                "execution_mode": "browser_use",
            },
            "ebay_search": {
                "agent": "ebay_search_agent",
                "display_name": "eBay Search Agent",
                "summary": "Found eBay listings",
                "results": [],
                "execution_mode": "httpx",
            },
            "mercari_search": {
                "agent": "mercari_search_agent",
                "display_name": "Mercari Search Agent",
                "summary": "Mercari failed — no results",
                "results": [],
                "execution_mode": "fallback",
            },
            "offerup_search": {
                "agent": "offerup_search_agent",
                "display_name": "OfferUp Search Agent",
                "summary": "Found OfferUp listings",
                "results": [
                    {
                        "platform": "offerup",
                        "title": "Nike tee medium",
                        "price": 35.0,
                        "url": "https://offerup.example/1",
                        "condition": "good",
                        "seller": "seller-2",
                        "seller_score": 5,
                        "posted_at": "2026-04-05T10:00:00+00:00",
                    }
                ],
                "execution_mode": "fallback",
            },
            "ranking": {
                "agent": "ranking_agent",
                "display_name": "Ranking Agent",
                "summary": "Ranked listings",
                "top_choice": {
                    "platform": "depop",
                    "title": "Vintage Nike tee",
                    "price": 38.0,
                    "score": 0.92,
                    "reason": "Best value",
                    "url": "https://depop.example/1",
                    "seller": "seller-1",
                    "seller_score": 4,
                    "posted_at": "2026-04-05T10:00:00+00:00",
                },
                "candidate_count": 2,
                "ranked_listings": [],
                "median_price": 36.5,
            },
            "negotiation": {
                "agent": "negotiation_agent",
                "display_name": "Negotiation Agent",
                "summary": "Prepared offers",
                "offers": [
                    {
                        "platform": "depop",
                        "seller": "seller-1",
                        "listing_url": "https://depop.example/1",
                        "listing_title": "Vintage Nike tee",
                        "target_price": 32.0,
                        "message": "Would you take $32?",
                        "status": "sent",
                        "conversation_url": "https://messages.example/1",
                        "execution_mode": "browser_use",
                        "attempt_source": "browser_use",
                    },
                    {
                        "platform": "offerup",
                        "seller": "seller-2",
                        "listing_url": "https://offerup.example/1",
                        "listing_title": "Nike tee medium",
                        "target_price": 30.0,
                        "message": "Would you take $30?",
                        "status": "failed",
                        "failure_reason": "seller unavailable",
                        "execution_mode": "deterministic",
                        "attempt_source": "prepared",
                    },
                ],
            },
        },
    }
    session.events.append(
        SessionEvent(
            session_id=session.session_id,
            event_type="agent_error",
            pipeline="buy",
            step="mercari_search",
            data={"error": "timeout"},
        )
    )

    response = client.get(f"/runs/{session.session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["phase"] == "completed"
    assert payload["result_source"] == "mixed"
    assert payload["search_summary"] == {
        "total_results": 2,
        "results_by_platform": {"depop": 1, "ebay": 0, "mercari": 0, "offerup": 1},
        "platforms_searched": 2,
        "platforms_failed": 1,
        "median_price": 36.5,
    }
    assert payload["top_choice"]["platform"] == "depop"
    assert payload["offer_summary"]["total_offers"] == 2
    assert payload["offer_summary"]["offers_sent"] == 1
    assert payload["offer_summary"]["offers_failed"] == 1
    assert payload["offer_summary"]["best_offer"]["target_price"] == 32.0


@pytest.mark.asyncio
async def test_run_stream_alias_reuses_legacy_stream() -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="run-stream-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": []}, metadata={"item_id": "item-stream"}),
    )
    await session_manager.append_event(
        SessionEvent(
            session_id=session.session_id,
            event_type="pipeline_complete",
            pipeline="sell",
            data={"outputs": {}},
        )
    )

    response = client.get(f"/runs/{session.session_id}/stream")

    assert response.status_code == 200
    assert "event: pipeline_complete" in response.text


@pytest.mark.asyncio
async def test_run_scoped_sell_endpoints_delegate_to_legacy_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()
    session = await session_manager.create_session(
        session_id="run-review-session",
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": []}, metadata={"item_id": "item-review"}),
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

    decision_response = client.post(
        f"/runs/{session.session_id}/sell/listing-decision",
        json=RunSellListingDecisionRequest(decision="revise", revision_instructions=" Lower the price ").model_dump(),
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["session_id"] == session.session_id
    assert decision_response.json()["decision"] == "revise"
    assert decision_response.json()["queued_action"] == "apply_revision"
    await asyncio.wait_for(called.wait(), timeout=1.0)
    assert captured == {
        "session_id": session.session_id,
        "decision": "revise",
        "revision_instructions": "Lower the price",
    }

    correction_called = asyncio.Event()

    async def fake_resume_sell_pipeline(session_id: str, corrected_item: dict[str, object]) -> None:
        assert session_id == session.session_id
        assert corrected_item == {"brand": "Nike", "detected_item": "hoodie"}
        correction_called.set()

    monkeypatch.setattr("backend.orchestrator.resume_sell_pipeline", fake_resume_sell_pipeline)

    correction_response = client.post(
        f"/runs/{session.session_id}/sell/correct",
        json=RunCorrectionRequest(corrected_item={"brand": "Nike", "detected_item": "hoodie"}).model_dump(),
    )
    assert correction_response.status_code == 200
    assert correction_response.json() == {"ok": True}
    await asyncio.wait_for(correction_called.wait(), timeout=1.0)
