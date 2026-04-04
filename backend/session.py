import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


EventQueue = asyncio.Queue

_sessions: Dict[str, EventQueue] = {}
_results: Dict[str, dict] = {}
_session_records: Dict[str, dict] = {}
_session_events: Dict[str, List[dict]] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(session_id: str, mode: Optional[str] = None, input_payload: Optional[dict] = None) -> EventQueue:
    queue: EventQueue = asyncio.Queue()
    _sessions[session_id] = queue
    _session_records[session_id] = {
        "session_id": session_id,
        "mode": mode,
        "status": "running",
        "input_payload": input_payload or {},
        "error_summary": None,
        "started_at": _utc_now_iso(),
        "completed_at": None,
    }
    _session_events[session_id] = []
    return queue


def get_session(session_id: str) -> Optional[EventQueue]:
    return _sessions.get(session_id)


def session_count() -> int:
    return len(_sessions)


async def push_event(session_id: str, event_type: str, data: dict) -> None:
    queue = _sessions.get(session_id)
    _session_events.setdefault(session_id, []).append(
        {
            "event": event_type,
            "data": data,
            "created_at": _utc_now_iso(),
        }
    )
    if queue is not None:
        await queue.put({"event": event_type, "data": data})


async def close_session(session_id: str) -> None:
    queue = _sessions.get(session_id)
    if queue is not None:
        await queue.put(None)
    _sessions.pop(session_id, None)


def store_result(session_id: str, result_payload: dict) -> None:
    _results[session_id] = result_payload


def get_result(session_id: str) -> Optional[dict]:
    return _results.get(session_id)


def set_session_status(session_id: str, status: str, error_summary: Optional[str] = None) -> None:
    record = _session_records.get(session_id)
    if record is None:
        return
    record["status"] = status
    record["error_summary"] = error_summary
    if status != "running":
        record["completed_at"] = _utc_now_iso()


def list_sessions(mode: Optional[str] = None, limit: int = 20) -> List[dict]:
    records = list(_session_records.values())
    if mode:
        records = [record for record in records if record.get("mode") == mode]
    records.sort(key=lambda record: record.get("started_at") or "", reverse=True)
    return records[:limit]


def get_session_record(session_id: str) -> Optional[dict]:
    return _session_records.get(session_id)


def get_session_events(session_id: str) -> List[dict]:
    return _session_events.get(session_id, [])
