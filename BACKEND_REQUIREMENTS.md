# Backend Requirements — AgentMarket (Supabase)

Last updated: 2026-04-04

This document specifies everything needed to connect the React Native frontend to Supabase. It covers the database schema, Row-Level Security policies, storage buckets, and exactly which queries each screen makes. After implementing this file, the app should load all data from Supabase instead of the current mock data.

---

## 1. Stack

| Layer | Technology |
|-------|------------|
| Database | Supabase PostgreSQL |
| Auth | Supabase Auth (email/password, Google OAuth, Apple OAuth) |
| Storage | Supabase Storage (photo uploads) |
| Client | `@supabase/supabase-js` from React Native |
| Real-time | Supabase Realtime (conversations, status updates) |

**No separate backend server is needed for CRUD.** The frontend talks directly to Supabase via the JS client with RLS policies enforcing access control. The AI agent system (Jay's branch) is a separate service that reads/writes to the same Supabase database.

---

## 2. Supabase Project Setup

```
1. Create a Supabase project
2. Get the project URL and anon key
3. Install in frontend: npm install @supabase/supabase-js
4. Create frontend/lib/supabase.ts with:
   - SUPABASE_URL (from project settings)
   - SUPABASE_ANON_KEY (from project settings)
   - createClient() instance
```

---

## 3. Database Schema

### 3.1 `users` (managed by Supabase Auth)

Supabase Auth creates `auth.users` automatically. We extend it with a profile table:

```sql
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL DEFAULT '',
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name, email)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', ''), NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 3.2 `user_settings`

```sql
CREATE TABLE public.user_settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  theme_preference TEXT NOT NULL DEFAULT 'system' CHECK (theme_preference IN ('light', 'dark', 'system')),
  auto_reply BOOLEAN NOT NULL DEFAULT true,
  response_delay TEXT NOT NULL DEFAULT '5 min' CHECK (response_delay IN ('1 min', '5 min', '15 min', '30 min')),
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
```

### 3.3 `platform_connections`

```sql
CREATE TABLE public.platform_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  username TEXT,
  connected BOOLEAN NOT NULL DEFAULT false,
  connected_at TIMESTAMPTZ,
  UNIQUE(user_id, platform)
);
```

### 3.4 `items`

The core listing table. Each row is one buy or sell listing.

```sql
CREATE TABLE public.items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('buy', 'sell')),
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  condition TEXT NOT NULL DEFAULT 'Good',
  image_color TEXT NOT NULL DEFAULT '#6EE7B7',
  target_price NUMERIC(10,2) NOT NULL,
  min_price NUMERIC(10,2),
  max_price NUMERIC(10,2),
  auto_accept_threshold NUMERIC(10,2),
  initial_price NUMERIC(10,2),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),
  quantity INTEGER NOT NULL DEFAULT 1,
  negotiation_style TEXT NOT NULL DEFAULT 'moderate' CHECK (negotiation_style IN ('aggressive', 'moderate', 'passive')),
  reply_tone TEXT NOT NULL DEFAULT 'professional' CHECK (reply_tone IN ('professional', 'casual', 'firm')),
  best_offer NUMERIC(10,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_items_user_id ON public.items(user_id);
CREATE INDEX idx_items_status ON public.items(status);
CREATE INDEX idx_items_type ON public.items(type);
```

### 3.4a `updated_at` Auto-Trigger

Shared trigger function used by any table with an `updated_at` column:

```sql
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

CREATE TRIGGER set_market_data_updated_at
  BEFORE UPDATE ON public.market_data
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

### 3.5 `item_platforms`

Which platforms a listing is active on (many-to-many).

```sql
CREATE TABLE public.item_platforms (
  item_id UUID NOT NULL REFERENCES public.items(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  PRIMARY KEY (item_id, platform)
);
```

### 3.6 `item_photos`

Ordered photos for each listing.

```sql
CREATE TABLE public.item_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID NOT NULL REFERENCES public.items(id) ON DELETE CASCADE,
  photo_url TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_item_photos_item_id ON public.item_photos(item_id);
```

### 3.7 `market_data`

Per-platform pricing snapshot for a listing. Updated by AI agents.

```sql
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
```

### 3.8 `conversations`

Each conversation is between the AI agent and one counterparty on one platform.

```sql
CREATE TABLE public.conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID NOT NULL REFERENCES public.items(id) ON DELETE CASCADE,
  username TEXT NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  last_message TEXT NOT NULL DEFAULT '',
  last_message_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  unread BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversations_item_id ON public.conversations(item_id);
```

### 3.9 `messages`

Individual messages within a conversation.

```sql
CREATE TABLE public.messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
  sender TEXT NOT NULL CHECK (sender IN ('agent', 'them')),
  text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation_id ON public.messages(conversation_id);
```

### 3.10 `completed_trades`

When a deal closes, the AI agent (or user) creates a record here. This is what feeds the P&L chart and the Recent Trades page.

```sql
CREATE TABLE public.completed_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  item_id UUID REFERENCES public.items(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('Sold', 'Bought')),
  platform TEXT NOT NULL CHECK (platform IN ('ebay', 'depop', 'mercari', 'offerup', 'facebook')),
  price NUMERIC(10,2) NOT NULL,
  initial_price NUMERIC(10,2),
  completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_completed_trades_user_id ON public.completed_trades(user_id);
CREATE INDEX idx_completed_trades_completed_at ON public.completed_trades(completed_at);
```

---

## 4. Row-Level Security (RLS)

**Enable RLS on all tables.** Every table must have `ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`

### 4.1 Direct user tables

```sql
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

-- items (no DELETE — users archive instead)
ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own items" ON public.items FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own items" ON public.items FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own items" ON public.items FOR UPDATE USING (auth.uid() = user_id);

-- completed_trades
ALTER TABLE public.completed_trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own trades" ON public.completed_trades FOR ALL USING (auth.uid() = user_id);
```

### 4.2 Child tables (access via parent ownership)

```sql
-- item_platforms
ALTER TABLE public.item_platforms ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage platforms for own items" ON public.item_platforms FOR ALL
  USING (EXISTS (SELECT 1 FROM public.items WHERE items.id = item_platforms.item_id AND items.user_id = auth.uid()));

-- item_photos
ALTER TABLE public.item_photos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage photos for own items" ON public.item_photos FOR ALL
  USING (EXISTS (SELECT 1 FROM public.items WHERE items.id = item_photos.item_id AND items.user_id = auth.uid()));

-- market_data (agents write via service_role key which bypasses RLS — no write policy needed)
ALTER TABLE public.market_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read market data for own items" ON public.market_data FOR SELECT
  USING (EXISTS (SELECT 1 FROM public.items WHERE items.id = market_data.item_id AND items.user_id = auth.uid()));

-- conversations
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read conversations for own items" ON public.conversations FOR ALL
  USING (EXISTS (SELECT 1 FROM public.items WHERE items.id = conversations.item_id AND items.user_id = auth.uid()));

-- messages (agents write via service_role key which bypasses RLS — no write policy needed)
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read messages in own conversations" ON public.messages FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM public.conversations c
    JOIN public.items i ON c.item_id = i.id
    WHERE c.id = messages.conversation_id AND i.user_id = auth.uid()
  ));
```

---

## 5. Storage Buckets

```sql
-- Create a public bucket for item photos
INSERT INTO storage.buckets (id, name, public) VALUES ('item-photos', 'item-photos', true);

-- RLS: users can upload to their own folder
CREATE POLICY "Users can upload photos" ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'item-photos' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete own photos" ON storage.objects FOR DELETE
  USING (bucket_id = 'item-photos' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Anyone can read photos" ON storage.objects FOR SELECT
  USING (bucket_id = 'item-photos');
```

**Upload path convention:** `{user_id}/{item_id}/{filename}`

**Upload flow from frontend:**
```ts
const { data, error } = await supabase.storage
  .from('item-photos')
  .upload(`${userId}/${itemId}/${Date.now()}.jpg`, file);

const url = supabase.storage.from('item-photos').getPublicUrl(data.path).data.publicUrl;
// Then insert into item_photos table with this URL
```

---

## 6. Frontend Queries by Screen

### 6.1 Home Page (`app/index.tsx`)

**P&L Chart data:**
```ts
const { data: trades } = await supabase
  .from('completed_trades')
  .select('*')
  .eq('user_id', userId)
  .not('initial_price', 'is', null)
  .order('completed_at', { ascending: true });
```

**Items for carousels:**
```ts
const { data: items } = await supabase
  .from('items')
  .select(`
    *,
    item_platforms(platform),
    item_photos(id, photo_url, sort_order)
  `)
  .eq('user_id', userId)
  .neq('status', 'archived')
  .order('created_at', { ascending: false });
```

### 6.2 Item Detail Page (`app/item/[id].tsx`)

```ts
const { data: item } = await supabase
  .from('items')
  .select(`
    *,
    item_platforms(platform),
    item_photos(id, photo_url, sort_order),
    market_data(platform, best_buy_price, best_sell_price, volume),
    conversations(
      id, username, platform, last_message, last_message_at, unread,
      messages(id, sender, text, created_at)
    )
  `)
  .eq('id', itemId)
  .single();
```

### 6.3 Chat Log Page (`app/chat/[id].tsx`)

```ts
// Get conversation with messages
const { data: conversation } = await supabase
  .from('conversations')
  .select('*, messages(id, sender, text, created_at)')
  .eq('id', conversationId)
  .single();

// Mark as read
await supabase
  .from('conversations')
  .update({ unread: false })
  .eq('id', conversationId);
```

**Real-time subscription for new messages:**
```ts
supabase
  .channel(`messages:${conversationId}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'messages',
    filter: `conversation_id=eq.${conversationId}`,
  }, (payload) => {
    // Append new message to list
  })
  .subscribe();
