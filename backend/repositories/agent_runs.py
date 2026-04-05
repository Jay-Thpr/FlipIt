from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class RepositoryError(RuntimeError):
    """Raised when the repository layer cannot normalize a Supabase-like response."""


class TableQuery(Protocol):
    def insert(self, payload: Any) -> "TableQuery": ...

    def update(self, payload: Any) -> "TableQuery": ...

    def select(self, *columns: str) -> "TableQuery": ...

    def eq(self, column: str, value: Any) -> "TableQuery": ...

    def order(self, column: str, desc: bool = False) -> "TableQuery": ...

    def limit(self, count: int) -> "TableQuery": ...

    def execute(self) -> Any: ...


class SupabaseClientLike(Protocol):
    def table(self, name: str) -> TableQuery: ...


class AgentRunRepository:
    def __init__(
        self,
        client: SupabaseClientLike,
        *,
        runs_table: str = "agent_runs",
        events_table: str = "agent_run_events",
    ) -> None:
        self.client = client
        self.runs_table = runs_table
        self.events_table = events_table

    def create_run(self, row: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        if "created_at" not in payload and "updated_at" not in payload:
            from backend.run_records import utc_now_iso

            now = utc_now_iso()
            payload["created_at"] = now
            payload["updated_at"] = now
        elif "created_at" in payload and "updated_at" not in payload:
            payload["updated_at"] = payload["created_at"]
        return self._single_row(self.client.table(self.runs_table).insert(payload).execute())

    def update_run_by_session_id(self, session_id: str, updates: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(updates)
        if "updated_at" not in payload:
            from backend.run_records import utc_now_iso

            payload["updated_at"] = utc_now_iso()
        return self._single_row(
            self.client.table(self.runs_table).update(payload).eq("session_id", session_id).execute()
        )

    def get_run_by_session_id(self, session_id: str) -> dict[str, Any] | None:
        return self._first_row(
            self.client.table(self.runs_table)
            .select("*")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self._first_row(
            self.client.table(self.runs_table).select("*").eq("id", run_id).limit(1).execute()
        )

    def get_latest_run_for_item(self, item_id: str, *, pipeline: str | None = None) -> dict[str, Any] | None:
        query = self.client.table(self.runs_table).select("*").eq("item_id", item_id)
        if pipeline is not None:
            query = query.eq("pipeline", pipeline)
        return self._first_row(query.order("created_at", desc=True).limit(1).execute())

    def append_event(self, row: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        if "created_at" not in payload:
            from backend.run_records import utc_now_iso

            payload["created_at"] = utc_now_iso()
        return self._single_row(self.client.table(self.events_table).insert(payload).execute())

    def list_events_for_run(self, run_id: str) -> list[dict[str, Any]]:
        data = self.client.table(self.events_table).select("*").eq("run_id", run_id).order("created_at").execute()
        rows = self._response_rows(data)
        return [row for row in rows if isinstance(row, dict)]

    def _single_row(self, response: Any) -> dict[str, Any]:
        row = self._first_row(response)
        if row is None:
            raise RepositoryError("expected a single row response, received no rows")
        return row

    def _first_row(self, response: Any) -> dict[str, Any] | None:
        rows = self._response_rows(response)
        if not rows:
            return None
        first = rows[0]
        if not isinstance(first, dict):
            raise RepositoryError(f"expected row mapping, received {type(first)!r}")
        return first

    def _response_rows(self, response: Any) -> list[Any]:
        data = getattr(response, "data", response)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list):
                return data["data"]
            return [data]
        if data is None:
            return []
        return [data]
