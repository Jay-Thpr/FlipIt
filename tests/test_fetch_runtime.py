from __future__ import annotations

import pytest

from backend.fetch_runtime import (
    FETCH_AGENT_SPECS,
    build_buy_input,
    build_sell_input,
    execute_agent,
    extract_budget,
    extract_urls,
    format_fetch_response,
    get_fetch_agent_spec,
    get_fetch_agentverse_address,
    list_public_fetch_agent_slugs,
    list_fetch_agent_specs,
    run_fetch_query,
)


def test_extract_helpers_parse_urls_and_budget() -> None:
    text = "Find me a Nike tee under $45 and check https://example.com/item"
    assert extract_urls(text) == ["https://example.com/item"]
    assert extract_budget(text) == 45.0


def test_build_inputs_keep_expected_fields() -> None:
    sell_input = build_sell_input("Vintage Nike tee https://example.com/photo.jpg")
    assert sell_input["image_urls"] == ["https://example.com/photo.jpg"]
    assert "Vintage Nike tee" in str(sell_input["notes"])

    buy_input = build_buy_input("Need a Carhartt jacket budget 80")
    assert buy_input["query"] == "Need a Carhartt jacket budget 80"
    assert buy_input["budget"] == 80.0


def test_list_fetch_agent_specs_includes_optional_agentverse_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for spec in FETCH_AGENT_SPECS.values():
        monkeypatch.delenv(spec.agentverse_address_env_var, raising=False)
    monkeypatch.setenv("VISION_AGENT_AGENTVERSE_ADDRESS", "agent1qvisiondemo")

    specs = list_fetch_agent_specs()

    assert len(specs) == 11
    assert specs[0] == {
        "slug": "resale_copilot_agent",
        "name": "ResaleCopilotAgent",
        "port": 9211,
        "agentverse_address": None,
        "description": "Agentverse-facing resale copilot that routes broad buy, price, identify, and list requests across the local resale workflow.",
        "persona": "A resale operations copilot that triages broad flipping questions and routes them to the correct specialist workflow.",
        "capabilities": [
            "Route broad resale requests to the right specialist workflow",
            "Explain whether a request is best handled as identify, price, list, search, rank, or negotiate",
            "Return structured execution results from the existing backend pipeline",
        ],
        "example_prompts": [
            "Help me flip this vintage Nike tee",
            "Find the best place to buy this Carhartt jacket under $80",
            "Turn this item into a Depop draft",
        ],
        "input_contract": "Natural-language resale request with optional image URLs, budget, and marketplace constraints.",
        "output_contract": "Structured specialist result plus a concise resale-oriented summary of what was routed and why.",
        "tags": ["resale", "orchestration", "pricing", "search", "depop", "agentverse"],
        "task_family": "resale_copilot",
        "readme_path": get_fetch_agent_spec("resale_copilot_agent").readme_path,
        "is_public": True,
        "handoff_targets": ["vision_agent", "pricing_agent", "depop_listing_agent"],
    }
    assert specs[1] == {
        "slug": "vision_agent",
        "name": "VisionAgent",
        "port": 9201,
        "agentverse_address": "agent1qvisiondemo",
        "description": "Identifies a resale item from text or image URLs and summarizes its brand, category, and condition.",
        "persona": "An item identification specialist for resale inventory triage.",
        "capabilities": [
            "Identify likely item type, brand, category, and condition",
            "Extract useful resale notes from image URLs and short descriptions",
            "Prepare structured vision output for downstream pricing and listing agents",
        ],
        "example_prompts": [
            "Identify this vintage Nike tee from the photo",
            "What kind of jacket is this https://example.com/jacket.jpg",
            "Tell me the likely brand and condition of this item",
        ],
        "input_contract": "Short text description and optional image URLs for a single resale item.",
        "output_contract": "Vision analysis with detected item, brand, category, condition, confidence, and summary.",
        "tags": ["resale", "vision", "identification", "inventory"],
        "task_family": "sell_identify",
        "readme_path": get_fetch_agent_spec("vision_agent").readme_path,
        "is_public": False,
        "handoff_targets": ["pricing_agent", "resale_copilot_agent"],
    }
    assert get_fetch_agentverse_address("depop_search_agent") is None
    assert list_public_fetch_agent_slugs() == ["resale_copilot_agent"]


def test_only_resale_copilot_agent_is_launchable() -> None:
    assert FETCH_AGENT_SPECS["resale_copilot_agent"].is_launchable is True

    for slug, spec in FETCH_AGENT_SPECS.items():
        if slug == "resale_copilot_agent":
            continue
        assert spec.is_launchable is False


@pytest.mark.asyncio
async def test_run_fetch_query_for_search_agent_uses_existing_logic() -> None:
    result = await run_fetch_query("depop_search_agent", "Find me a vintage Nike tee under $45")
    assert result["agent"] == "depop_search_agent"
    assert isinstance(result["results"], list)
    assert result["summary"]


@pytest.mark.asyncio
async def test_run_fetch_query_for_pricing_agent_builds_sell_chain() -> None:
    result = await run_fetch_query("pricing_agent", "Vintage Nike tee in good condition")
    assert result["agent"] == "pricing_agent"
    assert result["recommended_list_price"] > 0
    assert result["expected_profit"] != 0


@pytest.mark.asyncio
async def test_run_fetch_query_for_resale_copilot_routes_to_specialist_workflow() -> None:
    result = await run_fetch_query("resale_copilot_agent", "Price this vintage Nike tee for resale")

    assert result["agent"] == "resale_copilot_agent"
    assert result["task_family"] == "sell_price"
    assert result["specialist_agent"] == "pricing_agent"
    assert result["result"]["agent"] == "pricing_agent"


def test_format_fetch_response_contains_summary_and_json() -> None:
    response = format_fetch_response(
        "vision_agent",
        "Vintage tee",
        {
            "summary": "done",
            "agent": "vision_agent",
            "brand": "Nike",
            "category": "apparel",
            "condition": "good",
            "detected_item": "tee",
            "confidence": 0.92,
        },
    )
    assert "Brand: Nike" in response
    assert "Summary: done" in response
    assert '"agent": "vision_agent"' in response


@pytest.mark.asyncio
async def test_execute_agent_returns_empty_ranking_for_empty_candidates() -> None:
    empty_search_output = {
        "agent": "search_agent",
        "display_name": "Search Agent",
        "summary": "No listings found",
        "results": [],
    }
    result = await execute_agent(
        agent_slug="ranking_agent",
        pipeline="buy",
        step="ranking",
        original_input={"query": "test", "budget": 40},
        previous_outputs={
            "depop_search": empty_search_output,
            "ebay_search": empty_search_output,
            "mercari_search": empty_search_output,
            "offerup_search": empty_search_output,
        },
    )

    assert result["summary"] == "No marketplace listings were found to rank"
    assert result["top_choice"] is None
    assert result["candidate_count"] == 0
    assert result["ranked_listings"] == []
    assert result["median_price"] == 0.0
