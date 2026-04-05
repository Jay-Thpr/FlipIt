# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude+Codex Orchestrator

## Role
- **Claude** (you): planner and reviewer. Handle goal decomposition, task spec writing, result review, and user communication.
- **Codex**: executor. Handles all file edits, shell commands, and test runs via the `codex` and `codex-reply` MCP tools.

Never write code or edit files yourself. Always delegate implementation to Codex.

## MCP Tools Available
- `codex(prompt)` — starts a new Codex session. Returns a result and a `conversationId`.
- `codex-reply(conversationId, prompt)` — continues an existing session. Use this for follow-ups on the same task.

## Task Spec Template
Every prompt sent to Codex via `codex()` or `codex-reply()` must follow this format exactly:

```
Task: <one specific thing, scoped to one function or file>
Acceptance criteria: <command that exits 0 — default for this repo: `make test`>
Constraints: <what must not change — API surface, other files, etc.>
Context: <any non-obvious info Codex needs to complete this task>
Output format: End your response with this exact block (no prose after it):
  RESULT:
  changed_files: [file1.py, file2.py]
  test_command: <command you ran>
  exit_code: <0 or 1>
  blocker: <"none" or one-sentence description>
```

Do not send a task to Codex if you cannot fill in `acceptance_criteria` with a concrete, runnable command.

## Reviewing Codex Output
Parse the RESULT block from every Codex response:
- `exit_code: 0` and `blocker: none` → task succeeded. Proceed to next task or summarise to user.
- `exit_code: 1` → send `codex-reply()` with the test output and ask Codex to fix it.
- `blocker` is set → see escalation rules below.

## Escalation Rules
- If a single goal requires more than **3 Codex calls** (codex + codex-reply combined): stop, report to user.
- If the **same blocker appears twice in a row**: stop, report to user. Do not retry.
- When escalating, tell the user: the goal, number of calls made, and the last blocker.
- Track call count per goal in your scratchpad. Reset when a new goal starts.

## Session Logging
After every Codex call, append a log entry to `.codex-session.log` in the repo root using a file write:
```
[<ISO timestamp>] TASK goal="<goal>" conversationId="<id>"
[<ISO timestamp>] RESULT conversationId="<id>" exit_code=<n> changed_files=[<files>] blocker="<blocker>"
```
If escalating, also append:
```
[<ISO timestamp>] ESCALATED goal="<goal>" reason="<why>"
```

## Workflow Summary
1. User gives high-level goal
2. Inspect repo context (structure, test command, build system)
3. Break goal into scoped tasks
4. For each task: call `codex()` with a full task spec → review RESULT block → continue or escalate
5. When all tasks pass: summarise changed files and test results to user

**Fallback:** If Codex MCP tools are unavailable, implement directly using your own file tools.

---

## SSE Event Contract

The backend uses underscore-delimited SSE event names:

- `pipeline_started`, `pipeline_complete`, `pipeline_failed`
- `agent_started`, `agent_completed`, `agent_error`, `agent_retrying`
- `search_method` (emitted by search agents: `{agent: str, method: "httpx"|"browser_use"|"fallback"}`)
- `vision_low_confidence` (when vision inference < 0.70 confidence)
- `draft_created` (from listing agent)
- `offer_prepared` / `offer_sent` / `offer_failed` (from negotiation agent)
- `browser_use_fallback` (when Browser Use fails and fallback data is returned)

---

## Commands

```bash
make install       # create .venv and install requirements.txt
make test          # run pytest -q (default test command)
make test-verbose  # run pytest -ra
make compile       # syntax-check backend/ and tests/
make check         # test + compile
make ci            # matches local CI flow
make run           # start full stack via ./start.sh
make run-agents    # start all agent HTTP servers (python -m backend.run_agents)
```

Run a single test file: `. .venv/bin/activate && python -m pytest tests/test_pipelines.py -q`

Browser Use validation commands:
```bash
# Smoke-test search agents in fallback/live mode
./.venv/bin/python scripts/browser_use_validation.py --group buy_search
./.venv/bin/python -m backend.browser_use_validation --mode fallback --scenario depop_listing
./.venv/bin/python -m backend.browser_use_validation --require-live --group sell

# Audit Chromium, env vars, profile dirs before live runs
./.venv/bin/python -m backend.browser_use_runtime_audit
```

---

## Architecture

This is a Python/FastAPI backend for an autonomous resale agent system. There is no frontend code in this repo — the backend exposes HTTP + SSE APIs consumed by an external Next.js frontend.

### Two Pipelines

**Sell pipeline** (`POST /sell/start`): user uploads item photo → 4 sequential agents:
1. `vision_agent` — Gemini Vision identifies item
2. `ebay_sold_comps_agent` — Browser Use scrapes eBay sold listings
3. `pricing_agent` — computes median price and profit margin
4. `depop_listing_agent` — populates Depop form via Browser Use, pauses before submit

