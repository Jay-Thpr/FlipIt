# PRD — AgentMarket
**Autonomous Resale Agent Platform**

---

## 1. Overview

AgentMarket is a mobile-first platform where users create buy and sell listings for secondhand items, and AI agents autonomously handle searching, negotiating, and managing deals across multiple resale platforms (eBay, Depop, Mercari, OfferUp, Facebook Marketplace).

Users optionally set an initial price (what they paid) to enable profit tracking via a cumulative P&L chart on the home screen.

---

## 2. Target Users

**Seller:** Has items to sell across multiple platforms. Sets up once, AI handles posting, messaging, and negotiation on each platform.

**Buyer:** Wants a specific item at the best price. Sets a target and lets agents find and negotiate across platforms.

---

## 3. Frontend (Built)

### 3.1 Stack
- React Native (Expo) with Expo Router
- Pure React Native StyleSheet (no Tailwind)
- Lucide icons, react-native-svg for charts
- Custom ThemeContext (Light/Dark/System)

### 3.2 Screens

| Route | Screen | Description |
|-------|--------|-------------|
| `/auth/sign-in` | Sign In | Email/password + Google/Apple OAuth login |
| `/auth/sign-up` | Sign Up | Name, email, password registration + OAuth |
| `/` | Home | P&L chart, Recent Trades button, Selling/Buying carousels |
| `/trades` | Recent Trades | Full-screen scrollable trade history with profit tracking |
| `/item/[id]` | Listing Detail | Metrics, photos, details, market data, conversations |
| `/chat/[id]` | Chat Log | Read-only conversation between AI agent and counterparty |
| `/new-listing` | New Listing | Full form to create buy or sell listing |
| `/settings/` | Account | Appearance, profile, usage stats |
| `/settings/platforms` | Platforms | Platform connection management |
| `/settings/agents` | Agent Defaults | Auto-reply, negotiation style, reply tone |
| `/settings/notifications` | Notifications | Toggle notification preferences |

### 3.3 Current State
Frontend is fully built with mock data (`data/mockData.ts`). Backend needs to replace mock data with real API calls and Supabase persistence.

---

## 4. Data Model

### 4.1 Core Types
```ts
type Platform = 'ebay' | 'depop' | 'mercari' | 'offerup' | 'facebook';
type ItemStatus = 'active' | 'paused' | 'archived';
type ItemType = 'buy' | 'sell';
type NegotiationStyle = 'aggressive' | 'moderate' | 'passive';
type ReplyTone = 'professional' | 'casual' | 'firm';
```

### 4.2 Item (Listing)
```ts
interface Item {
  id: string;
  type: ItemType;
  name: string;
  description: string;
  condition: string;
  imageColor: string;
  targetPrice: number;
  minPrice?: number;
  maxPrice?: number;
  autoAcceptThreshold?: number;
  initialPrice?: number;       // What user paid — enables P&L tracking
  platforms: Platform[];
  status: ItemStatus;
  quantity: number;
  negotiationStyle: NegotiationStyle;
  replyTone: ReplyTone;
  bestOffer?: number;
  photos: string[];            // Ordered URIs, first = cover
  marketData: MarketData[];
  conversations: Conversation[];
}
```

### 4.3 MarketData
```ts
interface MarketData {
  platform: Platform;
  bestBuyPrice: number;
  bestSellPrice: number;
  volume: number;
}
```

### 4.4 Conversation & Message
```ts
interface Conversation {
  id: string;
  username: string;
  platform: Platform;
  lastMessage: string;
  timestamp: string;
  unread: boolean;
  messages: Message[];
}

interface Message {
  id: string;
  sender: 'agent' | 'them';
  text: string;
  timestamp: string;
}
```

### 4.5 Completed Trade
```ts
interface Trade {
  id: string;
  name: string;
  type: 'Sold' | 'Bought';
  platform: string;
  price: number;
  initialPrice?: number;    // If set, profit = price - initialPrice (sell) or initialPrice - price (buy)
  date: string;
}
```

---

## 5. Backend Requirements

### 5.1 Stack
- **Database:** Supabase (PostgreSQL + Auth + Storage)
- **API:** Supabase client SDK from React Native (direct DB access via RLS)
- **Photo Storage:** Supabase Storage buckets
- **Auth:** Supabase Auth (email/password, Google OAuth, Apple OAuth on iOS)

### 5.2 What Needs to Be Built
See `BACKEND_REQUIREMENTS.md` for full Supabase schema, RLS policies, storage setup, and frontend integration guide.

---

## 6. AI Agent System (High-Level)

### What Agents Do
**Sell listings:** Post to platforms, monitor messages, negotiate with buyers, auto-accept offers at threshold, track market prices.

**Buy listings:** Search platforms, rank listings, send offers, negotiate with sellers, report best offers.

### Agent ↔ Database
- Agents read item config from Supabase (platforms, prices, negotiation style, tone)
- Agents write messages to `messages` table
- Agents update `best_offer` on items
- Agents update `market_data` with current platform prices
- Agent status controlled via `items.status` field
- When a deal closes, agent creates a record in `completed_trades`

---

## 7. User Settings

| Setting | Default | Options |
|---------|---------|---------|
| Theme | System | Light / Dark / System |
| Auto-Reply | On | Toggle |
| Response Delay | 5 min | Configurable |
| Negotiation Style | Moderate | Aggressive / Moderate / Passive |
| Reply Tone | Professional | Professional / Casual / Firm |
| Notif: New Message | On | Toggle |
| Notif: Price Drop | On | Toggle |
| Notif: Deal Closed | On | Toggle |
| Notif: Listing Expired | Off | Toggle |

---

## 8. P&L Tracking

- Users optionally set `initialPrice` when creating a listing (what they paid for the item)
- When a trade completes, profit is calculated:
  - Sell: `soldPrice - initialPrice`
  - Buy: `initialPrice - boughtPrice` (expected resale value minus purchase price)
- Trades without `initialPrice` are excluded from P&L chart but still appear in trade history
- Home page shows cumulative P&L curve with period filtering (1W/1M/3M/ALL)

---

## 9. Platform Connections

Supported: eBay, Depop, Mercari, OfferUp, Facebook Marketplace.

Each connection stores: platform, username, connected status.

---

## 10. ASI:One Master Agent Integration

### Purpose
AgentMarket has a single public Fetch.ai master agent (`resale_copilot_agent`) registered on the ASI:One network. The frontend provides a persistent floating action button (FAB) that gives users and hackathon judges a direct entry point to chat with this agent through ASI:One.

### How It Works
- The FAB appears on all primary screens for authenticated users (not on auth screens).
- On press, it opens `https://asi1.ai/chat?agent=<AGENT_ADDRESS>` in the device browser.
- The agent address is fetched from the backend's `GET /config` endpoint at app startup.
- If the address is unavailable (empty string or fetch failure), the FAB is hidden — no broken links.

### What It Is Not
- This is **not** an in-app chat feature. It is an external redirect to ASI:One.
- The backend remains the authoritative source of product/session state. The ASI:One button is a conversational layer and demo surface, not the primary app runtime.

### Hackathon Track
This integration demonstrates real Fetch.ai / ASI:One agent usage. The master agent can answer questions about listings, market data, and agent activity by querying the same Supabase database the app uses.

---

## 11. Out of Scope (For Now)
- In-app payments / checkout
- Push notifications
- Multi-user / team accounts
- Price history charts per item
- Actual platform API integrations (agents handle separately)
