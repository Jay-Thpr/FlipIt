from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import asyncio

from backend.agents.depop_listing_agent import app as depop_listing_app
from backend.agents.depop_search_agent import app as depop_search_app
from backend.agents.ebay_search_agent import app as ebay_search_app
from backend.agents.ebay_sold_comps_agent import app as ebay_sold_comps_app
from backend.agents.mercari_search_agent import app as mercari_search_app
from backend.agents.negotiation_agent import app as negotiation_app
from backend.agents.offerup_search_agent import app as offerup_search_app
from backend.agents.pricing_agent import app as pricing_app
from backend.agents.ranking_agent import app as ranking_app
from backend.agents.vision_agent import app as vision_app
from backend.schemas import AGENT_INPUT_CONTRACTS, AGENT_OUTPUT_MODELS, validate_agent_output


AGENT_APPS = [
    (vision_app, "vision_agent", "Vision Agent"),
    (ebay_sold_comps_app, "ebay_sold_comps_agent", "eBay Sold Comps Agent"),
    (pricing_app, "pricing_agent", "Pricing Agent"),
    (depop_listing_app, "depop_listing_agent", "Depop Listing Agent"),
    (depop_search_app, "depop_search_agent", "Depop Search Agent"),
    (ebay_search_app, "ebay_search_agent", "eBay Search Agent"),
    (mercari_search_app, "mercari_search_agent", "Mercari Search Agent"),
    (offerup_search_app, "offerup_search_agent", "OfferUp Search Agent"),
    (ranking_app, "ranking_agent", "Ranking Agent"),
    (negotiation_app, "negotiation_agent", "Negotiation Agent"),
]

