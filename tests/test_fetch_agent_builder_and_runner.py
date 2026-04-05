from __future__ import annotations

import os
import signal
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from backend import run_fetch_agents
from backend.fetch_agents import builder, launch


class FakeChatAcknowledgement:
    def __init__(self, *, timestamp: object, acknowledged_msg_id: object) -> None:
        self.timestamp = timestamp
        self.acknowledged_msg_id = acknowledged_msg_id


class FakeTextContent:
    def __init__(self, *, type: str, text: str) -> None:
        self.type = type
        self.text = text


class FakeEndSessionContent:
    def __init__(self, *, type: str) -> None:
        self.type = type


class FakeChatMessage:
    def __init__(self, *, timestamp: object | None = None, msg_id: object | None = None, content: list[object] | None = None) -> None:
        self.timestamp = timestamp
        self.msg_id = msg_id
        self.content = content or []


class FakeProtocol:
    def __init__(self, *, spec: object) -> None:
        self.spec = spec
        self.handlers: dict[object, Any] = {}

    def on_message(self, message_type: object):
        def decorator(fn):
            self.handlers[message_type] = fn
            return fn

        return decorator


class FakeAgent:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.included: list[tuple[object, bool]] = []
        self.ran = False

    def include(self, protocol: object, publish_manifest: bool = False) -> None:
        self.included.append((protocol, publish_manifest))

    def run(self) -> None:
        self.ran = True


def fake_uagents_tuple() -> tuple[object, ...]:
    return (
        FakeAgent,
        object,
        FakeProtocol,
        FakeChatAcknowledgement,
        FakeChatMessage,
        FakeEndSessionContent,
        FakeTextContent,
        "fake-chat-spec",
    )


def test_build_fetch_agent_requires_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "_import_uagents", fake_uagents_tuple)
    monkeypatch.delenv("VISION_FETCH_AGENT_SEED", raising=False)

    with pytest.raises(RuntimeError, match="Missing VISION_FETCH_AGENT_SEED"):
        builder.build_fetch_agent("vision_agent")


def test_build_fetch_agent_sets_mailbox_and_optional_local_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "_import_uagents", fake_uagents_tuple)
    monkeypatch.setenv("DEPOP_SEARCH_FETCH_AGENT_SEED", "seed-depop-search")
    monkeypatch.setenv("FETCH_USE_LOCAL_ENDPOINT", "true")

    agent = builder.build_fetch_agent("depop_search_agent")

    assert isinstance(agent, FakeAgent)
    assert agent.kwargs == {
        "name": "DepopSearchAgent",
        "seed": "seed-depop-search",
        "port": 9205,
        "mailbox": True,
        "publish_agent_details": True,
        "endpoint": ["http://127.0.0.1:9205/submit"],
    }
    assert len(agent.included) == 1
    protocol, publish_manifest = agent.included[0]
    assert isinstance(protocol, FakeProtocol)
    assert protocol.spec == "fake-chat-spec"
    assert publish_manifest is True


@pytest.mark.asyncio
async def test_build_fetch_agent_chat_handler_acknowledges_executes_and_ends_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "_import_uagents", fake_uagents_tuple)
    monkeypatch.setenv("VISION_FETCH_AGENT_SEED", "seed-vision")

    async def fake_run_fetch_query(agent_slug: str, user_text: str) -> dict[str, object]:
        assert agent_slug == "vision_agent"
        assert user_text == "Vintage Nike tee"
        return {
            "agent": "vision_agent",
            "summary": "Vision agent completed",
            "brand": "Nike",
        }

    monkeypatch.setattr(builder, "run_fetch_query", fake_run_fetch_query)

    agent = builder.build_fetch_agent("vision_agent")
    protocol, _ = agent.included[0]

    sent_messages: list[tuple[str, object]] = []

    class FakeLogger:
        def exception(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("chat handler should not log an exception in the success path")

        def debug(self, *args: object, **kwargs: object) -> None:
            return None

    class FakeContext:
        logger = FakeLogger()

        async def send(self, sender: str, message: object) -> None:
            sent_messages.append((sender, message))

    handler = protocol.handlers[FakeChatMessage]
    incoming = FakeChatMessage(
        msg_id="incoming-message-id",
        content=[FakeTextContent(type="text", text="Vintage"), FakeTextContent(type="text", text="Nike tee")],
    )

    await handler(FakeContext(), "buyer-address", incoming)

    assert len(sent_messages) == 2
    assert sent_messages[0][0] == "buyer-address"
    assert isinstance(sent_messages[0][1], FakeChatAcknowledgement)
    assert sent_messages[0][1].acknowledged_msg_id == "incoming-message-id"

    assert sent_messages[1][0] == "buyer-address"
    response = sent_messages[1][1]
    assert isinstance(response, FakeChatMessage)
    assert len(response.content) == 2
    assert isinstance(response.content[0], FakeTextContent)
    assert "Summary: Vision agent completed" in response.content[0].text
    assert isinstance(response.content[1], FakeEndSessionContent)
    assert response.content[1].type == "end-session"


def test_launch_main_handles_usage_and_build_errors(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = launch.main(["python", "-m", "backend.fetch_agents.launch"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Usage: python -m backend.fetch_agents.launch <agent-slug>" in captured.out

    monkeypatch.setattr(launch, "build_fetch_agent", lambda slug: (_ for _ in ()).throw(RuntimeError("bad seed")))
    exit_code = launch.main(["python", "vision_agent"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out.strip() == "bad seed"


def test_launch_main_runs_built_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_agent = FakeAgent(name="VisionAgent", seed="seed", port=9201, mailbox=True, publish_agent_details=True)
    monkeypatch.setattr(launch, "build_fetch_agent", lambda slug: fake_agent)

    exit_code = launch.main(["python", "vision_agent"])

    assert exit_code == 0
    assert fake_agent.ran is True


def test_run_fetch_agents_spawns_every_slug_and_terminates_children(monkeypatch: pytest.MonkeyPatch) -> None:
    spawned: list[dict[str, object]] = []
    signals_sent: list[tuple[str, object]] = []
    waits: list[str] = []

    class FakeProcess:
        def __init__(self, slug: str) -> None:
            self.slug = slug

        def poll(self) -> None:
            return None

        def send_signal(self, sig: object) -> None:
            signals_sent.append((self.slug, sig))

        def wait(self, timeout: float) -> None:
            waits.append(self.slug)

    def fake_popen(command: list[str], env: dict[str, str]) -> FakeProcess:
        slug = command[-1]
        spawned.append({"command": command, "env": env, "slug": slug})
        return FakeProcess(slug)

    sleep_calls = {"count": 0}

    def fake_sleep(seconds: float) -> None:
        sleep_calls["count"] += 1
        if seconds == 1 and sleep_calls["count"] > len(run_fetch_agents.list_fetch_agent_slugs()):
            raise KeyboardInterrupt()

    monkeypatch.setattr(run_fetch_agents.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(run_fetch_agents.time, "sleep", fake_sleep)

    exit_code = run_fetch_agents.main()

    assert exit_code == 0
    assert [item["slug"] for item in spawned] == run_fetch_agents.list_fetch_agent_slugs()
    assert spawned[0]["command"] == [
        sys.executable,
        "-m",
        "backend.fetch_agents.launch",
        run_fetch_agents.list_fetch_agent_slugs()[0],
    ]
    assert all(item["env"]["PYTHONPATH"] == os.getcwd() for item in spawned)
    assert len(signals_sent) == len(spawned)
    assert all(sig == signal.SIGTERM for _, sig in signals_sent)
    assert waits == run_fetch_agents.list_fetch_agent_slugs()

