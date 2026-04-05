# Frontend-Backend Reconciliation Plan

Date: 2026-04-05

## Purpose

This document reconciles the `origin/frontend` product requirements with the current backend implementation in this branch.

It exists because the frontend branch and backend branch are not describing the same architecture:

- `origin/frontend:UI_REQUIREMENTS.md` and `origin/frontend:PRD.md` assume a mobile app backed by durable app data.
- `origin/frontend:BACKEND_REQUIREMENTS.md` assumes Supabase is the primary app backend and the frontend talks to it directly for auth, CRUD, storage, and realtime.
- The current backend is a FastAPI orchestration service centered on async pipeline sessions, SSE, and in-memory state in `backend/main.py`, `backend/orchestrator.py`, `backend/schemas.py`, and `backend/session.py`.

The goal is not to force one side to conform to the other blindly. The goal is to define the merged architecture that preserves the strong parts of both.

## Recommendation

Adopt a hybrid architecture:

- Supabase becomes the durable system of record for app data.
- FastAPI remains the workflow and orchestration service for buy/sell agent pipelines.
- The frontend talks directly to Supabase for app CRUD, auth, storage, and realtime.
- The frontend talks to FastAPI only for long-running agent workflows, workflow status, sell review decisions, and public integration metadata like `/config`.

This is the only realistic path that:

- preserves the existing frontend branch direction
- preserves the current backend orchestration investment
- avoids duplicating all CRUD in FastAPI
- avoids throwing away the existing sell/buy workflow engine

## What We Should Not Do

Do not execute `origin/frontend:BACKEND_REQUIREMENTS.md` verbatim as if no backend server exists.

Do not force the frontend to use the current session API as its primary app data model.

Do not duplicate full listing/settings/chat CRUD in FastAPI if Supabase is already the durable store.

Do not keep in-memory pipeline sessions as the only source of truth once the frontend is merged.

## Architecture Decision

## Supabase owns

Supabase should be the source of truth for:

- `profiles`
- `user_settings`
- `platform_connections`
- `items`
- `item_platforms`
- `item_photos`
- `market_data`
- `conversations`
- `messages`
- `completed_trades`

Supabase should also gain workflow-oriented tables that do not exist in the frontend requirement doc yet:

- `agent_runs`
- `agent_run_events`

These are required because the current backend is session-driven and the frontend needs durable visibility into workflow progress.

## FastAPI owns

FastAPI should remain responsible for:

- sell pipeline execution
- buy pipeline execution
- Browser Use execution and fallback behavior
- Fetch.ai / Agentverse metadata endpoints
- SSE streaming for active runs
- sell review pause/resume logic
- writeback of workflow outputs into Supabase

## Frontend owns

The frontend should:

- authenticate with Supabase Auth
- read and write durable app entities directly through Supabase
- subscribe to durable entity changes through Supabase Realtime
- call FastAPI only when the user starts or resumes an agent workflow

## Core Mismatch To Resolve

The frontend branch models persistent listings and conversations.

The current backend models transient workflow sessions like:

- `POST /sell/start`
- `POST /buy/start`
- `GET /stream/{session_id}`
- `GET /result/{session_id}`

Those sessions are valid, but they are not durable app records.

The merge plan is therefore:

1. keep the session model as the execution model
2. persist each session into Supabase as an `agent_run`
3. connect `agent_run` records back to durable app entities like `items`
4. let the frontend render app state from Supabase and workflow state from either Supabase or FastAPI

## Required Data Model Changes

`origin/frontend:BACKEND_REQUIREMENTS.md` is missing workflow persistence. Add these tables.

### 1. `agent_runs`

Each row represents one orchestrated buy or sell run.

Suggested columns:

- `id UUID PRIMARY KEY`
- `session_id TEXT UNIQUE NOT NULL`
- `user_id UUID NOT NULL REFERENCES auth.users(id)`
- `item_id UUID REFERENCES public.items(id) ON DELETE SET NULL`
- `pipeline TEXT NOT NULL CHECK (pipeline IN ('sell', 'buy'))`
- `status TEXT NOT NULL`
- `phase TEXT NOT NULL`
- `next_action_type TEXT`
- `next_action_payload JSONB NOT NULL DEFAULT '{}'::jsonb`
- `request_payload JSONB NOT NULL DEFAULT '{}'::jsonb`
- `result_payload JSONB NOT NULL DEFAULT '{}'::jsonb`
- `error TEXT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `completed_at TIMESTAMPTZ`

Purpose:

- durable workflow status
- stable link between frontend items and backend sessions
- restart-safe run visibility

### 2. `agent_run_events`

Each row records a meaningful workflow event.

Suggested columns:

- `id UUID PRIMARY KEY`
- `run_id UUID NOT NULL REFERENCES public.agent_runs(id) ON DELETE CASCADE`
- `session_id TEXT NOT NULL`
- `event_type TEXT NOT NULL`
- `step TEXT`
- `payload JSONB NOT NULL DEFAULT '{}'::jsonb`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Purpose:

- durable event history
- frontend debugging
- audit trail
- fallback when SSE disconnects

### 3. Do not overload `items.status`

The existing frontend model uses:

- `active`
- `paused`
- `archived`

That field should remain listing-level lifecycle state.

Do not stuff orchestration-only values into `items.status`.

Workflow-specific status belongs in `agent_runs`.

## Required Backend Auth Changes

The current FastAPI backend does not enforce user auth for workflow endpoints in a frontend-safe way.

To merge cleanly with the frontend branch:

- frontend signs in with Supabase Auth
- frontend sends Supabase bearer token to FastAPI
- FastAPI validates the Supabase JWT
- FastAPI resolves the authenticated `user_id`
- FastAPI verifies item ownership before starting or resuming a run

Public endpoints can remain unauthenticated:

- `GET /health`
- `GET /config`
- `GET /agents`
- `GET /fetch-agents`
- `GET /fetch-agent-capabilities`
- `GET /pipelines`

Authenticated endpoints should include:

- start run
- read run result
- stream run events
- submit sell correction
- submit sell listing decision

## Required Backend Contract Changes

The current generic session endpoints are useful, but they are not ideal as the long-term frontend contract.

### Keep for compatibility

- `POST /sell/start`
- `POST /buy/start`
- `POST /sell/correct`
- `POST /sell/listing-decision`
- `GET /result/{session_id}`
- `GET /stream/{session_id}`

### Add frontend-oriented item/run endpoints

Recommended contract:

- `POST /items/{item_id}/sell/run`
- `POST /items/{item_id}/buy/run`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/stream`
- `POST /runs/{run_id}/sell/correct`
- `POST /runs/{run_id}/sell/listing-decision`
- `GET /items/{item_id}/runs/latest`

Why:

- the frontend is item-centric, not session-centric
- item-scoped endpoints remove guesswork around which session belongs to which listing
- these endpoints can still delegate internally to the existing orchestrator/session machinery

### Add normalized run fields

Whether the frontend reads from FastAPI or from `agent_runs`, the payload needs these normalized fields:

- `phase`
- `next_action`
- `result_source`

Suggested `phase` values:

- `queued`
- `running`
- `awaiting_user_correction`
- `awaiting_listing_review`
- `resuming`
- `completed`
- `failed`

Suggested `next_action.type` values:

- `wait`
- `submit_correction`
- `review_listing`
- `show_result`
- `show_error`

Suggested `result_source` values:

- `browser_use`
- `httpx`
- `fallback`
- `mixed`

## Mapping Current Backend Behavior To Frontend State

### Sell flow

Current backend reality:

- sell runs can pause for `vision_low_confidence`
- sell runs can pause for `listing_review_required`
- review windows can expire
- revisions are limited

Frontend implication:

- sell UI must be a state machine, not just a loading spinner
- the UI cannot infer pause reason from raw nested outputs only

Required normalized mapping:

- low confidence pause -> `phase=awaiting_user_correction`, `next_action.type=submit_correction`
- listing review pause -> `phase=awaiting_listing_review`, `next_action.type=review_listing`
- completed -> `phase=completed`, `next_action.type=show_result`
- failed -> `phase=failed`, `next_action.type=show_error`

### Buy flow

Current backend reality:

- the buy pipeline executes in two stages:
  1. four search agents run in parallel:
     - `depop_search_agent`
     - `ebay_search_agent`
     - `mercari_search_agent`
     - `offerup_search_agent`
  2. then `ranking_agent` and `negotiation_agent` run sequentially after search aggregation
- each search agent returns a `SearchResultsOutput` containing `SearchListing` objects with platform, title, price, url, condition, seller, seller_score, and posted_at
- each search agent tracks its own `execution_mode` (`browser_use`, `httpx`, or `fallback`) and any `browser_use_error`
- the ranking agent consumes all search results and produces a `RankingOutput` with `top_choice`, `ranked_listings`, `candidate_count`, and `median_price`
- the negotiation agent sends offers to sellers and produces a `NegotiationOutput` with a list of `NegotiationAttempt` objects tracking status (`sent`, `failed`, `prepared`), target price, message, and conversation URL
- search agents are retryable via `RETRYABLE_BUY_AGENT_SLUGS` with configurable max retries from `get_buy_agent_max_retries()`
- buy has no pause/resume logic today — unlike sell, there is no `PipelinePaused` raised during buy execution
- the final buy result is a nested dict of per-agent outputs keyed by step name (`depop_search`, `ebay_search`, etc.), not a single summarized object

