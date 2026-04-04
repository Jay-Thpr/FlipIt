from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from backend.agents.pricing_agent import app as pricing_app


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


def test_pricing_agent_prices_from_real_comps_and_item_signals() -> None:
    payload = {
        "session_id": "pricing-real-session",
        "pipeline": "sell",
        "step": "pricing",
        "input": {
            "original_input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "previous_outputs": {
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
            },
        },
        "context": {"request_metadata": {"source": "pricing-real-test"}},
    }

    with TestClient(pricing_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["recommended_list_price"] == 78.43
    assert result["output"]["expected_profit"] == 41.38
    assert result["output"]["pricing_confidence"] == 0.91
    assert result["output"]["summary"] == "Priced Patagonia hoodie at $78.43 with estimated profit $41.38"


def test_pricing_agent_falls_back_for_unknown_item_signals() -> None:
    payload = {
        "session_id": "pricing-fallback-session",
        "pipeline": "sell",
        "step": "pricing",
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
            },
        },
        "context": {},
    }

    with TestClient(pricing_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["recommended_list_price"] == 32.0
    assert result["output"]["expected_profit"] == 15.68
    assert result["output"]["pricing_confidence"] == 0.82
    assert result["output"]["summary"] == "Priced item at $32.0 with estimated profit $15.68"


def test_sell_pipeline_uses_real_pricing_output(client: TestClient) -> None:
    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "pricing-pipeline-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    result = wait_for_terminal_result(client, session_id)
    assert result["status"] == "completed"
    pricing = result["result"]["outputs"]["pricing"]
    assert pricing["recommended_list_price"] == 78.43
    assert pricing["expected_profit"] == 41.38
    assert pricing["pricing_confidence"] == 0.91
