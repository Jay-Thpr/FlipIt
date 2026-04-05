from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.repositories.agent_runs import RepositoryError, SupabaseClientLike


class ItemProjectionRepository:
    def __init__(
        self,
        client: SupabaseClientLike,
        *,
        items_table: str = "items",
    ) -> None:
        self.client = client
        self.items_table = items_table

    def update_item_projection(
        self,
        *,
        item_id: str,
        user_id: str,
        updates: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        payload = dict(updates)
        if not payload:
            return None
        return self._first_row(
            self.client.table(self.items_table)
            .update(payload)
            .eq("id", item_id)
            .eq("user_id", user_id)
            .execute()
        )

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
