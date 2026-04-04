from __future__ import annotations

from pathlib import Path

import backend.browser_use_runtime_audit as runtime_audit


def test_detect_chromium_installation_finds_cached_browser(tmp_path: Path) -> None:
    chromium_dir = tmp_path / "chromium-1234"
    chromium_dir.mkdir()

    installed, detail = runtime_audit.detect_chromium_installation([tmp_path])

    assert installed is True
    assert detail == str(chromium_dir)


def test_runtime_audit_passes_when_env_and_profiles_are_ready(tmp_path: Path, monkeypatch) -> None:
    for platform in runtime_audit.REQUIRED_PLATFORM_PROFILES:
        (tmp_path / platform).mkdir()

    monkeypatch.setenv("BROWSER_USE_PROFILE_ROOT", str(tmp_path))
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "secret")
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AGENT_EXECUTION_MODE", "local_functions")
    monkeypatch.setenv("BROWSER_USE_FORCE_FALLBACK", "false")
    monkeypatch.setattr(runtime_audit, "detect_chromium_installation", lambda search_roots=None: (True, "/tmp/chromium-1234"))

    report = runtime_audit.run_browser_use_runtime_audit()

    assert report["all_passed"] is True
    assert report["profiles"] == {
        "depop": True,
        "ebay": True,
        "mercari": True,
        "offerup": True,
    }
    assert all(check["passed"] for check in report["checks"])


def test_runtime_audit_flags_missing_profiles_and_low_timeout(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "depop").mkdir()

    monkeypatch.setenv("BROWSER_USE_PROFILE_ROOT", str(tmp_path))
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("INTERNAL_API_TOKEN", "secret")
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("AGENT_EXECUTION_MODE", "local_http")
    monkeypatch.setenv("BROWSER_USE_FORCE_FALLBACK", "true")
    monkeypatch.setattr(runtime_audit, "detect_chromium_installation", lambda search_roots=None: (False, "missing chromium"))

    report = runtime_audit.run_browser_use_runtime_audit()

    assert report["all_passed"] is False
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["chromium_installed"]["passed"] is False
    assert checks["google_api_key_configured"]["passed"] is False
    assert checks["platform_profiles_present"]["passed"] is False
    assert checks["agent_timeout_sane"]["passed"] is False
    assert checks["execution_mode_sane"]["passed"] is False
    assert checks["forced_fallback_disabled_for_live_runs"]["passed"] is False


def test_runtime_audit_main_returns_failure_code_when_checks_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_audit,
        "run_browser_use_runtime_audit",
        lambda: {"all_passed": False, "checks": [], "profiles": {}, "profile_root": "profiles"},
    )

    assert runtime_audit.main([]) == 1
