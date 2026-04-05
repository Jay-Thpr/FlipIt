from __future__ import annotations

from typing import Any

import pytest

from backend import orchestrator
from backend.schemas import AgentTaskResponse, PipelineStartRequest, SellListingReviewState, SessionState
from backend.sell_writeback import (
    SellWritebackManager,
    build_sell_item_projection,
    build_sell_market_data_snapshot,
)
from backend.session import session_manager

ITEM_ID = "22222222-2222-2222-2222-222222222222"
USER_ID = "11111111-1111-1111-1111-111111111111"


def _sell_outputs(*, ready_for_confirmation: bool = True, listing_status: str = "ready_for_confirmation") -> dict[str, dict[str, Any]]:
    return {
        "vision_analysis": {
            "agent": "vision_agent",
            "display_name": "Vision Agent",
            "summary": "Detected a Nike hoodie in good condition",
            "detected_item": "Hoodie",
            "brand": "Nike",
            "category": "Men/Tops/Hoodies",
            "condition": "good",
            "confidence": 0.95,
        },
        "ebay_sold_comps": {
            "agent": "ebay_sold_comps_agent",
            "display_name": "eBay Sold Comps Agent",
            "summary": "11 sold comps found",
            "median_sold_price": 58.0,
            "low_sold_price": 42.0,
            "high_sold_price": 79.0,
            "sample_size": 11,
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        },
        "pricing": {
            "agent": "pricing_agent",
            "display_name": "Pricing Agent",
            "summary": "Recommended a competitive sell price",
            "recommended_list_price": 72.0,
            "expected_profit": 61.0,
            "pricing_confidence": 0.84,
            "median_sold_price": 58.0,
            "trend": None,
            "velocity": None,
        },
        "depop_listing": {
            "agent": "depop_listing_agent",
            "display_name": "Depop Listing Agent",
            "summary": "Prepared a Depop listing draft",
            "title": "Nike hoodie - Good Condition",
            "description": "Good prefilled draft",
            "suggested_price": 72.0,
            "category_path": "Men/Tops/Hoodies",
            "listing_status": listing_status,
            "ready_for_confirmation": ready_for_confirmation,
            "draft_status": "browser_use",
            "draft_url": None,
            "form_screenshot_url": "artifact://preview",
            "listing_preview": {
                "title": "Nike hoodie - Good Condition",
                "price": 72.0,
                "description": "Good prefilled draft",
                "condition": "good",
                "clean_photo_url": None,
            },
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        },
    }


def _sell_request() -> PipelineStartRequest:
    return PipelineStartRequest(
        user_id=USER_ID,
        input={"image_urls": ["https://example.com/item.jpg"], "notes": "Nike hoodie"},
        metadata={"item_id": ITEM_ID, "user_id": USER_ID},
    )


def _sell_session(*, status: str = "paused", outputs: dict[str, dict[str, Any]] | None = None) -> SessionState:
    session = SessionState(session_id="sell-run-1", pipeline="sell", request=_sell_request(), status=status)
    session.result = {"pipeline": "sell", "outputs": outputs or _sell_outputs()}
    return session


def test_build_sell_item_projection_prefers_listing_fields() -> None:
    updates = build_sell_item_projection(_sell_outputs())
    assert updates == {
        "name": "Nike hoodie - Good Condition",
        "description": "Good prefilled draft",
        "target_price": 72.0,
        "condition": "Good",
        "min_price": 42.0,
        "max_price": 79.0,
        "listing_screenshot_url": "artifact://preview",
        "listing_preview_payload": {
            "title": "Nike hoodie - Good Condition",
            "price": 72.0,
            "description": "Good prefilled draft",
            "condition": "good",
            "clean_photo_url": None,
        },
    }


