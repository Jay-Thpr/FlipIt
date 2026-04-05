# Backend-Frontend Remaining Handoff

Date: 2026-04-05

## Purpose

This file is the handoff plan for the remaining backend work before the current FastAPI backend can be considered cleanly merged with the frontend architecture described on `origin/frontend`.

It is intentionally written for another implementation agent. It separates:

- what is already done
- what is still missing
- what is actively risky
- the recommended implementation order
- the acceptance criteria for each remaining section

## Current State

The backend is materially closer to the frontend architecture than it was at the start of reconciliation work.

Completed backend foundation:

- run normalization and compatibility endpoints
- Supabase config, thin client, and JWT auth foundation
- `agent_runs` / `agent_run_events` migration and repository foundation
- authenticated item-scoped and run-scoped workflow endpoints
- durable session lifecycle write-through into `agent_runs` and `agent_run_events`
- durable-first reads for `/runs/{run_id}` and `/items/{item_id}/runs/latest`
- persisted-history replay for `/runs/{run_id}/stream`
- buy-side durable writeback for conversations, messages, and completed trades
- sell-side projection writeback into `items` and `market_data`

Recent implementation commits:

- `4e35e37` Add frontend run normalization and compatibility endpoints
- `1b351c3` Add Supabase config, httpx client, and JWT auth foundation
- `f02442e` Add agent run persistence foundation
- `a370866` Add authenticated item/run-scoped endpoint layer with ownership enforcement
- `8d404af` Persist session lifecycle to Supabase
- `76ebdbb` Add durable run reads and stream replay
- `012df20` Add buy-side durable writeback for conversations, messages, and completed trades
- `d9d4f73` Add sell-side frontend projection writeback

Repo verification at handoff time:

- `make test` passes
- `make compile` passes
- latest local test count: `395 passed`

## What Is Already Good Enough

These areas are no longer the main blocker for frontend merge:

- public config endpoint for the ASI:One master-agent button
- normalized run payloads with `phase`, `next_action`, `progress`, and `result_source`
- item-scoped run start endpoints
- run-scoped correction and listing-decision endpoints
- persisted run/event history
- durable run lookups after in-memory session loss

## The Big Picture

The backend is no longer missing its basic frontend integration shape.

What is left is mostly about making the merged architecture actually correct and durable in production terms:

- user identity propagation
- Supabase schema completeness
- writeback semantics
- security hardening
- durable artifact handling
- merge-validation against the frontend data model

## Highest-Priority Remaining Work

These are the remaining items that matter most. They should be treated as blocking before calling the backend "frontend-ready".

## 1. Fix authenticated user propagation into durable workflow state

Status:

- partially implemented
- currently unsafe/incomplete

Why this is critical:

- authenticated item endpoints resolve the user from Supabase Auth
- but `backend/main.py` currently injects that user only into `request.metadata`
- durable run persistence in `backend/run_persistence.py` reads `session.request.user_id`
- buy writeback in `backend/orchestrator.py` passes `request.user_id` into `write_back_buy_result`
- if the frontend omits `user_id` in the body, or passes a non-UUID placeholder, persistence/writeback silently degrades or no-ops

Current issue:

- `POST /items/{item_id}/sell/run` and `POST /items/{item_id}/buy/run` should set the authenticated user ID as the canonical `request.user_id`
- right now they only set `metadata.user_id`

What to do:

1. In [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py), update item-scoped start endpoints so the authenticated user becomes:
   - `request.user_id`
   - `request.metadata["user_id"]`
2. Treat the body-provided `user_id` as untrusted for authenticated endpoints.
3. Add focused tests proving:
   - authenticated item run start stores authenticated UUID in the request
   - durable run persistence no longer depends on the client body including `user_id`
   - buy writeback receives the authenticated user ID

Definition of done:

- authenticated item/run workflows persist and write back using the actual authenticated Supabase user

## 2. Add the missing Supabase schema and migration coverage

Status:

- incomplete

Why this is critical:

- the repo currently contains only one migration:
  - [supabase/migrations/20260405_0001_agent_runs.sql](/Users/jt/Desktop/diamondhacks/supabase/migrations/20260405_0001_agent_runs.sql)
- the new repositories and writeback code assume these durable tables exist:
  - `items`
  - `market_data`
  - `conversations`
  - `messages`
  - `completed_trades`
