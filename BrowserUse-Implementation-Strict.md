# Browser Use Strict Implementation Plan

## Purpose

This plan expands [BrowserUse-Implementation-Plan.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Implementation-Plan.md) into execution phases for the remaining backend-side Browser Use work. It is scoped to the FastAPI `/task` contract described in [BROWSER_USE_GUIDE.md](/Users/jt/Desktop/diamondhacks/BROWSER_USE_GUIDE.md), the product behavior in [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md), and the current implementation status tracked in [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md).

## Constraints

- Do not change the frontend contract by removing existing SSE events.
- Keep Fetch.ai `/chat` work out of scope; that is owned separately.
- Additive schema changes are allowed if they preserve current pipeline behavior.
- Every phase must land with tests before the next phase begins.
- Commit after each completed phase.

## Phase 1: Browser Use Progress Events

Goal: emit backend milestone events without coupling to any frontend implementation.

Implementation:
- Add a shared helper that appends milestone events to the current session using `session_manager`.
- Emit `listing_found` from each Browser Use-backed search agent for every returned listing.
- Emit `draft_created` from `depop_listing_agent` when a draft is populated and `draft_status` is known.
- Emit `offer_prepared`, `offer_sent`, and `offer_failed` from `negotiation_agent` for each prepared or attempted offer.
- Keep existing pipeline and agent lifecycle events unchanged.

Tests:
- Extend [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py) to assert milestone events are included in session history and SSE payloads.
- Add a focused event helper test file if needed.

Commit boundary:
- milestone event helper
- search/listing/negotiation event emission
- pipeline event coverage

## Phase 2: Marketplace Failure Hardening

Goal: make Browser Use fallbacks and failures observable and consistent.

Implementation:
- Add additive runtime metadata to Browser Use-facing outputs:
  - search outputs report `execution_mode` and `browser_use_error`
  - sold comps report `execution_mode` and `browser_use_error`
  - Depop listing reports `execution_mode` and `browser_use_error`
- Normalize Browser Use exceptions into short failure reasons.
- Preserve deterministic fallback behavior when Browser Use is unavailable or the DOM changes.
- Emit `browser_use_fallback` when an agent falls back after a live attempt fails.

Tests:
- Extend [tests/test_browser_use_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime.py).
- Extend [tests/test_buy_search_agents_real.py](/Users/jt/Desktop/diamondhacks/tests/test_buy_search_agents_real.py).
- Extend [tests/test_depop_listing_agent_real.py](/Users/jt/Desktop/diamondhacks/tests/test_depop_listing_agent_real.py).
- Extend any sold-comps tests that assert the live/fallback split.

Commit boundary:
- metadata fields
- fallback classification helpers
- agent-specific failure tests

## Phase 3: Backend Validation Harness

Goal: make Browser Use validation repeatable without depending on the frontend.

Implementation:
- Add a backend validation harness module that can run canned SELL and BUY Browser Use scenarios through the real `/task` apps.
- Support agent-level runs and grouped runs.
- Produce structured JSON and human-readable summaries.
- Allow fallback-only mode and live-attempt mode through env flags.

Tests:
- Add [tests/test_browser_use_validation_harness.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_validation_harness.py).
- Validate report generation, scenario selection, and non-zero exit behavior for failed validations.

Commit boundary:
- harness module
- CLI entrypoint
- harness tests

## Phase 4: Deployment and Runtime Verification Tooling

Goal: make runtime readiness checkable before demo execution.

Implementation:
- Add a verification script that inspects env vars, Browser Use dependency availability, profile directories, and Render-sensitive runtime settings.
- Report hard failures separately from warnings.
- Add a live-validation checklist for warmed marketplace accounts and expected manual observations.

Tests:
- Add [tests/test_browser_use_runtime_verifier.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime_verifier.py).
- Extend [tests/test_project_scaffold.py](/Users/jt/Desktop/diamondhacks/tests/test_project_scaffold.py) if new docs or commands are documented.

Commit boundary:
- runtime verifier
- manual validation checklist
- scaffold/runtime verification tests

## Phase 5: Full Verification

Required commands:

```bash
./.venv/bin/python -m pytest -q tests/test_pipelines.py tests/test_browser_use_runtime.py tests/test_buy_search_agents_real.py tests/test_depop_listing_agent_real.py tests/test_buy_decision_agents_real.py
./.venv/bin/python -m pytest -q tests/test_browser_use_validation_harness.py tests/test_browser_use_runtime_verifier.py tests/test_project_scaffold.py
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall backend tests
```

Completion criteria:
- all phase gates pass
- full suite passes
- Browser Use status docs mention the new progress events, harness, and runtime verifier
- remaining manual work is limited to live marketplace validation against real accounts
