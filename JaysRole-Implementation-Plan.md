# Jay's Role Implementation Plan

## Key Risks And Things To Watch For

- SSE contract drift: if event names or payload shapes change after frontend work starts, integration slows down immediately. Freeze event names and payloads early.
- Agent interface churn: every `/task` endpoint must keep a stable `{"session_id","payload"}` request shape and a predictable JSON response shape so Browser Use and AI teammates can build independently.
- Mixing two transport models: local app execution will use direct HTTP calls to agent `/task` endpoints, while Fetch.ai Chat Protocol exists for Agentverse discoverability. Do not let those two paths diverge in naming or capability descriptions.
- Session lifecycle bugs: if sessions are created after pipeline kickoff, closed too early, or not cleaned up on failure, SSE streams will hang or vanish. Handle create, push, complete, and cleanup explicitly.
- In-memory state loss: session queues and result storage are intentionally ephemeral. This is acceptable for the hackathon, but any process restart drops active sessions.
- Long-running agent calls: Browser Use tasks can take 10-30 seconds and may fail unpredictably. Use clear timeouts, surface partial progress over SSE, and never let one stuck agent block cleanup forever.
- Error propagation gaps: every agent failure needs an `agent_error` event and a clear pipeline decision: retry, fallback, skip, or fail fast.
- Port collisions: 10 agents plus FastAPI means many local listeners. Fix the port map once and document it in one place.
- Render process model: Render expects one foreground process. The startup script must background agent processes reliably, then keep FastAPI in the foreground.
- Fetch.ai registration timing: mailbox registration and Agentverse propagation can be slow. Registration should happen after local scaffolding is stable, not during initial coding.
- Missing environment variables: many failures will look like runtime bugs but are actually missing seeds, API keys, or internal secrets. Add `.env.example` early and validate env at startup.
- Cross-teammate merge conflicts: the highest-risk files are `main.py`, shared agent base code, and any central schema/constants file. Keep teammate-owned logic isolated behind stubs.
- Browser Use instability on protected sites: eBay, Depop, and OfferUp can block automation. The backend must assume partial failure is normal and keep the demo path alive.
- Demo-path priority: the SELL flow is the clearest must-ship path. If time gets tight, protect SELL first, then BUY search, then BUY haggling, then Fetch polish.

## Goal

Deliver the backend and Fetch.ai infrastructure described in [Jay'sRole.md](/Users/jt/Desktop/diamondhacks/Jay'sRole.md): FastAPI + SSE backbone, 10 agent scaffolds with Chat Protocol support, local orchestration for SELL and BUY flows, Render deployment assets, and teammate integration contracts.

## Success Criteria

- A teammate can start FastAPI and all agents locally and run stubbed SELL and BUY flows end to end.
- The mobile app can consume live SSE events from a stable contract without polling.
- Browser Use and AI teammates have fixed files and stub functions to implement without changing architecture code.
- All 10 agents are structurally ready for Agentverse registration and ASI:One discovery.
- The repo contains enough docs and scripts that setup does not depend on verbal handoff.

## Proposed Repository Structure

```text
backend/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── vision_agent.py
│   ├── ebay_research_agent.py
│   ├── pricing_agent.py
│   ├── depop_listing_agent.py
│   ├── depop_search_agent.py
│   ├── ebay_search_agent.py
│   ├── mercari_search_agent.py
│   ├── offerup_search_agent.py
│   ├── ranking_agent.py
│   ├── haggling_agent.py
│   └── README_TEMPLATE.md
├── main.py
├── session.py
├── schemas.py
├── constants.py
├── run_agents.py
├── requirements.txt
├── .env.example
├── start.sh
└── render.yaml
README.md
```

## Phase Plan

### Phase 0: Project Skeleton And Contracts
Estimated time: 30-45 minutes

Purpose: create the structure that everyone else will build against.

