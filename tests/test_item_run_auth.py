"""Tests for item/run ownership auth dependencies and endpoint protection.

Covers:
- ItemRepository.get_item_for_user (pure unit)
- _require_item_ownership FastAPI dependency
- _require_run_ownership FastAPI dependency
- Item-scoped endpoints require auth (401 with no token)
- Run-scoped endpoints require auth (401 with no token)
- Legacy /sell/start and /buy/start remain unauthenticated
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.auth import AuthenticatedUser, get_current_user
from backend.main import app
from backend.repositories.agent_runs import RepositoryError
from backend.repositories.items import ItemRepository
from backend.schemas import PipelineStartRequest, SessionState
from backend.session import session_manager

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

FAKE_USER = AuthenticatedUser(
    user_id="user-1",
    email="u@example.com",
    role="authenticated",
    raw_claims={},
)

SELL_PAYLOAD = {
    "user_id": "demo-user-1",
    "input": {"image_urls": ["https://example.com/shirt.jpg"]},
    "metadata": {},
}

BUY_PAYLOAD = {
    "user_id": "demo-user-1",
    "input": {"query": "vintage jacket", "budget": 50.0},
    "metadata": {},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(session_id: str = "run-1", user_id: str = "user-1") -> SessionState:
    req = PipelineStartRequest(
        user_id=user_id,
        input={"image_urls": ["https://example.com/img.jpg"]},
        metadata={"user_id": user_id},
    )
    session = SessionState(session_id=session_id, pipeline="sell", request=req)
    session.status = "completed"
    session.result = {"outputs": {}}
    return session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authed_client(client: TestClient):
    """TestClient with get_current_user overridden to return FAKE_USER."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield client
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Class 1: TestItemRepository — pure unit tests
# ---------------------------------------------------------------------------


class TestItemRepository:
    def _make_mock_client(self, data):
        """Build a mock client whose fluent chain returns data on .execute()."""
        mock_result = MagicMock()
        mock_result.data = data

        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_result

        mock_client = MagicMock()
        mock_client.table.return_value = mock_query
        return mock_client

    def test_returns_item_when_found(self):
        row = {"id": "item-1", "user_id": "user-1"}
        client = self._make_mock_client([row])
        repo = ItemRepository(client)
        result = repo.get_item_for_user("item-1", "user-1")
        assert result == row

    def test_returns_none_when_not_found(self):
        client = self._make_mock_client([])
        repo = ItemRepository(client)
        result = repo.get_item_for_user("item-1", "user-1")
        assert result is None

    def test_raises_repository_error_on_malformed_row(self):
        client = self._make_mock_client(["bad"])
        repo = ItemRepository(client)
        with pytest.raises(RepositoryError):
            repo.get_item_for_user("item-1", "user-1")


# ---------------------------------------------------------------------------
# Class 2: TestRequireItemOwnership — FastAPI dependency tests
# ---------------------------------------------------------------------------


class TestRequireItemOwnership:
    def test_503_when_supabase_not_configured(self, authed_client: TestClient):
        with patch("backend.config.is_supabase_configured", return_value=False):
            resp = authed_client.get("/items/item-1/runs/latest")
        assert resp.status_code == 503

    def test_404_when_item_not_found(self, authed_client: TestClient):
        mock_supabase_client = MagicMock()
        with patch("backend.config.is_supabase_configured", return_value=True), \
             patch("backend.supabase.get_supabase_client", return_value=mock_supabase_client), \
             patch("backend.main.ItemRepository") as MockRepo:
            mock_instance = MagicMock()
            MockRepo.return_value = mock_instance
            mock_instance.get_item_for_user.return_value = None
            resp = authed_client.get("/items/item-1/runs/latest")
        assert resp.status_code == 404

    def test_success_when_item_owned(self, authed_client: TestClient):
        mock_supabase_client = MagicMock()
        fake_session = _make_session("run-99", "user-1")
        with patch("backend.config.is_supabase_configured", return_value=True), \
             patch("backend.supabase.get_supabase_client", return_value=mock_supabase_client), \
             patch("backend.main.ItemRepository") as MockRepo, \
             patch.object(
                 session_manager,
                 "get_latest_session_for_item",
                 new=AsyncMock(return_value=fake_session),
             ):
            mock_instance = MagicMock()
            MockRepo.return_value = mock_instance
            mock_instance.get_item_for_user.return_value = {"id": "item-1", "user_id": "user-1"}
            resp = authed_client.get("/items/item-1/runs/latest")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Class 3: TestRequireRunOwnership — FastAPI dependency tests
