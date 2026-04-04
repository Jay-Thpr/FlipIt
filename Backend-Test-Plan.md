# Backend Test Plan

## Key Risks To Validate First

- `SSE delivery breaks or stalls`: if the stream does not emit start, step, and completion events in order, the frontend demo will feel dead even when the backend is running.
- `Session state diverges from events`: `/result/{session_id}` and `/stream/{session_id}` must tell the same story.
- `Pipeline ordering regresses`: `SELL` and `BUY` both depend on strict step ordering.
- `Agent contract drift`: each agent must accept the same request envelope and return the same response shape.
- `Background task failure is invisible`: failed tasks must surface cleanly in both session state and SSE.
- `In-memory state edge cases`: bad session IDs, reconnects, duplicate requests, and process restarts need predictable behavior.
- `Fallback execution path breaks`: `AGENT_EXECUTION_MODE=local_functions` is the current default and must remain reliable.
- `Separate agent apps drift from in-process execution`: `/task` behavior should match whether the backend calls local functions or per-agent FastAPI apps.

## Purpose

This document defines a comprehensive set of tests to validate the backend scaffold for Jay's role. It is designed to answer three questions:

1. Does each individual step work?
2. Does each step produce the right shape of output for the next step?
3. Does the whole system behave reliably under demo conditions?

## Scope

This plan covers:

- FastAPI backend endpoints
- In-memory session lifecycle
- SSE streaming behavior
- SELL pipeline orchestration
- BUY pipeline orchestration
- Each of the 10 agent scaffolds
- Internal event routing
- Local multi-process agent startup
- Render-readiness checks

This plan does not yet cover:

- Real Browser Use flows
- Real Fetch.ai Agentverse registration
- Real Gemini output quality
- End-to-end mobile frontend rendering

## Environments

### Local Backend Only

- `AGENT_EXECUTION_MODE=local_functions`
- Run `uvicorn backend.main:app --reload`
- Use this mode for the fastest API and orchestration validation

### Local Multi-Process

- `AGENT_EXECUTION_MODE=http`
- Run `python -m backend.run_agents`
- Run `uvicorn backend.main:app --reload`
- Use this mode to verify that per-agent `/task` apps behave correctly over HTTP

### Render Smoke

- Deploy backend only
- Keep `AGENT_EXECUTION_MODE=local_functions`
- Use this mode to verify deployment and demo survivability before introducing more moving parts

## Core Contracts To Freeze

Before adding real logic, these contracts should be treated as stable and regression-tested:

- `POST /sell/start`
- `POST /buy/start`
- `GET /stream/{session_id}`
- `GET /result/{session_id}`
- `POST /internal/event/{session_id}`
- `POST /task` on every agent app
- Session event names:
  - `pipeline.started`
  - `agent.started`
  - `agent.completed`
  - `pipeline.completed`
  - `pipeline.failed`

## Test Data

### SELL Input Fixture

```json
{
  "user_id": "demo-user-1",
  "input": {
    "image_urls": ["https://example.com/shirt.jpg"],
    "notes": "Vintage Nike tee"
  },
  "metadata": {
    "source": "manual-test"
  }
}
```

### BUY Input Fixture

```json
{
  "user_id": "demo-user-2",
  "input": {
    "query": "Nike vintage tee size M",
    "budget": 45,
    "target_platforms": ["depop", "ebay", "mercari", "offerup"]
  },
  "metadata": {
    "source": "manual-test"
  }
}
```

## Test Matrix

### 1. Boot And Health Checks

#### T1. Backend health endpoint

- Goal: confirm the API process boots
- Setup: run `uvicorn backend.main:app --reload`
- Action: call `GET /health`
- Expected:
  - status code `200`
  - body contains `{"status":"ok"}`
- Failure signals:
  - import error on boot
  - non-200 response
  - malformed JSON

#### T2. Every agent app health endpoint

