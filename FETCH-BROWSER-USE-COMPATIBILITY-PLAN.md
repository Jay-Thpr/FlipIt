# Fetch + Browser Use Compatibility Plan

## Goal

Keep the product-facing FastAPI backend and the parallel Fetch adapter path behaviorally aligned while Browser Use remains the marketplace execution layer.

## Completed

- Fixed brittle BUY tests that drifted with relative dates and ranking math updates.
- Routed `FETCH_ENABLED=true` orchestration through the Fetch adapter with structured `AgentTaskRequest` inputs.
- Preserved real pipeline `session_id` and `context` when Fetch-backed steps execute, so Browser Use events still attach to the active FastAPI session.
- Added end-to-end compatibility coverage for:
  - SELL with `BROWSER_USE_FORCE_FALLBACK=true`
  - BUY with `BROWSER_USE_FORCE_FALLBACK=true`
  - local SELL review loop with revise then confirm
  - BUY with `FETCH_ENABLED=true` and `BROWSER_USE_FORCE_FALLBACK=true`
- Updated the Makefile so `make run-fetch-agents` uses the dedicated `.venv-fetch` virtualenv instead of the main `.venv`.
- Documented port and virtualenv coexistence for `make run`, `make run-agents`, and `make run-fetch-agents`.

## Verified

- Focused compatibility suite covering Browser Use fallback, Fetch routing, and project scaffold expectations
- Broader pipeline and event suite covering main FastAPI flows, Browser Use progress events, and Fetch runtime behavior

## Remaining

- Live Browser Use validation on real logged-in marketplace profiles
- Agentverse / mailbox verification for the Fetch agents in a real networked environment
- Real browser-level checkpoint hardening for the SELL review boundary
- Timeout and cleanup hardening for abandoned paused SELL review sessions
