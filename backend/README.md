# Backend Scaffold

This scaffold gives the team a stable local contract before Gemini work lands and now includes parallel integration paths for Browser Use execution and Fetch.ai registration.

## Local Run

Use the Makefile targets. They activate the correct virtualenvs for you.

1. Install the main backend environment:

```bash
make install
```

2. Create the Fetch virtualenv once if you plan to run the Fetch agents:

```bash
make venv-fetch
```

3. Export the runtime variables in the shell that will launch the app:

```bash
export AGENT_EXECUTION_MODE=local_functions
export INTERNAL_API_TOKEN=dev-internal-token
export APP_HOST=0.0.0.0
export APP_PORT=8000
export APP_BASE_URL=http://localhost:8000
export FETCH_ENABLED=false
```

4. Start the FastAPI backend:

```bash
make run
```

5. If you are validating Fetch agents, set the Fetch-specific variables in a second shell:

```bash
export AGENTVERSE_API_KEY=your_agentverse_key
export FETCH_ENABLED=true
export VISION_FETCH_AGENT_SEED=vision-fetch-agent-seed
export EBAY_SOLD_COMPS_FETCH_AGENT_SEED=ebay-sold-comps-fetch-agent-seed
export PRICING_FETCH_AGENT_SEED=pricing-fetch-agent-seed
export DEPOP_LISTING_FETCH_AGENT_SEED=depop-listing-fetch-agent-seed
export DEPOP_SEARCH_FETCH_AGENT_SEED=depop-search-fetch-agent-seed
export EBAY_SEARCH_FETCH_AGENT_SEED=ebay-search-fetch-agent-seed
export MERCARI_SEARCH_FETCH_AGENT_SEED=mercari-search-fetch-agent-seed
export OFFERUP_SEARCH_FETCH_AGENT_SEED=offerup-search-fetch-agent-seed
export RANKING_FETCH_AGENT_SEED=ranking-fetch-agent-seed
export NEGOTIATION_FETCH_AGENT_SEED=negotiation-fetch-agent-seed
```

6. Start the Fetch agents:

```bash
make run-fetch-agents
```

7. Keep the ports in mind while debugging:

- FastAPI backend: `8000`
- Per-agent FastAPI apps from `make run-agents`: `9101-9110`
- Fetch `uAgents` from `make run-fetch-agents`: `9201-9210`

## Current Endpoints

- `GET /health`
- `GET /agents`
- `GET /fetch-agents`
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
- `make run-agents` starts one FastAPI process per agent scaffold when you want to validate the per-agent `/task` apps.
- `make run-fetch-agents` starts 10 Fetch `uAgents` that wrap the same local agent logic for Agentverse/ASI:One.
- When `FETCH_ENABLED=true`, orchestrator step execution routes through the Fetch adapter layer instead of the direct local registry.
- `make check` is the current local verification path and mirrors CI.

## Browser Use Validation Harness

Use the backend-only harness when you need repeatable Browser Use checks without frontend or Fetch.ai in the loop.

```bash
./.venv/bin/python -m backend.browser_use_runtime_audit --require-live
./.venv/bin/python -m backend.browser_use_validation --group buy_search --require-live
./.venv/bin/python -m backend.browser_use_validation --group pipeline --json
./.venv/bin/python -m backend.browser_use_validation --scenario depop_listing --require-live
```

- `--require-live` fails if the live Browser Use prerequisites are missing.
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

1. Install the standard backend dependencies:

```bash
make install
```

2. Create the dedicated Fetch virtualenv on Python 3.12:

```bash
make venv-fetch
```

3. Run the Fetch agents on Python 3.12 or 3.13. `uagents==0.24.0` does not currently import cleanly on Python 3.14 in this environment.

4. Set unique Fetch seeds and `AGENTVERSE_API_KEY` in your environment or `.env`.

5. Start one Fetch agent:

```bash
PYTHONPATH=$PWD python -m backend.fetch_agents.launch depop_search_agent
```

6. Start all Fetch agents from the dedicated Fetch virtualenv:

```bash
make run-fetch-agents
```

- `make run` keeps using `.venv` for the FastAPI app on port `8000`.
- `make run-fetch-agents` uses `.venv-fetch` for the Fetch `uAgents` on ports `9201-9210`.
- The per-agent FastAPI apps from `make run-agents` stay on ports `9101-9110`, so all three launch paths can coexist without port overlap.

7. Send a local smoke-test chat payload to a running Fetch agent:

```bash
. .venv/bin/activate && python scripts/fetch_demo.py 9205 "Vintage Nike tee under $45"
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
