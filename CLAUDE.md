# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Python/FastAPI)

```bash
make install          # create .venv and install requirements.txt
make test             # run pytest -q (default acceptance check)
make test-verbose     # run pytest -ra
make compile          # syntax-check backend/ and tests/
make check            # test + compile
make ci               # matches CI flow (same as check)
make run              # start backend via uvicorn (port 8000)
make run-agents       # start agent HTTP microservices (ports 9101–9110)
make verify-browser   # run browser_use_runtime_audit (quick smoke test)
make run-fetch-agent AGENT=<name>  # start a single uAgent (requires env loaded: set -a && source .env && set +a)
```

Single test file: `. .venv/bin/activate && python -m pytest tests/test_pipelines.py -q`

Browser Use validation:
```bash
./.venv/bin/python scripts/browser_use_validation.py --group buy_search
./.venv/bin/python -m backend.browser_use_validation --mode fallback --scenario depop_listing
./.venv/bin/python -m backend.browser_use_runtime_audit
```

### Frontend (React Native / Expo)

```bash
cd frontend
npm start             # Expo dev server
npm run web           # web only
npm run android       # Android
npm run ios           # iOS
npx expo install <pkg>  # add dependency (use this, not npm install, for Expo compat)
```

No test runner or linter is configured for the frontend.

## Architecture

Monorepo with a Python/FastAPI backend (`backend/`) and a React Native/Expo frontend (`frontend/`). They communicate over HTTP + SSE. Data is persisted in Supabase (Postgres + Auth). Frontend-specific guidance lives in `frontend/CLAUDE.md`.

### Backend: Two Pipelines

**Sell pipeline** (`POST /sell/start`): user uploads item photo → 4 sequential agents:
1. `vision_agent` — Gemini Vision identifies item
2. `ebay_sold_comps_agent` — Browser Use scrapes eBay sold listings
3. `pricing_agent` — computes median price and profit margin
4. `depop_listing_agent` — populates Depop form via Browser Use, pauses before submit

**Buy pipeline** (`POST /buy/start`): user provides search query/budget → 6 agents:
1–4. `depop_search_agent`, `ebay_search_agent`, `mercari_search_agent`, `offerup_search_agent` — search with 3-tier resolution: `httpx` → `browser_use` → `fallback`
5. `ranking_agent` — scores and ranks results
6. `negotiation_agent` — prepares/sends offers

### API Routes

Two route families exist:
- **Legacy (no auth):** `POST /sell/start`, `POST /buy/start`, `GET /stream/{session_id}`, `GET /result/{session_id}` — used for direct testing.
- **Authenticated:** `POST /items/{item_id}/sell/run`, `POST /items/{item_id}/buy/run`, `GET /runs/{run_id}/stream`, `GET /runs/{run_id}` — require Supabase JWT, verify item ownership. These are what the frontend uses.

Other endpoints: `POST /sell/correct` (vision correction), `POST /sell/listing-decision` (confirm/revise/abort), `POST /internal/event/{session_id}` (agent progress events, requires `INTERNAL_API_TOKEN`), `GET /health`, `GET /agents`, `GET /pipelines`.

### Request/Response Flow

`POST /{pipeline}/start` → creates `SessionState` → fires `asyncio.create_task(run_pipeline(...))` → returns `{session_id, stream_url, result_url}` immediately. Client connects to SSE stream for real-time events.

### Agent Execution Modes

`AGENT_EXECUTION_MODE` env var: `local_functions` (default, dev — all in-process via `backend/agents/registry.py`) or `http` (prod — separate microservices on ports 9101–9110, see `backend/config.py`).

### Session Management (`backend/session.py`)

`SessionManager` holds all active sessions in memory (`dict[str, SessionState]`) with async pub/sub event delivery via `asyncio.Queue`. When a session event is appended, it broadcasts to all SSE subscribers. Persistence to Supabase is handled by `RunPersistenceManager` (injected hook pattern, see `backend/run_persistence.py`).

A background cleanup loop (`_sell_review_cleanup_loop` in `main.py` lifespan) periodically expires stale sell listing reviews.

### Vision Correction Flow

If `vision_agent` returns confidence < 0.70, the sell pipeline raises `LowConfidencePause`. The frontend shows the low-confidence result and allows the user to submit corrections via `POST /sell/correct`. `resume_sell_pipeline()` in the orchestrator picks up from the vision step with corrected data.

### Sell Listing Review Flow

After `depop_listing_agent` creates a draft, the pipeline pauses (`SellListingReviewPause`). Session enters `listing_review` state, waits up to 15 min for:
- `POST /sell/listing-decision` with `decision: "confirm_submit"` — submit
- `POST /sell/listing-decision` with `decision: "revise"` — corrections (max 2 revisions)
- `POST /sell/listing-decision` with `decision: "abort"` — cancel

### Schema Contracts (`backend/schemas.py`)

Every agent has strict Pydantic input/output models. Adding a new agent requires:
1. Output model extending `AgentOutputBase` (search/comp agents include `execution_mode: Literal["httpx", "browser_use", "fallback"]`)
2. Input model specifying required `previous_outputs` fields
3. Entries in `AGENT_OUTPUT_MODELS` and `AGENT_INPUT_CONTRACTS`
4. Registration in `backend/agents/registry.py`

