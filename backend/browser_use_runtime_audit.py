from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from backend.agents.browser_use_support import env_flag, get_browser_profile_root
from backend.config import get_agent_execution_mode, get_agent_timeout_seconds

REQUIRED_PLATFORM_PROFILES = ("depop", "ebay", "mercari", "offerup")


def candidate_chromium_roots() -> list[Path]:
    home = Path.home()
    roots = [
        Path(os.getenv("PLAYWRIGHT_BROWSERS_PATH", "")),
        home / "Library" / "Caches" / "ms-playwright",
        home / ".cache" / "ms-playwright",
        Path("/opt/render/.cache/ms-playwright"),
    ]
    return [root for root in roots if str(root)]


def detect_chromium_installation(search_roots: list[Path] | None = None) -> tuple[bool, str]:
    roots = search_roots or candidate_chromium_roots()
    for root in roots:
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.name.startswith("chromium-"):
                return True, str(child)
    return False, "Chromium browser bundle was not found in the Patchright/Playwright cache roots"


def collect_profile_status(profile_root: Path) -> dict[str, bool]:
    return {platform: (profile_root / platform).exists() for platform in REQUIRED_PLATFORM_PROFILES}


def build_check(*, name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def run_browser_use_runtime_audit() -> dict[str, Any]:
    profile_root = get_browser_profile_root()
    profile_status = collect_profile_status(profile_root)
    chromium_installed, chromium_detail = detect_chromium_installation()
    timeout_seconds = get_agent_timeout_seconds()
    execution_mode = get_agent_execution_mode()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    internal_token = os.getenv("INTERNAL_API_TOKEN")

    checks = [
        build_check(
            name="chromium_installed",
            passed=chromium_installed,
            detail=chromium_detail,
        ),
        build_check(
            name="google_api_key_configured",
            passed=bool(google_api_key),
            detail="GOOGLE_API_KEY is configured" if google_api_key else "GOOGLE_API_KEY is missing",
        ),
        build_check(
            name="profile_root_exists",
            passed=profile_root.exists(),
            detail=f"Profile root: {profile_root}",
        ),
        build_check(
            name="platform_profiles_present",
            passed=all(profile_status.values()),
            detail=", ".join(f"{platform}={'ok' if exists else 'missing'}" for platform, exists in profile_status.items()),
        ),
        build_check(
            name="agent_timeout_sane",
            passed=timeout_seconds >= 30.0,
            detail=f"AGENT_TIMEOUT_SECONDS={timeout_seconds}",
        ),
        build_check(
            name="execution_mode_sane",
            passed=execution_mode == "local_functions",
            detail=f"AGENT_EXECUTION_MODE={execution_mode}",
        ),
        build_check(
            name="internal_token_configured",
            passed=bool(internal_token),
            detail="INTERNAL_API_TOKEN is configured" if internal_token else "INTERNAL_API_TOKEN is missing",
        ),
        build_check(
            name="forced_fallback_disabled_for_live_runs",
            passed=not env_flag("BROWSER_USE_FORCE_FALLBACK", default=False),
            detail=(
                "BROWSER_USE_FORCE_FALLBACK=false"
                if not env_flag("BROWSER_USE_FORCE_FALLBACK", default=False)
                else "BROWSER_USE_FORCE_FALLBACK=true"
            ),
        ),
    ]

    return {
        "all_passed": all(check["passed"] for check in checks),
        "profile_root": str(profile_root),
        "profiles": profile_status,
        "checks": checks,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Browser Use runtime prerequisites.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(argv)
    report = run_browser_use_runtime_audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
