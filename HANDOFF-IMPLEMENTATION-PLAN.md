# Handoff Implementation Plan

**Continuation of work from two prior agents.** This plan covers the remaining docs-only tasks and the runtime background-cleanup task that were scoped but not completed.

**Constraint:** Tasks 1–4 are docs-only. Task 5 is runtime code. Neither track edits `backend/orchestrator.py` (docs track) or docs (runtime track) — they are fully independent and can execute in parallel.

**Repo baseline at handoff (HEAD = `0c64c91`):**

- Sell listing review lifecycle is complete: pause at `ready_for_confirmation`, `confirm_submit`, `revise` (with `revision_count` and limit of 2), `abort`, and request-time expiry after 15-minute `deadline_at`.
- Revision deadline refresh landed: `_refresh_sell_listing_review_pause` resets `paused_at`/`deadline_at` after each successful revision so the user gets a fresh 15-minute window.
- Expiry is checked when a client hits `GET /result/{session_id}`, `GET /stream/{session_id}`, the SSE keepalive loop, or `POST /sell/listing-decision`, **and** via a **background sweep** (`SELL_REVIEW_CLEANUP_INTERVAL`, default 60s) implemented after this plan was written.
- Fetch runtime bridge (`backend/fetch_runtime.py`) passes chat text into the local agent registry. BUY search agents are called with `previous_outputs={}` (parallel in the Fetch path). SELL agents chain sequentially: vision → comps → pricing → listing. No-results flow produces synthetic ranking/negotiation outputs.
- Test suites added: `test_sell_listing_review_orchestration.py`, `test_sell_listing_decision_endpoint.py`, `test_browser_use_fetch_compatibility.py`. Contract tests aligned for Fetch manifest.
- Docs partially updated but contain inconsistencies flagged below.

---

## Track A — Docs Only (Tasks 1–4)

### Scope

Edit **only** these files:
- `BrowserUse-Live-Validation.md`
- `FETCH_INTEGRATION.md`
- `backend/README.md`
- `BACKEND-CODEBASE-PROBLEMS.md`

Do **not** edit any file under `backend/` except `backend/README.md`.

---

### Task 1: SELL live validation checklist in `BrowserUse-Live-Validation.md`

**Current state:** The SELL section (lines 52–67) covers the general review loop but lacks an exact step-by-step operator script with specific HTTP calls, expected SSE event sequences, and session field assertions.

**What to write:**

Add a subsection **"SELL Live Validation — Step-by-Step"** after the current SELL section. Structure it as a numbered operator checklist:

#### 1a. Prepare listing

- `POST /sell/start` with `{ "input": { "image_urls": [...], "notes": "..." } }`
- Wait for SSE: `pipeline_started` → `agent_started` (vision) → `agent_completed` (vision) → … → `agent_started` (depop_listing) → `agent_completed` (depop_listing) → `listing_review_required`
- Legacy `draft_created` may also appear — note it as compatibility-only.
- Assert `GET /result/{session_id}` returns:
  - `status: "paused"`
  - `sell_listing_review.state: "ready_for_confirmation"`
  - `sell_listing_review.deadline_at` is ~15 minutes from `sell_listing_review.paused_at`
  - `result.outputs.depop_listing.ready_for_confirmation: true`
  - `result.outputs.depop_listing.listing_status: "ready_for_confirmation"`

#### 1b. Revise once

- `POST /sell/listing-decision` with `{ "session_id": "...", "decision": "revise", "revision_instructions": "Lower the price by $5" }`
- Expected SSE sequence:
  1. `listing_decision_received` (`data.decision: "revise"`)
  2. `pipeline_resumed` (`data.reason: "listing_revision_requested"`)
  3. `listing_revision_requested` (`data.revision_instructions`, `data.revision_count: 1`)
  4. `listing_revision_applied` (`data.revision_count: 1`, updated `data.output`)
  5. `listing_review_required` (re-emitted with fresh `review_state`)
- Assert `GET /result/{session_id}`:
  - `status: "paused"` again
  - `sell_listing_review.state: "ready_for_confirmation"`
  - `sell_listing_review.revision_count: 1`
  - **New** `deadline_at` (refreshed — not the original timestamp)
- Note: max revisions = 2. A third revise attempt will trigger `listing_revision_limit_reached` → `pipeline_failed`.

#### 1c. Confirm submit

