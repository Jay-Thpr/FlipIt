# UI Requirements

## Overview

A mobile marketplace agent app where users set up automated buy/sell agents across multiple platforms. The UI is dark-mode-first, professional, and data-forward — purpose-built for a power user who wants to monitor and manage deals at a glance.

---

## Design System

### Theme
The app uses a **dynamic theme system** (`contexts/ThemeContext.tsx`) with three modes: **Dark** (default), **Light**, and **System**. Dark mode is the primary design target.

### Style
**Dark professional** — neutral zinc palette with violet accent, high contrast, clean typography. Feels closer to Linear or a trading terminal than a consumer marketplace.

### Color Tokens (`constants/colors.ts`)

Two full token sets are defined: `DarkColors` and `LightColors`. Components consume colors via `useTheme().colors`.

#### Dark Mode (default)
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
| `foreground` | `#FAFAFA` | Primary text |
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
| `background` | `#F4F4F5` | Neutral off-white (not lavender) |
| `surface` | `#FFFFFF` | — |
| `textPrimary` | `#18181B` | Dark gray, not purple |
| `textMuted` | `#A1A1AA` | — |
| `statusBarStyle` | `dark` | — |

### Typography
**Font:** Inter (system default, all weights via React Native)
- App name / display: Inter 800, 24px, letterSpacing -0.5
- Section headers: Inter 700, 18px, letterSpacing -0.3
- Card item name: Inter 700, 13px (overlay), 14px (list)
- Price: Inter 800, 15px, letterSpacing -0.3
- Labels/captions: Inter 600, 11–13px
- Section labels (uppercase): Inter 700, 11px, letterSpacing 0.8

### Spacing
Strict 4/8pt system. Common values: 4, 8, 10, 12, 14, 16, 20, 24, 32, 48.

### Icons
Lucide (`lucide-react-native`) throughout. No emojis as icons. Standard size: 18–22pt. Small: 14–16pt. All icon-only buttons use `hitSlop` for 44×44pt touch targets.

### Platform Badges
Two color configs per platform (dark + light). Dark mode uses deep tinted backgrounds with lighter text. Light mode uses pastel backgrounds.

| Platform | Dark text | Dark bg | Light text | Light bg |
|----------|-----------|---------|------------|----------|
| eBay | `#FC8181` | `#3D0F0F` | `#E53935` | `#FEE2E2` |
| Depop | `#F472B6` | `#3D0A24` | `#D1156B` | `#FCE7F3` |
| Mercari | `#60A5FA` | `#0F1E3D` | `#1E40AF` | `#DBEAFE` |
| OfferUp | `#FBBF24` | `#3D2000` | `#D97706` | `#FEF3C7` |
| Facebook | `#60A5FA` | `#0F1E3D` | `#1877F2` | `#EFF6FF` |

### Status Badges
Theme-aware, always inline pill shape.

| Status | Dark bg | Dark text | Light bg | Light text |
|--------|---------|-----------|----------|------------|
| Active | `#052E16` | `#4ADE80` | `#DCFCE7` | `#15803D` |
| Paused | `#27272A` | `#A1A1AA` | `#F4F4F5` | `#71717A` |
| Archived | `#450A0A` | `#F87171` | `#FEE2E2` | `#DC2626` |

On image cards (where the badge sits over a colored background), use a `rgba(0,0,0,0.45)` pill with a colored dot + white text — not the surface-aware badge.

---

## Pages

---

### 1. Home Page (`app/index.tsx`)

The main dashboard. Gives the user an immediate read on all active buying and selling agents.

#### Header Bar
- `AgentMarket` brand name (primary color, Inter 800, 24px) + subtitle on the left
- Settings icon button (40×40, `surface` bg, `border` border, 12px radius) on the right → navigates to Settings

#### Layout
Two stacked sections: **Selling** (top) and **Buying** (bottom), each with a horizontal card carousel.

#### Section Header
Per section:
- Section title (Inter 700, 18px) + active count pill (`"N active"` with green dot) on the left
- Total agent count label (`"N agents"`) on the right
- No divider between sections — 24px top padding separates them

