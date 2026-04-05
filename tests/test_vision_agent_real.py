from __future__ import annotations

import time

from fastapi.testclient import TestClient

from backend.agents.vision_agent import app as vision_app


def wait_for_terminal_result(client: TestClient, session_id: str, timeout: float = 3.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach a terminal state")


def test_vision_agent_infers_item_attributes_from_notes_and_image_url() -> None:
    payload = {
        "session_id": "vision-real-session",
        "pipeline": "sell",
        "step": "vision_analysis",
        "input": {
            "original_input": {
                "image_urls": ["https://cdn.example.com/uploads/nike-hoodie-nwt-front.jpg"],
                "notes": "Vintage Nike hoodie in excellent shape",
            },
            "previous_outputs": {},
        },
        "context": {"request_metadata": {"source": "vision-real-test"}},
    }

    with TestClient(vision_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["output"]["brand"] == "Nike"
    assert body["output"]["category"] == "apparel"
    assert body["output"]["detected_item"] == "hoodie"
    assert body["output"]["condition"] == "excellent"
    assert body["output"]["confidence"] == 0.88
    assert body["output"]["clean_photo_url"] == "https://cdn.example.com/uploads/nike-hoodie-nwt-front.jpg"
    assert body["output"]["search_query"] == "Nike hoodie"
    assert body["output"]["model"] is None
    assert "Nike hoodie" in body["output"]["summary"]


def test_vision_agent_falls_back_to_unknown_item_when_input_is_sparse() -> None:
    payload = {
        "session_id": "vision-fallback-session",
        "pipeline": "sell",
        "step": "vision_analysis",
        "input": {
            "original_input": {
                "image_urls": [],
                "notes": None,
            },
            "previous_outputs": {},
        },
        "context": {},
    }

    with TestClient(vision_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["output"]["brand"] == "Unknown"
    assert body["output"]["category"] == "unknown"
    assert body["output"]["detected_item"] == "item"
    assert body["output"]["condition"] == "good"
    assert body["output"]["confidence"] == 0.55
    assert body["output"]["clean_photo_url"] is None
    assert body["output"]["search_query"] is None


def test_sell_pipeline_uses_real_vision_agent_output(client: TestClient) -> None:
    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/inventory/carhartt-jacket-fair-wear.jpg"],
                "notes": "Carhartt work jacket with visible wear",
            },
            "metadata": {"source": "vision-pipeline-test"},
        },
    )
    assert response.status_code == 200
    result = wait_for_terminal_result(client, response.json()["session_id"])

    vision_output = result["result"]["outputs"]["vision_analysis"]
    assert vision_output["brand"] == "Carhartt"
    assert vision_output["category"] == "outerwear"
    assert vision_output["detected_item"] == "jacket"
    assert vision_output["condition"] == "fair"
