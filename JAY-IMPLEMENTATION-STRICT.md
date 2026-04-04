# Jay Strict Implementation Plan

This plan operationalizes `JAY-PLAN.md` into gated phases. Do not advance to the next phase until the current phase tests pass.

## Phase 1: CORS Middleware

- Files: `backend/main.py`, `tests/test_health_and_sessions.py`
- Change: add `CORSMiddleware` to the FastAPI app with hackathon-safe permissive settings.
- Tests:
  - `OPTIONS /health` with `Origin` and `Access-Control-Request-Method` returns the expected CORS headers.
  - `GET /health` echoes `Access-Control-Allow-Origin` when an `Origin` header is present.
- Gate: CORS tests pass before any SSE or deployment edits.

## Phase 2: SSE Keepalive

- Files: `backend/main.py`, `tests/test_pipelines.py`
- Change: add a module-level keepalive interval and emit SSE comment pings when no queued events arrive before timeout.
- Tests:
  - stream returns `: ping` while idle and continues waiting.
  - stream still terminates after `pipeline_complete` and `pipeline_failed`.
- Gate: all stream tests pass before env or Render edits.

## Phase 3: Runtime Dependency and Env Hygiene

- Files: `requirements.txt`, `.env.example`, `.gitignore`, `tests/test_project_scaffold.py`
- Change:
  - pin `browser-use`, `langchain-google-genai`, and `patchright`.
  - expand `.env.example` to match current runtime contract.
  - ensure `.env` is ignored.
- Tests:
  - scaffold test asserts pinned dependency lines.
  - scaffold test asserts `.env.example` includes all required runtime variables.
  - scaffold test asserts `.gitignore` excludes `.env`.
- Gate: scaffold tests pass before deployment-doc changes.

## Phase 4: Render and README Alignment

- Files: `render.yaml`, `README.md`, `tests/test_project_scaffold.py`
- Change:
  - add Render env vars required by Browser Use and internal events.
  - update build command to install Chromium via `patchright`.
  - document paid Render requirement and Browser Use deployment constraints in `README.md`.
- Tests:
  - scaffold test asserts Render build command and env var map.
  - doc test asserts README mentions Browser Use/Render deployment requirements.
- Gate: Render/doc tests pass before `CLAUDE.md` cleanup.

## Phase 5: CLAUDE Event Contract Cleanup

- Files: `CLAUDE.md`, `tests/test_project_scaffold.py`
- Change: remove stale dot-delimited event references and document underscore-delimited event names used by `backend/orchestrator.py`.
- Tests:
  - doc test asserts `CLAUDE.md` references underscore event names and does not reference the stale dot-delimited names.
- Gate: targeted tests plus full `pytest -q` and `compileall` pass.

## Final Verification

- Run targeted tests after each phase.
- Run `./.venv/bin/python -m pytest -q` after Phase 5.
- Run `./.venv/bin/python -m compileall backend tests`.
- Commit each completed phase separately.
