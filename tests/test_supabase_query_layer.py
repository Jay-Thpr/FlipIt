"""Tests for SupabaseClient.table() query builder and repository layer.

Covers:
  1. TableQueryBuilder param composition (patching _sync_get/_sync_post/_sync_patch)
  2. ItemRepository with mock client
  3. AgentRunRepository with mock client
  4. Integration: real SupabaseClient round-trip with patched HTTP transport
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, call, patch

import pytest

from backend.repositories.agent_runs import AgentRunRepository, RepositoryError
from backend.repositories.items import ItemRepository
from backend.supabase import SupabaseClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(json_data: Any) -> Mock:
    """Return a Mock that behaves like an httpx.Response with .json() and .raise_for_status()."""
    resp = Mock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _real_client() -> SupabaseClient:
    """Real SupabaseClient instance that will never talk to the network (methods are patched)."""
    return SupabaseClient("http://test.example", "test-service-key")


# ---------------------------------------------------------------------------
# 1. Query builder composition
# ---------------------------------------------------------------------------

class TestSelectBuildsCorrectParams:
    def test_select_builds_correct_params(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp) as mock_get:
            client.table("items").select("*").eq("id", "x").limit(1).execute()

        mock_get.assert_called_once_with(
            "/rest/v1/items",
            params={"select": "*", "id": "eq.x", "limit": "1"},
        )

    def test_eq_filter_uses_postgrest_syntax(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp) as mock_get:
            client.table("items").select("*").eq("user_id", "u1").eq("id", "i1").execute()

        _, kwargs = mock_get.call_args
        params = kwargs.get("params") or mock_get.call_args[0][1] if len(mock_get.call_args[0]) > 1 else mock_get.call_args[1]["params"]
        # Unpack however it was passed
        called_params = mock_get.call_args[1].get("params") if mock_get.call_args[1] else mock_get.call_args[0][1]
        assert called_params["user_id"] == "eq.u1"
        assert called_params["id"] == "eq.i1"

    def test_order_desc_builds_correct_param(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp) as mock_get:
            client.table("items").select("*").order("created_at", desc=True).execute()

        called_params = mock_get.call_args[1]["params"]
        assert called_params["order"] == "created_at.desc"

    def test_order_asc_builds_correct_param(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp) as mock_get:
            client.table("items").select("*").order("created_at").execute()

        called_params = mock_get.call_args[1]["params"]
        assert called_params["order"] == "created_at.asc"

    def test_insert_calls_post_with_prefer_header(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([{"a": 1}])

        with patch.object(client, "_sync_post", return_value=mock_resp) as mock_post:
            client.table("items").insert({"a": 1}).execute()

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs.get("json") == {"a": 1} or mock_post.call_args[1].get("json") == {"a": 1}
        extra_headers = mock_post.call_args[1].get("extra_headers", {})
        assert extra_headers.get("Prefer") == "return=representation"

    def test_update_calls_patch_with_filter_and_prefer(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([{"session_id": "abc", "status": "done"}])

        with patch.object(client, "_sync_patch", return_value=mock_resp) as mock_patch:
            client.table("agent_runs").update({"status": "done"}).eq("session_id", "abc").execute()

        mock_patch.assert_called_once()
        kwargs = mock_patch.call_args[1]
        assert kwargs.get("json") == {"status": "done"}
        assert kwargs.get("params", {}).get("session_id") == "eq.abc"
        assert kwargs.get("extra_headers", {}).get("Prefer") == "return=representation"

    def test_execute_returns_query_result_with_data(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([{"id": "1"}])

        with patch.object(client, "_sync_get", return_value=mock_resp):
            result = client.table("items").select("*").eq("id", "1").execute()

        assert result.data == [{"id": "1"}]


# ---------------------------------------------------------------------------
# Mock helpers for repository tests
# ---------------------------------------------------------------------------

class MockTableQuery:
    """Minimal fluent query that returns fixed rows on execute()."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows
        self._eq_filters: list[tuple[str, Any]] = []
        self._last_insert: dict[str, Any] | None = None
        self._last_update: dict[str, Any] | None = None

    def select(self, *args: str) -> "MockTableQuery":
        return self

    def eq(self, col: str, val: Any) -> "MockTableQuery":
        self._eq_filters.append((col, val))
        return self

    def order(self, col: str, desc: bool = False) -> "MockTableQuery":
        return self

    def limit(self, n: int) -> "MockTableQuery":
        return self

    def insert(self, payload: Any) -> "MockTableQuery":
        self._last_insert = dict(payload) if isinstance(payload, dict) else payload
        # Add inserted payload to rows so _single_row can retrieve it
        self._rows = [self._last_insert] if self._last_insert is not None else []
        return self

    def update(self, payload: Any) -> "MockTableQuery":
        self._last_update = dict(payload) if isinstance(payload, dict) else payload
        if self._rows:
            merged = {**self._rows[0], **self._last_update}
            self._rows = [merged]
        else:
            self._rows = [self._last_update]
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=list(self._rows))


