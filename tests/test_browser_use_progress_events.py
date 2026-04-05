from __future__ import annotations

import time
from typing import Any

import backend.agents.depop_listing_agent as depop_listing_module
import backend.agents.depop_search_agent as depop_search_module
import backend.agents.ebay_search_agent as ebay_search_module
import backend.agents.mercari_search_agent as mercari_search_module
import backend.agents.negotiation_agent as negotiation_module
import backend.agents.offerup_search_agent as offerup_search_module
from fastapi.testclient import TestClient


def wait_for_result_status(
    client: TestClient,
    session_id: str,
    *,
    statuses: set[str],
    timeout: float = 3.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in statuses:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach any of the expected states: {sorted(statuses)}")


def wait_for_event_count(
    client: TestClient,
    session_id: str,
    *,
    event_type: str,
    count: int = 1,
    timeout: float = 3.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if sum(1 for event in payload["events"] if event["event_type"] == event_type) >= count:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not emit {count} {event_type} event(s)")


def start_pipeline(client: TestClient, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(endpoint, json=payload)
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    return wait_for_result_status(client, session_id, statuses={"completed", "failed"})


def build_browser_results(platform: str) -> list[dict[str, object]]:
    return [
        {
            "platform": platform,
            "title": f"{platform} live listing #1",
            "price": 41.25,
            "url": f"https://{platform}.example/live-1",
            "condition": "good",
            "seller": f"{platform}_seller_1",
            "seller_score": 111,
            "posted_at": "2026-04-03",
        },
        {
            "platform": platform,
            "title": f"{platform} live listing #2",
            "price": 44.75,
            "url": f"https://{platform}.example/live-2",
            "condition": "great",
            "seller": f"{platform}_seller_2",
            "seller_score": 222,
            "posted_at": "2026-04-02",
        },
    ]


def test_buy_pipeline_emits_fallback_listing_found_events(client: TestClient) -> None:
    result = start_pipeline(
        client,
        "/buy/start",
        {
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "fallback-event-test"},
        },
    )

    listing_events = [event for event in result["events"] if event["event_type"] == "listing_found"]
    fallback_events = [event for event in result["events"] if event["event_type"] == "browser_use_fallback"]
    assert len(listing_events) == 8
    assert len(fallback_events) == 7
    assert {event["data"]["source"] for event in listing_events} == {"fallback"}
    assert {event["data"]["platform"] for event in listing_events} == {"depop", "ebay", "mercari", "offerup"}
    assert {event["data"]["platform"] for event in fallback_events} == {"depop", "ebay", "mercari", "offerup"}


def test_buy_pipeline_emits_browser_use_listing_events_when_live_search_succeeds(
    client: TestClient,
    monkeypatch,
) -> None:
    async def fake_run_marketplace_search(platform: str, query: str, max_results: int = 10) -> list[dict[str, object]]:
        if platform == "depop":
            return build_browser_results("depop")
        raise RuntimeError("fallback other platforms")

    monkeypatch.setattr(depop_search_module, "run_marketplace_search", fake_run_marketplace_search)
    monkeypatch.setattr(ebay_search_module, "run_marketplace_search", fake_run_marketplace_search)
    monkeypatch.setattr(mercari_search_module, "run_marketplace_search", fake_run_marketplace_search)
    monkeypatch.setattr(offerup_search_module, "run_marketplace_search", fake_run_marketplace_search)

    result = start_pipeline(
        client,
        "/buy/start",
        {
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "live-search-event-test"},
        },
    )

    depop_events = [
        event for event in result["events"] if event["event_type"] == "listing_found" and event["data"]["platform"] == "depop"
    ]
    assert len(depop_events) == 2
    assert {event["data"]["source"] for event in depop_events} == {"browser_use"}
    assert depop_events[0]["data"]["title"] == "depop live listing #1"


def test_sell_pipeline_emits_draft_created_event_with_live_metadata(client: TestClient, monkeypatch) -> None:
    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        return {
            "listing_status": "ready_for_confirmation",
            "ready_for_confirmation": True,
            "draft_status": "ready",
            "form_screenshot_url": "artifact://depop-form-preview",
        }

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(depop_listing_module.Path, "exists", lambda self: True)

    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "draft-created-event-test"},
        },
    )
    assert response.status_code == 200
    result = wait_for_result_status(client, response.json()["session_id"], statuses={"paused"})

    draft_events = [event for event in result["events"] if event["event_type"] == "draft_created"]
    assert draft_events == [
        {
            "session_id": result["session_id"],
            "event_type": "draft_created",
            "pipeline": "sell",
            "step": "depop_listing",
            "data": {
                "agent_name": "depop_listing_agent",
                "platform": "depop",
                "title": "Patagonia hoodie - Excellent Condition",
                "suggested_price": 78.43,
                "category_path": "Men/Tops/Hoodies",
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://depop-form-preview",
                "source": "browser_use",
            },
            "timestamp": draft_events[0]["timestamp"],
        }
    ]
    review_events = [event for event in result["events"] if event["event_type"] == "listing_review_required"]
    assert len(review_events) == 1
    assert review_events[0]["data"]["listing_status"] == "ready_for_confirmation"
    assert review_events[0]["data"]["ready_for_confirmation"] is True
    assert review_events[0]["data"]["output"]["listing_status"] == "ready_for_confirmation"
    assert review_events[0]["data"]["output"]["ready_for_confirmation"] is True


