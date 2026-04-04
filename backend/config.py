from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    name: str
    slug: str
    port: int


AGENTS: tuple[AgentConfig, ...] = (
    AgentConfig("Vision Agent", "vision_agent", 9101),
    AgentConfig("eBay Sold Comps Agent", "ebay_sold_comps_agent", 9102),
    AgentConfig("Pricing Agent", "pricing_agent", 9103),
    AgentConfig("Depop Listing Agent", "depop_listing_agent", 9104),
    AgentConfig("Depop Search Agent", "depop_search_agent", 9105),
    AgentConfig("eBay Search Agent", "ebay_search_agent", 9106),
    AgentConfig("Mercari Search Agent", "mercari_search_agent", 9107),
    AgentConfig("OfferUp Search Agent", "offerup_search_agent", 9108),
    AgentConfig("Ranking Agent", "ranking_agent", 9109),
    AgentConfig("Negotiation Agent", "negotiation_agent", 9110),
)

AGENT_PORTS = {agent.slug: agent.port for agent in AGENTS}

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_BASE_URL = os.getenv("APP_BASE_URL", f"http://localhost:{APP_PORT}")
AGENT_HOST = os.getenv("AGENT_HOST", "127.0.0.1")
AGENT_EXECUTION_MODE = os.getenv("AGENT_EXECUTION_MODE", "local_functions")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "dev-internal-token")


def get_agent_execution_mode() -> str:
    return os.getenv("AGENT_EXECUTION_MODE", AGENT_EXECUTION_MODE)
