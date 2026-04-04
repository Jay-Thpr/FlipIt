from __future__ import annotations

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend import orchestrator
from backend.schemas import (
    AgentTaskResponse,
    DepopListingOutput,
    EbaySoldCompsOutput,
    NegotiationOutput,
    PricingOutput,
    RankingOutput,
    SearchResultsOutput,
    VisionAnalysisOutput,
)


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
            "input": {"image_urls": ["https://example.com/item.jpg"], "notes": "Vintage tee"},
            "metadata": {"source": "test"},
        },
    )

    assert [event["event_type"] for event in events] == [
        "pipeline.started",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "pipeline.completed",
    ]
    assert [event["payload"]["step"] for event in events if event["payload"]["step"]] == [
        "vision_analysis",
        "vision_analysis",
        "ebay_sold_comps",
        "ebay_sold_comps",
        "pricing",
        "pricing",
        "depop_listing",
        "depop_listing",
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

    assert [event["event_type"] for event in events] == [
        "pipeline.started",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "agent.started",
        "agent.completed",
        "pipeline.completed",
    ]
    assert [event["payload"]["step"] for event in events if event["payload"]["step"]] == [
        "depop_search",
        "depop_search",
        "ebay_search",
        "ebay_search",
        "mercari_search",
        "mercari_search",
        "offerup_search",
        "offerup_search",
        "ranking",
        "ranking",
        "negotiation",
        "negotiation",
    ]
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
    assert result["result"]["outputs"]["negotiation"]["offer_messages"][0]["target_price"] == 32.0


def test_internal_event_requires_valid_token(client: TestClient) -> None:
    start_response = client.post("/sell/start", json={"input": {}, "metadata": {}})
    session_id = start_response.json()["session_id"]
    wait_for_terminal_result(client, session_id)

    response = client.post(
        f"/internal/event/{session_id}",
        json={"event_type": "custom.event", "data": {"hello": "world"}},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid internal token"}


def test_internal_event_is_appended_to_session_history(client: TestClient) -> None:
    start_response = client.post("/sell/start", json={"input": {}, "metadata": {}})
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
    assert session.events[-1].event_type == "pipeline.failed"


@pytest.mark.asyncio
async def test_invalid_agent_output_marks_session_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_agent_task(agent_slug: str, request: Any) -> AgentTaskResponse:
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
    assert session.events[-1].event_type == "pipeline.failed"