```

### 6.4 New Listing (`app/new-listing.tsx`)

```ts
// 1. Create item
const { data: item } = await supabase
  .from('items')
  .insert({
    user_id: userId,
    type: 'sell',
    name: 'Air Jordan 1',
    description: '...',
    condition: 'New',
    image_color: '#6EE7B7',
    target_price: 320,
    min_price: 260,
    max_price: 380,
    initial_price: 85,  // optional
    negotiation_style: 'moderate',
    reply_tone: 'professional',
    status: aiActive ? 'active' : 'paused',
    quantity: 1,
  })
  .select()
  .single();

// 2. Insert platforms
await supabase
  .from('item_platforms')
  .insert(selectedPlatforms.map(p => ({ item_id: item.id, platform: p })));

// 3. Upload photos + insert photo records
for (const [i, photo] of photos.entries()) {
  const path = `${userId}/${item.id}/${Date.now()}_${i}.jpg`;
  await supabase.storage.from('item-photos').upload(path, photo);
  const url = supabase.storage.from('item-photos').getPublicUrl(path).data.publicUrl;
  await supabase.from('item_photos').insert({ item_id: item.id, photo_url: url, sort_order: i });
}
```

### 6.5 Recent Trades (`app/trades.tsx`)

```ts
const { data: trades } = await supabase
  .from('completed_trades')
  .select('*')
  .eq('user_id', userId)
  .order('completed_at', { ascending: false });
