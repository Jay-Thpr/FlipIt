# Project Context

DiamondHacks 2026 | April 5–6 | UCSD

---

## What This Is

An autonomous resale agent app called **FILLER**. A user photographs a thrift store item (SELL) or pastes a search query (BUY). AI agents handle the entire workflow — item identification, market research, pricing, listing creation, cross-platform search, ranking, and offer negotiation — with real-time progress delivered over SSE to a mobile frontend.

**One-liner:** Photo in. Listing out. Profit shown.

---

## Tracks

| Track | Type |
|---|---|
| Enchanted Commerce | Main |
| Best Use of Browser Use | Sponsor — 2× iPhone 17 Pro + AirPods Max + SF hacker house trip |
| Best Use of Fetch.ai | Sponsor — $300/$200 cash |
| Best Use of Gemini API | MLH side prize |
| Best AI/ML Hack | Side |
| Best UI/UX Hack | Side |
| Best Mobile Hack | Side |

---

## Team Ownership

| Area | Owner | Status |
|---|---|---|
| FastAPI backend + SSE + orchestration | Jay | Done |
| Browser Use agents (7 agents) | Codex | Implemented behind `/task`; live validation still pending |
| Fetch.ai uAgents + Chat Protocol + Agentverse | Teammate | In progress |
| Mobile frontend (Expo React Native + NativeWind) | Teammate | In progress |
| Backend hardening + deployment (items 4–9) | Jay | Planned — see JAY-PLAN.md |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Expo React Native + NativeWind |
| Real-time updates | SSE (Server-Sent Events) |
| Backend | Python FastAPI |
| Agent orchestration | In-process async (local_functions mode) |
| Agent discoverability | Fetch.ai Agentverse + Chat Protocol |
| Item identification | Gemini Vision (via langchain-google-genai) |
| Browser automation | Browser Use (open-source) + patchright stealth |
| Deployment | Render (paid tier required for headed Chromium) |

---

## Architecture

### Execution Modes

`AGENT_EXECUTION_MODE` controls how the orchestrator calls agents:
- `local_functions` — all 10 agents run in-process, no subprocesses (default, use this for demo)
- `http` — orchestrator POSTs to each agent's FastAPI app on its fixed port (9101–9110); start agents with `make run-agents`

### SELL Pipeline (sequential)

1. `vision_agent` → `vision_analysis`
2. `ebay_sold_comps_agent` → `ebay_sold_comps`
3. `pricing_agent` → `pricing`
4. `depop_listing_agent` → `depop_listing`

### BUY Pipeline (sequential)

1. `depop_search_agent` → `depop_search`
2. `ebay_search_agent` → `ebay_search`
3. `mercari_search_agent` → `mercari_search`
4. `offerup_search_agent` → `offerup_search`
5. `ranking_agent` → `ranking`
6. `negotiation_agent` → `negotiation`

BUY search agents (depop, ebay, mercari, offerup) are retryable — controlled by `BUY_AGENT_MAX_RETRIES`. `offerup_search_agent` is best-effort and returns empty gracefully on failure.

### Agent Ports (local_http mode)

| Agent | Slug | Port |
|---|---|---|
| Vision Agent | vision_agent | 9101 |
| eBay Sold Comps Agent | ebay_sold_comps_agent | 9102 |
| Pricing Agent | pricing_agent | 9103 |
| Depop Listing Agent | depop_listing_agent | 9104 |
| Depop Search Agent | depop_search_agent | 9105 |
| eBay Search Agent | ebay_search_agent | 9106 |
| Mercari Search Agent | mercari_search_agent | 9107 |
| OfferUp Search Agent | offerup_search_agent | 9108 |
| Ranking Agent | ranking_agent | 9109 |
| Negotiation Agent | negotiation_agent | 9110 |

### SSE Event Contract (do not change these names without coordinating with the frontend)

Events emitted by `backend/orchestrator.py` using underscore-delimited names:

| Event | When |
|---|---|
| `pipeline_started` | Pipeline begins |
| `agent_started` | Each agent step begins |
| `agent_retrying` | Retryable agent fails and retries |
| `agent_error` | Agent step fails (after all retries) |
| `agent_completed` | Agent step succeeds |
| `pipeline_complete` | All steps completed |
| `pipeline_failed` | Pipeline aborted on failure |

Each event payload includes `session_id`, `pipeline`, `step`, `data`, and `timestamp`.

---

## Key Files

| File | Role |
|---|---|
| `backend/main.py` | FastAPI app, all API endpoints, SSE streaming |
| `backend/orchestrator.py` | Pipeline sequencing, event publishing, retry logic |
| `backend/session.py` | In-memory session + event queue lifecycle |
| `backend/schemas.py` | All Pydantic models and per-step input/output contracts |
| `backend/config.py` | Agent config, env var defaults |
| `backend/agents/base.py` | BaseAgent ABC + build_agent_app factory |
| `backend/agents/registry.py` | Agent slug → instance map |
| `backend/agent_client.py` | Dispatches to local function or HTTP based on execution mode |
| `backend/agents/browser_use_support.py` | Shared Browser Use helpers, lazy imports, structured task runner |

