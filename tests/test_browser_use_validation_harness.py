from __future__ import annotations

import json
import os

from backend import browser_use_validation


def test_validation_suite_runs_named_scenarios() -> None:
    report = browser_use_validation.run_validation_suite(
        scenario_names=["depop_search", "depop_listing"],
    )

    assert report["passed"] is True
    assert report["selected_scenarios"] == ["depop_search", "depop_listing"]
    assert report["result_count"] == 2
    assert {result["scenario"] for result in report["results"]} == {"depop_search", "depop_listing"}


def test_validation_suite_filters_groups() -> None:
    report = browser_use_validation.run_validation_suite(groups=["buy_search"])

    assert report["passed"] is True
    assert report["result_count"] == 4
    assert {result["group"] for result in report["results"]} == {"buy_search"}


def test_validation_suite_runs_pipeline_scenarios() -> None:
    report = browser_use_validation.run_validation_suite(groups=["pipeline"])

    assert report["passed"] is True
    assert report["result_count"] == 2
    assert {result["scenario"] for result in report["results"]} == {"sell_pipeline", "buy_pipeline"}
    assert {result["runner"] for result in report["results"]} == {"pipeline"}
    assert all(result["session_id"] for result in report["results"])


def test_validation_suite_require_live_fails_without_live_runtime() -> None:
    report = browser_use_validation.run_validation_suite(
        scenario_names=["depop_search"],
        require_live=True,
    )

    assert report["passed"] is False
    assert report["results"][0]["execution_mode"] == "fallback"


def test_validation_cli_outputs_json_and_returns_failure_for_require_live(capsys) -> None:
    exit_code = browser_use_validation.main(["--scenario", "depop_search", "--require-live", "--json"])
    captured = capsys.readouterr()

    assert exit_code == 1
    payload = json.loads(captured.out)
    assert payload["passed"] is False
    assert payload["selected_scenarios"] == ["depop_search"]


def test_validation_cli_fallback_mode_sets_env_and_passes(capsys, monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_USE_FORCE_FALLBACK", raising=False)

    exit_code = browser_use_validation.main(["--scenario", "depop_search", "--mode", "fallback"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Browser Use validation: passed" in captured.out
    assert os.environ["BROWSER_USE_FORCE_FALLBACK"] == "true"


def test_validation_cli_runs_pipeline_scenario_in_json_mode(capsys) -> None:
    exit_code = browser_use_validation.main(["--scenario", "sell_pipeline", "--json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["passed"] is True
    assert payload["selected_scenarios"] == ["sell_pipeline"]
    assert payload["results"][0]["runner"] == "pipeline"
