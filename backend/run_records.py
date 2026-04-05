from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_agent_run_row(
    *,
    session_id: str,
    user_id: str,
    pipeline: str,
    item_id: str | None = None,
    status: str = "queued",
    phase: str = "queued",
    next_action_type: str | None = "wait",
    next_action_payload: dict[str, Any] | None = None,
    request_payload: dict[str, Any] | None = None,
    result_payload: dict[str, Any] | None = None,
    error: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    created_at_value = created_at or utc_now_iso()
    return {
        "session_id": session_id,
        "user_id": user_id,
        "item_id": item_id,
        "pipeline": pipeline,
        "status": status,
        "phase": phase,
        "next_action_type": next_action_type,
        "next_action_payload": next_action_payload or {},
        "request_payload": request_payload or {},
        "result_payload": result_payload or {},
        "error": error,
        "created_at": created_at_value,
        "updated_at": updated_at or created_at_value,
        "completed_at": completed_at,
    }


def build_agent_run_event_row(
    *,
    run_id: str,
    session_id: str,
    event_type: str,
    step: str | None = None,
    payload: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "session_id": session_id,
        "event_type": event_type,
        "step": step,
        "payload": payload or {},
        "created_at": created_at or utc_now_iso(),
    }
