from __future__ import annotations

import time
from typing import Any

import backend.agents.depop_listing_agent as depop_listing_module
from fastapi.testclient import TestClient

from backend.agents.depop_listing_agent import app as depop_listing_app


def wait_for_terminal_result(client: TestClient, session_id: str, timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach a terminal state")


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


def test_depop_listing_agent_records_browser_use_confirmation(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
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
    assert result["output"]["draft_status"] == "ready"
    assert result["output"]["execution_mode"] == "browser_use"
    assert result["output"]["browser_use_error"] is None
    assert result["output"]["form_screenshot_url"] == "artifact://depop-form-preview"


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


def test_sell_pipeline_uses_real_depop_listing_output(client: TestClient, monkeypatch) -> None:
    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        return {
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

    result = wait_for_terminal_result(client, session_id)
    listing = result["result"]["outputs"]["depop_listing"]
    assert listing["title"] == "Patagonia hoodie - Excellent Condition"
    assert listing["suggested_price"] == 78.43
    assert listing["category_path"] == "Men/Tops/Hoodies"
    assert listing["draft_status"] == "ready"
    assert listing["execution_mode"] == "browser_use"
    assert listing["browser_use_error"] is None
    assert listing["form_screenshot_url"] == "artifact://sell-pipeline-preview"


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
