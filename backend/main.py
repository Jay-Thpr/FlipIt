import asyncio
import json
import logging
import os
import uuid
from contextlib import suppress
from typing import Any, Dict, Iterable, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from backend.constants import (
    BUY_AGENT_SEQUENCE,
    BUY_MODE,
    EVENT_AGENT_COMPLETED,
    EVENT_AGENT_ERROR,
    EVENT_AGENT_LOG,
    EVENT_AGENT_STARTED,
    EVENT_PIPELINE_COMPLETE,
    EVENT_PIPELINE_STARTED,
    SELL_AGENT_SEQUENCE,
    SELL_MODE,
    SESSION_TIMEOUT_SECONDS,
    STREAM_KEEPALIVE_SECONDS,
)
from backend.schemas import (
    BuyRequest,
    HealthResponse,
    InternalEventRequest,
    InternalResultRequest,
    SellRequest,
    SessionDetail,
    SessionEvent,
    SessionSummary,
    StartResponse,
)
from backend.session import (
    close_session,
    create_session,
    get_session_events as get_memory_session_events,
    get_session_record as get_memory_session_record,
    get_result as get_memory_result,
    get_session,
    list_sessions as list_memory_sessions,
    push_event,
    session_count,
    set_session_status,
    store_result,
)
from backend.supabase_repo import SupabaseRepository

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(title="DiamondHacks Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "diamondhacks-dev-secret")
supabase = SupabaseRepository()


async def persist_event(
    session_id: str,
    event_type: str,
    data: Dict[str, Any],
    *,
    agent_name: Optional[str] = None,
    summary: Optional[str] = None,
    dedupe_key: Optional[str] = None,
) -> None:
    await push_event(session_id, event_type, data)
    if not supabase.enabled():
        return
    try:
        await supabase.insert_event(
            session_id=session_id,
            event_type=event_type,
            payload=data,
            agent_name=agent_name,
            summary=summary,
            dedupe_key=dedupe_key,
        )
    except Exception:
        logger.exception("Failed to persist event for session %s", session_id)


async def persist_result(session_id: str, result_payload: Dict[str, Any]) -> None:
    store_result(session_id, result_payload)
    if not supabase.enabled():
        return
    try:
        await supabase.upsert_result(session_id=session_id, result_payload=result_payload)
    except Exception:
        logger.exception("Failed to persist result for session %s", session_id)


async def create_persistent_session(session_id: str, mode: str, input_payload: Dict[str, Any]) -> None:
    if not supabase.enabled():
        return
    try:
        await supabase.create_session(
            session_id=session_id,
            mode=mode,
            input_payload=input_payload,
        )
    except Exception:
        logger.exception("Failed to persist session %s", session_id)


async def mark_session_completed(session_id: str) -> None:
    set_session_status(session_id, "completed")
    if not supabase.enabled():
        return
    try:
        await supabase.mark_session_completed(session_id=session_id)
    except Exception:
        logger.exception("Failed to mark session %s completed", session_id)


async def mark_session_failed(session_id: str, error_summary: str) -> None:
    set_session_status(session_id, "failed", error_summary=error_summary)
    if not supabase.enabled():
        return
    try:
        await supabase.mark_session_failed(session_id=session_id, error_summary=error_summary)
    except Exception:
        logger.exception("Failed to mark session %s failed", session_id)


def _build_stub_result(mode: str, session_id: str, input_payload: Dict[str, Any]) -> Dict[str, Any]:
    if mode == SELL_MODE:
        return {
            "session_id": session_id,
            "mode": mode,
            "item": {
                "title": "Sample thrift item",
                "condition": "good",
            },
            "pricing": {
                "recommended_price": 48,
                "profit_margin": 27,
            },
            "listing_preview": {
                "platform": "Depop",
                "status": "ready_to_post",
            },
            "input_payload": input_payload,
        }

    return {
        "session_id": session_id,
        "mode": mode,
        "query": input_payload.get("query") or input_payload.get("url"),
        "ranked_listings": [
            {"platform": "Depop", "price": 60, "haggle_flag": True},
            {"platform": "eBay", "price": 67, "haggle_flag": False},
        ],
        "offers": [
            {"platform": "Depop", "seller": "sample_seller", "status": "sent"},
        ],
    }


async def run_stub_pipeline(
    session_id: str,
    mode: str,
    input_payload: Dict[str, Any],
    agents: Iterable[str],
) -> None:
    try:
        await persist_event(
            session_id,
            EVENT_PIPELINE_STARTED,
            {"mode": mode, "session_id": session_id},
            dedupe_key=f"{session_id}:{EVENT_PIPELINE_STARTED}",
        )

        for agent_name in agents:
            await persist_event(
                session_id,
                EVENT_AGENT_STARTED,
                {"agent_name": agent_name, "mode": mode},
                agent_name=agent_name,
                dedupe_key=f"{session_id}:{agent_name}:started",
            )
            await asyncio.sleep(0.5)
            await persist_event(
                session_id,
                EVENT_AGENT_LOG,
                {"agent_name": agent_name, "message": f"{agent_name} processed stub payload."},
                agent_name=agent_name,
            )
            await asyncio.sleep(0.5)
            await persist_event(
                session_id,
                EVENT_AGENT_COMPLETED,
                {"agent_name": agent_name, "summary": "Stub execution complete."},
                agent_name=agent_name,
                summary="Stub execution complete.",
                dedupe_key=f"{session_id}:{agent_name}:completed",
            )

        result_payload = _build_stub_result(mode, session_id, input_payload)
        await persist_result(session_id, result_payload)
        await persist_event(
            session_id,
            EVENT_PIPELINE_COMPLETE,
            {"mode": mode, "session_id": session_id},
            dedupe_key=f"{session_id}:{EVENT_PIPELINE_COMPLETE}",
        )
        await mark_session_completed(session_id)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        await persist_event(
            session_id,
            EVENT_AGENT_ERROR,
            {"agent_name": "pipeline", "error": str(exc)},
            agent_name="pipeline",
            summary=str(exc),
        )
        await mark_session_failed(session_id, str(exc))
    finally:
        await close_session(session_id)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        supabase_enabled=supabase.enabled(),
        memory_sessions=session_count(),
    )


