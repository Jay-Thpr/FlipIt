# UI Requirements — AgentMarket Frontend

Last updated: 2026-04-04

---

## Overview

A mobile marketplace agent app where users set up automated buy/sell agents across multiple resale platforms. Dark professional aesthetic — minimal color palette, no outlines, high contrast. Feels like a trading terminal.

---

## Design System

### Theme
Dynamic theme system (`contexts/ThemeContext.tsx`): **Light**, **Dark**, **System** (default).

### Color Philosophy
**3 colors per mode.** No purple anywhere in the UI (only the avatar placeholder uses `primary`).
- **Accent** (green) — prices, success, active switches, CTA buttons, checkboxes
- **Neutral** (background/surface) — hierarchy via shade differences, not borders
- **Destructive** (red) — errors, archive, sign out, paused status

**No outlines on cards.** Cards use `surface` bg on `background`. Internal dividers use very low-opacity `divider` token.

### Color Tokens (`constants/colors.ts`)

#### Dark Mode
| Token | Value | Usage |
|-------|-------|-------|
| `accent` | `#22C55E` | Prices, active states, switches, CTAs |
| `background` | `#09090B` | Page background |
| `surface` | `#151518` | Cards, headers |
| `surfaceRaised` | `#1E1E22` | Active segments, pressed states |
| `muted` | `#1E1E22` | Icon backgrounds, inactive segments |
| `destructive` | `#EF4444` | Errors, destructive actions, paused |
| `textPrimary` | `#FAFAFA` | Body text |
| `textSecondary` | `#A1A1AA` | Secondary labels, setting icons |
| `textMuted` | `#63636E` | Hints, timestamps |
| `divider` | `#ffffff0F` | Card dividers |

#### Light Mode
| Token | Value |
|-------|-------|
| `accent` | `#16A34A` |
| `background` | `#F4F4F5` |
| `surface` | `#FFFFFF` |
| `textPrimary` | `#18181B` |

### Typography
- Logo wordmark: Inter 700, 17px, letterSpacing -0.3
- Section headers: Inter 700, 16px
- Card item name: Inter 700, 15px
- Prices: Inter 800, 18px, tabular-nums
- Labels: Inter 600, 11-13px
- Section labels (uppercase): Inter 600, 11px, letterSpacing 0.8

### Icons
Lucide (`lucide-react-native`). No emojis. 14-20pt. `hitSlop` for 44pt touch targets.
- Setting icons use `textSecondary` (neutral gray, not colored)
- Active segment text uses `textPrimary` (not accent)
- `+` buttons use `textPrimary` (white)

---

## Pages

### 0. Auth Pages (`app/auth/`)

Two screens sharing the same layout and design language. Vertically centered content, 24px horizontal padding.

#### Sign In (`auth/sign-in.tsx`)

- **Hero:** Centered `<Logo>` (size 28) + "Welcome back" heading (24px, 700) + subtitle (15px, textSecondary)
- **OAuth buttons:** Full-width surface-bg cards (48px tall, 12px radius), icon + label centered
  - "Continue with Google" — multi-color Google "G" SVG icon
  - "Continue with Apple" — Apple logo SVG, iOS only (`Platform.OS === 'ios'`)
- **Divider:** Horizontal line + "or" text (textMuted) + horizontal line
- **Email/password form:**
  - Visible labels above inputs (13px, 600, textSecondary)
  - Inputs: 48px tall, surface bg, 12px radius, 16px padding
  - Password field: show/hide toggle (text button, right-aligned inside input)
  - Error text below fields (13px, destructive color)
- **Sign In button:** Full-width, accent bg, white text (16px, 700), 48px tall, 12px radius
  - Loading state: button disabled at 0.7 opacity, ActivityIndicator replaces text
- **Footer:** "Don't have an account? Sign Up" — accent-colored link navigates to `auth/sign-up`
- **Keyboard:** `KeyboardAvoidingView` with `behavior='padding'` (iOS) / `'height'` (Android)

