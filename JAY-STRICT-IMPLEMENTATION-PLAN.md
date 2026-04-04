# Jay Infrastructure Hardening — Strict Plan

This plan is derived from [JAY-PLAN.md](/Users/jt/Desktop/diamondhacks/JAY-PLAN.md) and constrained by the current Browser Use implementation documented in [BROWSER_USE_GUIDE.md](/Users/jt/Desktop/diamondhacks/BROWSER_USE_GUIDE.md), [BrowserUse-Implementation-Plan.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Implementation-Plan.md), [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md), [PROJECT-CONTEXT.md](/Users/jt/Desktop/diamondhacks/PROJECT-CONTEXT.md), [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md), and [README.md](/Users/jt/Desktop/diamondhacks/README.md).

## Phase 1: Backend Connectivity Hardening

- Add tests for browser-facing CORS behavior on `GET /health` and `OPTIONS /sell/start`.
- Add tests for SSE keepalive comments on `GET /stream/{session_id}` during idle gaps.
- Implement `CORSMiddleware` and module-level `KEEPALIVE_INTERVAL` in [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py).
- Verification gate:
  - `./.venv/bin/python -m pytest -q tests/test_health_and_sessions.py`

## Phase 2: Runtime and Deployment Contract Hardening

- Add/update tests covering:
  - `.env.example` variables from [backend/config.py](/Users/jt/Desktop/diamondhacks/backend/config.py) and [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)
  - `.gitignore` excludes `.env`
  - `render.yaml` Browser Use env vars, secret handling, and Chromium build step
  - pinned Browser Use dependencies in `requirements.txt`
  - Render/browser runtime note in [README.md](/Users/jt/Desktop/diamondhacks/README.md)
- Resolve and pin the current `browser-use`, `langchain-google-genai`, and `patchright` versions by installing the stack once, then freezing those exact versions into `requirements.txt`.
- Implement config/doc updates in `.env.example`, `.gitignore`, `render.yaml`, and `README.md`.
- Verification gate:
  - `make install`
  - `./.venv/bin/python -m pytest -q tests/test_project_scaffold.py`

## Phase 3: Contract Documentation Consistency

- Add/update tests for SSE naming and runtime contract wording in [CLAUDE.md](/Users/jt/Desktop/diamondhacks/CLAUDE.md) and related scaffold docs.
- Implement doc fixes so repo guidance matches the actual underscore-delimited orchestrator events and Render/runtime assumptions.
- Verification gate:
  - `./.venv/bin/python -m pytest -q tests/test_project_scaffold.py`
  - `./.venv/bin/python -m pytest -q`

## Commit Policy

- Commit after each completed phase with a focused message.
- Do not begin a later phase until the current phase test gate passes.