class MockClient:
    """Minimal mock that returns a MockTableQuery with pre-set rows."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows
        self._last_query: MockTableQuery | None = None

    def table(self, name: str) -> MockTableQuery:
        q = MockTableQuery(list(self._rows))
        self._last_query = q
        return q


class CapturingMockClient:
    """MockClient that captures each table query so tests can inspect call args."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows
        self.queries: list[tuple[str, MockTableQuery]] = []

    def table(self, name: str) -> MockTableQuery:
        q = MockTableQuery(list(self._rows))
        self.queries.append((name, q))
        return q


# ---------------------------------------------------------------------------
# 2. ItemRepository tests
# ---------------------------------------------------------------------------

class TestItemRepository:
    def test_get_item_for_user_found(self) -> None:
        row = {"id": "item-1", "user_id": "u1"}
        repo = ItemRepository(MockClient([row]))
        result = repo.get_item_for_user("item-1", "u1")
        assert result == row

    def test_get_item_for_user_not_found(self) -> None:
        repo = ItemRepository(MockClient([]))
        result = repo.get_item_for_user("item-1", "u1")
        assert result is None

    def test_get_item_for_user_malformed_row(self) -> None:
        repo = ItemRepository(MockClient(["bad"]))
        with pytest.raises(RepositoryError):
            repo.get_item_for_user("item-1", "u1")


# ---------------------------------------------------------------------------
# 3. AgentRunRepository tests
# ---------------------------------------------------------------------------

