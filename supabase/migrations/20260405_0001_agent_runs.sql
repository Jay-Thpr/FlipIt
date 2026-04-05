create extension if not exists "pgcrypto";

create table if not exists public.agent_runs (
    id uuid primary key default gen_random_uuid(),
    session_id text not null unique,
    user_id uuid not null,
    item_id uuid,
    pipeline text not null check (pipeline in ('sell', 'buy')),
    status text not null,
    phase text not null,
    next_action_type text,
    next_action_payload jsonb not null default '{}'::jsonb,
    request_payload jsonb not null default '{}'::jsonb,
    result_payload jsonb not null default '{}'::jsonb,
    error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    completed_at timestamptz
);

create table if not exists public.agent_run_events (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.agent_runs(id) on delete cascade,
    session_id text not null,
    event_type text not null,
    step text,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_agent_runs_user_created_at
    on public.agent_runs (user_id, created_at desc);

create index if not exists idx_agent_runs_item_created_at
    on public.agent_runs (item_id, created_at desc);

create index if not exists idx_agent_runs_session_id
    on public.agent_runs (session_id);

create index if not exists idx_agent_runs_status_phase
    on public.agent_runs (status, phase);

create index if not exists idx_agent_run_events_run_created_at
    on public.agent_run_events (run_id, created_at desc);

create index if not exists idx_agent_run_events_session_id
    on public.agent_run_events (session_id);

create index if not exists idx_agent_run_events_event_type
    on public.agent_run_events (event_type);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_agent_runs_updated_at on public.agent_runs;

create trigger set_agent_runs_updated_at
before update on public.agent_runs
for each row
execute function public.set_updated_at();