#### Item Card Carousel (`components/ItemCard.tsx`)
Horizontal `ScrollView` with `snapToInterval` per section. Card width = 44% of screen width (~2.3 cards visible). Cards snap to start alignment.

Each card:
- **Width**: 44% of screen width. **Height**: `width / 0.68` (portrait aspect ratio).
- **Background**: `item.imageColor` (colored placeholder; swap for `<Image>` when real images are available)
- **Watermark**: Large initial letter centered, `rgba(255,255,255,0.12)`, 120px, weight 900 — gives depth to placeholder
- **Status pill** (top-right, always visible over any image color):
  - `rgba(0,0,0,0.45)` background
  - Colored dot (`#4ADE80` active / `#A1A1AA` paused / `#F87171` archived)
  - White label text, 11px
- **Unread badge** (top-left): 9×9 purple dot when the item has unread conversations
- **Bottom overlay**: `rgba(0,0,0,0.62)` solid overlay containing:
  - Item name — white, Inter 700, 13px, max 2 lines
  - Price / price range — white, Inter 800, 15px
  - Row of `PlatformBadge` components (max 3 shown, `+N` overflow label)
- **Border radius**: 16px
- **Pressed state**: `activeOpacity={0.88}`
- Tapping navigates to Item Detail page

#### Add New Card (`components/AddNewCard.tsx`)
- Same dimensions as item cards (same `cardWidth / 0.68` height formula)
- `surface` background, dashed `border` border, 16px radius
- Centered: circle icon button (48×48) with `+` icon, "Add New" label, "Set up an agent" hint
- Always the last card in each section's carousel

#### Empty State
If a section has no items, the carousel contains only the Add New card.

---

### 2. Item Detail Page (`app/item/[id].tsx`)

Opened by tapping any item card. Full context on one item.

#### Header Bar
- Back arrow (38×38 button, `surface` bg, `border` border, 10px radius) → returns to Home
- Item name as title (truncated, Inter 700, 16px, `textPrimary`)
- `StatusBadge` (size `md`) on the right

#### Hero Image
Full-width colored block, 200px tall, `item.imageColor` background, giant watermark initial (72px, white 75% opacity). Replace with `<Image>` when real images are available.

#### Section: Overview
Card body (`surface` bg, `border` border, 14px radius) containing:
- Item name (Inter 700, 18px)
- Description (14px, `textSecondary`, lineHeight 20)
- Row of `MetaChip` components: Condition, Qty, Mode (Buy/Sell)

#### Section: Settings
Card body with labeled rows (label left, value/control right), separated by `border` dividers.

| Row | Control |
|-----|---------|
| Target Price | Static value |
| Min Acceptable | Static value (if set) |
| Max Acceptable | Static value (if set) |
| Auto-Accept Below | Static value (if set) |
| Negotiation Style | Static value |
| Reply Tone | Static value |
| Active Platforms | Comma-separated text |
| Auto-Relist | Live `Switch` component |

#### Section: Market Overview
Horizontal `ScrollView` of market cards. Each card (`surface` bg, `border` border, 12px radius):
- `PlatformBadge` (size `md`)
- Current price (Inter 800, 22px, `textPrimary`)
- Trend row: `TrendingUp`/`TrendingDown` icon + `%` change (colored `accent` or `destructive`)
- Volume label (11px, `textMuted`)

#### Section: Active Conversations
Card body with conversation rows separated by `border` dividers.

Each row:
- `PlatformBadge` (size `md`)
- Username (Inter 600, 14px) + purple unread dot if `conv.unread`
- Last message preview (1 line, `textMuted`)
- Timestamp + chevron (right side)

Tapping → Chat Log page. Empty state: centered muted text.

---

### 3. Chat Log Page (`app/chat/[id].tsx`)

Read-only conversation view.

#### Header Bar
- Back arrow → Item Detail
- Two-line center: item name (Inter 700, 15px) + `PlatformBadge` + `@username`
- Background: `surface`, bottom border

