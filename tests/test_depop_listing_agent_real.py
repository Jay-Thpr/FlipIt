from __future__ import annotations

import time
from typing import Any

import backend.agents.depop_listing_agent as depop_listing_module
import pytest
from fastapi.testclient import TestClient

from backend.agents.depop_listing_agent import app as depop_listing_app


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


def build_sell_previous_outputs() -> dict[str, Any]:
    return {
        "vision_analysis": {
            "agent": "vision_agent",
            "display_name": "Vision Agent",
            "summary": "Inferred Patagonia hoodie in excellent condition",
            "detected_item": "hoodie",
            "brand": "Patagonia",
            "category": "apparel",
            "condition": "excellent",
            "confidence": 0.88,
        },
        "ebay_sold_comps": {
            "agent": "ebay_sold_comps_agent",
            "display_name": "eBay Sold Comps Agent",
            "summary": "Estimated 11 sold eBay comps for Patagonia hoodie",
            "median_sold_price": 70.66,
            "low_sold_price": 55.11,
            "high_sold_price": 86.21,
            "sample_size": 11,
        },
        "pricing": {
            "agent": "pricing_agent",
            "display_name": "Pricing Agent",
            "summary": "Priced Patagonia hoodie at $78.43 with estimated profit $41.38",
            "recommended_list_price": 78.43,
            "expected_profit": 41.38,
            "pricing_confidence": 0.91,
        },
    }


