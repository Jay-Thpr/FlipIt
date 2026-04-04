from __future__ import annotations

import base64
import time

import pytest
from fastapi.testclient import TestClient

import backend.agents.vision_agent as vision_module
from backend.agents.vision_agent import agent as vision_agent
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


def wait_for_status(client: TestClient, session_id: str, statuses: set[str], timeout: float = 3.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in statuses:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach any of {sorted(statuses)}")


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


def test_vision_agent_accepts_inline_base64_and_enriches_output(monkeypatch: pytest.MonkeyPatch) -> None:
    sample_image = base64.b64encode(b"fake-image-bytes").decode()

    async def fake_identify_item(original_input, image_payload):
        assert original_input.image_base64 == sample_image
        assert image_payload == {"mime_type": "image/jpeg", "data": sample_image}
        return {
            "brand": "Sony",
            "detected_item": "headphones",
            "category": "accessories",
            "condition": "good",
            "item_name": "Sony WH-1000XM5",
            "model": "WH-1000XM5",
            "condition_notes": "Light wear on ear cups",
            "confidence": 0.94,
            "color": "Black",
            "size_visible": None,
            "search_query": "Sony WH-1000XM5 headphones",
            "clean_photo_url": None,
            "analysis_source": "gemini",
        }

    async def fake_generate_clean_photo(image_payload):
        assert image_payload["data"] == sample_image
        return "https://cdn.example.com/clean-photo.jpg"

    monkeypatch.setattr(vision_agent, "identify_item", fake_identify_item)
    monkeypatch.setattr(vision_agent, "generate_clean_photo", fake_generate_clean_photo)

    payload = {
        "session_id": "vision-inline-image-session",
        "pipeline": "sell",
        "step": "vision_analysis",
        "input": {
            "original_input": {
                "image_base64": sample_image,
                "image_mime_type": "image/jpeg",
                "notes": "Noise-canceling headphones",
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
    assert body["output"]["item_name"] == "Sony WH-1000XM5"
    assert body["output"]["clean_photo_url"] == "https://cdn.example.com/clean-photo.jpg"
    assert body["output"]["search_query"] == "Sony WH-1000XM5 headphones"


def test_sell_pipeline_pauses_on_low_confidence_and_resumes_after_correction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample_image = base64.b64encode(b"vision-low-confidence").decode()

    async def fake_identify_item(original_input, image_payload):
        assert image_payload is not None
        return {
            "brand": "Nike",
            "detected_item": "sneakers",
            "category": "footwear",
            "condition": "good",
            "item_name": "Nike sneakers",
            "model": "Unknown",
            "condition_notes": "Photo is blurry",
            "confidence": 0.42,
            "color": None,
            "size_visible": None,
            "search_query": "Nike sneakers",
            "clean_photo_url": None,
            "analysis_source": "gemini",
        }

    async def fake_generate_clean_photo(image_payload):
        return "https://cdn.example.com/resume-clean-photo.jpg"

    monkeypatch.setattr(vision_agent, "identify_item", fake_identify_item)
    monkeypatch.setattr(vision_agent, "generate_clean_photo", fake_generate_clean_photo)

    start_response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {
                "image_base64": sample_image,
                "image_mime_type": "image/jpeg",
                "notes": "Jordan pickup",
            },
            "metadata": {"source": "vision-correction-test"},
        },
    )
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    awaiting_result = wait_for_status(client, session_id, {"awaiting_input"})
    assert awaiting_result["result"]["pending"]["step"] == "vision_analysis"
    assert awaiting_result["result"]["pending"]["suggestion"]["confidence"] == 0.42
    assert awaiting_result["events"][-1]["event_type"] == "vision_low_confidence"

    correction_response = client.post(
        "/sell/correct",
        json={
            "session_id": session_id,
            "corrected_item": {
                "brand": "Nike",
                "item_name": "Air Jordan 1 Retro High OG",
                "model": "Air Jordan 1",
                "detected_item": "sneakers",
                "category": "footwear",
                "condition": "good",
                "condition_notes": "Minor creasing on toe box",
                "search_query": "Nike Air Jordan 1 Retro High OG",
            },
        },
    )
    assert correction_response.status_code == 200
    assert correction_response.json() == {"ok": True}

    result = wait_for_terminal_result(client, session_id)
    assert result["status"] == "completed"
    vision_output = result["result"]["outputs"]["vision_analysis"]
    assert vision_output["item_name"] == "Air Jordan 1 Retro High OG"
    assert vision_output["detected_item"] == "sneakers"
    assert vision_output["clean_photo_url"] == "https://cdn.example.com/resume-clean-photo.jpg"
    assert result["events"][-1]["event_type"] == "pipeline_complete"


@pytest.mark.asyncio
async def test_generate_clean_photo_can_force_nano_banana(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    async def fake_gemini_clean_photo(image_payload):
        called.append("gemini")
        return "gemini-result"

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"clean_photo_url": "mock-nano-result"}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            called.append("nano")
            assert url == "http://127.0.0.1:8010/clean"
            assert headers == {"Authorization": "Bearer test-nano-key"}
            assert json == {"image": "ZmFrZQ==", "mime_type": "image/jpeg"}
            return FakeResponse()

    monkeypatch.setattr(vision_agent, "_generate_clean_photo_with_gemini", fake_gemini_clean_photo)
    monkeypatch.setattr(vision_module, "get_clean_photo_provider", lambda: "nano_banana")
    monkeypatch.setattr(vision_module, "get_nano_banana_api_url", lambda: "http://127.0.0.1:8010/clean")
    monkeypatch.setattr(vision_module, "get_nano_banana_api_key", lambda: "test-nano-key")
    monkeypatch.setattr(vision_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await vision_agent.generate_clean_photo({"mime_type": "image/jpeg", "data": "ZmFrZQ=="})

    assert result == "mock-nano-result"
    assert called == ["nano"]
