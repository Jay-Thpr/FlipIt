from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import orchestrator
from backend.agent_client import run_agent_task
from backend.schemas import (
    AgentTaskRequest,
    AgentTaskResponse,
    DepopListingOutput,
    EbaySoldCompsOutput,
    PipelineStartRequest,
    PricingOutput,
    SearchResultsOutput,
    VisionAnalysisOutput,
    validate_agent_output,
    validate_agent_task_request,
)
from backend.fetch_runtime import FETCH_AGENT_SPECS
from backend.session import session_manager


def test_healthcheck_exposes_execution_metadata(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "agent_execution_mode": "local_functions",
        "agent_count": "10",
        "fetch_enabled": False,
        "agentverse_credentials_present": False,
    }


def test_agents_manifest_lists_all_agents(client: TestClient) -> None:
    response = client.get("/agents")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["agents"]) == 10
    assert payload["agents"][0] == {
        "name": "Vision Agent",
        "slug": "vision_agent",
        "port": 9101,
    }
    assert payload["agents"][-1] == {
        "name": "Negotiation Agent",
        "slug": "negotiation_agent",
        "port": 9110,
    }


def test_fetch_agents_manifest_lists_all_fetch_agents(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for spec in FETCH_AGENT_SPECS.values():
        monkeypatch.delenv(spec.agentverse_address_env_var, raising=False)
    monkeypatch.setenv("VISION_AGENT_AGENTVERSE_ADDRESS", "agent1qvisiondemo")
    response = client.get("/fetch-agents")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["agents"]) == 10
    assert payload["agents"][0] == {
        "name": "VisionAgent",
        "slug": "vision_agent",
        "port": 9201,
        "agentverse_address": "agent1qvisiondemo",
        "description": "Identifies a resale item from text or image URLs and summarizes its brand, category, and condition.",
    }
    assert payload["agents"][-1] == {
        "name": "NegotiationAgent",
        "slug": "negotiation_agent",
        "port": 9210,
        "agentverse_address": None,
        "description": "Runs the BUY flow through negotiation and returns prepared or sent offers.",
    }


def test_pipelines_manifest_matches_step_contracts(client: TestClient) -> None:
    response = client.get("/pipelines")

    assert response.status_code == 200
    assert response.json() == {
        "sell": [
            {"agent": "vision_agent", "step": "vision_analysis"},
            {"agent": "ebay_sold_comps_agent", "step": "ebay_sold_comps"},
            {"agent": "pricing_agent", "step": "pricing"},
            {"agent": "depop_listing_agent", "step": "depop_listing"},
        ],
        "buy": [
            {"agent": "depop_search_agent", "step": "depop_search"},
            {"agent": "ebay_search_agent", "step": "ebay_search"},
            {"agent": "mercari_search_agent", "step": "mercari_search"},
            {"agent": "offerup_search_agent", "step": "offerup_search"},
            {"agent": "ranking_agent", "step": "ranking"},
            {"agent": "negotiation_agent", "step": "negotiation"},
        ],
    }


def test_start_rejects_invalid_request_shape(client: TestClient) -> None:
    response = client.post("/sell/start", json={"input": ["not", "a", "dict"], "metadata": {}})

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"][0]["loc"] == ["body", "input"]


