# Browser Use Execution Strict Plan

## Goal

Finish the remaining backend-side Browser Use work without touching frontend, Fetch.ai runtime, or the vision agent. This plan follows:

- [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md)
- [BROWSER_USE_GUIDE.md](/Users/jt/Desktop/diamondhacks/BROWSER_USE_GUIDE.md)
- [BrowserUse-Implementation-Plan.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Implementation-Plan.md)
- [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md)
- [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md)

## Constraints

- Keep Browser Use behind FastAPI `/task` handlers.
- Preserve the existing `/sell/start`, `/buy/start`, `/stream/{session_id}`, and `/result/{session_id}` contracts.
- Additive changes only: no schema or event breakage for current consumers.
- Every phase adds tests first or alongside code, passes its gate, then commits before moving on.

## Phase 1: Browser Use Progress Events

### Scope

- Add backend event helpers for Browser Use milestone events.
- Emit granular underscore-delimited events that remain safe for SSE consumers:
  - `listing_found`
  - `draft_created`
  - `offer_prepared`
  - `offer_sent`
  - `offer_failed`
- Emit these events from search, listing, and negotiation agents without changing final output payloads.

### Files

- `backend/agents/browser_use_events.py`
- `backend/agents/depop_search_agent.py`
- `backend/agents/ebay_search_agent.py`
- `backend/agents/mercari_search_agent.py`
- `backend/agents/offerup_search_agent.py`
- `backend/agents/depop_listing_agent.py`
- `backend/agents/negotiation_agent.py`
- `tests/test_browser_use_progress_events.py`
- `tests/test_pipelines.py`

### Test Gate

```bash
./.venv/bin/python -m pytest -q tests/test_browser_use_progress_events.py tests/test_pipelines.py
```

### Commit

- `Add Browser Use progress milestone events`

## Phase 2: Marketplace Failure Hardening

### Scope

- Normalize Browser Use fallback reasons for search, listing, and negotiation paths.
- Distinguish `runtime_unavailable`, `profile_missing`, `browser_error`, and `result_invalid`.
- Add additive metadata to outputs where useful:
  - search source metadata
  - listing draft source / failure reason
  - negotiation attempt source / failure reason
- Keep existing fields intact so current consumers do not break.

### Files

- `backend/agents/browser_use_support.py`
- `backend/agents/browser_use_marketplaces.py`
- `backend/agents/depop_listing_agent.py`
- `backend/agents/depop_search_agent.py`
- `backend/agents/ebay_search_agent.py`
- `backend/agents/mercari_search_agent.py`
- `backend/agents/offerup_search_agent.py`
- `backend/agents/negotiation_agent.py`
- `backend/schemas.py`
- `tests/test_buy_search_agents_real.py`
- `tests/test_depop_listing_agent_real.py`
- `tests/test_buy_decision_agents_real.py`

### Test Gate

```bash
./.venv/bin/python -m pytest -q tests/test_buy_search_agents_real.py tests/test_depop_listing_agent_real.py tests/test_buy_decision_agents_real.py
```

### Commit

- `Harden Browser Use marketplace failure handling`

## Phase 3: Backend Validation Harness

### Scope

- Add a backend-only validation harness to exercise Browser Use agents without frontend or Fetch.ai dependencies.
- Support deterministic dry-run mode and live mode with warmed profiles.
- Capture result payloads and session events for each flow.
- Cover:
  - eBay sold comps
  - buy search agents
  - Depop listing
  - negotiation

### Files

- `backend/browser_use_validation.py`
- `tests/test_browser_use_validation_harness.py`
- `README.md`
- `BrowserUse-Status.md`

### Test Gate

```bash
./.venv/bin/python -m pytest -q tests/test_browser_use_validation_harness.py
```

### Commit

- `Add Browser Use validation harness`

## Phase 4: Deployment and Runtime Verification

### Scope

- Add runtime verification checks for Browser Use prerequisites:
  - Chromium install visibility
  - `GOOGLE_API_KEY`
  - profile-root existence
  - per-platform warmed profile presence
  - Render-oriented env sanity
- Expose checks through a lightweight backend utility entrypoint.
- Document exact manual live-validation steps and expected results.

### Files

- `backend/browser_use_runtime_audit.py`
- `tests/test_browser_use_runtime_audit.py`
- `README.md`
- `BROWSER_USE_GUIDE.md`
- `BrowserUse-Status.md`

### Test Gate

```bash
./.venv/bin/python -m pytest -q tests/test_browser_use_runtime.py tests/test_browser_use_runtime_audit.py tests/test_project_scaffold.py
```

### Commit

- `Add Browser Use runtime audit and deployment verification`

## Phase 5: Final Verification

### Scope

- Run the full suite.
- Run compile checks.
- Confirm repo docs match the implemented Browser Use state.

### Verification

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall backend tests
```

## Parallelization Rules

- Use parallel agents only for bounded repo inspection, test-gap discovery, or doc cross-checking.
- Do not split active code edits for the same files across agents.
- Keep commits phase-scoped and linear.

## Manual Live-Validation Checklist

This remains necessary even after all automated work lands.

1. Validate `profiles/depop` can create a draft without submitting.
2. Validate `profiles/ebay` can extract sold comps from the direct search URL.
3. Validate each buy search agent extracts at least two real listings with seller and recency metadata.
4. Validate negotiation can open the contact/offer flow and return either `sent` or a structured `failed` result.
5. Confirm SSE emits milestone events in order during live runs.