- `POST /sell/listing-decision` with `{ "session_id": "...", "decision": "confirm_submit" }`
- Expected SSE sequence:
  1. `listing_decision_received` (`data.decision: "confirm_submit"`)
  2. `pipeline_resumed`
  3. `listing_submission_approved`
  4. `listing_submit_requested`
  5. On success: `listing_submitted` → `pipeline_complete`
  6. On failure: `listing_submission_failed` → `pipeline_failed`
- Assert `GET /result/{session_id}`:
  - Success: `status: "completed"`, `sell_listing_review: null`
  - Failure: `status: "failed"`, `error` set

#### 1d. Abort path

- `POST /sell/listing-decision` with `{ "session_id": "...", "decision": "abort" }`
- Expected SSE sequence:
  1. `listing_decision_received`
  2. `listing_submission_aborted`
  3. `listing_abort_requested`
  4. `listing_aborted`
  5. `pipeline_complete`
- Assert: `status: "completed"`, `sell_listing_review: null`, `depop_listing.listing_status: "aborted"`

#### 1e. Expiry path

- Let a paused session sit past `deadline_at` (15 minutes).
- **Today's behavior:** expiry fires only when client polls:
  - `GET /result/{session_id}` checks `expire_sell_listing_review_if_needed`
  - `GET /stream/{session_id}` checks on connect and in the SSE keepalive loop (~15s ticks)
  - `POST /sell/listing-decision` checks before processing
- Expected events on trigger: `listing_review_cleanup_completed` (or `listing_review_cleanup_failed`), `listing_review_expired`, `pipeline_failed`
- Assert: `status: "failed"`, `error: "sell_listing_review_timeout"`, `sell_listing_review: null`, `depop_listing.listing_status: "expired"`
- **Known gap:** If no client ever polls after deadline, the session remains paused indefinitely in memory. A background cleanup task is planned (see Task 5) but is not yet implemented.

#### 1f. Error edge cases to document

- `POST /sell/listing-decision` when `status != "paused"` → 409
- `POST /sell/listing-decision` with `decision: "revise"` but empty `revision_instructions` → 422
- `POST /sell/listing-decision` when `revision_count >= 2` and `decision: "revise"` → 409 after `listing_revision_limit_reached` + `pipeline_failed`

**Source of truth for event sequences:** `backend/orchestrator.py` lines 683–940 (`handle_sell_listing_decision`), tests in `tests/test_sell_listing_review_orchestration.py`, and `tests/test_sell_listing_decision_endpoint.py`.

**Acceptance:** The checklist is copy-pasteable by an operator with `curl`/`httpie` against a running `make run` instance. Every assertion maps to an actual field in `SessionState` or `SellListingReviewState`.

---

### Task 2: Fetch setup docs in `FETCH_INTEGRATION.md` and `backend/README.md`

**Current inconsistency identified:**

| Topic | `FETCH_INTEGRATION.md` says | `Makefile` actually does | `backend/README.md` says |
|-------|---------------------------|-------------------------|-------------------------|
| `.venv-fetch` creation | `pip install -r requirements.txt` | `pip install uagents uagents-core` (only 2 packages) | `make venv-fetch` (correct) |
| Python version | 3.12 or 3.13 | `FETCH_PYTHON ?= python3.12` | 3.12 or 3.13 |
| `FETCH_ENABLED` default | Not explicit | Not in Makefile; `config.py` has getter | `false` |

**What to fix:**

#### 2a. `.venv-fetch` setup section (both files)

Write the exact sequence:

```
make venv-fetch           # creates .venv-fetch with python3.12, installs uagents + uagents-core only
```

**Remove** the `pip install -r requirements.txt` instruction from `FETCH_INTEGRATION.md` § "Important Environment Note" — the Fetch venv intentionally does **not** install the full backend requirements. The Fetch agents import from the backend via `PYTHONPATH=$PWD` set by the Makefile target, which means the Fetch processes need the backend packages accessible on the system or via `PYTHONPATH` pointing at the `.venv` site-packages. **Clarify** this: the Fetch processes rely on `PYTHONPATH=$PWD` to reach `backend/` source, but they run under `.venv-fetch`'s Python where `uagents` is installed. If a Fetch agent transitively imports a backend dependency (e.g. `pydantic`, `httpx`), that dependency must also be in `.venv-fetch` or reachable. **Document** whether this currently works or whether the operator needs `pip install -r requirements.txt` in `.venv-fetch` as well — test by running `make run-fetch-agents` in a clean `.venv-fetch` and noting any `ImportError`.