- Goal: confirm all 10 agent processes boot independently
- Setup: run `python -m backend.run_agents`
- Action: call `GET /health` on ports `9101` through `9110`
- Expected:
  - each returns `200`
  - body includes `status=ok`
  - body includes the correct `agent` slug
- Failure signals:
  - missing process
  - wrong agent slug on a port
  - port collision

### 2. Session Lifecycle

#### T3. SELL start creates a session

- Goal: confirm session creation contract
- Action: call `POST /sell/start` with the SELL fixture
- Expected:
  - status code `200`
  - response contains:
    - `session_id`
    - `pipeline = sell`
    - `status = queued`
    - usable `stream_url`
    - usable `result_url`
- Follow-up:
  - call `GET /result/{session_id}`
- Expected follow-up:
  - session exists
  - `pipeline = sell`
  - `status` becomes `running` or `completed`

#### T4. BUY start creates a session

- Goal: confirm BUY session creation contract
- Action: call `POST /buy/start` with the BUY fixture
- Expected:
  - same guarantees as `T3`, but `pipeline = buy`

#### T5. Unknown session returns 404

- Goal: confirm clean handling of bad IDs
- Action:
  - call `GET /result/not-a-real-session`
  - call `GET /stream/not-a-real-session`
- Expected:
  - both return `404`
  - error payload is clear and stable

### 3. SSE Behavior

#### T6. SELL stream emits the full event sequence

- Goal: confirm frontend-visible event flow for SELL
- Setup:
  - create a SELL session
  - connect to `GET /stream/{session_id}`
- Expected event order:
  1. `pipeline.started`
  2. `agent.started` for `vision_analysis`
  3. `agent.completed` for `vision_analysis`
  4. `agent.started` for `ebay_sold_comps`
  5. `agent.completed` for `ebay_sold_comps`
  6. `agent.started` for `pricing`
  7. `agent.completed` for `pricing`
  8. `agent.started` for `depop_listing`
  9. `agent.completed` for `depop_listing`
  10. `pipeline.completed`
- Validate:
  - each event includes the same `session_id`
  - timestamps are present
  - step names match orchestration order
  - final event terminates the stream cleanly

#### T7. BUY stream emits the full event sequence

- Goal: confirm frontend-visible event flow for BUY
- Expected event order:
  1. `pipeline.started`
  2. `agent.started` for `depop_search`
  3. `agent.completed` for `depop_search`
  4. `agent.started` for `ebay_search`
  5. `agent.completed` for `ebay_search`
  6. `agent.started` for `mercari_search`
  7. `agent.completed` for `mercari_search`
  8. `agent.started` for `offerup_search`
  9. `agent.completed` for `offerup_search`
  10. `agent.started` for `ranking`
  11. `agent.completed` for `ranking`
  12. `agent.started` for `negotiation`
  13. `agent.completed` for `negotiation`
  14. `pipeline.completed`

#### T8. Stream replay includes prior events

- Goal: confirm reconnect behavior after partial progress
- Setup:
  - start a session
  - let at least two events happen
  - connect to the stream after progress has already begun
- Expected:
  - existing session events are replayed first
  - new events continue after replay
- Failure signal:
  - reconnecting users miss already-emitted steps

### 4. Result Integrity

#### T9. Completed SELL result matches streamed steps

- Goal: confirm no divergence between SSE and stored state
- Action:
  - complete a SELL run
  - compare `GET /result/{session_id}` against the streamed events
- Expected:
  - `status = completed`
  - `result.pipeline = sell`
  - `result.outputs` contains:
    - `vision_analysis`
    - `ebay_sold_comps`
    - `pricing`
    - `depop_listing`
  - `events` includes the same step names and order as the stream

#### T10. Completed BUY result matches streamed steps

- Goal: same integrity check for BUY
- Expected:
  - `status = completed`
  - `result.pipeline = buy`
  - `result.outputs` contains:
    - `depop_search`
    - `ebay_search`
    - `mercari_search`
    - `offerup_search`
    - `ranking`
    - `negotiation`

