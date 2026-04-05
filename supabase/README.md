# Supabase Persistence Plan

Use Supabase here as durable storage for the current FastAPI session contract. The live SSE stream still comes from FastAPI memory; Supabase is for polling, restart recovery, and event history.

## What Matches The Frontend Now

- `POST /sell/start` and `POST /buy/start` create a `SessionState`.
- `GET /result/{session_id}` returns that same session object:
  - `session_id`
  - `pipeline`
  - `status`
  - `request`
  - `result`
  - `error`
  - `events`
- The Expo `new-listing` flow polls `GET /result/{session_id}` and reads:
  - `status`
  - `result.outputs`
  - `result.pending`
  - `error`

That means the durable schema should track the current backend/frontend session model, not the older `mode + input_payload + final_result` stub.

## Tables

- `public.pipeline_sessions`
  - one row per pipeline run
  - stores the durable session state fields that back `GET /result/{session_id}`
  - includes `request_payload`, `result_payload`, `status`, `error`, and timestamps
- `public.pipeline_session_events`
  - append-only event history for SSE replay, polling, and audit/debugging
  - stores `event_type`, `pipeline`, `step`, `data`, and `timestamp`

## Scope Boundary

This persistence layer now covers the pipeline session contract used by the new frontend flow.

It does not yet persist the `/items` catalog, item photos, or conversation history returned by the in-memory item store. Those APIs already match the frontend model, but they are still mock/in-memory data and should move to separate Supabase tables later instead of being forced into the pipeline session schema now.

## Apply The Schema

If you use the Supabase CLI in this repo:

```bash
supabase db push
```

Or run the SQL directly:

- [20260404145000_init_session_persistence.sql](/Users/derek/.superset/worktrees/Diamond Hacks/helpful-sagittarius/supabase/migrations/20260404145000_init_session_persistence.sql)

## Backend Integration

The current backend persists directly from `SessionManager`:

- session creation writes a row to `pipeline_sessions`
- status/result/error changes upsert the same row
- each `SessionEvent` appends to `pipeline_session_events`
- cache misses can be hydrated back from Supabase for `GET /result/{session_id}`

## Security Note

- Use `SUPABASE_SERVICE_ROLE_KEY` from FastAPI only.
- Do not expose write access from the mobile app.
- RLS is enabled so future client reads can be added intentionally with explicit read policies.
