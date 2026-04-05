"""Merge-validation tests: authenticated flows, run payload contract, durable read fallback.

These tests validate that the backend delivers a correct, frontend-ready contract
across the full authenticated workflow path.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.auth import AuthenticatedUser, get_current_user
from backend.frontend_runs import build_run_payload
from backend.main import _require_item_ownership, app
from backend.run_queries import normalize_persisted_run_payload
from backend.schemas import PipelineStartRequest, SessionState
from backend.session import session_manager

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

FAKE_USER = AuthenticatedUser(
    user_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    email="merge@test.com",
    role="authenticated",
    raw_claims={},
)

SELL_BODY = {
    "input": {"image_urls": ["https://example.com/img.jpg"]},
    "metadata": {},
}

BUY_BODY = {
    "input": {"query": "vintage jacket", "budget": 50.0},
    "metadata": {},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_session(session_id: str, pipeline: str, user_id: str) -> SessionState:
    req = PipelineStartRequest(user_id=user_id, input={}, metadata={})
    s = SessionState(session_id=session_id, pipeline=pipeline, request=req)
    s.status = "completed"
    s.result = {"outputs": {}}
    return s


def _get_run_id(data: dict) -> str:
    return data.get("run_id") or data.get("session_id")


def _get_session(run_id: str) -> SessionState | None:
    return asyncio.run(session_manager.get_session(run_id))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authed_client(client: TestClient):
    """TestClient with get_current_user overridden to return FAKE_USER."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def authed_client_with_ownership(authed_client: TestClient):
    """authed_client that also bypasses item ownership check."""
    app.dependency_overrides[_require_item_ownership] = lambda item_id: item_id
    yield authed_client
    app.dependency_overrides.pop(_require_item_ownership, None)


# ---------------------------------------------------------------------------
# Class 1: TestAuthenticatedSellRunUserPropagation
# ---------------------------------------------------------------------------


class TestAuthenticatedSellRunUserPropagation:
    """Authenticated sell run propagates user_id into the session."""

    def test_sell_run_session_has_authenticated_user_id(
        self, authed_client_with_ownership: TestClient
    ):
        with patch("backend.orchestrator.run_pipeline", new=AsyncMock()):
            resp = authed_client_with_ownership.post(
                "/items/item-1/sell/run", json=SELL_BODY
            )
        assert resp.status_code == 200
        session = _get_session(_get_run_id(resp.json()))
        assert session is not None
        assert session.request.user_id == FAKE_USER.user_id
        assert session.request.metadata["user_id"] == FAKE_USER.user_id

    def test_sell_run_body_user_id_overwritten_by_auth(
        self, authed_client_with_ownership: TestClient
    ):
        body = {**SELL_BODY, "user_id": "untrusted-body-user"}
        with patch("backend.orchestrator.run_pipeline", new=AsyncMock()):
            resp = authed_client_with_ownership.post(
                "/items/item-1/sell/run", json=body
            )
        assert resp.status_code == 200
        session = _get_session(_get_run_id(resp.json()))
        assert session is not None
        assert session.request.user_id == FAKE_USER.user_id
        assert session.request.user_id != "untrusted-body-user"


# ---------------------------------------------------------------------------
# Class 2: TestAuthenticatedBuyRunUserPropagation
# ---------------------------------------------------------------------------


class TestAuthenticatedBuyRunUserPropagation:
    """Authenticated buy run propagates user_id into the session."""

    def test_buy_run_session_has_authenticated_user_id(
        self, authed_client_with_ownership: TestClient
    ):
        with patch("backend.orchestrator.run_pipeline", new=AsyncMock()):
            resp = authed_client_with_ownership.post(
                "/items/item-1/buy/run", json=BUY_BODY
            )
        assert resp.status_code == 200
        session = _get_session(_get_run_id(resp.json()))
        assert session is not None
        assert session.request.user_id == FAKE_USER.user_id
        assert session.request.metadata["user_id"] == FAKE_USER.user_id


# ---------------------------------------------------------------------------
# Class 3: TestNormalizedRunPayloadShape
# ---------------------------------------------------------------------------


class TestNormalizedRunPayloadShape:
    """build_run_payload returns all required frontend contract fields."""

    def test_run_payload_has_required_fields(self):
        session = _build_session("s-sell-1", "sell", "user-1")
        payload = build_run_payload(session)
        assert "run_id" in payload
        assert "status" in payload
        assert "phase" in payload
        assert "pipeline" in payload
        assert "next_action" in payload
        assert isinstance(payload["next_action"], dict)
        assert "type" in payload["next_action"]
        assert "progress" in payload

    def test_buy_run_payload_has_required_fields(self):
        session = _build_session("s-buy-1", "buy", "user-1")
        payload = build_run_payload(session)
        assert "run_id" in payload
        assert "status" in payload
        assert "phase" in payload
        assert "pipeline" in payload
        assert "next_action" in payload
        assert isinstance(payload["next_action"], dict)
        assert "type" in payload["next_action"]
        assert "progress" in payload

    def test_run_payload_includes_result_source(self):
        session = _build_session("s-src-1", "sell", "user-1")
        payload = build_run_payload(session)
        assert "result_source" in payload


# ---------------------------------------------------------------------------
# Class 4: TestDurableRunReadFallback
# ---------------------------------------------------------------------------


class TestDurableRunReadFallback:
    """normalize_persisted_run_payload correctly reconstructs run payloads."""

    def test_run_lookup_falls_back_to_persisted_data(self):
        persisted = {
            "id": "run-db-id",
            "session_id": "s-gone",
            "user_id": "user-uuid-1",
            "pipeline": "sell",
            "status": "completed",
            "phase": "done",
            "next_action_type": "none",
            "next_action_payload": {},
            "result_payload": {
                "run_id": "s-gone",
                "status": "completed",
                "phase": "done",
                "pipeline": "sell",
                "next_action": {"type": "none", "payload": {}},
                "progress": 1.0,
                "result_source": "persisted",
            },
            "error": None,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:00:00Z",
            "item_id": None,
        }
        payload = normalize_persisted_run_payload(persisted)
        assert payload["run_id"] == "s-gone"
        assert payload["status"] == "completed"
        assert payload["result_source"] == "persisted"

    def test_normalize_fills_missing_fields_from_row(self):
        """Fields absent from result_payload are backfilled from the DB row."""
        row = {
            "session_id": "s-minimal",
            "pipeline": "buy",
            "status": "failed",
            "phase": "failed",
            "next_action_type": "show_error",
            "next_action_payload": {"error": "timeout"},
            "result_payload": {},
            "error": "timeout",
            "created_at": "2026-03-01T00:00:00Z",
            "updated_at": "2026-03-01T00:00:00Z",
            "item_id": "item-abc",
        }
        payload = normalize_persisted_run_payload(row)
        assert payload["run_id"] == "s-minimal"
        assert payload["pipeline"] == "buy"
        assert payload["status"] == "failed"
        assert payload["phase"] == "failed"
        assert payload["next_action"]["type"] == "show_error"
        assert payload["error"] == "timeout"
        assert payload["item_id"] == "item-abc"