#### Info Banner
Slim `muted` banner below header: `"Log view only — all messages sent by your agent"` (centered, 11px, `textMuted`)

#### Message List (`FlatList`)
- Padding 16px horizontal and vertical
- Agent bubbles: right-aligned, `primary` background, `onPrimary` text, `borderBottomRightRadius: 4`
- Counterparty bubbles: left-aligned, `surface` background with `border`, `textPrimary` text, `borderBottomLeftRadius: 4`
- All bubbles: 16px radius, 14px text, lineHeight 20
- Timestamp below each bubble (`textMuted`, 11px)
- Empty state: centered muted text

---

### 4. Settings Page (`app/settings.tsx`)

App-wide settings, fully wired to the global theme context.

Navigation: gear icon on Home → Settings (Stack navigator with custom header using `background` color).

#### Appearance
Segmented theme picker (Light / Dark / System). **Selecting a theme immediately updates the entire app** via `ThemeContext.setTheme()`. Active option shows `surfaceRaised` bg + `primary` border + primary-colored label/icon. Default: **Dark**.

#### Account
Three rows in a card: Display Name, Email, Profile Photo. Each row: icon in `muted` rounded square + label + value + chevron.

#### Connected Platforms
One row per platform. Each row:
- Colored icon square (theme-aware: dark bg in dark mode)
- Platform name + username or "Not connected"
- API status dot (green = valid, red = expired/missing)
- Connected badge (`rgba` green pill) or Connect badge (`muted` pill with border)

#### Agent Behavior
- Auto-Reply toggle
- Response Delay row (tappable, value shown)
- Negotiation Style segmented control (Aggressive / Moderate / Passive) — `muted` track, `surface` active pill

#### Notifications
Four toggle rows with Lucide icons: New Message, Price Drop, Deal Closed, Listing Expired.

#### Usage
2×2 grid of stat tiles (`surface` bg, `border` border, 14px radius). Each tile: large number (Inter 800, 28px, `primary`) + label (12px, `textMuted`).

---

## Component Map

| Component | File | Notes |
|-----------|------|-------|
| `ItemCard` | `components/ItemCard.tsx` | Image card with overlay. Prop: `item`, `cardWidth`, `onPress` |
| `AddNewCard` | `components/AddNewCard.tsx` | Matches ItemCard dimensions. Prop: `cardWidth`, `onPress` |
| `StatusBadge` | `components/StatusBadge.tsx` | Theme-aware. Prop: `status`, `size` (`sm`\|`md`) |
| `PlatformBadge` | `components/PlatformBadge.tsx` | Theme-aware. Prop: `platform`, `size` (`sm`\|`md`) |
| `ThemeProvider` | `contexts/ThemeContext.tsx` | Wraps entire app in `_layout.tsx`. Exposes `useTheme()` |

---

## General UX Rules

- **Back navigation** always restores the previous scroll position.
- **Dark mode default**: app opens in dark mode; user can switch in Settings > Appearance.
- **Theme propagation**: all color values come from `useTheme().colors` — no hardcoded hex values in components.
- **Image placeholders**: all item "images" are currently `item.imageColor` colored views with a watermark initial. Replace `backgroundColor` with `<Image source={{ uri: item.imageUrl }} />` when backend provides URLs.
- **Destructive actions** require a confirmation dialog. Use `destructive` color for the confirm button.
- **Empty states** include explanation + action (Add New card or helper text).
- **All interactive elements** have a visible pressed state (`activeOpacity` or `Switch` feedback). Transitions: 150–300ms ease-out.
- **Touch targets**: minimum 44×44pt via `hitSlop` where visual size is smaller.
- **Safe areas**: `SafeAreaView` with `edges` prop on every screen. No interactive UI behind notch, status bar, or gesture bar.
- **Contrast**: `textPrimary` ≥4.5:1, `textSecondary`/`textMuted` ≥3:1, verified in both light and dark modes.