- those tables may exist on the frontend branch or in a separate Supabase project, but they are not represented in this repo right now

What to do:

1. Pull in or recreate the canonical Supabase schema for the frontend-owned tables.
2. Check column names and constraints against actual backend write payloads.
3. Add migrations for any missing tables or missing columns now used by backend writeback.
4. Verify at minimum:
   - `items` contains every projected field the backend updates
   - `market_data` supports the current upsert key and payload
   - `conversations` supports upsert by `user_id + listing_url`
   - `messages` supports the persisted negotiation message fields
   - `completed_trades` supports the current payload

Definition of done:

- a fresh environment can apply repo migrations and support the full backend writeback path without relying on undocumented external schema

## 3. Add RLS and permission hardening for all workflow-related tables

Status:

- incomplete

Why this is critical:

- the current `agent_runs` migration creates tables and indexes
- it does not add row-level security policies
- the reconciliation plan explicitly called for frontend-safe user reads and service-role backend writes

What to do:

1. Add RLS policies for:
   - `agent_runs`
   - `agent_run_events`
   - any frontend-readable tables the backend now writes
2. Ensure:
   - authenticated users can read only their own rows
   - normal clients cannot write workflow persistence rows directly unless explicitly intended
   - service-role backend writes continue working
3. Document any tables intentionally writable by the frontend directly versus backend-only.

Definition of done:

- backend service role can write everything it needs
- frontend users can read only their own workflow state

## 4. Fix buy-side durable writeback semantics

Status:

- partially implemented
- semantics still need review

Why this is critical:

- current buy writeback exists in [backend/buy_writeback.py](/Users/jt/Desktop/diamondhacks/backend/buy_writeback.py)
- it persists:
  - conversations
  - messages
  - a `completed_trade` row for the top-choice listing when an offer is sent

Main semantic concern:

- the reconciliation plan says `completed_trades` should be written when a deal actually closes
- current code writes a completed trade when an offer is sent to the top choice
- that is likely too early and may pollute frontend P&L/trade history

What to do:

1. Decide the real lifecycle for `completed_trades`.
2. Most likely:
   - keep negotiation messages/conversations on offer send
   - do not create `completed_trades` until a real purchase completion signal exists
3. If no purchase-close signal exists yet, either:
   - remove the premature completed-trade write
   - or store that state in a different table/status model
4. Review whether buy writeback should also update:
   - item-facing `best_offer`
   - item-facing buy summary
   - `market_data` snapshots from search/ranking

Definition of done:

- buy writeback reflects real business semantics rather than “offer sent = deal closed”

## 5. Complete sell-side durable review artifact persistence

Status:

- partially implemented

What is done:

- sell projections write key summary fields into `items`
- pricing/comps are projected into `market_data`

What is still missing:

- review artifacts are not fully persisted as durable frontend-visible records
- important sell review fields still mainly live inside run payloads:
  - `draft_url`
  - `form_screenshot_url`
  - listing preview payload
  - revision history / latest review payload

Why this matters:

- the frontend item detail and review screens need deterministic state after refresh or restart
- relying only on nested run payloads makes the UI more brittle

What to do:

1. Decide where review artifacts belong:
   - projected onto `items`
   - a separate artifact table
   - or an explicit JSON column for review payloads
2. Persist enough durable review state to render:
   - current draft/review preview
   - current screenshot/artifact handle
   - current listing review state
   - latest revision instructions and revision count if needed
3. Align the backend payload with the actual frontend screen needs.

Definition of done:

- a paused sell review can be rendered after refresh without depending on transient in-memory-only details

## 6. Freeze one canonical external run identifier

Status:

- decision still muddy

Current behavior:

- API surfaces `run_id = session_id`
- database also has a distinct `agent_runs.id` UUID
- run lookup currently accepts either session ID or persisted DB ID

Why this matters:

- frontend contract should not have ambiguous identity rules
- debugging and data modeling get messier when both IDs behave like public IDs

What to do:

1. Pick one external ID for frontend use.
2. Recommended: keep `run_id = session_id` for compatibility unless there is a strong reason to switch.
3. If keeping session IDs externally:
   - document that `agent_runs.id` is internal storage identity
   - stop treating it as a frontend-facing ID
4. If switching to UUID `agent_runs.id` externally:
   - add an explicit migration path and compatibility layer

Definition of done:

- frontend and backend share one unambiguous definition of `run_id`

