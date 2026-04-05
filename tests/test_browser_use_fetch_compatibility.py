from __future__ import annotations

import time
from typing import Any

import backend.agents.depop_listing_agent as depop_listing_module
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


def test_sell_pipeline_completes_with_forced_browser_use_fallback(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_USE_FORCE_FALLBACK", "true")

    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-browser-fallback-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "forced-browser-fallback-sell-test"},
        },
    )
    assert response.status_code == 200

    result = wait_for_result_status(client, response.json()["session_id"], statuses={"completed"})
    outputs = result["result"]["outputs"]

    assert result["status"] == "completed"
    assert outputs["depop_listing"]["execution_mode"] == "fallback"
    assert outputs["depop_listing"]["ready_for_confirmation"] is False
    assert outputs["depop_listing"]["browser_use"]["mode"] == "fallback"
    assert outputs["depop_listing"]["browser_use"]["error_category"] == "runtime_unavailable"
    assert [event["event_type"] for event in result["events"]].count("browser_use_fallback") == 2
    assert not any(event["event_type"] == "listing_review_required" for event in result["events"])


def test_buy_pipeline_completes_with_forced_browser_use_fallback(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_USE_FORCE_FALLBACK", "true")

    response = client.post(
        "/buy/start",
        json={
            "user_id": "buy-browser-fallback-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "forced-browser-fallback-buy-test"},
        },
    )
    assert response.status_code == 200

    result = wait_for_result_status(client, response.json()["session_id"], statuses={"completed"})
    outputs = result["result"]["outputs"]

    assert result["status"] == "completed"
    for step in ("depop_search", "ebay_search", "mercari_search", "offerup_search"):
        assert outputs[step]["execution_mode"] == "fallback"
        assert outputs[step]["browser_use"]["mode"] == "fallback"
        assert outputs[step]["browser_use"]["error_category"] == "runtime_unavailable"

    assert outputs["negotiation"]["browser_use"]["mode"] == "fallback"
    assert all(offer["execution_mode"] == "deterministic" for offer in outputs["negotiation"]["offers"])
    assert [event["event_type"] for event in result["events"]].count("browser_use_fallback") == 7


def test_sell_pipeline_supports_revise_then_confirm_review_loop_in_local_mode(
    client: TestClient,
    monkeypatch,
) -> None:
    call_count = {"value": 0}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        call_count["value"] += 1
        if call_count["value"] == 1:
            return {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://depop-form-preview-v1",
            }
        if call_count["value"] == 2:
            assert "Lower the price" in kwargs["task"]
            return {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://depop-form-preview-v2",
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
            "user_id": "sell-review-loop-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "local-review-loop-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    paused = wait_for_result_status(client, session_id, statuses={"paused"})
    assert paused["result"]["outputs"]["depop_listing"]["ready_for_confirmation"] is True

    revise_response = client.post(
        "/sell/listing-decision",
        json={
            "session_id": session_id,
            "decision": "revise",
            "revision_instructions": "Lower the price and make the title shorter",
        },
    )
    assert revise_response.status_code == 200

    revised = wait_for_result_status(client, session_id, statuses={"paused"})
    assert revised["sell_listing_review"]["revision_count"] == 1
    assert revised["result"]["outputs"]["depop_listing"]["form_screenshot_url"] == "artifact://depop-form-preview-v2"

    confirm_response = client.post(
        "/sell/listing-decision",
        json={"session_id": session_id, "decision": "confirm_submit"},
    )
    assert confirm_response.status_code == 200

    completed = wait_for_result_status(client, session_id, statuses={"completed"})
    event_types = [event["event_type"] for event in completed["events"]]

    assert call_count["value"] == 3
    assert completed["result"]["outputs"]["depop_listing"]["listing_status"] == "submitted"
    assert completed["result"]["outputs"]["depop_listing"]["ready_for_confirmation"] is False
    assert event_types.count("listing_review_required") == 2
    assert "listing_revision_applied" in event_types
    assert "listing_submitted" in event_types
    assert event_types[-1] == "pipeline_complete"


def test_buy_pipeline_completes_with_fetch_enabled_and_forced_browser_use_fallback(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FETCH_ENABLED", "true")
    monkeypatch.setenv("BROWSER_USE_FORCE_FALLBACK", "true")

    response = client.post(
        "/buy/start",
        json={
            "user_id": "fetch-browser-fallback-buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "fetch-browser-fallback-buy-test"},
        },
    )
    assert response.status_code == 200

    result = wait_for_result_status(client, response.json()["session_id"], statuses={"completed"})
    outputs = result["result"]["outputs"]

    assert result["status"] == "completed"
    assert outputs["ranking"]["top_choice"]["platform"] == "ebay"
    assert outputs["negotiation"]["offers"][0]["execution_mode"] == "deterministic"
    assert [event["event_type"] for event in result["events"]].count("browser_use_fallback") == 7


def test_sell_pipeline_supports_revise_then_confirm_review_loop_with_fetch_enabled(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FETCH_ENABLED", "true")

    call_count = {"value": 0}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        call_count["value"] += 1
        if call_count["value"] == 1:
            return {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://depop-form-preview-v1",
            }
        if call_count["value"] == 2:
            assert "Lower the price" in kwargs["task"]
            return {
                "listing_status": "ready_for_confirmation",
                "ready_for_confirmation": True,
                "draft_status": "ready",
                "form_screenshot_url": "artifact://depop-form-preview-v2",
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
            "user_id": "fetch-sell-review-loop-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "fetch-review-loop-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    paused = wait_for_result_status(client, session_id, statuses={"paused"})
    assert paused["result"]["outputs"]["depop_listing"]["ready_for_confirmation"] is True

    revise_response = client.post(
        "/sell/listing-decision",
        json={
            "session_id": session_id,
            "decision": "revise",
            "revision_instructions": "Lower the price and make the title shorter",
        },
    )
    assert revise_response.status_code == 200

    revised = wait_for_result_status(client, session_id, statuses={"paused"})
    assert revised["sell_listing_review"]["revision_count"] == 1
    assert revised["result"]["outputs"]["depop_listing"]["form_screenshot_url"] == "artifact://depop-form-preview-v2"

    confirm_response = client.post(
        "/sell/listing-decision",
        json={"session_id": session_id, "decision": "confirm_submit"},
    )
    assert confirm_response.status_code == 200

    completed = wait_for_result_status(client, session_id, statuses={"completed"})
    event_types = [event["event_type"] for event in completed["events"]]

    assert call_count["value"] == 3
    assert completed["result"]["outputs"]["depop_listing"]["listing_status"] == "submitted"
    assert completed["result"]["outputs"]["depop_listing"]["ready_for_confirmation"] is False
    assert event_types.count("listing_review_required") == 2
    assert "listing_revision_applied" in event_types
    assert "listing_submitted" in event_types
    assert event_types[-1] == "pipeline_complete"