Files to create:
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/constants.py`
- `backend/schemas.py`
- `backend/session.py`
- `backend/agents/__init__.py`

Tasks:
- Create the `backend/` directory and final file layout.
- Define canonical agent names and fixed local ports.
- Define SSE event names as constants.
- Define Pydantic request and response schemas for:
  `SellRequest`, `BuyRequest`, `InternalEventRequest`, generic task request, and common result envelopes.
- Write `.env.example` with every required variable:
  Agentverse API key, internal secret, FastAPI base URL, and 10 seed phrases.

Acceptance checks:
- The file layout exists.
- Environment variables are documented in one place.
- Shared constants and schemas can be imported without circular dependencies.

### Phase 1: FastAPI Backbone
Estimated time: 60-90 minutes

Purpose: build the execution and streaming backbone before any agent logic.

Files to implement:
- `backend/main.py`
- `backend/session.py`
- `backend/schemas.py`
- `backend/constants.py`

Endpoints:
- `GET /health`
- `POST /sell/start`
- `POST /buy/start`
- `GET /stream/{session_id}`
- `POST /internal/event/{session_id}`
- `POST /internal/result/{session_id}`
- `GET /result/{session_id}`

Tasks:
- Build in-memory session creation, queue lookup, event push, and cleanup.
- Add permissive CORS for hackathon integration speed.
- Create background pipeline entrypoints for SELL and BUY.
- Implement SSE streaming with keepalive `ping` events.
- Store final results in a separate in-memory results map.
- Return useful HTTP errors for unknown sessions and bad secrets.

Acceptance checks:
- `GET /health` returns success.
- A manual test can create a fake session and receive streamed events.
- Disconnects and completion signals close SSE cleanly.

### Phase 2: Pipeline Orchestration
Estimated time: 60 minutes

Purpose: encode Jay's ownership over sequencing and session-level control flow.

Files to implement:
- `backend/main.py`
- `backend/constants.py`

Tasks:
- Implement `run_sell_pipeline()` with strict sequential calls:
  Vision -> eBay Research -> Pricing -> Depop Listing.
- Implement `run_buy_pipeline()` with strict sequential search:
  Depop -> eBay -> Mercari -> OfferUp -> Ranking -> Haggling x N.
- Emit `pipeline_started`, `agent_started`, `agent_completed`, `agent_error`, `pipeline_complete`, and any listing or offer events required by the PRD.
- Decide pipeline behavior per failure:
  fail fast for core SELL failures, continue on partial BUY search failures, and cap haggling to a safe max count.
- Implement a single `call_agent()` helper for local HTTP task execution with timeout handling.

Acceptance checks:
- Stubbed SELL flow produces ordered events and a final result.
- Stubbed BUY flow aggregates search results, ranks them, and iterates haggling targets.
- Agent failures appear in SSE and produce deterministic pipeline behavior.

### Phase 3: Shared Agent Base
Estimated time: 60-90 minutes

Purpose: reduce duplication across 10 agents and lock the integration pattern once.

Files to implement:
- `backend/agents/base_agent.py`

Responsibilities:
- Shared env loading
- Shared task request model usage
- Shared `push_log()` and possibly `push_event()` helpers back to FastAPI
- Shared Chat Protocol wiring for Agentverse discoverability
- Shared app startup pattern for running a FastAPI task server and a uAgent together

Tasks:
- Create a reusable factory or base pattern for agent task apps.
- Standardize agent metadata:
  display name, local port, seed env var, description, and keywords.
- Keep agent-specific business logic in isolated functions that teammates can replace safely.

Acceptance checks:
- One agent can be launched from the base pattern.
- Logs and SSE callbacks work from inside agent code.
- Chat Protocol support is present even before real business logic exists.

### Phase 4: Scaffold All 10 Agents
Estimated time: 90-120 minutes

Purpose: unblock all teammates by creating every file they need immediately.

Files to implement:
- `backend/agents/vision_agent.py`
- `backend/agents/ebay_research_agent.py`
- `backend/agents/pricing_agent.py`
- `backend/agents/depop_listing_agent.py`
- `backend/agents/depop_search_agent.py`
- `backend/agents/ebay_search_agent.py`
- `backend/agents/mercari_search_agent.py`
- `backend/agents/offerup_search_agent.py`
- `backend/agents/ranking_agent.py`
- `backend/agents/haggling_agent.py`

Tasks:
- Give every agent a `/task` endpoint.
- Return stubbed but structurally correct JSON.
- Emit summary text suitable for the frontend activity feed.
- Clearly mark teammate-owned stub sections with comments.
- Keep all request parsing and response shapes consistent across agents.

Teammate ownership boundaries:
- Browser Use owner:
  `ebay_research_agent.py`, `depop_listing_agent.py`, `depop_search_agent.py`, `ebay_search_agent.py`, `mercari_search_agent.py`, `offerup_search_agent.py`, `haggling_agent.py` browser steps.
- AI owner:
  `vision_agent.py`, `pricing_agent.py`, `ranking_agent.py`, `haggling_agent.py` message generation.
- Jay:
  structure, server wiring, event/log plumbing, Chat Protocol, ports, and orchestration compatibility.

Acceptance checks:
- All 10 modules start without syntax errors.
- Every `/task` endpoint accepts the same outer request envelope.
- Main pipeline code can call all 10 agents locally with stubbed outputs.

### Phase 5: Local Process Management
Estimated time: 30-45 minutes

Purpose: make the stack runnable by a human without manual process juggling.

Files to implement:
- `backend/run_agents.py`
- `backend/start.sh`

Tasks:
- Start all 10 agents as subprocesses with readable logging.
- Handle graceful shutdown when interrupted.
- Keep startup messages obvious enough to copy agent addresses later.
- Use `start.sh` to background agents and keep FastAPI as the foreground process for Render.

Acceptance checks:
- `python run_agents.py` starts all agents locally.
- `bash start.sh` works in a local shell.
- Ctrl+C stops child processes cleanly.

### Phase 6: Local Smoke Testing
Estimated time: 45-60 minutes

Purpose: validate the foundation before real automation or model integration.

Files to add or update:
- `README.md`
- Optional lightweight test script or curl examples

Tasks:
- Run FastAPI and all stub agents locally.
- Trigger SELL and BUY sessions manually.
- Inspect SSE output for event order and missing fields.
- Verify `/result/{session_id}` fallback behavior.
- Verify error cases:
  bad session, bad internal secret, agent timeout, agent returns malformed data.

Acceptance checks:
- Both flows complete end to end with stubbed agents.
- SSE feed is stable enough for frontend integration.
- Failures are visible and recoverable.

### Phase 7: Render Deployment Assets
Estimated time: 30-45 minutes

Purpose: prepare deployment once local behavior is stable.

Files to implement:
- `backend/render.yaml`
- `backend/start.sh`
- `README.md`

Tasks:
- Add the Render service definition and environment variable inventory.
- Ensure the start command matches the multi-process startup model.
- Document the required paid plan assumption for browser memory footprint.
- Keep `FASTAPI_BASE_URL` overridable for local and hosted use.

Acceptance checks:
- Deployment files are syntactically correct.
- The repo documents every required Render env var.

### Phase 8: Fetch.ai Registration Readiness
Estimated time: 30-45 minutes

Purpose: make Agentverse registration a finishing step, not a refactor.

Files to implement or update:
- `backend/agents/README_TEMPLATE.md`
- `README.md`

Tasks:
- Ensure every agent exposes stable metadata:
  name, description, capability wording, and seed source.
- Document the mailbox registration flow and where agent addresses get copied into `main.py`.
- Add the required `innovationlab` badge template for per-agent README content.

Acceptance checks:
- No code changes should be needed to register agents beyond filling env vars and running them.
- Metadata is consistent between code, docs, and Agentverse descriptions.

### Phase 9: Teammate Handoff Docs
Estimated time: 30-45 minutes

Purpose: reduce Slack or Discord back-and-forth during the hackathon.

Files to update:
- `README.md`
- This plan file

Tasks:
- Document local ports and endpoint examples.
- Document SSE event handling for frontend.
- Document which files Browser Use and AI teammates should modify.
- Include example request payloads for SELL and BUY starts.

Acceptance checks:
- A teammate can identify exactly where to plug in their logic without asking for clarification.

## File Responsibilities

### `backend/main.py`
- FastAPI app setup
- CORS
- API endpoints
- SELL and BUY orchestration
- local `call_agent()` helper
- final result storage integration

### `backend/session.py`
- in-memory session queue map
- create, get, push, close lifecycle helpers

### `backend/constants.py`
- agent names
- port map
- SSE event names
- default timeouts
- any shared status strings

### `backend/schemas.py`
- Pydantic request models
- internal event schema
- task envelope schema
- optionally shared result envelopes for consistency

### `backend/agents/base_agent.py`
- common startup and shared helper logic
- Chat Protocol wiring
- event push helpers back to FastAPI

### `backend/agents/*.py`
- per-agent `/task` endpoint
- teammate-owned business logic stubs
- summary generation for frontend display
- agent metadata for registration

### `backend/run_agents.py`
- subprocess startup and shutdown for all agents

### `backend/start.sh`
- deployment startup entrypoint

### `backend/render.yaml`
- Render service definition and env vars

### `README.md`
- local run instructions
- endpoint examples
- teammate integration notes
- deployment and registration notes

## Recommended Implementation Sequence

1. Create the backend folder, env file, requirements, constants, schemas, and session manager.
2. Implement FastAPI endpoints and a fake SSE test path.
3. Add pipeline orchestration and the local `call_agent()` helper.
4. Build the shared base agent.
5. Scaffold all 10 agent modules with stub returns.
6. Add `run_agents.py` and verify local startup.
7. Run manual stubbed SELL and BUY smoke tests.
8. Write teammate integration instructions.
9. Add Render deployment files.
10. Add Fetch.ai registration assets and instructions.

## Timeboxed Priority If The Hackathon Gets Tight

### Must Ship
- FastAPI + SSE infrastructure
- Shared schemas and constants
- All 10 scaffolded agents with stable ports and `/task` handlers
- SELL pipeline wired end to end with stub or real outputs

### Should Ship
- BUY pipeline wired end to end
- `run_agents.py` and clean local startup
- Render deployment assets
- Teammate integration docs

### Last Mile
- Agentverse registration polish
- ASI:One verification
- Per-agent README uploads

## Open Decisions To Make Early

- Whether `schemas.py` should define full per-agent result models or only shared transport envelopes.
- Whether final pipeline results should be assembled in FastAPI only, or also posted back from agents to `/internal/result/{session_id}`.
- Whether to keep `AGENT_ADDRESSES` directly in `main.py` or move them into env/config after registration.
- Whether to add a minimal automated smoke test file now or rely on documented curl-based testing for speed.

## First Implementation Milestone

The first milestone should end with this exact demo:
- start all agents locally
- start FastAPI locally
- `POST /sell/start`
- open `GET /stream/{session_id}`
- watch ordered stub events stream through to `pipeline_complete`

Once that works, the architecture is doing its job and teammates can start filling in the real logic.
