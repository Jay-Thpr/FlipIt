# Supabase Persistence Plan

Use Supabase here as a managed Postgres database, not as a replacement for the existing FastAPI + SSE runtime.

## Recommended Architecture

- Mobile app talks to FastAPI.
- FastAPI orchestrates agents and streams live SSE events.
- FastAPI writes durable state to Supabase.
- Supabase stores session metadata, event history, and final results.

This keeps the current contract in the planning docs intact:

- `GET /stream/{session_id}` stays the live channel.
- `GET /result/{session_id}` becomes durable instead of in-memory only.
- Restarting FastAPI no longer destroys session history and final outputs.

## Tables

- `public.pipeline_sessions`
  - one row per SELL or BUY invocation
  - keyed by `session_id`
- `public.pipeline_session_events`
  - append-only log of agent and pipeline events
- `public.pipeline_session_results`
  - final result payload per session

## Why This Scope

The existing repo docs do not define user accounts, marketplace inventory ownership, or long-term product analytics yet. The schema only covers the persistence requirements already present in the SSE/backend plan.

## Apply The Schema

If you use the Supabase CLI in the eventual app repo:

```bash
supabase db push
```

Or run the SQL in the Supabase SQL editor:

- [20260404145000_init_session_persistence.sql](migrations/20260404145000_init_session_persistence.sql)

## Backend Integration Sketch

At pipeline start:

```python
await create_session_row(session_id=session_id, mode="sell", input_payload=payload)
```

On each internal event:

```python
await insert_event(session_id=session_id, event_type="agent_started", payload=data)
```

When storing the final result:

```python
await upsert_result(session_id=session_id, result_payload=result)
await mark_session_complete(session_id=session_id)
```

On failure:

```python
await mark_session_failed(session_id=session_id, error_summary="agent timeout")
```

## Security Note

- Use the `service_role` key from FastAPI only.
- Do not expose write access from the mobile app.
- If you later add direct client reads, add RLS policies deliberately instead of opening the tables broadly.
