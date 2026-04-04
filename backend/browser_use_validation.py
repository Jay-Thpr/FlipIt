from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from backend.main import app as backend_app
from backend.agents.depop_listing_agent import app as depop_listing_app
from backend.agents.depop_search_agent import app as depop_search_app
from backend.agents.ebay_search_agent import app as ebay_search_app
from backend.agents.ebay_sold_comps_agent import app as ebay_sold_comps_app
from backend.agents.mercari_search_agent import app as mercari_search_app
from backend.agents.negotiation_agent import app as negotiation_app
from backend.agents.offerup_search_agent import app as offerup_search_app


@dataclass(frozen=True)
class ValidationScenario:
    name: str
    group: str
    agent_slug: str
    description: str
    payload: dict[str, Any]
    runner: str = "agent"
    endpoint: str = "/task"
    result_step: str | None = None


def _buy_previous_outputs() -> dict[str, Any]:
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
            "browser_use_error": "profile_missing",
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
            "browser_use_error": "unknown",
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
            "browser_use_error": "profile_missing",
        },
    }


def _sell_previous_outputs() -> dict[str, Any]:
    return {
        "vision_analysis": {
            "agent": "vision_agent",
            "display_name": "Vision Agent",
            "summary": "Inferred Patagonia hoodie in excellent condition",
            "detected_item": "hoodie",
            "brand": "Patagonia",
            "category": "apparel",
            "condition": "excellent",
            "confidence": 0.88,
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


def get_validation_scenarios() -> dict[str, ValidationScenario]:
    buy_previous_outputs = _buy_previous_outputs()
    sell_previous_outputs = _sell_previous_outputs()
    return {
        "ebay_sold_comps": ValidationScenario(
            name="ebay_sold_comps",
            group="sell",
            agent_slug="ebay_sold_comps_agent",
            description="Validate eBay sold comps research or deterministic fallback.",
            payload={
                "session_id": "validate-ebay-sold-comps",
                "pipeline": "sell",
                "step": "ebay_sold_comps",
                "input": {"original_input": {"image_urls": [], "notes": None}, "previous_outputs": {"vision_analysis": sell_previous_outputs["vision_analysis"]}},
                "context": {"request_metadata": {"source": "browser-use-validation"}},
            },
        ),
        "depop_search": ValidationScenario(
            name="depop_search",
            group="buy_search",
            agent_slug="depop_search_agent",
            description="Validate Depop Browser Use search or fallback listing generation.",
            payload={
                "session_id": "validate-depop-search",
                "pipeline": "buy",
                "step": "depop_search",
                "input": {"original_input": {"query": "Nike vintage tee size M", "budget": 45}, "previous_outputs": {}},
                "context": {"request_metadata": {"source": "browser-use-validation"}},
            },
        ),
        "ebay_search": ValidationScenario(
            name="ebay_search",
            group="buy_search",
            agent_slug="ebay_search_agent",
            description="Validate eBay Browser Use search or fallback listing generation.",
            payload={
                "session_id": "validate-ebay-search",
                "pipeline": "buy",
                "step": "ebay_search",
                "input": {
                    "original_input": {"query": "Nike vintage tee size M", "budget": 45},
                    "previous_outputs": {},
                },
                "context": {"request_metadata": {"source": "browser-use-validation"}},
            },
        ),
        "mercari_search": ValidationScenario(
            name="mercari_search",
            group="buy_search",
            agent_slug="mercari_search_agent",
            description="Validate Mercari Browser Use search or fallback listing generation.",
            payload={
                "session_id": "validate-mercari-search",
                "pipeline": "buy",
                "step": "mercari_search",
                "input": {
                    "original_input": {"query": "Nike vintage tee size M", "budget": 45},
                    "previous_outputs": {},
                },
                "context": {"request_metadata": {"source": "browser-use-validation"}},
            },
        ),
        "offerup_search": ValidationScenario(
            name="offerup_search",
            group="buy_search",
            agent_slug="offerup_search_agent",
            description="Validate OfferUp Browser Use search or fallback listing generation.",
            payload={
                "session_id": "validate-offerup-search",
                "pipeline": "buy",
                "step": "offerup_search",
                "input": {
                    "original_input": {"query": "Nike vintage tee size M", "budget": 45},
                    "previous_outputs": {},
                },
                "context": {"request_metadata": {"source": "browser-use-validation"}},
            },
        ),
        "depop_listing": ValidationScenario(
            name="depop_listing",
            group="sell",
            agent_slug="depop_listing_agent",
            description="Validate Depop draft creation or deterministic draft fallback.",
            payload={
                "session_id": "validate-depop-listing",
                "pipeline": "sell",
                "step": "depop_listing",
                "input": {
                    "original_input": {"image_urls": [], "notes": "Patagonia hoodie in excellent condition"},
                    "previous_outputs": sell_previous_outputs,
                },
                "context": {"request_metadata": {"source": "browser-use-validation"}},
            },
        ),
        "negotiation": ValidationScenario(
            name="negotiation",
            group="buy_decision",
            agent_slug="negotiation_agent",
            description="Validate per-listing offer preparation or live send flow.",
            payload={
                "session_id": "validate-negotiation",
                "pipeline": "buy",
                "step": "negotiation",
                "input": {
                    "original_input": {"query": "Nike vintage tee size M", "budget": 45},
                    "previous_outputs": {
                        **buy_previous_outputs,
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
                    },
                },
                "context": {"request_metadata": {"source": "browser-use-validation"}},
            },
        ),
        "sell_pipeline": ValidationScenario(
            name="sell_pipeline",
            group="pipeline",
            agent_slug="backend",
            description="Validate the full sell pipeline and inspect the final Depop listing step.",
            payload={
                "user_id": "validation-sell-user",
                "input": {
                    "image_urls": ["https://images.example.com/patagonia-hoodie-excellent.jpg"],
                    "notes": "Patagonia hoodie in excellent condition",
                },
                "metadata": {"source": "browser-use-validation"},
            },
            runner="pipeline",
            endpoint="/sell/start",
            result_step="depop_listing",
        ),
        "buy_pipeline": ValidationScenario(
            name="buy_pipeline",
            group="pipeline",
            agent_slug="backend",
            description="Validate the full buy pipeline and inspect the final negotiation step.",
            payload={
                "user_id": "validation-buy-user",
                "input": {"query": "Nike vintage tee size M", "budget": 45},
                "metadata": {"source": "browser-use-validation"},
            },
            runner="pipeline",
            endpoint="/buy/start",
            result_step="negotiation",
        ),
    }


def get_group_names() -> dict[str, list[str]]:
    scenarios = get_validation_scenarios()
    groups: dict[str, list[str]] = {"all": list(scenarios)}
    for name, scenario in scenarios.items():
        groups.setdefault(scenario.group, []).append(name)
    return groups


def get_agent_app(agent_slug: str):
    return {
        "ebay_sold_comps_agent": ebay_sold_comps_app,
        "depop_search_agent": depop_search_app,
        "ebay_search_agent": ebay_search_app,
        "mercari_search_agent": mercari_search_app,
        "offerup_search_agent": offerup_search_app,
        "depop_listing_agent": depop_listing_app,
        "negotiation_agent": negotiation_app,
    }[agent_slug]


def _get_scenario_app(scenario: ValidationScenario):
    if scenario.runner == "pipeline":
        return backend_app
    return get_agent_app(scenario.agent_slug)


def _wait_for_terminal_pipeline_result(client: TestClient, session_id: str, timeout: float = 3.0) -> dict[str, Any]:
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Validation session {session_id} did not reach a terminal state")


def _extract_execution_mode(output: dict[str, Any]) -> str | None:
    if "execution_mode" in output:
        return output.get("execution_mode")
    offers = output.get("offers")
    if isinstance(offers, list):
        modes = {offer.get("execution_mode") for offer in offers}
        if "browser_use" in modes:
            return "browser_use"
        if modes:
            return next(iter(modes))
    return None


def _extract_browser_use_error(output: dict[str, Any]) -> str | None:
    if output.get("browser_use_error"):
        return str(output["browser_use_error"])
    offers = output.get("offers")
    if isinstance(offers, list):
        for offer in offers:
            if offer.get("browser_use_error"):
                return str(offer["browser_use_error"])
    return None


def _run_single_scenario(scenario: ValidationScenario, *, require_live: bool) -> dict[str, Any]:
    app = _get_scenario_app(scenario)
    with TestClient(app) as client:
        response = client.post(scenario.endpoint, json=scenario.payload)
        payload = response.json()
        if scenario.runner == "pipeline" and response.status_code == 200:
            pipeline_result = _wait_for_terminal_pipeline_result(client, payload["session_id"])
            output = pipeline_result["result"]["outputs"][scenario.result_step] if scenario.result_step else pipeline_result["result"]
            task_status = pipeline_result["status"]
            summary = output.get("summary")
            extra = {"session_id": payload["session_id"]}
        else:
            output = payload.get("output", {})
            task_status = payload.get("status")
            summary = output.get("summary")
            extra = {}

    execution_mode = _extract_execution_mode(output)
    passed = response.status_code == 200 and task_status == "completed"
    if require_live:
        passed = passed and execution_mode == "browser_use"

    return {
        "scenario": scenario.name,
        "group": scenario.group,
        "agent_slug": scenario.agent_slug,
        "description": scenario.description,
        "runner": scenario.runner,
        "http_status": response.status_code,
        "task_status": task_status,
        "passed": passed,
        "execution_mode": execution_mode,
        "browser_use_error": _extract_browser_use_error(output),
        "summary": summary,
        **extra,
    }


def run_validation_suite(
    *,
    scenario_names: list[str] | None = None,
    groups: list[str] | None = None,
    require_live: bool = False,
) -> dict[str, Any]:
    scenarios = get_validation_scenarios()
    group_names = get_group_names()

    selected_names: list[str]
    if scenario_names:
        selected_names = scenario_names[:]
    elif groups:
        selected_names = []
        for group in groups:
            selected_names.extend(group_names[group])
    else:
        selected_names = group_names["all"]

    deduped_names = list(dict.fromkeys(selected_names))
    results = [_run_single_scenario(scenarios[name], require_live=require_live) for name in deduped_names]
    passed = all(result["passed"] for result in results)
    return {
        "passed": passed,
        "require_live": require_live,
        "selected_scenarios": deduped_names,
        "result_count": len(results),
        "results": results,
    }


def build_cli(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backend Browser Use validation scenarios.")
    parser.add_argument("--scenario", action="append", default=[], help="Scenario name to run. Repeatable.")
    parser.add_argument("--group", action="append", default=[], help="Scenario group to run. Repeatable.")
    parser.add_argument("--mode", choices=("auto", "fallback"), default="auto", help="Execution mode for this process.")
    parser.add_argument("--require-live", action="store_true", help="Fail unless each selected scenario executes in browser_use mode.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = build_cli(argv)
    if args.mode == "fallback":
        os.environ["BROWSER_USE_FORCE_FALLBACK"] = "true"

    report = run_validation_suite(
        scenario_names=args.scenario or None,
        groups=args.group or None,
        require_live=args.require_live,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"Browser Use validation: {'passed' if report['passed'] else 'failed'} "
            f"({report['result_count']} scenario{'s' if report['result_count'] != 1 else ''})"
        )
        for result in report["results"]:
            print(
                f"- {result['scenario']}: {'passed' if result['passed'] else 'failed'} "
                f"[mode={result['execution_mode'] or 'n/a'} error={result['browser_use_error'] or 'none'}]"
            )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