---

## Current Agent Status

### Real Browser Use

- `ebay_sold_comps_agent` — attempts live Browser Use for eBay sold comps, falls back to deterministic estimation
- `depop_listing_agent`
- `depop_search_agent`
- `ebay_search_agent`
- `mercari_search_agent`
- `offerup_search_agent`
- `negotiation_agent`
  - Each agent attempts Browser Use first and falls back to structured non-live behavior when runtime dependencies, profiles, or live site interactions fail.

### No Browser Use (AI logic, not automation)

- `vision_agent` — item identification (heuristic scaffold today; Gemini integration in progress)
- `pricing_agent` — median price + profit calculation
- `ranking_agent` — multi-signal listing scorer

---

## Known Bugs / Issues

1. **Browser Use profile dependency** — live Depop listing and live negotiation sending require warmed persisted profiles under `BROWSER_USE_PROFILE_ROOT`. Without them, those agents intentionally fall back.
2. **Marketplace DOM drift** — live Browser Use paths still need real-site rehearsal on eBay, Depop, Mercari, and OfferUp before demo use.
3. **CORS** — `backend/main.py` mounts `CORSMiddleware` with `allow_origins=["*"]` for development. Tighten origins for production if needed.
4. **SSE keepalive** — `GET /stream/{session_id}` emits periodic `: ping\n\n` (see `KEEPALIVE_INTERVAL` in `main.py`) so proxies do not drop idle connections.
5. **Fetch.ai runtime not implemented** — `/chat` remains a placeholder and Agentverse/ASI:One wiring is still separate work.

---

## Fetch.ai Status

Not implemented. Only a `{"status": "not_implemented"}` placeholder exists at the `/chat` endpoint in `backend/agents/base.py`. Teammate is implementing:
- Real `uagents` runtime in each agent module
- Chat Protocol handlers
- Agentverse mailbox registration for all 10 agents
- ASI:One verification

Recommended implementation order (per `FetchAI-Status.md`):
1. Add shared Fetch runtime support to `base.py`
2. Add Agentverse credentials + seeds to `config.py` and `.env.example`
3. Wire one agent (vision_agent) end to end as reference implementation
4. Generalize across remaining 9 agents
5. Deploy + verify Agentverse registration
6. Run ASI:One verification, capture submission URL

**Do not break the `/task` contract while adding Fetch runtime support.**

---

## Fetch.ai Deliverables Required

- ASI:One Chat session URL: `https://asi1.ai/shared-chat/<id>`
- Agentverse profile URL for each agent
- Public GitHub repo + demo video on Devpost

---

## Browser Use Setup (for local development with real agents)

```bash
pip install browser-use langchain-google-genai patchright
python -m patchright install chromium
```

Required env vars:
```
GOOGLE_API_KEY=...
ANONYMIZED_TELEMETRY=false
```

Browser Use runs headed Chromium + patchright stealth. Keep one browser context per agent invocation. Realistic delays 500ms–2000ms. Hard timeout: `AGENT_TIMEOUT_SECONDS` (default 30s, use 60s on Render).

---

## Deployment

- Platform: Render (paid Standard plan required for headed Chromium memory)
- `render.yaml` defines the service
- `start.sh` boots uvicorn; with `AGENT_EXECUTION_MODE=local_functions` no agent subprocesses needed
- Chromium must be installed at build time: `python -m patchright install chromium` in `buildCommand`
- Secrets (`GOOGLE_API_KEY`, `INTERNAL_API_TOKEN`) must be set in Render dashboard (not in render.yaml)

---

## Test Coverage

122 tests passing as of last verification. Run with:

```bash
make check
```

Test files:
- `test_agents.py` — agent contract tests
- `test_pipelines.py` — SELL and BUY end-to-end
- `test_orchestrator_resilience.py` — timeout, retry, failure handling
- `test_contracts_and_execution.py` — schema validation
- `test_http_execution_and_launcher.py` — local_http mode
- `test_health_and_sessions.py` — API endpoints
- `test_browser_use_runtime.py` — Browser Use availability detection

---

## Demo Script Priority

**Protect in this order if time gets tight:**
1. SELL pipeline end to end (photo → Depop listing)
2. BUY pipeline search (query → ranked listings)
3. BUY negotiation (offers prepared/sent)
4. Fetch.ai Chat Protocol polish

**SELL demo arc:** Open app → tap "+" in Selling section → camera → bottom sheet shows agents running → item card appears on dashboard → tap into Item Detail with pricing and listing details.

**BUY demo arc:** Tap "+" in Buying section → paste query → bottom sheet shows search agents → item card appears → Item Detail → Chat Log showing negotiation messages.
