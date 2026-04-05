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
**Dark professional** — minimal color palette, no unnecessary outlines, high contrast, clean typography. Feels closer to Linear or a trading terminal than a consumer marketplace.

### Color Philosophy
**3-4 colors per mode.** The palette is intentionally limited:
- **Primary** (violet) — brand, active states, CTAs
- **Accent** (green) — prices, success states
- **Neutral** (background/surface) — structure and hierarchy via shade differences, not borders
- **Destructive** (red) — errors, archive, sign out (minimal use)

**No outlines on cards.** Cards are differentiated from backgrounds by surface color alone. Dividers inside cards use a very subtle `divider` token (low-opacity white/black).

### Color Tokens (`constants/colors.ts`)

#### Dark Mode
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#8B5CF6` | Primary actions, active accents, brand |
| `onPrimary` | `#FFFFFF` | Text/icons on primary bg |
| `accent` | `#22C55E` | Success, prices, active states |
| `background` | `#09090B` | Page background |
| `surface` | `#151518` | Cards, elevated surfaces |
| `surfaceRaised` | `#1E1E22` | Active/pressed surface state |
| `muted` | `#1E1E22` | Subtle fills, icon backgrounds, inactive segments |
| `destructive` | `#EF4444` | Errors, destructive actions |
| `textPrimary` | `#FAFAFA` | Body text |
| `textSecondary` | `#A1A1AA` | Secondary labels |
| `textMuted` | `#63636E` | Hints, timestamps, counts |
| `divider` | `#ffffff0F` | Internal card dividers (very low opacity) |

#### Light Mode
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#7C3AED` | — |
| `accent` | `#16A34A` | — |
| `background` | `#F4F4F5` | Neutral off-white |
| `surface` | `#FFFFFF` | — |
| `surfaceRaised` | `#EDEDEF` | — |
| `textPrimary` | `#18181B` | Dark gray |
| `textMuted` | `#A1A1AA` | — |
| `divider` | `#0000000A` | — |

### Typography
**Font:** Inter (system default, all weights via React Native)
- App name: Inter 800, 20px, letterSpacing -0.5
- Section headers: Inter 700, 16px, letterSpacing -0.3
- Card item name: Inter 700, 15px
- Price / offer: Inter 800, 18px, letterSpacing -0.3, tabular-nums
- Labels/captions: Inter 600, 11–13px
- Section labels (uppercase): Inter 600, 11px, letterSpacing 0.8

### Spacing
Strict 4/8pt system. Common values: 4, 8, 10, 12, 14, 16, 20, 24, 32, 48.

### Icons
Lucide (`lucide-react-native`) throughout. No emojis as icons. Standard size: 14–20pt. All icon-only buttons use `hitSlop` for 44×44pt touch targets.

### Platform Colors
Two color configs per platform (dark + light). Dark mode uses deep tinted backgrounds with lighter text. Light mode uses pastel backgrounds.

| Platform | Dark text | Dark bg | Light text | Light bg |
|----------|-----------|---------|------------|----------|
| eBay | `#FC8181` | `#3D0F0F` | `#E53935` | `#FEE2E2` |
| Depop | `#F472B6` | `#3D0A24` | `#D1156B` | `#FCE7F3` |
| Mercari | `#60A5FA` | `#0F1E3D` | `#1E40AF` | `#DBEAFE` |
| OfferUp | `#FBBF24` | `#3D2000` | `#D97706` | `#FEF3C7` |
| Facebook | `#60A5FA` | `#0F1E3D` | `#1877F2` | `#EFF6FF` |

**Note:** Platform icons currently use text-based shortLabel placeholders (e.g. "eB", "Dp"). These will be replaced with official brand logo images in a future update.

### Status Badges (theme-aware, rounded rect with radius 6)

| Status | Dark bg | Dark text | Light bg | Light text |
|--------|---------|-----------|----------|------------|
| Active | `#052E16` | `#4ADE80` | `#DCFCE7` | `#15803D` |
| Paused | `surfaceRaised` | `textMuted` | `muted` | `textMuted` |
| Archived | `#450A0A` | `#F87171` | `#FEE2E2` | `#DC2626` |

---

## Pages

---

### 1. Home Page (`app/index.tsx`)

The main dashboard. Gives the user an immediate read on all active buying and selling agents.

#### Header Bar (surface background, extends to top of screen behind status bar)
- Left: `AgentMarket` brand name (textPrimary, Inter 800, 20px) + **agent cap counter pill** (`{current}/{limit}`, surface bg, textMuted, 12px tabular-nums). The limit is the plan cap (currently 10).
- Right: Circular avatar button (34×34, primary bg, initials "SS") → tapping opens a profile dropdown modal
- **Header uses `surface` bg** — `SafeAreaView` has `edges={['top']}` with surface color so the header blends seamlessly from the status bar down. Scroll content below uses `background` color.

#### Profile Dropdown Modal (semi-transparent overlay, top-right)
- User avatar + name + email row
- "Settings" menu item → navigates to `/settings`
- Divider
- "Sign Out" (destructive red)
- **No outline on the modal** — uses surface background on scrim

