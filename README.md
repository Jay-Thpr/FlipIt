# DiamondHacks

FastAPI backend scaffold for the DiamondHacks resale-agent demo. The current repo state is a working backend shell with in-memory sessions, SSE streaming, 10 agent services, and an automated test suite.
Agent inputs and outputs are validated against step-specific schemas so pipeline contracts stay structurally stable as real logic is added. All 10 agents now run deterministic non-stub logic, and the orchestrator includes timeout, retry, and structured failure-event handling for demo resilience.

Supabase persistence scaffolding is also present in the repo for the next backend phase:

- [supabase/README.md](supabase/README.md)
- [supabase/migrations/20260404145000_init_session_persistence.sql](supabase/migrations/20260404145000_init_session_persistence.sql)
- [backend/supabase_repo.py](backend/supabase_repo.py)

## Quick Start

```bash
make install
make check
```

Run the backend:

```bash
make run
```

Run the separate agent apps:

```bash
make run-agents
```

For local development, copy `.env.example` to `.env` and set `INTERNAL_API_TOKEN`. Live Browser Use flows also require `GOOGLE_API_KEY`, warmed profiles under `profiles/`, and Chromium installed by `make install`.

## Core Commands

- `make install` creates `.venv` and installs dependencies.
- `make test` runs the pytest suite.
- `make compile` byte-compiles backend and tests as a quick build sanity check.
- `make check` runs tests plus compile checks.
- `make ci` matches the local CI flow.

## Current API

- `GET /health`
- `GET /agents`
- `GET /pipelines`
- `POST /sell/start`
- `POST /buy/start`
- `GET /stream/{session_id}`
- `GET /result/{session_id}`
- `POST /internal/event/{session_id}`

## Browser Use Deployment Notes

- Browser Use agents run behind the FastAPI task layer and fall back to deterministic logic if Browser Use dependencies, auth profiles, or `GOOGLE_API_KEY` are missing.
- Render builds must install Chromium with `python -m patchright install chromium`.
- Headed Chromium needs a paid Render instance for demo reliability; the free tier is not sufficient for live Browser Use runs.
- Set `INTERNAL_API_TOKEN` and `GOOGLE_API_KEY` in the Render dashboard as secrets instead of committing values into `render.yaml`.
