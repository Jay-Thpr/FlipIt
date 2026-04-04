from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import AGENTS, APP_BASE_URL, INTERNAL_API_TOKEN, get_agent_execution_mode
from backend.orchestrator import get_pipeline_steps, run_pipeline
from backend.schemas import (
    InternalEventRequest,
    PipelineStartRequest,
    PipelineStartResponse,
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


@app.get("/pipelines")
async def list_pipelines() -> dict[str, list[dict[str, str]]]:
    return get_pipeline_steps()


@app.post("/sell/start", response_model=PipelineStartResponse)
async def start_sell(request: PipelineStartRequest) -> PipelineStartResponse:
    return await start_session("sell", request)


@app.post("/buy/start", response_model=PipelineStartResponse)
async def start_buy(request: PipelineStartRequest) -> PipelineStartResponse:
    return await start_session("buy", request)


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

    async def event_generator():
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def format_sse(event: SessionEvent) -> str:
    return f"event: {event.event_type}\ndata: {json.dumps(event.model_dump())}\n\n"
