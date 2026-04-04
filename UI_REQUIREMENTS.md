# UI Requirements — AgentMarket Frontend

Last updated: 2026-04-04

---

## Overview

A mobile marketplace agent app where users set up automated buy/sell agents across multiple platforms. The UI is professional and data-forward — purpose-built for a power user who wants to monitor and manage deals at a glance.

---

## Design System

### Theme
The app uses a **dynamic theme system** (`contexts/ThemeContext.tsx`) with three modes: **Light**, **Dark**, and **System**. Default is **System** (follows device setting).

### Style
**Dark professional** — neutral zinc palette with violet accent, high contrast, clean typography. Feels closer to Linear or a trading terminal than a consumer marketplace.

### Color Tokens (`constants/colors.ts`)

Two full token sets are defined: `DarkColors` and `LightColors`. Components consume colors via `useTheme().colors`.

#### Dark Mode
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#8B5CF6` | Primary actions, active accents, brand |
| `onPrimary` | `#FFFFFF` | Text/icons on primary bg |
| `secondary` | `#A78BFA` | Secondary highlights |
| `accent` | `#22C55E` | Success, active states, prices |
| `accentLight` | `#14532D` | Accent tint bg |
| `background` | `#09090B` | Page background (zinc-950) |
| `surface` | `#18181B` | Cards, elevated surfaces (zinc-900) |
| `surfaceRaised` | `#27272A` | Pressed/active surface state |
| `muted` | `#27272A` | Subtle fills, icon backgrounds |
| `border` | `#3F3F46` | Dividers, card borders (zinc-700) |
| `destructive` | `#EF4444` | Errors, destructive actions |
| `textPrimary` | `#FAFAFA` | Body text |
| `textSecondary` | `#A1A1AA` | Secondary labels |
| `textMuted` | `#71717A` | Hints, timestamps, counts |
| `statusBarStyle` | `light` | Status bar icons |

#### Light Mode
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#7C3AED` | — |
| `accent` | `#16A34A` | — |
| `background` | `#F4F4F5` | Neutral off-white |
| `surface` | `#FFFFFF` | — |
| `textPrimary` | `#18181B` | Dark gray |
| `textMuted` | `#A1A1AA` | — |
| `statusBarStyle` | `dark` | — |

### Typography
**Font:** Inter (system default, all weights via React Native)
- App name: Inter 800, 24px, letterSpacing -0.5
- Section headers: Inter 700, 18px, letterSpacing -0.3
- Card item name: Inter 700, 13px (overlay)
- Price / offer: Inter 800, 15px, letterSpacing -0.3
- Labels/captions: Inter 600, 11–13px
- Section labels (uppercase): Inter 600, 11px, letterSpacing 0.8

### Spacing
Strict 4/8pt system. Common values: 4, 8, 10, 12, 14, 16, 20, 24, 32, 48.

### Icons
Lucide (`lucide-react-native`) throughout. No emojis as icons. Standard size: 18–22pt. Small: 14–16pt. All icon-only buttons use `hitSlop` for 44×44pt touch targets.

### Platform Colors
Two color configs per platform (dark + light). Dark mode uses deep tinted backgrounds with lighter text. Light mode uses pastel backgrounds.

| Platform | Dark text | Dark bg | Light text | Light bg |
|----------|-----------|---------|------------|----------|
| eBay | `#FC8181` | `#3D0F0F` | `#E53935` | `#FEE2E2` |
| Depop | `#F472B6` | `#3D0A24` | `#D1156B` | `#FCE7F3` |
| Mercari | `#60A5FA` | `#0F1E3D` | `#1E40AF` | `#DBEAFE` |
| OfferUp | `#FBBF24` | `#3D2000` | `#D97706` | `#FEF3C7` |
| Facebook | `#60A5FA` | `#0F1E3D` | `#1877F2` | `#EFF6FF` |

### Status Badges (theme-aware pill shape)

