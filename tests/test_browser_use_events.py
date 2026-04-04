from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.agents import browser_use_events
from backend.schemas import PipelineStartRequest
from backend.session import session_manager


@pytest.mark.asyncio
async def test_emit_browser_use_event_appends_to_session_in_local_functions_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = "browser-use-event-local"
    await session_manager.create_session(
        session_id=session_id,
        pipeline="buy",
        request=PipelineStartRequest(input={}, metadata={}),
    )
    monkeypatch.setenv("AGENT_EXECUTION_MODE", "local_functions")

    await browser_use_events.emit_browser_use_event(
        session_id=session_id,
        pipeline="buy",
        step="depop_search",
        event_type="listing_found",
        data={"title": "Demo listing", "platform": "depop"},
    )

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.events[-1].event_type == "listing_found"
    assert session.events[-1].data == {"title": "Demo listing", "platform": "depop"}


@pytest.mark.asyncio
async def test_emit_browser_use_event_posts_to_internal_endpoint_in_local_http_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeAsyncClient:
        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]) -> None:
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers

    monkeypatch.setenv("AGENT_EXECUTION_MODE", "local_http")
    monkeypatch.setattr(browser_use_events.httpx, "AsyncClient", lambda timeout: FakeAsyncClient())

    await browser_use_events.emit_browser_use_event(
        session_id="browser-use-event-http",
        pipeline="buy",
        step="negotiation",
        event_type="offer_sent",
        data={"listing_url": "https://example.com/listing"},
    )

    assert captured["url"].endswith("/internal/event/browser-use-event-http")
    assert captured["json"] == {
        "event_type": "offer_sent",
        "data": {"listing_url": "https://example.com/listing"},
    }
    assert captured["headers"]["x-internal-token"]
