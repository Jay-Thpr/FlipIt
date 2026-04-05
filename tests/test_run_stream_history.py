from __future__ import annotations

import asyncio
import threading
import time
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.auth import AuthenticatedUser, get_current_user
from backend.main import app
from backend.schemas import PipelineStartRequest, SessionEvent
from backend.session import session_manager


FAKE_USER = AuthenticatedUser(
    user_id="11111111-1111-1111-1111-111111111111",
    email="user@example.com",
    role="authenticated",
    raw_claims={},
)


@contextmanager
def _authed_app():
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _persisted_run() -> dict:
    return {
        "id": "db-run-1",
        "session_id": "run-1",
        "user_id": FAKE_USER.user_id,
        "item_id": "22222222-2222-2222-2222-222222222222",
        "pipeline": "sell",
        "status": "completed",
        "phase": "completed",
        "result_payload": {
            "session_id": "run-1",
            "run_id": "run-1",
            "pipeline": "sell",
            "status": "completed",
            "phase": "completed",
            "next_action": {"type": "show_result", "payload": {}},
        },
        "created_at": "2026-04-05T09:00:00+00:00",
        "updated_at": "2026-04-05T10:00:00+00:00",
    }


def test_stream_run_replays_persisted_history_without_live_session(client: TestClient) -> None:
    persisted_events = [
        SessionEvent(
            session_id="run-1",
            event_type="agent_started",
            pipeline="sell",
            step="vision_analysis",
            data={"message": "started"},
            timestamp="2026-04-05T09:00:00+00:00",
        ),
        SessionEvent(
            session_id="run-1",
            event_type="pipeline_complete",
            pipeline="sell",
            data={"outputs": {}},
            timestamp="2026-04-05T09:01:00+00:00",
        ),
    ]

    with _authed_app():
        with patch("backend.main.get_persisted_run_record", new=AsyncMock(return_value=_persisted_run())), patch(
            "backend.main.list_persisted_run_events",
            new=AsyncMock(return_value=persisted_events),
        ), patch("backend.main.session_manager.get_session", new=AsyncMock(return_value=None)):
            with client.stream("GET", "/runs/run-1/stream") as response:
                assert response.status_code == 200
                body = "".join(response.iter_text())

    assert body.count("event: agent_started") == 1
    assert body.count("event: pipeline_complete") == 1


def test_stream_run_replays_history_then_tails_live_events_without_duplicates(client: TestClient, monkeypatch) -> None:
    session_id = "run-1"
    initial_event = SessionEvent(
        session_id=session_id,
        event_type="agent_started",
        pipeline="sell",
        step="vision_analysis",
        data={"message": "started"},
        timestamp="2026-04-05T09:00:00+00:00",
    )
    terminal_event = SessionEvent(
        session_id=session_id,
        event_type="pipeline_complete",
        pipeline="sell",
        data={"outputs": {}},
    )
    asyncio.run(
        session_manager.create_session(
            session_id=session_id,
            pipeline="sell",
            request=PipelineStartRequest(
                user_id=FAKE_USER.user_id,
                input={"image_urls": ["https://example.com/item.jpg"]},
                metadata={"item_id": "22222222-2222-2222-2222-222222222222", "user_id": FAKE_USER.user_id},
            ),
        )
    )
    asyncio.run(session_manager.append_event(initial_event))
    monkeypatch.setattr("backend.main.KEEPALIVE_INTERVAL", 0.01, raising=False)

    def emit_terminal_event() -> None:
        time.sleep(0.03)
        asyncio.run(session_manager.append_event(terminal_event))

    worker = threading.Thread(target=emit_terminal_event, daemon=True)
    worker.start()

    with _authed_app():
        with patch("backend.main.get_persisted_run_record", new=AsyncMock(return_value=_persisted_run())), patch(
            "backend.main.list_persisted_run_events",
            new=AsyncMock(return_value=[initial_event]),
        ):
            with client.stream("GET", f"/runs/{session_id}/stream") as response:
                assert response.status_code == 200
                chunks: list[str] = []
                for chunk in response.iter_text():
                    chunks.append(chunk)
                    if "event: pipeline_complete" in "".join(chunks):
                        break

    worker.join(timeout=1)
    body = "".join(chunks)
    assert body.count("event: agent_started") == 1
    assert body.count("event: pipeline_complete") == 1