#### 2b. Ports/process model (both files)

Write a clear table:

| Process | Command | Venv | Ports | Purpose |
|---------|---------|------|-------|---------|
| FastAPI backend | `make run` | `.venv` | 8000 | Product API, SSE, orchestrator |
| Per-agent FastAPI apps | `make run-agents` | `.venv` | 9101–9110 | Optional; validates per-agent `/task` surface |
| Fetch uAgents | `make run-fetch-agents` | `.venv-fetch` | 9201–9210 | Agentverse/ASI:One exposure |

All three can run concurrently without port collisions.

#### 2c. `make run` + `make run-fetch-agents` coexistence

Document: two terminal windows, two shells. Backend shell: standard env with `FETCH_ENABLED=false` (default — Fetch routing is opt-in). Fetch shell: export `AGENTVERSE_API_KEY` + all 10 seed vars, then `make run-fetch-agents`.

If you want the **backend orchestrator** to route through Fetch instead of local registry: set `FETCH_ENABLED=true` in the **backend** shell. This is only needed for integration testing; normal demos use both processes independently.

#### 2d. Live validation for `FETCH_ENABLED=true`

Numbered checklist:

1. `make run` — confirm `GET /health` shows `fetch_enabled: false` by default.
2. In Fetch shell: `make run-fetch-agents` — confirm ports 9201–9210 occupied.
3. Smoke one search agent: `python scripts/fetch_demo.py 9205 "Vintage Nike tee under $45"`.
4. Restart backend with `FETCH_ENABLED=true`.
5. `GET /health` now shows `fetch_enabled: true`.
6. `POST /buy/start` — confirm the pipeline completes; SSE events appear.
7. For mailbox mode: `FETCH_USE_LOCAL_ENDPOINT=false` (default). Confirm Agentverse registration in Fetch agent stdout.
8. For local inspector mode: `FETCH_USE_LOCAL_ENDPOINT=true`. Document that this is debug-only, not mailbox-backed.

**Acceptance:** An operator can follow the numbered steps from a clean clone, both with and without `FETCH_ENABLED=true`, and know exactly what output to expect at each step.

---

### Task 3: Refresh `BACKEND-CODEBASE-PROBLEMS.md`

**Current state:** 4 P0s, 4 P1s, 4 P2s, 3 P3s. Several items were addressed in the last 5 commits but not marked.

**Changes to make:**

#### 3a. Mark completed items

These are **done** (code + tests landed):

- ~~P1: "Add background cleanup for abandoned paused SELL review sessions"~~ — **Partially done.** Request-time expiry works. The backlog item should be updated to reflect: "request-time expiry is implemented; background timer-driven cleanup is not." **Do not mark fully complete.**

Actually on closer review, **nothing in the last 5 commits fully closes any P0/P1 item**. The work added sell-review lifecycle hardening and test coverage, but the four P0 items (Fetch BUY bridge, vision heuristic, vision schema alignment, deterministic browser checkpoint, placeholder screenshot) remain open. The revision-limit and expiry logic is new capability, not a fix to an existing backlog item.

#### 3b. Add "Implemented but not live-validated" section

Create a new section between P1 and P2:

**Implemented, Not Live-Validated:**

- [x] Sell listing review lifecycle: pause, confirm, revise (with revision limit = 2), abort, request-time expiry (15 min deadline). **Code:** `backend/orchestrator.py` lines 85–215, 683–940. **Tests:** `test_sell_listing_review_orchestration.py`, `test_sell_listing_decision_endpoint.py`. **Not validated:** against a real Depop browser session with live Browser Use submit/revise/abort actions.
- [x] Revision deadline refresh: `_refresh_sell_listing_review_pause` resets window after each successful revision. **Tests:** `test_sell_listing_review_orchestration.py`. **Not validated:** against a live revision where Browser Use modifies form fields.
- [x] Fetch runtime bridge: SELL chain (vision → comps → pricing → listing) and BUY chain (parallel search → ranking → negotiation) with no-results short-circuit. **Tests:** `test_fetch_runtime.py`, `test_browser_use_fetch_compatibility.py`. **Not validated:** actual Agentverse mailbox discovery or ASI:One prompt-response cycle.
- [x] Fetch agent manifest: `GET /fetch-agents` returns all 10 specs. **Tests:** `test_contracts_and_execution.py`. **Not validated:** live agent registration on Agentverse.

