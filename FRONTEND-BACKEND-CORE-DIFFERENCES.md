# Frontend-Backend Core Differences

Date: 2026-04-05

## Purpose

This file is a handoff summary for teammates.

It captures the core differences between:

- the `origin/frontend` requirements docs
- the current backend implementation in this branch

It also records the recommended path forward so someone else can reason from the same baseline instead of rediscovering the mismatch from scratch.

## Source Documents Reviewed

Frontend branch assumptions:

- `origin/frontend:UI_REQUIREMENTS.md`
- `origin/frontend:BACKEND_REQUIREMENTS.md`
- `origin/frontend:PRD.md`

Current backend reality:

- `backend/main.py`
- `backend/orchestrator.py`
- `backend/schemas.py`
- `backend/session.py`
- `API_CONTRACT.md`
- `BACKEND-FRONTEND-INTEGRATION-PLAN.md`

## Executive Summary

The frontend branch and the current backend are not implementing the same architecture.

The frontend branch assumes:

- Supabase is the app backend
- frontend talks directly to Supabase for auth, CRUD, storage, and realtime
- AI agents are a separate service that read and write the same database
- a tiny `/config` endpoint is enough for backend integration

The current backend actually is:

- a FastAPI orchestration service
- centered on async buy/sell workflows
- powered by session state, SSE, and pipeline outputs
- currently using in-memory session storage
- not yet connected to Supabase for app persistence

## Main Recommendation

Do not choose between Supabase and FastAPI.

Use both:

- Supabase should be the durable system of record for the app.
- FastAPI should remain the agent workflow engine.
- Frontend should use Supabase for app data and FastAPI for long-running agent actions.

This is the cleanest merge path.

## Core Differences And Recommendations

## 1. App architecture

Frontend branch assumption:

- Supabase is the primary backend.
- No separate backend server is needed for app CRUD.

Current backend reality:

- FastAPI is the primary implemented backend.
- It already contains the workflow engine, SSE stream, sell review logic, and agent orchestration contract.

Why this matters:

- These are fundamentally different integration models.
- If the team does not resolve this first, frontend and backend work will drift further apart.

Recommendation:

- Adopt a hybrid architecture.
- Supabase handles durable app data.
- FastAPI handles workflow execution and workflow state transitions.

## 2. Data model shape

Frontend branch assumption:

- The app is built around durable entities like:
  - `items`
  - `item_photos`
  - `market_data`
  - `conversations`
  - `messages`
  - `completed_trades`

Current backend reality:

- The backend is built around transient pipeline sessions:
  - `POST /sell/start`
  - `POST /buy/start`
  - `GET /stream/{session_id}`
  - `GET /result/{session_id}`

Why this matters:

- A session is not the same thing as an item.
- The frontend cannot use raw session outputs as its whole app data model.

Recommendation:

- Keep sessions as the execution model.
- Add durable workflow tables in Supabase:
  - `agent_runs`
  - `agent_run_events`
- Link each run to a real `item` and `user`.

## 3. Persistence

Frontend branch assumption:

- App state is durable in Supabase.

Current backend reality:

- Session state is in memory in `backend/session.py`.

Why this matters:

- Refreshing or restarting the backend loses run state.
- That is incompatible with a real frontend integration.

Recommendation:

- Move workflow persistence into Supabase-backed tables.
- Keep in-memory session state only as a runtime cache if needed.

## 4. Auth model

Frontend branch assumption:

- Supabase Auth handles:
  - email/password
  - Google OAuth
  - Apple OAuth

Current backend reality:

- FastAPI has no real frontend auth layer for user-owned workflows.
- The request schema has optional `user_id`, but that is not a frontend-safe auth boundary.

Why this matters:

- The merged app needs secure ownership checks for starting and managing workflows.

Recommendation:

- Frontend authenticates with Supabase.
- Frontend sends Supabase access token to FastAPI.
- FastAPI validates Supabase JWT and resolves the authenticated user.
- FastAPI verifies that the item belongs to that user before running workflows.

## 5. Realtime model

Frontend branch assumption:

- Supabase Realtime is used for messages, conversations, and status updates.

Current backend reality:

- Workflow progress uses Server-Sent Events from FastAPI.

Why this matters:

- These are different realtime channels solving different problems.

Recommendation:

- Use Supabase Realtime for durable entity changes:
  - conversations
  - messages
  - item updates
- Use FastAPI SSE only for active workflow runs:
  - start
  - progress
  - pause
  - completion

## 6. Listing creation flow

Frontend branch assumption:

- User creates an `item` first in Supabase.
- Photos and platforms are attached to that item.

Current backend reality:

- Sell flow currently starts from free-form input like:
  - `image_urls`
  - `notes`

Why this matters:

- The frontend is item-centric.
- The backend is currently payload-centric.

Recommendation:

- Add item-scoped workflow endpoints, not just generic session endpoints.
- Suggested endpoints:
  - `POST /items/{item_id}/sell/run`
  - `POST /items/{item_id}/buy/run`
- FastAPI should load item data from Supabase and use that as workflow input.