```

### 6.6 Settings — Account (`settings/index.tsx`)

```ts
// Read
const { data: profile } = await supabase.from('profiles').select('*').eq('id', userId).single();
const { data: settings } = await supabase.from('user_settings').select('*').eq('user_id', userId).single();

// Update
await supabase.from('profiles').update({ display_name: 'New Name' }).eq('id', userId);
await supabase.from('user_settings').update({ theme_preference: 'dark' }).eq('user_id', userId);
```

### 6.7 Settings — Platforms (`settings/platforms.tsx`)

```ts
const { data: platforms } = await supabase
  .from('platform_connections')
  .select('*')
  .eq('user_id', userId);

// Connect
await supabase
  .from('platform_connections')
  .upsert({
    user_id: userId,
    platform: 'ebay',
    connected: true,
    username: '@reseller_sam',
    connected_at: new Date().toISOString(),
  });

// Disconnect
await supabase
  .from('platform_connections')
  .update({ connected: false })
  .eq('user_id', userId)
  .eq('platform', 'ebay');
```

### 6.8 Settings — Agent Defaults (`settings/agents.tsx`)

```ts
// Same user_settings table
await supabase
  .from('user_settings')
  .update({ negotiation_style: 'aggressive', reply_tone: 'casual' })
  .eq('user_id', userId);
```

### 6.9 Settings — Notifications (`settings/notifications.tsx`)

```ts
await supabase
  .from('user_settings')
  .update({ notif_new_message: false })
  .eq('user_id', userId);
```

---

## 7. Item Status Updates

```ts
// Pause/resume (AI toggle)
await supabase.from('items').update({ status: 'paused' }).eq('id', itemId);
await supabase.from('items').update({ status: 'active' }).eq('id', itemId);

