from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from uuid import uuid4

from backend.agents.registry import run_local_agent_task
from backend.schemas import AgentTaskRequest, validate_agent_output


@dataclass(frozen=True)
class FetchAgentSpec:
    slug: str
    name: str
    port: int
    seed_env_var: str
    description: str


FETCH_AGENT_SPECS: dict[str, FetchAgentSpec] = {
    "vision_agent": FetchAgentSpec(
        slug="vision_agent",
        name="VisionAgent",
        port=9201,
        seed_env_var="VISION_FETCH_AGENT_SEED",
        description="Identifies a resale item from text or image URLs and summarizes its brand, category, and condition.",
    ),
    "ebay_sold_comps_agent": FetchAgentSpec(
        slug="ebay_sold_comps_agent",
        name="EbaySoldCompsAgent",
        port=9202,
        seed_env_var="EBAY_SOLD_COMPS_FETCH_AGENT_SEED",
        description="Estimates eBay sold comparables for an item using the vision output as input.",
    ),
    "pricing_agent": FetchAgentSpec(
        slug="pricing_agent",
        name="PricingAgent",
        port=9203,
        seed_env_var="PRICING_FETCH_AGENT_SEED",
        description="Prices an item after vision and sold comps analysis and estimates profit.",
    ),
    "depop_listing_agent": FetchAgentSpec(
        slug="depop_listing_agent",
        name="DepopListingAgent",
        port=9204,
        seed_env_var="DEPOP_LISTING_FETCH_AGENT_SEED",
        description="Builds a Depop-ready draft listing after item analysis and pricing.",
    ),
    "depop_search_agent": FetchAgentSpec(
        slug="depop_search_agent",
        name="DepopSearchAgent",
        port=9205,
        seed_env_var="DEPOP_SEARCH_FETCH_AGENT_SEED",
        description="Searches Depop for a resale query and returns active listings.",
    ),
    "ebay_search_agent": FetchAgentSpec(
        slug="ebay_search_agent",
        name="EbaySearchAgent",
        port=9206,
        seed_env_var="EBAY_SEARCH_FETCH_AGENT_SEED",
        description="Searches eBay for active resale listings for a query.",
    ),
    "mercari_search_agent": FetchAgentSpec(
        slug="mercari_search_agent",
        name="MercariSearchAgent",
        port=9207,
        seed_env_var="MERCARI_SEARCH_FETCH_AGENT_SEED",
        description="Searches Mercari for active resale listings for a query.",
    ),
    "offerup_search_agent": FetchAgentSpec(
        slug="offerup_search_agent",
        name="OfferUpSearchAgent",
        port=9208,
        seed_env_var="OFFERUP_SEARCH_FETCH_AGENT_SEED",
        description="Searches OfferUp for active resale listings for a query.",
    ),
    "ranking_agent": FetchAgentSpec(
        slug="ranking_agent",
        name="RankingAgent",
        port=9209,
        seed_env_var="RANKING_FETCH_AGENT_SEED",
        description="Runs multi-marketplace search and ranks the best buying options.",
    ),
    "negotiation_agent": FetchAgentSpec(
        slug="negotiation_agent",
        name="NegotiationAgent",
        port=9210,
        seed_env_var="NEGOTIATION_FETCH_AGENT_SEED",
        description="Runs the BUY flow through negotiation and returns prepared or sent offers.",
    ),
}

