# Orchestrator Implementation Plan (Handoff)

**Audience:** A coordinating agent or human lead slicing work to executors.  
**Repo:** DiamondHacks backend — FastAPI, in-memory sessions, SSE, ten agents, optional Fetch uAgents.  
**Baseline:** `make check` must stay green after each merge; default verification is `make install` then `make check`.

---

## 1. Ground truth (do not contradict)

| Fact | Detail |
|------|--------|
| **Product API** | FastAPI in `backend/main.py` — **not** ASI:One as the runtime orchestrator for the mobile app. |
| **Pipelines** | `POST /sell/start`, `POST /buy/start`; progress via `GET /stream/{session_id}` (underscore SSE event names). |
| **Sell review** | Pauses at `listing_review_required`; user drives `POST /sell/listing-decision` (`confirm_submit` \| `revise` \| `abort`). Max **2** revisions; **15**-minute review window per pause (refreshed after each successful revise). |
| **Expiry** | Lazy checks on `/result`, `/stream`, `/sell/listing-decision` **plus** background sweep: `SELL_REVIEW_CLEANUP_INTERVAL` (default 60s). |
| **Agent execution** | `AGENT_EXECUTION_MODE=local_functions` (default) or `http` + `make run-agents`. |
| **Fetch** | Parallel layer: `make venv-fetch` + `make run-fetch-agents` (ports 9201–9210). `FETCH_ENABLED=true` routes orchestrator through Fetch adapter when testing that path. |
| **Contracts** | Pydantic models in `backend/schemas.py`; agent registry in `backend/agents/registry.py`. |

**Canonical references:** `AGENTS.md`, `CLAUDE.md`, `API_CONTRACT.md`, `FETCH_INTEGRATION.md`, `BrowserUse-Live-Validation.md`, `BACKEND-CODEBASE-PROBLEMS.md`, `IMPLEMENTATION-PLAN.md`.

---

## 2. Already implemented (automated; live validation still optional)

- Sell listing review loop, revision limit, deadline refresh, expiry (request + background).
- Fetch runtime bridge, parallel BUY search in Fetch chat path, no-results short-circuit.
- `GET /fetch-agents` manifest; health flags for Fetch / Agentverse key presence.
- Test coverage: sell review orchestration, listing-decision endpoint, result contract, background cleanup, fetch compatibility, contracts.

**Do not re-scope these unless a regression appears.**

---

## 3. Priority workstreams (recommended order)

Execute in phases; each phase should end with `make check` and a short changelog note in the PR or commit message.

### Phase A — Browser Use demo hardening (P0)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| A1 | Deterministic stop at sell listing **ready-to-submit** (not prompt-luck). | `browser_use_marketplaces.py`, `browser_use_support.py`, `BROWSER-USE-GAPS.md` | Live or harness: listing reaches `ready_for_confirmation` reliably; tests or harness scenario still pass with `BROWSER_USE_FORCE_FALLBACK=true`. |
| A2 | Replace placeholder listing screenshot with real capture (or schema-backed artifact). | `schemas.py` (Depop listing output), `browser_use_marketplaces.py` | Contract tests + at least one agent test assert non-placeholder behavior when mock provides bytes. |

**Dependency:** A1 before relying on A2 in demos.

### Phase B — Vision + schema truth (P0 / unblocks PRD + frontend)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| B1 | Real Gemini (or agreed) vision path for images — retire heuristic-only identification where product requires it. | `vision_agent.py`, config/env | `VisionAnalysisOutput` validates; pipeline uses real fields. |
| B2 | Align `VisionAnalysisOutput` with orchestrator/frontend (e.g. `confidence`, fields PRD promises). | `schemas.py`, `orchestrator.py` | No extra keys dropped by strict validation; low-confidence pause path testable. |
| B3 | Normalize `POST /sell/correct` payload → valid vision output (if not done). | `orchestrator.py`, `schemas.py`, tests | `tests/test_sell_correct_endpoint.py` (or equivalent) covers shape. |

See `IMPLEMENTATION-PLAN.md` Phase 2 for detailed subtasks.

### Phase C — Product depth (P1)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| C1 | Reduce synthetic fallback on default happy path (search, comps, pricing) where PRD demands real data. | `search_support.py`, `ebay_sold_comps_agent.py`, `pricing_agent.py` | Document behavior when keys missing; tests updated. |
| C2 | Unify pricing SSE/result fields with `PricingOutput` (`median_sold_price` vs `median_price`, etc.). | `orchestrator.py`, `schemas.py` | Contract + pipeline tests. |
| C3 | Negotiation: move beyond single template / small listing set (product-dependent). | `negotiation_agent.py` | Tests + safe demo behavior. |
| C4 | Docs: execution order (httpx → browser_use → fallback) consistent in `backend/README.md` and agent docstrings. | README, search agents | No “Browser Use first” drift. |

