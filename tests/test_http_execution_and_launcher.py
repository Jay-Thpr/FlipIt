from __future__ import annotations

import sys

import pytest

from backend import run_agents
from backend.agent_client import run_agent_task
from backend.schemas import AgentTaskRequest


@pytest.mark.asyncio
async def test_http_agent_execution_mode_posts_to_agent_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "session_id": "http-mode-session",
                "step": "vision_analysis",
                "status": "completed",
                "output": {"agent": "vision_agent", "transport": "http"},
                "error": None,
            }

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setenv("AGENT_EXECUTION_MODE", "http")
    monkeypatch.setattr("backend.agent_client.httpx.AsyncClient", FakeAsyncClient)

    request = AgentTaskRequest(
        session_id="http-mode-session",
        pipeline="sell",
        step="vision_analysis",
        input={"image_urls": ["https://example.com/item.jpg"]},
    )

    response = await run_agent_task("vision_agent", request)

    assert captured == {
        "timeout": 60.0,
        "url": "http://127.0.0.1:9101/task",
        "json": request.model_dump(),
    }
    assert response.output == {"agent": "vision_agent", "transport": "http"}


def test_run_agents_spawns_expected_commands_and_stops_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    spawned: list[dict[str, object]] = []
    signal_log: list[tuple[str, object]] = []
    wait_log: list[str] = []

    class FakeProcess:
        def __init__(self, slug: str) -> None:
            self.slug = slug

        def poll(self) -> None:
            return None

        def send_signal(self, sig: object) -> None:
            signal_log.append((self.slug, sig))

        def wait(self, timeout: float) -> None:
            wait_log.append(self.slug)

    def fake_popen(command: list[str], env: dict[str, str]) -> FakeProcess:
        slug = command[3].split(".")[-1].split(":")[0]
        spawned.append({"command": command, "env": env, "slug": slug})
        return FakeProcess(slug)

    sleep_calls = {"count": 0}

    def fake_sleep(seconds: float) -> None:
        sleep_calls["count"] += 1
        if seconds == 1 and sleep_calls["count"] > len(run_agents.AGENTS):
            raise KeyboardInterrupt()

    monkeypatch.setattr(run_agents.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(run_agents.time, "sleep", fake_sleep)

    exit_code = run_agents.main()

    assert exit_code == 0
    assert len(spawned) == len(run_agents.AGENTS)
    assert spawned[0]["command"] == [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.agents.vision_agent:app",
        "--host",
        "0.0.0.0",
        "--port",
        "9101",
    ]
    assert spawned[-1]["command"][3] == "backend.agents.negotiation_agent:app"
    assert all("PYTHONPATH" in item["env"] for item in spawned)
    assert len(signal_log) == len(run_agents.AGENTS)
    assert len(wait_log) == len(run_agents.AGENTS)
