# Backend Scaffold

This scaffold gives the team a stable local contract before Browser Use, Gemini, and Fetch.ai integration work lands.

## Current Endpoints

- `GET /health`
- `GET /agents`
- `GET /pipelines`
- `POST /sell/start`
- `POST /buy/start`
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

## Persistence Scaffolding

- [supabase/README.md](../supabase/README.md) documents the intended persistence model.
- [supabase/migrations/20260404145000_init_session_persistence.sql](../supabase/migrations/20260404145000_init_session_persistence.sql) creates the initial session, event, and result tables.
- [supabase_repo.py](supabase_repo.py) contains the repository layer for future durable session storage integration.

## Next Backend Tasks

- Manually validate the profile-gated Browser Use paths on real logged-in marketplace accounts.
- Add frontend-facing custom Browser Use events such as `listing_found` and `offer_sent` where needed.
- Add actual Fetch.ai uAgent and Chat Protocol registration plus Agentverse verification.