| Status | Dark bg | Dark text | Light bg | Light text |
|--------|---------|-----------|----------|------------|
| Active | `#052E16` | `#4ADE80` | `#DCFCE7` | `#15803D` |
| Paused | `#27272A` | `#A1A1AA` | `#F4F4F5` | `#71717A` |
| Archived | `#450A0A` | `#F87171` | `#FEE2E2` | `#DC2626` |

---

## Pages

---

### 1. Home Page (`app/index.tsx`)

The main dashboard. Gives the user an immediate read on all active buying and selling agents.

#### Header Bar
- Left: `AgentMarket` brand name (primary color, Inter 800, 24px) + "X / 10 Agents in Use" counter pill below it
- Right: Circular avatar button (40×40, primary bg, initials "SS") → tapping opens a profile dropdown modal

**No subtitle** under the app name.

#### Profile Dropdown Modal (semi-transparent overlay, top-right)
- User avatar + name + email row
- "Settings" menu item → navigates to `/settings`
- Divider
- "Sign Out" (destructive red)

#### Layout
Two stacked sections: **Selling** (top) and **Buying** (bottom), each with:
- Section title (Inter 700, 18px) + active count pill (text only, **no dot**) on the left
- Total agent count label on the right
- Horizontal scrollable carousel of `ItemCard` components
- `AddNewCard` button pinned **below** the carousel (full-width, outside scroll, always visible)

---

### 2. Item Detail Page (`app/item/[id].tsx`)

Opened by tapping any item card.

#### Header Bar
- Back arrow — **bare, no box or border** (36×36 touch area, no background)
- Item name as title (Inter 700, 16px, truncated)
- `StatusBadge` on the right

#### Hero Image
Full-width colored block, 200px tall, `item.imageColor` background, giant watermark initial.

#### Section: Overview
Uppercase section label + card body containing:
- Description, Condition, Quantity, Mode (label / value rows)
- **Best Current Offer** (highlighted in primary color) — shown only if `item.bestOffer` exists
- **Item name is NOT repeated** here (already shown in header)

#### Section: Settings
Uppercase section label + card body:

| Row | Control |
|-----|---------|
| **AI Agent Active** | Live `Switch` (at top) |
| Target Price | Static value |
| Min Acceptable | Static value (if set) |
| Max Acceptable | Static value (if set) |
| Auto-Accept Below | Static value (if set) |
| Negotiation Style | Static value |
| Reply Tone | Static value |
| Active Platforms | Comma-separated company names (e.g. "eBay, Depop") |

**No "Auto-Relist" row.**

#### Section: Market Overview
Horizontal `ScrollView` of market cards. Each card (`surface` bg, `border` border, 12px radius):
- **Platform name** (company name, e.g. "eBay") — no custom badge widget
- **Buy price** + **Sell price** side by side with a vertical divider
- **Volume** — "N listings"
- No trend percentage indicators

#### Section: Active Conversations
Card body with conversation rows:
- Username (bold) + platform name as text (muted)
- Last message preview: **white/primary color** when unread, **grayed** when read — **no dot indicator**
- Timestamp + chevron

#### Archive Listing (bottom)
- Outlined destructive button: "Archive Listing"
- Tapping triggers `Alert.alert` confirmation before archiving

---

### 3. Chat Log Page (`app/chat/[id].tsx`)

Read-only conversation view.

#### Header Bar
- Back arrow — **bare, no box** (same pattern as item detail)
- Center: `@username` (bold, 15px) + item name (muted subtitle, 12px)
- Right: Platform company name as plain text (e.g. "Depop") — **no platform badge widget**

**No info banner** below the header ("Log view only" banner has been removed).

#### Message List (`FlatList`)
- Agent bubbles: right-aligned, `primary` background, `onPrimary` text
- Counterparty bubbles: left-aligned, `surface` background with `border`
- Timestamp below each bubble (`textMuted`, 11px)

---

### 4. Settings Page (`app/settings.tsx`)

Navigation: avatar menu on Home → Settings (Stack navigator, back button labeled "Back").

#### Appearance
Segmented theme picker (Light / Dark / System). Default: **System**. Active option shows `surfaceRaised` bg + `primary` border.

