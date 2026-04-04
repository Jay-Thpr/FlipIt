from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.session import session_manager
from backend.schemas import PipelineStartRequest

client = TestClient(app)


@pytest.mark.asyncio
async def test_sell_correct_endpoint_resumes_pipeline() -> None:
    session_id = "awaiting-input-sell-correct"
    await session_manager.create_session(
        session_id=session_id,
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )
    await session_manager.update_status(
        session_id,
        status="awaiting_input",
        result={
            "pipeline": "sell",
            "outputs": {},
            "pending": {
                "step": "vision_analysis",
                "suggestion": {
                    "brand": "Unknown",
                    "item_name": "Item",
                    "detected_item": "item",
                    "category": "unknown",
                    "condition": "good",
                    "confidence": 0.42,
                },
                "message": "Not sure.",
            },
        },
    )

    corrected_item = {
        "brand": "Nike",
        "item_name": "Hoodie",
        "detected_item": "hoodie",
        "category": "apparel",
        "model": "Promo",
        "condition": "good",
        "search_query": "Nike Hoodie Promo",
    }

    correct_resp = client.post(
        "/sell/correct",
        json={
            "session_id": session_id,
            "corrected_item": corrected_item,
        }
    )
    assert correct_resp.status_code == 200
    assert correct_resp.json() == {"ok": True}

    import asyncio

    await asyncio.sleep(0.1)
    session_updated = await session_manager.get_session(session_id)
    assert session_updated is not None
    assert session_updated.result.get("outputs", {}).get("vision_analysis", {}).get("brand") == "Nike"


@pytest.mark.asyncio
async def test_sell_correct_endpoint_rejects_unknown_session() -> None:
    correct_resp = client.post(
        "/sell/correct",
        json={
            "session_id": "nonexistent-session",
            "corrected_item": {"brand": "Nike"}
        }
    )
    assert correct_resp.status_code == 404
    assert correct_resp.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_sell_correct_endpoint_rejects_session_not_waiting_for_input() -> None:
    session_id = "running-sell-correct"
    await session_manager.create_session(
        session_id=session_id,
        pipeline="sell",
        request=PipelineStartRequest(input={"image_urls": [], "notes": "Test"}),
    )

    correct_resp = client.post(
        "/sell/correct",
        json={
            "session_id": session_id,
            "corrected_item": {"brand": "Nike"},
        },
    )

    assert correct_resp.status_code == 409
    assert correct_resp.json()["detail"] == "Sell session is not waiting for correction"