URL_PATTERN = re.compile(r"https?://\S+")
BUDGET_PATTERN = re.compile(r"(?:\$|budget\s+)(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
BUY_SEARCH_AGENT_CHAIN = (
    ("depop_search_agent", "depop_search"),
    ("ebay_search_agent", "ebay_search"),
    ("mercari_search_agent", "mercari_search"),
    ("offerup_search_agent", "offerup_search"),
)
BUY_SEARCH_STEPS_BY_AGENT = {agent_slug: step_name for agent_slug, step_name in BUY_SEARCH_AGENT_CHAIN}


def list_fetch_agent_slugs() -> list[str]:
    return list(FETCH_AGENT_SPECS)


def extract_urls(text: str) -> list[str]:
    return [match.rstrip(".,)") for match in URL_PATTERN.findall(text)]


def extract_budget(text: str) -> float | None:
    match = BUDGET_PATTERN.search(text)
    if match is None:
        return None
    return float(match.group(1))


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def remove_urls(text: str) -> str:
    return normalize_text(URL_PATTERN.sub(" ", text))


def build_sell_input(text: str) -> dict[str, object]:
    notes = normalize_text(remove_urls(text))
    return {
        "image_urls": extract_urls(text),
        "notes": notes or text.strip() or "resale item",
    }


def build_buy_input(text: str) -> dict[str, object]:
    query = normalize_text(remove_urls(text))
    return {
        "query": query or text.strip() or "resale item",
        "budget": extract_budget(text),
    }


async def execute_agent(
    *,
    agent_slug: str,
    pipeline: str,
    step: str,
    original_input: dict[str, object],
    previous_outputs: dict[str, dict[str, object]],
) -> dict[str, object]:
    request = AgentTaskRequest(
        session_id=f"fetch-{agent_slug}-{uuid4()}",
        pipeline=pipeline,
        step=step,
        input={
            "original_input": original_input,
            "previous_outputs": previous_outputs,
        },
        context={
            "source": "fetch_chat",
        },
    )
    response = await run_local_agent_task(agent_slug, request)
    if response.status != "completed":
        raise RuntimeError(response.error or f"{agent_slug} failed")
    return validate_agent_output(agent_slug, response.output)


async def _run_fetch_search_agents(buy_input: dict[str, object]) -> dict[str, dict[str, object]]:
    async def run_one(agent_slug: str, step_name: str) -> tuple[str, dict[str, object]]:
        return (
            step_name,
            await execute_agent(
                agent_slug=agent_slug,
                pipeline="buy",
                step=step_name,
                original_input=buy_input,
                previous_outputs={},
            ),
        )

    results = await asyncio.gather(*(run_one(agent_slug, step_name) for agent_slug, step_name in BUY_SEARCH_AGENT_CHAIN))
    return {step_name: output for step_name, output in results}


async def run_fetch_query(
    agent_slug: str,
    user_text: str = "",
    *,
    task_request: AgentTaskRequest | None = None,
) -> dict[str, object]:
    if task_request is not None:
        return await execute_agent(
            agent_slug=agent_slug,
            pipeline=task_request.pipeline,
            step=task_request.step,
            original_input=task_request.input["original_input"],
            previous_outputs=task_request.input["previous_outputs"],
        )

    text = normalize_text(user_text)
    if not text:
        spec = FETCH_AGENT_SPECS[agent_slug]
        return {
            "agent": agent_slug,
            "summary": f"{spec.name} needs a text request to run.",
            "hint": spec.description,
        }

    if agent_slug in {"vision_agent", "ebay_sold_comps_agent", "pricing_agent", "depop_listing_agent"}:
        sell_input = build_sell_input(text)
        vision = await execute_agent(
            agent_slug="vision_agent",
            pipeline="sell",
            step="vision_analysis",
            original_input=sell_input,
            previous_outputs={},
        )
        if agent_slug == "vision_agent":
            return vision

        comps = await execute_agent(
            agent_slug="ebay_sold_comps_agent",
            pipeline="sell",
            step="ebay_sold_comps",
            original_input=sell_input,
            previous_outputs={"vision_analysis": vision},
        )
        if agent_slug == "ebay_sold_comps_agent":
            return comps

        pricing = await execute_agent(
            agent_slug="pricing_agent",
            pipeline="sell",
            step="pricing",
            original_input=sell_input,
            previous_outputs={
                "vision_analysis": vision,
                "ebay_sold_comps": comps,
            },
        )
        if agent_slug == "pricing_agent":
            return pricing

        return await execute_agent(
            agent_slug="depop_listing_agent",
            pipeline="sell",
            step="depop_listing",
            original_input=sell_input,
            previous_outputs={
                "vision_analysis": vision,
                "ebay_sold_comps": comps,
                "pricing": pricing,
            },
        )

    buy_input = build_buy_input(text)
    if agent_slug in BUY_SEARCH_STEPS_BY_AGENT:
        return await execute_agent(
            agent_slug=agent_slug,
            pipeline="buy",
            step=BUY_SEARCH_STEPS_BY_AGENT[agent_slug],
            original_input=buy_input,
            previous_outputs={},
        )

    search_outputs = await _run_fetch_search_agents(buy_input)

    ranking = await execute_agent(
        agent_slug="ranking_agent",
        pipeline="buy",
        step="ranking",
        original_input=buy_input,
        previous_outputs=search_outputs,
    )
    if agent_slug == "ranking_agent":
        return ranking

    return await execute_agent(
        agent_slug="negotiation_agent",
        pipeline="buy",
        step="negotiation",
        original_input=buy_input,
        previous_outputs={**search_outputs, "ranking": ranking},
    )


def format_fetch_response(agent_slug: str, user_text: str, result: dict[str, object]) -> str:
    spec = FETCH_AGENT_SPECS[agent_slug]
    summary = str(result.get("summary") or f"{spec.name} completed the request.")
    body = json.dumps(result, indent=2, sort_keys=True)
    return (
        f"{spec.name} handled: {normalize_text(user_text)}\n\n"
        f"Summary: {summary}\n\n"
        "Structured result:\n"
        f"{body}"
    )