VALID_TASK_PAYLOADS = {
    "vision_agent": {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "vision_analysis",
        "input": {
            "original_input": {"image_urls": ["https://example.com/item.jpg"], "notes": "Vintage tee"},
            "previous_outputs": {},
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"image_urls": ["https://example.com/item.jpg"]}},
    },
    "ebay_sold_comps_agent": {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "ebay_sold_comps",
        "input": {
            "original_input": {"image_urls": ["https://example.com/item.jpg"]},
            "previous_outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Vision Agent completed vision_analysis",
                    "detected_item": "sample item",
                    "brand": "unknown",
                    "category": "apparel",
                    "condition": "good",
                    "confidence": 0.85,
                }
            },
        },
        "context": {
            "request_metadata": {"source": "contract-test"},
            "pipeline_input": {"image_urls": ["https://example.com/item.jpg"]},
            "vision_analysis": {
                "agent": "vision_agent",
                "display_name": "Vision Agent",
                "summary": "Vision Agent completed vision_analysis",
                "detected_item": "sample item",
                "brand": "unknown",
                "category": "apparel",
                "condition": "good",
                "confidence": 0.85,
            },
        },
    },
    "pricing_agent": {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "pricing",
        "input": {
            "original_input": {"image_urls": ["https://example.com/item.jpg"]},
            "previous_outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Vision Agent completed vision_analysis",
                    "detected_item": "sample item",
                    "brand": "unknown",
                    "category": "apparel",
                    "condition": "good",
                    "confidence": 0.85,
                },
                "ebay_sold_comps": {
                    "agent": "ebay_sold_comps_agent",
                    "display_name": "eBay Sold Comps Agent",
                    "summary": "eBay Sold Comps Agent completed ebay_sold_comps",
                    "median_sold_price": 42.0,
                    "low_sold_price": 28.0,
                    "high_sold_price": 58.0,
                    "sample_size": 12,
                },
            },
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"image_urls": ["https://example.com/item.jpg"]}},
    },
    "depop_listing_agent": {
        "session_id": "test-session",
        "pipeline": "sell",
        "step": "depop_listing",
        "input": {
            "original_input": {"image_urls": ["https://example.com/item.jpg"]},
            "previous_outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Vision Agent completed vision_analysis",
                    "detected_item": "sample item",
                    "brand": "unknown",
                    "category": "apparel",
                    "condition": "good",
                    "confidence": 0.85,
                },
                "ebay_sold_comps": {
                    "agent": "ebay_sold_comps_agent",
                    "display_name": "eBay Sold Comps Agent",
                    "summary": "eBay Sold Comps Agent completed ebay_sold_comps",
                    "median_sold_price": 42.0,
                    "low_sold_price": 28.0,
                    "high_sold_price": 58.0,
                    "sample_size": 12,
                },
                "pricing": {
                    "agent": "pricing_agent",
                    "display_name": "Pricing Agent",
                    "summary": "Pricing Agent completed pricing",
                    "recommended_list_price": 55.0,
                    "expected_profit": 23.0,
                    "pricing_confidence": 0.82,
                },
            },
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"image_urls": ["https://example.com/item.jpg"]}},
    },
    "depop_search_agent": {
        "session_id": "test-session",
        "pipeline": "buy",
        "step": "depop_search",
        "input": {"original_input": {"query": "Nike vintage tee size M", "budget": 45}, "previous_outputs": {}},
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"query": "Nike vintage tee size M", "budget": 45}},
    },
    "ebay_search_agent": {
        "session_id": "test-session",
        "pipeline": "buy",
        "step": "ebay_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {},
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"query": "Nike vintage tee size M", "budget": 45}},
    },
    "mercari_search_agent": {
        "session_id": "test-session",
        "pipeline": "buy",
        "step": "mercari_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {},
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"query": "Nike vintage tee size M", "budget": 45}},
    },
    "offerup_search_agent": {
        "session_id": "test-session",
        "pipeline": "buy",
        "step": "offerup_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {},
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"query": "Nike vintage tee size M", "budget": 45}},
    },
    "ranking_agent": {
        "session_id": "test-session",
        "pipeline": "buy",
        "step": "ranking",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {
                "depop_search": {
                    "agent": "depop_search_agent",
                    "display_name": "Depop Search Agent",
                    "summary": "Depop Search Agent completed depop_search",
                    "results": [{
                        "platform": "depop", "title": "Sample listing", "price": 40.0,
                        "url": "https://depop.example/listing-1", "condition": "good",
                        "seller": "depop_seller_1", "seller_score": 21, "posted_at": "2026-04-02",
                    }],
                },
                "ebay_search": {
                    "agent": "ebay_search_agent",
                    "display_name": "eBay Search Agent",
                    "summary": "eBay Search Agent completed ebay_search",
                    "results": [{
                        "platform": "ebay", "title": "Sample listing", "price": 38.0,
                        "url": "https://ebay.example/listing-1", "condition": "good",
                        "seller": "ebay_seller_1", "seller_score": 640, "posted_at": "2026-04-03",
                    }],
                },
                "mercari_search": {
                    "agent": "mercari_search_agent",
                    "display_name": "Mercari Search Agent",
                    "summary": "Mercari Search Agent completed mercari_search",
                    "results": [{
                        "platform": "mercari", "title": "Sample listing", "price": 37.0,
                        "url": "https://mercari.example/listing-1", "condition": "good",
                        "seller": "mercari_seller_1", "seller_score": 56, "posted_at": "2026-04-03",
                    }],
                },
                "offerup_search": {
                    "agent": "offerup_search_agent",
                    "display_name": "OfferUp Search Agent",
                    "summary": "OfferUp Search Agent completed offerup_search",
                    "results": [{
                        "platform": "offerup", "title": "Sample listing", "price": 36.0,
                        "url": "https://offerup.example/listing-1", "condition": "good",
                        "seller": "offerup_seller_1", "seller_score": 14, "posted_at": "2026-03-30",
                    }],
                },
            },
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"query": "Nike vintage tee size M", "budget": 45}},
    },
    "negotiation_agent": {
        "session_id": "test-session",
        "pipeline": "buy",
        "step": "negotiation",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {
                "depop_search": {
                    "agent": "depop_search_agent",
                    "display_name": "Depop Search Agent",
                    "summary": "Depop Search Agent completed depop_search",
                    "results": [{
                        "platform": "depop", "title": "Sample listing", "price": 40.0,
                        "url": "https://depop.example/listing-1", "condition": "good",
                        "seller": "depop_seller_1", "seller_score": 21, "posted_at": "2026-04-02",
                    }],
                },
                "ebay_search": {
                    "agent": "ebay_search_agent",
                    "display_name": "eBay Search Agent",
                    "summary": "eBay Search Agent completed ebay_search",
                    "results": [{
                        "platform": "ebay", "title": "Sample listing", "price": 38.0,
                        "url": "https://ebay.example/listing-1", "condition": "good",
                        "seller": "ebay_seller_1", "seller_score": 640, "posted_at": "2026-04-03",
                    }],
                },
                "mercari_search": {
                    "agent": "mercari_search_agent",
                    "display_name": "Mercari Search Agent",
                    "summary": "Mercari Search Agent completed mercari_search",
                    "results": [{
                        "platform": "mercari", "title": "Sample listing", "price": 37.0,
                        "url": "https://mercari.example/listing-1", "condition": "good",
                        "seller": "mercari_seller_1", "seller_score": 56, "posted_at": "2026-04-03",
                    }],
                },
                "offerup_search": {
                    "agent": "offerup_search_agent",
                    "display_name": "OfferUp Search Agent",
                    "summary": "OfferUp Search Agent completed offerup_search",
                    "results": [{
                        "platform": "offerup", "title": "Sample listing", "price": 36.0,
                        "url": "https://offerup.example/listing-1", "condition": "good",
                        "seller": "offerup_seller_1", "seller_score": 14, "posted_at": "2026-03-30",
                    }],
                },
                "ranking": {
                    "agent": "ranking_agent",
                    "display_name": "Ranking Agent",
                    "summary": "Ranking Agent completed ranking",
                    "top_choice": {
                        "platform": "offerup",
                        "title": "Sample ranked listing",
                        "price": 36.0,
                        "score": 0.91,
                        "reason": "Lowest price with strong condition match",
                        "url": "https://offerup.example/listing-1",
                        "seller": "offerup_seller_1",
                        "seller_score": 14,
                        "posted_at": "2026-03-30",
                    },
                    "candidate_count": 4,
                    "ranked_listings": [{
                        "platform": "offerup",
                        "title": "Sample ranked listing",
                        "price": 36.0,
                        "score": 0.91,
                        "reason": "Lowest price with strong condition match",
                        "url": "https://offerup.example/listing-1",
                        "seller": "offerup_seller_1",
                        "seller_score": 14,
                        "posted_at": "2026-03-30",
                    }],
                    "median_price": 37.75,
                },
            },
        },
        "context": {"request_metadata": {"source": "contract-test"}, "pipeline_input": {"query": "Nike vintage tee size M", "budget": 45}},
    },
}