# ---------------------------------------------------------------------------


class TestRequireRunOwnership:
    def test_404_when_session_not_found(self, authed_client: TestClient):
        with patch.object(session_manager, "get_session", new=AsyncMock(return_value=None)):
            resp = authed_client.get("/runs/run-1")
        assert resp.status_code == 404

    def test_403_when_user_mismatch(self, authed_client: TestClient):
        # Session owned by "other-user", authenticated as "user-1"
        other_session = _make_session("run-1", "other-user")
        with patch.object(session_manager, "get_session", new=AsyncMock(return_value=other_session)):
            resp = authed_client.get("/runs/run-1")
        assert resp.status_code == 403

    def test_200_when_run_owned(self, authed_client: TestClient):
        my_session = _make_session("run-1", "user-1")
        with patch.object(session_manager, "get_session", new=AsyncMock(return_value=my_session)):
            resp = authed_client.get("/runs/run-1")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Class 4: TestItemEndpointsRequireAuth
# ---------------------------------------------------------------------------


class TestItemEndpointsRequireAuth:
    """No auth header → 401 on item-scoped endpoints."""

    def test_item_sell_run_requires_auth(self, client: TestClient):
        resp = client.post("/items/item-1/sell/run", json=SELL_PAYLOAD)
        assert resp.status_code == 401

    def test_item_buy_run_requires_auth(self, client: TestClient):
        resp = client.post("/items/item-1/buy/run", json=BUY_PAYLOAD)
        assert resp.status_code == 401

    def test_item_runs_latest_requires_auth(self, client: TestClient):
        resp = client.get("/items/item-1/runs/latest")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Class 5: TestRunEndpointsRequireAuth
# ---------------------------------------------------------------------------


class TestRunEndpointsRequireAuth:
    """No auth header → 401 on run-scoped endpoints."""

    def test_get_run_requires_auth(self, client: TestClient):
        resp = client.get("/runs/run-1")
        assert resp.status_code == 401

    def test_stream_run_requires_auth(self, client: TestClient):
        resp = client.get("/runs/run-1/stream")
        assert resp.status_code == 401

    def test_run_sell_correct_requires_auth(self, client: TestClient):
        resp = client.post("/runs/run-1/sell/correct", json={"corrected_item": {}})
        assert resp.status_code == 401

    def test_run_sell_listing_decision_requires_auth(self, client: TestClient):
        resp = client.post(
            "/runs/run-1/sell/listing-decision",
            json={"decision": "confirm_submit"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Class 6: TestLegacyEndpointsUnaffected
# ---------------------------------------------------------------------------


class TestLegacyEndpointsUnaffected:
    """Legacy /sell/start and /buy/start should not require auth."""

    def test_sell_start_no_auth_needed(self, client: TestClient):
        with patch("backend.orchestrator.run_pipeline", new=AsyncMock()):
            resp = client.post("/sell/start", json=SELL_PAYLOAD)
        assert resp.status_code == 200

    def test_buy_start_no_auth_needed(self, client: TestClient):
        with patch("backend.orchestrator.run_pipeline", new=AsyncMock()):
            resp = client.post("/buy/start", json=BUY_PAYLOAD)
        assert resp.status_code == 200
