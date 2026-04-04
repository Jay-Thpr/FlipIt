from __future__ import annotations

from typing import Any

import httpx

from backend.config import APP_BASE_URL, INTERNAL_API_TOKEN, get_agent_execution_mode
from backend.schemas import InternalEventRequest, SessionEvent
from backend.session import session_manager


async def emit_browser_use_event(
    *,
    session_id: str,
    pipeline: str,
    step: str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    if not session_id:
        return

    if get_agent_execution_mode() == "local_functions":
        session = await session_manager.get_session(session_id)
        if session is None:
            return
        await session_manager.append_event(
            SessionEvent(
                session_id=session_id,
                pipeline=pipeline,
                step=step,
                event_type=event_type,
                data=data,
            )
        )
        return

    request = InternalEventRequest(event_type=event_type, data=data)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{APP_BASE_URL}/internal/event/{session_id}",
                json=request.model_dump(),
                headers={"x-internal-token": INTERNAL_API_TOKEN},
            )
    except Exception:
        return