def test_internal_event_unknown_session_returns_404(client: TestClient) -> None:
    response = client.post(
        "/internal/event/not-a-real-session",
        headers={"x-internal-token": "dev-internal-token"},
        json={"event_type": "custom.event", "data": {"hello": "world"}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


@pytest.mark.asyncio
async def test_pipeline_passes_accumulated_outputs_to_each_step(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_requests: list[AgentTaskRequest] = []
    valid_outputs = {
        "vision_agent": VisionAnalysisOutput(
            agent="vision_agent",
            display_name="Vision Agent",
            summary="Vision Agent completed vision_analysis",
            detected_item="sample item",
            brand="unknown",
            category="apparel",
            condition="good",
            confidence=0.85,
        ).model_dump(),
        "ebay_sold_comps_agent": EbaySoldCompsOutput(
            agent="ebay_sold_comps_agent",
            display_name="eBay Sold Comps Agent",
            summary="eBay Sold Comps Agent completed ebay_sold_comps",
            median_sold_price=42.0,
            low_sold_price=28.0,
            high_sold_price=58.0,
            sample_size=12,
        ).model_dump(),
        "pricing_agent": PricingOutput(
            agent="pricing_agent",
            display_name="Pricing Agent",
            summary="Pricing Agent completed pricing",
            recommended_list_price=55.0,
            expected_profit=23.0,
            pricing_confidence=0.82,
        ).model_dump(),
        "depop_listing_agent": DepopListingOutput(
            agent="depop_listing_agent",
            display_name="Depop Listing Agent",
            summary="Depop Listing Agent completed depop_listing",
            title="Sample Depop Listing",
            description="Stub listing generated for scaffold.",
            suggested_price=55.0,
            category_path="Men/Tops/T-Shirts",
        ).model_dump(),
    }

    async def fake_run_agent_task(agent_slug: str, request: AgentTaskRequest) -> AgentTaskResponse:
        captured_requests.append(request)
        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="completed",
            output=valid_outputs[agent_slug],
        )

    monkeypatch.setattr(orchestrator, "run_agent_task", fake_run_agent_task)

    request = PipelineStartRequest(
        user_id="sell-user",
        input={"image_urls": ["https://example.com/item.jpg"]},
        metadata={"source": "test"},
    )
    session_id = "context-chain-session"
    await session_manager.create_session(session_id=session_id, pipeline="sell", request=request)

    await orchestrator.run_pipeline(session_id, "sell", request)

    assert [task.step for task in captured_requests] == [
        "vision_analysis",
        "ebay_sold_comps",
        "pricing",
        "depop_listing",
    ]
    assert captured_requests[0].input == {
        "original_input": {"image_urls": ["https://example.com/item.jpg"], "notes": None},
        "previous_outputs": {},
    }
    assert captured_requests[1].input["previous_outputs"] == {
        "vision_analysis": valid_outputs["vision_agent"],
    }
    assert captured_requests[2].context["vision_analysis"] == valid_outputs["vision_agent"]
    assert captured_requests[3].context["pricing"] == valid_outputs["pricing_agent"]


@pytest.mark.asyncio
async def test_execute_step_routes_through_fetch_runtime_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_run_fetch_query(
        agent_slug: str,
        user_text: str = "",
        *,
        task_request: AgentTaskRequest | None = None,
    ) -> dict[str, object]:
        captured["agent_slug"] = agent_slug
        captured["user_text"] = user_text
        captured["task_request"] = task_request
        return VisionAnalysisOutput(
            agent="vision_agent",
            display_name="Vision Agent",
            summary="Vision Agent completed vision_analysis",
            detected_item="sample item",
            brand="Nike",
            category="apparel",
            condition="good",
            confidence=0.95,
        ).model_dump()

    async def fail_run_agent_task(agent_slug: str, request: AgentTaskRequest) -> AgentTaskResponse:
        raise AssertionError("local agent task runner should not be used when fetch is enabled")

    monkeypatch.setattr(orchestrator, "run_fetch_query", fake_run_fetch_query)
    monkeypatch.setattr(orchestrator, "run_agent_task", fail_run_agent_task)
    monkeypatch.setattr(orchestrator, "is_fetch_enabled", lambda: True)

    result = await orchestrator.execute_step(
        session_id="fetch-step-session",
        pipeline="sell",
        agent_slug="vision_agent",
        step_name="vision_analysis",
        task_request=AgentTaskRequest(
            session_id="fetch-step-session",
            pipeline="sell",
            step="vision_analysis",
            input={
                "original_input": {
                    "notes": "Vintage Nike tee",
                    "image_urls": ["https://example.com/item.jpg"],
                },
                "previous_outputs": {},
            },
            context={},
        ),
    )

    assert captured["agent_slug"] == "vision_agent"
    assert captured["user_text"] == ""
    assert isinstance(captured["task_request"], AgentTaskRequest)
    assert captured["task_request"].input["original_input"] == {
        "notes": "Vintage Nike tee",
        "image_urls": ["https://example.com/item.jpg"],
    }
    assert result["agent"] == "vision_agent"


@pytest.mark.asyncio
async def test_local_agent_execution_rejects_unknown_slug() -> None:
    request = AgentTaskRequest(
        session_id="unknown-agent-session",
        pipeline="sell",
        step="vision_analysis",
    )

    with pytest.raises(ValueError, match="Unknown agent slug: missing_agent"):
        await run_agent_task("missing_agent", request)


def test_validate_agent_task_request_rejects_wrong_step() -> None:
    request = AgentTaskRequest(
        session_id="step-mismatch-session",
        pipeline="sell",
        step="pricing",
        input={"original_input": {"image_urls": ["https://example.com/item.jpg"]}, "previous_outputs": {}},
    )

    with pytest.raises(ValueError, match="expected step"):
        validate_agent_task_request("vision_agent", request)


def test_validate_agent_task_request_rejects_invalid_buy_input_shape() -> None:
    request = AgentTaskRequest(
        session_id="bad-buy-input-session",
        pipeline="buy",
        step="depop_search",
        input={"original_input": {"query": ["not", "a", "string"]}, "previous_outputs": {}},
    )

    with pytest.raises(ValidationError):
        validate_agent_task_request("depop_search_agent", request)


def test_validate_agent_output_rejects_malformed_search_result() -> None:
    with pytest.raises(ValidationError):
        validate_agent_output(
            "depop_search_agent",
            {
                "agent": "depop_search_agent",
                "display_name": "Depop Search Agent",
                "summary": "broken payload",
                "results": [{"platform": "depop", "price": 40.0, "title": "Missing url and condition"}],
            },
        )


def test_search_results_schema_round_trips_expected_fields() -> None:
    output = SearchResultsOutput.model_validate(
        {
            "agent": "offerup_search_agent",
            "display_name": "OfferUp Search Agent",
            "summary": "OfferUp Search Agent completed offerup_search",
            "results": [
                {
                    "platform": "offerup",
                    "title": "Vintage tee",
                    "price": 36.0,
                    "url": "https://offerup.example/listing-1",
                    "condition": "good",
                    "seller": "offerup_local_1",
                    "seller_score": 15,
                    "posted_at": "2026-04-01",
                }
            ],
        }
    )

    assert output.results[0].platform == "offerup"
    assert output.results[0].url == "https://offerup.example/listing-1"
    assert output.results[0].seller == "offerup_local_1"


@pytest.mark.asyncio
async def test_pipeline_rejects_invalid_initial_input_before_first_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    agent_called = {"value": False}

    async def fake_run_agent_task(agent_slug: str, request: AgentTaskRequest) -> AgentTaskResponse:
        agent_called["value"] = True
        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="completed",
            output={},
        )

    monkeypatch.setattr(orchestrator, "run_agent_task", fake_run_agent_task)

    request = PipelineStartRequest(
        user_id="buy-user",
        input={"query": ["not", "a", "string"], "budget": 45},
        metadata={"source": "test"},
    )
    session_id = "invalid-initial-input-session"
    await session_manager.create_session(session_id=session_id, pipeline="buy", request=request)

    await orchestrator.run_pipeline(session_id, "buy", request)

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.status == "completed"
    assert session.error is None
    assert agent_called["value"] is False
    assert session.result is not None
    assert session.result["outputs"]["ranking"]["candidate_count"] == 0
    assert session.result["outputs"]["ranking"]["top_choice"]["price"] == 0.0
    assert "no marketplace listings" in session.result["outputs"]["ranking"]["top_choice"]["reason"].lower()
    assert session.events[-2].event_type == "buy_no_results"
    assert session.events[-1].event_type == "pipeline_complete"