// Archive
await supabase.from('items').update({ status: 'archived' }).eq('id', itemId);
```

---

## 8. Photo Management

### Reorder
```ts
// Update sort_order for all photos of an item
await Promise.all(
  photos.map((photo, i) =>
    supabase.from('item_photos').update({ sort_order: i }).eq('id', photo.id)
  )
);
```

### Delete
```ts
// Delete from storage + table
await supabase.storage.from('item-photos').remove([photo.path]);
await supabase.from('item_photos').delete().eq('id', photoId);
```

---

## 9. P&L Calculation

The frontend computes P&L from `completed_trades`:

```ts
// Sell trade: profit = price - initial_price
// Buy trade: profit = initial_price - price (expected resale - what you paid)
// Trades without initial_price: excluded from P&L chart

function getProfit(trade: CompletedTrade): number | null {
  if (trade.initial_price == null) return null;
  if (trade.type === 'Sold') return trade.price - trade.initial_price;
  return trade.initial_price - trade.price;
}
```

The cumulative P&L is computed client-side by summing profits in chronological order. The chart renders this as a bezier curve.

---

## 10. AI Agent Integration

AI agents (separate service, Jay's branch) access Supabase using the **service_role key** (bypasses RLS).

### What agents read:
- `items` — listing config (platforms, prices, negotiation style, reply tone, status)
- `item_photos` — photos to upload to platforms
- `user_settings` — default agent behavior

### What agents write:
- `messages` — when sending/receiving messages on platforms
- `conversations` — create new conversations, update `last_message`, set `unread`
- `market_data` — periodic platform price updates
- `items.best_offer` — when a better offer comes in
- `completed_trades` — when a deal closes

### Agent reads item config:
```sql
SELECT i.*, array_agg(ip.platform) as platforms
FROM items i
JOIN item_platforms ip ON i.id = ip.item_id
WHERE i.status = 'active'
GROUP BY i.id;
```

### Agent records a completed trade:
```sql
INSERT INTO completed_trades (user_id, item_id, name, type, platform, price, initial_price)
SELECT user_id, id, name,
  CASE WHEN type = 'sell' THEN 'Sold' ELSE 'Bought' END,
  'ebay', 145.00, initial_price
FROM items WHERE id = '<item_id>';

-- Then archive the item
UPDATE items SET status = 'archived' WHERE id = '<item_id>';
```

---

## 11. Realtime Subscriptions

**Required setup:** Enable replication for realtime-enabled tables. Run this in the SQL editor or it will be in the migration:

```sql
ALTER PUBLICATION supabase_realtime ADD TABLE public.conversations, public.messages, public.items;
```

For live updates without polling:

```ts
// Subscribe to conversation updates for all user's items
supabase
  .channel('user-conversations')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'conversations',
  }, (payload) => {
    // Refresh conversation list
  })
  .subscribe();

// Subscribe to item status changes (agent paused/activated something)
supabase
  .channel('user-items')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'items',
    filter: `user_id=eq.${userId}`,
  }, (payload) => {
    // Refresh item data
  })
  .subscribe();
```

---

## 12. Authentication Flow

### 12.1 Supabase Auth Setup

Enable the following providers in the Supabase Dashboard under **Authentication > Providers**:

| Provider | Setup |
|----------|-------|
| Email/Password | Enabled by default. Disable "Confirm email" for dev, enable for production. |
| Google | Create OAuth credentials in Google Cloud Console. Set authorized redirect URI to `https://<project-ref>.supabase.co/auth/v1/callback`. Add Client ID and Secret in Supabase dashboard. |
| Apple | Register a Services ID with Apple Developer. Configure Sign in with Apple. Set return URL to `https://<project-ref>.supabase.co/auth/v1/callback`. Add Service ID and Secret Key in Supabase dashboard. |

### 12.2 Email/Password Sign Up

```ts
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'securepassword',
  options: {
    data: {
      display_name: 'Sam',  // stored in raw_user_meta_data, used by handle_new_user trigger
    },
  },
});
```

The `on_auth_user_created` trigger auto-creates a row in `profiles` and `user_settings`.

### 12.3 Email/Password Sign In

```ts
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'securepassword',
});
```

### 12.4 Google OAuth

For React Native, use `expo-auth-session` or `expo-web-browser` to handle the OAuth redirect:

```ts
import * as WebBrowser from 'expo-web-browser';
import { makeRedirectUri } from 'expo-auth-session';

const redirectUri = makeRedirectUri();

const handleGoogleSignIn = async () => {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: redirectUri,
      skipBrowserRedirect: true,
    },
  });

  if (data?.url) {
    const result = await WebBrowser.openAuthSessionAsync(data.url, redirectUri);
    if (result.type === 'success') {
      const url = new URL(result.url);
      const access_token = url.searchParams.get('access_token');
      const refresh_token = url.searchParams.get('refresh_token');
      if (access_token && refresh_token) {
        await supabase.auth.setSession({ access_token, refresh_token });
      }
    }
  }
};
```

