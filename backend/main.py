from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import (
    AGENTS,
    APP_BASE_URL,
    INTERNAL_API_TOKEN,
    fetch_integration_flags,
    get_agent_execution_mode,
)
from backend.fetch_runtime import FETCH_AGENT_SPECS
from backend.orchestrator import get_pipeline_steps, run_pipeline
from backend.schemas import (
    CorrectionRequest,
    InternalEventRequest,
    PipelineStartRequest,
    PipelineStartResponse,
    SellListingDecisionRequest,
    SellListingDecisionResponse,
    SessionEvent,
)
from backend.session import session_manager

logger = logging.getLogger(__name__)

SELL_REVIEW_CLEANUP_INTERVAL_SECONDS = int(os.environ.get("SELL_REVIEW_CLEANUP_INTERVAL", "60"))


async def run_sell_review_cleanup_sweep() -> None:
    """Expire paused sell-listing reviews whose deadline has passed (used by tests and the background loop)."""
    from backend.orchestrator import expire_sell_listing_review_if_needed

    session_ids = await session_manager.list_paused_sell_review_session_ids()
    for session_id in session_ids:
        await expire_sell_listing_review_if_needed(session_id)


async def _sell_review_cleanup_loop() -> None:
    while True:
        try:
            await asyncio.sleep(SELL_REVIEW_CLEANUP_INTERVAL_SECONDS)
            await run_sell_review_cleanup_sweep()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("sell review cleanup sweep failed")


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    cleanup_task = asyncio.create_task(_sell_review_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="DiamondHacks Backend", version="0.1.0", lifespan=_app_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

KEEPALIVE_INTERVAL = 15.0


async def start_session(pipeline: str, request: PipelineStartRequest) -> PipelineStartResponse:
    response = PipelineStartResponse(
        pipeline=pipeline,
        status="queued",
        stream_url=f"{APP_BASE_URL}/stream",
        result_url=f"{APP_BASE_URL}/result",
    )
    await session_manager.create_session(session_id=response.session_id, pipeline=pipeline, request=request)
    asyncio.create_task(run_pipeline(response.session_id, pipeline, request))
    return response.model_copy(
        update={
            "stream_url": f"{APP_BASE_URL}/stream/{response.session_id}",
            "result_url": f"{APP_BASE_URL}/result/{response.session_id}",
        }
    )


@app.get("/health")
async def healthcheck() -> dict[str, str | bool]:
    flags = fetch_integration_flags()
    return {
        "status": "ok",
        "agent_execution_mode": get_agent_execution_mode(),
        "agent_count": str(len(AGENTS)),
        "fetch_enabled": flags["fetch_enabled"],
        "agentverse_credentials_present": flags["agentverse_credentials_present"],
    }


@app.get("/agents")
async def list_agents() -> dict[str, list[dict[str, str | int]]]:
    return {
        "agents": [
            {
                "name": agent.name,
                "slug": agent.slug,
                "port": agent.port,
            }
            for agent in AGENTS
        ]
    }


@app.get("/fetch-agents")
async def list_fetch_agents() -> dict[str, list[dict[str, str | int]]]:
    return {
        "agents": [
            {
                "name": spec.name,
                "slug": spec.slug,
                "port": spec.port,
            }
            for spec in FETCH_AGENT_SPECS.values()
        ]
    }


@app.get("/pipelines")
async def list_pipelines() -> dict[str, list[dict[str, str]]]:
    return get_pipeline_steps()


@app.post("/sell/start")
async def sell_start(request: PipelineStartRequest) -> PipelineStartResponse:
    return await start_session("sell", request)


@app.post("/buy/start")
async def buy_start(request: PipelineStartRequest) -> PipelineStartResponse:
    return await start_session("buy", request)


@app.post("/sell/correct")
async def sell_correct(request: CorrectionRequest) -> dict[str, bool]:
    """Called by frontend when user corrects a low-confidence identification."""
    from backend.orchestrator import resume_sell_pipeline
    
    session = await session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
        
    asyncio.create_task(resume_sell_pipeline(request.session_id, request.corrected_item))
    return {"ok": True}


@app.post("/sell/listing-decision")
async def sell_listing_decision(request: SellListingDecisionRequest) -> SellListingDecisionResponse:
    """Called by frontend when user confirms, revises, or aborts a paused sell listing review."""
    from backend.orchestrator import (
        fail_sell_listing_review,
        handle_sell_listing_decision,
        SELL_LISTING_MAX_REVISIONS,
        sell_listing_review_is_expired,
        sell_listing_review_reached_revision_limit,
    )

    session = await session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.pipeline != "sell":
        raise HTTPException(status_code=409, detail="Session is not a sell pipeline")
    if session.status != "paused" or session.sell_listing_review is None:
        raise HTTPException(status_code=409, detail="Session is not awaiting a sell listing decision")
    if sell_listing_review_is_expired(session.sell_listing_review):
        await fail_sell_listing_review(
            request.session_id,
            error="sell_listing_review_timeout",
            event_type="listing_review_expired",
        )
        raise HTTPException(status_code=409, detail="Session sell listing review has expired")
    if request.decision == "revise" and sell_listing_review_reached_revision_limit(session.sell_listing_review):
        await fail_sell_listing_review(
            request.session_id,
            error="sell_listing_revision_limit_reached",
            event_type="listing_revision_limit_reached",
            event_data={
                "decision": request.decision,
                "revision_count": session.sell_listing_review.revision_count,
                "max_revisions": SELL_LISTING_MAX_REVISIONS,
            },
        )
        raise HTTPException(status_code=409, detail="Session sell listing revision limit has been reached")

    asyncio.create_task(
        handle_sell_listing_decision(
            request.session_id,
            request.decision,
            revision_instructions=request.revision_instructions,
        )
    )
    review_state = session.sell_listing_review.model_copy() if session.sell_listing_review is not None else None
    queued_action = {
        "confirm_submit": "submit_listing",
        "revise": "apply_revision",
        "abort": "abort_listing",
    }[request.decision]
    return SellListingDecisionResponse(
        session_id=request.session_id,
        decision=request.decision,
        session_status=session.status,
        queued_action=queued_action,
        review_state=review_state,
        revision_instructions=request.revision_instructions,
    )


@app.get("/result/{session_id}")
async def get_result(session_id: str) -> dict:
    from backend.orchestrator import expire_sell_listing_review_if_needed

    await expire_sell_listing_review_if_needed(session_id)
    session = await session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@app.post("/internal/event/{session_id}")
async def post_internal_event(
    session_id: str,
    request: InternalEventRequest,
    x_internal_token: str | None = Header(default=None),
) -> dict[str, str]:
    if x_internal_token != INTERNAL_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid internal token")
    session = await session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await session_manager.append_event(
        SessionEvent(
            session_id=session_id,
            event_type=request.event_type,
            pipeline=session.pipeline,
            data=request.data,
        )
    )
    return {"status": "accepted"}


@app.get("/stream/{session_id}")
async def stream(session_id: str) -> StreamingResponse:
    from backend.orchestrator import expire_sell_listing_review_if_needed

    await expire_sell_listing_review_if_needed(session_id)
    session = await session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(iter_session_events(session_id), media_type="text/event-stream")


async def iter_session_events(session_id: str):
    from backend.orchestrator import expire_sell_listing_review_if_needed

    session = await session_manager.get_session(session_id)
    if session is None:
        return

    queue = await session_manager.subscribe(session_id)
    try:
        for event in session.events:
            yield format_sse(event)
            if event.event_type in {"pipeline_complete", "pipeline_failed"}:
                return
        while True:
            try:
                await expire_sell_listing_review_if_needed(session_id)
                event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_INTERVAL)
                yield format_sse(event)
                if event.event_type in {"pipeline_complete", "pipeline_failed"}:
                    break
            except asyncio.TimeoutError:
                yield ": ping\n\n"
    finally:
        await session_manager.unsubscribe(session_id, queue)


def format_sse(event: SessionEvent) -> str:
    return f"event: {event.event_type}\ndata: {json.dumps(event.model_dump())}\n\n"