#### 3c. Update P1 item for background cleanup

Rewrite the item:

> **Add background cleanup for abandoned paused SELL review sessions.**
> Current state: request-time expiry is implemented — `expire_sell_listing_review_if_needed` runs from `/result`, `/stream`, SSE loop, and `/sell/listing-decision`. Sessions that are never polled after `deadline_at` remain paused indefinitely. A timer-driven cleanup task is needed to sweep these.
> References: `backend/orchestrator.py` L201–215, `backend/main.py` L248.

#### 3d. Keep remaining items prioritized

P0s stay P0. Reorder within P0 by actionability:

1. Deterministic Browser Use submit checkpoint (blocks live SELL demo)
2. Real screenshot capture (blocks listing preview UX)
3. Fix Fetch BUY bridge `previous_outputs` contract (blocks Fetch BUY demo)
4. Vision heuristic → real image pipeline (blocks Gemini story)
5. Vision output schema alignment (blocks confidence pause)

#### 3e. Add verification notes update

Update the "Verification Notes" section at the bottom to list the new test files from the last 5 commits:

- `test_sell_listing_review_orchestration.py` (7 tests)
- `test_sell_listing_decision_endpoint.py` (5+ tests)
- `test_browser_use_fetch_compatibility.py` (3+ tests)
- Expanded `test_contracts_and_execution.py` (fetch agent manifest)
- Expanded `test_pipelines.py` (sell listing review pause test)

**Acceptance:** Each backlog item clearly states whether it is a **code gap** or an **ops/validation gap**. No item is marked done unless both code and tests landed.

---

### Task 4: Commit

Stage only:
- `BrowserUse-Live-Validation.md`
- `FETCH_INTEGRATION.md`
- `backend/README.md`
- `BACKEND-CODEBASE-PROBLEMS.md`

Commit message: `Update validation checklists, Fetch setup docs, and backlog status`

Verify: `make check` still passes (docs-only changes should not affect tests, but confirm).

---

## Track B — Runtime: Background Session Expiry (Task 5)

### Scope

Edit **only**:
- `backend/main.py` (startup/shutdown lifecycle)
- `backend/session.py` (if a new query method is needed)
- `tests/test_sell_listing_review_orchestration.py` (or new test file)

Do **not** edit `backend/orchestrator.py` — reuse existing `expire_sell_listing_review_if_needed`.
Do **not** edit any doc file.

---

### Task 5: Timer-driven cleanup for abandoned paused sell-review sessions

#### 5a. Design

**Approach:** Add an `asyncio` background task that starts on FastAPI app startup (via `lifespan` or `@app.on_event("startup")`) and runs a periodic sweep.

**Sweep logic:**

```
every CLEANUP_INTERVAL_SECONDS (default: 60):
    for each session_id in session_manager.list_paused_sell_sessions():
        session = await session_manager.get_session(session_id)
        if session is None:
            continue
        if session.status != "paused" or session.sell_listing_review is None:
            continue
        await expire_sell_listing_review_if_needed(session_id)
```

This reuses the existing `expire_sell_listing_review_if_needed` function, which already:
- Checks `sell_listing_review_is_expired(review)` against `deadline_at`
- Calls `fail_sell_listing_review` with `sell_listing_review_timeout` error
- Emits `listing_review_expired` + cleanup events + `pipeline_failed`
- Calls `session_manager.clear_sell_listing_review`
- Marks session `status: "failed"`, `error: "sell_listing_review_timeout"`

No new orchestrator logic needed.

#### 5b. Session manager changes

`backend/session.py` currently stores sessions in a dict. Add one method:

```python
async def list_paused_sell_review_session_ids(self) -> list[str]:
    """Return session IDs that are paused with an active sell_listing_review."""
    return [
        sid for sid, session in self._sessions.items()
        if session.status == "paused"
        and session.pipeline == "sell"
        and session.sell_listing_review is not None
    ]
```

This is a read-only scan of the in-memory dict. No locking issues since the dict mutation and this scan both run on the same event loop.

#### 5c. Background task in `backend/main.py`

Add to the app lifecycle:

```python
CLEANUP_INTERVAL_SECONDS = int(os.environ.get("SELL_REVIEW_CLEANUP_INTERVAL", "60"))

async def _sell_review_cleanup_loop():
    from backend.orchestrator import expire_sell_listing_review_if_needed
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            session_ids = await session_manager.list_paused_sell_review_session_ids()
            for sid in session_ids:
                await expire_sell_listing_review_if_needed(sid)
        except Exception:
            pass  # log but never crash the cleanup loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_sell_review_cleanup_loop())
    yield
    task.cancel()
```

If `main.py` already uses `@app.on_event("startup")` instead of `lifespan`, adapt to the existing pattern. The key constraint: the task must be cancellable on shutdown and must not raise.

#### 5d. Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SELL_REVIEW_CLEANUP_INTERVAL` | `60` | Seconds between sweep runs |

The existing `SELL_LISTING_REVIEW_TIMEOUT_MINUTES` (15) controls when a session is considered expired. The cleanup interval only controls how frequently the sweep checks — worst-case a session stays alive up to `CLEANUP_INTERVAL_SECONDS` past its deadline.

#### 5e. Tests

Add to `tests/test_sell_listing_review_orchestration.py` (or a new `tests/test_sell_review_background_expiry.py`):

**Test 1: Background sweep expires an abandoned session**

```
1. Create session, set status="paused", sell_listing_review with deadline_at in the past.
2. Do NOT call any endpoint (simulating zero client activity).
3. Directly call the sweep function (or the expiry function it delegates to).
4. Assert session.status == "failed", error == "sell_listing_review_timeout",
   sell_listing_review is None.
5. Assert events include "listing_review_expired" and "pipeline_failed".
```

**Test 2: Background sweep skips non-expired sessions**

```
1. Create session, set status="paused", sell_listing_review with deadline_at 10 minutes in the future.
2. Run sweep.
3. Assert session.status == "paused" (unchanged).
```

**Test 3: Background sweep skips non-sell sessions**

```
1. Create a buy session with status="running".
2. Run sweep.
3. Assert no state change.
```

**Test 4: Regression — existing sell review orchestration still works**

```
Run existing test suite: make test
All tests in test_sell_listing_review_orchestration.py,
test_sell_listing_decision_endpoint.py, and test_pipelines.py pass.
```

**Test 5: Cleanup loop does not crash on empty session store**

```
1. Ensure no sessions exist.
2. Run one sweep iteration.
3. Assert no errors.
```

#### 5f. What NOT to do

- Do not add expiry to `run_pipeline` — that would couple pipeline execution with cleanup.
- Do not add a `deadline_at` watcher per session (over-engineered for in-memory store).
- Do not change the existing lazy-expiry behavior in `/result`, `/stream`, `/sell/listing-decision` — the background task is additive, not a replacement.
- Do not edit `backend/orchestrator.py` — all expiry logic already exists there.

#### 5g. Commit

Stage: `backend/main.py`, `backend/session.py`, new/modified test files.

Commit message: `Add background cleanup for abandoned paused sell-review sessions`

Verify: `make check` passes.

---

## Execution Order

Both tracks are independent. If executing sequentially:

1. **Track A (docs)** first — faster, no test risk, clarifies the state of the world.
2. **Track B (runtime)** second — small code surface, reuses existing functions, focused tests.

If executing in parallel: assign to two agents. No file overlap.

---

## Post-Completion Checklist

After both tracks land:

- [ ] `make check` passes
- [ ] `BACKEND-CODEBASE-PROBLEMS.md` P1 "background cleanup" item can be marked done
- [ ] `BrowserUse-Live-Validation.md` SELL checklist can be walked through against `make run` with fallback mode
- [ ] `FETCH_INTEGRATION.md` setup instructions match `Makefile` exactly
- [ ] No runtime files were edited by the docs track
- [ ] No doc files were edited by the runtime track

---

## Out of Scope (flagged for future)

These are **not** part of this plan:

- Deterministic Browser Use submit checkpoint (P0 code gap — needs `browser_use_marketplaces.py` changes)
- Real screenshot capture (P0 code gap — needs `browser_use_support.py` + schema changes)
- Fetch BUY bridge `previous_outputs` fix (P0 code gap — needs `schemas.py` contract relaxation)
- Vision heuristic → Gemini (separate workstream)
- Live Agentverse mailbox/discoverability validation (ops task, not code)
- Full end-to-end live validation against real marketplace accounts (ops task)
