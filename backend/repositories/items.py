from __future__ import annotations

from typing import Any

from backend.repositories.agent_runs import RepositoryError, SupabaseClientLike


class ItemRepository:
    def __init__(
        self,
        client: SupabaseClientLike,
        *,
        items_table: str = "items",
    ) -> None:
        self.client = client
        self.items_table = items_table

    def get_item_for_user(self, item_id: str, user_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table(self.items_table)
            .select("*")
            .eq("id", item_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return self._first_row(response)

    def list_active_items(self) -> list[dict[str, Any]]:
        """Return all items with status='active', including their photos."""
        response = (
            self.client.table(self.items_table)
            .select("*", "item_photos(photo_url,sort_order)")
            .eq("status", "active")
            .execute()
        )
        return self._response_rows(response)

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
