# PRD — AgentMarket
**Autonomous Resale Agent Platform**

---

## 1. Overview

AgentMarket is a mobile-first platform where users create buy and sell listings for secondhand items, and AI agents autonomously handle searching, negotiating, and managing deals across multiple resale platforms (eBay, Depop, Mercari, OfferUp, Facebook Marketplace).

**One-liner:** Set up a listing, let AI agents do the selling and buying for you across every resale platform.

**Two modes:**
- **SELL** — Create a listing with photos, pricing, and preferences. AI agents post it to platforms and negotiate with buyers.
- **BUY** — Describe what you want with a target price. AI agents search platforms, find listings, and haggle sellers down.

---

## 2. Target Users

**Seller (resale flipper):** Has items to sell across multiple platforms but doesn't want to manually manage listings, respond to messages, and negotiate on each one. Sets up once, AI handles the rest.

**Buyer (niche item hunter):** Wants a specific item at the best price. Instead of manually checking Depop, eBay, Mercari — sets a target and lets agents find and negotiate.

---

## 3. Frontend Architecture (Already Built)

### 3.1 Stack
- React Native (Expo) with Expo Router (file-based routing)
- Pure React Native StyleSheet (no Tailwind/NativeWind)
- Lucide icons (`lucide-react-native`)
- Custom ThemeContext (Light/Dark/System, default System)

### 3.2 Screens & Routes

| Route | Screen | Description |
|-------|--------|-------------|
| `/` | Home | Dashboard with Selling/Buying carousels of listing cards |
| `/settings` | Settings | Appearance, account, platforms, agent defaults, notifications, usage |
| `/item/[id]` | Listing Detail | Full listing view: metrics, photos, overview, settings, market data, conversations |
| `/chat/[id]` | Chat Log | Read-only conversation view between AI agent and a buyer/seller |
| `/new-listing` | New Listing | Form to create a new buy or sell listing (takes `?type=buy` or `?type=sell`) |

### 3.3 Current State
The frontend is fully built with **mock data** (`data/mockData.ts`). All screens are functional with placeholder data. The backend needs to replace mock data with real API calls and persistent storage.

---

## 4. Data Model

> These types are defined in `frontend/data/mockData.ts`. The backend database schema should match these structures.

### 4.1 Core Types

```ts
type Platform = 'ebay' | 'depop' | 'mercari' | 'offerup' | 'facebook';
type ItemStatus = 'active' | 'paused' | 'archived';
type ItemType = 'buy' | 'sell';
type NegotiationStyle = 'aggressive' | 'moderate' | 'passive';
type ReplyTone = 'professional' | 'casual' | 'firm';
```

### 4.2 Item (Listing)

The core entity. Each item is a buy or sell listing with an attached AI agent.

```ts
interface Item {
  id: string;                          // Unique ID
  type: ItemType;                      // 'buy' or 'sell'
  name: string;                        // Listing name (required)
  description: string;                 // Item description
  condition: string;                   // 'New' | 'Like New' | 'Good' | 'Fair' | 'Poor'
  imageColor: string;                  // Fallback color when no photos (hex)
  targetPrice: number;                 // User's target price
  minPrice?: number;                   // Min acceptable price
  maxPrice?: number;                   // Max acceptable price
  autoAcceptThreshold?: number;        // Auto-accept offers at/below this price
  platforms: Platform[];               // Which platforms to list/search on
  status: ItemStatus;                  // 'active' | 'paused' | 'archived'
  quantity: number;                    // Number of items
  negotiationStyle: NegotiationStyle;  // How aggressive the AI negotiates
  replyTone: ReplyTone;               // Tone of AI messages
  bestOffer?: number;                  // Current best offer received/found
  photos: string[];                    // Ordered array of photo URIs (first = cover)
  marketData: MarketData[];            // Per-platform market data
  conversations: Conversation[];       // Active conversations for this listing
}
```

### 4.3 MarketData

Per-platform pricing snapshot for a listing.

```ts
interface MarketData {
  platform: Platform;
  bestBuyPrice: number;    // Lowest asking price on platform
  bestSellPrice: number;   // Highest offer/sold price on platform
  volume: number;          // Number of active listings on platform
}
```

### 4.4 Conversation

A conversation between the AI agent and a buyer/seller on a platform.

