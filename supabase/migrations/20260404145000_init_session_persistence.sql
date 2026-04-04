create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.pipeline_sessions (
  session_id uuid primary key,
  mode text not null check (mode in ('sell', 'buy')),
  status text not null default 'running' check (status in ('running', 'completed', 'failed', 'timed_out', 'cancelled')),
  input_payload jsonb not null default '{}'::jsonb,
  error_summary text,
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.pipeline_session_events (
  id bigint generated always as identity primary key,
  session_id uuid not null references public.pipeline_sessions(session_id) on delete cascade,
  event_type text not null,
  agent_name text,
  summary text,
  payload jsonb not null default '{}'::jsonb,
  dedupe_key text,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.pipeline_session_results (
  session_id uuid primary key references public.pipeline_sessions(session_id) on delete cascade,
  result_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists pipeline_sessions_mode_idx
  on public.pipeline_sessions (mode);

create index if not exists pipeline_sessions_status_idx
  on public.pipeline_sessions (status);

create index if not exists pipeline_sessions_started_at_idx
  on public.pipeline_sessions (started_at desc);

create index if not exists pipeline_session_events_session_id_created_at_idx
  on public.pipeline_session_events (session_id, created_at asc);

create index if not exists pipeline_session_events_event_type_idx
  on public.pipeline_session_events (event_type);

create unique index if not exists pipeline_session_events_session_id_dedupe_key_idx
  on public.pipeline_session_events (session_id, dedupe_key)
  where dedupe_key is not null;

drop trigger if exists set_pipeline_sessions_updated_at on public.pipeline_sessions;

create trigger set_pipeline_sessions_updated_at
before update on public.pipeline_sessions
for each row
execute function public.set_updated_at();

drop trigger if exists set_pipeline_session_results_updated_at on public.pipeline_session_results;

create trigger set_pipeline_session_results_updated_at
before update on public.pipeline_session_results
for each row
execute function public.set_updated_at();

alter table public.pipeline_sessions enable row level security;
alter table public.pipeline_session_events enable row level security;
alter table public.pipeline_session_results enable row level security;

comment on table public.pipeline_sessions is
  'One row per SELL or BUY pipeline session, keyed by application-generated session_id.';

comment on table public.pipeline_session_events is
  'Append-only event log for SSE and backend audit history.';

comment on table public.pipeline_session_results is
  'Durable final result payload for GET /result/{session_id}.';
