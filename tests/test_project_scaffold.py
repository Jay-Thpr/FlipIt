from __future__ import annotations

from pathlib import Path
import re

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_makefile_exposes_expected_build_targets() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()

    for target in ("install:", "test:", "compile:", "check:", "run:", "run-agents:", "ci:"):
        assert target in makefile


def test_start_script_launches_backend_entrypoint() -> None:
    start_script = (REPO_ROOT / "start.sh").read_text()

    assert 'uvicorn backend.main:app' in start_script
    assert 'APP_HOST:-0.0.0.0' in start_script
    assert 'APP_PORT:-8000' in start_script


def test_env_example_contains_required_runtime_variables() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text()

    for variable in (
        "APP_HOST=",
        "APP_PORT=",
        "APP_BASE_URL=",
        "AGENT_HOST=",
        "AGENT_EXECUTION_MODE=",
        "INTERNAL_API_TOKEN=",
        "AGENT_TIMEOUT_SECONDS=",
        "BUY_AGENT_MAX_RETRIES=",
        "GOOGLE_API_KEY=",
        "ANONYMIZED_TELEMETRY=",
        "BROWSER_USE_GEMINI_MODEL=",
        "BROWSER_USE_PROFILE_ROOT=",
        "BROWSER_USE_MAX_STEPS=",
        "BROWSER_USE_FORCE_FALLBACK=",
    ):
        assert variable in env_example


def test_gitignore_excludes_local_env_files() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text()

    assert ".env" in gitignore


def test_render_config_matches_backend_runtime_contract() -> None:
    render_config = yaml.safe_load((REPO_ROOT / "render.yaml").read_text())

    assert "services" in render_config
    assert len(render_config["services"]) == 1

    service = render_config["services"][0]
    assert service["type"] == "web"
    assert service["runtime"] == "python"
    assert "pip install -r requirements.txt" in service["buildCommand"]
    assert "python -m patchright install chromium" in service["buildCommand"]
    assert service["startCommand"] == "./start.sh"

    env_vars = {item["key"]: item for item in service["envVars"]}
    assert env_vars["APP_HOST"]["value"] == "0.0.0.0"
    assert env_vars["APP_PORT"]["value"] == "10000"
    assert env_vars["APP_BASE_URL"]["value"] == "https://diamondhacks-backend.onrender.com"
    assert env_vars["AGENT_EXECUTION_MODE"]["value"] == "local_functions"
    assert env_vars["INTERNAL_API_TOKEN"]["sync"] is False
    assert env_vars["AGENT_TIMEOUT_SECONDS"]["value"] == "60"
    assert env_vars["BUY_AGENT_MAX_RETRIES"]["value"] == "1"
    assert env_vars["GOOGLE_API_KEY"]["sync"] is False
    assert env_vars["ANONYMIZED_TELEMETRY"]["value"] == "false"
    assert env_vars["BROWSER_USE_GEMINI_MODEL"]["value"] == "gemini-2.0-flash"
    assert env_vars["BROWSER_USE_MAX_STEPS"]["value"] == "15"
    assert env_vars["BROWSER_USE_FORCE_FALLBACK"]["value"] == "false"


def test_requirements_pin_browser_use_runtime_dependencies() -> None:
    requirements = (REPO_ROOT / "requirements.txt").read_text()

    assert re.search(r"^browser-use==[^\s]+$", requirements, flags=re.MULTILINE)
    assert re.search(r"^langchain-google-genai==[^\s]+$", requirements, flags=re.MULTILINE)
    assert re.search(r"^patchright==[^\s]+$", requirements, flags=re.MULTILINE)


def test_readme_documents_render_browser_runtime_requirements() -> None:
    readme = (REPO_ROOT / "README.md").read_text()

    assert "Browser Use Deployment Notes" in readme
    assert "Render" in readme
    assert "paid" in readme.lower()
    assert "Chromium" in readme
    assert "GOOGLE_API_KEY" in readme
    assert "BrowserUse-Live-Validation.md" in readme


def test_browser_use_docs_and_scripts_exist() -> None:
    status = (REPO_ROOT / "BrowserUse-Status.md").read_text()
    live_validation = (REPO_ROOT / "BrowserUse-Live-Validation.md").read_text()

    assert "listing_found" in status
    assert "browser_use_fallback" in status
    assert "backend.browser_use_runtime_audit" in status
    assert "Preconditions" in live_validation
    assert "BUY Flow" in live_validation
    assert "SELL Flow" in live_validation
    assert (REPO_ROOT / "scripts/browser_use_validation.py").exists()
    assert (REPO_ROOT / "scripts/browser_use_runtime_audit.py").exists()


def test_claude_documents_current_sse_event_names() -> None:
    claude = (REPO_ROOT / "CLAUDE.md").read_text()

    assert "underscore-delimited SSE event names" in claude
    assert "`pipeline_started`, `pipeline_complete`, `pipeline_failed`" in claude
    assert "`agent_started`, `agent_completed`, `agent_error`, `agent_retrying`" in claude
    assert "pipeline.started" not in claude
    assert "agent.failed" not in claude


def test_ci_workflow_runs_repo_verification_steps() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/backend-ci.yml").read_text())

    assert workflow["name"] == "Backend CI"
    test_job = workflow["jobs"]["test"]
    assert test_job["runs-on"] == "ubuntu-latest"

    run_steps = [step["run"] for step in test_job["steps"] if "run" in step]
    assert "python -m pytest -q" in run_steps
    assert "python -m compileall backend tests" in run_steps
