from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from backend.agents.depop_listing_agent import app as depop_listing_app
from backend.agents.depop_search_agent import app as depop_search_app
from backend.agents.ebay_search_agent import app as ebay_search_app
from backend.agents.ebay_sold_comps_agent import app as ebay_sold_comps_app
from backend.agents.mercari_search_agent import app as mercari_search_app
from backend.agents.negotiation_agent import app as negotiation_app
from backend.agents.offerup_search_agent import app as offerup_search_app
from backend.main import app as backend_app


def build_sell_previous_outputs() -> dict[str, Any]:
    return {
        "vision_analysis": {
            "agent": "vision_agent",
            "display_name": "Vision Agent",
            "summary": "Inferred Patagonia hoodie in excellent condition",
            "detected_item": "hoodie",
            "brand": "Patagonia",
            "category": "apparel",
            "condition": "excellent",
        },
        "ebay_sold_comps": {
            "agent": "ebay_sold_comps_agent",
            "display_name": "eBay Sold Comps Agent",
            "summary": "Estimated 11 sold eBay comps for Patagonia hoodie",
            "median_sold_price": 70.66,
            "low_sold_price": 55.11,
            "high_sold_price": 86.21,
            "sample_size": 11,
            "execution_mode": "fallback",
            "browser_use_error": "runtime_unavailable",
        },
        "pricing": {
            "agent": "pricing_agent",
            "display_name": "Pricing Agent",
            "summary": "Priced Patagonia hoodie at $78.43 with estimated profit $41.38",
            "recommended_list_price": 78.43,
            "expected_profit": 41.38,
            "pricing_confidence": 0.91,
        },
    }


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
            "execution_mode": "fallback",
            "browser_use_error": "runtime_unavailable",
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
            "execution_mode": "fallback",
            "browser_use_error": "runtime_unavailable",
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
            "execution_mode": "fallback",
            "browser_use_error": "runtime_unavailable",
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
            "execution_mode": "fallback",
            "browser_use_error": "runtime_unavailable",
        },
        "ranking": {
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
        },
    }


