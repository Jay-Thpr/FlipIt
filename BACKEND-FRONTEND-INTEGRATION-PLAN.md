# Backend-Frontend Integration Plan

Date: 2026-04-05

## Goal

Make the backend safe and predictable for frontend integration so a frontend branch can be merged cleanly without discovering API or state-management surprises late.

This plan is grounded in the current backend behavior:

- FastAPI exposes `POST /sell/start`, `POST /buy/start`, `GET /stream/{session_id}`, and `GET /result/{session_id}` in [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py).
- Pipelines are asynchronous and session-driven, not synchronous request/response flows.
- The sell flow has explicit pause/resume checkpoints for user correction and listing review.
- Session state is currently in memory only in [backend/session.py](/Users/jt/Desktop/diamondhacks/backend/session.py).
- There is no checked-in `frontend/` app in this repo right now, so the immediate task is to make the integration contract explicit and hard to misuse.

## Current Backend Readiness

## What is already good

- The core endpoint surface is stable and tested.
- Input and output contracts are explicit in [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py).
- The orchestrator already emits a meaningful SSE event stream in [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py).
- Sell review pause and resume behavior already exists and is covered by tests in [tests/test_sell_correct_endpoint.py](/Users/jt/Desktop/diamondhacks/tests/test_sell_correct_endpoint.py) and [tests/test_sell_listing_decision_endpoint.py](/Users/jt/Desktop/diamondhacks/tests/test_sell_listing_decision_endpoint.py).
- `make check` currently passes, so the backend has a solid baseline before integration changes.

## What is not ready enough yet

- The backend does not publish a frontend-facing integration spec anywhere in-repo.
- Session durability is weak because all state lives in process memory.
- The frontend would need to infer too much from raw SSE event names and payload shapes.
- Absolute `stream_url` and `result_url` values depend on `APP_BASE_URL`, which can drift in real deployment setups.
- CORS is open for local development but not intentionally configured for a real frontend deployment.
- The backend has no explicit session summary endpoint or typed state machine doc that a frontend can rely on.
- Browser Use and fallback behavior are exposed in outputs, but the semantics are not normalized into a frontend-ready presentation contract.

## Desired End State

After this plan is complete:

- A frontend engineer can wire the app without reverse-engineering the backend.
- The backend exposes a stable integration contract for start, stream, pause, resume, and result flows.
- SSE event semantics are documented and tested.
- Sell flow pause states are easy for the frontend to detect and render.
- The backend survives ordinary frontend behavior such as reconnecting, polling, resuming, and duplicate button clicks.
- Merging the frontend branch becomes primarily a UI/state-machine task rather than a backend debugging task.

## Workstreams

## Workstream 1: Freeze and document the integration contract

This is the first priority because the frontend should not be built against implied behavior.

### Backend tasks

1. Create a dedicated API contract document for frontend integration.
   Files:
   - `docs/FRONTEND_INTEGRATION_SPEC.md` or equivalent

   It should define:
   - request shapes for `POST /sell/start` and `POST /buy/start`
   - response shape from `PipelineStartResponse`
   - `GET /result/{session_id}` response semantics
   - all terminal statuses: `completed`, `failed`
   - paused sell status: `paused`
   - sell correction contract for `POST /sell/correct`
   - sell listing review contract for `POST /sell/listing-decision`
   - expected polling and SSE behavior
   - how to interpret `execution_mode` and `browser_use.mode`

2. Add a machine-readable integration manifest endpoint.
   Suggested endpoint:
   - `GET /frontend-contract`

   Return:
   - supported pipeline names
   - start endpoints
   - pause-capable pipelines
   - terminal session statuses
   - SSE event names
   - decision actions for sell review

   Reason:
   - a frontend can gate behavior from a single source of truth
   - deployment smoke tests can validate the contract without parsing docs

3. Add an explicit event catalog.
   Current events are spread across orchestration flow and tests.
   Promote them into one canonical constant module, for example:
   - `backend/events.py`

   Include at minimum:
   - `pipeline_started`
   - `agent_started`
   - `agent_completed`
   - `agent_error`
   - `agent_retrying`
   - `pipeline_complete`
   - `pipeline_failed`
   - `vision_result`
   - `pricing_result`
   - `draft_created`
   - `listing_review_required`
   - `listing_review_submitted`
   - `listing_review_expired`
   - `listing_found`
   - `offer_prepared`
   - `browser_use_fallback`

4. Add tests that treat the event catalog as contract, not implementation detail.
   Files:
   - new test file such as `tests/test_frontend_contract.py`

### Definition of done

- A frontend engineer can find one document and one endpoint that describe the integration contract.
- Event names are no longer only implied by test assertions.

## Workstream 2: Make session state frontend-safe

The frontend will reconnect, refresh, double-submit, and occasionally race itself. The backend needs to tolerate that predictably.

### Backend tasks

