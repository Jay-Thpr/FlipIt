from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.repositories.agent_runs import RepositoryError, SupabaseClientLike
from backend.run_records import utc_now_iso


class MessageRepository:
    def __init__(
        self,
        client: SupabaseClientLike,
        *,
        messages_table: str = "messages",
    ) -> None:
        self.client = client
        self.messages_table = messages_table

    def create_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = {**payload}
        if "id" not in row:
            row["id"] = str(uuid4())
        row.setdefault("created_at", utc_now_iso())
        response = self.client.table(self.messages_table).insert(row).execute()
        result = self._first_row(response)
        if result is None:
            raise RepositoryError("expected a single row response from message insert")
        return result

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
