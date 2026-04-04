import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from backend.constants import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_RUNNING,
)


class SupabaseRepository:
    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.timeout = float(os.getenv("SUPABASE_TIMEOUT_SECONDS", "10"))

    def enabled(self) -> bool:
        return bool(self.url and self.service_role_key)

    def _headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
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
        params: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        prefer: Optional[str] = None,
    ) -> Optional[Any]:
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

    async def create_session(
        self,
        *,
        session_id: str,
        mode: str,
        input_payload: Dict[str, Any],
    ) -> None:
        payload = {
            "session_id": session_id,
            "mode": mode,
            "status": SESSION_STATUS_RUNNING,
            "input_payload": input_payload,
        }
        await self._request(
            "POST",
            "pipeline_sessions",
            json=payload,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    async def mark_session_completed(self, *, session_id: str) -> None:
        await self._request(
            "PATCH",
            "pipeline_sessions",
            params={"session_id": f"eq.{session_id}"},
            json={
                "status": SESSION_STATUS_COMPLETED,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=minimal",
        )

    async def mark_session_failed(self, *, session_id: str, error_summary: str) -> None:
        await self._request(
            "PATCH",
            "pipeline_sessions",
            params={"session_id": f"eq.{session_id}"},
            json={
                "status": SESSION_STATUS_FAILED,
                "error_summary": error_summary,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=minimal",
        )

    async def insert_event(
        self,
        *,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
        agent_name: Optional[str] = None,
        summary: Optional[str] = None,
        dedupe_key: Optional[str] = None,
    ) -> None:
        event = {
            "session_id": session_id,
            "event_type": event_type,
            "agent_name": agent_name,
            "summary": summary,
            "payload": payload,
            "dedupe_key": dedupe_key,
        }
        await self._request(
            "POST",
            "pipeline_session_events",
            json=event,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    async def upsert_result(self, *, session_id: str, result_payload: Dict[str, Any]) -> None:
        await self._request(
            "POST",
            "pipeline_session_results",
            json={"session_id": session_id, "result_payload": result_payload},
            prefer="resolution=merge-duplicates,return=minimal",
        )

    async def get_result(self, *, session_id: str) -> Optional[Dict[str, Any]]:
        response = await self._request(
            "GET",
            "pipeline_session_results",
            params={"session_id": f"eq.{session_id}", "select": "result_payload"},
        )
        if not response:
            return None
        return response[0]["result_payload"]

    async def list_sessions(self, *, mode: Optional[str] = None, limit: int = 20) -> list[Dict[str, Any]]:
        params: Dict[str, str] = {
            "select": "session_id,mode,status,input_payload,error_summary,started_at,completed_at",
            "order": "started_at.desc",
            "limit": str(limit),
        }
        if mode:
            params["mode"] = f"eq.{mode}"
        response = await self._request("GET", "pipeline_sessions", params=params)
        return response or []

    async def get_session(self, *, session_id: str) -> Optional[Dict[str, Any]]:
        response = await self._request(
            "GET",
            "pipeline_sessions",
            params={
                "session_id": f"eq.{session_id}",
                "select": "session_id,mode,status,input_payload,error_summary,started_at,completed_at",
            },
        )
        if not response:
            return None
        return response[0]

    async def get_events(self, *, session_id: str) -> list[Dict[str, Any]]:
        response = await self._request(
            "GET",
            "pipeline_session_events",
            params={
                "session_id": f"eq.{session_id}",
                "select": "event_type,agent_name,summary,payload,created_at",
                "order": "created_at.asc",
            },
        )
        if not response:
            return []
        return response
