# Backend Scaffold

This scaffold gives the team a stable local contract before Browser Use, Gemini, and Fetch.ai integration work lands.

## Current Endpoints

- `GET /health`
- `GET /agents`
- `GET /pipelines`
- `POST /sell/start`
- `POST /buy/start`
- `POST /sell/correct`
- `GET /stream/{session_id}`
- `GET /result/{session_id}`
- `POST /internal/event/{session_id}`

## Current Behavior

- Sessions are stored in memory only.
- Pipelines run in the background; Browser Use-capable agents attempt live browser execution first and fall back to deterministic local logic when the Browser Use runtime or warmed profiles are unavailable.
- Each agent input is validated against a step-specific schema before the orchestrator calls that step.
- Each agent output is validated against a step-specific schema before it is emitted to SSE or saved in `/result`.
- The orchestrator applies per-step timeouts, emits `agent_error` and `agent_retrying` events, retries transient `BUY` search failures once by default, and stores partial results on pipeline failure.
- `AGENT_EXECUTION_MODE=local_functions` keeps the app runnable without launching separate agent processes.
- `python -m backend.run_agents` starts one FastAPI process per agent scaffold when you want to validate the per-agent `/task` apps.
- `make check` is the current local verification path and mirrors CI.

## Browser Use Validation Harness

Use the backend-only harness when you need repeatable Browser Use checks without frontend or Fetch.ai in the loop.

```bash
python scripts/browser_use_validation.py --group buy_search
python scripts/browser_use_validation.py --group pipeline --json
python scripts/browser_use_validation.py --scenario depop_listing --require-live
```

- `--group buy_search` runs the four marketplace search agents.
- `--group pipeline` runs full `sell` and `buy` smoke scenarios against the FastAPI app.
- `--scenario ... --require-live` is useful for warmed-profile checks before demos.
- `--mode fallback` forces deterministic fallback mode for quick local sanity checks.

## Next Backend Tasks

- Manually validate the profile-gated Browser Use paths on real logged-in marketplace accounts.
- Add frontend-facing custom Browser Use events such as `listing_found` and `offer_sent` where needed.
- Add actual Fetch.ai uAgent and Chat Protocol registration plus Agentverse verification.