def test_build_sell_market_data_snapshot_uses_comps_and_pricing() -> None:
    snapshot = build_sell_market_data_snapshot(_sell_outputs())
    assert snapshot == {
        "platform": "ebay",
        "best_buy_price": 58.0,
        "best_sell_price": 72.0,
        "volume": 11,
    }


@pytest.mark.asyncio
async def test_sell_writeback_manager_persists_item_projection_and_market_snapshot() -> None:
    item_calls: list[dict[str, Any]] = []
    market_calls: list[dict[str, Any]] = []

    class FakeItemRepository:
        def __init__(self, _client: Any) -> None:
            pass

        def update_item_projection(self, *, item_id: str, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
            item_calls.append({"item_id": item_id, "user_id": user_id, "updates": updates})
            return {"id": item_id, "user_id": user_id, **updates}

    class FakeMarketRepository:
        def __init__(self, _client: Any) -> None:
            pass

        def upsert_market_snapshot(self, *, item_id: str, platform: str, snapshot: dict[str, Any]) -> dict[str, Any]:
            market_calls.append({"item_id": item_id, "platform": platform, "snapshot": snapshot})
            return {"item_id": item_id, "platform": platform, **snapshot}

    manager = SellWritebackManager(
        enabled=True,
        client_factory=lambda: object(),
        item_repository_factory=FakeItemRepository,
        market_data_repository_factory=FakeMarketRepository,
    )

    await manager.persist_session(_sell_session())

    assert item_calls == [
        {
            "item_id": ITEM_ID,
            "user_id": USER_ID,
            "updates": {
                "name": "Nike hoodie - Good Condition",
                "description": "Good prefilled draft",
                "target_price": 72.0,
                "condition": "Good",
                "min_price": 42.0,
                "max_price": 79.0,
                "listing_screenshot_url": "artifact://preview",
                "listing_preview_payload": {
                    "title": "Nike hoodie - Good Condition",
                    "price": 72.0,
                    "description": "Good prefilled draft",
                    "condition": "good",
                    "clean_photo_url": None,
                },
            },
        }
    ]
    assert market_calls == [
        {
            "item_id": ITEM_ID,
            "platform": "ebay",
            "snapshot": {
                "best_buy_price": 58.0,
                "best_sell_price": 72.0,
                "volume": 11,
            },
        }
    ]


@pytest.mark.asyncio
async def test_sell_writeback_manager_skips_when_item_context_missing() -> None:
    item_calls: list[dict[str, Any]] = []

    class FakeItemRepository:
        def __init__(self, _client: Any) -> None:
            pass

        def update_item_projection(self, *, item_id: str, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
            item_calls.append({"item_id": item_id, "user_id": user_id, "updates": updates})
            return {}

    manager = SellWritebackManager(
        enabled=True,
        client_factory=lambda: object(),
        item_repository_factory=FakeItemRepository,
    )

    session = _sell_session()
    session.request.metadata = {}

    await manager.persist_session(session)

    assert item_calls == []


@pytest.mark.asyncio
async def test_run_pipeline_persists_sell_projection_when_listing_review_pauses(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()

    outputs_by_agent = {
        "vision_agent": _sell_outputs()["vision_analysis"],
        "ebay_sold_comps_agent": _sell_outputs()["ebay_sold_comps"],
        "pricing_agent": _sell_outputs()["pricing"],
        "depop_listing_agent": _sell_outputs(ready_for_confirmation=True)["depop_listing"],
    }
    persisted_sessions: list[SessionState] = []

    async def fake_run_agent_task(agent_slug: str, request: Any) -> AgentTaskResponse:
        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="completed",
            output=outputs_by_agent[agent_slug],
        )

    async def fake_persist(session: SessionState) -> None:
        persisted_sessions.append(session.model_copy(deep=True))

    monkeypatch.setattr(orchestrator, "run_agent_task", fake_run_agent_task)
    monkeypatch.setattr("backend.sell_writeback.persist_sell_session_projection", fake_persist)

    request = _sell_request()
    session_id = "sell-review-pause-session"
    await session_manager.create_session(session_id=session_id, pipeline="sell", request=request)

    await orchestrator.run_pipeline(session_id, "sell", request)

    assert any(
        session.status == "paused"
        and session.result["outputs"]["depop_listing"]["ready_for_confirmation"] is True
        and session.request.metadata["item_id"] == ITEM_ID
        for session in persisted_sessions
    )


@pytest.mark.asyncio
async def test_handle_sell_listing_decision_confirm_persists_submitted_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    await session_manager.reset()

    session = await session_manager.create_session(
        session_id="sell-review-confirm-session",
        pipeline="sell",
        request=_sell_request(),
    )
    session.status = "paused"
    session.result = {"pipeline": "sell", "outputs": _sell_outputs()}
    session.sell_listing_review = SellListingReviewState(state="ready_for_confirmation")

    persisted_sessions: list[SessionState] = []

    async def fake_submit_sell_listing() -> tuple[dict[str, Any], None, bool]:
        return (
            {
                "listing_status": "submitted",
                "ready_for_confirmation": False,
                "draft_status": "submitted",
                "form_screenshot_url": "artifact://submitted",
            },
            None,
            True,
        )

    async def fake_persist(session: SessionState) -> None:
        persisted_sessions.append(session.model_copy(deep=True))

    monkeypatch.setattr(orchestrator, "submit_sell_listing", fake_submit_sell_listing)
    monkeypatch.setattr("backend.sell_writeback.persist_sell_session_projection", fake_persist)

    await orchestrator.handle_sell_listing_decision(session.session_id, "confirm_submit")

    assert any(
        snapshot.status == "completed"
        and snapshot.result["outputs"]["depop_listing"]["listing_status"] == "submitted"
        and snapshot.request.metadata["item_id"] == ITEM_ID
        for snapshot in persisted_sessions
    )


# ---------------------------------------------------------------------------
# Sell review artifact persistence tests
# ---------------------------------------------------------------------------


def _sell_outputs_with_artifacts() -> dict:
    outputs = _sell_outputs()
    outputs["depop_listing"]["draft_url"] = "https://depop.com/drafts/abc123"
    outputs["depop_listing"]["form_screenshot_url"] = "https://storage.example.com/screenshots/xyz.png"
    outputs["depop_listing"]["listing_preview"] = {
        "title": "Nike hoodie - Good Condition",
        "price": 72.0,
        "description": "Good prefilled draft",
        "condition": "Good",
        "category": "Men/Tops/Hoodies",
    }
    return outputs


def test_build_sell_item_projection_includes_draft_url() -> None:
    updates = build_sell_item_projection(_sell_outputs_with_artifacts())
    assert updates.get("draft_url") == "https://depop.com/drafts/abc123"


def test_build_sell_item_projection_includes_listing_screenshot_url() -> None:
    updates = build_sell_item_projection(_sell_outputs_with_artifacts())
    assert updates.get("listing_screenshot_url") == "https://storage.example.com/screenshots/xyz.png"


def test_build_sell_item_projection_includes_listing_preview_payload() -> None:
    updates = build_sell_item_projection(_sell_outputs_with_artifacts())
    assert updates.get("listing_preview_payload") == {
        "title": "Nike hoodie - Good Condition",
        "price": 72.0,
        "description": "Good prefilled draft",
        "condition": "Good",
        "category": "Men/Tops/Hoodies",
    }


def test_build_sell_item_projection_skips_none_artifacts() -> None:
    outputs = _sell_outputs()
    outputs["depop_listing"]["draft_url"] = None
    outputs["depop_listing"]["form_screenshot_url"] = None
    outputs["depop_listing"]["listing_preview"] = None
    updates = build_sell_item_projection(outputs)
    assert "draft_url" not in updates
    assert "listing_screenshot_url" not in updates
    assert "listing_preview_payload" not in updates