**Required packages:** `expo-web-browser`, `expo-auth-session`

### 12.5 Apple OAuth (iOS only)

```ts
import * as AppleAuthentication from 'expo-apple-authentication';

const handleAppleSignIn = async () => {
  const credential = await AppleAuthentication.signInAsync({
    requestedScopes: [
      AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
      AppleAuthentication.AppleAuthenticationScope.EMAIL,
    ],
  });

  if (credential.identityToken) {
    const { data, error } = await supabase.auth.signInWithIdToken({
      provider: 'apple',
      token: credential.identityToken,
    });
  }
};
```

**Required package:** `expo-apple-authentication`

### 12.6 Profile Trigger for OAuth Users

The existing `handle_new_user` trigger works for OAuth too. For Google/Apple, the display name comes from the provider's metadata:

```sql
-- Updated trigger to handle OAuth display names
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
```

### 12.7 Session Persistence

Supabase JS client auto-persists the session in `AsyncStorage` (React Native) or `localStorage` (web). On app launch, call:

```ts
const { data: { session } } = await supabase.auth.getSession();
```

### 12.8 Auth State Listener

Set up in the root layout so the app reacts to sign-in/sign-out:

```ts
useEffect(() => {
  const { data: { subscription } } = supabase.auth.onAuthStateChange(
    (event, session) => {
      if (event === 'SIGNED_IN') {
        router.replace('/');
      } else if (event === 'SIGNED_OUT') {
        router.replace('/auth/sign-in');
      }
    }
  );
  return () => subscription.unsubscribe();
}, []);
```

### 12.9 Sign Out

```ts
await supabase.auth.signOut();
```

### 12.10 Getting Current User ID

```ts
const userId = (await supabase.auth.getUser()).data.user?.id;
```

This `userId` is what all queries use for `user_id` and what RLS checks via `auth.uid()`.

---

## 13. Error Handling

All Supabase calls return `{ data, error }`. The frontend should handle errors consistently:

```ts
const { data, error } = await supabase.from('items').select('*').eq('user_id', userId);

if (error) {
  // Log for debugging
  console.error('Failed to load items:', error.message);

  // Show user-friendly message
  Alert.alert('Error', 'Could not load your listings. Please try again.');
  return;
}
```

### Common error scenarios

| Scenario | Cause | Handling |
|----------|-------|----------|
| `error.code === 'PGRST301'` | RLS denied access | User is likely signed out — redirect to sign-in |
| `error.code === '23505'` | Unique constraint violation | Duplicate entry — show "already exists" message |
| `error.code === '23503'` | Foreign key violation | Referenced item was deleted — refresh the list |
| `error.message` contains `JWT expired` | Session expired | Call `supabase.auth.refreshSession()` or redirect to sign-in |
| Network error (no `error.code`) | Offline / timeout | Show "No internet connection" message |

### Wrapper pattern (optional)

```ts
async function query<T>(promise: Promise<{ data: T | null; error: any }>): Promise<T> {
  const { data, error } = await promise;
  if (error) throw new Error(error.message);
  return data as T;
}
```

---

## 14. Frontend Integration Checklist

After implementing the Supabase schema above, the frontend developer needs to:

1. [ ] Install `@supabase/supabase-js`, `expo-web-browser`, `expo-auth-session`, `expo-apple-authentication` and create `lib/supabase.ts`
2. [ ] Wire up `auth/sign-in.tsx` and `auth/sign-up.tsx` to Supabase Auth (replace TODO stubs)
3. [ ] Add `onAuthStateChange` listener in `_layout.tsx` to redirect on sign-in/sign-out
4. [ ] Enable Google and Apple providers in Supabase Dashboard
5. [ ] Replace `mockItems` import in `index.tsx` with Supabase query
6. [ ] Replace `TRADE_HISTORY` in `trades.tsx` with Supabase query
7. [ ] Replace static settings data with `user_settings` + `profiles` queries
8. [ ] Replace static platform data with `platform_connections` query
9. [ ] Wire up `new-listing.tsx` form to `items` + `item_platforms` + `item_photos` inserts
10. [ ] Wire up item detail page to Supabase query with nested selects
11. [ ] Wire up chat page to messages query + realtime subscription
12. [ ] Wire up photo upload to Supabase Storage
13. [ ] Wire up AI toggle to `items.status` update
14. [ ] Wire up archive to `items.status` update
15. [ ] Wire up P&L chart to `completed_trades` query

