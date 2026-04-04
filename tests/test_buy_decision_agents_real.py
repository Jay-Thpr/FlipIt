from __future__ import annotations

import time
from typing import Any

import backend.agents.negotiation_agent as negotiation_module
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
                    "seller": "depop_closet_1",
                    "seller_score": 34,
                    "posted_at": "2026-04-02",
                },
                {
                    "platform": "depop",
                    "title": "Nike tee size M #2 on Depop",
                    "price": 50.66,
                    "url": "https://depop.example/nike-tee-2",
                    "condition": "great",
                    "seller": "depop_closet_2",
                    "seller_score": 29,
                    "posted_at": "2026-03-31",
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
                    "seller": "ebay_seller_1",
                    "seller_score": 640,
                    "posted_at": "2026-04-03",
                },
                {
                    "platform": "ebay",
                    "title": "Nike tee size M #2 on eBay",
                    "price": 47.03,
                    "url": "https://ebay.example/nike-tee-2",
                    "condition": "good",
                    "seller": "ebay_seller_2",
                    "seller_score": 515,
                    "posted_at": "2026-04-01",
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
                    "seller": "mercari_shop_1",
                    "seller_score": 88,
                    "posted_at": "2026-04-03",
                },
                {
                    "platform": "mercari",
                    "title": "Nike tee size M #2 on Mercari",
                    "price": 48.39,
                    "url": "https://mercari.example/nike-tee-2",
                    "condition": "good",
                    "seller": "mercari_shop_2",
                    "seller_score": 74,
                    "posted_at": "2026-04-01",
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
                    "seller": "offerup_local_1",
                    "seller_score": 18,
                    "posted_at": "2026-03-29",
                },
                {
                    "platform": "offerup",
                    "title": "Nike tee size M #2 on Offerup",
                    "price": 44.32,
                    "url": "https://offerup.example/nike-tee-2",
                    "condition": "good",
                    "seller": "offerup_local_2",
                    "seller_score": 12,
                    "posted_at": "2026-03-28",
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
        "platform": "ebay",
        "title": "Nike tee size M #1 on eBay",
        "price": 42.53,
        "score": 0.94,
        "reason": "Good condition, seller score 640, posted 2026-04-03 on ebay",
        "url": "https://ebay.example/nike-tee-1",
        "seller": "ebay_seller_1",
        "seller_score": 640,
        "posted_at": "2026-04-03",
    }


