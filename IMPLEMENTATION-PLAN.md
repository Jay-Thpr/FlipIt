# DiamondHacks Backend — In-Depth Implementation Plan

**Document purpose:** A single, execution-oriented plan for finishing the resale-agent backend and integrating it cleanly with parallel workstreams (Fetch.ai, Gemini vision, mobile frontend). It is meant to be sliced into tickets and owned by individuals without duplicating effort.

**Repo baseline:** FastAPI app in `backend/`, in-memory sessions, SSE progress, ten agents behind a stable `/task` contract, `AGENT_EXECUTION_MODE` of `local_functions` (default) or `http` for per-process microservices.

**Related documents:** `PROJECT-CONTEXT.md`, `PRD.md`, `API_CONTRACT.md`, `FetchAI-Status.md`, `FETCH_INTEGRATION.md`, `AGENTVERSE_IMPLEMENTATION_PLAN.md`, `AGENTVERSE_SETUP.md`, `AGENTS.md`, `CLAUDE.md`, `BROWSER_USE_GUIDE.md`, `BrowserUse-Live-Validation.md`.

---

## Table of Contents

1. [Goals and success criteria](#1-goals-and-success-criteria)
2. [Architecture invariants](#2-architecture-invariants-non-negotiables)
3. [Workstream ownership matrix](#3-workstream-ownership-matrix)
4. [Phase 0 — Alignment and contract baselines](#phase-0--alignment-and-contract-baselines)
5. [Phase 1 — Frontend integration readiness](#phase-1--frontend-integration-readiness)
6. [Phase 2 — Vision contract, low-confidence pause, and resume](#phase-2--vision-contract-low-confidence-pause-and-resume)
7. [Phase 3 — Buy pipeline performance and search quality](#phase-3--buy-pipeline-performance-and-search-quality)
8. [Phase 4 — Sell pipeline depth (post-vision)](#phase-4--sell-pipeline-depth-post-vision)
9. [Phase 5 — Browser Use reliability and demo hardening](#phase-5--browser-use-reliability-and-demo-hardening)
10. [Phase 6 — Fetch.ai integration support](#phase-6--fetchai-integration-support-glue-only)
11. [Phase 7 — Deployment, observability, and operations](#phase-7--deployment-observability-and-operations)
12. [Testing strategy](#12-testing-strategy)
13. [Risk register](#13-risk-register)
14. [Appendix A — Canonical file map](#appendix-a--canonical-file-map)
15. [Appendix B — Environment variables](#appendix-b--environment-variables)
16. [Appendix C — SSE event catalog](#appendix-c--sse-event-catalog)

---

## 1. Goals and success criteria

### 1.1 Product goals

- **Sell path:** User provides image URL(s) and notes → system identifies item, pulls comps, prices, prepares Depop listing (with optional human confirmation when identification is uncertain).
- **Buy path:** User provides query and budget → system searches four marketplaces, ranks, prepares/sends negotiation actions (with clear disclosure when automation is simulated or fallback).
- **Realtime:** Client receives structured SSE events for every meaningful state transition without polling the orchestrator internals.
- **Sponsor tracks:** Browser Use and Fetch.ai remain demonstrable without breaking the primary FastAPI contract.

### 1.2 Technical success criteria (definition of done for “backend ready for demo”)

| Criterion | Verification |
|-----------|----------------|
| `make check` passes locally and in CI | GitHub Actions workflow green |
| `API_CONTRACT.md` matches observable HTTP + SSE behavior | Manual diff + contract tests |
| Sell pipeline completes in `local_functions` with fallback where Browser Use unavailable | `tests/test_pipelines.py` + smoke |
| Buy pipeline completes with deterministic or httpx/browser_use paths | Same |
| Low-confidence vision path is **schema-valid**, test-covered, and documented | New tests; frontend can implement UX against fixed payloads |
| Optional: four buy searches complete faster than sequential baseline | Timing log or benchmark test (non-flaky bounds) |
| Deployed staging URL documented with required secrets | Runbook section filled in |

---

## 2. Architecture invariants (non-negotiables)

These protect parallel development.

1. **`/task` request/response shape** — The orchestrator always builds `AgentTaskRequest` with `input.original_input` and `input.previous_outputs`. Agent outputs must validate against `AGENT_OUTPUT_MODELS` in `backend/schemas.py`. Fetch or Gemini work must not remove or rename these fields without a versioned migration plan.

2. **SSE event names** — Use underscore-delimited names as emitted today (`pipeline_started`, `agent_completed`, etc.). Renaming requires explicit frontend agreement and a deprecation window.

3. **Agent slugs and ports** — Defined in `backend/config.py`. Agentverse metadata should reference the same slugs.

4. **Execution modes** — `local_functions` vs `http` must remain behaviorally equivalent for the same inputs (within limits of subprocess isolation and timing). Integration tests should run the default mode; at least one CI job or documented manual step should exercise `http` mode periodically.

5. **Browser Use failures are not pipeline failures** — Agents should return structured `execution_mode: "fallback"` (or equivalent) when live automation is unavailable, unless the product decision is to hard-fail (document if changed).

---

## 3. Workstream ownership matrix

| Workstream | Primary owner | Backend buddy responsibilities |
|------------|---------------|--------------------------------|
| Fetch.ai uAgents, `/chat`, Agentverse | Dedicated teammate | Config stubs, health flags, CI secrets layout, “do not break `/task`” reviews |
| Gemini / vision identification | Dedicated teammate | Pydantic fields, pause threshold, tests that mock vision output, merge order after schema lands |
| Mobile frontend (Expo) | Dedicated teammate | Accurate `API_CONTRACT.md`, example payloads, CORS if web tooling used, SSE samples |
| Orchestration, contracts, perf, tests, deploy | You (recommended) | This plan’s Phases 0–5, 7; selective Phase 6 |

---

## Phase 0 — Alignment and contract baselines

**Objective:** Eliminate drift between docs, tests, and runtime before building new features.

### 0.1 Audit documentation against code

**Tasks:**

1. Reconcile `PROJECT-CONTEXT.md` with `backend/main.py`:
   - CORS: `main.py` already mounts `CORSMiddleware` (`allow_origins=["*"]`). Update `PROJECT-CONTEXT.md` “Known Bugs” if it still claims CORS is missing.
   - SSE keepalive: `iter_session_events` yields `: ping\n\n` on timeout. Update any doc that claims no keepalive.

2. Reconcile execution mode naming: `backend/config.py` uses `AGENT_EXECUTION_MODE` values `local_functions` and `http`. If any doc says `local_http`, standardize on `http`.

3. Map every public route in `main.py` to a section in `API_CONTRACT.md`:
   - `GET /health`, `GET /agents`, `GET /pipelines`
   - `POST /sell/start`, `POST /buy/start`, `POST /sell/correct`
   - `GET /stream/{session_id}`, `GET /result/{session_id}`
   - `POST /internal/event/{session_id}`

**Acceptance criteria:** PR that only updates markdown (and optionally adds a CI check or script that fails if a route is removed without updating `API_CONTRACT.md` — optional stretch).

**Files:** `PROJECT-CONTEXT.md`, `API_CONTRACT.md`, `README.md`, `backend/README.md`.

---

### 0.2 Establish a “contract changelog” convention

**Tasks:**

1. Add a short subsection to `API_CONTRACT.md`: **Changelog** with date, author, and bullet list of breaking vs additive changes.

2. For any future schema change to `SessionState` or event payloads, require a one-line changelog entry.

**Acceptance criteria:** Changelog section exists; team agrees in standup.

---

## Phase 1 — Frontend integration readiness

**Objective:** Minimize frontend integration time and surprise.

### 1.1 Normalize `GET /result/{session_id}` documentation

**Current behavior:** Returns full `SessionState.model_dump()` including `status`, `request`, `result`, `error`, `events`, timestamps.

**Tasks:**

1. Update `API_CONTRACT.md` §1.4 to show the **actual** JSON shape (not a simplified `final_outputs` placeholder unless you add a dedicated field).

2. Optionally add a stable `GET /result/{session_id}/summary` that returns only `{session_id, status, pipeline, error, outputs}` — **only if** the frontend wants a smaller payload. If added, it must be tested and documented; otherwise prefer documenting the full shape.

**Acceptance criteria:** Frontend developer can implement result polling from the doc alone.

**Files:** `API_CONTRACT.md`, optionally `backend/main.py`, `tests/test_health_and_sessions.py` or new test file.

---

### 1.2 SSE payload examples (golden files)

**Tasks:**

1. Add `tests/fixtures/sse/` (or `docs/examples/sse/`) with **redacted** example JSON bodies for:
   - `pipeline_started` (sell and buy)
   - `agent_completed` for each step name
   - `agent_error` and `pipeline_failed`
   - `vision_low_confidence` (after Phase 2 fixes)
   - `pipeline_resumed` (sell correction path)

2. Optionally add a pytest that parses these fixtures with the same `parse_sse_events` helper style as `tests/test_pipelines.py`.

**Acceptance criteria:** Frontend can copy-paste types from examples.

---

### 1.3 Error semantics for the UI

**Tasks:**

1. Document in `API_CONTRACT.md` how to interpret:
   - `session.status === "failed"` vs in-progress
   - `agent_error.data.category` (`timeout`, `validation`, `agent_execution`) from `backend/orchestrator.py` `classify_error`
   - Partial `result.outputs` on failure (orchestrator already attaches `partial_result` on `pipeline_failed`)

2. If the product needs **stable machine-readable codes**, extend `agent_error` / `pipeline_failed` `data` with optional `code: str` fields (additive only). Coordinate with frontend before shipping.

**Acceptance criteria:** Documented; optional code fields behind explicit decision.

**Files:** `API_CONTRACT.md`, possibly `backend/orchestrator.py`.

---

## Phase 2 — Vision contract, low-confidence pause, and resume

**Objective:** Make the sell-side “uncertain identification → user corrects → pipeline continues” flow **end-to-end correct** and testable, independent of whether Gemini or a stub produces vision output.

### 2.1 Problem statement (as of repo survey)

- `backend/orchestrator.py` after `vision_analysis` checks `validated_output.get("confidence", …)` and may emit `vision_low_confidence` and pause.
- `VisionAnalysisOutput` in `backend/schemas.py` does **not** define `confidence` (or related fields). `validate_agent_output` uses strict output models; extra keys from agents may not survive validation depending on Pydantic configuration.
- `backend/agents/vision_agent.py` currently performs **heuristic** extraction from notes and image URL strings; it does not emit `confidence`.

**Result:** The pause path is unlikely to behave as designed until schema + agent output align.

### 2.2 Schema design

**Tasks:**

1. Extend `VisionAnalysisOutput` with:
   - `confidence: float` — required, range `0.0`–`1.0`, or optional with default `1.0` for backward compatibility (prefer **required** once Gemini owns it, with stub setting explicit values).
   - Optional: `identification_notes: str | None`, `raw_model_response_ref: str | None` (for debug only; avoid PII).

2. Update `AGENT_OUTPUT_MODELS` entry (already points at `VisionAnalysisOutput`).

3. Ensure `CorrectionRequest.corrected_item` is documented to match **either** a superset of vision fields or the exact shape the frontend will POST. Align with `resume_sell_pipeline`, which assigns `outputs["vision_analysis"] = corrected_item`. The downstream agents expect `VisionAnalysisOutput` fields (`detected_item`, `brand`, `category`, `condition`). **Require** corrected payloads to include those keys or define a normalization function in `resume_sell_pipeline` that maps `item_name` → `detected_item` etc.

### 2.3 Normalization layer for user corrections

**Tasks:**

1. Implement `normalize_vision_correction(corrected_item: dict) -> dict` (e.g. in `backend/schemas.py` or `backend/orchestrator.py`) that:
   - Accepts frontend-friendly keys (`item_name`, `search_query`, …)
   - Produces a dict that validates as `VisionAnalysisOutput` (or merge into existing output)

2. Call this from `resume_sell_pipeline` before persisting `outputs["vision_analysis"]`.

**Acceptance criteria:** `tests/test_sell_correct_endpoint.py` asserts downstream-valid shape, not only dict equality with arbitrary keys.

**Files:** `backend/orchestrator.py`, `backend/schemas.py`, `tests/test_sell_correct_endpoint.py`.

---

### 2.4 Orchestrator pause semantics

**Tasks:**

1. Replace string comparison `str(exc) == "low_confidence_pause"` with a **typed exception** (e.g. `class LowConfidencePause(Exception): pass`) raised from a dedicated branch after emitting `vision_low_confidence`.

2. Ensure session `status` remains **`running`** (not `failed`) when pausing, and `result` retains partial outputs for resume. Verify `session_manager.update_status` behavior matches product expectation (frontend may poll `/result` while waiting for user).

3. Document whether **`pipeline_failed`** should **never** fire for low-confidence pause (current design: no).

4. Align `vision_low_confidence` payload with `API_CONTRACT.md`: include everything the UI needs (`suggestion`, `message`, scores, optional bounding fields).

**Acceptance criteria:** Unit/integration test: force low confidence → stream shows `vision_low_confidence` → session still `running` → `POST /sell/correct` → `pipeline_complete`.

**Files:** `backend/orchestrator.py`, `tests/test_pipelines.py` (new case), `API_CONTRACT.md`.

---

### 2.5 Stub and Gemini handoff

**Tasks:**

1. Until Gemini merges: update **heuristic** `vision_agent` to emit `confidence` (e.g. lower when brand is `Unknown` or token count is low).

2. After Gemini merges: ensure model output maps to `VisionAnalysisOutput` including calibrated `confidence`.

**Acceptance criteria:** Single source of truth for output shape; Gemini PR only changes `vision_agent.py` (and possibly prompts), not orchestrator logic.

---

## Phase 3 — Buy pipeline performance and search quality

**Objective:** Reduce wall-clock time for buy flows and improve usefulness of results when Browser Use is unavailable.

### 3.1 Parallelize the four search agents

**Current:** `run_pipeline` loops sequentially; each search agent only *needs* prior search outputs for schema chaining, but **each agent’s input model** encodes cumulative `previous_outputs` (eBay needs Depop, Mercari needs Depop+eBay, etc.). **Ranking** needs all four.

**Design options:**

| Option | Pros | Cons |
|--------|------|------|
| A. `asyncio.gather` on four tasks with **synthetic empty** previous_outputs where the contract allows | Fast | Violates current `AGENT_INPUT_CONTRACTS` unless relaxed |
| B. Change input models so each search agent only needs `BuyPipelineInput` | Clean, parallel | Breaking change to `validate_agent_task_request`; must update all agents |
| C. Parallelize only the **httpx** attempt layer inside a new composite step | Keeps orchestrator | Larger refactor |

**Recommended path for hackathon velocity:** **Option B (contract simplification)** if team accepts a one-time breaking internal contract:

1. Change `DepopSearchAgentInput`, `EbaySearchAgentInput`, etc. to use `previous_outputs: EmptyPreviousOutputs` (or a single shared model).

2. Update each search agent’s `build_output` to ignore cross-agent prior outputs.

3. In `run_pipeline`, replace the four-step loop with one orchestration block:
   - `gather` four coroutines wrapping `execute_step` for each slug with **synthetic** per-agent task requests **or** a new meta-agent `marketplace_search_fanout` that returns a dict of four result lists (bigger change).

4. Map results into `outputs` keys `depop_search`, `ebay_search`, … for `ranking_agent` unchanged.

**Tasks (detailed):**

1. Update `backend/schemas.py` input models for the four search agents.

2. Update `backend/agents/*_search_agent.py` to stop reading `previous_outputs` from other platforms.

3. Refactor `BUY_STEPS` or introduce `run_buy_search_phase` in `orchestrator.py` that runs four steps concurrently, then continues sequentially to ranking and negotiation.

4. SSE ordering: today events are strictly sequential. Parallel execution will interleave `agent_started` / `agent_completed`. **Document** this for the frontend (UI should key off `step` + `agent_name`, not global order).

5. Retries: `get_max_attempts` applies per agent; concurrent retries remain independent.

**Acceptance criteria:**

- Tests updated; `make test` passes.
- Optional: assert four searches start within same event loop “tick” (weak signal) or log timestamps.

**Files:** `backend/orchestrator.py`, `backend/schemas.py`, four search agent modules, `tests/test_contracts_and_execution.py`, `tests/test_pipelines.py`.

---

### 3.2 Tier-1 (httpx) coverage expansion

**Tasks:**

1. Audit `backend/agents/httpx_clients.py` for each marketplace. For any stub returning `None` too often, implement or improve internal API scraping **within ToS**.

2. Wire `EBAY_APP_ID` / `EBAY_CERT_ID` where Browse API is partially implemented; document failure modes when unset.

3. Ensure every search agent emits `search_method` (already pattern in `depop_search_agent`) for observability.

**Acceptance criteria:** With `BROWSER_USE_FORCE_FALLBACK=true`, buy pipeline still returns non-empty ranked results for a canned test query (may use deterministic mock data — document).

---

## Phase 4 — Sell pipeline depth (post-vision)

**Objective:** Maximize perceived quality of comps, pricing, and listing copy without blocking the Gemini teammate.

### 4.1 eBay sold comps

**Tasks:**

1. Review `ebay_sold_comps_agent` for consistency between Browser Use, httpx, and fallback.

2. Ensure `EbaySoldCompsOutput` always includes defensible `sample_size` and price spread when in fallback.

3. Add unit tests for edge cases: empty query, vision output with `Unknown` brand.

**Files:** `backend/agents/ebay_sold_comps_agent.py`, `tests/`.

---

### 4.2 Pricing agent

**Tasks:**

1. Validate `TrendData` / `VelocityData` are populated whenever comp dates/prices allow (`pricing_agent.py`, `trend_analysis.py`).

2. Ensure `pricing_confidence` reflects data quality (sample size, spread) for frontend display.

**Files:** `backend/agents/pricing_agent.py`, `backend/agents/trend_analysis.py`, `tests/test_trend_analysis.py`, `tests/test_pricing_agent_real.py`.

---

### 4.3 Depop listing agent

**Tasks:**

1. Confirm `draft_created`-style events if the frontend expects listing preview milestones (see `browser_use_events` and `API_CONTRACT.md`).

2. Align `DepopListingOutput.listing_preview` with what the mobile UI can render offline.

**Files:** `backend/agents/depop_listing_agent.py`, `backend/agents/browser_use_events.py`, `API_CONTRACT.md`.

---

## Phase 5 — Browser Use reliability and demo hardening

**Objective:** Repeatable demos on target hardware and hosting.

### 5.1 Profile and environment validation

**Tasks:**

1. Run `backend/browser_use_runtime_audit.py` (and `scripts/browser_use_runtime_audit.py` if duplicated — consider consolidating to avoid drift).

2. Document in `BrowserUse-Live-Validation.md` the **minimum** profile state for Depop listing and negotiation.

3. Add a `make verify-browser` target that runs audit + optional `--mode fallback` validation (fast CI) vs `--require-live` (manual pre-demo).

**Files:** `Makefile`, `BrowserUse-Live-Validation.md`, `README.md`.

---

### 5.2 Render / paid tier constraints

**Tasks:**

1. Confirm `render.yaml` installs Chromium via patchright as in README.

2. Document headed vs headless flags and env vars for production.

3. Define `BROWSER_USE_FORCE_FALLBACK=true` for Render free tier smoke, `false` for paid demo.

**Files:** `render.yaml`, `README.md`.

---

### 5.3 DOM drift playbook

**Tasks:**

1. For each Browser Use agent, maintain a short “last verified” note in `BrowserUse-Status.md` or agent module docstring.

2. On failure, ensure `browser_use_error` and `BrowserUseMetadata` surface enough for judges without leaking secrets.

---

## Phase 6 — Fetch.ai integration support (glue only)

**Objective:** Support the Fetch teammate without owning uAgent internals.

### 6.1 Configuration and feature flags

**Tasks:**

1. Add placeholder env vars to `.env.example` (no real secrets): e.g. `FETCH_ENABLED`, `AGENTVERSE_API_KEY`, per-agent seed names if required.

2. In `backend/config.py`, expose typed getters that return `None` when unset.

3. Optional: extend `GET /health` with `fetch_configured: bool` (never expose secret values).

---

### 6.2 Review gate

**Tasks:**

1. On each Fetch-related PR, verify:
   - `POST /task` still accepts `AgentTaskRequest` unchanged.
   - Local tests pass with `FETCH_ENABLED=false`.

---

### 6.3 Documentation

**Tasks:**

1. Link `FetchAI-Status.md` from this plan; ensure ASI:One verification steps are copy-paste ready.

2. Execute **`AGENTVERSE_IMPLEMENTATION_PLAN.md`** for Agentverse alignment: canonical slug/port/env table, local `make run-fetch-agents` runbook, doc fixes to `AGENTVERSE_SETUP.md`, and submission URL collection.

---

## Phase 7 — Deployment, observability, and operations

### 7.1 Staging URL and secrets matrix

**Tasks:**

1. Table: variable name, required for which feature, who owns rotation, where stored (Render dashboard, 1Password, etc.).

2. Document `INTERNAL_API_TOKEN` usage for `POST /internal/event/{session_id}`.

---

### 7.2 Logging

**Tasks:**

1. Standardize structured logs for: `session_id`, `pipeline`, `step`, `agent_slug`, `execution_mode`.

2. Avoid logging full PII from `original_input`; truncate image URLs if logged.

**Files:** `backend/orchestrator.py`, `backend/main.py`, agent base classes.

---

### 7.3 Rate limiting and abuse (stretch)

**Tasks:**

1. If public demo URL is shared, consider basic rate limits on `/sell/start` and `/buy/start` (e.g. `slowapi`) or API key header — product decision.

---

## 12. Testing strategy

### 12.1 Layers

| Layer | Scope | Tools |
|-------|--------|--------|
| Contract | `AGENT_INPUT_CONTRACTS`, `AGENT_OUTPUT_MODELS` | `tests/test_contracts_and_execution.py` |
| Orchestrator | Retries, failures, ordering | `tests/test_orchestrator_resilience.py`, `tests/test_pipelines.py` |
| Agents | Individual `build_output` with mocks | `tests/test_agents.py`, `tests/test_*_real.py` |
| HTTP | Main app routes | `TestClient` |
| Browser Use | Live vs fallback | `browser_use_validation.py`, marked optional in CI |

### 12.2 New tests required by this plan

1. **Vision pause/resume E2E** (TestClient + stream parsing): low confidence → `vision_low_confidence` → correct → `pipeline_complete`.

2. **Correction normalization**: invalid `corrected_item` → `422` or normalized output (explicit product choice).

3. **Parallel buy search** (if Phase 3 ships): ordering-agnostic assertions on final `ranking` input.

4. **Regression:** `AGENT_EXECUTION_MODE=http` smoke script (optional nightly): start `run_agents` + one pipeline.

---

## 13. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Frontend depends on strict SSE ordering | Medium | High | Document interleaved events after parallel search; UI keys off `step` |
| Gemini latency exceeds `AGENT_TIMEOUT_SECONDS` | Medium | High | Raise timeout for vision only, or async vision job (out of scope — then increase global timeout for demo) |
| Marketplace blocks automation mid-demo | High | Medium | Fallback paths + judge-facing narrative |
| Schema drift between mobile and backend | Medium | High | `API_CONTRACT.md` changelog + contract tests |
| Fetch registration fails in prod | Medium | Medium | Recorded video + Agentverse screenshots as backup demo |

---

## Appendix A — Canonical file map

| Path | Responsibility |
|------|----------------|
| `backend/main.py` | Routes, SSE, session lifecycle |
| `backend/orchestrator.py` | Pipelines, retries, events, resume |
| `backend/session.py` | In-memory state |
| `backend/schemas.py` | Pydantic contracts |
| `backend/config.py` | Env and agent table |
| `backend/agent_client.py` | Local vs HTTP dispatch |
| `backend/agents/registry.py` | Local agent registry |
| `backend/agents/base.py` | `BaseAgent`, per-agent FastAPI app factory |
| `backend/run_agents.py` | Multi-uvicorn launcher |
| `tests/conftest.py` | Shared fixtures |
| `API_CONTRACT.md` | Frontend contract |

---

## Appendix B — Environment variables

| Variable | Purpose |
|----------|---------|
| `AGENT_EXECUTION_MODE` | `local_functions` or `http` |
| `APP_BASE_URL` | URLs returned to client |
| `INTERNAL_API_TOKEN` | Internal event auth |
| `AGENT_TIMEOUT_SECONDS` | Per-agent wall clock |
| `BUY_AGENT_MAX_RETRIES` | Buy search retries |
| `BROWSER_USE_FORCE_FALLBACK` | Skip live Browser Use |
| `BROWSER_USE_PROFILE_ROOT` | Profile directory |
| `GOOGLE_API_KEY` | Gemini / Browser Use stacks as applicable |
| `EBAY_APP_ID`, `EBAY_CERT_ID` | eBay Browse API |

*(Extend table when Fetch vars land.)*

---

## Appendix C — SSE event catalog

Events observed from orchestration and agents (non-exhaustive for agent-emitted internal events):

| Event | Source | Notes |
|-------|--------|------|
| `pipeline_started` | Orchestrator | |
| `agent_started` | Orchestrator | |
| `agent_retrying` | Orchestrator | Buy search agents |
| `agent_error` | Orchestrator | |
| `agent_completed` | Orchestrator | |
| `pipeline_complete` | Orchestrator | |
| `pipeline_failed` | Orchestrator | Includes `partial_result` |
| `vision_low_confidence` | Orchestrator | Sell pause path |
| `pipeline_resumed` | Orchestrator | After `/sell/correct` |
| `search_method` | Search agents | Via internal event helper |
| `browser_use_fallback` | Various | Per `CLAUDE.md` / agent code |

**Note:** Agents may emit additional events through `POST /internal/event/{session_id}`; maintain a single list in `API_CONTRACT.md` as new events appear.

---

## Suggested execution order (summary)

1. **Phase 0** — Doc/code alignment (fast, reduces confusion).
2. **Phase 2** — Vision schema + pause/resume + normalization (unblocks Gemini + frontend UX).
3. **Phase 1** — Golden SSE examples and result payload docs (parallel with Phase 2).
4. **Phase 3** — Parallel buy searches if time permits (coordinate SSE expectations).
5. **Phases 4–5** — Depth + demo reliability.
6. **Phases 6–7** — Fetch glue + deploy/runbook.

---

*End of implementation plan. Update this document when phases complete or priorities change.*
