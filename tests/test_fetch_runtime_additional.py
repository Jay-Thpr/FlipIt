from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend import fetch_runtime


@pytest.mark.asyncio
async def test_run_fetch_query_for_depop_listing_agent_executes_sell_chain_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    outputs_by_agent = {
        "vision_agent": {
            "agent": "vision_agent",
            "summary": "vision_agent completed",
            "detected_item": "t-shirt",
            "brand": "Nike",
            "category": "apparel",
            "condition": "good",
            "confidence": 0.88,
        },
        "ebay_sold_comps_agent": {
            "agent": "ebay_sold_comps_agent",
            "summary": "ebay_sold_comps_agent completed",
            "median_sold_price": 44.0,
            "low_sold_price": 31.0,
            "high_sold_price": 56.0,
            "sample_size": 10,
        },
        "pricing_agent": {
            "agent": "pricing_agent",
            "summary": "pricing_agent completed",
            "recommended_list_price": 48.0,
            "expected_profit": 22.0,
            "pricing_confidence": 0.84,
        },
        "depop_listing_agent": {
            "agent": "depop_listing_agent",
            "summary": "depop_listing_agent completed",
            "title": "Nike t-shirt - Good Condition",
            "description": "Prepared listing",
            "suggested_price": 48.0,
            "category_path": "Men/Tops/T-Shirts",
            "listing_status": "ready_for_confirmation",
            "ready_for_confirmation": True,
            "draft_status": "ready",
        },
    }

    async def fake_execute_agent(
        *,
        agent_slug: str,
        pipeline: str,
        step: str,
        original_input: dict[str, object],
        previous_outputs: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        calls.append(
            {
                "agent_slug": agent_slug,
                "pipeline": pipeline,
                "step": step,
                "original_input": original_input,
                "previous_outputs": previous_outputs,
            }
        )
        return outputs_by_agent[agent_slug]

    monkeypatch.setattr(fetch_runtime, "execute_agent", fake_execute_agent)

    result = await fetch_runtime.run_fetch_query(
        "depop_listing_agent",
        "Vintage Nike tee https://example.com/photo.jpg",
    )

    assert result == outputs_by_agent["depop_listing_agent"]
    assert [call["agent_slug"] for call in calls] == [
        "vision_agent",
        "ebay_sold_comps_agent",
        "pricing_agent",
        "depop_listing_agent",
    ]
    assert all(call["pipeline"] == "sell" for call in calls)
    assert calls[0]["original_input"] == {
        "image_urls": ["https://example.com/photo.jpg"],
        "notes": "Vintage Nike tee",
    }
    assert calls[1]["previous_outputs"] == {"vision_analysis": outputs_by_agent["vision_agent"]}
    assert calls[2]["previous_outputs"] == {
        "vision_analysis": outputs_by_agent["vision_agent"],
        "ebay_sold_comps": outputs_by_agent["ebay_sold_comps_agent"],
    }
    assert calls[3]["previous_outputs"] == {
        "vision_analysis": outputs_by_agent["vision_agent"],
        "ebay_sold_comps": outputs_by_agent["ebay_sold_comps_agent"],
        "pricing": outputs_by_agent["pricing_agent"],
    }


@pytest.mark.asyncio
async def test_execute_agent_uses_fetch_session_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        status = "completed"
        output = {"agent": "vision_agent", "summary": "done", "brand": "Nike", "detected_item": "tee", "category": "apparel", "condition": "good", "confidence": 0.88}
        error = None

    async def fake_run_local_agent_task(agent_slug: str, request: Any) -> FakeResponse:
        captured["agent_slug"] = agent_slug
        captured["request"] = request
        return FakeResponse()

    monkeypatch.setattr(fetch_runtime, "run_local_agent_task", fake_run_local_agent_task)
    monkeypatch.setattr(fetch_runtime, "validate_agent_output", lambda slug, output: output)

    result = await fetch_runtime.execute_agent(
        agent_slug="vision_agent",
        pipeline="sell",
        step="vision_analysis",
        original_input={"notes": "Nike tee", "image_urls": []},
        previous_outputs={},
    )

    assert captured["agent_slug"] == "vision_agent"
    request = captured["request"]
    assert request.session_id.startswith("fetch-vision_agent-")
    assert request.context == {"source": "fetch_chat"}
    assert request.input["original_input"] == {"notes": "Nike tee", "image_urls": []}
    assert result["agent"] == "vision_agent"


@pytest.mark.asyncio
async def test_run_fetch_query_preserves_task_request_session_and_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_execute_agent(**kwargs: Any) -> dict[str, object]:
        captured.update(kwargs)
        return {"agent": kwargs["agent_slug"], "summary": "done"}

    monkeypatch.setattr(fetch_runtime, "execute_agent", fake_execute_agent)

    request = fetch_runtime.AgentTaskRequest(
        session_id="real-session-id",
        pipeline="buy",
        step="depop_search",
        input={
            "original_input": {"query": "Nike tee", "budget": 45},
            "previous_outputs": {},
        },
        context={"source": "pipeline", "user_id": "buyer-1"},
    )

    result = await fetch_runtime.run_fetch_query("depop_search_agent", task_request=request)

    assert result == {"agent": "depop_search_agent", "summary": "done"}
    assert captured["session_id"] == "real-session-id"
    assert captured["context"] == {"source": "pipeline", "user_id": "buyer-1"}
    assert captured["pipeline"] == "buy"
    assert captured["step"] == "depop_search"


@pytest.mark.asyncio
async def test_run_fetch_query_for_ebay_search_agent_uses_empty_previous_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    async def fake_execute_agent(
        *,
        agent_slug: str,
        pipeline: str,
        step: str,
        original_input: dict[str, object],
        previous_outputs: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        calls.append(
            {
                "agent_slug": agent_slug,
                "pipeline": pipeline,
                "step": step,
                "previous_outputs": previous_outputs,
            }
        )
        return {
            "agent": agent_slug,
            "display_name": "eBay Search Agent",
            "summary": "Found 1 eBay listing",
            "results": [
                {
                    "platform": "ebay",
                    "title": "Nike tee on eBay",
                    "price": 42.0,
                    "url": "https://ebay.example/nike",
                    "condition": "good",
                    "seller": "ebay_seller",
                    "seller_score": 200,
                    "posted_at": "2026-04-04",
                }
            ],
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        }

    monkeypatch.setattr(fetch_runtime, "execute_agent", fake_execute_agent)

    result = await fetch_runtime.run_fetch_query("ebay_search_agent", "Find me a vintage Nike tee under $45")

    assert result["agent"] == "ebay_search_agent"
    assert calls == [
        {
            "agent_slug": "ebay_search_agent",
            "pipeline": "buy",
            "step": "ebay_search",
            "previous_outputs": {},
        }
    ]


def test_public_fetch_agents_have_specialization_metadata_and_readmes() -> None:
    public_specs = [spec for spec in fetch_runtime.FETCH_AGENT_SPECS.values() if spec.is_public]

    assert [spec.slug for spec in public_specs] == [
        "resale_copilot_agent",
        "vision_agent",
        "pricing_agent",
        "depop_listing_agent",
    ]
    for spec in public_specs:
        assert spec.persona
        assert spec.capabilities
        assert spec.example_prompts
        assert spec.readme_path
        assert Path(spec.readme_path).is_file()


def test_public_fetch_agent_readmes_cover_required_sections() -> None:
    required_sections = (
        "## Description",
        "## Example Prompts",
        "## Input Requirements",
        "## Output Summary",
        "## Limitations",
    )

    for spec in fetch_runtime.FETCH_AGENT_SPECS.values():
        if not spec.is_public:
            continue
        readme = Path(spec.readme_path or "").read_text()
        for section in required_sections:
            assert section in readme
