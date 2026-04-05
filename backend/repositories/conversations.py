from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.repositories.agent_runs import RepositoryError, SupabaseClientLike
from backend.run_records import utc_now_iso


class ConversationRepository:
    def __init__(
        self,
        client: SupabaseClientLike,
        *,
        conversations_table: str = "conversations",
    ) -> None:
        self.client = client
        self.conversations_table = conversations_table

    def get_conversation_by_listing_url(self, user_id: str, listing_url: str) -> dict[str, Any] | None:
        response = (
            self.client.table(self.conversations_table)
            .select("*")
            .eq("user_id", user_id)
            .eq("listing_url", listing_url)
            .limit(1)
            .execute()
        )
        return self._first_row(response)

    def create_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = {**payload}
        if "id" not in row:
            row["id"] = str(uuid4())
        now = utc_now_iso()
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        response = self.client.table(self.conversations_table).insert(row).execute()
        result = self._first_row(response)
        if result is None:
            raise RepositoryError("expected a single row response from conversation insert")
        return result

    def upsert_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Find existing conversation by user_id + listing_url, or create a new one."""
        user_id = payload.get("user_id")
        listing_url = payload.get("listing_url")
        if user_id and listing_url:
            existing = self.get_conversation_by_listing_url(str(user_id), str(listing_url))
            if existing:
                return existing
        return self.create_conversation(payload)

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
