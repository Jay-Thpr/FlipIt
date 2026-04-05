-- Migration 0002: Frontend tables for backend writeback
-- Tables: items, item_platforms, market_data, conversations, messages, completed_trades

create extension if not exists "pgcrypto";

-- items table
create table if not exists public.items (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    name text,
    description text,
    target_price numeric,
    condition text,
    min_price numeric,
    max_price numeric,
    -- frontend columns
    type text not null default 'sell' check (type in ('buy', 'sell')),
    image_color text not null default '#6EE7B7',
    auto_accept_threshold numeric,
    initial_price numeric,
    quantity integer not null default 1,
    negotiation_style text not null default 'moderate' check (negotiation_style in ('aggressive', 'moderate', 'passive')),
    reply_tone text not null default 'professional' check (reply_tone in ('professional', 'casual', 'firm')),
    best_offer numeric,
    last_viewed_at timestamptz not null default now(),
    -- sell review artifacts (added for paused listing refresh)
    draft_url text,
    listing_screenshot_url text,
    listing_preview_payload jsonb,
    -- lifecycle
    status text not null default 'pending',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- item_platforms table (many-to-many between items and platforms)
create table if not exists public.item_platforms (
    id uuid primary key default gen_random_uuid(),
    item_id uuid not null references public.items(id) on delete cascade,
    platform text not null,
    created_at timestamptz not null default now(),
    unique (item_id, platform)
);

-- market_data table
create table if not exists public.market_data (
    id uuid primary key default gen_random_uuid(),
    item_id uuid not null references public.items(id) on delete cascade,
    platform text not null,
    best_buy_price numeric,
    best_sell_price numeric,
    volume integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (item_id, platform)
);

-- conversations table
create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid,
    item_id uuid references public.items(id),
    username text not null default '',
    platform text,
    listing_url text,
    listing_title text,
    seller text,
    last_message text not null default '',
    last_message_at timestamptz not null default now(),
    unread boolean not null default false,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- messages table
create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations(id) on delete cascade,
    sender text not null check (sender in ('agent', 'them')),
    text text not null,
    target_price numeric,
    created_at timestamptz not null default now()
);

-- completed_trades table
create table if not exists public.completed_trades (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    item_id uuid references public.items(id) on delete set null,
    name text not null default '',
    type text not null default 'Bought' check (type in ('Sold', 'Bought')),
    platform text,
    listing_url text,
    listing_title text,
    price numeric,
    initial_price numeric,
    seller text,
    conversation_id uuid references public.conversations(id) on delete set null,
    run_id text,
    completed_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

-- updated_at trigger function (reuse or redefine)
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

-- Apply updated_at trigger to items
drop trigger if exists set_items_updated_at on public.items;
create trigger set_items_updated_at
before update on public.items
for each row execute function public.set_updated_at();

-- Apply updated_at trigger to market_data
drop trigger if exists set_market_data_updated_at on public.market_data;
create trigger set_market_data_updated_at
before update on public.market_data
for each row execute function public.set_updated_at();

-- Apply updated_at trigger to conversations
drop trigger if exists set_conversations_updated_at on public.conversations;
create trigger set_conversations_updated_at
before update on public.conversations
for each row execute function public.set_updated_at();

-- Indexes
create index if not exists idx_items_user_id on public.items(user_id);
create index if not exists idx_item_platforms_item_id on public.item_platforms(item_id);
create index if not exists idx_market_data_item_id on public.market_data(item_id);
create index if not exists idx_conversations_user_listing on public.conversations(user_id, listing_url);
create index if not exists idx_conversations_item_id on public.conversations(item_id);
create index if not exists idx_messages_conversation_id on public.messages(conversation_id);
create index if not exists idx_completed_trades_user_id on public.completed_trades(user_id);
