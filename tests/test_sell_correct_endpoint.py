from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.session import session_manager
from backend.schemas import PipelineStartRequest

client = TestClient(app)


@pytest.mark.asyncio
async def test_sell_correct_endpoint_resumes_pipeline() -> None:
    # 1. Start a sell pipeline
    start_resp = client.post(
        "/sell/start",
        json={"input": {"image_urls": [], "notes": "Test"}},
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]
    
    # Verify session is queued or running
    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.pipeline == "sell"

    # 2. Call /sell/correct
    corrected_item = {
        "brand": "Nike",
        "item_name": "Hoodie",
        "model": "Promo",
        "condition": "good",
        "search_query": "Nike Hoodie Promo"
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
    
    # 3. Verify that the context gets updated via resume_sell_pipeline
    # Wait briefly for the asyncio.create_task to run and update state
    import asyncio
    await asyncio.sleep(0.1)
    
    session_updated = await session_manager.get_session(session_id)
    assert session_updated.result.get("outputs", {}).get("vision_analysis") == corrected_item


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