## 7. Workflow status model

Frontend branch assumption:

- Items have simple lifecycle state:
  - `active`
  - `paused`
  - `archived`

Current backend reality:

- Workflows have richer run state:
  - `queued`
  - `running`
  - `paused`
  - `completed`
  - `failed`
- Sell flows also pause for specific reasons:
  - low-confidence vision correction
  - listing review

Why this matters:

- `items.status` and workflow status are not the same concept.

Recommendation:

- Keep `items.status` as listing lifecycle state.
- Put workflow status in `agent_runs`.
- Add normalized workflow fields:
  - `phase`
  - `next_action`

## 8. Sell flow pause/resume behavior

Frontend branch assumption:

- The frontend docs describe CRUD screens well, but they do not fully model the backend’s paused sell workflow.

Current backend reality:

- The sell pipeline can pause for:
  - `vision_low_confidence`
  - `listing_review_required`
- It supports:
  - correction submission
  - review confirmation
  - revision loop
  - abort
  - timeout expiration

Why this matters:

- This is the most complex integration point in the app.
- If the frontend is built without a stable contract for this, the merge will be painful.

Recommendation:

- Expose normalized run state:
  - `phase=awaiting_user_correction`
  - `phase=awaiting_listing_review`
- Expose normalized next action:
  - `submit_correction`
  - `review_listing`
- Persist paused review state durably.

## 8b. Buy flow pipeline complexity

Frontend branch assumption:

- The frontend docs model a buy action as: user wants an item, app finds deals, user sees results.
- The expected output is a simple list of deals or a best offer.

Current backend reality:

- The buy pipeline executes in two stages:
  1. four marketplace search agents run in parallel:
     - `depop_search_agent`
     - `ebay_search_agent`
     - `mercari_search_agent`
     - `offerup_search_agent`
  2. then `ranking_agent` and `negotiation_agent` run sequentially after search aggregation
- Each search agent independently tracks its own `execution_mode` (`browser_use`, `httpx`, or `fallback`) and any `browser_use_error`.
- Search agents are retryable via `RETRYABLE_BUY_AGENT_SLUGS` with configurable max retries.
- The ranking agent produces structured output: `top_choice`, `ranked_listings`, `candidate_count`, and `median_price`.
- The negotiation agent produces a list of `NegotiationAttempt` objects, each with its own `status` (`sent`, `failed`, `prepared`), `target_price`, `message`, `conversation_url`, and `execution_mode`.
- Negotiation is per-offer, not per-run — partial success is possible (e.g. 2 of 3 offers sent, 1 failed).
- The final buy result is a nested dict of per-agent outputs keyed by step name, not a single flat object.
- Unlike sell, buy currently has no pause/resume logic — no `PipelinePaused` is raised, and the entire pipeline runs to completion or failure without user interaction.

Why this matters:

- This is more complex than the frontend docs suggest.
- The frontend cannot render a buy result by reading a single flat field — it must either parse nested per-agent outputs or consume a normalized summary.
- The buy pipeline needs meaningful progress states, not just a single loading state.
- The overall `result_source` cannot be derived from a simple live/fallback binary because search agents can independently use `browser_use`, `httpx`, or `fallback`.
- Negotiation results are not binary success/failure — the UI must handle mixed outcomes per offer.
- The lack of user interaction during buy is a product decision, not a technical limitation — the backend architecture already has room for future pause points if desired.

Recommendation:

- Normalize the buy result into frontend-facing summary fields:
  - `search_summary` with total results, results per platform, platforms searched, platforms failed, and median price.
  - `top_choice` with platform, title, price, score, reason, url, seller, and seller_score.
  - `offer_summary` with total offers, offers sent, offers failed, and best offer details.
  - `result_source` as one of:
    - `browser_use` if all search agents used Browser Use
    - `httpx` if all search agents used HTTP-only search
    - `fallback` if all search agents used fallback logic
    - `mixed` if the run combines multiple search execution modes
- Expose step-level progress during the run so the UI can show which stage is executing (e.g. "Searching eBay..." then "Ranking results..." then "Sending offers...").
- Consider optional future pause points:
  - `phase=awaiting_negotiation_approval` before the negotiation agent runs
  - `phase=awaiting_listing_selection` to let the user choose from ranked results

## 9. Frontend data ownership

Frontend branch assumption:

- Frontend reads app state directly from Supabase.

Current backend reality:

- FastAPI returns raw workflow outputs, not durable app-ready screen objects.

Why this matters:

- If the frontend starts reading too much from raw workflow payloads, UI code will become tightly coupled to agent internals.

Recommendation:

- Frontend should read durable screen data from Supabase.
- FastAPI should write relevant workflow outcomes back into Supabase.
- FastAPI responses should focus on run state and run summaries, not replace the app database.

## 10. Conversations and messages

Frontend branch assumption:

- `conversations` and `messages` are durable tables with realtime updates.

Current backend reality:

