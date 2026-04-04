# UI Requirements

## Overview

A mobile marketplace agent app where users set up automated buy/sell agents across multiple platforms. The UI should feel polished, professional, and data-forward — purpose-built for a power user who wants to monitor and manage deals at a glance.

---

## Design System

### Style
**Vibrant & Block-based** — bold, energetic, high color contrast, geometric shapes, modern. Every screen should feel intentional and structured, not cluttered.

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#7C3AED` | Primary actions, active states, key accents |
| `--color-on-primary` | `#FFFFFF` | Text/icons on primary backgrounds |
| `--color-secondary` | `#A78BFA` | Secondary UI elements, subtle highlights |
| `--color-accent` | `#16A34A` | CTAs, success states, deal-closed indicators |
| `--color-background` | `#FAF5FF` | Page backgrounds (light mode) |
| `--color-foreground` | `#4C1D95` | Primary text |
| `--color-muted` | `#ECEEF9` | Card backgrounds, dividers |
| `--color-border` | `#DDD6FE` | Borders, separators |
| `--color-destructive` | `#DC2626` | Errors, destructive actions |

Dark mode variants must be defined separately — do not invert light mode values.

### Typography
**Font:** Inter (all weights)
- Display/Headings: Inter 700, 32px+
- Section headers: Inter 600, 18–24px
- Body: Inter 400, 16px, line-height 1.5
- Labels/captions: Inter 500, 12–14px
- Numeric data (prices, counts): tabular figures to prevent layout shift

### Spacing
Use a strict 4/8pt spacing system. Common values: 4, 8, 12, 16, 24, 32, 48px.

### Icons
Use a single consistent SVG icon set (e.g. Lucide). No emojis as icons. All icon-only buttons must have an `aria-label`. Icon size: 20–24pt standard, 16pt small.

### Touch Targets
All tappable elements minimum 44×44pt. Use `hitSlop` where visual size is smaller.

### Animation
Micro-interactions: 150–300ms. Use `transform`/`opacity` only (no width/height animation). Respect `prefers-reduced-motion`. Exit animations ~60–70% of enter duration.

---

## Pages

---

### 1. Home Page

The main dashboard. Gives the user an immediate read on all active buying and selling agents.

#### Header Bar
- App name/logo on the left
- Settings icon (gear, SVG) on the right — tapping navigates to the Settings page
- Visible pressed state on the settings icon (opacity or scale 0.9)

#### Layout
- Two stacked sections: **Buying** (top) and **Selling** (bottom)
- Each section has a section header ("Buying" / "Selling") in Inter 600, 18px
- Horizontal scroll grid of cards within each section (or 2-column grid if screen width allows)
- Sections are visually separated with a 32px gap or a subtle divider

#### Item Card (Buy or Sell)
Each card is a solid block with rounded corners (12–16px radius), subtle shadow, and `--color-muted` background.

Contents:
- Item image (square thumbnail, top of card) or a placeholder with item initial
- Item name — Inter 600, 16px
- Target price or price range — Inter 700, tabular figures, accent-colored
- Status badge — pill shape: green (`--color-accent`) for Active, gray for Paused
- Row of small platform icons (SVG) at the bottom of the card showing which platforms it's active on
- Entire card is tappable → navigates to Item Detail page
- Pressed state: scale to 0.97, 150ms ease-out

#### Add New Card
- Same size and shape as item cards
- Centered `+` icon (24pt, `--color-primary`) with "Add New" label below
- Dashed border in `--color-border`
- Tapping opens the new item creation flow

#### Empty State (no items yet)
- If a section has no items, show only the Add New card plus a short helper text: "No active agents. Tap + to get started."

---

### 2. Item Detail Page

Opened when a user taps a buy or sell card. Full context on one item.

#### Header Bar
- Back arrow (left) — tapping returns to Home, preserving scroll position
- Item name as title (truncate with ellipsis if too long)
- Status toggle (Active / Paused) — pill toggle, right side of header

#### Section: Item Overview
- Item image (full-width or large square, top of page)
- Item name — Inter 700, 24px
- Description — Inter 400, 16px, line-height 1.6
- Condition label (e.g. "Used – Good") — muted text, 14px
- Quantity — "x3 units" or "Buying up to 2"

#### Section: Item Settings
Presented as a card-grouped settings list (similar to iOS Settings rows). Each row has a label on the left and a value/control on the right.

| Setting | Control Type |
|---------|-------------|
| Target Price | Editable text field (numeric keyboard) |
| Min Acceptable Price | Editable text field |
| Max Acceptable Price | Editable text field |
| Auto-Accept Threshold | Editable text field |
| Active Platforms | Multi-select toggle row (platform icons + label) |
| Negotiation Style | Segmented control: Aggressive / Moderate / Passive |
| Reply Tone | Dropdown or segmented: Professional / Casual / Firm |
| Auto-Relist | Toggle switch |
| Schedule Start | Date picker row |
| Schedule End | Date picker row |

