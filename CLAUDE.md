# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install        # create .venv and install requirements.txt
make check          # run tests + compile (standard local verification)
make test           # run pytest quietly
make test-verbose   # run pytest with full summary (-ra)
make compile        # byte-compile backend/ and tests/ as a quick sanity check
make run            # start FastAPI via start.sh
make run-agents     # start all 10 per-agent FastAPI apps as subprocesses
```

Run a single test file:
```bash
. .venv/bin/activate && python -m pytest tests/test_<name>.py -q
```

Run a single test by name:
```bash
. .venv/bin/activate && python -m pytest -k "test_function_name" -q
```

## Architecture

### What This Is
A FastAPI backend for a two-sided autonomous resale agent ("FILLER") built for DiamondHacks 2026. It runs a **SELL** pipeline (scan thrift item → price it → draft Depop listing) and a **BUY** pipeline (search 4 resale platforms → rank listings → send haggling offers). 6 of 10 agents use Browser Use for browser automation.

### Execution Modes
`AGENT_EXECUTION_MODE` (env var, default `local_functions`) controls how the orchestrator calls agents:
- `local_functions` — agents are called as in-process async functions (no HTTP, no subprocesses needed)
- `local_http` — orchestrator POSTs to each agent's FastAPI task server at its fixed port (`backend/config.py` `AGENT_PORTS`, ports 9101–9110)

For development, `local_functions` is the default and simplest path. Use `make run-agents` only when validating the HTTP transport.

### Key Files
| File | Role |
|---|---|
| `backend/main.py` | FastAPI app, all API endpoints, session lifecycle |
| `backend/orchestrator.py` | Pipeline sequencing (`SELL_STEPS`, `BUY_STEPS`), event publishing, retry logic |
| `backend/session.py` | In-memory session queue map; create/push/close lifecycle |
| `backend/schemas.py` | All Pydantic models — `AgentTaskRequest`, `AgentTaskResponse`, per-step input/output contracts, `AGENT_INPUT_CONTRACTS` |
| `backend/config.py` | `AGENTS` tuple (name, slug, port), env var defaults, `get_agent_execution_mode()` |
| `backend/agents/base.py` | `BaseAgent` ABC with `handle_task()` / `build_output()` pattern; `build_agent_app()` factory |
| `backend/agents/registry.py` | Maps agent slugs → agent instances; used by orchestrator |
| `backend/agent_client.py` | `run_agent_task()` — dispatches to local function or HTTP based on execution mode |

### Pipeline Flow
Both pipelines are strictly sequential. The orchestrator in `orchestrator.py` iterates `SELL_STEPS` or `BUY_STEPS`, calling each agent via `run_agent_task()`, accumulating `context` across steps, and emitting SSE events (`pipeline.started`, `agent.started`, `agent.completed`, `agent.failed`, `agent.retrying`, `pipeline.completed`, `pipeline.failed`) to `session_manager`.

BUY search agents (`depop_search_agent`, `ebay_search_agent`, `mercari_search_agent`, `offerup_search_agent`) are retryable — controlled by `BUY_AGENT_MAX_RETRIES` env var. `offerup_search_agent` is best-effort and returns an empty list gracefully on failure.

### Adding or Modifying an Agent
1. Create/edit `backend/agents/<slug>_agent.py` — subclass `BaseAgent`, implement `build_output(request: AgentTaskRequest) -> dict`.
2. The output dict must validate against the agent's `output_model` (a Pydantic model defined in `schemas.py`).
3. Input contracts are defined in `schemas.py` `AGENT_INPUT_CONTRACTS` — do not rename steps.
4. Register the agent instance in `backend/agents/registry.py`.

### Browser Use Agents
The agents that own Browser Use logic (you are implementing these):
- `ebay_sold_comps_agent` — eBay sold listings scraping (SELL)
- `depop_listing_agent` — Depop form population up to submit (SELL)
- `depop_search_agent`, `ebay_search_agent`, `mercari_search_agent`, `offerup_search_agent` — active listing search (BUY)
- `negotiation_agent` — send one offer message per seller (BUY)

Browser Use setup (local OSS, not Cloud):
```bash
pip install browser-use langchain-google-genai patchright
uvx browser-use install   # installs Chromium
python -m patchright install chromium
```

Required env:
```
GOOGLE_API_KEY=...
ANONYMIZED_TELEMETRY=false
```

Use headed Chromium + patchright (stealth), separate browser context per invocation, realistic delays (500ms–2000ms), 30-second hard timeout per agent. Never keep multiple browser contexts open simultaneously.

### SSE Contract
Frontend connects to `GET /stream/{session_id}`. Events use dot-delimited names — do not change these without coordinating with the mobile frontend:
- `pipeline.started`, `pipeline.completed`, `pipeline.failed`
- `agent.started`, `agent.completed`, `agent.failed`, `agent.retrying`

### Environment Variables
See `backend/.env.example` (if present) or `backend/config.py` for the full list. Key vars:
- `AGENT_EXECUTION_MODE` — `local_functions` (default) or `local_http`
- `APP_BASE_URL` — overridden on Render
- `INTERNAL_API_TOKEN` — gates `/internal/event/{session_id}` and `/internal/result/{session_id}`
- `AGENT_TIMEOUT_SECONDS` — default 20s
- `BUY_AGENT_MAX_RETRIES` — default 1

### Deployment
Hosted on Render (paid tier required for headed Chromium memory). `start.sh` backgrounds agent processes and keeps FastAPI in the foreground. `render.yaml` defines the service.

### Testing
Tests live in `tests/`. Use `pytest-asyncio` and FastAPI `TestClient`. Test names should be behavior-focused. Run `make check` before any PR.
