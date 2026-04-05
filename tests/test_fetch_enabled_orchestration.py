from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient


def wait_for_status(client: TestClient, session_id: str, *, statuses: set[str], timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in statuses:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach one of {sorted(statuses)}")


def _sell_output_for(agent_slug: str) -> dict[str, Any]:
    outputs = {
        "vision_agent": {
            "agent": "vision_agent",
            "display_name": "Vision Agent",
            "summary": "Identified Nike tee",
            "detected_item": "tee",
            "brand": "Nike",
            "category": "apparel",
            "condition": "good",
            "confidence": 0.91,
        },
        "ebay_sold_comps_agent": {
            "agent": "ebay_sold_comps_agent",
            "display_name": "eBay Sold Comps Agent",
            "summary": "Estimated sold comps",
            "median_sold_price": 44.0,
            "low_sold_price": 30.0,
            "high_sold_price": 57.0,
            "sample_size": 9,
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        },
        "pricing_agent": {
            "agent": "pricing_agent",
            "display_name": "Pricing Agent",
            "summary": "Priced item",
            "recommended_list_price": 48.0,
            "expected_profit": 19.5,
            "pricing_confidence": 0.84,
            "trend": None,
            "velocity": None,
        },
        "depop_listing_agent": {
            "agent": "depop_listing_agent",
            "display_name": "Depop Listing Agent",
            "summary": "Prepared listing",
            "title": "Nike tee - Good Condition",
            "description": "Prepared listing description",
            "suggested_price": 48.0,
            "category_path": "Men/Tops/T-Shirts",
            "listing_status": "fallback",
            "ready_for_confirmation": False,
            "draft_status": "fallback",
            "draft_url": None,
            "form_screenshot_url": None,
            "listing_preview": {
                "title": "Nike tee - Good Condition",
                "price": 48.0,
                "description": "Prepared listing description",
                "condition": "good",
                "clean_photo_url": None,
            },
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        },
    }
    return outputs[agent_slug]


def _buy_output_for(agent_slug: str) -> dict[str, Any]:
    search_outputs = {
        "depop_search_agent": {
            "agent": "depop_search_agent",
            "display_name": "Depop Search Agent",
            "summary": "Found 1 Depop listing",
            "results": [
                {
                    "platform": "depop",
                    "title": "Nike tee on Depop",
                    "price": 44.0,
                    "url": "https://depop.example/nike",
                    "condition": "great",
                    "seller": "depop_seller",
                    "seller_score": 12,
                    "posted_at": "2026-04-03",
                }
            ],
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        },
        "ebay_search_agent": {
            "agent": "ebay_search_agent",
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
        },
        "mercari_search_agent": {
            "agent": "mercari_search_agent",
            "display_name": "Mercari Search Agent",
            "summary": "Found 1 Mercari listing",
            "results": [
                {
                    "platform": "mercari",
                    "title": "Nike tee on Mercari",
                    "price": 43.0,
                    "url": "https://mercari.example/nike",
                    "condition": "excellent",
                    "seller": "mercari_seller",
                    "seller_score": 50,
                    "posted_at": "2026-04-04",
                }
            ],
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        },
        "offerup_search_agent": {
            "agent": "offerup_search_agent",
            "display_name": "OfferUp Search Agent",
            "summary": "Found 1 OfferUp listing",
            "results": [
                {
                    "platform": "offerup",
                    "title": "Nike tee on OfferUp",
                    "price": 40.0,
                    "url": "https://offerup.example/nike",
                    "condition": "good",
                    "seller": "offerup_seller",
                    "seller_score": 8,
                    "posted_at": "2026-04-01",
                }
            ],
            "execution_mode": "fallback",
            "browser_use_error": None,
            "browser_use": None,
        },
    }
    if agent_slug in search_outputs:
        return search_outputs[agent_slug]
    if agent_slug == "ranking_agent":
        return {
            "agent": "ranking_agent",
            "display_name": "Ranking Agent",
            "summary": "Ranked 4 candidates",
            "top_choice": {
                "platform": "ebay",
                "title": "Nike tee on eBay",
                "price": 42.0,
                "score": 0.95,
                "reason": "Best value",
                "url": "https://ebay.example/nike",
                "seller": "ebay_seller",
                "seller_score": 200,
                "posted_at": "2026-04-04",
            },
            "candidate_count": 4,
            "ranked_listings": [
                {
                    "platform": "ebay",
                    "title": "Nike tee on eBay",
                    "price": 42.0,
                    "score": 0.95,
                    "reason": "Best value",
                    "url": "https://ebay.example/nike",
                    "seller": "ebay_seller",
                    "seller_score": 200,
                    "posted_at": "2026-04-04",
                }
            ],
            "median_price": 42.5,
        }
    return {
        "agent": "negotiation_agent",
        "display_name": "Negotiation Agent",
        "summary": "Prepared 1 offer",
        "offers": [
            {
                "platform": "ebay",
                "seller": "ebay_seller",
                "listing_url": "https://ebay.example/nike",
                "listing_title": "Nike tee on eBay",
                "target_price": 40.5,
                "message": "Would you take $40.50?",
                "status": "prepared",
                "failure_reason": None,
                "conversation_url": None,
                "execution_mode": "deterministic",
                "browser_use_error": "profile_missing",
                "attempt_source": "prepared",
                "failure_category": None,
            }
        ],
        "browser_use": {
            "mode": "skipped",
            "attempted_live_run": False,
            "profile_name": "ebay",
            "profile_available": False,
            "error_category": "profile_missing",
            "detail": "Prepared an offer because the warmed browser profile is missing.",
        },
    }


def test_sell_pipeline_uses_fetch_runtime_when_enabled(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import backend.orchestrator as orchestrator

    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("FETCH_ENABLED", "true")

    async def fake_run_fetch_query(agent_slug: str, user_text: str = "", *, task_request: Any = None) -> dict[str, Any]:
        assert task_request is not None
        calls.append(
            {
                "agent_slug": agent_slug,
                "pipeline": task_request.pipeline,
                "step": task_request.step,
                "previous_outputs": sorted(task_request.input["previous_outputs"]),
            }
        )
        return _sell_output_for(agent_slug)

    async def fail_run_agent_task(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("local registry should not be used when FETCH_ENABLED=true")

    monkeypatch.setattr(orchestrator, "run_fetch_query", fake_run_fetch_query)
    monkeypatch.setattr(orchestrator, "run_agent_task", fail_run_agent_task)

    response = client.post(
        "/sell/start",
        json={
            "user_id": "sell-user",
            "input": {"image_urls": ["https://example.com/item.jpg"], "notes": "Vintage Nike tee"},
            "metadata": {"source": "fetch-enabled-sell"},
        },
    )
    assert response.status_code == 200
    session = wait_for_status(client, response.json()["session_id"], statuses={"completed"})

    assert [call["agent_slug"] for call in calls] == [
        "vision_agent",
        "ebay_sold_comps_agent",
        "pricing_agent",
        "depop_listing_agent",
    ]
    assert calls[0]["previous_outputs"] == []
    assert calls[1]["previous_outputs"] == ["vision_analysis"]
    assert calls[2]["previous_outputs"] == ["ebay_sold_comps", "vision_analysis"]
    assert calls[3]["previous_outputs"] == ["ebay_sold_comps", "pricing", "vision_analysis"]
    assert session["result"]["outputs"]["depop_listing"]["title"] == "Nike tee - Good Condition"


def test_buy_pipeline_uses_fetch_runtime_when_enabled(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import backend.orchestrator as orchestrator

    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("FETCH_ENABLED", "true")

    async def fake_run_fetch_query(agent_slug: str, user_text: str = "", *, task_request: Any = None) -> dict[str, Any]:
        assert task_request is not None
        calls.append(
            {
                "agent_slug": agent_slug,
                "step": task_request.step,
                "previous_outputs": sorted(task_request.input["previous_outputs"]),
            }
        )
        return _buy_output_for(agent_slug)

    async def fail_run_agent_task(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("local registry should not be used when FETCH_ENABLED=true")

    monkeypatch.setattr(orchestrator, "run_fetch_query", fake_run_fetch_query)
    monkeypatch.setattr(orchestrator, "run_agent_task", fail_run_agent_task)

    response = client.post(
        "/buy/start",
        json={
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "fetch-enabled-buy"},
        },
    )
    assert response.status_code == 200
    session = wait_for_status(client, response.json()["session_id"], statuses={"completed"})

    assert [call["agent_slug"] for call in calls] == [
        "depop_search_agent",
        "ebay_search_agent",
        "mercari_search_agent",
        "offerup_search_agent",
        "ranking_agent",
        "negotiation_agent",
    ]
    for call in calls[:4]:
        assert call["previous_outputs"] == []
    assert calls[4]["previous_outputs"] == ["depop_search", "ebay_search", "mercari_search", "offerup_search"]
    assert calls[5]["previous_outputs"] == ["depop_search", "ebay_search", "mercari_search", "offerup_search", "ranking"]
    assert session["result"]["outputs"]["ranking"]["top_choice"]["platform"] == "ebay"