def test_depop_listing_agent_builds_listing_from_real_sell_outputs() -> None:
    payload = {
        "session_id": "depop-listing-real-session",
        "pipeline": "sell",
        "step": "depop_listing",
        "input": {
            "original_input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "previous_outputs": build_sell_previous_outputs(),
        },
        "context": {"request_metadata": {"source": "depop-listing-real-test"}},
    }

    with TestClient(depop_listing_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["title"] == "Patagonia hoodie - Excellent Condition"
    assert result["output"]["suggested_price"] == 78.43
    assert result["output"]["category_path"] == "Men/Tops/Hoodies"
    assert "Patagonia hoodie in excellent condition." in result["output"]["description"]
    assert "Recent eBay sold range: $55.11-$86.21 across 11 comps." in result["output"]["description"]
    assert result["output"]["summary"] == "Prepared Depop listing for Patagonia hoodie at $78.43"
    assert result["output"]["draft_status"] == "fallback"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "profile_missing"
    assert result["output"]["form_screenshot_url"] is None
    assert result["output"]["browser_use"] == {
        "mode": "skipped",
        "attempted_live_run": False,
        "profile_name": "depop",
        "profile_available": False,
        "error_category": "profile_missing",
        "detail": "Skipped live Depop draft creation because the warmed depop profile is missing.",
    }


def test_depop_listing_agent_records_browser_use_confirmation(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "listing_status": "ready_for_confirmation",
            "ready_for_confirmation": True,
            "draft_status": "ready",
            "form_screenshot_url": "artifact://depop-form-preview",
        }

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(depop_listing_module.Path, "exists", lambda self: True)

    payload = {
        "session_id": "depop-listing-browser-session",
        "pipeline": "sell",
        "step": "depop_listing",
        "input": {
            "original_input": {"image_urls": [], "notes": "Patagonia hoodie in excellent condition"},
            "previous_outputs": build_sell_previous_outputs(),
        },
        "context": {},
    }

    with TestClient(depop_listing_app) as client:
        response = client.post("/task", json=payload)

    result = response.json()
    assert result["status"] == "completed"
    assert str(captured["user_data_dir"]).endswith("/profiles/depop")
    assert "Patagonia hoodie - Excellent Condition" in str(captured["task"])
    assert result["output"]["listing_status"] == "ready_for_confirmation"
    assert result["output"]["ready_for_confirmation"] is True
    assert result["output"]["draft_status"] == "ready"
    assert result["output"]["execution_mode"] == "browser_use"
    assert result["output"]["browser_use_error"] is None
    assert result["output"]["form_screenshot_url"] == "artifact://depop-form-preview"
    assert result["output"]["browser_use"] == {
        "mode": "browser_use",
        "attempted_live_run": True,
        "profile_name": "depop",
        "profile_available": True,
        "error_category": None,
        "detail": "Live Depop listing was prepared through Browser Use and paused for user confirmation.",
    }


def test_depop_listing_agent_uses_fallback_copy_for_sparse_input(monkeypatch) -> None:
    async def broken_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("login expired")

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", broken_run_structured_browser_task)
    monkeypatch.setattr(depop_listing_module.Path, "exists", lambda self: True)

    payload = {
        "session_id": "depop-listing-fallback-session",
        "pipeline": "sell",
        "step": "depop_listing",
        "input": {
            "original_input": {"image_urls": [], "notes": None},
            "previous_outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Inferred item in good condition",
                    "detected_item": "item",
                    "brand": "Unknown",
                    "category": "unknown",
                    "condition": "good",
                    "confidence": 0.55,
                },
                "ebay_sold_comps": {
                    "agent": "ebay_sold_comps_agent",
                    "display_name": "eBay Sold Comps Agent",
                    "summary": "Estimated 16 sold eBay comps for item",
                    "median_sold_price": 32.0,
                    "low_sold_price": 22.4,
                    "high_sold_price": 41.6,
                    "sample_size": 16,
                },
                "pricing": {
                    "agent": "pricing_agent",
                    "display_name": "Pricing Agent",
                    "summary": "Priced item at $32.0 with estimated profit $15.68",
                    "recommended_list_price": 32.0,
                    "expected_profit": 15.68,
                    "pricing_confidence": 0.82,
                },
            },
        },
        "context": {},
    }

    with TestClient(depop_listing_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["title"] == "Item - Good Condition"
    assert result["output"]["suggested_price"] == 32.0
    assert result["output"]["category_path"] == "Men/Tops/T-Shirts"
    assert "Clean item ready to list." in result["output"]["description"]
    assert result["output"]["summary"] == "Prepared Depop listing for Item at $32.0"
    assert result["output"]["draft_status"] == "fallback"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "browser_error"
    assert result["output"]["form_screenshot_url"] is None
    assert result["output"]["browser_use"] == {
        "mode": "fallback",
        "attempted_live_run": True,
        "profile_name": "depop",
        "profile_available": True,
        "error_category": "browser_error",
        "detail": "Used deterministic fallback listing metadata.",
    }


def test_sell_pipeline_uses_real_depop_listing_output(client: TestClient, monkeypatch) -> None:
    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        return {
            "listing_status": "ready_for_confirmation",
            "ready_for_confirmation": True,
            "draft_status": "ready",
            "form_screenshot_url": "artifact://sell-pipeline-preview",
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
            "metadata": {"source": "depop-listing-pipeline-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    result = wait_for_result_status(client, session_id, statuses={"paused"})
    assert result["status"] == "paused"
    listing = result["result"]["outputs"]["depop_listing"]
    assert listing["title"] == "Patagonia hoodie - Excellent Condition"
    assert listing["suggested_price"] == 78.43
    assert listing["category_path"] == "Men/Tops/Hoodies"
    assert listing["listing_status"] == "ready_for_confirmation"
    assert listing["ready_for_confirmation"] is True
    assert listing["draft_status"] == "ready"
    assert listing["execution_mode"] == "browser_use"
    assert listing["browser_use_error"] is None
    assert listing["form_screenshot_url"] == "artifact://sell-pipeline-preview"
    assert listing["browser_use"]["mode"] == "browser_use"


def test_depop_listing_agent_defaults_to_fallback_metadata_without_live_run() -> None:
    payload = {
        "session_id": "depop-listing-real-session",
        "pipeline": "sell",
        "step": "depop_listing",
        "input": {
            "original_input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "previous_outputs": build_sell_previous_outputs(),
        },
        "context": {"request_metadata": {"source": "depop-listing-real-test"}},
    }

    with TestClient(depop_listing_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["draft_status"] == "fallback"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "profile_missing"
    assert result["output"]["form_screenshot_url"] is None
    assert result["output"]["browser_use"]["mode"] == "skipped"


@pytest.mark.asyncio
async def test_depop_listing_agent_can_prepare_revision_submit_and_abort_checkpoints(monkeypatch) -> None:
    captured_tasks: list[str] = []
    queued_results = [
        {
            "listing_status": "ready_for_confirmation",
            "ready_for_confirmation": True,
            "draft_status": "ready",
            "form_screenshot_url": "artifact://revision-preview",
        },
        {
            "listing_status": "submitted",
            "ready_for_confirmation": False,
            "draft_status": None,
            "form_screenshot_url": "artifact://submit-confirmation",
        },
        {
            "listing_status": "aborted",
            "ready_for_confirmation": False,
            "draft_status": None,
            "form_screenshot_url": None,
        },
    ]

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        captured_tasks.append(str(kwargs["task"]))
        return queued_results.pop(0)

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(depop_listing_module.Path, "exists", lambda self: True)

    revision_result, revision_error, revision_profile = await depop_listing_module.agent.apply_browser_use_listing_revision(
        listing_output={
            "title": "Patagonia hoodie - Excellent Condition",
            "description": "Patagonia hoodie in excellent condition.",
            "suggested_price": 78.43,
            "category_path": "Men/Tops/Hoodies",
        },
        revision_instructions="Change the title to include size medium and lower the price by $5.",
    )
    submit_result, submit_error, submit_profile = await depop_listing_module.agent.submit_browser_use_listing()
    abort_result, abort_error, abort_profile = await depop_listing_module.agent.abort_browser_use_listing()

    assert revision_error is None
    assert revision_profile is True
    assert revision_result["listing_status"] == "ready_for_confirmation"
    assert revision_result["ready_for_confirmation"] is True
    assert "Change the title to include size medium" in captured_tasks[0]

    assert submit_error is None
    assert submit_profile is True
    assert submit_result["listing_status"] == "submitted"
    assert "perform the final publish or submit action" in captured_tasks[1]

    assert abort_error is None
    assert abort_profile is True
    assert abort_result["listing_status"] == "aborted"
    assert "discard, or otherwise abandon the draft" in captured_tasks[2]
