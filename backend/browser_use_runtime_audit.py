from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from backend.agents.browser_use_support import (
    get_browser_profile_root,
    get_browser_use_max_steps,
    import_browser_use_dependencies,
)
from backend.config import get_agent_execution_mode, get_agent_timeout_seconds, get_gemini_api_key

PROFILE_NAMES = ("depop", "ebay", "mercari", "offerup")
REQUIRED_PLATFORM_PROFILES = PROFILE_NAMES


def _status(ok: bool) -> str:
    return "pass" if ok else "fail"


def _check(name: str, ok: bool, detail: str, *, severity: str = "error") -> dict[str, str]:
    return {
        "name": name,
        "status": _status(ok) if severity == "error" else ("pass" if ok else "warn"),
        "severity": severity,
        "detail": detail,
    }


def audit_browser_use_runtime(*, require_live: bool = False) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    timeout_seconds = get_agent_timeout_seconds()
    timeout_ok = timeout_seconds >= 30
    checks.append(
        _check(
            "agent_timeout",
            timeout_ok,
            f"AGENT_TIMEOUT_SECONDS={timeout_seconds}",
        )
    )

    max_steps = get_browser_use_max_steps()
    checks.append(
        _check(
            "browser_use_max_steps",
            max_steps > 0,
            f"BROWSER_USE_MAX_STEPS={max_steps}",
        )
    )

    internal_api_token = os.getenv("INTERNAL_API_TOKEN", "dev-internal-token")
    token_is_default = internal_api_token == "dev-internal-token"
    checks.append(
        _check(
            "internal_api_token",
            not token_is_default,
            "INTERNAL_API_TOKEN is configured" if not token_is_default else "INTERNAL_API_TOKEN is still using the dev default",
            severity="warning",
        )
    )

    gemini_api_key = get_gemini_api_key()
    checks.append(
        _check(
            "google_api_key",
            bool(gemini_api_key),
            (
                "GEMINI_API_KEY or GOOGLE_API_KEY is configured"
                if gemini_api_key
                else "GEMINI_API_KEY or GOOGLE_API_KEY is missing"
            ),
            severity="error" if require_live else "warning",
        )
    )

    execution_mode = get_agent_execution_mode()
    checks.append(
        _check(
            "execution_mode",
            execution_mode == "local_functions",
            f"AGENT_EXECUTION_MODE={execution_mode}",
        )
    )

    forced_fallback = os.getenv("BROWSER_USE_FORCE_FALLBACK", "false").strip().lower() == "true"
    checks.append(
        _check(
            "forced_fallback",
            not forced_fallback,
            "BROWSER_USE_FORCE_FALLBACK is disabled" if not forced_fallback else "BROWSER_USE_FORCE_FALLBACK=true",
            severity="error" if require_live else "warning",
        )
    )

    try:
        import_browser_use_dependencies()
    except Exception as exc:
        checks.append(
            _check(
                "browser_use_dependencies",
                False,
                f"Browser Use imports failed: {exc}",
                severity="error" if require_live else "warning",
            )
        )
    else:
        checks.append(
            _check(
                "browser_use_dependencies",
                True,
                "Browser Use dependencies imported successfully",
                severity="warning",
            )
        )

    profile_root = get_browser_profile_root()
    checks.append(
        _check(
            "profile_root",
            profile_root.exists(),
            f"profile root: {profile_root}",
            severity="error" if require_live else "warning",
        )
    )
    for profile_name in PROFILE_NAMES:
        profile_path = profile_root / profile_name
        checks.append(
            _check(
                f"profile_{profile_name}",
                profile_path.exists(),
                f"profile path: {profile_path}",
                severity="error" if require_live else "warning",
            )
        )

    chromium_installed, chromium_detail = detect_chromium_installation()
    checks.append(
        _check(
            "chromium",
            chromium_installed,
            chromium_detail,
            severity="error" if require_live else "warning",
        )
    )

    errors = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warn"]

    return {
        "passed": not errors,
        "require_live": require_live,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def detect_chromium_installation(search_roots: list[Path] | None = None) -> tuple[bool, str]:
    roots = search_roots or [
        Path.home() / ".cache" / "ms-playwright",
        Path.home() / ".cache" / "patchright",
    ]
    for root in roots:
        if not root.exists():
            continue
        matches = sorted(root.glob("chromium-*"))
        if matches:
            return True, str(matches[-1])
    return False, "chromium cache not found"


def run_browser_use_runtime_audit(*, require_live: bool = False) -> dict[str, Any]:
    profiles = {
        profile_name: (get_browser_profile_root() / profile_name).exists()
        for profile_name in REQUIRED_PLATFORM_PROFILES
    }
    chromium_installed, chromium_detail = detect_chromium_installation()
    checks = []
    checks.append(
        {
            "name": "chromium_installed",
            "passed": chromium_installed,
            "detail": chromium_detail,
        }
    )
    checks.append(
        {
            "name": "google_api_key_configured",
            "passed": bool(get_gemini_api_key()),
            "detail": (
                "GEMINI_API_KEY or GOOGLE_API_KEY is configured"
                if get_gemini_api_key()
                else "GEMINI_API_KEY or GOOGLE_API_KEY is missing"
            ),
        }
    )
    checks.append(
        {
            "name": "platform_profiles_present",
            "passed": all(profiles.values()),
            "detail": json.dumps(profiles, sort_keys=True),
        }
    )
    checks.append(
        {
            "name": "agent_timeout_sane",
            "passed": get_agent_timeout_seconds() >= 30,
            "detail": f"AGENT_TIMEOUT_SECONDS={get_agent_timeout_seconds()}",
        }
    )
    checks.append(
        {
            "name": "execution_mode_sane",
            "passed": get_agent_execution_mode() == "local_functions",
            "detail": f"AGENT_EXECUTION_MODE={get_agent_execution_mode()}",
        }
    )
    checks.append(
        {
            "name": "forced_fallback_disabled_for_live_runs",
            "passed": os.getenv("BROWSER_USE_FORCE_FALLBACK", "false").strip().lower() != "true",
            "detail": f"BROWSER_USE_FORCE_FALLBACK={os.getenv('BROWSER_USE_FORCE_FALLBACK', 'false')}",
        }
    )
    return {
        "all_passed": all(check["passed"] for check in checks),
        "checks": checks,
        "profiles": profiles,
        "profile_root": str(get_browser_profile_root()),
    }


def build_cli(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Browser Use runtime readiness.")
    parser.add_argument("--require-live", action="store_true", help="Fail if live Browser Use prerequisites are missing.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = build_cli(argv)
    report = audit_browser_use_runtime(require_live=args.require_live)
    legacy_report = (
        run_browser_use_runtime_audit(require_live=True)
        if args.require_live
        else run_browser_use_runtime_audit()
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"Browser Use runtime audit: {'passed' if legacy_report['all_passed'] else 'failed'} "
            f"(profiles={legacy_report['profile_root']})"
        )
        for check in legacy_report["checks"]:
            print(f"- {check['name']}: {'pass' if check['passed'] else 'fail'} ({check['detail']})")
    if args.json:
        return 0 if report["passed"] else 1
    if not legacy_report["all_passed"]:
        return 1
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
