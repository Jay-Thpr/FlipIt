from __future__ import annotations

import json

from backend import browser_use_runtime_audit


def test_runtime_audit_warns_without_live_prerequisites(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("INTERNAL_API_TOKEN", "dev-internal-token")
    monkeypatch.setenv("BROWSER_USE_PROFILE_ROOT", "missing-profiles")

    report = browser_use_runtime_audit.audit_browser_use_runtime(require_live=False)

    assert report["passed"] is True
    assert report["warning_count"] >= 1
    assert any(check["name"] == "google_api_key" and check["status"] == "warn" for check in report["checks"])


def test_runtime_audit_fails_when_live_mode_is_required(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("BROWSER_USE_PROFILE_ROOT", "missing-profiles")

    report = browser_use_runtime_audit.audit_browser_use_runtime(require_live=True)

    assert report["passed"] is False
    assert report["error_count"] >= 1
    assert any(check["name"] == "google_api_key" and check["status"] == "fail" for check in report["checks"])


def test_runtime_audit_cli_outputs_json(capsys, monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    exit_code = browser_use_runtime_audit.main(["--json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert "checks" in payload


def test_runtime_audit_cli_returns_failure_when_live_required(capsys, monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("BROWSER_USE_PROFILE_ROOT", "missing-profiles")

    exit_code = browser_use_runtime_audit.main(["--require-live"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Browser Use runtime audit: failed" in captured.out
