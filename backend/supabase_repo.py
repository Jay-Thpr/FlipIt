from __future__ import annotations

import os
from typing import Any

import httpx

from backend.schemas import SessionEvent, SessionState


TERMINAL_SESSION_STATUSES = {"completed", "failed"}


class SupabaseRepository:
    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.timeout = float(os.getenv("SUPABASE_TIMEOUT_SECONDS", "10"))

    def enabled(self) -> bool:
        return bool(self.url and self.service_role_key)

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> Any | None:
        if not self.enabled():
            return None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                f"{self.url}/rest/v1/{path}",
                params=params,
                json=json,
                headers=self._headers(prefer=prefer),
            )
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()

    def _session_payload(self, session: SessionState) -> dict[str, Any]:
        completed_at = session.updated_at if session.status in TERMINAL_SESSION_STATUSES else None
        return {
            "session_id": session.session_id,
            "pipeline": session.pipeline,
            "status": session.status,
            "request_payload": session.request.model_dump(),
            "result_payload": session.result,
            "error": session.error,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "completed_at": completed_at,
        }

    async def upsert_session_state(self, session: SessionState) -> None:
        await self._request(
            "POST",
            "pipeline_sessions",
            json=self._session_payload(session),
            prefer="resolution=merge-duplicates,return=minimal",
        )

    async def insert_event(self, event: SessionEvent) -> None:
        await self._request(
            "POST",
            "pipeline_session_events",
            json={
                "session_id": event.session_id,
                "event_type": event.event_type,
                "pipeline": event.pipeline,
                "step": event.step,
                "data": event.data,
                "timestamp": event.timestamp,
            },
            prefer="return=minimal",
        )

    async def get_session_state(self, session_id: str) -> SessionState | None:
        response = await self._request(
            "GET",
            "pipeline_sessions",
            params={
                "session_id": f"eq.{session_id}",
                "select": "session_id,pipeline,status,created_at,updated_at,request_payload,result_payload,error",
            },
        )
        if not response:
            return None

        events = await self.get_events(session_id)
        row = response[0]
        return SessionState(
            session_id=row["session_id"],
            pipeline=row["pipeline"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            request=row.get("request_payload") or {},
            result=row.get("result_payload") or {},
            error=row.get("error"),
            events=events,
        )

    async def get_events(self, session_id: str) -> list[SessionEvent]:
        response = await self._request(
            "GET",
            "pipeline_session_events",
            params={
                "session_id": f"eq.{session_id}",
                "select": "session_id,event_type,pipeline,step,data,timestamp",
                "order": "timestamp.asc",
            },
        )
        if not response:
            return []
        return [SessionEvent(**row) for row in response]
