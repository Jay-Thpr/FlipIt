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
PUBLIC_APP_BASE_URL = os.getenv("PUBLIC_APP_BASE_URL", "")
AGENT_HOST = os.getenv("AGENT_HOST", "127.0.0.1")
AGENT_EXECUTION_MODE = os.getenv("AGENT_EXECUTION_MODE", "local_functions")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "dev-internal-token")
AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "30"))
BUY_AGENT_MAX_RETRIES = int(os.getenv("BUY_AGENT_MAX_RETRIES", "1"))
EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
VISION_LOW_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_LOW_CONFIDENCE_THRESHOLD", "0.70"))
NANO_BANANA_API_URL = os.getenv("NANO_BANANA_API_URL", "")
NANO_BANANA_API_KEY = os.getenv("NANO_BANANA_API_KEY", "")
IMAGE_PROCESSING_TIMEOUT_SECONDS = float(os.getenv("IMAGE_PROCESSING_TIMEOUT_SECONDS", "30"))
CLEAN_PHOTO_PROVIDER = os.getenv("CLEAN_PHOTO_PROVIDER", "auto")


def get_agent_execution_mode() -> str:
    return os.getenv("AGENT_EXECUTION_MODE", AGENT_EXECUTION_MODE)


def get_public_app_base_url() -> str:
    return os.getenv("PUBLIC_APP_BASE_URL", PUBLIC_APP_BASE_URL).rstrip("/")


def get_agent_timeout_seconds() -> float:
    return float(os.getenv("AGENT_TIMEOUT_SECONDS", str(AGENT_TIMEOUT_SECONDS)))


def get_buy_agent_max_retries() -> int:
    return int(os.getenv("BUY_AGENT_MAX_RETRIES", str(BUY_AGENT_MAX_RETRIES)))


def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", GEMINI_API_KEY))


def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", GEMINI_MODEL)


def get_gemini_image_model() -> str:
    return os.getenv("GEMINI_IMAGE_MODEL", GEMINI_IMAGE_MODEL)


def get_vision_low_confidence_threshold() -> float:
    return float(os.getenv("VISION_LOW_CONFIDENCE_THRESHOLD", str(VISION_LOW_CONFIDENCE_THRESHOLD)))


def get_nano_banana_api_url() -> str:
    return os.getenv("NANO_BANANA_API_URL", NANO_BANANA_API_URL)


def get_nano_banana_api_key() -> str:
    return os.getenv("NANO_BANANA_API_KEY", NANO_BANANA_API_KEY)


def get_image_processing_timeout_seconds() -> float:
    return float(os.getenv("IMAGE_PROCESSING_TIMEOUT_SECONDS", str(IMAGE_PROCESSING_TIMEOUT_SECONDS)))


def get_clean_photo_provider() -> str:
    return os.getenv("CLEAN_PHOTO_PROVIDER", CLEAN_PHOTO_PROVIDER).strip().lower() or "auto"