class TestAgentRunRepository:
    def test_get_latest_run_for_item_builds_correct_query(self) -> None:
        row = {"id": "run-1", "item_id": "item-1", "pipeline": "buy", "created_at": "2026-01-01T00:00:00+00:00"}
        repo = AgentRunRepository(MockClient([row]))
        result = repo.get_latest_run_for_item("item-1")
        assert result is not None
        assert result["id"] == "run-1"

    def test_get_latest_run_for_item_with_pipeline_filter(self) -> None:
        row = {"id": "run-1", "item_id": "item-1", "pipeline": "sell", "created_at": "2026-01-01T00:00:00+00:00"}
        capturing = CapturingMockClient([row])
        repo = AgentRunRepository(capturing)
        repo.get_latest_run_for_item("item-1", pipeline="sell")

        assert len(capturing.queries) == 1
        _table_name, query = capturing.queries[0]
        # "pipeline" eq filter must be present
        filter_cols = [col for col, _ in query._eq_filters]
        assert "item_id" in filter_cols
        assert "pipeline" in filter_cols

    def test_get_run_by_session_id_found(self) -> None:
        row = {"id": "run-1", "session_id": "s1"}
        repo = AgentRunRepository(MockClient([row]))
        result = repo.get_run_by_session_id("s1")
        assert result == row

    def test_get_run_by_session_id_not_found(self) -> None:
        repo = AgentRunRepository(MockClient([]))
        result = repo.get_run_by_session_id("s1")
        assert result is None

    def test_create_run_sets_timestamps(self) -> None:
        capturing = CapturingMockClient([])
        repo = AgentRunRepository(capturing)

        # create_run calls insert; MockTableQuery.insert sets _rows to [payload]
        # so _single_row will get the payload back.
        repo.create_run({"session_id": "s1", "pipeline": "sell"})

        assert len(capturing.queries) == 1
        _table_name, query = capturing.queries[0]
        inserted = query._last_insert
        assert inserted is not None
        assert "created_at" in inserted
        assert "updated_at" in inserted

    def test_update_run_sets_updated_at(self) -> None:
        existing = {"session_id": "s1", "status": "running"}
        capturing = CapturingMockClient([existing])
        repo = AgentRunRepository(capturing)

        repo.update_run_by_session_id("s1", {"status": "completed"})

        _table_name, query = capturing.queries[0]
        updated = query._last_update
        assert updated is not None
        assert "updated_at" in updated

    def test_append_event_sets_created_at(self) -> None:
        capturing = CapturingMockClient([])
        repo = AgentRunRepository(capturing)

        repo.append_event({"run_id": "r1", "event_type": "test"})

        _table_name, query = capturing.queries[0]
        inserted = query._last_insert
        assert inserted is not None
        assert "created_at" in inserted

    def test_single_row_raises_on_empty(self) -> None:
        repo = AgentRunRepository(MockClient([]))
        with pytest.raises(RepositoryError, match="expected a single row response"):
            repo._single_row(SimpleNamespace(data=[]))


# ---------------------------------------------------------------------------
# 4. Integration: real SupabaseClient.table() with patched HTTP methods
# ---------------------------------------------------------------------------

class TestSupabaseClientTableIntegration:
    def test_table_select_returns_rows_from_real_client(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([{"id": "1"}])

        with patch.object(client, "_sync_get", return_value=mock_resp):
            result = client.table("items").select("*").eq("id", "1").limit(1).execute()

        assert result.data == [{"id": "1"}]

    def test_table_insert_returns_created_row(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([{"id": "1", "name": "test"}])

        with patch.object(client, "_sync_post", return_value=mock_resp):
            result = client.table("items").insert({"name": "test"}).execute()

        assert result.data[0]["id"] == "1"
        assert result.data[0]["name"] == "test"

    def test_table_update_returns_updated_row(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([{"session_id": "abc", "status": "done"}])

        with patch.object(client, "_sync_patch", return_value=mock_resp):
            result = client.table("agent_runs").update({"status": "done"}).eq("session_id", "abc").execute()

        assert result.data[0]["status"] == "done"

    def test_select_no_rows_returns_empty_data(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp):
            result = client.table("items").select("*").execute()

        assert result.data == []

    def test_path_includes_table_name(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp) as mock_get:
            client.table("my_custom_table").select("*").execute()

        called_path = mock_get.call_args[0][0]
        assert "my_custom_table" in called_path

    def test_multiple_eq_filters_all_in_params(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp) as mock_get:
            client.table("items").select("*").eq("user_id", "u1").eq("id", "i1").execute()

        called_params = mock_get.call_args[1]["params"]
        assert called_params["user_id"] == "eq.u1"
        assert called_params["id"] == "eq.i1"

    def test_limit_included_in_select_params(self) -> None:
        client = _real_client()
        mock_resp = _make_mock_response([])

        with patch.object(client, "_sync_get", return_value=mock_resp) as mock_get:
            client.table("items").select("*").limit(5).execute()

        called_params = mock_get.call_args[1]["params"]
        assert called_params["limit"] == "5"

    def test_insert_payload_forwarded_as_json(self) -> None:
        client = _real_client()
        payload = {"name": "sneakers", "price": 42}
        mock_resp = _make_mock_response([payload])

        with patch.object(client, "_sync_post", return_value=mock_resp) as mock_post:
            client.table("items").insert(payload).execute()

        assert mock_post.call_args[1]["json"] == payload
