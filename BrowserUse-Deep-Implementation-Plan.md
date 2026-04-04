# Browser Use Deep Implementation Plan

## Goal

Finish the remaining backend-side Browser Use work without touching frontend, Fetch.ai runtime, or the vision agent. The scope in this plan follows:

- [BrowserUse-Implementation-Plan.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Implementation-Plan.md)
- [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md)
- [BROWSER_USE_GUIDE.md](/Users/jt/Desktop/diamondhacks/BROWSER_USE_GUIDE.md)
- [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md)
- [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md)

## Constraints

- Keep Browser Use behind the existing FastAPI `/task` contract.
- Add tests before or alongside each phase and require that they pass before moving on.
- Make additive schema changes only.
- Preserve deterministic fallback behavior so CI and local development remain stable without Browser Use credentials or Chromium.
- Commit after each completed phase.

## Phase 1: Progress Events

### Objective

Emit granular SSE events from Browser Use-capable agents so the frontend can later subscribe to meaningful milestones without depending on agent internals.

### Changes

- Add a backend helper for agent-side progress event emission that works in `local_functions` mode and remains compatible with `/internal/event` for `local_http` mode.
- Emit `listing_found` events from:
  - [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py)
  - [backend/agents/ebay_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_search_agent.py)
  - [backend/agents/mercari_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/mercari_search_agent.py)
  - [backend/agents/offerup_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/offerup_search_agent.py)
- Emit `draft_created` from [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py).
- Emit `offer_prepared`, `offer_sent`, and `offer_failed` from [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py).
- Keep the orchestrator lifecycle events unchanged.

### Test Gate

- Extend [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py)
- Add [tests/test_browser_use_progress_events.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_progress_events.py)

### Commit Boundary

- Commit when the new event helper, agent emissions, and event tests all pass.

## Phase 2: Failure Hardening

### Objective

Make live Browser Use failures diagnosable without breaking pipeline output stability.

### Changes

- Add additive Browser Use runtime metadata models in [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py).
- Record whether each Browser Use-capable step ran live, fell back, skipped due to missing profile/runtime, or failed and recovered.
- Classify failures into stable categories such as `runtime_unavailable`, `profile_missing`, `navigation`, `validation`, and `unknown`.
- Update:
  - [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py)
  - [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py)
  - [backend/agents/ebay_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_search_agent.py)
  - [backend/agents/mercari_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/mercari_search_agent.py)
  - [backend/agents/offerup_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/offerup_search_agent.py)
  - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
  - [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py)
- Reuse shared helpers where possible instead of duplicating exception handling.

### Test Gate

- Extend:
  - [tests/test_browser_use_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime.py)
  - [tests/test_buy_search_agents_real.py](/Users/jt/Desktop/diamondhacks/tests/test_buy_search_agents_real.py)
  - [tests/test_depop_listing_agent_real.py](/Users/jt/Desktop/diamondhacks/tests/test_depop_listing_agent_real.py)
  - [tests/test_buy_decision_agents_real.py](/Users/jt/Desktop/diamondhacks/tests/test_buy_decision_agents_real.py)

### Commit Boundary

- Commit when every Browser Use-capable output includes stable runtime metadata and the phase test suite passes.

## Phase 3: Backend Validation Harness

### Objective

Add a backend-only harness so marketplace automation can be exercised repeatedly without frontend or Fetch.ai dependencies.

### Changes

- Add a CLI entry point under `backend/` for:
  - single-agent task execution with canned payloads
  - full `sell` and `buy` pipeline smoke runs against the FastAPI app
  - optional `--live` versus fallback-only modes
  - JSON output suitable for teammates and demo validation
- Add canned payload builders for:
  - `ebay_sold_comps`
  - the four search agents
  - `depop_listing`
  - `negotiation`
- Document how to use the harness in [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md) and [BROWSER_USE_GUIDE.md](/Users/jt/Desktop/diamondhacks/BROWSER_USE_GUIDE.md).

### Test Gate

- Add [tests/test_browser_use_validation_harness.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_validation_harness.py)

### Commit Boundary

- Commit when the harness runs in deterministic mode during tests and the docs reflect the workflow.

## Phase 4: Deployment and Runtime Verification Tooling

### Objective

Make Browser Use deployment readiness measurable before Render or demo runs.

### Changes

- Add a verification module under `backend/` that checks:
  - required environment variables
  - Browser Use dependency availability
  - Chromium/Patchright availability
  - profile directory presence for authenticated agents
  - timeout and max-step settings
- Add a simple CLI that prints machine-readable and human-readable verification results.
- Document local and Render verification in:
  - [README.md](/Users/jt/Desktop/diamondhacks/README.md)
  - [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md)
  - [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md)

### Test Gate

- Add [tests/test_browser_use_runtime_verifier.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime_verifier.py)
- Extend [tests/test_project_scaffold.py](/Users/jt/Desktop/diamondhacks/tests/test_project_scaffold.py) for documentation references where needed

### Commit Boundary

- Commit when the verifier passes deterministically in tests and the docs explain the verification path.

## Phase 5: Live Validation Checklist

### Objective

Capture the remaining manual work in a format that is executable by the team before demo use.

### Changes

- Add a dedicated manual validation tracker covering:
  - warmed profile prerequisites
  - per-agent live validation steps
  - expected progress events
  - success/failure capture fields
  - rerun procedure after DOM breakage
- Link it from [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md) and [BROWSER_USE_GUIDE.md](/Users/jt/Desktop/diamondhacks/BROWSER_USE_GUIDE.md).

### Test Gate

- Extend [tests/test_project_scaffold.py](/Users/jt/Desktop/diamondhacks/tests/test_project_scaffold.py) to ensure the new validation doc is referenced from the repo docs.

### Commit Boundary

- Commit when the checklist is present and linked from the Browser Use docs.

## Final Verification

Run after every phase where relevant and once at the end:

```bash
./.venv/bin/python -m pytest -q tests/test_browser_use_runtime.py tests/test_buy_search_agents_real.py tests/test_depop_listing_agent_real.py tests/test_buy_decision_agents_real.py tests/test_browser_use_progress_events.py tests/test_browser_use_validation_harness.py tests/test_browser_use_runtime_verifier.py tests/test_project_scaffold.py tests/test_pipelines.py
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall backend tests
```