New agents extend `BaseAgent` from `backend/agents/base.py` and implement `build_output(request) -> dict`.

### Auth

Backend uses Supabase JWT auth (`backend/auth.py`). Frontend attaches the Supabase session JWT as a Bearer token on all API calls (`frontend/lib/api.ts`). Item ownership is verified server-side before pipeline operations.

### Frontend Architecture

See `frontend/CLAUDE.md` for full frontend details. Summary: Expo SDK 54 with expo-router v6 (file-based routing), Supabase auth, NativeWind styling (though most code uses `StyleSheet.create`). Backend URL configured via `EXPO_PUBLIC_API_URL` (default `http://localhost:8000`) in `frontend/constants/config.ts`.

### Supabase Schema

Defined in `supabase_schema.sql`. Key tables: `profiles`, `user_settings`, `platform_connections`, `items`, `conversations`, `messages`, `agent_runs`, `completed_trades`, `market_data`. All tables have RLS policies scoping data to `auth.uid()`. Triggers auto-create `profiles` and `user_settings` on signup.

Backend repository layer: `backend/repositories/` (items, agent_runs, conversations, messages, completed_trades, market_data).

### Background Scheduler (`backend/scheduler.py`)

`scheduler_loop()` starts automatically in `main.py` lifespan. Polls Supabase every `SCHEDULER_INTERVAL` seconds (default 300) for active items without a recent run and fires pipelines. Tracks in-flight item IDs to prevent duplicate concurrent runs.

### AI Analyze Endpoint (`backend/ai_generate.py`)

`POST /ai/analyze-item` — uses Gemini Vision (via `NANO_BANANA_API_KEY`) to analyze a product photo and optionally generate professional listing photos. Returns `{name, description, condition}` plus generated image URLs if requested.

### Fetch.ai Agent Layer

`backend/fetch_agents/` — uAgents-based wrappers exposing buy search over Fetch.ai network. Requires Python 3.12/3.13 (uagents 0.24.0 incompatible with 3.14). Enabled via `FETCH_ENABLED=true`. Separate venv: `make venv-fetch` + `make run-fetch-agents`.

### SSE Event Contract

The backend uses underscore-delimited SSE event names:
- `pipeline_started`, `pipeline_complete`, `pipeline_failed`
- `agent_started`, `agent_completed`, `agent_error`, `agent_retrying`
- `search_method`, `vision_low_confidence`, `draft_created`
- `offer_prepared`, `offer_sent`, `offer_failed`
- `browser_use_fallback`

### CI

GitHub Actions (`.github/workflows/backend-ci.yml`): Python 3.14, `pip install -r requirements.txt`, `pytest -q`, `compileall backend tests`. Runs on push to main and PRs.

### Deployment

Render (`render.yaml`): single web service, builds with `pip install -r requirements.txt && python -m patchright install chromium`, starts via `./start.sh` (uvicorn). Chromium needed for live Browser Use flows; falls back to deterministic mock data without it.

### Key Runtime Constants

- `SELL_LISTING_REVIEW_TIMEOUT_MINUTES = 15` — max wait for user listing decision
- `SELL_LISTING_MAX_REVISIONS = 2` — max revision rounds before forced decision
- `AGENT_TIMEOUT_SECONDS = 30` (default) — per-agent execution timeout
- `BUY_AGENT_MAX_RETRIES = 1` (default) — retry count for search agents
- Vision confidence threshold: `< 0.70` triggers low-confidence pause

## Key Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_EXECUTION_MODE` | `local_functions` | `local_functions` or `http` |
| `APP_BASE_URL` | `http://localhost:8000` | Stream/result URL construction |
| `INTERNAL_API_TOKEN` | `dev-internal-token` | Auth for internal event endpoint |
| `GOOGLE_API_KEY` | *(none)* | Gemini Vision + Browser Use |
| `EBAY_APP_ID`, `EBAY_CERT_ID` | *(none)* | eBay Browse API credentials |
| `BROWSER_USE_FORCE_FALLBACK` | `false` | Skip Chromium, return mock data |
| `BROWSER_USE_GEMINI_MODEL` | `gemini-2.0-flash` | Model for Browser Use flows |
| `FETCH_ENABLED` | `false` | Enable Fetch.ai uAgents layer |
| `SUPABASE_URL` | *(none)* | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | *(none)* | Supabase service role key |
| `SUPABASE_JWT_SECRET` | *(none)* | JWT verification secret |
| `ALLOWED_ORIGINS` | `*` | CORS origins (comma-separated) |
| `NANO_BANANA_API_KEY` | *(none)* | Gemini API key for `ai_generate.py` (analyze + photo gen) |
| `SCHEDULER_INTERVAL` | `300` | Seconds between scheduler polling cycles |

## Codex Orchestrator (optional)

If `codex` / `codex-reply` MCP tools are available, delegate implementation to Codex using structured task specs. See the task spec template, escalation rules, and session logging format below. **Fallback:** If Codex MCP tools are unavailable, implement directly.

Task spec format for Codex:
```
Task: <scoped to one function or file>
Acceptance criteria: <command that exits 0 — default: `make test`>
Constraints: <what must not change>
Context: <non-obvious info>
Output format: RESULT block with changed_files, test_command, exit_code, blocker
```

Escalation: stop after 3 Codex calls per goal or if the same blocker appears twice. Log to `.codex-session.log`.