def wait_for_terminal_result(client: TestClient, session_id: str, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise RuntimeError(f"Validation session {session_id} did not reach a terminal state")


@contextmanager
def browser_use_mode(mode: str) -> Iterator[None]:
    original = os.getenv("BROWSER_USE_FORCE_FALLBACK")
    if mode == "dry-run":
        os.environ["BROWSER_USE_FORCE_FALLBACK"] = "true"
    elif mode == "live" and original is None:
        os.environ.pop("BROWSER_USE_FORCE_FALLBACK", None)
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("BROWSER_USE_FORCE_FALLBACK", None)
        else:
            os.environ["BROWSER_USE_FORCE_FALLBACK"] = original


def run_agent_case(*, name: str, app: Any, payload: dict[str, Any]) -> dict[str, Any]:
    with TestClient(app) as client:
        response = client.post("/task", json=payload)
    result = response.json()
    return {
        "name": name,
        "kind": "agent",
        "http_status": response.status_code,
        "status": result["status"],
        "output": result.get("output", {}),
        "error": result.get("error"),
    }


def run_pipeline_case(*, name: str, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    with TestClient(backend_app) as client:
        response = client.post(endpoint, json=payload)
        start_payload = response.json()
        session_id = start_payload["session_id"]
        terminal = wait_for_terminal_result(client, session_id)
    return {
        "name": name,
        "kind": "pipeline",
        "http_status": response.status_code,
        "status": terminal["status"],
        "session_id": session_id,
        "result": terminal.get("result"),
        "error": terminal.get("error"),
        "event_count": len(terminal.get("events", [])),
        "event_types": [event["event_type"] for event in terminal.get("events", [])],
    }


def build_validation_cases() -> dict[str, Callable[[], dict[str, Any]]]:
    return {
        "ebay_sold_comps_agent": lambda: run_agent_case(
            name="ebay_sold_comps_agent",
            app=ebay_sold_comps_app,
            payload={
                "session_id": "validation-ebay-sold-comps",
                "pipeline": "sell",
                "step": "ebay_sold_comps",
                "input": {
                    "original_input": {"image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"]},
                    "previous_outputs": {
                        "vision_analysis": {
                            "agent": "vision_agent",
                            "display_name": "Vision Agent",
                            "summary": "Inferred Patagonia hoodie in excellent condition",
                            "detected_item": "hoodie",
                            "brand": "Patagonia",
                            "category": "apparel",
                            "condition": "excellent",
                        }
                    },
                },
                "context": {},
            },
        ),
        "depop_search_agent": lambda: run_agent_case(
            name="depop_search_agent",
            app=depop_search_app,
            payload={
                "session_id": "validation-depop-search",
                "pipeline": "buy",
                "step": "depop_search",
                "input": {"original_input": {"query": "Nike vintage tee size M", "budget": 45}, "previous_outputs": {}},
                "context": {},
            },
        ),
        "ebay_search_agent": lambda: run_agent_case(
            name="ebay_search_agent",
            app=ebay_search_app,
            payload={
                "session_id": "validation-ebay-search",
                "pipeline": "buy",
                "step": "ebay_search",
                "input": {
                    "original_input": {"query": "Nike vintage tee size M", "budget": 45},
                    "previous_outputs": {"depop_search": build_buy_previous_outputs()["depop_search"]},
                },
                "context": {},
            },
        ),
        "mercari_search_agent": lambda: run_agent_case(
            name="mercari_search_agent",
            app=mercari_search_app,
            payload={
                "session_id": "validation-mercari-search",
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
            },
        ),
        "offerup_search_agent": lambda: run_agent_case(
            name="offerup_search_agent",
            app=offerup_search_app,
            payload={
                "session_id": "validation-offerup-search",
                "pipeline": "buy",
                "step": "offerup_search",
                "input": {
                    "original_input": {"query": "Nike vintage tee size M", "budget": 45},
                    "previous_outputs": {
                        "depop_search": build_buy_previous_outputs()["depop_search"],
                        "ebay_search": build_buy_previous_outputs()["ebay_search"],
                        "mercari_search": build_buy_previous_outputs()["mercari_search"],
                    },
                },
                "context": {},
            },
        ),
        "depop_listing_agent": lambda: run_agent_case(
            name="depop_listing_agent",
            app=depop_listing_app,
            payload={
                "session_id": "validation-depop-listing",
                "pipeline": "sell",
                "step": "depop_listing",
                "input": {
                    "original_input": {
                        "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                        "notes": "Patagonia hoodie in excellent condition",
                    },
                    "previous_outputs": build_sell_previous_outputs(),
                },
                "context": {},
            },
        ),
        "negotiation_agent": lambda: run_agent_case(
            name="negotiation_agent",
            app=negotiation_app,
            payload={
                "session_id": "validation-negotiation",
                "pipeline": "buy",
                "step": "negotiation",
                "input": {
                    "original_input": {"query": "Nike vintage tee size M", "budget": 45},
                    "previous_outputs": build_buy_previous_outputs(),
                },
                "context": {},
            },
        ),
        "sell_pipeline": lambda: run_pipeline_case(
            name="sell_pipeline",
            endpoint="/sell/start",
            payload={
                "user_id": "validation-sell-user",
                "input": {
                    "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                    "notes": "Patagonia hoodie in excellent condition",
                },
                "metadata": {"source": "browser-use-validation"},
            },
        ),
        "buy_pipeline": lambda: run_pipeline_case(
            name="buy_pipeline",
            endpoint="/buy/start",
            payload={
                "user_id": "validation-buy-user",
                "input": {"query": "Nike vintage tee size M", "budget": 45},
                "metadata": {"source": "browser-use-validation"},
            },
        ),
    }


def run_browser_use_validation_suite(*, mode: str = "dry-run", selected_cases: list[str] | None = None) -> dict[str, Any]:
    cases = build_validation_cases()
    case_names = selected_cases or list(cases)

    results: list[dict[str, Any]] = []
    with browser_use_mode(mode):
        for case_name in case_names:
            if case_name not in cases:
                raise ValueError(f"Unknown validation case: {case_name}")
            results.append(cases[case_name]())

    return {
        "mode": mode,
        "case_count": len(results),
        "cases": results,
        "all_passed": all(case["status"] == "completed" for case in results),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backend-only Browser Use validation flows.")
    parser.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    parser.add_argument("--case", action="append", dest="cases", default=None, help="Validation case to run")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_browser_use_validation_suite(mode=args.mode, selected_cases=args.cases)
    import json

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
