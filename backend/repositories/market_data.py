from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.repositories.agent_runs import RepositoryError, SupabaseClientLike


class MarketDataRepository:
    def __init__(
        self,
        client: SupabaseClientLike,
        *,
        table_name: str = "market_data",
    ) -> None:
        self.client = client
        self.table_name = table_name

    def upsert_market_snapshot(
        self,
        *,
        item_id: str,
        platform: str,
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = {"item_id": item_id, "platform": platform, **dict(snapshot)}
        existing = self._first_row(
            self.client.table(self.table_name)
            .select("*")
            .eq("item_id", item_id)
            .eq("platform", platform)
            .limit(1)
            .execute()
        )
        if existing is not None and existing.get("id"):
            return self._single_row(
                self.client.table(self.table_name)
                .update(dict(snapshot))
                .eq("id", existing["id"])
                .execute()
            )
        return self._single_row(self.client.table(self.table_name).insert(payload).execute())

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