1. Add explicit session phase metadata to `SessionState`.
   Files:
   - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py)

   Add a normalized field such as:
   - `phase`

   Suggested values:
   - `queued`
   - `running`
   - `awaiting_user_correction`
   - `awaiting_listing_review`
   - `resuming`
   - `completed`
   - `failed`

   Reason:
   - `status="paused"` is too coarse for frontend rendering
   - today the frontend would need to inspect `sell_listing_review` and prior outputs to infer the pause reason

2. Make `GET /result/{session_id}` explicitly frontend-oriented.
   Keep current behavior, but add a normalized top-level section such as:
   - `next_action`
   - `ui_hints`

   Example:
   - `next_action.type = "submit_correction"`
   - `next_action.type = "review_listing"`
   - `next_action.type = "wait"`
   - `next_action.type = "show_result"`

3. Add idempotency protection for user-driven resume actions.
   Files:
   - [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py)
   - [backend/session.py](/Users/jt/Desktop/diamondhacks/backend/session.py)
   - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py)

   Protect:
   - repeated `POST /sell/correct`
   - repeated `POST /sell/listing-decision`

   Approach:
   - reject duplicate resume attempts when the same session is already transitioning
   - or accept idempotently and return the current queued action

4. Add a lightweight persistent session store abstraction.
   Do not jump straight to a database if time is tight.

   Phase 1:
   - introduce a repository interface for session state
   - keep in-memory implementation as the default

   Phase 2:
   - add a file-backed or SQLite-backed implementation for demo resilience

   Reason:
   - frontend integration becomes much smoother when refreshes and local backend restarts are less destructive

### Definition of done

- Frontend code can render from `phase` and `next_action` without reverse-engineering session internals.
- Duplicate user actions do not create ambiguous pipeline behavior.

## Workstream 3: Normalize the sell flow for UI consumption

The sell flow is the hardest part of frontend integration because it pauses mid-pipeline.

### Backend tasks

1. Explicitly separate sell pause reasons in contract and events.
   Current states:
   - low-confidence identification
   - listing ready for confirmation

   Add stable event payload fields:
   - `pause_reason`
   - `required_action`
   - `deadline_at`

2. Normalize the correction payload contract.
   Current correction handling already maps frontend-friendly values like `item_name` into `detected_item`.
   Strengthen this by documenting and testing the accepted aliases.

3. Normalize listing review payloads.
   The frontend needs one stable object for the review screen.

   Ensure `review_state` plus `depop_listing` expose:
   - title
   - description
   - suggested price
   - category path
   - draft status
   - preview image if available
   - screenshot or artifact URL if available
   - deadline
   - revision count remaining

4. Add a dedicated review summary in the result payload.
   Suggested top-level field:
   - `sell_review`

   Purpose:
   - reduce frontend dependence on nested partial output interpretation

5. Add tests that validate the paused-session UI contract.
   Focus on:
   - low-confidence pause
   - ready-for-confirmation pause
   - revision loop
   - timeout expiry
   - revision-limit exhaustion

### Definition of done

- The sell frontend can be written as a simple state machine.
- No UI screen needs to understand raw agent internals.

## Workstream 4: Normalize the buy flow for UI consumption

The buy pipeline is simpler but still needs a frontend-oriented contract.

### Backend tasks

1. Add a top-level buy summary object to the session result.
   Suggested fields:
   - `search_summary`
   - `top_choice`
   - `offer_summary`

2. Mark fallback vs live results in a concise frontend-facing way.
   The current outputs expose `execution_mode` and `browser_use`.
   Add a normalized field such as:
   - `result_source = "live" | "fallback" | "mixed"`

3. Add pagination or truncation rules for large event streams and results.
   The current event list grows inside the session object.
   For frontend usability:
   - keep a stable recent event window in `/result`
   - reserve full history for a dedicated debug endpoint if needed

4. Add tests asserting the buy result is renderable without reading every step output.

### Definition of done

- A frontend can render the buy result screen from one summarized object plus optional drill-down data.

## Workstream 5: Harden transport behavior for real frontend usage

The current backend is locally usable, but frontend merge will be smoother if transport behavior is explicit and stable.

### Backend tasks

1. Revisit `stream_url` and `result_url` generation.
   Files:
   - [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py)

   Recommended change:
   - return relative paths in addition to absolute URLs
   - or make relative paths the primary contract

   Reason:
   - the frontend often already knows the API origin
   - absolute URLs are brittle across proxies, preview URLs, and local tunnels

2. Tighten CORS around actual frontend origins.
   Files:
   - [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py)
   - [backend/config.py](/Users/jt/Desktop/diamondhacks/backend/config.py)

   Add:
   - `ALLOWED_ORIGINS`
   - environment-driven origin config

3. Add request/response examples for browser clients.
   This can live in the frontend integration doc and tests.

4. Add backend timeouts and error shapes that the frontend can classify cleanly.
   Standardize:
   - `detail`
   - `error_code`
   - `retryable`

5. Add heartbeat/reconnect guidance for SSE clients.
   Current keepalive ping exists, but the frontend needs explicit reconnection semantics.

### Definition of done

- A browser client can connect, reconnect, and classify errors without special-case guesswork.

