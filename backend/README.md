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
- Pipelines run in the background; `vision_agent` and `ebay_sold_comps_agent` now run deterministic `SELL` pipeline logic, while the remaining agents still return scaffold outputs.
- Each agent input is validated against a step-specific schema before the orchestrator calls that step.
- Each agent output is validated against a step-specific schema before it is emitted to SSE or saved in `/result`.
- `AGENT_EXECUTION_MODE=local_functions` keeps the app runnable without launching separate agent processes.
- `python -m backend.run_agents` starts one FastAPI process per agent scaffold when you want to validate the per-agent `/task` apps.
- `make check` is the current local verification path and mirrors CI.

## Next Backend Tasks

- Replace the remaining stub agent logic with real Browser Use and Gemini logic, starting with `pricing_agent` and `depop_listing_agent`.
- Add actual Fetch.ai uAgent and Chat Protocol registration.
- Add richer result schemas and retry/error policies.
