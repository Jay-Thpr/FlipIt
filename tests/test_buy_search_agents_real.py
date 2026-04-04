from __future__ import annotations

import time
from typing import Any

import backend.agents.depop_search_agent as depop_search_module
import backend.agents.ebay_search_agent as ebay_search_module
import backend.agents.mercari_search_agent as mercari_search_module
import backend.agents.offerup_search_agent as offerup_search_module
from backend.agents.browser_use_marketplaces import build_marketplace_search_url
from backend.agents.browser_use_support import BrowserUseRuntimeUnavailable
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


def build_browser_results(platform: str) -> list[dict[str, object]]:
    return [
        {
            "platform": platform,
            "title": f"{platform} live listing #1",
            "price": 41.25,
            "url": f"https://{platform}.example/live-1",
            "condition": "good",
            "seller": f"{platform}_seller_1",
            "seller_score": 111,
            "posted_at": "2026-04-03",
        },
        {
            "platform": platform,
            "title": f"{platform} live listing #2",
            "price": 44.75,
            "url": f"https://{platform}.example/live-2",
            "condition": "excellent" if platform == "mercari" else "great",
            "seller": f"{platform}_seller_2",
            "seller_score": 222,
            "posted_at": "2026-04-02",
        },
    ]


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
                    "seller_score": 30,
                    "posted_at": "2026-04-02",
                },
                {
                    "platform": "depop",
                    "title": "Nike tee size M #2 on Depop",
                    "price": 50.66,
                    "url": "https://depop.example/nike-tee-2",
                    "condition": "great",
                    "seller": "depop_closet_2",
                    "seller_score": 37,
                    "posted_at": "2026-03-30",
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
                    "seller_score": 647,
                    "posted_at": "2026-04-03",
                },
                {
                    "platform": "ebay",
                    "title": "Nike tee size M #2 on eBay",
                    "price": 47.03,
                    "url": "https://ebay.example/nike-tee-2",
                    "condition": "good",
                    "seller": "ebay_seller_2",
                    "seller_score": 654,
                    "posted_at": "2026-03-31",
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
                    "seller_score": 65,
                    "posted_at": "2026-04-03",
                },
                {
                    "platform": "mercari",
                    "title": "Nike tee size M #2 on Mercari",
                    "price": 48.39,
                    "url": "https://mercari.example/nike-tee-2",
                    "condition": "good",
                    "seller": "mercari_shop_2",
                    "seller_score": 72,
                    "posted_at": "2026-04-01",
                },
            ],
        },
    }


def test_marketplace_search_urls_use_direct_platform_filters() -> None:
    assert build_marketplace_search_url("depop", "Nike vintage tee size M") == "https://www.depop.com/search/?q=Nike+vintage+tee+size+M"
    assert build_marketplace_search_url("ebay", "Nike vintage tee size M") == "https://www.ebay.com/sch/i.html?_nkw=Nike+vintage+tee+size+M&LH_BIN=1&_ipg=24"
    assert build_marketplace_search_url("mercari", "Nike vintage tee size M") == "https://www.mercari.com/search/?keyword=Nike+vintage+tee+size+M"
    assert build_marketplace_search_url("offerup", "Nike vintage tee size M") == "https://offerup.com/search?q=Nike+vintage+tee+size+M"


def test_depop_search_agent_uses_browser_use_results_when_available(monkeypatch) -> None:
    async def fake_run_marketplace_search(platform: str, query: str, max_results: int = 10) -> list[dict[str, object]]:
        assert platform == "depop"
        assert query == "Nike vintage tee size M"
        assert max_results == 10
        return build_browser_results("depop")

    monkeypatch.setattr(depop_search_module, "run_marketplace_search", fake_run_marketplace_search)

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
    assert result["output"]["execution_mode"] == "browser_use"
    assert result["output"]["browser_use_error"] is None
    assert result["output"]["results"] == build_browser_results("depop")
    assert result["output"]["execution_mode"] == "browser_use"
    assert result["output"]["browser_use_error"] is None


