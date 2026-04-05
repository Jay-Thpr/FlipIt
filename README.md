# DiamondHacks

FastAPI backend scaffold for the DiamondHacks resale-agent demo. The repo now exposes both the product-facing FastAPI backend and a specialized Fetch/Agentverse surface with public customized agents backed by the same local resale workflows.
Agent inputs and outputs are validated against step-specific schemas so pipeline contracts stay structurally stable as real logic is added. All 10 backend agents still run deterministic non-stub logic, and the Fetch layer now adds a public `resale_copilot_agent`, specialist public agents, README-backed metadata, and deterministic handoff or clarification behavior for Agentverse demos.

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
- `./.venv/bin/python scripts/browser_use_validation.py --group buy_search` runs backend-only Browser Use smoke validation for the search agents.
- `./.venv/bin/python -m backend.browser_use_validation --mode fallback --scenario depop_listing` forces deterministic fallback for a targeted validation case.
- `./.venv/bin/python -m backend.browser_use_validation --require-live --group sell` fails if the selected sell-side scenarios do not execute in live Browser Use mode.
- `./.venv/bin/python -m backend.browser_use_runtime_audit` audits Chromium, env vars, profile directories, and runtime settings before live Browser Use runs.

## Fetch Agentverse Surface

- Public Fetch agents: `resale_copilot_agent`, `vision_agent`, `pricing_agent`, and `depop_listing_agent`.
- Internal Fetch worker agents stay available through the local runtime for orchestration, but they are not part of the default public launch set.
- `GET /fetch-agents` exposes the Fetch catalog with persona, capabilities, example prompts, task family, README path, and public/private status.
- `GET /fetch-agent-capabilities` adds runtime verification details such as seed presence and README availability.
- `make run-fetch-agents` now launches only the public Agentverse-facing agents.
- `PYTHONPATH=$PWD .venv-fetch/bin/python scripts/fetch_demo.py --catalog` prints the judge-path catalog and sample prompts.

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
- Use the validation harness before demos: fallback mode checks contract stability, and `--require-live` confirms that selected flows actually executed through Browser Use.
- Use [BrowserUse-Live-Validation.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Live-Validation.md) as the manual pre-demo checklist for warmed profiles and platform-specific smoke tests.