def test_sell_pipeline_emits_review_confirmation_events(client: TestClient, monkeypatch) -> None:
    call_count = {"value": 0}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        call_count["value"] += 1
        if call_count["value"] == 1:
            return {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://depop-form-preview",
            }
        return {
            "listing_status": "submitted",
            "ready_for_confirmation": False,
            "draft_status": "submitted",
            "form_screenshot_url": "artifact://depop-form-submitted",
        }

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(depop_listing_module.Path, "exists", lambda self: True)

    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "review-confirmation-event-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    paused = wait_for_result_status(client, session_id, statuses={"paused"})
    assert paused["status"] == "paused"
    assert paused["result"]["outputs"]["depop_listing"]["ready_for_confirmation"] is True

    decision_response = client.post(
        "/sell/listing-decision",
        json={"session_id": session_id, "decision": "confirm_submit"},
    )
    assert decision_response.status_code == 200

    completed = wait_for_result_status(client, session_id, statuses={"completed"})
    event_types = [event["event_type"] for event in completed["events"]]

    def first_index(event_type: str) -> int:
        return next(i for i, event in enumerate(completed["events"]) if event["event_type"] == event_type)

    assert first_index("listing_review_required") < first_index("listing_decision_received")
    assert first_index("listing_decision_received") < first_index("pipeline_resumed")
    assert first_index("pipeline_resumed") < first_index("listing_submit_requested")
    assert first_index("listing_submit_requested") < first_index("listing_submitted")
    assert event_types[-1] == "pipeline_complete"

    review_requested = next(event for event in completed["events"] if event["event_type"] == "listing_review_required")
    submitted = next(event for event in completed["events"] if event["event_type"] == "listing_submitted")
    assert review_requested["data"]["listing_status"] == "ready_for_confirmation"
    assert review_requested["data"]["ready_for_confirmation"] is True
    assert review_requested["data"]["output"]["listing_status"] == "ready_for_confirmation"
    assert review_requested["data"]["output"]["ready_for_confirmation"] is True
    assert submitted["data"]["platform"] == "depop"
    assert submitted["data"]["output"]["listing_status"] == "submitted"
    assert submitted["data"]["output"]["ready_for_confirmation"] is False