Frontend implication:

- home/item screens should not need to parse raw per-agent outputs
- the frontend needs a summarized buy result object
- the buy UI should show meaningful progress through search, ranking, and negotiation
- `result_source` must be computed across all search agents since some may use Browser Use, others `httpx`, and others fallback logic
- negotiation status is per-offer, not per-run — the UI must handle partial success (2 of 3 offers sent, 1 failed)
- unlike sell, buy currently has no user interaction points mid-run — the entire pipeline runs to completion or failure without pausing

Required normalized phase mapping:

- all searches queued -> `phase=queued`, `next_action.type=wait`
- searches running -> `phase=running`, `next_action.type=wait`, `progress.step=depop_search|ebay_search|mercari_search|offerup_search`
- ranking running -> `phase=running`, `next_action.type=wait`, `progress.step=ranking`
- negotiation running -> `phase=running`, `next_action.type=wait`, `progress.step=negotiation`
- completed -> `phase=completed`, `next_action.type=show_result`
- failed -> `phase=failed`, `next_action.type=show_error`

Required normalized result mapping:

- `search_summary`: aggregated stats across all four search agents
  - `total_results`: total listings found across all platforms
  - `results_by_platform`: count per platform
  - `platforms_searched`: number of platforms that returned results
  - `platforms_failed`: number of platforms whose agents errored
  - `median_price`: from ranking agent output
- `top_choice`: the single best listing from the ranking agent
  - `platform`, `title`, `price`, `score`, `reason`, `url`, `seller`, `seller_score`
- `offer_summary`: aggregated negotiation results
  - `total_offers`: number of offers attempted
  - `offers_sent`: number successfully sent
  - `offers_failed`: number that failed
  - `offers`: list of individual `NegotiationAttempt` objects for detail views
  - `best_offer`: the offer with the lowest target price that was successfully sent
- `result_source`: overall execution mode
  - `browser_use` if all search agents used Browser Use
  - `httpx` if all search agents used HTTP-only search
  - `fallback` if all search agents used fallback search
  - `mixed` if the run combines multiple search execution modes
  - derived from each agent's `execution_mode` field

Future consideration:

- buy could gain pause/resume in the future (e.g. user confirms before negotiation begins, or user selects which listing to negotiate on instead of the ranking agent choosing automatically)
- if that is added, the sell-side pause architecture is already a useful pattern to follow
- suggested future phases:
  - `awaiting_negotiation_approval` with `next_action.type=approve_negotiation`
  - `awaiting_listing_selection` with `next_action.type=select_listing`

## Screen-By-Screen Ownership

### Auth screens

Use Supabase only.

No FastAPI dependency should be required for:

- sign in
- sign up
- Google OAuth
- Apple OAuth
- session persistence

### Home screen

Use Supabase for:

- items
- completed trades
- market data

Optionally enrich with:

- latest active `agent_runs` for items

Do not make Home depend on active SSE sessions.

### Item detail screen

Use Supabase for:

- item
- platforms
- photos
- market data
- conversations

Supplement with either:

- `GET /items/{item_id}/runs/latest`
- or a direct `agent_runs` query

This is where run state like "awaiting review" should surface.

### Chat screen

Use Supabase only.

Messages and conversation state should remain durable, realtime records.

Do not proxy chat history through FastAPI.

### New listing screen

Use Supabase for:

- creating the item
- uploading photos
- inserting item platforms

Then, if AI is enabled, call FastAPI to start the run against that new `item_id`.

### Settings screens

Use Supabase only.

### Master agent button

Use FastAPI `GET /config` for `resale_copilot_agent_address`.

The button remains a global external link to ASI:One.

## Writeback Rules

The backend must stop treating pipeline output as self-contained session data only.

It should also write durable results back into Supabase.

### Sell run writeback

Expected durable writes:

- update `items` fields if the agent produces better listing metadata
- update `market_data` from pricing/comps where appropriate
- persist current run state into `agent_runs`
- persist workflow events into `agent_run_events`
- when listing review is ready, store the preview artifacts and review payload durably

### Buy run writeback

Expected durable writes:

- update `market_data` snapshots if useful
- create or update conversations/messages when live negotiation actually occurs
- update `items.best_offer` when applicable
- persist run summary into `agent_runs`
- persist workflow events into `agent_run_events`

### Trade completion writeback

When a deal closes:

- insert into `completed_trades`
- archive or otherwise update the source item

## Implementation Phases

## Phase 1: Freeze the merged architecture

Deliverables:

- this reconciliation doc
- update or replace the old assumption in the frontend backend requirements that "no separate backend server is needed"
- add a repo-local contract doc for the merged architecture

Definition of done:

- the team is coding toward one architecture, not two conflicting ones

## Phase 2: Add Supabase infrastructure to the backend

Backend work:

- add Supabase service-role config
- add a backend Supabase client module
- add repository helpers for `items`, `item_photos`, `market_data`, `conversations`, `messages`, `completed_trades`, and `agent_runs`

Suggested files:

- `backend/supabase.py`
- `backend/repositories/`
- `backend/auth.py`

Definition of done:

- FastAPI can read and write the same durable data model the frontend uses

## Phase 3: Add workflow persistence tables

Work:

- create `agent_runs`
- create `agent_run_events`
- add RLS for user reads
- allow backend writes through service role
- add indexes on `user_id`, `item_id`, `session_id`, and recency

Definition of done:

- workflow state survives process restarts
- frontend can query run state without relying on in-memory sessions

## Phase 4: Add authenticated item-scoped workflow endpoints

Work:

- add Supabase-authenticated FastAPI dependencies
- add item ownership verification
- implement `POST /items/{item_id}/sell/run`
- implement `POST /items/{item_id}/buy/run`
- implement `GET /runs/{run_id}`
- implement `GET /runs/{run_id}/stream`
- implement `POST /runs/{run_id}/sell/correct`
- implement `POST /runs/{run_id}/sell/listing-decision`

Definition of done:

- the frontend can start and manage workflows from durable item records

## Phase 5: Persist orchestrator state into Supabase

Work:

- every session creation writes an `agent_run`
- every event write also writes an `agent_run_event`
- every status transition updates `phase`, `next_action`, and `result_payload`
- paused sell runs persist review state durably

Definition of done:

- the backend no longer depends on process memory as the only workflow record

## Phase 6: Normalize payloads for frontend consumption

Work:

- add `phase`
- add `next_action`
- add `result_source`
- add top-level sell review summary
- add top-level buy summary
- add presentation-oriented payloads that avoid forcing the frontend to parse raw agent outputs

Definition of done:

- the frontend can render workflow state without backend-specific parsing logic

## Phase 7: Merge validation

Work:

- add fixture-backed contract tests for frontend-facing run payloads
- add one full sell flow test including:
  - create item
  - start run
  - low-confidence correction
  - listing review
  - confirm submit
- add one full buy flow test including:
  - create item
  - start run
  - read summary result

Definition of done:

- backend and frontend are validating the same durable contract

## Immediate Implementation Queue

This is the recommended execution order once coding starts.

1. Add Supabase backend foundation.
2. Create SQL for `agent_runs` and `agent_run_events`.
3. Add backend auth using Supabase JWTs.
4. Add item-scoped run endpoints.
5. Introduce `phase` and `next_action` into backend session/run payloads.
6. Persist session state and events into Supabase.
7. Add frontend-contract fixtures and tests.
8. Only then wire the real frontend screens to the merged backend contract.

## Risks

1. The frontend branch assumes durable app records today, while the backend run engine is transient.

   If that gap is not closed explicitly, the merge will produce confusing duplicated state.

2. The existing sell pipeline accepts free-form input payloads, while the frontend creates durable item records.

   If we do not add item-scoped run endpoints, the frontend will need awkward adapter logic.

3. The current backend has no real frontend auth boundary.

   Without Supabase token validation, the merged app will have unsafe workflow endpoints.

4. Browser Use live/fallback behavior is backend-friendly but not yet presentation-friendly.

   Without normalized payloads, the frontend will accumulate brittle conditionals.

## Success Condition

This plan is working if:

- the frontend uses Supabase for durable app state
- the backend uses Supabase as shared persistence but remains the workflow engine
- every agent run is attached to a real item and real user
- workflow status survives refreshes and restarts
- the sell review flow can be rendered deterministically from normalized payloads
- the frontend merge becomes an integration exercise instead of an architectural rewrite

## Best Next Step

Start with backend infrastructure, not UI wiring:

1. add the backend Supabase client and auth layer
2. create `agent_runs` and `agent_run_events`
3. add item-scoped run endpoints

That is the minimum foundation required before frontend implementation can proceed cleanly.
