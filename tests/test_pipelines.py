from __future__ import annotations

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend import main, orchestrator
from backend.schemas import (
    AgentTaskResponse,
    DepopListingOutput,
    EbaySoldCompsOutput,
    NegotiationOutput,
    PricingOutput,
    RankingOutput,
    SearchResultsOutput,
    SessionEvent,
    VisionAnalysisOutput,
)
from backend.session import session_manager


def wait_for_terminal_result(client: TestClient, session_id: str, timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach a terminal state")


def parse_sse_events(response_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for chunk in response_text.strip().split("\n\n"):
        if not chunk:
            continue
        lines = chunk.splitlines()
        event_type = lines[0].removeprefix("event: ").strip()
        data = json.loads(lines[1].removeprefix("data: ").strip())
        events.append({"event_type": event_type, "payload": data})
    return events


def lifecycle_event_types(events: list[dict[str, Any]]) -> list[str]:
    return [
        event["event_type"]
        for event in events
        if event["event_type"]
        in {
            "pipeline_started",
            "agent_started",
            "agent_completed",
            "agent_error",
            "agent_retrying",
            "pipeline_complete",
            "pipeline_failed",
        }
    ]


def step_event_types(events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [
        (event["event_type"], event["payload"]["step"])
        for event in events
        if event["payload"]["step"]
        and event["event_type"] in {"agent_started", "agent_completed", "draft_created", "listing_found", "offer_prepared"}
    ]


def start_and_collect_events(client: TestClient, endpoint: str, payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    response = client.post(endpoint, json=payload)
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    terminal_result = wait_for_terminal_result(client, session_id)
    stream_response = client.get(f"/stream/{session_id}")
    assert stream_response.status_code == 200
    return session_id, parse_sse_events(stream_response.text), terminal_result


def test_sell_pipeline_emits_expected_event_order_and_result(client: TestClient) -> None:
    session_id, events, result = start_and_collect_events(
        client,
        "/sell/start",
        {
            "user_id": "sell-user",
            "input": {"image_urls": ["https://example.com/item.jpg"], "notes": "Vintage Nike tee"},
            "metadata": {"source": "test"},
        },
    )

    assert lifecycle_event_types(events) == [
        "pipeline_started",
        "agent_started",
        "agent_completed",
        "agent_started",
        "agent_completed",
        "agent_started",
        "agent_completed",
        "agent_started",
        "agent_completed",
        "pipeline_complete",
    ]
    draft_events = [event for event in events if event["event_type"] == "draft_created"]
    assert [event["event_type"] for event in draft_events] == ["draft_created"]
    assert draft_events[0]["payload"]["data"]["platform"] == "depop"
    assert draft_events[0]["payload"]["data"]["draft_status"] == "fallback"
    assert draft_events[0]["payload"]["data"]["ready_for_confirmation"] is False
    fallback_events = [event for event in events if event["event_type"] == "browser_use_fallback"]
    assert len(fallback_events) == 2
    assert not any(event["event_type"] == "listing_review_required" for event in events)
    assert step_event_types(events) == [
        ("agent_started", "vision_analysis"),
        ("agent_completed", "vision_analysis"),
        ("agent_started", "ebay_sold_comps"),
        ("agent_completed", "ebay_sold_comps"),
        ("agent_started", "pricing"),
        ("agent_completed", "pricing"),
        ("agent_started", "depop_listing"),
        ("draft_created", "depop_listing"),
        ("agent_completed", "depop_listing"),
    ]
    assert all(event["payload"]["session_id"] == session_id for event in events)
    assert result["status"] == "completed"
    assert result["result"]["pipeline"] == "sell"
    assert set(result["result"]["outputs"]) == {
        "vision_analysis",
        "ebay_sold_comps",
        "pricing",
        "depop_listing",
    }
    VisionAnalysisOutput.model_validate(result["result"]["outputs"]["vision_analysis"])
    EbaySoldCompsOutput.model_validate(result["result"]["outputs"]["ebay_sold_comps"])
    PricingOutput.model_validate(result["result"]["outputs"]["pricing"])
    DepopListingOutput.model_validate(result["result"]["outputs"]["depop_listing"])
    assert result["result"]["outputs"]["depop_listing"]["category_path"] == "Men/Tops/T-Shirts"


def test_sell_pipeline_generates_real_listing_outputs(client: TestClient) -> None:
    _, _, result = start_and_collect_events(
        client,
        "/sell/start",
        {
            "user_id": "sell-user",
            "input": {
                "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                "notes": "Patagonia hoodie in excellent condition",
            },
            "metadata": {"source": "sell-listing-output-test"},
        },
    )

    depop_listing = result["result"]["outputs"]["depop_listing"]
    assert depop_listing["title"] == "Patagonia hoodie - Excellent Condition"
    assert depop_listing["suggested_price"] == 78.43
    assert depop_listing["category_path"] == "Men/Tops/Hoodies"
    assert "Recent eBay sold range: $55.11-$86.21 across 11 comps." in depop_listing["description"]


def test_buy_pipeline_emits_expected_event_order_and_result(client: TestClient) -> None:
    session_id, events, result = start_and_collect_events(
        client,
        "/buy/start",
        {
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "test"},
        },
    )

    lifecycle = lifecycle_event_types(events)
    assert lifecycle[0] == "pipeline_started"
    assert lifecycle[-1] == "pipeline_complete"
    assert lifecycle.count("agent_started") == 6
    assert lifecycle.count("agent_completed") == 6

    search_steps = {"depop_search", "ebay_search", "mercari_search", "offerup_search"}
    started_steps = [
        e["payload"]["step"]
        for e in events
        if e["event_type"] == "agent_started" and e["payload"].get("step") in search_steps
    ]
    assert set(started_steps) == search_steps

    def last_index(ev_type: str, step: str) -> int:
        return max(i for i, e in enumerate(events) if e["event_type"] == ev_type and e["payload"].get("step") == step)

    def first_index(ev_type: str, step: str) -> int:
        return next(i for i, e in enumerate(events) if e["event_type"] == ev_type and e["payload"].get("step") == step)

    last_search_done = max(last_index("agent_completed", s) for s in search_steps)
    assert last_search_done < first_index("agent_started", "ranking")
    assert last_index("agent_completed", "ranking") < first_index("agent_started", "negotiation")

    listing_events = [event for event in events if event["event_type"] == "listing_found"]
    prepared_offer_events = [event for event in events if event["event_type"] == "offer_prepared"]
    assert len(listing_events) == 8
    assert len(prepared_offer_events) == 3
    depop_listings = [e for e in listing_events if e["payload"]["data"]["platform"] == "depop"]
    assert depop_listings
    assert depop_listings[0]["payload"]["data"]["source"] == "fallback"
    assert prepared_offer_events[0]["payload"]["data"]["seller"] == "nike_seller_1"
    fallback_events = [event for event in events if event["event_type"] == "browser_use_fallback"]
    assert len(fallback_events) == 7
    assert all(event["payload"]["session_id"] == session_id for event in events)
    assert result["status"] == "completed"
    assert result["result"]["pipeline"] == "buy"
    assert set(result["result"]["outputs"]) == {
        "depop_search",
        "ebay_search",
        "mercari_search",
        "offerup_search",
        "ranking",
        "negotiation",
    }
    SearchResultsOutput.model_validate(result["result"]["outputs"]["depop_search"])
    SearchResultsOutput.model_validate(result["result"]["outputs"]["ebay_search"])
    SearchResultsOutput.model_validate(result["result"]["outputs"]["mercari_search"])
    SearchResultsOutput.model_validate(result["result"]["outputs"]["offerup_search"])
    RankingOutput.model_validate(result["result"]["outputs"]["ranking"])
    NegotiationOutput.model_validate(result["result"]["outputs"]["negotiation"])
    assert result["result"]["outputs"]["ranking"]["top_choice"]["reason"]
    assert result["result"]["outputs"]["ranking"]["top_choice"]["platform"] == "ebay"
    assert result["result"]["outputs"]["negotiation"]["offers"][0]["target_price"] == 45.35


def test_internal_event_requires_valid_token(client: TestClient) -> None:
    start_response = client.post(
        "/sell/start",
        json={"input": {"notes": "Nike hoodie good"}, "metadata": {}},
    )
    session_id = start_response.json()["session_id"]
    wait_for_terminal_result(client, session_id)

    response = client.post(
        f"/internal/event/{session_id}",
        json={"event_type": "custom.event", "data": {"hello": "world"}},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid internal token"}


def test_internal_event_is_appended_to_session_history(client: TestClient) -> None:
    start_response = client.post(
        "/sell/start",
        json={"input": {"notes": "Nike hoodie good"}, "metadata": {}},
    )
    session_id = start_response.json()["session_id"]
    wait_for_terminal_result(client, session_id)

    response = client.post(
        f"/internal/event/{session_id}",
        headers={"x-internal-token": "dev-internal-token"},
        json={"event_type": "custom.event", "data": {"hello": "world"}},
    )

    assert response.status_code == 200
    result = client.get(f"/result/{session_id}")
    events = result.json()["events"]
    assert events[-1]["event_type"] == "custom.event"
    assert events[-1]["data"] == {"hello": "world"}


def test_stream_emits_keepalive_ping_before_terminal_event(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = "keepalive-session"

    async def seed_session() -> None:
        from backend.schemas import PipelineStartRequest

        await session_manager.create_session(
            session_id=session_id,
            pipeline="sell",
            request=PipelineStartRequest(input={}, metadata={}),
        )

    import asyncio

    asyncio.run(seed_session())

    queue: asyncio.Queue[SessionEvent] = asyncio.Queue()
    queue.put_nowait(
        SessionEvent(
            session_id=session_id,
            pipeline="sell",
            event_type="pipeline_complete",
            data={"done": True},
        )
    )

    async def fake_subscribe(requested_session_id: str) -> asyncio.Queue[SessionEvent]:
        assert requested_session_id == session_id
        return queue

    call_count = {"value": 0}
    original_wait_for = main.asyncio.wait_for

    async def fake_wait_for(awaitable: Any, timeout: float) -> Any:
        call_count["value"] += 1
        if call_count["value"] == 1:
            awaitable.close()
            raise asyncio.TimeoutError
        return await original_wait_for(awaitable, timeout=timeout)

    monkeypatch.setattr(main, "KEEPALIVE_INTERVAL", 0.01)
    monkeypatch.setattr(session_manager, "subscribe", fake_subscribe)
    monkeypatch.setattr(main.asyncio, "wait_for", fake_wait_for)

    response = client.get(f"/stream/{session_id}")

    assert response.status_code == 200
    assert ": ping" in response.text
    assert "event: pipeline_complete" in response.text


@pytest.mark.asyncio
async def test_failed_agent_marks_session_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_agent_task(agent_slug: str, request: Any) -> AgentTaskResponse:
        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="failed",
            error=f"{agent_slug} broke",
            output={},
        )

    monkeypatch.setattr(orchestrator, "run_agent_task", fake_run_agent_task)

    from backend.schemas import PipelineStartRequest
    from backend.session import session_manager

    session_id = "failed-session"
    await session_manager.create_session(
        session_id=session_id,
        pipeline="sell",
        request=PipelineStartRequest(input={}, metadata={}),
    )

    await orchestrator.run_pipeline(session_id, "sell", PipelineStartRequest(input={}, metadata={}))

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.status == "failed"
    assert session.error == "vision_agent broke"
    assert session.result == {"pipeline": "sell", "outputs": {}}
    assert session.events[-2].event_type == "agent_error"
    assert session.events[-1].event_type == "pipeline_failed"


@pytest.mark.asyncio
async def test_invalid_agent_output_marks_session_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_agent_task(agent_slug: str, request: Any) -> AgentTaskResponse:
        if agent_slug in {
            "depop_search_agent",
            "ebay_search_agent",
            "mercari_search_agent",
            "offerup_search_agent",
        }:
            results = []
            if agent_slug == "ebay_search_agent":
                results = [
                    {
                        "platform": "ebay",
                        "title": "One valid listing",
                        "price": 40.0,
                        "url": "https://ebay.example/item",
                        "condition": "good",
                        "seller": "seller",
                        "seller_score": 100,
                        "posted_at": "2026-04-04",
                    }
                ]
            return AgentTaskResponse(
                session_id=request.session_id,
                step=request.step,
                status="completed",
                output={
                    "agent": agent_slug,
                    "display_name": "Broken Search Agent",
                    "summary": "Search payload",
                    "results": results,
                    "execution_mode": "fallback",
                    "browser_use_error": None,
                    "browser_use": None,
                },
            )
        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="completed",
            output={"agent": agent_slug, "display_name": "Broken Agent", "summary": "bad payload"},
        )

    monkeypatch.setattr(orchestrator, "run_agent_task", fake_run_agent_task)

    from backend.schemas import PipelineStartRequest
    from backend.session import session_manager

    session_id = "invalid-output-session"
    await session_manager.create_session(
        session_id=session_id,
        pipeline="buy",
        request=PipelineStartRequest(input={}, metadata={}),
    )

    await orchestrator.run_pipeline(session_id, "buy", PipelineStartRequest(input={}, metadata={}))

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.status == "failed"
    assert "validation" in session.error.lower()
    assert session.events[-2].event_type == "agent_error"
    assert session.events[-1].event_type == "pipeline_failed"
