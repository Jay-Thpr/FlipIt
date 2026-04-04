from __future__ import annotations

import backend.browser_use_validation as validation


def test_validation_suite_runs_default_cases_in_dry_run_mode(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_USE_FORCE_FALLBACK", raising=False)

    result = validation.run_browser_use_validation_suite(mode="dry-run")

    assert result["mode"] == "dry-run"
    assert result["case_count"] == 9
    assert result["all_passed"] is True
    assert {case["name"] for case in result["cases"]} == {
        "ebay_sold_comps_agent",
        "depop_search_agent",
        "ebay_search_agent",
        "mercari_search_agent",
        "offerup_search_agent",
        "depop_listing_agent",
        "negotiation_agent",
        "sell_pipeline",
        "buy_pipeline",
    }
    buy_pipeline = next(case for case in result["cases"] if case["name"] == "buy_pipeline")
    assert buy_pipeline["kind"] == "pipeline"
    assert "listing_found" in buy_pipeline["event_types"]
    assert "offer_prepared" in buy_pipeline["event_types"]


def test_validation_suite_restores_browser_force_fallback_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_USE_FORCE_FALLBACK", "false")

    validation.run_browser_use_validation_suite(mode="dry-run", selected_cases=["depop_search_agent"])

    assert validation.os.getenv("BROWSER_USE_FORCE_FALLBACK") == "false"


def test_validation_suite_can_run_selected_case_only(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_USE_FORCE_FALLBACK", raising=False)

    result = validation.run_browser_use_validation_suite(mode="dry-run", selected_cases=["sell_pipeline"])

    assert result["mode"] == "dry-run"
    assert result["case_count"] == 1
    assert result["all_passed"] is True
    assert len(result["cases"]) == 1
    assert result["cases"][0]["name"] == "sell_pipeline"
    assert result["cases"][0]["status"] == "completed"
    assert "draft_created" in result["cases"][0]["event_types"]


def test_validation_suite_rejects_unknown_case() -> None:
    try:
        validation.run_browser_use_validation_suite(mode="dry-run", selected_cases=["unknown_case"])
    except ValueError as exc:
        assert str(exc) == "Unknown validation case: unknown_case"
    else:
        raise AssertionError("Expected ValueError for unknown validation case")
