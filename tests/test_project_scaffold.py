from __future__ import annotations

from pathlib import Path

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
    ):
        assert variable in env_example


def test_render_config_matches_backend_runtime_contract() -> None:
    render_config = yaml.safe_load((REPO_ROOT / "render.yaml").read_text())

    assert "services" in render_config
    assert len(render_config["services"]) == 1

    service = render_config["services"][0]
    assert service["type"] == "web"
    assert service["runtime"] == "python"
    assert service["buildCommand"] == "pip install -r requirements.txt"
    assert service["startCommand"] == "./start.sh"

    env_vars = {item["key"]: item["value"] for item in service["envVars"]}
    assert env_vars == {
        "APP_HOST": "0.0.0.0",
        "APP_PORT": "10000",
        "APP_BASE_URL": "https://diamondhacks-backend.onrender.com",
        "AGENT_EXECUTION_MODE": "local_functions",
    }


def test_ci_workflow_runs_repo_verification_steps() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/backend-ci.yml").read_text())

    assert workflow["name"] == "Backend CI"
    test_job = workflow["jobs"]["test"]
    assert test_job["runs-on"] == "ubuntu-latest"

    run_steps = [step["run"] for step in test_job["steps"] if "run" in step]
    assert "python -m pytest -q" in run_steps
    assert "python -m compileall backend tests" in run_steps