### Phase D — Reliability + SELL fallback (P2)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| D1 | SELL fallback listing path honors review loop (no silent bypass of human checkpoint). | `depop_listing_agent.py`, `test_pipelines.py` | Test asserts paused review when required. |
| D2 | Abort / cleanup semantics explicit in session result and events. | `orchestrator.py` | Tests for failure vs completed abort. |
| D3 | Deterministic temp file cleanup for remote image URLs in listing agent. | `depop_listing_agent.py` | Unit test or integration hook. |

### Phase E — Fetch + Agentverse (ops + glue)

| ID | Task | Notes |
|----|------|------|
| E1 | Mailbox registration and one end-to-end ASI:One smoke per agent (start with `depop_search_agent` per `FETCH_INTEGRATION.md`). | Mostly ops; code only if bridge gaps found. |
| E2 | Surface `execution_mode` / fallback reason in Fetch chat responses (optional P1 polish). | `fetch_runtime.py`, response formatting. |

### Phase F — Documentation (P3, can parallelize)

| ID | Task | File | Status |
|----|------|------|--------|
| F1 | PRD §5: **FastAPI + in-process orchestrator** is primary for the app; ASI:One/Fetch as parallel discovery — not “ASI:One is the orchestrator” for mobile. | `PRD.md` | Done |
| F2 | PRD BUY search: match **code** (sequential in main pipeline vs parallel in Fetch path — state both accurately). | `PRD.md` | Done |
| F3 | Replace legacy **listing_ready** language with `listing_review_required` + `/sell/listing-decision`. | `PRD.md`, any stray docs | Done (PRD §7.3, §7.6) |
| F4 | Note **draft_created** as compatibility-only vs `listing_review_required`. | `PRD.md`, `API_CONTRACT.md` | PRD done; align `API_CONTRACT.md` if still drift |

### Phase G — Performance (optional; from `IMPLEMENTATION-PLAN.md` Phase 3)

- Parallelize four BUY search steps in **main** orchestrator only after contract change and frontend agreement on interleaved SSE ordering.

---

## 4. Workstream boundaries (avoid merge pain)

| Stream | Owns | Touch only if necessary |
|--------|------|-------------------------|
| Browser Use | `browser_use_*`, listing/search agents’ browser paths | Schemas — coordinate with contract stream |
| Vision / Gemini | `vision_agent.py`, vision schemas | Orchestrator pause/resume |
| Contracts / SSE | `schemas.py`, `orchestrator.py` event payloads | Frontend + `API_CONTRACT.md` |
| Fetch | `fetch_agents/`, `fetch_runtime.py`, `run_fetch_agents.py` | Core `/task` shape |
| Docs | `PRD.md`, `README.md`, `API_CONTRACT.md` | No behavior change without code PR |

---

## 5. Definition of done (demo / judging)

- [ ] `make check` green on main branch.
- [ ] SELL: vision → comps → pricing → Depop draft → **review** → submit/revise/abort path demonstrable (fallback or live).
- [ ] BUY: four searches → rank → negotiation path demonstrable.
- [ ] Browser Use sponsor story: at least one **live** flow documented in `BrowserUse-Live-Validation.md` with sign-off notes.
- [ ] Fetch: 10 agents registered; at least one **live** ASI:One or Agentverse proof captured (screenshot/log) per team process.
- [ ] `PRD.md` architecture section matches implementation (no ASI:One-as-primary-orchestrator confusion).

---

## 6. Out of scope for this plan (unless product changes)

- Frontend / Expo app implementation (consume `API_CONTRACT.md` + SSE).
- Production deploy hardening beyond existing `render.yaml` / README (track separately).
- Replacing in-memory sessions with durable storage.

---

## 7. Suggested first sprint for an executor pool

1. **A1** (deterministic listing checkpoint) + tests/harness update.  
2. **B2** + **B3** (vision schema + correction normalization) if Gemini lands in parallel.  
3. **F1–F4** (PRD doc fix) in a docs-only PR to unblock judges reading PRD.  
4. **E1** (one Fetch agent live) as ops parallel track.

---

*Generated for handoff. Update `BACKEND-CODEBASE-PROBLEMS.md` when P0/P1 items close.*