**Buy pipeline** (`POST /buy/start`): user provides search query/budget → 6 agents:
1–4. `depop_search_agent`, `ebay_search_agent`, `mercari_search_agent`, `offerup_search_agent` — parallel-ish search (sequential in code, retryable).
     **Note on Search Architecture:** We use a 3-tier resolution path for speed and stealth: `httpx` (internal APIs / eBay Browse API) → `browser_use` (Chromium scrape) → `fallback` (deterministic mock data).
5. `ranking_agent` — scores and ranks all results
6. `negotiation_agent` — prepares/sends offers

### Agent Execution Modes

`AGENT_EXECUTION_MODE` env var controls how agents run:
- `local_functions` (default, dev): all agents run in-process via `backend/agents/registry.py`
- `http` (prod): each agent is a separate FastAPI microservice on ports 9101–9110 (see `backend/config.py`), started with `make run-agents`

### Request/Response Flow

`POST /{pipeline}/start` → creates a `SessionState` → fires `asyncio.create_task(run_pipeline(...))` → returns `{session_id, stream_url, result_url}` immediately.

Client connects to `GET /stream/{session_id}` (SSE) to receive real-time events. See the SSE Event Contract section in this file for the full list of event names.

### Schema Contracts (`backend/schemas.py`)

Every agent has a strict Pydantic input model (e.g. `EbaySoldCompsAgentInput`) that validates `previous_outputs` from prior steps. Adding a new agent requires:
1. New output model extending `AgentOutputBase`. Search agents and comp agents have an `execution_mode: Literal["httpx", "browser_use", "fallback"]` field.
2. New input model specifying which `previous_outputs` fields are required.
3. Entries in `AGENT_OUTPUT_MODELS` and `AGENT_INPUT_CONTRACTS`
4. Registration in `backend/agents/registry.py`

*Note on PricingOutput:* `PricingAgent` synthesizes market comps to include `TrendData` and `VelocityData` objects indicating market direction and demand based on dates and prices.

### Sell Listing Review Flow

After `depop_listing_agent` creates a draft, the pipeline pauses with a `SellListingReviewPause` (not an error). The session enters `listing_review` state and waits up to 15 minutes for the user to call one of:
- `POST /sell/confirm` — submits the listing
- `POST /sell/revise` — sends corrections back through `depop_listing_agent` (max 2 revisions)
- `POST /sell/abort` — cancels the listing

### Fetch.ai Agent Layer

`backend/fetch_agents/` contains uAgents-based wrappers (`builder.py`, `launch.py`) that expose the buy search pipeline over the Fetch.ai agent network. Requires Python 3.12/3.13 — uagents 0.24.0 is incompatible with Python 3.14. Enabled via `FETCH_ENABLED=true`; the orchestrator calls `run_fetch_query()` from `backend/fetch_runtime.py` when active.

### Adding a New Agent

Extend `BaseAgent` from `backend/agents/base.py`, implement `build_output(request) -> dict`. The base class handles input/output Pydantic validation and error wrapping. `StubAgent` is a convenience class for agents that return static mock data.

### Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_EXECUTION_MODE` | `local_functions` | `local_functions` or `http` |
| `APP_BASE_URL` | `http://localhost:8000` | Used to construct stream/result URLs in responses |
| `AGENT_HOST` | `127.0.0.1` | Host for HTTP agent microservices |
| `INTERNAL_API_TOKEN` | `dev-internal-token` | Auth for `POST /internal/event/{session_id}` |
| `AGENT_TIMEOUT_SECONDS` | `30` | Per-agent execution timeout |
| `BUY_AGENT_MAX_RETRIES` | `1` | Extra retries for buy-side search agents |
| `BROWSER_USE_FORCE_FALLBACK`| `false` | If `true`, skips all Chromium scraping and returns fallback mock data |
| `BROWSER_USE_PROFILE_ROOT` | `profiles` | Dir for persistent browser profiles |
| `EBAY_APP_ID`, `EBAY_CERT_ID`| *(none)* | eBay developer credentials for Browse API (Topic 3) |
| `GOOGLE_API_KEY` | *(none)* | Required for live Gemini Vision and Browser Use flows |
| `FETCH_ENABLED` | `false` | Enable Fetch.ai uAgents layer for buy search |
| `RESALE_COPILOT_AGENT_ADDRESS` | `""` | Stable agent1q... address for resale_copilot_agent; used by frontend FAB to link to ASI:One chat |
| `ALLOWED_ORIGINS` | *(none)* | Comma-separated list of allowed CORS origins (e.g. `https://app.example.com,https://staging.example.com`). Defaults to `*` (dev only). In production, set to your actual frontend origin(s). |