```ts
interface Conversation {
  id: string;
  username: string;        // Other party's username
  platform: Platform;      // Which platform this conversation is on
  lastMessage: string;     // Preview of most recent message
  timestamp: string;       // Relative timestamp (e.g. "2m ago")
  unread: boolean;         // Whether there are unread messages
  messages: Message[];     // Full message history
}
```

### 4.5 Message

```ts
interface Message {
  id: string;
  sender: 'agent' | 'them';   // 'agent' = our AI, 'them' = the other party
  text: string;
  timestamp: string;           // e.g. "10:32 AM"
}
```

### 4.6 Platform Names

```ts
const PLATFORM_NAMES: Record<Platform, string> = {
  ebay: 'eBay',
  depop: 'Depop',
  mercari: 'Mercari',
  offerup: 'OfferUp',
  facebook: 'Facebook',
};
```

---

## 5. Backend Requirements

### 5.1 What Needs to Be Built

The backend needs to:
1. **Persist all data** — Items, conversations, messages, user settings, photos
2. **Serve API endpoints** that the frontend will call instead of reading mock data
3. **Handle photo uploads** — Accept images, store them (S3/Cloudinary/etc), return URIs
4. **Provide real-time updates** — When AI agents send/receive messages, the frontend needs to know
5. **Manage user accounts** — Authentication, per-user data isolation
6. **Interface with AI agents** — Trigger agent actions (start searching, start negotiating, pause, resume)

### 5.2 Recommended Stack

- **API:** Python FastAPI (already referenced in the project)
- **Database:** PostgreSQL (relational, fits the data model well)
- **Photo Storage:** S3-compatible (AWS S3, Cloudflare R2, etc.)
- **Auth:** JWT or session-based
- **Real-time:** WebSocket or SSE for conversation updates

### 5.3 Required API Endpoints

#### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create new account |
| POST | `/auth/login` | Login, returns token |
| GET | `/auth/me` | Get current user profile |
| PATCH | `/auth/me` | Update display name, email, profile photo |

#### Items (Listings)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/items` | List all user's items (supports `?type=buy` or `?type=sell` filter) |
| POST | `/items` | Create a new item (from new-listing form) |
| GET | `/items/:id` | Get single item with full detail (conversations, market data) |
| PATCH | `/items/:id` | Update item settings (price, negotiation style, platforms, status, etc.) |
| DELETE | `/items/:id` | Archive/delete an item |
| PATCH | `/items/:id/status` | Change status (active/paused/archived) |
| PATCH | `/items/:id/photos` | Update photo order, add/remove photos |

#### Photos
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/photos/upload` | Upload a photo, returns URI |
| DELETE | `/photos/:id` | Delete a photo |

#### Conversations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/items/:id/conversations` | List conversations for an item |
| GET | `/conversations/:id` | Get full conversation with messages |
| PATCH | `/conversations/:id/read` | Mark conversation as read |

#### Market Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/items/:id/market` | Get market data for an item (per-platform prices, volume) |

#### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/settings` | Get user settings (appearance, notifications, agent defaults, connected platforms) |
| PATCH | `/settings` | Update settings |
| POST | `/settings/platforms/:id/connect` | Connect a platform account |
| DELETE | `/settings/platforms/:id/disconnect` | Disconnect a platform account |

#### Stats
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | Get usage stats (active listings, messages this month, deals closed, API usage) |

### 5.4 Database Schema (Suggested)

```
users
  id, email, display_name, profile_photo_url, created_at

user_settings
  user_id, theme_preference, auto_reply, response_delay,
  negotiation_style, reply_tone, notif_new_message, notif_price_drop,
  notif_deal_closed, notif_listing_expired

platform_connections
  id, user_id, platform, username, connected, api_status, connected_at

items
  id, user_id, type, name, description, condition, image_color,
  target_price, min_price, max_price, auto_accept_threshold,
  status, quantity, negotiation_style, reply_tone,
  best_offer, created_at, updated_at

item_platforms
  item_id, platform

item_photos
  id, item_id, photo_url, sort_order

market_data
  id, item_id, platform, best_buy_price, best_sell_price,
  volume, updated_at

conversations
  id, item_id, username, platform, last_message, last_message_at,
  unread

messages
  id, conversation_id, sender, text, created_at
```

### 5.5 Frontend Integration Points

The frontend currently imports everything from `data/mockData.ts`. To integrate:

1. **Replace `mockItems` with API calls.** The home screen calls `GET /items`, filtered by type. The item detail screen calls `GET /items/:id`.

2. **Replace static conversation data with API calls.** The chat screen calls `GET /conversations/:id`.

3. **New listing form** (`/new-listing`) should `POST /items` with all form fields + uploaded photo URIs.

4. **Settings page** reads from `GET /settings` and writes via `PATCH /settings`.

5. **Real-time conversation updates** — When the AI agent sends/receives a message, the frontend needs to know. Options:
   - WebSocket connection per item detail screen
   - Polling `GET /items/:id/conversations` every 10-30 seconds
   - Push notifications for new messages

6. **Photo upload flow:**
   - User taps "Add Photo" → opens image picker (expo-image-picker)
   - Selected image is uploaded via `POST /photos/upload`
   - Returned URI is added to the item's `photos` array
   - Photo order is persisted via `PATCH /items/:id/photos`

### 5.6 Agent Limit

The frontend shows an "X / 10" agent counter. The backend should enforce this limit — max 10 active items per user (configurable per plan).

---

## 6. AI Agent System (High-Level)

> The agent system is a separate concern from the CRUD backend. It plugs into the same database.

### 6.1 What Agents Do

**For SELL listings:**
- Post listing to selected platforms (using photos, description, price from the item)
- Monitor and respond to incoming messages from buyers
- Negotiate based on the user's negotiation style and price boundaries
- Auto-accept offers that meet the threshold
- Track market prices across platforms

**For BUY listings:**
- Search selected platforms for matching items
- Find and rank the best listings by price, condition, seller credibility
- Send offer messages to sellers
- Negotiate based on user preferences
- Report back best current offer

### 6.2 Agent ↔ Backend Integration

- Agents read item configuration from the database (platforms, prices, negotiation style, reply tone)
- Agents write messages to the `messages` table when they send/receive
- Agents update `best_offer` on the item when a better offer comes in
- Agents update `market_data` periodically with current platform prices
- Agent status (active/paused) is controlled via `items.status`

---

## 7. User Settings (Defaults)

These settings act as defaults for new listings. Each listing can override them.

| Setting | Default | Options |
|---------|---------|---------|
| Theme | System | Light / Dark / System |
| Auto-Reply | On | Toggle |
| Response Delay | 5 min | Configurable |
| Negotiation Style | Moderate | Aggressive / Moderate / Passive |
| Reply Tone | Professional | Professional / Casual / Firm |
| Notifications: New Message | On | Toggle |
| Notifications: Price Drop | On | Toggle |
| Notifications: Deal Closed | On | Toggle |
| Notifications: Listing Expired | Off | Toggle |

---

## 8. Platform Connections

Users connect their accounts on each platform. The backend needs to store:
- Platform ID
- Connected status (boolean)
- Username on that platform
- Connection validity / API status

Supported platforms: eBay, Depop, Mercari, OfferUp, Facebook Marketplace.

---

## 9. Key Frontend Behaviors the Backend Must Support

1. **Home page loads all items** grouped by type (sell/buy), with status counts per group.
2. **Item detail page** loads: item data + photos (ordered) + market data + conversations with messages.
3. **Unread state** — conversations have an `unread` boolean. When the user opens a conversation, call `PATCH /conversations/:id/read`.
4. **Archive flow** — User taps "Archive Listing" → confirmation → `PATCH /items/:id/status` to `archived`. Item disappears from active view.
5. **AI toggle** — User toggles "AI Agent Active" → `PATCH /items/:id/status` between `active` and `paused`.
6. **Photo ordering matters** — The `photos` array order is the upload order for platform listings. The first photo is the cover image shown on the home page card.
7. **New listing creation** — `POST /items` with: name, description, condition, quantity, targetPrice, minPrice, maxPrice, autoAcceptThreshold, platforms[], negotiationStyle, replyTone, photos[], type, status (default: active).
8. **Market data refresh** — The item detail page shows per-platform best buy/sell prices and listing volume. This data should be periodically refreshed by agents.

---

## 10. Out of Scope (For Now)

- In-app payments / checkout
- Push notifications (can be added later)
- Multi-user / team accounts
- Price history charts over time
- In-app camera (photo upload only via image picker for now)
- Actual platform API integrations (agents handle this separately)