### 5. Individual Agent Contract Tests

Run the following tests against each agent app and, separately, against the in-process local registry path.

#### T11. Agent accepts the standard task envelope

- Goal: confirm request shape consistency
- Action: `POST /task` with:

```json
{
  "session_id": "test-session",
  "pipeline": "sell",
  "step": "test-step",
  "input": {
    "sample": true
  },
  "context": {
    "source": "contract-test"
  }
}
```

- Expected:
  - status code `200`
  - response contains:
    - `session_id`
    - `step`
    - `status`
    - `output`

#### T12. Agent returns its correct identity

- Goal: catch copy-paste mistakes between scaffolds
- Expected:
  - `output.agent` matches the app being called
  - `output.display_name` matches the intended agent name

#### T13. Agent completes without unexpected fields missing

- Goal: confirm minimum downstream-safe output
- Expected:
  - `status = completed`
  - `output.summary` exists
  - output shape is a JSON object, not a list or string

#### Agent-Specific Efficacy Checks

##### T14. Vision Agent

- Validate:
  - returns `detected_item`
  - returns category-like metadata
  - output is useful as resale-identification input

##### T15. eBay Sold Comps Agent

- Validate:
  - returns sold-price summary
  - returns sample size or equivalent confidence indicator
  - output is usable by pricing logic

##### T16. Pricing Agent

- Validate:
  - returns a proposed list price
  - returns profit or margin signal
  - output is usable by listing generation

##### T17. Depop Listing Agent

- Validate:
  - returns listing title
  - returns listing description
  - output is usable by the frontend listing review flow

##### T18. Depop Search Agent

- Validate:
  - returns a `results` array
  - each result looks like a listing candidate

##### T19. eBay Search Agent

- Validate:
  - same expectations as the Depop search agent

##### T20. Mercari Search Agent

- Validate:
  - same expectations as the Depop search agent

##### T21. OfferUp Search Agent

- Validate:
  - same expectations as the Depop search agent

##### T22. Ranking Agent

- Validate:
  - returns a top choice
  - returns candidate count or ranking metadata
  - output is usable by negotiation logic

##### T23. Negotiation Agent

- Validate:
  - returns at least one message or offer payload
  - output is usable by a messaging or offer-sending step

### 6. Orchestration Behavior

#### T24. SELL executes in strict order

- Goal: confirm no out-of-order execution
- Method:
  - inspect event order from the stream
  - confirm the next step does not start before the prior step completes
- Expected:
  - exactly one active step at a time

#### T25. BUY executes in strict order

- Goal: same ordering guarantee for BUY
- Expected:
  - ranking does not start before all search agents complete
  - negotiation does not start before ranking completes

#### T26. Previous outputs are passed forward

- Goal: confirm step chaining
- Method:
  - instrument or inspect agent input in a test harness
  - verify `previous_outputs` grows as the pipeline progresses
- Expected:
  - each later step receives all earlier outputs in its input envelope

### 7. Error Handling

#### T27. Forced agent failure marks the session failed

- Goal: confirm failure visibility
- Setup:
  - temporarily modify one agent to return `status = failed`
- Expected:
  - stream emits `pipeline.failed`
  - `/result/{session_id}` shows `status = failed`
  - `/result/{session_id}` includes a meaningful `error`

#### T28. Stream closes on terminal failure

- Goal: prevent hanging frontend subscriptions
- Expected:
  - after `pipeline.failed`, the stream ends cleanly

#### T29. Invalid internal token is rejected

- Goal: verify internal event endpoint protection
- Action:
  - call `POST /internal/event/{session_id}` with no token
  - call with a bad token
- Expected:
  - both return `401`

#### T30. Valid internal event is appended to session history

- Goal: verify internal event routing
- Action:
  - call `POST /internal/event/{session_id}` with the correct `x-internal-token`