#### Layout
Two stacked sections: **Selling** (top) and **Buying** (bottom), each with:
- Section title (Inter 700, 16px) + **Add New button (+ icon in a small surface-bg square)** on the left — navigates to `/new-listing?type=sell` or `/new-listing?type=buy`
- **Merged count** on the right: `{active}/{total} active` (single text, textMuted)
- Horizontal scrollable carousel of `ItemCard` components (card width = 58% screen width)
- **No AddNewCard below the carousel** — the add button is inline with the section header

---

### 2. Item Detail Page (`app/item/[id].tsx`)

Opened by tapping any item card.

#### Header Bar
- Back arrow — bare, no box (36×36 touch area)
- Item name as title (Inter 700, 16px, truncated)
- `StatusBadge` on the right
- **No bottom border** — header blends into page

#### Header Bar (surface background, extends to top of screen)
- Same surface-bg-to-status-bar pattern as home page

#### Hero Strip
Compact metrics bar with accent stripe (3px, `primary` in dark / `muted` in light) at top:
- Three metrics side by side: **Best Offer** (accent green or "None"), **Target** (textPrimary), **Mode** (primary violet)
- Separated by subtle vertical dividers
- Surface background, no outline

#### Section: Photos
Positioned after the hero strip, before Overview. Uppercase label "PHOTOS (N)" with an inline "+ Add" button on the right.

**When photos exist:** Horizontal `ScrollView` of photo cards (150×150 images, surface bg, 12px radius). Each card shows:
- The photo image (cover fit)
- Position badge (bottom-left, semi-transparent black pill)
- Delete button (top-right, 28×28 circle with X icon, semi-transparent black)
- Below image: left/right ChevronLeft/ChevronRight reorder buttons (36×32, surfaceRaised bg)
- Disabled arrow opacity (0.3) for first/last items
- **No extra add card** at end of scroll — the "+ Add" button in the header is sufficient

**When no photos:** A tappable empty state (surface bg, rounded) with `+` icon, "Add photos for your listing" label, and a hint: "Photos are uploaded in order when the AI creates listings".

Photos are stored as an ordered `string[]` of URIs. The order is significant — the AI uploads them in this order when creating listings on platforms.

#### AI Agent Active Toggle
Standalone row below the photos section (surface bg, 12px radius). Shows "AI Agent Active" label + Switch. **Not inside the Settings card.**

#### Section: Overview
Uppercase section label + card body. **Description is stacked vertically** (label above, value below) to give long text room. Then a compact horizontal row for **Condition** and **Quantity** (no Mode — mode is shown in the hero strip only).

#### Section: Settings
Uppercase section label + card body:

| Row | Control |
|-----|---------|
| Target Price | Static value |
| Min Acceptable | Static value (if set) |
| Max Acceptable | Static value (if set) |
| Auto-Accept Below | Static value (if set) |
| Negotiation Style | Static value |
| Reply Tone | Static value |
| Active Platforms | Comma-separated company names |

#### Section: Market Overview
Horizontal `ScrollView` of market cards. Each card (surface bg, **no border**, 12px radius):
- Platform name
- Buy price + Sell price side by side with vertical divider
- Volume — "N listings"

#### Section: Active Conversations
Card body with conversation rows:
- Username (bold) + platform name as text (muted)
- Last message preview: **textPrimary + fontWeight 500** when unread, **textMuted** when read
- **Timestamp is also highlighted (textPrimary, fontWeight 600) when unread** — not just the message
- Chevron

#### Archive Listing (bottom)
- **No outline** — uses surface background with destructive-colored text
- Tapping triggers `Alert.alert` confirmation before archiving

---

### 3. Chat Log Page (`app/chat/[id].tsx`)

Read-only conversation view.

#### Header Bar
- Back arrow — bare, no box
- Center: `@username` (bold, 15px) + item name (muted subtitle, 12px)
- Right: Platform name as uppercase text
- **Surface background, no border**

#### Message List (`FlatList`)
- Agent bubbles: right-aligned, `primary` background, `onPrimary` text
- Counterparty bubbles: left-aligned, `surface` background, **no border**
- Timestamp below each bubble (`textMuted`, 11px)

---

### 4. New Listing Page (`app/new-listing.tsx`)

Full-screen form for creating a new buy or sell listing. Opened from the `+` button next to "Selling" or "Buying" on the home page. The `type` query param (`buy`/`sell`) sets the listing type.

#### Header Bar (surface background, extends to top of screen)
- Back arrow (bare, no box)
- Title: "New Buy Listing" or "New Sell Listing"
- Spacer on right (no button in header)

#### Form Sections (scrollable, background color)

1. **Photos** — Empty state with `+` icon + prompt text. When photos exist: horizontal scroll of 80×80 thumbnails with delete X overlays and position badges, plus "+ Add More" button below.

2. **Basic Information** — Name (required, text input), Description (multiline text input), Condition (segmented: New / Like New / Good / Fair / Poor), Quantity (number pad).

