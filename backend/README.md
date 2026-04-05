# Backend Scaffold

This scaffold gives the team a stable local contract before Gemini work lands and now includes parallel integration paths for Browser Use execution and Fetch.ai registration.

## Current Endpoints

- `GET /health`
- `GET /agents`
- `GET /pipelines`
- `POST /sell/start`
- `POST /buy/start`
- `POST /sell/correct`
- `POST /sell/listing-decision`
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
- `python -m backend.run_fetch_agents` starts 10 Fetch `uAgents` that wrap the same local agent logic for Agentverse/ASI:One.
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

## Fetch Agents

The mobile app still talks to FastAPI directly. Fetch.ai is implemented as a parallel adapter layer:

- FastAPI + SSE stay as the product-facing interface for the mobile app.
- Browser Use remains the browser execution layer used by search, listing, and negotiation agents.
- Fetch `uAgents` reuse the same backend agent logic so the Agentverse path does not diverge from the app path.

### Setup

1. Install dependencies:

```bash
make install
```

2. Run the Fetch agents on Python 3.12 or 3.13. `uagents==0.24.0` does not currently import cleanly on Python 3.14 in this environment.

3. Set unique Fetch seeds in your environment or `.env`.

4. Start one Fetch agent:

```bash
PYTHONPATH=$PWD python -m backend.fetch_agents.launch depop_search_agent
```

5. Start all Fetch agents:

```bash
make run-fetch-agents
```

### Chat-to-Agent Mapping

- `vision_agent` turns the chat message into item notes and optional image URLs.
- `ebay_sold_comps_agent` runs vision first, then sold comps.
- `pricing_agent` runs vision + sold comps + pricing.
- `depop_listing_agent` runs the full SELL chain through listing creation.
- `depop_search_agent`, `ebay_search_agent`, `mercari_search_agent`, and `offerup_search_agent` treat the chat message as a marketplace search query and attempt Browser Use first.
- `ranking_agent` runs the BUY search chain and ranking.
- `negotiation_agent` runs the BUY flow through negotiation.

## Next Backend Tasks

- Manually validate the profile-gated Browser Use paths on real logged-in marketplace accounts.
- Add frontend-facing custom Browser Use events such as `listing_found` and `offer_sent` where needed.
- Add live Agentverse verification and profile metadata for each Fetch agent.
