from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from backend.agents.negotiation_agent import app as negotiation_app
from backend.agents.ranking_agent import app as ranking_app


def wait_for_terminal_result(client: TestClient, session_id: str, timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach a terminal state")


def build_buy_previous_outputs() -> dict[str, Any]:
    return {
        "depop_search": {
            "agent": "depop_search_agent",
            "display_name": "Depop Search Agent",
            "summary": "Found 2 Depop listings for Nike tee",
            "results": [
                {
                    "platform": "depop",
                    "title": "Nike tee size M #1 on Depop",
                    "price": 46.16,
                    "url": "https://depop.example/nike-tee-1",
                    "condition": "great",
                },
                {
                    "platform": "depop",
                    "title": "Nike tee size M #2 on Depop",
                    "price": 50.66,
                    "url": "https://depop.example/nike-tee-2",
                    "condition": "great",
                },
            ],
        },
        "ebay_search": {
            "agent": "ebay_search_agent",
            "display_name": "eBay Search Agent",
            "summary": "Found 2 eBay listings for Nike tee",
            "results": [
                {
                    "platform": "ebay",
                    "title": "Nike tee size M #1 on eBay",
                    "price": 42.53,
                    "url": "https://ebay.example/nike-tee-1",
                    "condition": "good",
                },
                {
                    "platform": "ebay",
                    "title": "Nike tee size M #2 on eBay",
                    "price": 47.03,
                    "url": "https://ebay.example/nike-tee-2",
                    "condition": "good",
                },
            ],
        },
        "mercari_search": {
            "agent": "mercari_search_agent",
            "display_name": "Mercari Search Agent",
            "summary": "Found 2 Mercari listings for Nike tee",
            "results": [
                {
                    "platform": "mercari",
                    "title": "Nike tee size M #1 on Mercari",
                    "price": 43.89,
                    "url": "https://mercari.example/nike-tee-1",
                    "condition": "excellent",
                },
                {
                    "platform": "mercari",
                    "title": "Nike tee size M #2 on Mercari",
                    "price": 48.39,
                    "url": "https://mercari.example/nike-tee-2",
                    "condition": "good",
                },
            ],
        },
        "offerup_search": {
            "agent": "offerup_search_agent",
            "display_name": "OfferUp Search Agent",
            "summary": "Found 2 OfferUp listings for Nike tee",
            "results": [
                {
                    "platform": "offerup",
                    "title": "Nike tee size M #1 on Offerup",
                    "price": 39.82,
                    "url": "https://offerup.example/nike-tee-1",
                    "condition": "good",
                },
                {
                    "platform": "offerup",
                    "title": "Nike tee size M #2 on Offerup",
                    "price": 44.32,
                    "url": "https://offerup.example/nike-tee-2",
                    "condition": "good",
                },
            ],
        },
    }


def test_ranking_agent_selects_best_budget_and_condition_match() -> None:
    payload = {
        "session_id": "ranking-real-session",
        "pipeline": "buy",
        "step": "ranking",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": build_buy_previous_outputs(),
        },
        "context": {},
    }

    with TestClient(ranking_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["candidate_count"] == 8
    assert result["output"]["top_choice"] == {
        "platform": "mercari",
        "title": "Nike tee size M #1 on Mercari",
        "price": 43.89,
        "score": 0.93,
        "reason": "Excellent condition with strong budget fit on mercari",
    }


def test_negotiation_agent_generates_messages_for_top_candidates() -> None:
    previous_outputs = build_buy_previous_outputs()
    previous_outputs["ranking"] = {
        "agent": "ranking_agent",
        "display_name": "Ranking Agent",
        "summary": "Ranked 8 listings and selected mercari as the top choice",
        "top_choice": {
            "platform": "mercari",
            "title": "Nike tee size M #1 on Mercari",
            "price": 43.89,
            "score": 0.93,
            "reason": "Excellent condition with strong budget fit on mercari",
        },
        "candidate_count": 8,
    }

    payload = {
        "session_id": "negotiation-real-session",
        "pipeline": "buy",
        "step": "negotiation",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": previous_outputs,
        },
        "context": {},
    }

    with TestClient(negotiation_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Prepared 3 negotiation messages starting with mercari"
    assert result["output"]["offer_messages"] == [
        {
            "platform": "mercari",
            "listing_title": "Nike tee size M #1 on Mercari",
            "target_price": 40.38,
            "message": "Hi! I love this listing. Would you consider $40.38 for Nike tee size M #1 on Mercari?",
        },
        {
            "platform": "offerup",
            "listing_title": "Nike tee size M #1 on Offerup",
            "target_price": 35.84,
            "message": "Hi! I love this listing. Would you consider $35.84 for Nike tee size M #1 on Offerup?",
        },
        {
            "platform": "ebay",
            "listing_title": "Nike tee size M #1 on eBay",
            "target_price": 38.7,
            "message": "Hi! I love this listing. Would you consider $38.7 for Nike tee size M #1 on eBay?",
        },
    ]


def test_buy_pipeline_uses_real_ranking_and_negotiation_outputs(client: TestClient) -> None:
    response = client.post(
        "/buy/start",
        json={
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "buy-decision-pipeline-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    result = wait_for_terminal_result(client, session_id)
    ranking = result["result"]["outputs"]["ranking"]
    negotiation = result["result"]["outputs"]["negotiation"]

    assert ranking["top_choice"]["platform"] == "mercari"
    assert ranking["top_choice"]["score"] == 0.93
    assert negotiation["offer_messages"][0]["target_price"] == 40.38
    assert len(negotiation["offer_messages"]) == 3