## 7. Harden transport behavior for real frontend deployment

Status:

- incomplete

Current issues:

- CORS in [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py) is currently:
  - `allow_origins=["*"]`
  - `allow_credentials=True`
- start responses use absolute URLs derived from `APP_BASE_URL`
- that can drift behind proxies, preview deployments, mobile clients, or separate frontend hosts

What to do:

1. Replace wildcard CORS with environment-driven allowed origins.
2. Decide whether run start responses should return:
   - relative URLs
   - or absolute URLs only when explicitly configured for deployed environments
3. Document expected frontend usage for:
   - `/stream/{session_id}`
   - `/runs/{run_id}/stream`
   - cookies versus bearer token transport
4. Confirm SSE behavior from the actual frontend environment.

Definition of done:

- backend endpoints behave correctly when called from the real merged frontend host(s)

## 8. Decide the long-term status of legacy unauthenticated endpoints

Status:

- intentionally preserved for compatibility
- long-term policy not finalized

Still available:

- `POST /sell/start`
- `POST /buy/start`
- `POST /sell/correct`
- `POST /sell/listing-decision`
- `GET /result/{session_id}`
- `GET /stream/{session_id}`

Why this matters:

- they are useful for tests and backward compatibility
- but they bypass the frontend-oriented auth and item ownership model

What to do:

1. Decide whether these remain:
   - internal/dev-only
   - public but deprecated
   - fully supported compatibility endpoints
2. If dev-only:
   - gate them behind environment flags or internal auth
3. If compatibility-only:
   - document them clearly as non-primary endpoints
4. Update tests and docs to reflect their actual support status.

Definition of done:

- no confusion remains about which endpoints are the real frontend contract

## 9. Expand merge-validation to real authenticated, durable workflows

Status:

- incomplete

Current test state is good, but still mostly backend-centric:

- run contract tests exist
- durable read tests exist
- buy/sell writeback unit tests exist

What is still missing:

- full flow tests against the merged data model
- tests that confirm the durable writes are sufficient for frontend screens

What to add:

1. Full authenticated sell flow:
   - create item
   - start run through `/items/{item_id}/sell/run`
   - low-confidence pause
   - correction
   - listing review
   - confirm submit
   - verify:
     - `agent_runs`
     - `agent_run_events`
     - item projections
     - persisted review artifacts
2. Full authenticated buy flow:
   - create item
   - start `/items/{item_id}/buy/run`
   - complete search/ranking/negotiation
   - verify:
     - normalized run payload
     - conversations/messages writeback
     - correct trade semantics
3. Snapshot or fixture tests for frontend-facing JSON shapes.
4. Restart-style tests:
   - clear in-memory sessions
   - confirm frontend-facing reads still work from durable state

Definition of done:

- the backend contract is validated as a frontend integration surface, not only as an internal orchestration system

## 10. Add repo-local architecture and contract docs that match reality

Status:

- incomplete

Why this matters:

- the code has moved significantly
- the repo still needs one clean source of truth for the merged architecture

What to document:

1. Backend/frontend merged architecture.
2. Canonical endpoint contract.
3. Which data lives in Supabase versus FastAPI.
4. Which endpoints are primary versus compatibility-only.
5. Required Supabase tables, RLS expectations, and env vars.
6. Run lifecycle and frontend state mapping.

Definition of done:

- a teammate can implement frontend integration without reverse-engineering the code

## Important Open Design Decisions

These must be explicitly resolved; otherwise the remaining implementation work will drift.

## A. What constitutes a completed trade?

Current code:

- top-choice offer sent can create a `completed_trades` row

Likely desired behavior:

- only a true closed purchase should create `completed_trades`

Decision needed:

- define the exact event that closes a trade

## B. Where should sell review artifacts live durably?

Options:

- `items`
- dedicated artifact/review table
- embedded JSON on `agent_runs`

Decision needed:

- choose the durable surface the frontend will actually read

## C. What is the canonical frontend-visible run ID?

Options:

- `session_id`
- `agent_runs.id`

Decision needed:

- freeze one

## D. How much of run state should the frontend read from FastAPI versus Supabase directly?

Current direction:

- FastAPI for live workflow starts, run reads, and SSE
- Supabase for durable app entities

Decision needed:

- whether frontend should ever query `agent_runs` directly, or always go through FastAPI for run data

## Recommended Implementation Order

