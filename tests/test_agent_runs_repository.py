from __future__ import annotations

from typing import Any, Mapping

from backend.repositories.agent_runs import AgentRunRepository


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, rows_by_table: dict[str, list[dict[str, Any]]], table_name: str) -> None:
        self.rows_by_table = rows_by_table
        self.table_name = table_name
        self.operations: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def insert(self, payload: Any) -> "FakeQuery":
        self.operations.append(("insert", (payload,), {}))
        if isinstance(payload, Mapping):
            self.rows_by_table[self.table_name].append(dict(payload))
        return self

    def update(self, payload: Any) -> "FakeQuery":
        self.operations.append(("update", (payload,), {}))
        self._pending_update = dict(payload)
        return self

    def select(self, *columns: str) -> "FakeQuery":
        self.operations.append(("select", columns, {}))
        return self

    def eq(self, column: str, value: Any) -> "FakeQuery":
        self.operations.append(("eq", (column, value), {}))
        self._filter = (column, value)
        return self

    def order(self, column: str, desc: bool = False) -> "FakeQuery":
        self.operations.append(("order", (column,), {"desc": desc}))
        self._order = (column, desc)
        return self

    def limit(self, count: int) -> "FakeQuery":
        self.operations.append(("limit", (count,), {}))
        self._limit = count
        return self

    def execute(self) -> FakeResponse:
        rows = list(self.rows_by_table[self.table_name])
        if hasattr(self, "_filter"):
            column, value = self._filter
            rows = [row for row in rows if row.get(column) == value]
        if hasattr(self, "_order"):
            column, desc = self._order
            rows.sort(key=lambda row: row.get(column), reverse=desc)
        if hasattr(self, "_pending_update"):
            updated_rows = []
            for row in rows:
                row.update(self._pending_update)
                updated_rows.append(row)
            rows = updated_rows
        if hasattr(self, "_limit"):
            rows = rows[: self._limit]
        return FakeResponse(rows)


class FakeClient:
    def __init__(self) -> None:
        self.rows_by_table: dict[str, list[dict[str, Any]]] = {
            "agent_runs": [],
            "agent_run_events": [],
        }
        self.queries: list[tuple[str, FakeQuery]] = []

    def table(self, name: str) -> FakeQuery:
        query = FakeQuery(self.rows_by_table, name)
        self.queries.append((name, query))
        return query


def test_repository_create_and_fetch_run_by_session_id() -> None:
    client = FakeClient()
    repo = AgentRunRepository(client)

    created = repo.create_run(
        {
            "id": "run-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "pipeline": "sell",
            "status": "queued",
            "phase": "queued",
        }
    )

    fetched = repo.get_run_by_session_id("session-1")

    assert created["session_id"] == "session-1"
    assert created["id"] == "run-1"
    assert fetched is not None
    assert fetched["session_id"] == "session-1"
    assert client.rows_by_table["agent_runs"][0]["user_id"] == "user-1"


def test_repository_update_and_latest_lookup() -> None:
    client = FakeClient()
    repo = AgentRunRepository(client)

    repo.create_run(
        {
            "id": "run-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "pipeline": "buy",
            "item_id": "item-1",
            "status": "running",
            "phase": "running",
            "created_at": "2026-04-05T00:00:00+00:00",
            "updated_at": "2026-04-05T00:00:00+00:00",
        }
    )
    repo.create_run(
        {
            "id": "run-2",
            "session_id": "session-2",
            "user_id": "user-1",
            "pipeline": "buy",
            "item_id": "item-1",
            "status": "completed",
            "phase": "completed",
            "created_at": "2026-04-05T01:00:00+00:00",
            "updated_at": "2026-04-05T01:00:00+00:00",
        }
    )

    updated = repo.update_run_by_session_id("session-1", {"status": "completed", "phase": "completed"})
    latest = repo.get_latest_run_for_item("item-1", pipeline="buy")

    assert updated["status"] == "completed"
    assert latest is not None
    assert latest["session_id"] == "session-2"


def test_repository_append_and_list_events() -> None:
    client = FakeClient()
    repo = AgentRunRepository(client)

    run = repo.create_run(
        {
            "id": "run-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "pipeline": "sell",
            "status": "running",
            "phase": "running",
        }
    )
    repo.append_event(
        {
            "run_id": run["id"],
            "session_id": "session-1",
            "event_type": "pipeline_started",
            "step": "vision_analysis",
            "payload": {"hello": "world"},
        }
    )

    events = repo.list_events_for_run("run-1")

    assert len(events) == 1
    assert events[0]["event_type"] == "pipeline_started"
    assert events[0]["session_id"] == "session-1"
