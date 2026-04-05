from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import AGENTS, INTERNAL_API_TOKEN, get_agent_execution_mode, get_public_app_base_url
from backend.item_schemas import Conversation, Item, ItemCreateRequest, ItemCreateResponse
from backend.item_store import item_store
from backend.orchestrator import get_pipeline_steps, resume_sell_pipeline, run_pipeline
from backend.schemas import (
    InternalEventRequest,
    PipelineStartRequest,
    PipelineStartResponse,
    SellCorrectionRequest,
    SessionEvent,
)
from backend.session import session_manager

app = FastAPI(title="DiamondHacks Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

KEEPALIVE_INTERVAL = 15.0


def get_request_base_url(request: Request) -> str:
    configured_public_base_url = get_public_app_base_url()
    if configured_public_base_url:
        return configured_public_base_url
    return str(request.base_url).rstrip("/")


async def start_session(
    pipeline: str,
    request: PipelineStartRequest,
    http_request: Request,
) -> PipelineStartResponse:
    base_url = get_request_base_url(http_request)
    response = PipelineStartResponse(
        pipeline=pipeline,
        status="queued",
        stream_url=f"{base_url}/stream",
        result_url=f"{base_url}/result",
    )
    await session_manager.create_session(session_id=response.session_id, pipeline=pipeline, request=request)
    asyncio.create_task(run_pipeline(response.session_id, pipeline, request))
    return response.model_copy(
        update={
            "stream_url": f"{base_url}/stream/{response.session_id}",
            "result_url": f"{base_url}/result/{response.session_id}",
        }
    )


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "agent_execution_mode": get_agent_execution_mode(),
        "agent_count": str(len(AGENTS)),
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


@app.get("/items", response_model=list[Item])
async def list_items(type: str | None = None) -> list[Item]:
    return item_store.list_items(item_type=type)


@app.post("/items", response_model=ItemCreateResponse, status_code=201)
async def create_item(request: ItemCreateRequest) -> ItemCreateResponse:
    return ItemCreateResponse(**item_store.create_item(request).model_dump())


@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: str) -> Item:
    item = item_store.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/items/{item_id}/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(item_id: str, conversation_id: str) -> Conversation:
    conversation = item_store.get_conversation(item_id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/pipelines")
async def list_pipelines() -> dict[str, list[dict[str, str]]]:
    return get_pipeline_steps()


@app.post("/sell/start", response_model=PipelineStartResponse)
async def start_sell(request: PipelineStartRequest, http_request: Request) -> PipelineStartResponse:
    return await start_session("sell", request, http_request)


@app.post("/buy/start", response_model=PipelineStartResponse)
async def start_buy(request: PipelineStartRequest, http_request: Request) -> PipelineStartResponse:
    return await start_session("buy", request, http_request)


@app.post("/sell/correct")
async def sell_correct(request: SellCorrectionRequest) -> dict[str, bool]:
    session = await session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.pipeline != "sell":
        raise HTTPException(status_code=400, detail="Only sell sessions can be corrected")
    if session.status != "awaiting_input":
        raise HTTPException(status_code=409, detail="Sell session is not waiting for correction")

    asyncio.create_task(resume_sell_pipeline(request.session_id, request.corrected_item))
    return {"ok": True}


@app.get("/result/{session_id}")
async def get_result(session_id: str) -> dict:
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
    session = await session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(iter_session_events(session_id), media_type="text/event-stream")


async def iter_session_events(session_id: str):
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
