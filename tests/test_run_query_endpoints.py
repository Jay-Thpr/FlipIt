from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.auth import AuthenticatedUser, get_current_user
from backend.main import _require_item_ownership, app
from backend.schemas import PipelineStartRequest, SessionState


FAKE_USER = AuthenticatedUser(
    user_id="11111111-1111-1111-1111-111111111111",
    email="user@example.com",
    role="authenticated",
    raw_claims={},
)


@contextmanager
def _authed_app(*, item_ownership: bool = False):
    overrides: dict = {get_current_user: lambda: FAKE_USER}
    if item_ownership:
        async def _skip_item(item_id: str) -> str:
            return item_id
        overrides[_require_item_ownership] = _skip_item
    app.dependency_overrides.update(overrides)
    try:
        yield
    finally:
        for key in overrides:
            app.dependency_overrides.pop(key, None)


def _persisted_run(*, run_id: str = "run-1", item_id: str = "22222222-2222-2222-2222-222222222222", status: str = "completed", phase: str = "completed", updated_at: str = "2026-04-05T10:00:00+00:00") -> dict:
    return {
        "id": "db-run-1",
        "session_id": run_id,
        "user_id": FAKE_USER.user_id,
        "item_id": item_id,
        "pipeline": "sell",
        "status": status,
        "phase": phase,
        "next_action_type": "show_result" if status == "completed" else "wait",
        "next_action_payload": {},
        "result_payload": {
            "session_id": run_id,
            "run_id": run_id,
            "pipeline": "sell",
            "status": status,
            "phase": phase,
            "item_id": item_id,
            "next_action": {"type": "show_result" if status == "completed" else "wait", "payload": {}},
            "sell_summary": {"detected_item": "hoodie"},
        },
        "created_at": "2026-04-05T09:00:00+00:00",
        "updated_at": updated_at,
        "error": None,
    }


def _live_session(*, session_id: str = "run-1", item_id: str = "22222222-2222-2222-2222-222222222222", status: str = "running", updated_at: str = "2026-04-05T11:00:00+00:00") -> SessionState:
    session = SessionState(
        session_id=session_id,
        pipeline="sell",
        request=PipelineStartRequest(
            user_id=FAKE_USER.user_id,
            input={"image_urls": ["https://example.com/item.jpg"]},
            metadata={"item_id": item_id, "user_id": FAKE_USER.user_id},
        ),
    )
    session.status = status
    session.updated_at = updated_at
    session.result = {
        "pipeline": "sell",
        "outputs": {
            "vision_analysis": {
                "agent": "vision_agent",
                "display_name": "Vision Agent",
                "summary": "Detected hoodie",
                "detected_item": "hoodie",
                "brand": "Nike",
                "category": "tops",
                "condition": "good",
                "confidence": 0.92,
            }
        },
    }
    return session


def test_get_run_uses_persisted_payload_when_live_session_missing(client: TestClient) -> None:
    row = _persisted_run()
    with _authed_app():
        with patch("backend.main.get_persisted_run_record", new=AsyncMock(return_value=row)), patch(
            "backend.main.session_manager.get_session",
            new=AsyncMock(return_value=None),
        ):
            response = client.get("/runs/run-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-1"
    assert payload["item_id"] == row["item_id"]
    assert payload["phase"] == "completed"
    assert payload["sell_summary"]["detected_item"] == "hoodie"


def test_get_latest_item_run_prefers_newer_live_session(client: TestClient) -> None:
    item_id = "22222222-2222-2222-2222-222222222222"
    row = _persisted_run(item_id=item_id, updated_at="2026-04-05T10:00:00+00:00")
    session = _live_session(item_id=item_id, updated_at="2026-04-05T11:00:00+00:00")

    with _authed_app(item_ownership=True):
        with patch("backend.main.get_latest_persisted_run_for_item", new=AsyncMock(return_value=row)), patch(
            "backend.main.session_manager.get_latest_session_for_item",
            new=AsyncMock(return_value=session),
        ):
            response = client.get(f"/items/{item_id}/runs/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == session.session_id
    assert payload["status"] == "running"
    assert payload["phase"] == "running"


def test_get_run_returns_403_for_persisted_run_owned_by_another_user(client: TestClient) -> None:
    row = _persisted_run()
    row["user_id"] = "99999999-9999-9999-9999-999999999999"

    with _authed_app():
        with patch("backend.main.get_persisted_run_record", new=AsyncMock(return_value=row)), patch(
            "backend.main.session_manager.get_session",
            new=AsyncMock(return_value=None),
        ):
            response = client.get("/runs/run-1")

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}
