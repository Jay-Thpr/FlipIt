from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.session import session_manager

client = TestClient(app)


@pytest.mark.asyncio
async def test_sell_correct_endpoint_resumes_pipeline() -> None:
    start_resp = client.post(
        "/sell/start",
        json={"input": {"image_urls": [], "notes": "Test"}},
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.pipeline == "sell"

    for _ in range(100):
        session = await session_manager.get_session(session_id)
        assert session is not None
        if session.result and "vision_analysis" in session.result.get("outputs", {}):
            break
        await asyncio.sleep(0.05)
    else:
        raise AssertionError("vision_analysis never landed in session result")

    corrected_item = {
        "brand": "Nike",
        "item_name": "Hoodie",
        "model": "Promo",
        "condition": "good",
        "search_query": "Nike Hoodie Promo",
    }

    correct_resp = client.post(
        "/sell/correct",
        json={
            "session_id": session_id,
            "corrected_item": corrected_item,
        },
    )
    assert correct_resp.status_code == 200
    assert correct_resp.json() == {"ok": True}

    deadline = time.time() + 10.0
    while time.time() < deadline:
        session_updated = await session_manager.get_session(session_id)
        assert session_updated is not None
        if session_updated.status == "completed":
            va = session_updated.result.get("outputs", {}).get("vision_analysis")
            assert va is not None
            assert va["brand"] == "Nike"
            assert va["detected_item"] == "Hoodie"
            assert va["confidence"] == 1.0
            assert "ebay_sold_comps" in session_updated.result.get("outputs", {})
            return
        if session_updated.status == "failed":
            raise AssertionError(session_updated.error)
        await asyncio.sleep(0.05)
    raise AssertionError("sell pipeline did not complete after correction")


@pytest.mark.asyncio
async def test_sell_correct_endpoint_rejects_unknown_session() -> None:
    correct_resp = client.post(
        "/sell/correct",
        json={
            "session_id": "nonexistent-session",
            "corrected_item": {"brand": "Nike"},
        },
    )
    assert correct_resp.status_code == 404
    assert correct_resp.json()["detail"] == "Session not found"