def test_ebay_search_agent_falls_back_when_browser_use_unavailable(monkeypatch) -> None:
    async def fake_run_marketplace_search(platform: str, query: str, max_results: int = 10) -> list[dict[str, object]]:
        raise BrowserUseRuntimeUnavailable("missing runtime")

    monkeypatch.setattr(ebay_search_module, "run_marketplace_search", fake_run_marketplace_search)

    payload = {
        "session_id": "ebay-search-session",
        "pipeline": "buy",
        "step": "ebay_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {"depop_search": build_buy_previous_outputs()["depop_search"]},
        },
        "context": {},
    }

    with TestClient(ebay_search_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Found 2 eBay listings for Nike tee"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "runtime_unavailable"
    assert result["output"]["results"][0]["price"] == 42.53
    assert result["output"]["results"][0]["seller"] == "nike_seller_1"
    assert result["output"]["results"][0]["posted_at"] == "2026-04-03"


def test_mercari_search_agent_falls_back_when_browser_use_raises(monkeypatch) -> None:
    async def fake_run_marketplace_search(platform: str, query: str, max_results: int = 10) -> list[dict[str, object]]:
        raise RuntimeError("dom changed")

    monkeypatch.setattr(mercari_search_module, "run_marketplace_search", fake_run_marketplace_search)

    payload = {
        "session_id": "mercari-search-session",
        "pipeline": "buy",
        "step": "mercari_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": {
                "depop_search": build_buy_previous_outputs()["depop_search"],
                "ebay_search": build_buy_previous_outputs()["ebay_search"],
            },
        },
        "context": {},
    }

    with TestClient(mercari_search_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Found 2 Mercari listings for Nike tee"
    assert result["output"]["execution_mode"] == "fallback"
    assert result["output"]["browser_use_error"] == "browser_error"
    assert result["output"]["results"][0]["price"] == 43.89
    assert result["output"]["results"][0]["condition"] == "excellent"


def test_offerup_search_agent_uses_browser_use_results_when_available(monkeypatch) -> None:
    async def fake_run_marketplace_search(platform: str, query: str, max_results: int = 10) -> list[dict[str, object]]:
        assert platform == "offerup"
        return build_browser_results("offerup")

    monkeypatch.setattr(offerup_search_module, "run_marketplace_search", fake_run_marketplace_search)

    payload = {
        "session_id": "offerup-search-session",
        "pipeline": "buy",
        "step": "offerup_search",
        "input": {
            "original_input": {"query": "Nike vintage tee size M", "budget": 45},
            "previous_outputs": build_buy_previous_outputs(),
        },
        "context": {},
    }

    with TestClient(offerup_search_app) as client:
        response = client.post("/task", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["output"]["summary"] == "Found 2 OfferUp listings for Nike tee"
    assert result["output"]["execution_mode"] == "browser_use"
    assert result["output"]["browser_use_error"] is None
    assert result["output"]["results"] == build_browser_results("offerup")
    assert result["output"]["execution_mode"] == "browser_use"
    assert result["output"]["browser_use_error"] is None


def test_buy_pipeline_accepts_live_search_results(monkeypatch, client: TestClient) -> None:
    async def fake_run_marketplace_search(platform: str, query: str, max_results: int = 10) -> list[dict[str, object]]:
        if platform == "depop":
            return build_browser_results("depop")
        raise BrowserUseRuntimeUnavailable("fallback for other platforms")

    monkeypatch.setattr(depop_search_module, "run_marketplace_search", fake_run_marketplace_search)
    monkeypatch.setattr(ebay_search_module, "run_marketplace_search", fake_run_marketplace_search)
    monkeypatch.setattr(mercari_search_module, "run_marketplace_search", fake_run_marketplace_search)
    monkeypatch.setattr(offerup_search_module, "run_marketplace_search", fake_run_marketplace_search)

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

    assert depop_results == build_browser_results("depop")
    assert ebay_results[0]["platform"] == "ebay"
    assert mercari_results[0]["platform"] == "mercari"
    assert offerup_results[0]["platform"] == "offerup"
    assert ebay_results[0]["price"] < depop_results[0]["price"]
    assert mercari_results[0]["seller"].startswith("nike_")
    assert offerup_results[0]["posted_at"].startswith("2026-")