#### Sign Up (`auth/sign-up.tsx`)

Same layout as Sign In with these differences:
- **Hero:** "Create your account" + "Set up your AI agents in minutes"
- **Form fields:** Name (autoCapitalize words), Email, Password (min 6 chars hint in placeholder)
- **Button:** "Create Account"
- **Footer:** "Already have an account? Sign In" — navigates back

#### Auth Design Rules
- No header bar — full-screen centered layout on background color
- OAuth buttons use surface bg (no outlines, consistent with card pattern)
- SVG icons only (Google multi-color, Apple uses textPrimary)
- Inputs have no borders — surface bg on background creates hierarchy
- All touch targets meet 48px minimum height
- `textContentType` and `autoComplete` set for system autofill support
- Transitions: sign-in uses `fade`, sign-up uses `slide_from_right`

---

### 1. Home Page (`app/index.tsx`)

#### Header (surface bg, extends to status bar)
- Left: `<Logo>` component — SVG double-chevron "A" mark + "AgentMarket" wordmark
- Right: Avatar button (34×34, primary bg placeholder)
- `SafeAreaView edges={['top']}` with surface color

#### P&L Chart
Below header, in the scroll content. Rendered by `<PnLChart>` component:
- Hero "Net Profit" number (24px bold, green when positive, red when negative)
- SVG bezier area chart with gradient fill
- Three subtle grid lines with Y-axis labels
- Period tabs: 1W / 1M / 3M / ALL (surfaceRaised active state)
- Data: cumulative P&L from completed trades that have `initialPrice` set
- Empty state: "Set initial prices on listings to track profit"

#### Recent Trades Button
Below the chart. Surface card, 12px radius, full width:
- "Recent Trades" text (textPrimary, 14px, 600 weight) + ChevronRight (textMuted)
- Tapping navigates to `/trades` full-screen page

#### Selling / Buying Carousels
Two sections below the trades button:
- Section title (16px, 700) + `AddNewCard` button (28×28 surface square with `+` icon) on left
- `{active}/{total} active` count on right (textMuted)
- Horizontal snap carousel of `ItemCard` components (58% screen width)

#### Profile Menu (Modal)
- Avatar+name+email row → tappable, navigates to `/settings` (Account)
- Platforms → `/settings/platforms`
- Agent Defaults → `/settings/agents`
- Notifications → `/settings/notifications`
- Sign Out (destructive)

---

### 2. Item Detail Page (`app/item/[id].tsx`)

#### Header (surface bg, extends to status bar)
- Back arrow (bare), item name + "Buying"/"Selling" subtitle, AI Agent Active switch

#### Hero Metrics Strip (surface bg, continuous with header)
- Best Offer (28px bold, accent green or textPrimary "None")
- Target (18px, textPrimary)
- Separated by vertical divider

#### Photos Section
- "PHOTOS (N)" label + "+ Add" button
- 150×150 photo cards with position badge, delete X overlay, left/right reorder arrows
- Subtle opacity animation on reorder (80ms dip to 0.5, 120ms restore)

#### Details Card (merged Overview + Settings)
Single card with:
- Description (stacked vertically)
- 2×2 info grid: Condition, Quantity, Negotiation, Tone
- Price settings: Initial Price (if set), Target, Min/Max, Auto-Accept
- Platforms (comma-separated names)

#### Market Overview
Horizontal scroll of cards: platform name, buy/sell prices side by side, volume

#### Conversations
Rows with circular avatar initials, username, platform, message preview (bold when unread), timestamp

#### Archive
Text-only button at bottom, destructive color

---

### 3. Chat Log Page (`app/chat/[id].tsx`)

- Back arrow, `@username` + item name, platform name on right
- Agent bubbles: accent green bg, white text
- Other party bubbles: surface bg, textPrimary

---

### 4. Recent Trades Page (`app/trades.tsx`)

