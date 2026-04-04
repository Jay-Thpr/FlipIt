from __future__ import annotations

import time
from typing import Any

import backend.agents.ebay_sold_comps_agent as ebay_sold_comps_module
from fastapi.testclient import TestClient

from backend.agents.ebay_sold_comps_agent import app as ebay_sold_comps_app


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


def test_ebay_sold_comps_agent_prices_brand_item_and_condition() -> None:
    payload = {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "ebay_sold_comps",
        "input": {
            "original_input": {
                "image_urls": ["https://images.example.com/carhartt-jacket.jpg"],
                "notes": "Carhartt work jacket with visible wear",
            },
            "previous_outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Inferred Carhartt jacket in fair condition",
                    "detected_item": "jacket",
                    "brand": "Carhartt",
                    "category": "outerwear",
                    "condition": "fair",
                }
            },
        },
        "context": {
            "request_metadata": {"source": "contract-test"},
            "pipeline_input": {"image_urls": ["https://images.example.com/carhartt-jacket.jpg"]},
            "vision_analysis": {
                "agent": "vision_agent",
                "display_name": "Vision Agent",
                "summary": "Inferred Carhartt jacket in fair condition",
                "detected_item": "jacket",
                "brand": "Carhartt",
                "category": "outerwear",
                "condition": "fair",
            },
        },
    }

    with TestClient(ebay_sold_comps_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["median_sold_price"] == 72.03
    assert result["output"]["low_sold_price"] == 50.42
    assert result["output"]["high_sold_price"] == 93.64
    assert result["output"]["sample_size"] == 10
    assert result["output"]["summary"] == "Estimated 10 sold eBay comps for Carhartt jacket"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "runtime_unavailable"


def test_ebay_sold_comps_agent_uses_unknown_brand_fallback() -> None:
    payload = {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "ebay_sold_comps",
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
                }
            },
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {}},
    }

    with TestClient(ebay_sold_comps_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["median_sold_price"] == 32.0
    assert result["output"]["low_sold_price"] == 22.4
    assert result["output"]["high_sold_price"] == 41.6
    assert result["output"]["sample_size"] == 16
    assert result["output"]["summary"] == "Estimated 16 sold eBay comps for item"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "runtime_unavailable"


def test_ebay_sold_comps_agent_records_live_execution_metadata(monkeypatch) -> None:
    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        return {
            "median_sold_price": 64.0,
            "low_sold_price": 58.0,
            "high_sold_price": 71.0,
            "sample_size": 7,
        }

    monkeypatch.setattr(ebay_sold_comps_module, "run_structured_browser_task", fake_run_structured_browser_task)

    payload = {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "ebay_sold_comps",
        "input": {
            "original_input": {"image_urls": [], "notes": None},
            "previous_outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Inferred Patagonia hoodie in excellent condition",
                    "detected_item": "hoodie",
                    "brand": "Patagonia",
                    "category": "outerwear",
                    "condition": "excellent",
                }
            },
        },
        "context": {"request_metadata": {"source": "browser-use-live-test"}, "pipeline_input": {}},
    }

    with TestClient(ebay_sold_comps_app) as client:
        response = client.post("/task", json=payload)

    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Extracted 7 sold eBay comps for Patagonia hoodie with Browser Use"
    assert result["output"]["execution_mode"] == "browser_use"
    assert result["output"]["browser_use_error"] is None


def test_ebay_sold_comps_agent_reports_browser_use_fallback_error(monkeypatch) -> None:
    async def broken_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("sold page changed")

    monkeypatch.setattr(ebay_sold_comps_module, "run_structured_browser_task", broken_run_structured_browser_task)

    payload = {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "ebay_sold_comps",
        "input": {
            "original_input": {"image_urls": [], "notes": None},
            "previous_outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Inferred Patagonia hoodie in excellent condition",
                    "detected_item": "hoodie",
                    "brand": "Patagonia",
                    "category": "outerwear",
                    "condition": "excellent",
                }
            },
        },
        "context": {"request_metadata": {"source": "browser-use-fallback-test"}, "pipeline_input": {}},
    }

    with TestClient(ebay_sold_comps_app) as client:
        response = client.post("/task", json=payload)

    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "unknown"


def test_sell_pipeline_uses_real_ebay_sold_comps_output(client: TestClient) -> None:
    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    result = wait_for_terminal_result(client, session_id)
    assert result["status"] == "completed"
    sold_comps = result["result"]["outputs"]["ebay_sold_comps"]
    assert sold_comps["median_sold_price"] == 70.66
    assert sold_comps["low_sold_price"] == 55.11
    assert sold_comps["high_sold_price"] == 86.21
    assert sold_comps["sample_size"] == 11
    assert sold_comps["summary"] == "Estimated 11 sold eBay comps for Patagonia hoodie"
    assert sold_comps["execution_mode"] == "fallback"
    assert sold_comps["browser_use_error"] == "runtime_unavailable"
