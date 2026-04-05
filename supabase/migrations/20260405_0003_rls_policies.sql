-- Migration 0003: Row-Level Security policies
-- Service role bypasses RLS; authenticated users read only their own rows.
-- Backend writes via service role key, so no INSERT/UPDATE policies needed for
-- workflow tables (agent_runs, agent_run_events, market_data, messages, completed_trades).

-- Enable RLS on all tables
alter table public.agent_runs enable row level security;
alter table public.agent_run_events enable row level security;
alter table public.items enable row level security;
alter table public.market_data enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.completed_trades enable row level security;

-- agent_runs: users can read their own runs
drop policy if exists "users_select_own_agent_runs" on public.agent_runs;
create policy "users_select_own_agent_runs"
on public.agent_runs for select
to authenticated
using (auth.uid() = user_id);

-- agent_run_events: users can read events for runs they own
drop policy if exists "users_select_own_agent_run_events" on public.agent_run_events;
create policy "users_select_own_agent_run_events"
on public.agent_run_events for select
to authenticated
using (
    exists (
        select 1 from public.agent_runs r
        where r.id = agent_run_events.run_id
          and r.user_id = auth.uid()
    )
);

-- items: users can read and write their own items
drop policy if exists "users_select_own_items" on public.items;
create policy "users_select_own_items"
on public.items for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "users_insert_own_items" on public.items;
create policy "users_insert_own_items"
on public.items for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "users_update_own_items" on public.items;
create policy "users_update_own_items"
on public.items for update
to authenticated
using (auth.uid() = user_id);

-- market_data: users can read market data for their own items
drop policy if exists "users_select_own_market_data" on public.market_data;
create policy "users_select_own_market_data"
on public.market_data for select
to authenticated
using (
    exists (
        select 1 from public.items i
        where i.id = market_data.item_id
          and i.user_id = auth.uid()
    )
);

-- conversations: users can read their own conversations
drop policy if exists "users_select_own_conversations" on public.conversations;
create policy "users_select_own_conversations"
on public.conversations for select
to authenticated
using (auth.uid() = user_id);

-- messages: users can read messages for their own conversations
drop policy if exists "users_select_own_messages" on public.messages;
create policy "users_select_own_messages"
on public.messages for select
to authenticated
using (
    exists (
        select 1 from public.conversations c
        where c.id = messages.conversation_id
          and c.user_id = auth.uid()
    )
);

-- completed_trades: users can read their own trades
drop policy if exists "users_select_own_completed_trades" on public.completed_trades;
create policy "users_select_own_completed_trades"
on public.completed_trades for select
to authenticated
using (auth.uid() = user_id);