@app.post("/sell/start", response_model=StartResponse)
async def sell_start(req: SellRequest) -> StartResponse:
    session_id = str(uuid.uuid4())
    input_payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    create_session(session_id, SELL_MODE, input_payload)
    await create_persistent_session(session_id, SELL_MODE, input_payload)
    asyncio.create_task(run_stub_pipeline(session_id, SELL_MODE, input_payload, SELL_AGENT_SEQUENCE))
    return StartResponse(session_id=session_id, mode=SELL_MODE)


@app.post("/buy/start", response_model=StartResponse)
async def buy_start(req: BuyRequest) -> StartResponse:
    if not req.query and not req.url:
        raise HTTPException(status_code=422, detail="Provide either query or url.")
    session_id = str(uuid.uuid4())
    input_payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    create_session(session_id, BUY_MODE, input_payload)
    await create_persistent_session(session_id, BUY_MODE, input_payload)
    asyncio.create_task(run_stub_pipeline(session_id, BUY_MODE, input_payload, BUY_AGENT_SEQUENCE))
    return StartResponse(session_id=session_id, mode=BUY_MODE)


@app.get("/stream/{session_id}")
async def stream(session_id: str, request: Request) -> EventSourceResponse:
    queue = get_session(session_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=STREAM_KEEPALIVE_SECONDS)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}
                continue

            if event is None:
                break

            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator(), send_timeout=SESSION_TIMEOUT_SECONDS)


@app.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(mode: Optional[str] = None, limit: int = 20) -> list[SessionSummary]:
    if supabase.enabled():
        with suppress(Exception):
            rows = await supabase.list_sessions(mode=mode, limit=limit)
            return [SessionSummary(**row) for row in rows]

    return [SessionSummary(**row) for row in list_memory_sessions(mode=mode, limit=limit)]


@app.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session_detail(session_id: str) -> SessionDetail:
    if supabase.enabled():
        with suppress(Exception):
            record = await supabase.get_session(session_id=session_id)
            if record is not None:
                events = await supabase.get_events(session_id=session_id)
                result_payload = await supabase.get_result(session_id=session_id)
                return SessionDetail(
                    **record,
                    events=[
                        SessionEvent(
                            event=event["event_type"],
                            data=event.get("payload") or {},
                            created_at=event.get("created_at"),
                        )
                        for event in events
                    ],
                    result_payload=result_payload,
                )

    record = get_memory_session_record(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetail(
        **record,
        events=[SessionEvent(**event) for event in get_memory_session_events(session_id)],
        result_payload=get_memory_result(session_id),
    )


@app.post("/internal/event/{session_id}")
async def internal_event(session_id: str, req: InternalEventRequest) -> Dict[str, bool]:
    if req.secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    await persist_event(
        session_id,
        req.event_type,
        req.data,
        agent_name=req.agent_name,
        summary=req.summary,
        dedupe_key=req.dedupe_key,
    )
    return {"ok": True}


@app.post("/internal/result/{session_id}")
async def store_internal_result(session_id: str, req: InternalResultRequest) -> Dict[str, bool]:
    if req.secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    await persist_result(session_id, req.result_payload)
    return {"ok": True}


@app.get("/result/{session_id}")
async def get_result(session_id: str) -> Dict[str, Any]:
    memory_result = get_memory_result(session_id)
    if memory_result is not None:
        return memory_result

    if supabase.enabled():
        with suppress(Exception):
            persisted_result = await supabase.get_result(session_id=session_id)
            if persisted_result is not None:
                return persisted_result

    raise HTTPException(status_code=404, detail="Result not found")