- The backend has workflow outputs related to negotiation, but not the full persistent chat model described in the frontend docs.
- Specifically, the buy pipeline's `negotiation_agent` produces `NegotiationAttempt` objects that contain `message` (the text sent to a seller), `conversation_url` (the external platform conversation link), and `status` (`sent`, `failed`, `prepared`).
- These negotiation messages are currently embedded in the session result payload and are not written into any durable `conversations` or `messages` table.
- A single buy run can produce multiple negotiation attempts to different sellers on different platforms, each with its own conversation thread.

Why this matters:

- The frontend chat screen expects durable history, not temporary run output.
- If a user refreshes after a buy run, negotiation messages would be lost unless they are persisted.
- The negotiation agent's `conversation_url` links to external platform conversations, so the frontend needs a durable way to surface those links.

Recommendation:

- Keep chat history in Supabase.
- When the negotiation agent sends offers, FastAPI should write each `NegotiationAttempt` into `conversations` and `messages` as part of the buy run writeback.
- Each negotiation attempt should create a `conversation` linked to the item and platform, with the initial offer as the first `message`.
- Store the external `conversation_url` on the `conversation` record so the frontend can link out to the platform.
- Do not make the chat screen depend on workflow session payloads.

## 11. Completed trades and P&L

Frontend branch assumption:

- Completed trades are a durable queryable table.
- P&L is calculated client-side from `completed_trades`.

Current backend reality:

- The orchestrator can finish workflows, but durable trade persistence is not currently the primary app model in this branch.

Why this matters:

- Home screen and trade history depend on durable trade records.

Recommendation:

- Preserve the frontend branch approach here.
- When a deal closes, agents should write durable records into `completed_trades`.

## 12. Error and result shape

Frontend branch assumption:

- Supabase queries return relatively simple entity data.

Current backend reality:

- FastAPI returns workflow-centric payloads with:
  - per-agent outputs
  - fallback metadata
  - event streams
  - partial results

Why this matters:

- That shape is valid for orchestration but too raw for direct UI consumption.

Recommendation:

- Add normalized frontend-facing fields to workflow results:
  - `phase`
  - `next_action`
  - `result_source` derived from `browser_use`, `httpx`, and `fallback` execution modes
  - `sell_review`
  - `buy_summary`
- Keep raw per-agent outputs available for debugging, but do not force the frontend to depend on them.

## 13. Deployment assumption

Frontend branch assumption:

- The app can mostly run against Supabase plus a tiny config surface.

Current backend reality:

- The backend needs to be a real running service for:
  - pipeline start
  - SSE streaming
  - pause/resume logic
  - Browser Use work
  - Fetch.ai helper endpoints

Why this matters:

- The merged app needs both services running.

Recommendation:

- Treat the final system as two services:
  - Supabase
  - FastAPI orchestration service

## 14. Master agent button

Frontend branch assumption:

- A persistent FAB opens ASI:One with the master agent address.

Current backend reality:

- This is already compatible.
- `GET /config` exists and returns `resale_copilot_agent_address`.

Why this matters:

- This is one of the few parts already aligned.

Recommendation:

- Keep this exactly as planned.
- Frontend reads `/config` and hides the FAB if the address is empty.

## Recommended Merged Architecture

## Supabase should own

- auth
- profiles
- settings
- platform connections
- items
- photos
- market data
- conversations
- messages
- completed trades
- workflow persistence tables

## FastAPI should own

- workflow execution
- workflow status transitions
- SSE
- Browser Use integration
- sell review logic
- writeback into Supabase
- public metadata endpoints like `/config`

## Frontend should call

Supabase for:

- app CRUD
- auth
- storage
- realtime

FastAPI for:

- starting agent runs
- watching active run progress
- resuming paused sell flows
- reading normalized run state
- reading master-agent config

## Concrete Recommendations

1. Do not build duplicate CRUD endpoints in FastAPI.

2. Add Supabase integration to the backend so FastAPI and the frontend share the same source of truth.

3. Add workflow persistence tables:
   - `agent_runs`
   - `agent_run_events`

4. Add Supabase-authenticated item-scoped workflow endpoints.

5. Add normalized workflow fields:
   - `phase`
   - `next_action`
   - `result_source`

6. Persist paused sell review state durably instead of keeping it only in memory.

7. Treat Supabase Realtime and FastAPI SSE as complementary, not competing, channels.

8. Write agent outcomes back into durable frontend-visible tables instead of leaving them only inside session results.

9. Keep the ASI:One master-agent button exactly as designed. It is already the least problematic part of the merge.

## Recommended Execution Order

1. Freeze the architecture decision: hybrid Supabase + FastAPI.

2. Add backend Supabase client and auth validation.

3. Add workflow persistence tables.

4. Add item-scoped run endpoints.

5. Normalize workflow result payloads.

6. Persist workflow state and events into Supabase.

7. Only then wire the real frontend screens against the merged contract.

## Bottom Line

The frontend branch is not wrong.

The backend branch is not wrong.

They are solving different layers of the system.

The fix is not to pick one and discard the other. The fix is to make Supabase the durable app layer and FastAPI the workflow engine, then connect them with authenticated item-scoped workflow endpoints and durable run persistence.
