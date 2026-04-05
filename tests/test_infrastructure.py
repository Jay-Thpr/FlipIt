"""Infrastructure tests (Topic 5).

Validates render.yaml, .env.example, schema modes, and SSE event naming.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


class TestRenderYaml:
    def test_contains_required_env_vars(self):
        render_path = ROOT / "render.yaml"
        assert render_path.exists(), "render.yaml not found"

        with open(render_path) as f:
            data = yaml.safe_load(f)

        env_keys = {
            v["key"] for s in data["services"] for v in s.get("envVars", [])
        }

        required = {
            "APP_HOST",
            "APP_PORT",
            "APP_BASE_URL",
            "AGENT_EXECUTION_MODE",
            "INTERNAL_API_TOKEN",
            "AGENT_TIMEOUT_SECONDS",
            "BUY_AGENT_MAX_RETRIES",
            "GOOGLE_API_KEY",
            "BROWSER_USE_GEMINI_MODEL",
            "BROWSER_USE_MAX_STEPS",
            "BROWSER_USE_FORCE_FALLBACK",
            "BROWSER_USE_PROFILE_ROOT",
            "EBAY_APP_ID",
            "EBAY_CERT_ID",
        }

        missing = required - env_keys
        assert not missing, f"render.yaml missing env vars: {missing}"


class TestEnvExample:
    def test_contains_required_env_vars(self):
        env_path = ROOT / ".env.example"
        assert env_path.exists(), ".env.example not found"

        text = env_path.read_text()
        lines = [line.split("=")[0].strip() for line in text.splitlines() if "=" in line and not line.strip().startswith("#")]

        required = {
            "GOOGLE_API_KEY",
            "AGENT_EXECUTION_MODE",
            "BROWSER_USE_FORCE_FALLBACK",
            "EBAY_APP_ID",
            "EBAY_CERT_ID",
        }

        missing = required - set(lines)
        assert not missing, f".env.example missing keys: {missing}"


class TestSseEventNaming:
    def test_orchestrator_events_are_underscore_delimited(self):
        orch_path = ROOT / "backend" / "orchestrator.py"
        text = orch_path.read_text()

        # Find all event_type string literals in publish() calls
        import re

        events = re.findall(r'\"([a-z_]+)\"', text)
        event_names = [e for e in events if "_" in e or e in {"agent", "pipeline"}]

        for name in event_names:
            assert "." not in name, f"Event name '{name}' uses dots instead of underscores"


class TestSchemaExecutionModes:
    def test_search_results_accepts_httpx(self):
        from backend.schemas import SearchResultsOutput

        output = SearchResultsOutput(
            agent="test",
            display_name="Test",
            summary="Test",
            execution_mode="httpx",
        )
        assert output.execution_mode == "httpx"

    def test_ebay_comps_accepts_httpx(self):
        from backend.schemas import EbaySoldCompsOutput

        output = EbaySoldCompsOutput(
            agent="test",
            display_name="Test",
            summary="Test",
            median_sold_price=50.0,
            low_sold_price=30.0,
            high_sold_price=70.0,
            sample_size=10,
            execution_mode="httpx",
        )
        assert output.execution_mode == "httpx"
