# Repository Guidelines

## Project Structure & Module Organization
`backend/` contains the FastAPI app, orchestration logic, shared schemas, session state, and agent implementations under `backend/agents/`. `tests/` mirrors backend behavior with endpoint, contract, agent, and resilience coverage. Top-level docs such as `README.md` and `backend/README.md` describe runtime behavior; `start.sh` boots the main app; `Makefile` is the standard entrypoint for local work.

## Build, Test, and Development Commands
- `make install`: create `.venv` and install `requirements.txt`.
- `make test`: run the pytest suite quietly.
- `make test-verbose`: run pytest with extra summary output.
- `make compile`: byte-compile `backend` and `tests` as a fast sanity check.
- `make check`: run the standard local verification path (`test` + `compile`).
- `make run`: start the main FastAPI backend through `start.sh`.
- `make run-agents`: start the separate per-agent FastAPI apps for integration checks.

## Coding Style & Naming Conventions
Use Python with 4-space indentation, type hints, and `from __future__ import annotations` where existing modules use it. Follow the current style: snake_case for functions, variables, and modules; PascalCase for Pydantic models and other classes; short, explicit docstrings or comments only when logic is not obvious. Keep imports grouped and prefer small, single-purpose functions over large handlers.

## Testing Guidelines
Tests use `pytest`, `pytest-asyncio`, and FastAPI `TestClient`. Add tests in `tests/` with filenames like `test_<feature>.py`; keep test names behavior-focused, for example `test_buy_search_agent_retries_once_and_completes`. Cover both happy paths and contract or failure cases when changing orchestrator or agent behavior. Run `make check` before opening a PR.

## Commit & Pull Request Guidelines
Recent history uses short imperative commit subjects such as `Implement buy decision agents and orchestration resilience`. Keep commits scoped to one change and use the same style. PRs should include a brief summary, note any API or contract changes, link the relevant issue or task, and include sample requests or screenshots when endpoint behavior changes are user-visible.

## Configuration & Runtime Notes
The app is currently designed for local development with in-memory sessions. Keep `AGENT_EXECUTION_MODE=local_functions` for the simplest workflow; use `make run-agents` only when validating per-agent `/task` apps. Do not commit secrets or local `.venv` artifacts.
