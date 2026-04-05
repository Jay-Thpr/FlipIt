from __future__ import annotations

from typing import Any

import pytest

from backend.run_persistence import RunPersistenceManager
from backend.schemas import PipelineStartRequest, SessionEvent, SessionState, SellListingReviewState
from backend.session import session_manager


class FakeRunStore:
    def __init__(self) -> None:
        self.created_rows: list[dict[str, Any]] = []
        self.updated_rows: list[tuple[str, dict[str, Any]]] = []
        self.event_rows: list[dict[str, Any]] = []

    async def create_run(self, row: dict) -> None:
        self.created_rows.append(dict(row))

    async def update_run_by_session_id(self, session_id: str, updates: dict) -> None:
        self.updated_rows.append((session_id, dict(updates)))

    async def append_event(self, row: dict) -> None:
        self.event_rows.append(dict(row))


class FakePersistenceManager:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.updated: list[str] = []
        self.events: list[tuple[str, str]] = []

    async def persist_session_created(self, session: SessionState) -> None:
        self.created.append(session.session_id)

    async def persist_session_updated(self, session: SessionState) -> None:
        self.updated.append(session.session_id)

    async def persist_event(self, session: SessionState, event: SessionEvent) -> None:
        self.events.append((session.session_id, event.event_type))


def _sell_session(*, session_id: str = "session-1", user_id: str = "11111111-1111-1111-1111-111111111111") -> SessionState:
    return SessionState(
        session_id=session_id,
        pipeline="sell",
        status="paused",
        request=PipelineStartRequest(
            user_id=user_id,
            input={"image_urls": ["https://example.com/item.jpg"], "notes": "Vintage hoodie"},
            metadata={"item_id": "22222222-2222-2222-2222-222222222222"},
        ),
        sell_listing_review=SellListingReviewState(
            state="ready_for_confirmation",
            revision_count=1,
            revision_instructions="Shorten the title",
            paused_at="2026-04-05T10:00:00+00:00",
            deadline_at="2026-04-05T10:15:00+00:00",
        ),
        result={
            "pipeline": "sell",
            "outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Identified item",
                    "detected_item": "hoodie",
                    "brand": "Nike",
                    "category": "tops",
                    "condition": "good",
                    "confidence": 0.95,
                },
                "pricing": {
                    "agent": "pricing_agent",
                    "display_name": "Pricing Agent",
                    "summary": "Priced item",
                    "recommended_list_price": 72.0,
                    "expected_profit": 30.0,
                    "pricing_confidence": 0.8,
                },
                "depop_listing": {
                    "agent": "depop_listing_agent",
                    "display_name": "Depop Listing Agent",
                    "summary": "Ready for confirmation",
                    "title": "Vintage Nike hoodie",
                    "description": "Good condition",
                    "suggested_price": 72.0,
                    "category_path": "Men/Tops/Hoodies",
                    "listing_status": "ready_for_confirmation",
                    "ready_for_confirmation": True,
                    "execution_mode": "browser_use",
                },
            },
        },
    )


@pytest.mark.asyncio
async def test_run_persistence_manager_creates_normalized_run_row() -> None:
    store = FakeRunStore()
    manager = RunPersistenceManager(store=store)

    await manager.persist_session_created(_sell_session())

    assert len(store.created_rows) == 1
    row = store.created_rows[0]
    assert row["session_id"] == "session-1"
    assert row["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert row["item_id"] == "22222222-2222-2222-2222-222222222222"
    assert row["phase"] == "awaiting_listing_review"
    assert row["next_action_type"] == "review_listing"
    assert row["result_payload"]["sell_summary"]["listing_title"] == "Vintage Nike hoodie"


@pytest.mark.asyncio
async def test_run_persistence_manager_skips_invalid_user_ids() -> None:
    store = FakeRunStore()
    manager = RunPersistenceManager(store=store)

    await manager.persist_session_created(_sell_session(user_id="demo-user"))

    assert store.created_rows == []


@pytest.mark.asyncio
async def test_run_persistence_manager_updates_terminal_run_state() -> None:
    store = FakeRunStore()
    manager = RunPersistenceManager(store=store)
    session = _sell_session()

    await manager.persist_session_created(session)
    session.status = "completed"
    session.sell_listing_review = None
    session.updated_at = "2026-04-05T11:00:00+00:00"

    await manager.persist_session_updated(session)

    assert len(store.updated_rows) == 1
    session_id, updates = store.updated_rows[0]
    assert session_id == "session-1"
    assert updates["status"] == "completed"
    assert updates["phase"] == "completed"
    assert updates["next_action_type"] == "show_result"
    assert updates["completed_at"] == "2026-04-05T11:00:00+00:00"


@pytest.mark.asyncio
async def test_run_persistence_manager_appends_event_with_persisted_run_id() -> None:
    store = FakeRunStore()
    manager = RunPersistenceManager(store=store)
    session = _sell_session()
    event = SessionEvent(
        session_id=session.session_id,
        event_type="listing_review_required",
        pipeline="sell",
        step="depop_listing",
        data={"ready": True},
    )

    await manager.persist_session_created(session)
    await manager.persist_event(session, event)

    assert len(store.event_rows) == 1
    row = store.event_rows[0]
    assert row["session_id"] == session.session_id
    assert row["event_type"] == "listing_review_required"
    assert row["step"] == "depop_listing"
    assert row["payload"] == {"ready": True}
    assert row["run_id"]


@pytest.mark.asyncio
async def test_session_manager_calls_persistence_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakePersistenceManager()
    monkeypatch.setattr("backend.run_persistence.get_run_persistence_manager", lambda: fake)

    session = await session_manager.create_session(
        session_id="session-hook",
        pipeline="buy",
        request=PipelineStartRequest(
            user_id="11111111-1111-1111-1111-111111111111",
            input={"query": "vintage tee"},
            metadata={"item_id": "33333333-3333-3333-3333-333333333333"},
        ),
    )
    await session_manager.update_status(session.session_id, status="running", result={"pipeline": "buy", "outputs": {}})
    await session_manager.append_event(
        SessionEvent(
            session_id=session.session_id,
            event_type="agent_started",
            pipeline="buy",
            step="depop_search",
            data={"attempt": 1},
        )
    )

    assert fake.created == ["session-hook"]
    assert fake.updated == ["session-hook"]
    assert fake.events == [("session-hook", "agent_started")]
