from __future__ import annotations

import httpx

from backend.config import AGENT_HOST, AGENT_PORTS, get_agent_execution_mode
from backend.schemas import AgentTaskRequest, AgentTaskResponse


async def run_agent_task(agent_slug: str, request: AgentTaskRequest) -> AgentTaskResponse:
    if get_agent_execution_mode() == "local_functions":
        from backend.agents.registry import run_local_agent_task

        return await run_local_agent_task(agent_slug, request)

    if agent_slug not in AGENT_PORTS:
        raise ValueError(f"Unknown agent slug: {agent_slug}")

    port = AGENT_PORTS[agent_slug]
    url = f"http://{AGENT_HOST}:{port}/task"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=request.model_dump())
        response.raise_for_status()
        return AgentTaskResponse.model_validate(response.json())
