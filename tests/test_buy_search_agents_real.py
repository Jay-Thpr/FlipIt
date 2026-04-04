from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from backend.agents.depop_search_agent import app as depop_search_app
from backend.agents.ebay_search_agent import app as ebay_search_app
from backend.agents.mercari_search_agent import app as mercari_search_app
from backend.agents.offerup_search_agent import app as offerup_search_app


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


def test_depop_search_agent_builds_query_matched_listings() -> None:
    payload = {
        "session_id": "depop-search-session",
        "pipeline": "buy",
        "step": "depop_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {},
        },
        "context": {"request_metadata": {"source": "depop-search-real-test"}},
    }

    with TestClient(depop_search_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Found 2 Depop listings for Nike tee"
    assert result["output"]["results"][0] == {
        "platform": "depop",
        "title": "Nike tee size M #1 on Depop",
        "price": 46.16,
        "url": "https://depop.example/nike-tee-1",
        "condition": "great",
    }
    assert result["output"]["results"][1]["price"] == 50.66


def test_ebay_search_agent_prices_against_depop_baseline() -> None:
    payload = {
        "session_id": "ebay-search-session",
        "pipeline": "buy",
        "step": "ebay_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {
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
                }
            },
        },
        "context": {},
    }

    with TestClient(ebay_search_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Found 2 eBay listings for Nike tee"
    assert result["output"]["results"][0]["price"] == 42.53
    assert result["output"]["results"][0]["condition"] == "good"


def test_offerup_search_agent_uses_accumulated_market_prices() -> None:
    payload = {
        "session_id": "offerup-search-session",
        "pipeline": "buy",
        "step": "offerup_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {
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
            },
        },
        "context": {},
    }

    with TestClient(offerup_search_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Found 2 OfferUp listings for Nike tee"
    assert result["output"]["results"][0]["price"] == 39.82
    assert result["output"]["results"][0]["title"] == "Nike tee size M #1 on Offerup"


def test_buy_pipeline_uses_real_search_outputs(client: TestClient) -> None:
    response = client.post(
        "/buy/start",
        json={
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "buy-search-pipeline-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    result = wait_for_terminal_result(client, session_id)
    depop_results = result["result"]["outputs"]["depop_search"]["results"]
    ebay_results = result["result"]["outputs"]["ebay_search"]["results"]
    mercari_results = result["result"]["outputs"]["mercari_search"]["results"]
    offerup_results = result["result"]["outputs"]["offerup_search"]["results"]

    assert depop_results[0]["price"] == 46.16
    assert ebay_results[0]["price"] == 42.53
    assert mercari_results[0]["price"] == 43.89
    assert offerup_results[0]["price"] == 39.82
