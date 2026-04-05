from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import (
    AGENTS,
    APP_BASE_URL,
    INTERNAL_API_TOKEN,
    assert_fetch_agent_ports_do_not_overlap,
    fetch_integration_flags,
    get_agent_execution_mode,
)
from backend.fetch_runtime import list_fetch_agent_capabilities, list_fetch_agent_specs
from backend.frontend_runs import build_run_payload, build_run_start_response
from backend.orchestrator import get_pipeline_steps, run_pipeline
from backend.run_queries import (
    event_identity,
    get_latest_persisted_run_for_item,
    get_persisted_run_record,
    iso_sort_key,
    list_persisted_run_events,
    normalize_persisted_run_payload,
)
from backend.schemas import (
    CorrectionRequest,
    InternalEventRequest,
    PipelineStartRequest,
    PipelineStartResponse,
    RunCorrectionRequest,
    RunSellListingDecisionRequest,
    SellListingDecisionRequest,
    SellListingDecisionResponse,
    SessionEvent,
)
from backend.auth import AuthenticatedUser, get_current_user
from backend.repositories.items import ItemRepository
from backend.session import session_manager

logger = logging.getLogger(__name__)


async def _require_item_ownership(
    item_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """Verify the authenticated user owns item_id. Returns item_id on success."""
    from backend.config import is_supabase_configured
    from backend.supabase import get_supabase_client

    if not is_supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase not configured")
    client = get_supabase_client()
    repo = ItemRepository(client)
    item = repo.get_item_for_user(item_id, user.user_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_id


async def _require_run_ownership(
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """Verify the authenticated user owns the run identified by run_id."""
    session = await session_manager.get_session(run_id)
    if session is not None:
        session_user_id = session.request.user_id or session.request.metadata.get("user_id")
        if session_user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return run_id

    persisted_run = await get_persisted_run_record(run_id)
    if persisted_run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if str(persisted_run.get("user_id")) != user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return run_id


async def _get_live_or_persisted_session_id(run_id: str) -> str | None:
    session = await session_manager.get_session(run_id)
    if session is not None:
        return session.session_id
    persisted_run = await get_persisted_run_record(run_id)
    if persisted_run is None:
        return None
    return str(persisted_run.get("session_id") or "")


async def _get_run_payload(run_id: str) -> dict | None:
    persisted_run = await get_persisted_run_record(run_id)
    session_id = run_id
    if persisted_run is not None and persisted_run.get("session_id"):
        session_id = str(persisted_run["session_id"])
    session = await session_manager.get_session(session_id)
    if session is None:
        return normalize_persisted_run_payload(persisted_run) if persisted_run is not None else None
    return build_run_payload(session)


async def _get_latest_item_run_payload(item_id: str, *, user_id: str) -> dict | None:
    persisted_run = await get_latest_persisted_run_for_item(item_id, user_id=user_id)
    live_session = await session_manager.get_latest_session_for_item(item_id)

    if persisted_run is None and live_session is None:
        return None
    if persisted_run is None:
        return build_run_payload(live_session)
    if live_session is None:
        return normalize_persisted_run_payload(persisted_run)

    persisted_updated_at = iso_sort_key(persisted_run.get("updated_at") or persisted_run.get("created_at"))
    live_updated_at = iso_sort_key(live_session.updated_at or live_session.created_at)
    if live_updated_at >= persisted_updated_at:
        return build_run_payload(live_session)
    return normalize_persisted_run_payload(persisted_run)


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
    assert_fetch_agent_ports_do_not_overlap()
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


async def start_session(pipeline: str, request: PipelineStartRequest, *, item_id: str | None = None) -> dict:
    if item_id is not None:
        request = request.model_copy(update={"metadata": {**request.metadata, "item_id": item_id}})
    response = PipelineStartResponse(
        pipeline=pipeline,
        status="queued",
        stream_url=f"{APP_BASE_URL}/stream",
        result_url=f"{APP_BASE_URL}/result",
    )
    await session_manager.create_session(session_id=response.session_id, pipeline=pipeline, request=request)
    asyncio.create_task(run_pipeline(response.session_id, pipeline, request))
    response_payload = response.model_copy(
        update={
            "stream_url": f"{APP_BASE_URL}/stream/{response.session_id}",
            "result_url": f"{APP_BASE_URL}/result/{response.session_id}",
        }
    ).model_dump()
    return build_run_start_response(
        payload=response_payload,
        item_id=item_id,
        run_url=f"{APP_BASE_URL}/runs/{response.session_id}",
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


@app.get("/config")
async def get_config() -> dict[str, str]:
    return {
        "resale_copilot_agent_address": os.environ.get("RESALE_COPILOT_AGENT_ADDRESS", ""),
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
async def list_fetch_agents() -> dict[str, list[dict[str, object]]]:
    return {
        "agents": list_fetch_agent_specs(),
    }


@app.get("/fetch-agent-capabilities")
async def list_fetch_agent_capability_registry() -> dict[str, list[dict[str, object]]]:
    return {
        "agents": list_fetch_agent_capabilities(),
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


@app.post("/items/{item_id}/sell/run")
async def item_sell_run(
    item_id: str,
    request: PipelineStartRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    _owned: str = Depends(_require_item_ownership),
) -> dict:
    request = request.model_copy(update={"metadata": {**request.metadata, "user_id": user.user_id}})
    return await start_session("sell", request, item_id=item_id)


@app.post("/items/{item_id}/buy/run")
async def item_buy_run(
    item_id: str,
    request: PipelineStartRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    _owned: str = Depends(_require_item_ownership),
) -> dict:
    request = request.model_copy(update={"metadata": {**request.metadata, "user_id": user.user_id}})
    return await start_session("buy", request, item_id=item_id)


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
    return build_run_payload(session)


@app.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    _owned: str = Depends(_require_run_ownership),
) -> dict:
    from backend.orchestrator import expire_sell_listing_review_if_needed

    live_or_persisted_session_id = await _get_live_or_persisted_session_id(run_id)
    if live_or_persisted_session_id is not None:
        await expire_sell_listing_review_if_needed(live_or_persisted_session_id)
    payload = await _get_run_payload(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return payload


@app.get("/items/{item_id}/runs/latest")
async def get_latest_item_run(
    item_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    _owned: str = Depends(_require_item_ownership),
) -> dict:
    payload = await _get_latest_item_run_payload(item_id, user_id=user.user_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found for item")
    return payload


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


@app.get("/runs/{run_id}/stream")
async def stream_run(
    run_id: str,
    _owned: str = Depends(_require_run_ownership),
) -> StreamingResponse:
    live_or_persisted_session_id = await _get_live_or_persisted_session_id(run_id)
    if live_or_persisted_session_id is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return StreamingResponse(iter_run_events(run_id), media_type="text/event-stream")


@app.post("/runs/{run_id}/sell/correct")
async def run_sell_correct(
    run_id: str,
    request: RunCorrectionRequest,
    _owned: str = Depends(_require_run_ownership),
) -> dict[str, bool]:
    return await sell_correct(CorrectionRequest(session_id=run_id, corrected_item=request.corrected_item))


@app.post("/runs/{run_id}/sell/listing-decision")
async def run_sell_listing_decision(
    run_id: str,
    request: RunSellListingDecisionRequest,
    _owned: str = Depends(_require_run_ownership),
) -> SellListingDecisionResponse:
    return await sell_listing_decision(
        SellListingDecisionRequest(
            session_id=run_id,
            decision=request.decision,
            revision_instructions=request.revision_instructions,
        )
    )


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


async def iter_run_events(run_id: str):
    from backend.orchestrator import expire_sell_listing_review_if_needed

    persisted_run = await get_persisted_run_record(run_id)
    session_id = str(persisted_run.get("session_id")) if persisted_run is not None and persisted_run.get("session_id") else run_id
    live_session = await session_manager.get_session(session_id)
    queue = None
    emitted: set[tuple[str, str, str | None, str, str]] = set()

    if live_session is not None:
        queue = await session_manager.subscribe(session_id)

    try:
        pipeline = (
            str(persisted_run.get("pipeline"))
            if persisted_run is not None and persisted_run.get("pipeline") is not None
            else (live_session.pipeline if live_session is not None else None)
        )
        for event in await list_persisted_run_events(run_id, session_id=session_id, pipeline=pipeline):
            emitted.add(event_identity(event))
            yield format_sse(event)
            if event.event_type in {"pipeline_complete", "pipeline_failed"}:
                return

        if live_session is None:
            return

        for event in live_session.events:
            identity = event_identity(event)
            if identity in emitted:
                continue
            emitted.add(identity)
            yield format_sse(event)
            if event.event_type in {"pipeline_complete", "pipeline_failed"}:
                return

        while True:
            try:
                await expire_sell_listing_review_if_needed(session_id)
                event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_INTERVAL)
                identity = event_identity(event)
                if identity in emitted:
                    continue
                emitted.add(identity)
                yield format_sse(event)
                if event.event_type in {"pipeline_complete", "pipeline_failed"}:
                    break
            except asyncio.TimeoutError:
                yield ": ping\n\n"
    finally:
        if queue is not None:
            await session_manager.unsubscribe(session_id, queue)


def format_sse(event: SessionEvent) -> str:
    return f"event: {event.event_type}\ndata: {json.dumps(event.model_dump())}\n\n"
