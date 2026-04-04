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
from backend.config import AGENT_TIMEOUT_SECONDS, INTERNAL_API_TOKEN

PROFILE_NAMES = ("depop", "ebay", "mercari", "offerup")


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

    timeout_ok = AGENT_TIMEOUT_SECONDS >= 30
    checks.append(
        _check(
            "agent_timeout",
            timeout_ok,
            f"AGENT_TIMEOUT_SECONDS={AGENT_TIMEOUT_SECONDS}",
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

    token_is_default = INTERNAL_API_TOKEN == "dev-internal-token"
    checks.append(
        _check(
            "internal_api_token",
            not token_is_default,
            "INTERNAL_API_TOKEN is configured" if not token_is_default else "INTERNAL_API_TOKEN is still using the dev default",
            severity="warning",
        )
    )

    google_api_key = os.getenv("GOOGLE_API_KEY")
    checks.append(
        _check(
            "google_api_key",
            bool(google_api_key),
            "GOOGLE_API_KEY is configured" if google_api_key else "GOOGLE_API_KEY is missing",
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

    errors = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warn"]

    return {
        "passed": not errors,
        "require_live": require_live,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def build_cli(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Browser Use runtime readiness.")
    parser.add_argument("--require-live", action="store_true", help="Fail if live Browser Use prerequisites are missing.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a text summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = build_cli(argv)
    report = audit_browser_use_runtime(require_live=args.require_live)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"Browser Use runtime audit: {'passed' if report['passed'] else 'failed'} "
            f"(errors={report['error_count']} warnings={report['warning_count']})"
        )
        for check in report["checks"]:
            print(f"- {check['name']}: {check['status']} ({check['detail']})")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
