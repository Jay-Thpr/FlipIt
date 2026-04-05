from __future__ import annotations

from backend.schemas import AgentTaskRequest, AgentTaskResponse

from .depop_listing_agent import agent as depop_listing_agent
from .depop_search_agent import agent as depop_search_agent
from .ebay_search_agent import agent as ebay_search_agent
from .ebay_sold_comps_agent import agent as ebay_sold_comps_agent
from .mercari_search_agent import agent as mercari_search_agent
from .negotiation_agent import agent as negotiation_agent
from .offerup_search_agent import agent as offerup_search_agent
from .pricing_agent import agent as pricing_agent
from .ranking_agent import agent as ranking_agent
from .vision_agent import agent as vision_agent

LOCAL_AGENT_REGISTRY = {
    "vision_agent": vision_agent,
    "ebay_sold_comps_agent": ebay_sold_comps_agent,
    "pricing_agent": pricing_agent,
    "depop_listing_agent": depop_listing_agent,
    "depop_search_agent": depop_search_agent,
    "ebay_search_agent": ebay_search_agent,
    "mercari_search_agent": mercari_search_agent,
    "offerup_search_agent": offerup_search_agent,
    "ranking_agent": ranking_agent,
    "negotiation_agent": negotiation_agent,
}


def get_local_agent(agent_slug: str):
    try:
        return LOCAL_AGENT_REGISTRY[agent_slug]
    except KeyError as exc:
        raise ValueError(f"Unknown agent slug: {agent_slug}") from exc


async def run_local_agent_task(agent_slug: str, request: AgentTaskRequest) -> AgentTaskResponse:
    agent = get_local_agent(agent_slug)
    return await agent.handle_task(request)