#### Account
Three rows: Display Name, Email, Profile Photo (icon + label + value + chevron).

#### Platforms (formerly "Connected Platforms")
One row per platform:
- Colored icon square (theme-aware)
- Platform name + username (if connected), or "Not connected"
- **No colored dots next to username**
- Status: "Connected" (green text, no wifi icon) or "Connect" (gray outlined text badge)

#### Default Agent Behavior (formerly "Agent Behavior")
**No subtitle/subtext under the section title.**
- Auto-Reply toggle
- Response Delay row
- Negotiation Style — **stacked layout**: label row above, full-width segmented selector below (prevents overflow)

#### Notifications
Four toggle rows: New Message, Price Drop, Deal Closed, Listing Expired.

#### Usage
2×2 grid inside a `SectionCard` (same visual treatment as other sections):
- Active Listings, Messages This Month, Deals Closed, API Usage
- Each tile: large number (Inter 800, 28px, `primary`) + label

---

## Components

### `ItemCard` (`components/ItemCard.tsx`)
- Colored background with watermark initial letter
- **Top-left**: Status text label — "Active" (green `#4ADE80`) or "Paused" (gray `#A1A1AA`) — **text only, no dot**
- **Bottom overlay** (`rgba(0,0,0,0.62)`): Item name + best offer (`$X` or "Finding..." if no `bestOffer`)
- **No platform badges, no unread dot, no price range display**

### `AddNewCard` (`components/AddNewCard.tsx`)
- Rendered **outside** the horizontal carousel, below it, full-width
- Always visible regardless of how many items exist in a section

### `StatusBadge` (`components/StatusBadge.tsx`)
- Theme-aware pill. Used in item detail header.

### `PlatformBadge` (`components/PlatformBadge.tsx`)
- Still defined but **not used** in conversations or chat headers (replaced by plain company name text)

---

## Data Model (`data/mockData.ts`)

### `Item`
```ts
interface Item {
  id: string;
  type: 'buy' | 'sell';
  name: string;
  description: string;
  condition: string;
  imageColor: string;
  targetPrice: number;
  minPrice?: number;
  maxPrice?: number;
  autoAcceptThreshold?: number;
  platforms: Platform[];
  status: 'active' | 'paused' | 'archived';
  quantity: number;
  negotiationStyle: 'aggressive' | 'moderate' | 'passive';
  replyTone: 'professional' | 'casual' | 'firm';
  bestOffer?: number;       // Current best offer — shown in card and overview
  marketData: MarketData[];
  conversations: Conversation[];
}
```

### `MarketData`
```ts
interface MarketData {
  platform: Platform;
  bestBuyPrice: number;   // Best (lowest) buy price on this platform
  bestSellPrice: number;  // Best (highest) sell price on this platform
  volume: number;         // Number of active listings
}
```

### `PLATFORM_NAMES`
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

## Navigation

- **Back button label**: "Back" (set globally in `_layout.tsx` via `headerBackTitle: 'Back'`)
- Routes: `index`, `settings`, `item/[id]`, `chat/[id]`
- `item/[id]` and `chat/[id]` use `headerShown: false` (custom headers)

---

## Key Design Rules

- **No colored status dots** anywhere — status is text-only ("Active" / "Paused") or themed badge
- **No wifi icons** in platform connection status
- **No decorative dots** in count pills
- **Profile access** via circular avatar button — no hamburger / gear icon on home
- **AddNewCard** always visible below carousel — not inside the scroll
- **Negotiation Style** uses stacked layout in settings to prevent overflow
- **Unread conversations** shown by bright/bold preview text — no dot
- **Archive** requires `Alert.alert` confirmation
- **Destructive actions** use `colors.destructive` and are visually separated from primary actions
- **Theme propagation**: all color values come from `useTheme().colors` — no hardcoded hex in components (exception: status text on image cards)
- **Touch targets**: minimum 44×44pt via `hitSlop` where visual size is smaller
- **Safe areas**: `SafeAreaView` with `edges` on every screen