This is the order that keeps risk lowest and rework smallest.

1. Fix authenticated user propagation into `request.user_id`.
2. Pull in or create the missing Supabase schema for frontend-owned tables.
3. Add RLS and permissions for workflow tables and any backend-written app tables.
4. Correct buy writeback semantics, especially `completed_trades`.
5. Complete sell review artifact persistence.
6. Freeze canonical `run_id` semantics and document them.
7. Harden CORS and URL behavior for real frontend deployment.
8. Decide the status of legacy compatibility endpoints.
9. Add full merge-validation suites and durable restart tests.
10. Update repo docs to reflect the merged architecture.

## File Areas Most Likely To Change Next

Core backend:

- [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py)
- [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py)
- [backend/run_persistence.py](/Users/jt/Desktop/diamondhacks/backend/run_persistence.py)
- [backend/run_queries.py](/Users/jt/Desktop/diamondhacks/backend/run_queries.py)
- [backend/frontend_runs.py](/Users/jt/Desktop/diamondhacks/backend/frontend_runs.py)
- [backend/config.py](/Users/jt/Desktop/diamondhacks/backend/config.py)
- [backend/auth.py](/Users/jt/Desktop/diamondhacks/backend/auth.py)
- [backend/supabase.py](/Users/jt/Desktop/diamondhacks/backend/supabase.py)

Repositories and writeback:

- [backend/repositories/items.py](/Users/jt/Desktop/diamondhacks/backend/repositories/items.py)
- [backend/repositories/items_projection.py](/Users/jt/Desktop/diamondhacks/backend/repositories/items_projection.py)
- [backend/repositories/market_data.py](/Users/jt/Desktop/diamondhacks/backend/repositories/market_data.py)
- [backend/repositories/conversations.py](/Users/jt/Desktop/diamondhacks/backend/repositories/conversations.py)
- [backend/repositories/messages.py](/Users/jt/Desktop/diamondhacks/backend/repositories/messages.py)
- [backend/repositories/completed_trades.py](/Users/jt/Desktop/diamondhacks/backend/repositories/completed_trades.py)
- [backend/repositories/agent_runs.py](/Users/jt/Desktop/diamondhacks/backend/repositories/agent_runs.py)
- [backend/buy_writeback.py](/Users/jt/Desktop/diamondhacks/backend/buy_writeback.py)
- [backend/sell_writeback.py](/Users/jt/Desktop/diamondhacks/backend/sell_writeback.py)

Schema and migrations:

- [supabase/migrations/20260405_0001_agent_runs.sql](/Users/jt/Desktop/diamondhacks/supabase/migrations/20260405_0001_agent_runs.sql)
- additional new `supabase/migrations/*`

Tests:

- [tests/test_frontend_run_contract.py](/Users/jt/Desktop/diamondhacks/tests/test_frontend_run_contract.py)
- [tests/test_item_run_auth.py](/Users/jt/Desktop/diamondhacks/tests/test_item_run_auth.py)
- [tests/test_run_query_endpoints.py](/Users/jt/Desktop/diamondhacks/tests/test_run_query_endpoints.py)
- [tests/test_run_stream_history.py](/Users/jt/Desktop/diamondhacks/tests/test_run_stream_history.py)
- [tests/test_buy_writeback.py](/Users/jt/Desktop/diamondhacks/tests/test_buy_writeback.py)
- [tests/test_sell_writeback.py](/Users/jt/Desktop/diamondhacks/tests/test_sell_writeback.py)
- new end-to-end merge-validation tests

## Practical Success Condition

The backend is truly ready for a smooth frontend merge when all of these are true:

- authenticated item-scoped runs always persist with the real authenticated user
- repo migrations fully represent the durable schema the backend writes to
- RLS is present and correct
- buy writeback semantics are not overclaiming completed trades
- paused sell review state is durably renderable after refresh
- frontend and backend use one canonical `run_id`
- transport behavior is deployment-safe
- at least one full buy flow and one full sell flow are validated against the merged durable contract

## Bottom Line

The backend is no longer missing its basic frontend integration architecture.

What remains is the hardening layer:

- make identity propagation correct
- make the Supabase schema real and secure
- make writeback semantics match product reality
- validate the merged contract end to end

That is the remaining path from “backend is structurally compatible with the frontend” to “backend can be handed to the frontend team as a reliable merged platform”.
