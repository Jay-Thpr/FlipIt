from __future__ import annotations

import logging
from typing import Protocol
from urllib.parse import quote
from uuid import UUID, uuid4

from backend.config import is_supabase_configured
from backend.frontend_runs import build_run_payload, get_session_item_id
from backend.run_records import build_agent_run_event_row, build_agent_run_row
from backend.schemas import SessionEvent, SessionState
from backend.supabase import SupabaseClient, get_supabase_client

logger = logging.getLogger(__name__)


class RunStore(Protocol):
    async def create_run(self, row: dict) -> None: ...

    async def update_run_by_session_id(self, session_id: str, updates: dict) -> None: ...

    async def append_event(self, row: dict) -> None: ...


class SupabaseRunStore:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def create_run(self, row: dict) -> None:
        response = await self._client.post("/rest/v1/agent_runs", json=row)
        response.raise_for_status()

    async def update_run_by_session_id(self, session_id: str, updates: dict) -> None:
        encoded_session_id = quote(session_id, safe="")
        response = await self._client.patch(f"/rest/v1/agent_runs?session_id=eq.{encoded_session_id}", json=updates)
        response.raise_for_status()

    async def append_event(self, row: dict) -> None:
        response = await self._client.post("/rest/v1/agent_run_events", json=row)
        response.raise_for_status()


class RunPersistenceManager:
    def __init__(self, store: RunStore | None = None) -> None:
        self._store = store
        self._run_ids_by_session_id: dict[str, str] = {}

    async def persist_session_created(self, session: SessionState) -> None:
        row = self._build_run_row(session)
        if row is None:
            return
        if session.session_id in self._run_ids_by_session_id:
            return

        row["id"] = str(uuid4())
        try:
            await self._get_store().create_run(row)
        except Exception:
            logger.exception("failed to persist created run for session %s", session.session_id)
            return
        self._run_ids_by_session_id[session.session_id] = row["id"]

    async def persist_session_updated(self, session: SessionState) -> None:
        row = self._build_run_row(session)
        if row is None:
            return

        if session.session_id not in self._run_ids_by_session_id:
            await self.persist_session_created(session)
            if session.session_id not in self._run_ids_by_session_id:
                return

        updates = {
            "status": row["status"],
            "phase": row["phase"],
            "next_action_type": row["next_action_type"],
            "next_action_payload": row["next_action_payload"],
            "request_payload": row["request_payload"],
            "result_payload": row["result_payload"],
            "error": row["error"],
            "item_id": row["item_id"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
        }
        try:
            await self._get_store().update_run_by_session_id(session.session_id, updates)
        except Exception:
            logger.exception("failed to persist updated run for session %s", session.session_id)

    async def persist_event(self, session: SessionState, event: SessionEvent) -> None:
        run_id = self._run_ids_by_session_id.get(event.session_id)
        if run_id is None:
            await self.persist_session_created(session)
            run_id = self._run_ids_by_session_id.get(event.session_id)
            if run_id is None:
                return

        row = build_agent_run_event_row(
            run_id=run_id,
            session_id=event.session_id,
            event_type=event.event_type,
            step=event.step,
            payload=event.data,
            created_at=event.timestamp,
        )
        row["id"] = str(uuid4())
        try:
            await self._get_store().append_event(row)
        except Exception:
            logger.exception("failed to persist run event %s for session %s", event.event_type, event.session_id)

    def reset(self) -> None:
        self._run_ids_by_session_id.clear()

    def _get_store(self) -> RunStore:
        if self._store is not None:
            return self._store
        self._store = SupabaseRunStore(get_supabase_client())
        return self._store

    def _build_run_row(self, session: SessionState) -> dict | None:
        user_id = _normalize_uuid(session.request.user_id)
        if user_id is None:
            logger.debug("skipping durable run persistence for session %s: invalid or missing user_id", session.session_id)
            return None

        frontend_payload = build_run_payload(session)
        return build_agent_run_row(
            session_id=session.session_id,
            user_id=user_id,
            pipeline=session.pipeline,
            item_id=_normalize_uuid(get_session_item_id(session)),
            status=session.status,
            phase=frontend_payload["phase"],
            next_action_type=frontend_payload["next_action"]["type"],
            next_action_payload=frontend_payload["next_action"]["payload"],
            request_payload=session.request.model_dump(),
            result_payload=frontend_payload,
            error=session.error,
            created_at=session.created_at,
            updated_at=session.updated_at,
            completed_at=session.updated_at if session.status in {"completed", "failed"} else None,
        )


_run_persistence_manager: RunPersistenceManager | None = None


def get_run_persistence_manager() -> RunPersistenceManager:
    global _run_persistence_manager
    if _run_persistence_manager is None:
        if is_supabase_configured():
            _run_persistence_manager = RunPersistenceManager()
        else:
            _run_persistence_manager = RunPersistenceManager(store=_NoopRunStore())
    return _run_persistence_manager


def reset_run_persistence_manager() -> None:
    global _run_persistence_manager
    if _run_persistence_manager is not None:
        _run_persistence_manager.reset()
    _run_persistence_manager = None


class _NoopRunStore:
    async def create_run(self, row: dict) -> None:
        return None

    async def update_run_by_session_id(self, session_id: str, updates: dict) -> None:
        return None

    async def append_event(self, row: dict) -> None:
        return None


def _normalize_uuid(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None
