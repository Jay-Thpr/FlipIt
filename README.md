# DiamondHacks

FastAPI backend scaffold for the DiamondHacks resale-agent demo. The current repo state is a working backend shell with in-memory sessions, SSE streaming, 10 agent services, and an automated test suite.
Agent inputs and outputs are validated against step-specific schemas so pipeline contracts stay structurally stable as real logic is added. All 10 agents now run deterministic non-stub logic, and the orchestrator includes timeout, retry, and structured failure-event handling for demo resilience.

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

Browser Use-backed agents run inside the FastAPI pipeline and use headed Chromium via `patchright`. Local setup comes from `make install`; Render builds must also run `python -m patchright install chromium` so the browser binary exists before the service starts.

For deployment, use a paid Render plan. Headed Chromium is too heavy for the free tier, and Browser Use tasks routinely need longer timeouts than local deterministic agents. Render should keep `AGENT_EXECUTION_MODE=local_functions`, set `AGENT_TIMEOUT_SECONDS=60`, and provide `GOOGLE_API_KEY` plus `INTERNAL_API_TOKEN` as dashboard-managed secrets.

## Browser Use Deployment Notes

- Browser Use agents run behind the FastAPI task layer and fall back to deterministic logic if Browser Use dependencies, auth profiles, or `GOOGLE_API_KEY` are missing.
- Render builds must install Chromium with `python -m patchright install chromium`.
- Headed Chromium needs a paid Render instance for demo reliability; the free tier is not sufficient for live Browser Use runs.
- Set `INTERNAL_API_TOKEN` and `GOOGLE_API_KEY` in the Render dashboard as secrets instead of committing values into `render.yaml`.