Full-screen scrollable list of completed trades. Custom header (surface bg extending to status bar, back arrow, "Recent Trades" title).

Each trade row:
- Item name (14px, 600 weight)
- Type · Platform · Date (12px, textMuted)
- Price on right (15px, 700, tabular-nums)
- Profit below price when `initialPrice` exists: `+$X` (accent) or `-$X` (destructive)

---

### 5. New Listing Page (`app/new-listing.tsx`)

Full-screen form, `?type=buy|sell` param. Custom header (surface bg, back arrow, title).

Sections: Photos, Basic Info (name, description, condition, quantity), Pricing (initial price optional with hint, target, min/max, auto-accept), Platforms (checkboxes, accent bg when selected), Agent Settings (AI toggle, negotiation style, reply tone).

"Create Listing" button at bottom (full-width, accent bg).

---

### 6. Settings Pages (`app/settings/`)

Four separate pages, each with custom header (surface bg, back arrow):

- **Account** (`settings/index.tsx`) — Appearance (Light/Dark/System), account info, usage stats
- **Platforms** (`settings/platforms.tsx`) — Platform connection list
- **Agent Defaults** (`settings/agents.tsx`) — Auto-reply, response delay, negotiation style, reply tone
- **Notifications** (`settings/notifications.tsx`) — Toggle rows

---

## Components

### `ItemCard`
- Photo preview (first photo, or imageColor placeholder)
- Name + Best Offer / Target prices
- **Paused overlay**: `rgba(0,0,0,0.45)` dark scrim over entire card (not opacity fade)

### `Logo`
- SVG double-chevron "A" mark (react-native-svg) + "AgentMarket" wordmark
- Theme-aware (uses textPrimary)

### `PnLChart`
- Accepts `data: PnLDataPoint[]` prop
- SVG bezier curve with gradient fill, period tabs, hero P&L number

### `MasterAgentFAB`
- Persistent floating action button linking to the ASI:One master agent
- **Visibility:** All screens for authenticated users. Hidden on auth screens. Hidden if backend returns no agent address.
- **Position:** `absolute`, bottom: 24, right: 16. Above all screen content (`zIndex: 999`).
- **Size:** 56×56 circular (`borderRadius: 28`)
- **Background:** `#7C3AED` (fixed, not theme-dependent)
- **Icon:** `asi-one-logo-modified.png` from assets, 30×30, white `tintColor`
- **Shadow:** `elevation: 6`, `shadowOffset: {0, 3}`, `shadowOpacity: 0.3`, `shadowRadius: 4`
- **Pressed state:** opacity 0.8, scale 0.95
- **Accessibility:** `accessibilityLabel="Chat with AI agent on ASI:One"`, `accessibilityRole="button"`
- **Behavior:** Opens `https://asi1.ai/chat?agent=<address>` via `Linking.openURL()`. Address fetched from `GET /config`.

### `AddNewCard`
- 28×28 surface square with `+` icon (textPrimary)

---

## Data Model

### Item
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
  initialPrice?: number;      // What user paid — enables profit tracking
  platforms: Platform[];
  status: 'active' | 'paused' | 'archived';
  quantity: number;
  negotiationStyle: 'aggressive' | 'moderate' | 'passive';
  replyTone: 'professional' | 'casual' | 'firm';
  bestOffer?: number;
  photos: string[];
  marketData: MarketData[];
  conversations: Conversation[];
}
```

### Navigation
Routes: `auth/sign-in`, `auth/sign-up`, `index`, `settings/*`, `item/[id]`, `chat/[id]`, `new-listing`, `trades`, `trade/[id]`

### Key Rules
- No purple in UI (only avatar placeholder)
- No outlines/borders on cards
- Paused = dark scrim overlay, not opacity
- Settings icons are neutral gray (textSecondary)
- Active segments use textPrimary, not accent
- + buttons are textPrimary (white)
- Chat agent bubbles are accent green
- Header surface-bg-to-status-bar pattern on all custom-header pages