- Expected:
  - response is accepted
  - event appears in session history
  - if a stream is connected, the event is emitted live

### 8. Execution Mode Parity

#### T31. Local function mode works end-to-end

- Goal: protect the default demo path
- Setup:
  - `AGENT_EXECUTION_MODE=local_functions`
- Expected:
  - full SELL and BUY flows complete without running `backend.run_agents`

#### T32. HTTP mode works end-to-end

- Goal: protect future distributed execution
- Setup:
  - `AGENT_EXECUTION_MODE=http`
  - run `python -m backend.run_agents`
- Expected:
  - full SELL and BUY flows complete through HTTP `/task` calls

#### T33. Output parity across execution modes

- Goal: ensure the same agent logic is exposed both ways
- Method:
  - run the same input through both modes
  - compare response shapes
- Expected:
  - same field names
  - same status values
  - materially equivalent outputs

### 9. Concurrency And Stability

#### T34. Two sessions can run concurrently

- Goal: catch shared-state bugs
- Action:
  - start two SELL sessions, or one SELL and one BUY, nearly simultaneously
- Expected:
  - both complete
  - events do not leak between session IDs
  - result data stays isolated

#### T35. Multiple stream subscribers can attach to one session

- Goal: validate frontend reconnect or multi-observer behavior
- Action:
  - connect two stream clients to the same session
- Expected:
  - both receive the same event sequence

#### T36. Process restart behavior is explicit

- Goal: document the in-memory state limitation
- Action:
  - create a session
  - restart the backend process
  - request the same session
- Expected:
  - session is gone
  - behavior is understood and documented as an intentional current limitation

### 10. Deployment Readiness

#### T37. `start.sh` launches the app successfully

- Goal: validate deployment entrypoint
- Action:
  - run `./start.sh`
- Expected:
  - server boots with no missing-module errors

#### T38. Render config is internally consistent

- Goal: catch deployment configuration drift early
- Validate:
  - `render.yaml` references `requirements.txt`
  - `render.yaml` uses `./start.sh`
  - `APP_PORT` and `APP_BASE_URL` assumptions are coherent

## Suggested Automation Split

### Priority 1: Immediate Automated Tests

- Health endpoints
- Session creation
- Unknown session 404s
- SELL event order
- BUY event order
- Session/result integrity
- Internal token rejection
- Internal event acceptance
- Local function end-to-end flow

### Priority 2: Next Automated Tests

- HTTP execution mode end-to-end flow
- Per-agent `/task` contract tests
- Concurrent sessions
- Multi-subscriber SSE behavior
- Forced failure propagation

### Priority 3: Manual Demo Rehearsal Tests

- Full SELL run while watching live SSE output
- Full BUY run while watching live SSE output
- Repeat runs back-to-back
- Restart/recovery expectations
- Hosted Render smoke run

## Pass Criteria

The scaffold should be considered stable enough for teammate integration when all of the following are true:

- All health checks pass
- SELL and BUY both complete in local function mode
- SSE events arrive in the correct order
- `/result/{session_id}` matches the streamed execution history
- All 10 agents pass the standard `/task` contract test
- Invalid session and invalid token cases fail cleanly
- At least one concurrent-session test passes

## Failure Triage Guide

If a test fails, classify it immediately:

- `Contract failure`: wrong schema, missing field, bad status code
- `Ordering failure`: steps execute out of order
- `State failure`: session result and event history disagree
- `Transport failure`: SSE or HTTP call path breaks
- `Deployment failure`: boot, env, or start command issues
- `Agent logic failure`: step returns unusable output

This classification matters because the highest-priority fixes should be contract and transport issues first, then ordering and state issues, then agent logic quality.

## Recommended Next Step

Turn the Priority 1 section into actual automated tests first. That gives the team a fast safety net before real Browser Use and AI logic start changing the scaffold.