3. **Pricing** — Target Price (required, `$` prefix, decimal pad), Min Acceptable, Max Acceptable, Auto-Accept Threshold — all with `$` prefix.

4. **Platforms** — Checkbox list of all 5 platforms (eBay, Depop, Mercari, OfferUp, Facebook). At least one required. Uses custom checkbox (22×22, primary bg when selected with Check icon).

5. **Agent Settings** — AI Agent Active toggle, Negotiation Style (segmented: Aggressive / Moderate / Passive), Reply Tone (segmented: Professional / Casual / Firm).

#### Create Button
Full-width primary button at the bottom of the scroll content: "Create Listing". Validates: name required, target price required, at least one platform. Shows success alert then navigates back.

---

### 5. Settings Page (`app/settings.tsx`)

Navigation: avatar menu on Home → Settings (Stack navigator, back button labeled "Back").

#### Appearance
Segmented theme picker (Light / Dark / System). Default: **System**. Active option shows `surfaceRaised` bg. **No border on individual options** — active state uses background color alone.

#### Account
Three rows: Display Name, Email, Profile Photo (icon + label + value + chevron).

#### Platforms
One row per platform:
- Colored icon square (theme-aware) — **currently uses text placeholders, to be replaced with actual logos**
- Platform name + username (if connected), or "Not connected"
- Status: "Connected" (green badge) or "Connect" (muted bg badge, **no border**)

#### Default Agent Behavior
- Auto-Reply toggle
- Response Delay row
- Negotiation Style — stacked layout: label row above, full-width segmented selector below
- **Reply Tone** — same stacked layout as Negotiation Style, options: Professional / Casual / Firm. Acts as the global default for all new chats.

#### Notifications
Four toggle rows: New Message, Price Drop, Deal Closed, Listing Expired.

#### Usage
2×2 grid inside a card:
- Active Listings, Messages This Month, Deals Closed, API Usage
- Each tile: large number (Inter 800, 28px, `primary`, tabular-nums) + label

---

## Components

### `ItemCard` (`components/ItemCard.tsx`)
- **Photo preview** at the top — shows the first photo from `item.photos[]` (cover fit). Falls back to `imageColor` placeholder with initial letter when no photos exist.
- Status label overlaid on the photo (top-left, semi-transparent black pill): **"Active"** (accent green) or **"Paused"** (destructive red)
- Surface background, **no border/outline**
- Item name (Inter 700, 15px), content padding 14px with 10px gap
- Bottom row: Best Offer label + value (accent green, or "None" in textPrimary if no offer) | Target label + value
- Uses `tabular-nums` for price alignment

### `AddNewCard` (`components/AddNewCard.tsx`)
- **Compact icon-only button** (28×28, surface bg, 8px radius) with Plus icon
- Rendered **inline next to the section title** in the header, not below the carousel

### `StatusBadge` (`components/StatusBadge.tsx`)
- Theme-aware badge with radius 6. Used in item detail header.

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
  bestOffer?: number;
  photos: string[];           // Ordered array of photo URIs — first photo is the card thumbnail
  marketData: MarketData[];
  conversations: Conversation[];
}
```

### `MarketData`
```ts
interface MarketData {
  platform: Platform;
  bestBuyPrice: number;
  bestSellPrice: number;
  volume: number;
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
- Routes: `index`, `settings`, `item/[id]`, `chat/[id]`, `new-listing`
- `item/[id]`, `chat/[id]`, and `new-listing` use `headerShown: false` (custom headers)

---

## Key Design Rules

- **No outlines/borders on cards** — surface color differentiation only. Internal dividers use the `divider` token (very low opacity).
- **3-4 color palette** per mode: primary (violet), accent (green), neutral (bg/surface), destructive (red, minimal use)
- **No colored status dots** anywhere — status is text-only or themed badge
- **No platform names on item cards** — cards show only status, name, and prices
- **"None"** shown when no best offer exists
- **Unread conversation highlighting** applies to both the message preview AND the timestamp
- **New Agent button** is a compact + icon inline with section headers, not a separate card
- **Merged agent counts** — single `X/Y active` text on the right of each section header
- **Reply Tone** has a global default in Settings (professional/casual/firm), overridable per item
- **Profile access** via circular avatar button — no hamburger / gear icon on home
- **Theme propagation**: all color values come from `useTheme().colors` — no hardcoded hex in components (exception: status badge config, platform colors)
- **Touch targets**: minimum 44×44pt via `hitSlop` where visual size is smaller
- **Safe areas**: `SafeAreaView` with `edges` on every screen
- **Header surface pattern**: Pages with custom headers (home, item detail, chat, new-listing) use `SafeAreaView edges={['top']}` with `surface` bg so the header color extends behind the status bar, then `background` color for the scroll content below
- **Paused status color**: uses `destructive` (red), not gray
- **AI Agent toggle**: shown as standalone row below photos on item detail page, not inside the Settings card
- **Platform logos**: currently text-based placeholders, to be replaced with official brand assets
