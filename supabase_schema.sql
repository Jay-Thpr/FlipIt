-- ============================================================
-- AgentMarket — Complete Supabase Schema
-- Run this entire file in Supabase Dashboard > SQL Editor
-- ============================================================

-- ============================================================
-- 1. PROFILES (extends auth.users)
-- ============================================================
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL DEFAULT '',
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-create profile on signup (handles OAuth display names too)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name, email)
  VALUES (
    NEW.id,
    COALESCE(
      NEW.raw_user_meta_data->>'display_name',
      NEW.raw_user_meta_data->>'full_name',
      NEW.raw_user_meta_data->>'name',
      ''
    ),
    COALESCE(NEW.email, '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- 2. USER SETTINGS
-- ============================================================
CREATE TABLE public.user_settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  theme_preference TEXT NOT NULL DEFAULT 'system' CHECK (theme_preference IN ('light', 'dark', 'system')),
  auto_reply BOOLEAN NOT NULL DEFAULT true,
  response_delay TEXT NOT NULL DEFAULT '5 min' CHECK (response_delay IN ('1 min', '5 min', '15 min', '30 min', '1 hr')),
  negotiation_style TEXT NOT NULL DEFAULT 'moderate' CHECK (negotiation_style IN ('aggressive', 'moderate', 'passive')),
  reply_tone TEXT NOT NULL DEFAULT 'professional' CHECK (reply_tone IN ('professional', 'casual', 'firm')),
  notif_new_message BOOLEAN NOT NULL DEFAULT true,
  notif_price_drop BOOLEAN NOT NULL DEFAULT true,
  notif_deal_closed BOOLEAN NOT NULL DEFAULT true,
  notif_listing_expired BOOLEAN NOT NULL DEFAULT false,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-create settings on signup
CREATE OR REPLACE FUNCTION public.handle_new_user_settings()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_settings (user_id) VALUES (NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created_settings
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_settings();

-- ============================================================
-- 3. PLATFORM CONNECTIONS
-- ============================================================
CREATE TABLE public.platform_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  username TEXT,
  connected BOOLEAN NOT NULL DEFAULT false,
  connected_at TIMESTAMPTZ,
  UNIQUE(user_id, platform)
);

-- ============================================================
-- 4. ITEMS
-- ============================================================
CREATE TABLE public.items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('buy', 'sell')),
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  condition TEXT NOT NULL DEFAULT 'Good',
  image_color TEXT NOT NULL DEFAULT '#6EE7B7',
  target_price NUMERIC(10,2),
  min_price NUMERIC(10,2),
  max_price NUMERIC(10,2),
  auto_accept_threshold NUMERIC(10,2),
  initial_price NUMERIC(10,2),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived', 'draft')),
  quantity INTEGER NOT NULL DEFAULT 1,
  negotiation_style TEXT NOT NULL DEFAULT 'moderate' CHECK (negotiation_style IN ('aggressive', 'moderate', 'passive')),
  reply_tone TEXT NOT NULL DEFAULT 'professional' CHECK (reply_tone IN ('professional', 'casual', 'firm')),
  response_delay TEXT NOT NULL DEFAULT '5 min' CHECK (response_delay IN ('1 min', '5 min', '15 min', '30 min', '1 hr')),
  best_offer NUMERIC(10,2),
  -- Backend sell review artifacts (from jay's pipeline)
  draft_url TEXT,
  listing_screenshot_url TEXT,
  listing_preview_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_viewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_items_user_id ON public.items(user_id);
CREATE INDEX idx_items_status ON public.items(status);
CREATE INDEX idx_items_type ON public.items(type);

-- ============================================================
-- 5. UPDATED_AT AUTO-TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_items_updated_at
  BEFORE UPDATE ON public.items
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER set_user_settings_updated_at
  BEFORE UPDATE ON public.user_settings
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- 6. ITEM PLATFORMS (many-to-many)
-- ============================================================
CREATE TABLE public.item_platforms (
  item_id UUID NOT NULL REFERENCES public.items(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  PRIMARY KEY (item_id, platform)
);

-- ============================================================
-- 7. ITEM PHOTOS
-- ============================================================
CREATE TABLE public.item_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID NOT NULL REFERENCES public.items(id) ON DELETE CASCADE,
  photo_url TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_item_photos_item_id ON public.item_photos(item_id);

-- ============================================================
-- 8. MARKET DATA
-- ============================================================
CREATE TABLE public.market_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID NOT NULL REFERENCES public.items(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  best_buy_price NUMERIC(10,2) NOT NULL,
  best_sell_price NUMERIC(10,2) NOT NULL,
  volume INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(item_id, platform)
);

CREATE TRIGGER set_market_data_updated_at
  BEFORE UPDATE ON public.market_data
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- 9. CONVERSATIONS
-- ============================================================
CREATE TABLE public.conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID REFERENCES public.items(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT NOT NULL DEFAULT '',
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  last_message TEXT NOT NULL DEFAULT '',
  last_message_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  unread BOOLEAN NOT NULL DEFAULT false,
  -- Backend writeback columns (from jay's pipeline)
  listing_url TEXT,
  listing_title TEXT,
  seller TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversations_item_id ON public.conversations(item_id);

-- ============================================================
-- 10. MESSAGES
-- ============================================================
CREATE TABLE public.messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
  sender TEXT NOT NULL CHECK (sender IN ('agent', 'them')),
  text TEXT NOT NULL,
  target_price NUMERIC(10,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation_id ON public.messages(conversation_id);

-- ============================================================
-- 11. COMPLETED TRADES
-- ============================================================
CREATE TABLE public.completed_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  item_id UUID REFERENCES public.items(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('Sold', 'Bought')),
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  price NUMERIC(10,2) NOT NULL,
  initial_price NUMERIC(10,2),
  -- Backend writeback columns (from jay's pipeline)
  listing_url TEXT,
  seller TEXT,
  conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
  run_id TEXT,
  listed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_completed_trades_user_id ON public.completed_trades(user_id);
CREATE INDEX idx_completed_trades_completed_at ON public.completed_trades(completed_at);

-- ============================================================
-- 12. AGENT RUNS (from jay's pipeline)
-- ============================================================
CREATE TABLE public.agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL UNIQUE,
  user_id UUID NOT NULL,
  item_id UUID,
  pipeline TEXT NOT NULL CHECK (pipeline IN ('sell', 'buy')),
  status TEXT NOT NULL,
  phase TEXT NOT NULL,
  next_action_type TEXT,
  next_action_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  request_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  result_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_agent_runs_user_created_at ON public.agent_runs(user_id, created_at DESC);
CREATE INDEX idx_agent_runs_item_created_at ON public.agent_runs(item_id, created_at DESC);
CREATE INDEX idx_agent_runs_session_id ON public.agent_runs(session_id);
CREATE INDEX idx_agent_runs_status_phase ON public.agent_runs(status, phase);

CREATE TRIGGER set_agent_runs_updated_at
  BEFORE UPDATE ON public.agent_runs
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- 13. AGENT RUN EVENTS (from jay's pipeline)
-- ============================================================
CREATE TABLE public.agent_run_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES public.agent_runs(id) ON DELETE CASCADE,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  step TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_run_events_run_created_at ON public.agent_run_events(run_id, created_at DESC);
CREATE INDEX idx_agent_run_events_session_id ON public.agent_run_events(session_id);
CREATE INDEX idx_agent_run_events_event_type ON public.agent_run_events(event_type);

-- Add updated_at trigger to conversations
CREATE TRIGGER set_conversations_updated_at
  BEFORE UPDATE ON public.conversations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- 14. ROW-LEVEL SECURITY
-- ============================================================

-- profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- user_settings
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own settings" ON public.user_settings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own settings" ON public.user_settings FOR UPDATE USING (auth.uid() = user_id);

-- platform_connections
ALTER TABLE public.platform_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own platforms" ON public.platform_connections FOR ALL USING (auth.uid() = user_id);

-- items
ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own items" ON public.items FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own items" ON public.items FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own items" ON public.items FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own items" ON public.items FOR DELETE USING (auth.uid() = user_id);

-- item_platforms
ALTER TABLE public.item_platforms ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage platforms for own items" ON public.item_platforms FOR ALL
  USING (EXISTS (SELECT 1 FROM public.items WHERE items.id = item_platforms.item_id AND items.user_id = auth.uid()));

-- item_photos
ALTER TABLE public.item_photos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage photos for own items" ON public.item_photos FOR ALL
  USING (EXISTS (SELECT 1 FROM public.items WHERE items.id = item_photos.item_id AND items.user_id = auth.uid()));

-- market_data (agents write via service_role key which bypasses RLS)
ALTER TABLE public.market_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read market data for own items" ON public.market_data FOR SELECT
  USING (EXISTS (SELECT 1 FROM public.items WHERE items.id = market_data.item_id AND items.user_id = auth.uid()));

-- conversations (accessible via item ownership OR direct user_id)
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access own conversations" ON public.conversations FOR ALL
  USING (
    conversations.user_id = auth.uid()
    OR EXISTS (SELECT 1 FROM public.items WHERE items.id = conversations.item_id AND items.user_id = auth.uid())
  );

-- messages (agents write via service_role key which bypasses RLS)
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read messages in own conversations" ON public.messages FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM public.conversations c
    WHERE c.id = messages.conversation_id
    AND (
      c.user_id = auth.uid()
      OR EXISTS (SELECT 1 FROM public.items i WHERE i.id = c.item_id AND i.user_id = auth.uid())
    )
  ));

-- completed_trades
ALTER TABLE public.completed_trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own trades" ON public.completed_trades FOR ALL USING (auth.uid() = user_id);

-- agent_runs (agents write via service_role key which bypasses RLS)
ALTER TABLE public.agent_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own agent runs" ON public.agent_runs FOR SELECT USING (auth.uid() = user_id);

-- agent_run_events (agents write via service_role key which bypasses RLS)
ALTER TABLE public.agent_run_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read events for own runs" ON public.agent_run_events FOR SELECT
  USING (EXISTS (SELECT 1 FROM public.agent_runs r WHERE r.id = agent_run_events.run_id AND r.user_id = auth.uid()));

-- ============================================================
-- 15. STORAGE BUCKET
-- ============================================================
-- Bucket already exists; create only if missing
INSERT INTO storage.buckets (id, name, public)
VALUES ('item-photos', 'item-photos', true)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Users can upload photos" ON storage.objects;
CREATE POLICY "Users can upload photos" ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'item-photos' AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "Users can delete own photos" ON storage.objects;
CREATE POLICY "Users can delete own photos" ON storage.objects FOR DELETE
  USING (bucket_id = 'item-photos' AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "Anyone can read photos" ON storage.objects;
CREATE POLICY "Anyone can read photos" ON storage.objects FOR SELECT
  USING (bucket_id = 'item-photos');

-- ============================================================
-- 16. REALTIME
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.conversations, public.messages, public.items;