@pytest.mark.parametrize(("agent_app", "slug", "display_name"), AGENT_APPS)
def test_agent_health_endpoint(agent_app, slug: str, display_name: str) -> None:
    with TestClient(agent_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "agent": slug}


@pytest.mark.parametrize(("agent_app", "slug", "display_name"), AGENT_APPS)
def test_agent_task_contract(agent_app, slug: str, display_name: str) -> None:
    with TestClient(agent_app) as client:
        response = client.post("/task", json=VALID_TASK_PAYLOADS[slug])

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "test-session"
    assert payload["step"] == VALID_TASK_PAYLOADS[slug]["step"]
    assert payload["status"] == "completed"
    validated = validate_agent_output(slug, payload["output"])
    assert validated["agent"] == slug
    assert validated["display_name"] == display_name
    assert "summary" in validated


@pytest.mark.parametrize(
    ("agent_app", "slug"),
    [
        (ebay_sold_comps_app, "ebay_sold_comps_agent"),
        (pricing_app, "pricing_agent"),
        (depop_listing_app, "depop_listing_agent"),
        (ranking_app, "ranking_agent"),
        (negotiation_app, "negotiation_agent"),
    ],
)
def test_agent_task_rejects_missing_required_previous_outputs(agent_app, slug: str) -> None:
    payload = {
        **VALID_TASK_PAYLOADS[slug],
        "input": {
            "original_input": VALID_TASK_PAYLOADS[slug]["input"]["original_input"],
            "previous_outputs": {},
        },
    }

    with TestClient(agent_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "Input validation failed" in response.json()["error"]


def test_agent_task_rejects_wrong_step_for_contract() -> None:
    payload = {**VALID_TASK_PAYLOADS["vision_agent"], "step": "pricing"}

    with TestClient(vision_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "expected step" in response.json()["error"]


@pytest.mark.parametrize(("agent_app", "slug", "_display_name"), AGENT_APPS)
def test_agent_chat_placeholder_is_exposed(agent_app, slug: str, _display_name: str) -> None:
    with TestClient(agent_app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_implemented"
    assert payload["agent"] == slug
    assert "Chat Protocol scaffold placeholder" in payload["message"]


@pytest.mark.parametrize("slug", sorted(AGENT_OUTPUT_MODELS))
def test_agent_output_registry_contains_expected_schema_types(slug: str) -> None:
    model = AGENT_OUTPUT_MODELS[slug]

    assert issubclass(model, BaseModel)


@pytest.mark.parametrize("slug", sorted(AGENT_INPUT_CONTRACTS))
def test_agent_input_registry_contains_expected_contract_keys(slug: str) -> None:
    contract = AGENT_INPUT_CONTRACTS[slug]

    assert set(contract) == {"pipeline", "step", "input_model"}


def _empty_search_output(agent_slug: str, step: str, platform: str) -> dict:
    return {
        "agent": agent_slug,
        "display_name": f"{platform.title()} Search Agent",
        "summary": f"Found 0 {platform} listings",
        "results": [],
        "execution_mode": "fallback",
        "browser_use_error": None,
        "browser_use": None,
    }


def test_ranking_agent_empty_candidates_raises_value_error() -> None:
    from backend.agents.ranking_agent import agent
    from backend.schemas import AgentTaskRequest

    request = AgentTaskRequest(
        session_id="test-empty",
        pipeline="buy",
        step="ranking",
        input={
            "original_input": {"query": "nike hoodie", "budget": 50.0},
            "previous_outputs": {
                "depop_search": _empty_search_output("depop_search_agent", "depop_search", "depop"),
                "ebay_search": _empty_search_output("ebay_search_agent", "ebay_search", "ebay"),
                "mercari_search": _empty_search_output("mercari_search_agent", "mercari_search", "mercari"),
                "offerup_search": _empty_search_output("offerup_search_agent", "offerup_search", "offerup"),
            },
        },
    )

    with pytest.raises(ValueError, match="No marketplace listings were found to rank"):
        asyncio.run(agent.build_output(request))
