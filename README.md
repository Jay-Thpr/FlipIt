# DiamondHacks

FastAPI backend scaffold for the DiamondHacks resale-agent demo. The current repo state is a working backend shell with in-memory sessions, SSE streaming, 10 agent services, and an automated test suite.
Agent inputs and outputs are now validated against step-specific schemas so pipeline contracts stay structurally stable as real logic is added. `vision_agent`, `ebay_sold_comps_agent`, and `pricing_agent` now run deterministic non-stub logic for the `SELL` pipeline.

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