def test_sell_pipeline_emits_revision_events_and_repauses(client: TestClient, monkeypatch) -> None:
    call_count = {"value": 0}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        call_count["value"] += 1
        if call_count["value"] == 1:
            return {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://depop-form-preview",
            }
        return {
            "listing_status": "ready_for_confirmation",
            "ready_for_confirmation": True,
            "draft_status": "ready",
            "form_screenshot_url": "artifact://depop-form-revised",
        }

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(depop_listing_module.Path, "exists", lambda self: True)

    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "review-revision-event-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    paused = wait_for_result_status(client, session_id, statuses={"paused"})
    assert paused["status"] == "paused"

    decision_response = client.post(
        "/sell/listing-decision",
        json={
            "session_id": session_id,
            "decision": "revise",
            "revision_instructions": "Change the title and lower the price",
        },
    )
    assert decision_response.status_code == 200

    resumed = wait_for_event_count(client, session_id, event_type="listing_revision_applied")
    event_types = [event["event_type"] for event in resumed["events"]]

    def first_index(event_type: str) -> int:
        return next(i for i, event in enumerate(resumed["events"]) if event["event_type"] == event_type)

    assert first_index("listing_review_required") < first_index("listing_decision_received")
    assert first_index("listing_decision_received") < first_index("pipeline_resumed")
    assert first_index("pipeline_resumed") < first_index("listing_revision_requested")
    assert first_index("listing_revision_requested") < first_index("listing_revision_applied")
    assert event_types.count("listing_review_required") == 2
    assert event_types[-1] == "listing_review_required"

    revision_requested = next(event for event in resumed["events"] if event["event_type"] == "listing_revision_requested")
    revision_applied = next(event for event in resumed["events"] if event["event_type"] == "listing_revision_applied")
    review_requested = [event for event in resumed["events"] if event["event_type"] == "listing_review_required"][-1]
    assert revision_requested["data"]["revision_instructions"] == "Change the title and lower the price"
    assert revision_requested["data"]["revision_count"] == 1
    assert revision_applied["data"]["revision_count"] == 1
    assert revision_applied["data"]["output"]["listing_status"] == "ready_for_confirmation"
    assert revision_applied["data"]["output"]["ready_for_confirmation"] is True
    assert review_requested["data"]["output"]["form_screenshot_url"] == "artifact://depop-form-revised"
    assert review_requested["data"]["ready_for_confirmation"] is True


def test_sell_pipeline_emits_browser_use_fallback_event_when_listing_draft_fails(client: TestClient, monkeypatch) -> None:
    async def broken_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("profile expired")

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", broken_run_structured_browser_task)
    monkeypatch.setattr(depop_listing_module.Path, "exists", lambda self: True)

    result = start_pipeline(
        client,
        "/sell/start",
        {
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "draft-fallback-event-test"},
        },
    )

    fallback_events = [event for event in result["events"] if event["event_type"] == "browser_use_fallback"]
    assert fallback_events[-1]["data"] == {
        "agent_name": "depop_listing_agent",
        "platform": "depop",
        "error": "profile_missing",
    }


def test_buy_pipeline_emits_offer_sent_events_when_live_negotiation_succeeds(client: TestClient, monkeypatch) -> None:
    call_count = {"value": 0}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        call_count["value"] += 1
        return {
            "status": "sent",
            "failure_reason": None,
            "conversation_url": f"https://messages.example/{call_count['value']}",
        }

    monkeypatch.setattr(negotiation_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(negotiation_module.Path, "exists", lambda self: True)

    result = start_pipeline(
        client,
        "/buy/start",
        {
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "offer-sent-event-test"},
        },
    )

    prepared_events = [event for event in result["events"] if event["event_type"] == "offer_prepared"]
    sent_events = [event for event in result["events"] if event["event_type"] == "offer_sent"]
    failed_events = [event for event in result["events"] if event["event_type"] == "offer_failed"]

    assert len(prepared_events) == 3
    assert len(sent_events) == 3
    assert failed_events == []
    assert sent_events[0]["data"]["status"] == "sent"
    assert sent_events[0]["data"]["source"] == "browser_use"
    assert sent_events[0]["data"]["conversation_url"] == "https://messages.example/1"