Validation: show error inline below the field on blur. Required fields marked with a subtle asterisk. Numeric inputs use `inputmode="numeric"`.

#### Section: Market Overview
Per-platform cards in a horizontal scroll or stacked list. Each card shows:
- Platform name + SVG icon
- Current market price (large, tabular Inter 700)
- Volume / active listing count
- A subtle trend indicator (up/down arrow + % change) if available

#### Section: Active Conversations
List of people the agent is currently talking to, grouped by platform with a platform header row.

Each conversation row:
- Platform icon (16pt)
- Username/handle — Inter 500, 15px
- Last message preview — truncated to 1 line, muted text
- Timestamp — right-aligned, muted, 12px
- Unread badge (dot or count) if there are new messages

Tapping a row navigates to the Chat Log page.

Empty state: "No active conversations yet."

---

### 3. Chat Log Page

A read-only view of the conversation between the agent and one counterparty.

#### Header Bar
- Back arrow → returns to Item Detail, restoring scroll position
- Two-line title: item name (top, smaller) + platform + username (bottom, bold)

#### Chat Log
- Chronological message list, oldest at top, newest at bottom
- **Agent messages** (our side): right-aligned bubble, `--color-primary` background, white text
- **Counterparty messages**: left-aligned bubble, `--color-muted` background, `--color-foreground` text
- Timestamp below each message (or grouped by date with a centered date chip)
- Bubble corner radius: 16px, with the "tail" corner 4px on the sending side
- No compose or reply area — this is a log only
- System events (e.g. "Offer sent: $45", "Listing marked sold") shown as centered pills in muted style

#### Empty State
"No messages yet." centered in the log area.

---

### 4. Settings Page

App-wide settings. Must look complete and professional — not everything needs to be fully wired up, but it should feel like a real, polished product.

Navigation: accessible from the Home Page header settings icon. Uses a standard back arrow to return.

---

#### Appearance
| Setting | Control |
|---------|---------|
| Theme | Segmented control: Light / Dark / System Default |

---

#### Account
| Setting | Control |
|---------|---------|
| Profile photo | Tappable avatar with "Edit" overlay |
| Display name | Editable text row |
| Email address | Editable text row |

---

#### Platforms
Section header: "Connected Platforms"

For each supported marketplace (eBay, Facebook Marketplace, Craigslist, OfferUp, Depop, etc.):
- Platform logo/icon (SVG, 24pt)
- Platform name — Inter 500
- Connection status badge: "Connected" (green) or "Not Connected" (muted)
- If connected: account username shown in muted text below
- Connect / Disconnect button on the right (text button or chevron that opens an auth flow)
- API key status indicator where applicable (green dot = valid, red dot = expired/missing)

---

#### Agent Behavior
Section header: "Global Defaults" with a subheading: "These apply to all agents unless overridden per item."

| Setting | Control |
|---------|---------|
| Auto-reply | Toggle switch |
| Response delay | Stepper or dropdown: Instant / 1 min / 5 min / 15 min / 1 hr |
| Default negotiation style | Segmented: Aggressive / Moderate / Passive |

---

#### Notifications
Toggle rows, each with an icon (SVG), label, and toggle switch on the right:

| Notification | Default |
|---|---|
| New message received | On |
| Price drop detected | On |
| Deal closed | On |
| Listing expired | Off |

---

#### Usage
Displayed as a 2×2 stats grid. Each cell:
- Large number — Inter 700, 28px, `--color-primary`
- Label below — Inter 400, 13px, muted

| Stat | Label |
|------|-------|
| Active listings count | "Active Listings" |
| Messages this month | "Messages This Month" |
| Deals closed | "Deals Closed" |
| API calls used | "API Usage" |

---

## General UX Rules

- **Back navigation** always restores the previous scroll position and any open filters/state.
- **Loading states**: show a skeleton screen (shimmer) for any content that takes >300ms to load. Never show a blank screen.
- **Destructive actions** (archive, delete agent, disconnect platform) require a confirmation dialog before executing. Use `--color-destructive` for the confirm button.
- **Disabled controls** use 40% opacity + `cursor: not-allowed` (web) or non-interactive semantics (native). They must still be visually distinguishable.
- **Error messages** appear inline near the relevant field, state the cause, and suggest a fix. Never show a generic "Something went wrong."
- **Empty states** always include a short explanation and a clear action to resolve them.
- **All interactive elements** have a visible pressed/hover state. Transitions: 150–300ms ease-out.
- **Contrast**: primary text ≥4.5:1, secondary/muted text ≥3:1, in both light and dark modes.
- **Safe areas**: no interactive UI behind the notch, status bar, or gesture indicator bar.