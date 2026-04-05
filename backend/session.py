from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from backend.schemas import PipelineStartRequest, SellListingReviewState, SessionEvent, SessionState


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._subscribers: dict[str, set[asyncio.Queue[SessionEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

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
            return state

    async def get_session(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

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
            if error is not None:
                session.error = error
            return session

    async def update_sell_listing_review(
        self,
        session_id: str,
        review_state: SellListingReviewState | None,
    ) -> SessionState | None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.sell_listing_review = review_state
            session.updated_at = utc_now_iso()
            return session

    async def clear_sell_listing_review(self, session_id: str) -> SessionState | None:
        return await self.update_sell_listing_review(session_id, None)

    async def append_event(self, event: SessionEvent) -> None:
        async with self._lock:
            session = self._sessions.get(event.session_id)
            if session is None:
                return
            session.events.append(event)
            session.updated_at = utc_now_iso()
            queues = list(self._subscribers.get(event.session_id, set()))
        for queue in queues:
            await queue.put(event)

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


session_manager = SessionManager()