## Workstream 6: Add a merge-safe backend test matrix for frontend work

The frontend branch should not merge based on manual clicking alone.

### Backend tasks

1. Add contract snapshot tests for:
   - `POST /sell/start`
   - `POST /buy/start`
   - `GET /result/{session_id}`
   - paused sell result shape
   - `GET /stream/{session_id}` event sequence

2. Add fixture payloads that frontend tests can reuse.
   Example directory:
   - `tests/fixtures/frontend_contract/`

   Include:
   - sell completed result
   - sell paused for correction
   - sell paused for review
   - sell failed by timeout
   - buy completed result

3. Add one end-to-end backend integration test that simulates the expected frontend loop:
   - start sell
   - receive pause
   - submit correction
   - receive review pause
   - submit confirm
   - read final result

4. Add a second end-to-end flow for buy:
   - start buy
   - consume SSE
   - read final result

### Definition of done

- Frontend integration can be validated from fixtures and backend tests before the real frontend branch lands.

## Workstream 7: Separate product-facing payloads from debug payloads

Right now `/result` is carrying raw backend detail. That is useful, but it mixes UI needs with debugging needs.

### Backend tasks

1. Keep raw per-step outputs for debugging, but add a normalized `presentation` section.
   Example:
   - `presentation.header`
   - `presentation.cards`
   - `presentation.actions`
   - `presentation.alerts`

2. Add a `debug` query parameter or separate endpoint for full raw detail if needed.

3. Make the frontend default to `presentation`, not raw agent outputs.

### Definition of done

- UI-facing payloads can evolve carefully without forcing the frontend to parse agent internals.

## Workstream 8: Prepare the repo for an actual frontend merge

There is no checked-in frontend app yet, so the merge plan needs to define ownership and sequence now.

### Merge sequence

1. Land backend contract changes first.
   Scope:
   - schema additions
   - event catalog
   - integration docs
   - tests and fixtures

2. Freeze the contract.
   Rule:
   - no further shape changes without updating fixtures and tests

3. Build the frontend against the frozen contract in a separate branch or repo.

4. Add a thin integration adapter in the frontend.
   The frontend should centralize:
   - start calls
   - SSE subscription
   - result polling fallback
   - mapping backend `phase` and `next_action` to UI routes/states

5. Run merge validation on both sides.
   Required checks:
   - backend `make check`
   - frontend integration tests
   - one manual sell correction run
   - one manual sell review run
   - one manual buy run

6. Merge only after the backend and frontend both pass the same fixture-backed contract expectations.

## Recommended execution order

### Phase 1: Contract and docs

1. Add the frontend integration spec doc.
2. Add event catalog constants.
3. Add `GET /frontend-contract`.
4. Add snapshot and fixture tests.

### Phase 2: Session normalization

1. Add `phase` to session state.
2. Add `next_action` and normalized pause metadata.
3. Make resume endpoints idempotent or duplicate-safe.

### Phase 3: Result normalization

1. Add sell summary / review summary payload.
2. Add buy summary payload.
3. Add presentation-oriented result section.

### Phase 4: Transport hardening

1. Fix URL generation strategy.
2. Add real origin config.
3. Standardize error codes and retryability markers.

### Phase 5: Persistence and resilience

1. Introduce session store abstraction.
2. Add optional durable demo storage.

### Phase 6: Frontend merge validation

1. Freeze fixtures.
2. Run full backend/frontend integration checklist.

## Suggested file ownership

Backend contract work:
- [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py)
- [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py)
- [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py)
- [backend/session.py](/Users/jt/Desktop/diamondhacks/backend/session.py)
- [backend/config.py](/Users/jt/Desktop/diamondhacks/backend/config.py)
- new `backend/events.py`
- new docs file under `docs/`
- new contract tests and fixtures under `tests/`

Frontend integration adapter work once a frontend exists:
- session state mapping
- SSE client
- polling fallback
- pause/resume flows
- result presentation rendering

## Risks

1. The backend contract is currently functional but too implicit.
   If a frontend is built against inferred behavior now, merge churn is likely.

2. In-memory sessions are acceptable for development but fragile for real demos.
   A backend restart will break frontend continuity.

3. Browser Use and fallback outputs are backend-friendly today, not UI-friendly by default.
   Without normalization, the frontend will accumulate backend-specific parsing logic.

4. The sell flow is where most merge pain will happen.
   If the pause contract is not frozen first, frontend implementation will thrash.

## Success criteria

This plan is complete when:

- the backend exposes a documented and test-backed frontend contract
- the frontend can render from normalized session state instead of raw agent internals
- pause/resume flows are idempotent and easy to integrate
- SSE event semantics are explicit and fixed
- backend and frontend can validate against shared fixture payloads before merge

## Best next step

Start with Workstream 1 and Workstream 2 together:

1. create the frontend integration spec
2. add the event catalog
3. add `phase` and `next_action` to session responses
4. back those changes with fixture-driven tests

That gives the future frontend branch a stable target immediately and removes the biggest source of merge friction.
