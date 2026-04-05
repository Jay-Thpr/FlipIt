from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import logging

from backend.schemas import PipelineStartRequest, SessionEvent, SessionState
from backend.supabase_repo import SupabaseRepository


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._subscribers: dict[str, set[asyncio.Queue[SessionEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._repo = SupabaseRepository()

    async def create_session(
        self,
        *,
        session_id: str,
        pipeline: str,
        request: PipelineStartRequest,
    ) -> SessionState:
        async with self._lock:
            state = SessionState(session_id=session_id, pipeline=pipeline, request=request)
            self._sessions[session_id] = state
        await self._persist_session(state)
        return state

    async def get_session(self, session_id: str) -> SessionState | None:
        session = self._sessions.get(session_id)
        if session is not None:
            return session
        if not self._repo.enabled():
            return None

        try:
            persisted_session = await self._repo.get_session_state(session_id)
        except Exception:
            logger.exception("Failed to load session %s from Supabase", session_id)
            return None
        if persisted_session is None:
            return None

        async with self._lock:
            self._sessions[session_id] = persisted_session
        return persisted_session

    async def update_status(
        self,
        session_id: str,
        *,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> SessionState | None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = status
            session.updated_at = utc_now_iso()
            if result is not None:
                session.result = result
            session.error = error
            snapshot = session.model_copy(deep=True)
        await self._persist_session(snapshot)
        return snapshot

    async def append_event(self, event: SessionEvent) -> None:
        async with self._lock:
            session = self._sessions.get(event.session_id)
            if session is None:
                return
            session.events.append(event)
            session.updated_at = utc_now_iso()
            snapshot = session.model_copy(deep=True)
            queues = list(self._subscribers.get(event.session_id, set()))
        for queue in queues:
            await queue.put(event)
        await self._persist_event(event)
        await self._persist_session(snapshot)

    async def subscribe(self, session_id: str) -> asyncio.Queue[SessionEvent]:
        queue: asyncio.Queue[SessionEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers[session_id].add(queue)
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue[SessionEvent]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(session_id)
            if subscribers is None:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(session_id, None)

    async def reset(self) -> None:
        async with self._lock:
            self._sessions.clear()
            self._subscribers.clear()

    async def _persist_session(self, session: SessionState) -> None:
        if not self._repo.enabled():
            return
        try:
            await self._repo.upsert_session_state(session)
        except Exception:
            logger.exception("Failed to persist session %s to Supabase", session.session_id)

    async def _persist_event(self, event: SessionEvent) -> None:
        if not self._repo.enabled():
            return
        try:
            await self._repo.insert_event(event)
        except Exception:
            logger.exception(
                "Failed to persist event %s for session %s to Supabase",
                event.event_type,
                event.session_id,
            )


session_manager = SessionManager()