---

## 15. Column Name Mapping

The frontend uses camelCase. Supabase uses snake_case. Use the Supabase JS client's built-in camelCase transform or map manually:

| Frontend | Supabase Column |
|----------|----------------|
| `targetPrice` | `target_price` |
| `minPrice` | `min_price` |
| `maxPrice` | `max_price` |
| `autoAcceptThreshold` | `auto_accept_threshold` |
| `initialPrice` | `initial_price` |
| `imageColor` | `image_color` |
| `bestOffer` | `best_offer` |
| `negotiationStyle` | `negotiation_style` |
| `replyTone` | `reply_tone` |
| `bestBuyPrice` | `best_buy_price` |
| `bestSellPrice` | `best_sell_price` |
| `lastMessage` | `last_message` |
| `lastMessageAt` / `timestamp` (Conversation) | `last_message_at` |
| `timestamp` (Message) | `created_at` |
| `photoUrl` | `photo_url` |
| `sortOrder` | `sort_order` |
| `completedAt` | `completed_at` |
| `createdAt` | `created_at` |
| `updatedAt` | `updated_at` |

---

## 16. Seed Data

Run this after creating a test user via sign-up. Replace `TEST_USER_ID` with the UUID from `auth.users`.

```sql
-- ============================================================
-- Replace this with your test user's UUID after signing up
-- ============================================================
DO $$
DECLARE
  uid UUID := 'TEST_USER_ID';  -- <-- REPLACE THIS
  item1 UUID := gen_random_uuid();
  item2 UUID := gen_random_uuid();
  item3 UUID := gen_random_uuid();
  item4 UUID := gen_random_uuid();
  item5 UUID := gen_random_uuid();
  conv1 UUID := gen_random_uuid();
  conv2 UUID := gen_random_uuid();
  conv3 UUID := gen_random_uuid();
  conv4 UUID := gen_random_uuid();
  conv5 UUID := gen_random_uuid();
  conv6 UUID := gen_random_uuid();
BEGIN

-- ============================================================
-- Items (matches mockItems in frontend/data/mockData.ts)
-- ============================================================
INSERT INTO public.items (id, user_id, type, name, description, condition, image_color, target_price, min_price, max_price, auto_accept_threshold, initial_price, status, quantity, negotiation_style, reply_tone, best_offer) VALUES
  (item1, uid, 'sell', 'Air Jordan 1 Retro High OG', 'Chicago colorway, DS (deadstock). Box included. Size 10.', 'New', '#FCA5A5', 320, 260, 380, 300, 85, 'active', 1, 'moderate', 'professional', 295),
  (item2, uid, 'sell', 'Sony WH-1000XM4', 'Excellent condition, barely used. Midnight blue. All accessories included.', 'Like New', '#93C5FD', 190, 150, 220, 175, 45, 'active', 1, 'passive', 'casual', NULL),
  (item3, uid, 'sell', 'North Face Nuptse 700', 'Vintage 90s Nuptse puffer. Navy blue. Size M. Minor fade on left arm.', 'Good', '#6EE7B7', 145, 110, 180, NULL, NULL, 'paused', 1, 'moderate', 'casual', NULL),
  (item4, uid, 'buy', 'Canon AE-1 Program', 'Looking for a clean body with working meter and shutter. Black preferred.', 'Good', '#FCD34D', 85, 60, 120, 90, NULL, 'active', 1, 'aggressive', 'professional', 95),
  (item5, uid, 'buy', 'Supreme Box Logo Hoodie FW20', 'Black or white preferred. Size L. Must be verified authentic.', 'Good', '#F9A8D4', 380, 300, 450, 400, NULL, 'active', 1, 'moderate', 'professional', NULL);

-- ============================================================
-- Item Platforms
-- ============================================================
INSERT INTO public.item_platforms (item_id, platform) VALUES
  (item1, 'depop'), (item1, 'ebay'), (item1, 'mercari'),
  (item2, 'depop'), (item2, 'facebook'), (item2, 'mercari'),
  (item3, 'depop'), (item3, 'ebay'),
  (item4, 'ebay'), (item4, 'depop'), (item4, 'mercari'), (item4, 'offerup'),
  (item5, 'depop'), (item5, 'ebay'), (item5, 'mercari');

-- ============================================================
-- Item Photos
-- ============================================================
INSERT INTO public.item_photos (item_id, photo_url, sort_order) VALUES
  (item1, 'https://picsum.photos/seed/jordan1a/400/400', 0),
  (item1, 'https://picsum.photos/seed/jordan1b/400/400', 1),
  (item1, 'https://picsum.photos/seed/jordan1c/400/400', 2),
  (item2, 'https://picsum.photos/seed/sonyxm4a/400/400', 0),
  (item2, 'https://picsum.photos/seed/sonyxm4b/400/400', 1),
  (item3, 'https://picsum.photos/seed/nuptse700/400/400', 0),
  (item5, 'https://picsum.photos/seed/supremebogo/400/400', 0),
  (item5, 'https://picsum.photos/seed/supremebogo2/400/400', 1);

-- ============================================================
-- Market Data
-- ============================================================
INSERT INTO public.market_data (item_id, platform, best_buy_price, best_sell_price, volume) VALUES
  (item1, 'depop', 299, 315, 42),
  (item1, 'ebay', 310, 332, 128),
  (item1, 'mercari', 285, 298, 67),
  (item2, 'depop', 170, 185, 23),
  (item2, 'facebook', 160, 172, 15),
  (item2, 'mercari', 180, 195, 41),
  (item3, 'depop', 130, 142, 19),
  (item3, 'ebay', 145, 158, 34),
  (item4, 'ebay', 85, 98, 87),
  (item4, 'depop', 95, 110, 31),
  (item4, 'mercari', 80, 89, 44),
  (item4, 'offerup', 65, 75, 12),
  (item5, 'depop', 390, 410, 8),
  (item5, 'ebay', 405, 425, 22),
  (item5, 'mercari', 375, 395, 11);

-- ============================================================
-- Conversations
-- ============================================================
INSERT INTO public.conversations (id, item_id, username, platform, last_message, last_message_at, unread) VALUES
  (conv1, item1, 'sneaker_kylie', 'depop', 'Would you take $280?', now() - interval '2 minutes', true),
  (conv2, item1, 'j1collector', 'ebay', 'Offer of $295 submitted', now() - interval '1 hour', false),
  (conv3, item2, 'techwatcher', 'mercari', 'Do they come with the case?', now() - interval '30 minutes', true),
  (conv4, item4, 'vintage_photo_co', 'depop', 'I can do $95 shipped.', now() - interval '15 minutes', true),
  (conv5, item4, 'filmcameraseller', 'ebay', 'Offer sent: $80', now() - interval '2 hours', false),
  (conv6, item5, 'supreme_resells', 'depop', 'Can''t go lower than $400.', now() - interval '45 minutes', false);

-- ============================================================
-- Messages
-- ============================================================
INSERT INTO public.messages (conversation_id, sender, text, created_at) VALUES
  -- conv1: sneaker_kylie <> agent (Air Jordan 1)
  (conv1, 'them',  'Hey! Love these. Are they still available?', now() - interval '15 minutes'),
  (conv1, 'agent', 'Hi! Yes, still available. DS with original box. Happy to answer any questions!', now() - interval '14 minutes'),
  (conv1, 'them',  'Would you take $280?', now() - interval '6 minutes'),
  (conv1, 'agent', 'Thanks for the offer! I''m firm at $310 given recent eBay sold comps averaging $330. Would you meet me at $310?', now() - interval '5 minutes'),

  -- conv2: j1collector <> agent (Air Jordan 1)
  (conv2, 'them',  'Are these authentic?', now() - interval '2 hours'),
  (conv2, 'agent', 'Absolutely 100% authentic. I can provide purchase receipt and authentication photos.', now() - interval '119 minutes'),
  (conv2, 'them',  'Offer of $295 submitted', now() - interval '90 minutes'),

  -- conv3: techwatcher <> agent (Sony XM4)
  (conv3, 'them',  'Do they come with the case?', now() - interval '35 minutes'),
  (conv3, 'agent', 'Yes! Comes with original Sony carry case, charging cable, aux cable, and all documentation.', now() - interval '34 minutes'),

  -- conv4: vintage_photo_co <> agent (Canon AE-1)
  (conv4, 'agent', 'Hi! I''ve seen similar ones sell for around $80–90 recently. Would you consider $75 shipped? Happy to pay right away.', now() - interval '50 minutes'),
  (conv4, 'them',  'Hmm, I think it''s worth more. Shutter sounds perfect on this one.', now() - interval '33 minutes'),
  (conv4, 'agent', 'Totally fair! Could you meet me at $85? I''m ready to buy today.', now() - interval '32 minutes'),
  (conv4, 'them',  'I can do $95 shipped.', now() - interval '17 minutes'),

  -- conv5: filmcameraseller <> agent (Canon AE-1)
  (conv5, 'agent', 'Hi! I''d like to offer $80 shipped. Based on recent sales data, this is a fair market offer — I can pay immediately.', now() - interval '3 hours'),
  (conv5, 'them',  'Offer sent: $80', now() - interval '3 hours'),

  -- conv6: supreme_resells <> agent (Supreme Hoodie)
  (conv6, 'agent', 'Hey! Recent eBay sold prices average around $380 for FW20 box logo. Would you consider $360?', now() - interval '1 hour'),
  (conv6, 'them',  'Can''t go lower than $400.', now() - interval '45 minutes');

-- ============================================================
-- Completed Trades (matches TRADE_HISTORY in frontend/app/trades.tsx)
-- ============================================================
INSERT INTO public.completed_trades (user_id, name, type, platform, price, initial_price, completed_at) VALUES
  (uid, 'Nike Dunk Low Panda',   'Sold',   'ebay',     145, 93,   '2026-03-28T12:00:00Z'),
  (uid, 'Vintage Levi 501s',     'Sold',   'depop',    68,  12,   '2026-03-25T12:00:00Z'),
  (uid, 'Canon AE-1 Body',       'Bought', 'mercari',  82,  NULL, '2026-03-22T12:00:00Z'),
  (uid, 'Ray-Ban Aviators',      'Sold',   'facebook', 85,  95,   '2026-03-18T12:00:00Z'),
  (uid, 'Bose QC45',             'Sold',   'ebay',     195, 120,  '2026-03-15T12:00:00Z'),
  (uid, 'Supreme Beanie',        'Bought', 'depop',    45,  NULL, '2026-03-12T12:00:00Z'),
  (uid, 'PS5 DualSense',         'Sold',   'mercari',  42,  28,   '2026-03-10T12:00:00Z'),
  (uid, 'Patagonia Fleece',      'Sold',   'ebay',     78,  15,   '2026-03-08T12:00:00Z'),
  (uid, 'AirPods Pro 2',         'Sold',   'facebook', 165, 130,  '2026-03-05T12:00:00Z'),
  (uid, 'Vintage Polaroid',      'Bought', 'ebay',     55,  120,  '2026-03-02T12:00:00Z'),
  (uid, 'North Face Puffer',     'Sold',   'depop',    125, 35,   '2026-02-28T12:00:00Z'),
  (uid, 'Mechanical Keyboard',   'Sold',   'mercari',  95,  NULL, '2026-02-25T12:00:00Z');

-- ============================================================
-- Platform Connections (defaults for test user)
-- ============================================================
INSERT INTO public.platform_connections (user_id, platform, username, connected, connected_at) VALUES
  (uid, 'ebay',     '@reseller_sam', true,  now()),
  (uid, 'depop',    '@reseller_sam', true,  now()),
  (uid, 'mercari',  '@reseller_sam', true,  now()),
  (uid, 'offerup',  NULL,            false, NULL),
  (uid, 'facebook', NULL,            false, NULL);

END $$;
```

---

## 17. Master Agent Config Endpoint

The frontend includes a persistent floating action button (FAB) that links users to the project's public Fetch.ai master agent on ASI:One. The backend must expose a lightweight config endpoint so the frontend can retrieve the agent's address at runtime.

### 17.1 Endpoint

```
GET /config
```

**Response:**
```json
{
  "resale_copilot_agent_address": "agent1q..."
}
```

- If no agent is registered or the address is unavailable, return an empty string for the value.
- This endpoint does **not** require authentication — it returns public project-level config.

### 17.2 Frontend Usage

The `MasterAgentFAB` component (`components/MasterAgentFAB.tsx`) fetches this endpoint on mount. If the address is present, it renders a FAB that opens `https://asi1.ai/chat?agent=<address>` in the device browser. If the address is empty or the fetch fails, the button is hidden.

### 17.3 Backend Implementation Notes

- This can be a simple static JSON response from a lightweight HTTP server (e.g., FastAPI, Express) or a Supabase Edge Function.
- The agent address is the stable on-chain address of the `resale_copilot_agent` registered with Fetch.ai / ASI:One.
- The frontend currently uses a placeholder backend URL (`http://localhost:8000`). Update this when the backend is deployed.
