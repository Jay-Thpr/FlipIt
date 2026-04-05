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
  pipeline text not null check (pipeline in ('sell', 'buy')),
  status text not null default 'queued' check (status in ('queued', 'running', 'awaiting_input', 'completed', 'failed')),
  request_payload jsonb not null default '{}'::jsonb,
  result_payload jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz
);

create table if not exists public.pipeline_session_events (
  id bigint generated always as identity primary key,
  session_id uuid not null references public.pipeline_sessions(session_id) on delete cascade,
  event_type text not null,
  pipeline text check (pipeline in ('sell', 'buy')),
  step text,
  data jsonb not null default '{}'::jsonb,
  timestamp timestamptz not null default timezone('utc', now())
);

create index if not exists pipeline_sessions_pipeline_idx
  on public.pipeline_sessions (pipeline);

create index if not exists pipeline_sessions_status_idx
  on public.pipeline_sessions (status);

create index if not exists pipeline_sessions_created_at_idx
  on public.pipeline_sessions (created_at desc);

create index if not exists pipeline_session_events_session_id_timestamp_idx
  on public.pipeline_session_events (session_id, timestamp asc);

create index if not exists pipeline_session_events_event_type_idx
  on public.pipeline_session_events (event_type);

drop trigger if exists set_pipeline_sessions_updated_at on public.pipeline_sessions;

create trigger set_pipeline_sessions_updated_at
before update on public.pipeline_sessions
for each row
execute function public.set_updated_at();

alter table public.pipeline_sessions enable row level security;
alter table public.pipeline_session_events enable row level security;

comment on table public.pipeline_sessions is
  'Durable pipeline session state returned by GET /result/{session_id}, including request, status, error, and structured outputs.';

comment on table public.pipeline_session_events is
  'Append-only SSE event history for each pipeline session, including pipeline, step, and event data.';
