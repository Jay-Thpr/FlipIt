from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


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
AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "30"))
BUY_AGENT_MAX_RETRIES = int(os.getenv("BUY_AGENT_MAX_RETRIES", "1"))
EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")

# Fetch.ai (optional; uAgent / Agentverse wiring is separate from /task contracts)
FETCH_ENABLED = os.getenv("FETCH_ENABLED", "").lower() in ("1", "true", "yes")
AGENTVERSE_API_KEY = os.getenv("AGENTVERSE_API_KEY", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_JWT_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")


def get_agent_execution_mode() -> str:
    return os.getenv("AGENT_EXECUTION_MODE", AGENT_EXECUTION_MODE)


def get_agent_timeout_seconds() -> float:
    return float(os.getenv("AGENT_TIMEOUT_SECONDS", str(AGENT_TIMEOUT_SECONDS)))


def get_buy_agent_max_retries() -> int:
    return int(os.getenv("BUY_AGENT_MAX_RETRIES", str(BUY_AGENT_MAX_RETRIES)))


def is_fetch_enabled() -> bool:
    return os.getenv("FETCH_ENABLED", "true" if FETCH_ENABLED else "false").lower() in ("1", "true", "yes")


def get_agentverse_api_key() -> str:
    return os.getenv("AGENTVERSE_API_KEY", AGENTVERSE_API_KEY)


def get_agent_ports() -> set[int]:
    return {agent.port for agent in AGENTS}


def assert_fetch_agent_ports_do_not_overlap(fetch_ports: Iterable[int] | None = None) -> None:
    if fetch_ports is None:
        from backend.fetch_runtime import FETCH_AGENT_SPECS

        fetch_ports = [spec.port for spec in FETCH_AGENT_SPECS.values()]

    overlaps = sorted(get_agent_ports().intersection(fetch_ports))
    if overlaps:
        overlap_list = ", ".join(str(port) for port in overlaps)
        raise RuntimeError(f"Fetch agent ports overlap with FastAPI agent ports: {overlap_list}")


def is_supabase_configured() -> bool:
    """True when both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set."""
    return bool(
        os.getenv("SUPABASE_URL", SUPABASE_URL).strip()
        and os.getenv("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY).strip()
    )


def fetch_integration_flags() -> dict[str, bool]:
    """Non-secret booleans for /health (Agentverse key presence only, never the value)."""
    return {
        "fetch_enabled": is_fetch_enabled(),
        "agentverse_credentials_present": bool(get_agentverse_api_key().strip()),
    }
