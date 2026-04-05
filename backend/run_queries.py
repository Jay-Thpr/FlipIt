from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping
from urllib.parse import quote

from backend.config import is_supabase_configured
from backend.schemas import SessionEvent
from backend.supabase import get_supabase_client


def normalize_persisted_run_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    result_payload = row.get("result_payload")
    payload = dict(result_payload) if isinstance(result_payload, Mapping) else {}
    session_id = str(row.get("session_id", payload.get("session_id", "")))
    payload.setdefault("session_id", session_id)
    payload.setdefault("run_id", session_id)
    payload.setdefault("pipeline", row.get("pipeline"))
    payload.setdefault("status", row.get("status"))
    payload.setdefault("created_at", row.get("created_at"))
    payload.setdefault("updated_at", row.get("updated_at"))
    payload.setdefault("error", row.get("error"))
    payload.setdefault("item_id", row.get("item_id"))
    payload.setdefault("phase", row.get("phase"))
    if "next_action" not in payload:
        payload["next_action"] = {
            "type": row.get("next_action_type") or "wait",
            "payload": row.get("next_action_payload") or {},
        }
    return payload


def persisted_event_to_session_event(
    row: Mapping[str, Any],
    *,
    pipeline: str | None,
) -> SessionEvent:
    return SessionEvent(
        session_id=str(row.get("session_id", "")),
        event_type=str(row.get("event_type", "")),
        pipeline=pipeline,
        step=str(row["step"]) if row.get("step") is not None else None,
        data=dict(row.get("payload") or {}),
        timestamp=str(row.get("created_at") or ""),
    )


async def get_persisted_run_record(run_identifier: str, *, user_id: str | None = None) -> dict[str, Any] | None:
    if not is_supabase_configured():
        return None

    client = get_supabase_client()
    row = await _fetch_first_row(
        client,
        "/rest/v1/agent_runs",
        select="*",
        session_id=f"eq.{_quote(run_identifier)}",
        limit="1",
    )
    if row is None:
        row = await _fetch_first_row(
            client,
            "/rest/v1/agent_runs",
            select="*",
            id=f"eq.{_quote(run_identifier)}",
            limit="1",
        )
    if row is None:
        return None
    if user_id is not None and str(row.get("user_id")) != user_id:
        return None
    return row


async def get_latest_persisted_run_for_item(
    item_id: str,
    *,
    user_id: str,
    pipeline: str | None = None,
) -> dict[str, Any] | None:
    if not is_supabase_configured():
        return None

    params = {
        "select": "*",
        "item_id": f"eq.{_quote(item_id)}",
        "user_id": f"eq.{_quote(user_id)}",
        "order": "created_at.desc",
        "limit": "1",
    }
    if pipeline is not None:
        params["pipeline"] = f"eq.{_quote(pipeline)}"
    return await _fetch_first_row(get_supabase_client(), "/rest/v1/agent_runs", **params)


async def list_persisted_run_events(
    run_identifier: str,
    *,
    session_id: str | None = None,
    pipeline: str | None = None,
) -> list[SessionEvent]:
    if not is_supabase_configured():
        return []

    resolved_session_id = session_id or run_identifier
    rows = await _fetch_rows(
        get_supabase_client(),
        "/rest/v1/agent_run_events",
        select="*",
        session_id=f"eq.{_quote(resolved_session_id)}",
        order="created_at.asc",
    )
    return [persisted_event_to_session_event(row, pipeline=pipeline) for row in rows]


def event_identity(event: SessionEvent) -> tuple[str, str, str | None, str, str]:
    payload = json.dumps(event.data, sort_keys=True, separators=(",", ":"))
    return (
        event.session_id,
        event.event_type,
        event.step,
        event.timestamp,
        payload,
    )


def iso_sort_key(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.min


async def _fetch_first_row(client: Any, path: str, **params: str) -> dict[str, Any] | None:
    rows = await _fetch_rows(client, path, **params)
    if not rows:
        return None
    first = rows[0]
    return first if isinstance(first, dict) else None


async def _fetch_rows(client: Any, path: str, **params: str) -> list[dict[str, Any]]:
    response = await client.get(path, params=params)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        payload = data.get("data")
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        return [data]
    return []


def _quote(value: object) -> str:
    return quote(str(value), safe="")
