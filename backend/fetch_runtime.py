from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.agents.registry import run_local_agent_task
from backend.schemas import AgentTaskRequest, validate_agent_output

FETCH_AGENT_READMES_DIR = Path(__file__).resolve().parent / "fetch_agents" / "readmes"


@dataclass(frozen=True)
class FetchAgentSpec:
    slug: str
    name: str
    port: int
    seed_env_var: str
    description: str
    persona: str
    capabilities: tuple[str, ...]
    example_prompts: tuple[str, ...]
    input_contract: str
    output_contract: str
    tags: tuple[str, ...]
    task_family: str
    readme_path: str | None = None
    is_public: bool = False
    is_launchable: bool = False
    handoff_targets: tuple[str, ...] = ()

    @property
    def agentverse_address_env_var(self) -> str:
        return f"{self.slug.upper()}_AGENTVERSE_ADDRESS"


def _readme_path(filename: str) -> str:
    return str(FETCH_AGENT_READMES_DIR / filename)


FETCH_AGENT_SPECS: dict[str, FetchAgentSpec] = {
    "resale_copilot_agent": FetchAgentSpec(
        slug="resale_copilot_agent",
        name="ResaleCopilotAgent",
        port=9211,
        seed_env_var="RESALE_COPILOT_FETCH_AGENT_SEED",
        description="Agentverse-facing resale copilot that routes broad buy, price, identify, and list requests across the local resale workflow.",
        persona="A resale operations copilot that triages broad flipping questions and routes them to the correct specialist workflow.",
        capabilities=(
            "Route broad resale requests to the right specialist workflow",
            "Explain whether a request is best handled as identify, price, list, search, rank, or negotiate",
            "Return structured execution results from the existing backend pipeline",
        ),
        example_prompts=(
            "Help me flip this vintage Nike tee",
            "Find the best place to buy this Carhartt jacket under $80",
            "Turn this item into a Depop draft",
        ),
        input_contract="Natural-language resale request with optional image URLs, budget, and marketplace constraints.",
        output_contract="Structured specialist result plus a concise resale-oriented summary of what was routed and why.",
        tags=("resale", "orchestration", "pricing", "search", "depop", "agentverse"),
        task_family="resale_copilot",
        readme_path=_readme_path("resale_copilot_agent.md"),
        is_public=True,
        is_launchable=True,
        handoff_targets=("vision_agent", "pricing_agent", "depop_listing_agent"),
    ),
    "vision_agent": FetchAgentSpec(
        slug="vision_agent",
        name="VisionAgent",
        port=9201,
        seed_env_var="VISION_FETCH_AGENT_SEED",
        description="Identifies a resale item from text or image URLs and summarizes its brand, category, and condition.",
        persona="An item identification specialist for resale inventory triage.",
        capabilities=(
            "Identify likely item type, brand, category, and condition",
            "Extract useful resale notes from image URLs and short descriptions",
            "Prepare structured vision output for downstream pricing and listing agents",
        ),
        example_prompts=(
            "Identify this vintage Nike tee from the photo",
            "What kind of jacket is this https://example.com/jacket.jpg",
            "Tell me the likely brand and condition of this item",
        ),
        input_contract="Short text description and optional image URLs for a single resale item.",
        output_contract="Vision analysis with detected item, brand, category, condition, confidence, and summary.",
        tags=("resale", "vision", "identification", "inventory"),
        task_family="sell_identify",
        readme_path=_readme_path("vision_agent.md"),
        is_public=False,
        handoff_targets=("pricing_agent", "resale_copilot_agent"),
    ),
    "ebay_sold_comps_agent": FetchAgentSpec(
        slug="ebay_sold_comps_agent",
        name="EbaySoldCompsAgent",
        port=9202,
        seed_env_var="EBAY_SOLD_COMPS_FETCH_AGENT_SEED",
        description="Estimates eBay sold comparables for an item using the vision output as input.",
        persona="An internal sold-comps specialist focused on pricing evidence from eBay resale history.",
        capabilities=(
            "Estimate sold comparables from item signals",
            "Support pricing decisions with sold-market ranges",
        ),
        example_prompts=("Estimate sold comps for this item",),
        input_contract="Structured sell input plus vision analysis output.",
        output_contract="Sold-comp summary with price range and sample size.",
        tags=("resale", "ebay", "sold-comps", "pricing"),
        task_family="sell_price",
        handoff_targets=("pricing_agent",),
    ),
    "pricing_agent": FetchAgentSpec(
        slug="pricing_agent",
        name="PricingAgent",
        port=9203,
        seed_env_var="PRICING_FETCH_AGENT_SEED",
        description="Prices an item after vision and sold comps analysis and estimates profit.",
        persona="A resale pricing analyst that translates item signals and sold comps into a listing recommendation.",
        capabilities=(
            "Estimate list price and expected profit",
            "Use item identification and sold comps to set a resale recommendation",
            "Summarize pricing confidence and key value drivers",
        ),
        example_prompts=(
            "What should I price this vintage Nike tee at?",
            "Estimate profit on this jacket if I list it now",
            "Price this item from the photos and notes",
        ),
        input_contract="Natural-language item description or sell input with optional image URLs.",
        output_contract="Pricing recommendation with expected profit, confidence, and concise rationale.",
        tags=("resale", "pricing", "profit", "valuation"),
        task_family="sell_price",
        readme_path=_readme_path("pricing_agent.md"),
        is_public=False,
        handoff_targets=("depop_listing_agent", "resale_copilot_agent"),
    ),
    "depop_listing_agent": FetchAgentSpec(
        slug="depop_listing_agent",
        name="DepopListingAgent",
        port=9204,
        seed_env_var="DEPOP_LISTING_FETCH_AGENT_SEED",
        description="Builds a Depop-ready draft listing after item analysis and pricing.",
        persona="A Depop listing specialist that turns analyzed resale inventory into a draft ready for review or submission.",
        capabilities=(
            "Create a Depop-ready draft from item details and pricing",
            "Revise listing copy and summarize what changed",
            "Prepare listing output for review before submit",
        ),
        example_prompts=(
            "Turn this item into a Depop draft",
            "Create a Depop listing for this Carhartt jacket",
            "Revise the draft to sound more streetwear-focused",
        ),
        input_contract="Sell-side item description with optional image URLs and any listing instructions.",
        output_contract="Depop draft payload with title, description, price, category path, and draft status.",
        tags=("resale", "depop", "listing", "drafting"),
        task_family="sell_list",
        readme_path=_readme_path("depop_listing_agent.md"),
        is_public=False,
        handoff_targets=("pricing_agent", "resale_copilot_agent"),
    ),
    "depop_search_agent": FetchAgentSpec(
        slug="depop_search_agent",
        name="DepopSearchAgent",
        port=9205,
        seed_env_var="DEPOP_SEARCH_FETCH_AGENT_SEED",
        description="Searches Depop for a resale query and returns active listings.",
        persona="A marketplace-specific search specialist for active Depop inventory.",
        capabilities=(
            "Search active Depop listings",
            "Return listing candidates for buy-side resale sourcing",
        ),
        example_prompts=("Find this on Depop under $60",),
        input_contract="Buy query with optional budget.",
        output_contract="Active Depop listings with summary and execution metadata.",
        tags=("resale", "search", "depop", "buy-side"),
        task_family="buy_search",
        handoff_targets=("resale_copilot_agent",),
    ),
    "ebay_search_agent": FetchAgentSpec(
        slug="ebay_search_agent",
        name="EbaySearchAgent",
        port=9206,
        seed_env_var="EBAY_SEARCH_FETCH_AGENT_SEED",
        description="Searches eBay for active resale listings for a query.",
        persona="A marketplace-specific search specialist for active eBay inventory.",
        capabilities=(
            "Search active eBay listings",
            "Return listing candidates for buy-side resale sourcing",
        ),
        example_prompts=("Find this on eBay under $60",),
        input_contract="Buy query with optional budget.",
        output_contract="Active eBay listings with summary and execution metadata.",
        tags=("resale", "search", "ebay", "buy-side"),
        task_family="buy_search",
        handoff_targets=("resale_copilot_agent",),
    ),
    "mercari_search_agent": FetchAgentSpec(
        slug="mercari_search_agent",
        name="MercariSearchAgent",
        port=9207,
        seed_env_var="MERCARI_SEARCH_FETCH_AGENT_SEED",
        description="Searches Mercari for active resale listings for a query.",
        persona="A marketplace-specific search specialist for active Mercari inventory.",
        capabilities=(
            "Search active Mercari listings",
            "Return listing candidates for buy-side resale sourcing",
        ),
        example_prompts=("Find this on Mercari under $60",),
        input_contract="Buy query with optional budget.",
        output_contract="Active Mercari listings with summary and execution metadata.",
        tags=("resale", "search", "mercari", "buy-side"),
        task_family="buy_search",
        handoff_targets=("resale_copilot_agent",),
    ),
    "offerup_search_agent": FetchAgentSpec(
        slug="offerup_search_agent",
        name="OfferUpSearchAgent",
        port=9208,
        seed_env_var="OFFERUP_SEARCH_FETCH_AGENT_SEED",
        description="Searches OfferUp for active resale listings for a query.",
        persona="A marketplace-specific search specialist for active OfferUp inventory.",
        capabilities=(
            "Search active OfferUp listings",
            "Return listing candidates for buy-side resale sourcing",
        ),
        example_prompts=("Find this on OfferUp under $60",),
        input_contract="Buy query with optional budget.",
        output_contract="Active OfferUp listings with summary and execution metadata.",
        tags=("resale", "search", "offerup", "buy-side"),
        task_family="buy_search",
        handoff_targets=("resale_copilot_agent",),
    ),
    "ranking_agent": FetchAgentSpec(
        slug="ranking_agent",
        name="RankingAgent",
        port=9209,
        seed_env_var="RANKING_FETCH_AGENT_SEED",
        description="Runs multi-marketplace search and ranks the best buying options.",
        persona="An internal buy-side ranking specialist for comparing marketplace options.",
        capabilities=(
            "Rank buy-side candidates across marketplaces",
            "Summarize why the top listing is the best option",
        ),
        example_prompts=("Rank these marketplace results",),
        input_contract="Buy query with prior marketplace search outputs.",
        output_contract="Ranked listings, top choice, and median price summary.",
        tags=("resale", "ranking", "buy-side", "comparison"),
        task_family="buy_rank",
        handoff_targets=("resale_copilot_agent",),
    ),
    "negotiation_agent": FetchAgentSpec(
        slug="negotiation_agent",
        name="NegotiationAgent",
        port=9210,
        seed_env_var="NEGOTIATION_FETCH_AGENT_SEED",
        description="Runs the BUY flow through negotiation and returns prepared or sent offers.",
        persona="An internal negotiation specialist for preparing or sending marketplace offers.",
        capabilities=(
            "Prepare buy-side offers from ranked listings",
            "Attempt marketplace negotiation when the environment supports it",
        ),
        example_prompts=("Negotiate on the best result",),
        input_contract="Buy query with ranked candidates.",
        output_contract="Prepared or sent offers with negotiation metadata.",
        tags=("resale", "negotiation", "offers", "buy-side"),
        task_family="buy_negotiate",
        handoff_targets=("resale_copilot_agent",),
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
BUY_SEARCH_STEPS = tuple(step_name for _, step_name in BUY_SEARCH_AGENT_CHAIN)
PUBLIC_FETCH_AGENT_SLUGS = tuple(spec.slug for spec in FETCH_AGENT_SPECS.values() if spec.is_public)


def list_fetch_agent_slugs() -> list[str]:
    return list(FETCH_AGENT_SPECS)


def list_public_fetch_agent_slugs() -> list[str]:
    return list(PUBLIC_FETCH_AGENT_SLUGS)


def get_fetch_agent_spec(agent_slug: str) -> FetchAgentSpec:
    return FETCH_AGENT_SPECS[agent_slug]


def get_fetch_agentverse_address(agent_slug: str) -> str | None:
    spec = FETCH_AGENT_SPECS[agent_slug]
    value = os.getenv(spec.agentverse_address_env_var, "").strip()
    return value or None


def list_fetch_agent_specs() -> list[dict[str, str | int | None]]:
    return [
        {
            "slug": spec.slug,
            "name": spec.name,
            "port": spec.port,
            "agentverse_address": get_fetch_agentverse_address(spec.slug),
            "description": spec.description,
            "persona": spec.persona,
            "capabilities": list(spec.capabilities),
            "example_prompts": list(spec.example_prompts),
            "input_contract": spec.input_contract,
            "output_contract": spec.output_contract,
            "tags": list(spec.tags),
            "task_family": spec.task_family,
            "readme_path": spec.readme_path,
            "is_public": spec.is_public,
            "handoff_targets": list(spec.handoff_targets),
        }
        for spec in FETCH_AGENT_SPECS.values()
    ]


def list_fetch_agent_capabilities() -> list[dict[str, object]]:
    capabilities: list[dict[str, object]] = []
    for spec in FETCH_AGENT_SPECS.values():
        capabilities.append(
            {
                "slug": spec.slug,
                "name": spec.name,
                "is_public": spec.is_public,
                "task_family": spec.task_family,
                "persona": spec.persona,
                "capabilities": list(spec.capabilities),
                "example_prompts": list(spec.example_prompts),
                "tags": list(spec.tags),
                "readme_path": spec.readme_path,
                "handoff_targets": list(spec.handoff_targets),
                "runtime": {
                    "port": spec.port,
                    "seed_env_var": spec.seed_env_var,
                    "seed_configured": bool(os.getenv(spec.seed_env_var, "").strip()),
                    "agentverse_address": get_fetch_agentverse_address(spec.slug),
                    "readme_present": bool(spec.readme_path and Path(spec.readme_path).is_file()),
                },
            }
        )
    return capabilities


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


def infer_task_family(agent_slug: str, text: str) -> str:
    if agent_slug != "resale_copilot_agent":
        return FETCH_AGENT_SPECS[agent_slug].task_family

    normalized = normalize_text(text).lower()
    if any(keyword in normalized for keyword in ("offer", "negotiat", "message seller", "send offer")):
        return "buy_negotiate"
    if any(keyword in normalized for keyword in ("find", "search", "buy", "source", "under $", "budget")):
        return "buy_rank"
    if any(keyword in normalized for keyword in ("list", "draft", "depop", "post", "publish")):
        return "sell_list"
    if any(keyword in normalized for keyword in ("price", "worth", "profit", "comp", "comps", "valuation")):
        return "sell_price"
    return "sell_identify"


def _today_iso_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def buy_search_results_are_empty(search_outputs: dict[str, dict[str, object]]) -> bool:
    return not any(search_outputs.get(step_name, {}).get("results") for step_name in BUY_SEARCH_STEPS)


def build_buy_no_results_outputs(
    *,
    buy_input: dict[str, object],
    search_outputs: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    query = normalize_text(str(buy_input.get("query") or ""))
    summary_query = query or "the search query"
    no_results_summary = f"No marketplace listings were found for {summary_query}."
    top_choice = {
        "platform": "depop",
        "title": "No marketplace listings found",
        "price": 0.0,
        "score": 0.0,
        "reason": no_results_summary,
        "url": "",
        "seller": "",
        "seller_score": 0,
        "posted_at": _today_iso_date(),
    }
    ranking_output = {
        "agent": "ranking_agent",
        "display_name": "Ranking Agent",
        "summary": no_results_summary,
        "top_choice": top_choice,
        "candidate_count": 0,
        "ranked_listings": [],
        "median_price": 0.0,
    }
    negotiation_output = {
        "agent": "negotiation_agent",
        "display_name": "Negotiation Agent",
        "summary": no_results_summary,
        "offers": [],
        "browser_use": None,
    }
    return {
        "ranking": ranking_output,
        "negotiation": negotiation_output,
    }


def build_buy_no_results_output(
    *,
    agent_slug: str,
    buy_input: dict[str, object],
    search_outputs: dict[str, dict[str, object]],
) -> dict[str, object]:
    no_results_outputs = build_buy_no_results_outputs(buy_input=buy_input, search_outputs=search_outputs)
    if agent_slug == "ranking_agent":
        return no_results_outputs["ranking"]
    if agent_slug == "negotiation_agent":
        return no_results_outputs["negotiation"]
    raise ValueError(f"Unsupported no-results BUY agent: {agent_slug}")


async def execute_agent(
    *,
    agent_slug: str,
    pipeline: str,
    step: str,
    original_input: dict[str, object],
    previous_outputs: dict[str, dict[str, object]],
    session_id: str | None = None,
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    request = AgentTaskRequest(
        session_id=session_id or f"fetch-{agent_slug}-{uuid4()}",
        pipeline=pipeline,
        step=step,
        input={
            "original_input": original_input,
            "previous_outputs": previous_outputs,
        },
        context=context or {"source": "fetch_chat"},
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


async def _run_sell_chain(agent_slug: str, text: str) -> dict[str, object]:
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


async def _run_buy_chain(agent_slug: str, text: str) -> dict[str, object]:
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
    if buy_search_results_are_empty(search_outputs):
        return build_buy_no_results_output(
            agent_slug=agent_slug,
            buy_input=buy_input,
            search_outputs=search_outputs,
        )

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


async def _run_resale_copilot_query(text: str) -> dict[str, object]:
    task_family = infer_task_family("resale_copilot_agent", text)
    if task_family == "sell_identify":
        result = await _run_sell_chain("vision_agent", text)
    elif task_family == "sell_price":
        result = await _run_sell_chain("pricing_agent", text)
    elif task_family == "sell_list":
        result = await _run_sell_chain("depop_listing_agent", text)
    elif task_family == "buy_rank":
        result = await _run_buy_chain("ranking_agent", text)
    elif task_family == "buy_negotiate":
        result = await _run_buy_chain("negotiation_agent", text)
    else:
        result = await _run_buy_chain("ranking_agent", text)

    return {
        "agent": "resale_copilot_agent",
        "display_name": "Resale Copilot Agent",
        "summary": f"Routed the request as {task_family.replace('_', ' ')} and completed the specialist workflow.",
        "task_family": task_family,
        "specialist_agent": result.get("agent"),
        "result": result,
    }


async def run_fetch_query(
    agent_slug: str,
    user_text: str = "",
    *,
    task_request: AgentTaskRequest | None = None,
) -> dict[str, object]:
    if task_request is not None:
        if agent_slug in {"ranking_agent", "negotiation_agent"}:
            previous_outputs = task_request.input["previous_outputs"]
            if buy_search_results_are_empty(previous_outputs):
                buy_input = task_request.input["original_input"]
                return build_buy_no_results_output(
                    agent_slug=agent_slug,
                    buy_input=buy_input,
                    search_outputs=previous_outputs,
                )
        return await execute_agent(
            agent_slug=agent_slug,
            pipeline=task_request.pipeline,
            step=task_request.step,
            original_input=task_request.input["original_input"],
            previous_outputs=task_request.input["previous_outputs"],
            session_id=task_request.session_id,
            context=task_request.context,
        )

    text = normalize_text(user_text)
    if not text:
        spec = FETCH_AGENT_SPECS[agent_slug]
        return {
            "agent": agent_slug,
            "summary": f"{spec.name} needs a text request to run.",
            "hint": spec.description,
        }

    if agent_slug == "resale_copilot_agent":
        return await _run_resale_copilot_query(text)

    if FETCH_AGENT_SPECS[agent_slug].task_family.startswith("sell_"):
        return await _run_sell_chain(agent_slug, text)

    return await _run_buy_chain(agent_slug, text)


def format_fetch_response(agent_slug: str, user_text: str, result: dict[str, object]) -> str:
    spec = FETCH_AGENT_SPECS[agent_slug]
    summary = str(result.get("summary") or f"{spec.name} completed the request.")
    body = json.dumps(result, indent=2, sort_keys=True)
    normalized_user_text = normalize_text(user_text)

    if agent_slug == "resale_copilot_agent":
        task_family = str(result.get("task_family") or spec.task_family).replace("_", " ")
        specialist_agent = str(result.get("specialist_agent") or "specialist workflow")
        return (
            f"{spec.name} routed: {normalized_user_text}\n\n"
            f"Route: {task_family}\n"
            f"Specialist: {specialist_agent}\n"
            f"Summary: {summary}\n\n"
            "Structured result:\n"
            f"{body}"
        )

    if agent_slug == "vision_agent":
        return (
            f"{spec.name} reviewed: {normalized_user_text}\n\n"
            f"Item: {result.get('detected_item', 'unknown')}\n"
            f"Brand: {result.get('brand', 'unknown')}\n"
            f"Category: {result.get('category', 'unknown')}\n"
            f"Condition: {result.get('condition', 'unknown')}\n"
            f"Confidence: {result.get('confidence', 'unknown')}\n"
            f"Summary: {summary}\n\n"
            "Structured result:\n"
            f"{body}"
        )

    if agent_slug == "pricing_agent":
        return (
            f"{spec.name} reviewed: {normalized_user_text}\n\n"
            f"Recommended price: {result.get('recommended_list_price', 'unknown')}\n"
            f"Expected profit: {result.get('expected_profit', 'unknown')}\n"
            f"Confidence: {result.get('pricing_confidence', 'unknown')}\n"
            f"Summary: {summary}\n\n"
            "Structured result:\n"
            f"{body}"
        )

    if agent_slug == "depop_listing_agent":
        return (
            f"{spec.name} drafted from: {normalized_user_text}\n\n"
            f"Title: {result.get('title', 'unknown')}\n"
            f"Suggested price: {result.get('suggested_price', 'unknown')}\n"
            f"Category path: {result.get('category_path', 'unknown')}\n"
            f"Draft status: {result.get('draft_status', result.get('listing_status', 'unknown'))}\n"
            f"Summary: {summary}\n\n"
            "Structured result:\n"
            f"{body}"
        )

    return (
        f"{spec.name} handled: {normalized_user_text}\n\n"
        f"Summary: {summary}\n\n"
        "Structured result:\n"
        f"{body}"
    )