def test_negotiation_agent_generates_messages_for_top_candidates() -> None:
    previous_outputs = build_buy_previous_outputs()
    previous_outputs["ranking"] = {
        "agent": "ranking_agent",
        "display_name": "Ranking Agent",
        "summary": "Ranked 8 listings and selected ebay as the top choice",
        "top_choice": {
            "platform": "ebay",
            "title": "Nike tee size M #1 on eBay",
            "price": 42.53,
            "score": 0.94,
            "reason": "Good condition, seller score 640, posted 2026-04-03 on ebay",
            "url": "https://ebay.example/nike-tee-1",
            "seller": "ebay_seller_1",
            "seller_score": 640,
            "posted_at": "2026-04-03",
        },
        "candidate_count": 8,
        "ranked_listings": [
            {
                "platform": "ebay",
                "title": "Nike tee size M #1 on eBay",
                "price": 42.53,
                "score": 0.94,
                "reason": "Good condition, seller score 640, posted 2026-04-03 on ebay",
                "url": "https://ebay.example/nike-tee-1",
                "seller": "ebay_seller_1",
                "seller_score": 640,
                "posted_at": "2026-04-03",
            }
        ],
        "median_price": 45.35,
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
    assert result["output"]["summary"] == "Prepared 3 negotiation attempts starting with ebay_seller_1 on ebay"
    assert result["output"]["offers"] == [
        {
            "platform": "ebay",
            "seller": "ebay_seller_1",
            "listing_url": "https://ebay.example/nike-tee-1",
            "listing_title": "Nike tee size M #1 on eBay",
            "target_price": 45.35,
            "message": "Hi! I love this listing. Would you consider $45.35 for Nike tee size M #1 on eBay? I can pay right away.",
            "status": "prepared",
            "failure_reason": None,
            "conversation_url": None,
            "execution_mode": "deterministic",
            "browser_use_error": "profile_missing",
            "attempt_source": "prepared",
            "failure_category": "profile_missing",
        },
        {
            "platform": "offerup",
            "seller": "offerup_local_1",
            "listing_url": "https://offerup.example/nike-tee-1",
            "listing_title": "Nike tee size M #1 on Offerup",
            "target_price": 45.35,
            "message": "Hi! I love this listing. Would you consider $45.35 for Nike tee size M #1 on Offerup? I can pay right away.",
            "status": "prepared",
            "failure_reason": None,
            "conversation_url": None,
            "execution_mode": "deterministic",
            "browser_use_error": "profile_missing",
            "attempt_source": "prepared",
            "failure_category": "profile_missing",
        },
        {
            "platform": "mercari",
            "seller": "mercari_shop_1",
            "listing_url": "https://mercari.example/nike-tee-1",
            "listing_title": "Nike tee size M #1 on Mercari",
            "target_price": 45.35,
            "message": "Hi! I love this listing. Would you consider $45.35 for Nike tee size M #1 on Mercari? I can pay right away.",
            "status": "prepared",
            "failure_reason": None,
            "conversation_url": None,
            "execution_mode": "deterministic",
            "browser_use_error": "profile_missing",
            "attempt_source": "prepared",
            "failure_category": "profile_missing",
        },
    ]
    assert result["output"]["browser_use"]["mode"] == "skipped"


def test_negotiation_agent_sends_offers_with_browser_use_when_profiles_exist(monkeypatch) -> None:
    previous_outputs = build_buy_previous_outputs()
    previous_outputs["ranking"] = {
        "agent": "ranking_agent",
        "display_name": "Ranking Agent",
        "summary": "Ranked 8 listings and selected ebay as the top choice",
        "top_choice": {
            "platform": "ebay",
            "title": "Nike tee size M #1 on eBay",
            "price": 42.53,
            "score": 0.94,
            "reason": "Good condition, seller score 640, posted 2026-04-03 on ebay",
            "url": "https://ebay.example/nike-tee-1",
            "seller": "ebay_seller_1",
            "seller_score": 640,
            "posted_at": "2026-04-03",
        },
        "candidate_count": 8,
        "ranked_listings": [],
        "median_price": 45.35,
    }

    call_count = {"value": 0}

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        call_count["value"] += 1
        return {
            "status": "sent",
            "failure_reason": None,
            "conversation_url": f"https://messages.example/{call_count['value']}",
        }

    monkeypatch.setattr(negotiation_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(negotiation_module.Path, "exists", lambda self: True)

    payload = {
        "session_id": "negotiation-browser-session",
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
    assert result["output"]["summary"] == "Processed 3 negotiation attempts starting with ebay_seller_1 on ebay"
    assert all(offer["status"] == "sent" for offer in result["output"]["offers"])
    assert all(offer["execution_mode"] == "browser_use" for offer in result["output"]["offers"])
    assert all(offer["browser_use_error"] is None for offer in result["output"]["offers"])
    assert all(offer["attempt_source"] == "browser_use" for offer in result["output"]["offers"])
    assert result["output"]["offers"][0]["conversation_url"] == "https://messages.example/1"
    assert result["output"]["browser_use"]["mode"] == "browser_use"
    assert call_count["value"] == 3


def test_negotiation_agent_records_failed_live_send_without_breaking_batch(monkeypatch) -> None:
    previous_outputs = build_buy_previous_outputs()
    previous_outputs["ranking"] = {
        "agent": "ranking_agent",
        "display_name": "Ranking Agent",
        "summary": "Ranked 8 listings and selected ebay as the top choice",
        "top_choice": {
            "platform": "ebay",
            "title": "Nike tee size M #1 on eBay",
            "price": 42.53,
            "score": 0.94,
            "reason": "Good condition, seller score 640, posted 2026-04-03 on ebay",
            "url": "https://ebay.example/nike-tee-1",
            "seller": "ebay_seller_1",
            "seller_score": 640,
            "posted_at": "2026-04-03",
        },
        "candidate_count": 8,
        "ranked_listings": [],
        "median_price": 45.35,
    }

    outcomes = iter(
        [
            {"status": "sent", "failure_reason": None, "conversation_url": "https://messages.example/1"},
            RuntimeError("offer form changed"),
            {"status": "sent", "failure_reason": None, "conversation_url": "https://messages.example/3"},
        ]
    )

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(negotiation_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(negotiation_module.Path, "exists", lambda self: True)

    payload = {
        "session_id": "negotiation-mixed-session",
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
    assert result["output"]["offers"][0]["status"] == "sent"
    assert result["output"]["offers"][0]["execution_mode"] == "browser_use"
    assert result["output"]["offers"][0]["browser_use_error"] is None
    assert result["output"]["offers"][0]["attempt_source"] == "browser_use"
    assert result["output"]["offers"][1]["status"] == "failed"
    assert result["output"]["offers"][1]["failure_reason"] == "offer form changed"
    assert result["output"]["offers"][1]["execution_mode"] == "browser_use"
    assert result["output"]["offers"][1]["browser_use_error"] == "unknown"
    assert result["output"]["offers"][1]["failure_category"] == "unknown"
    assert result["output"]["offers"][2]["status"] == "sent"
    assert result["output"]["offers"][2]["execution_mode"] == "browser_use"
    assert result["output"]["offers"][2]["browser_use_error"] is None
    assert result["output"]["browser_use"]["mode"] == "browser_use"


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

    assert ranking["top_choice"]["platform"] == "ebay"
    assert ranking["top_choice"]["score"] == 0.94
    assert negotiation["offers"][0]["target_price"] == 45.35
    assert negotiation["offers"][0]["execution_mode"] == "deterministic"
    assert negotiation["offers"][0]["browser_use_error"] == "profile_missing"
    assert negotiation["browser_use"]["mode"] == "skipped"
    assert len(negotiation["offers"]) == 3


def test_buy_pipeline_processes_live_negotiation_results(monkeypatch, client: TestClient) -> None:
    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        return {
            "status": "sent",
            "failure_reason": None,
            "conversation_url": "https://messages.example/live",
        }

    monkeypatch.setattr(negotiation_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setattr(negotiation_module.Path, "exists", lambda self: True)

    response = client.post(
        "/buy/start",
        json={
            "user_id": "buy-user",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "buy-live-negotiation-test"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    result = wait_for_terminal_result(client, session_id)
    negotiation = result["result"]["outputs"]["negotiation"]

    assert negotiation["offers"][0]["status"] == "sent"
    assert negotiation["offers"][0]["execution_mode"] == "browser_use"
    assert negotiation["offers"][0]["browser_use_error"] is None
    assert negotiation["offers"][0]["attempt_source"] == "browser_use"
    assert negotiation["offers"][0]["conversation_url"] == "https://messages.example/live"
    assert negotiation["browser_use"]["mode"] == "browser_use"
