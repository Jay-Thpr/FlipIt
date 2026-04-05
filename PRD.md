# PRD — Autonomous Resale Agent (FILLER) v4
**DiamondHacks 2026 | April 5–6 | UCSD**

---

## 1. Overview

A mobile-first autonomous resale agent that works from both sides of the secondhand market. Thrifters in-store scan items to instantly know if they're worth buying and get a ready-to-post listing. Buyers paste a link to any niche item and dedicated agents swarm resale platforms sequentially, find the best listings, and send optimized offer messages to haggle sellers down automatically.

**One-liner:** The secondhand market, but with AI doing all the work on both sides.

**Two modes:**
- **SELL** — scan something at Goodwill, know your margin, list it in one tap
- **BUY** — find something niche, agents hunt every resale platform and haggle people down for you

---

## 2. Goals

- Win: Browser Use (primary sponsor), Fetch.ai, Gemini, Enchanted Commerce (main track), Best AI/ML, Best UI/UX, Best Mobile Hack, Best .Tech Domain
- Demo works reliably in under 3 minutes — two 90-second arcs
- Every API genuinely load-bearing
- 10 registered Fetch.ai agents — explicitly maximizes Fetch.ai judging score
- Feels like a real product someone uses daily

---

## 3. Target Users

**Seller (thrift flipper):** Walks into Goodwill, sees something interesting, has no idea what it's worth. Currently: Googles manually, checks eBay sold listings by hand, takes bad photos, types listings. This replaces all of that in under 60 seconds in-store.

**Buyer (niche item hunter):** Wants a specific item — rare sneaker, vintage camera, limited streetwear. Currently: manually checks Depop, eBay, Mercari one by one, messages sellers hoping they'll budge, usually pays asking. This agent does all of that autonomously.

---

## 4. Core User Flows

The app is a persistent agent management dashboard. Users add items to buy or sell; the app configures an agent for each item that runs autonomously and surfaces results on the dashboard. Each item card shows real-time agent status and taps through to a detail view with settings, market data, and active conversations.

### SELL Flow
```
User opens app → taps "+" in Selling section → takes photo of item
        ↓
VisionAgent: identifies item (Gemini Vision) + clean photo (Nano Banana)
        ↓
EbayResearchAgent: pulls sold comps (Browser Use)
        ↓
PricingAgent: computes median price + profit margin (Gemini)
        ↓
DepopListingAgent: populates Depop form (Browser Use)
        ↓
Item card appears in Selling dashboard — shows profit margin + "Ready to Post"
User opens Item Detail → reviews Depop form preview → taps Post (manual final step)
```

### BUY Flow
```
User opens app → taps "+" in Buying section → pastes link or describes item
        ↓
DepopSearchAgent: finds active Depop listings (Browser Use)
        ↓
EbaySearchAgent: finds active eBay listings (Browser Use)
        ↓
MercariSearchAgent: finds active Mercari listings (Browser Use)
        ↓
OfferUpSearchAgent: finds active OfferUp listings (Browser Use) [best effort]
        ↓
RankingAgent: scores + ranks all listings (Gemini)
        ↓
NegotiationAgent × N: sends one optimized offer per seller (Browser Use, once per seller)
        ↓
Item card appears in Buying dashboard — shows best price found + offer statuses
User opens Item Detail → sees ranked listings, market overview, active conversations per seller
```

---

## 5. Agent Architecture

### 5.1 The Orchestration Layer

**ASI:One is the orchestrator.** This is Fetch.ai’s own LLM — not a custom agent you build. ASI:One discovers your registered agents on Agentverse and routes natural-language tasks to them. Your job is building the specialist agents, registering them, and implementing the Chat Protocol. **ASI:One handles coordination** across the multi-agent graph for the sponsor story and judging.

**Mobile app (Expo) path:** The app connects to **FastAPI**, which runs an in-process pipeline (`backend/orchestrator.py`) that executes the **same ten agents, contracts, and sequencing** as the uAgent layer: SELL/BUY pipelines, SSE progress, and session state (`POST /sell/start`, `POST /buy/start`, `GET /stream/{session_id}`). Think of it as **one agent system, two front doors** — ASI:One for discovery and natural-language orchestration on Agentverse; FastAPI for low-latency, demo-stable HTTP/SSE on the phone.

**Summary:** ASI:One orchestrates the agent network; FastAPI mirrors that execution for the mobile product surface without changing the roster or the Fetch.ai narrative.

### 5.2 Full Agent Roster — 10 Agents

All agents: local Python uAgents, running on Render, registered on Agentverse via Mailbox, implementing Chat Protocol, discoverable by ASI:One.

| # | Agent | Mode | Responsibility | Key APIs |
|---|---|---|---|---|
| 1 | VisionAgent | SELL | Item identification + clean photo | Gemini Vision, Nano Banana |
| 2 | EbayResearchAgent | SELL | eBay sold comp scraping | Browser Use |
| 3 | PricingAgent | SELL | Median price + profit margin | Gemini, Python |
| 4 | DepopListingAgent | SELL | Depop form population | Browser Use |
| 5 | DepopSearchAgent | BUY | Active Depop listing search | Browser Use |
| 6 | EbaySearchAgent | BUY | Active eBay listing search | Browser Use |
| 7 | MercariSearchAgent | BUY | Active Mercari listing search | Browser Use |
| 8 | OfferUpSearchAgent | BUY | Active OfferUp listing search | Browser Use |
| 9 | RankingAgent | BUY | Score + rank all listings | Gemini |
| 10 | NegotiationAgent | BUY | Generate + send one offer per seller | Browser Use, Gemini |

### 5.3 SELL Sequencing
```
VisionAgent → EbayResearchAgent → PricingAgent → DepopListingAgent
```
Strictly sequential. Each agent completes fully before the next fires. EbayResearchAgent output feeds PricingAgent; PricingAgent output feeds DepopListingAgent.

### 5.4 BUY Sequencing
```
DepopSearchAgent → EbaySearchAgent → MercariSearchAgent → OfferUpSearchAgent
        → RankingAgent
        → NegotiationAgent (×N, once per target seller)
```
**FastAPI BUY pipeline (today):** Search agents run **sequentially** in code — one platform step after another. Sequential-but-fast in demo: each platform search is often 10–20 seconds, total search phase on the order of ~60 seconds. Results aggregate into `previous_outputs`, then RankingAgent, then NegotiationAgent.

**Fetch chat path:** The Fetch bridge may fan out the four marketplace searches **in parallel** before ranking/negotiation. When documenting or demoing, state which path you are using.

### 5.5 Fetch.ai Integration — Full Detail

**Registration:** All 10 agents run locally on Render as uAgents. Each registers on Agentverse via the Mailbox feature. Mailbox buffers messages during any brief downtime and delivers them when agent reconnects. Once registered, each agent shows as Active in Agentverse Marketplace.

**Chat Protocol:** Every agent implements `uagents_core.contrib.protocols.chat` — receives `ChatMessage`, sends `ChatAcknowledgement`, processes, returns `ChatMessage` with results.

**Discoverability:** All 10 agents discoverable by ASI:One via Agentverse search. ASI:One can route user natural language requests to any of them directly.

**Deliverables:**
- 10 Agentverse profile URLs (one per agent)
- ASI:One Chat session URL demonstrating agents working through ASI:One
- README.md per agent with name, address, capability description
- `![tag:innovationlab]` badge in each README

**Fetch.ai judging story:** 10 distinct registered agents, genuine multi-agent coordination, Browser Use inside agent logic, **ASI:One as the orchestration layer** (discovery + task routing across agents). FastAPI implements the parallel mobile path with the same agents. Directly hits "Quantity of Agents Created" and "multi-agent collaboration" judging criteria.

---

## 6. Feature Specifications

### 6.1 VisionAgent (SELL)

**Input:** Camera photo (base64, sent via Chat Protocol)

**Step 1 — Gemini Vision**
- Identify: brand, product name, model/variant, condition (excellent/good/fair)
- Output confidence score — shown in UI
- If confidence < 70%: surface correction field, pipeline pauses

**Step 2 — Nano Banana**
- Generate clean white-background product photo from raw input
- Output: listing-ready image URL
- Before/after shown side-by-side in UI

**Output:** `{ item_name, brand, model, condition, confidence, clean_photo_url }`

---

### 6.2 EbayResearchAgent (SELL)

**Input:** `{ item_name, brand, model, condition }` from VisionAgent

**Browser Use task:**
- Navigate to eBay sold listings
- Search `"[brand] [model]"` with sold + condition filter
- Wait for results to render (explicit selector wait, not fixed timeout)
- Extract per listing: sold price, date sold, condition, listing title
- Filter: last 90 days only, condition match only
- Cap at 20 results
- Headed Chromium + playwright-stealth

**Fallback:** If eBay blocks after 30s timeout → emit `fallback_triggered` SSE event → MercariResearchAgent logic fires instead (same agent, different task string)

**Output:** `{ comps: [{ price, date, condition, title }], platform, raw_count }`

---

### 6.3 PricingAgent (SELL)

**Input:** Comps from EbayResearchAgent + item details from VisionAgent

**Logic:**
- Remove outliers (>2 std deviations from mean)
- Compute median sold price from filtered set
- Condition multiplier: excellent ×1.05, good ×1.00, fair ×0.85
- Thrift cost: $8 default (editable in UI)
- Shipping: $5 flat default
- Depop fee: 10%
- Profit = `median_price × condition_multiplier - shipping - (median_price × 0.10) - thrift_cost`
- Gemini generates 2-sentence listing description from item details

**Output:** `{ recommended_price, profit_margin, median_price, comp_table, listing_description }`

---

### 6.4 DepopListingAgent (SELL)

**Input:** VisionAgent output + PricingAgent output + clean_photo_url

**Browser Use task:**
- Open Depop in pre-warmed logged-in session
- Navigate to listing creation
- Populate form sequentially (fields appear conditionally):
  1. Upload clean photo via file input
  2. Select category → subcategory
  3. Fill title: `[Brand] [Model] - [Condition]`
  4. Fill description: from PricingAgent
  5. Set price: recommended_price
  6. Select condition
  7. Fill size if applicable
- Pause at submit — do NOT click post
- Screenshot populated form

**Output:**
```python
{
    "form_screenshot_b64": str,          # base64 PNG of the populated form
    "listing_preview": {
        "title": str,
        "price": float,
        "description": str,
        "condition": str,
        "clean_photo_url": str,
    },
    "draft_url": str | None,             # Depop draft URL if draft was saved; None otherwise
    "summary": str,
}
```

**Draft sync:** Agent attempts to save as draft before stopping. If draft save succeeds, `draft_url` is the web draft URL and the mobile app deep-links to `depop://selling/drafts`. If draft save fails, `draft_url` is `None` and the app falls back to showing the screenshot + opening `depop://sell`.

**Implementation note (backend today):** The live schema may still expose `form_screenshot_url` and related placeholders until real capture lands; see `BACKEND-CODEBASE-PROBLEMS.md` P0. The **target** shape above is what the app and agents should converge on.

---

### 6.5 DepopSearchAgent (BUY)

**Input:** Item name/description (extracted from pasted link or natural language)

**Browser Use task:**
- Navigate to `depop.com/search/?q=[query]`
- Wait for listing grid to render
- Extract top 15 listings: price, condition, seller username, listing URL, date posted, seller review count
- Headed Chromium + playwright-stealth

**Output:** `{ platform: "depop", listings: [{ price, condition, seller, url, date, reviews }] }`

---

### 6.6 EbaySearchAgent (BUY)

**Input:** Same query as DepopSearchAgent

**Browser Use task:**
- Navigate to eBay active listings (Buy It Now filter)
- Search with condition filter
- Extract top 15 listings: price, condition, seller username, listing URL, seller feedback score
- Headed Chromium + playwright-stealth

**Output:** `{ platform: "ebay", listings: [{ price, condition, seller, url, feedback_score }] }`

---

### 6.7 MercariSearchAgent (BUY)

**Input:** Same query

**Browser Use task:**
- Navigate to `mercari.com/search/?keyword=[query]`
- Extract top 15 listings: price, condition, seller username, listing URL, seller rating
- Lower bot detection than eBay — more reliable

**Output:** `{ platform: "mercari", listings: [...] }`

---

### 6.8 OfferUpSearchAgent (BUY)

**Input:** Same query

**Browser Use task:**
- Navigate to `offerup.com/search/?q=[query]`
- Best effort — 30 second hard timeout
- Extract whatever listings render before timeout
- High bot detection risk — treat as nice-to-have

**Failure mode:** Returns empty list + `{ status: "blocked" }`. Pipeline continues normally. Frontend shows "OfferUp unavailable" badge rather than crashing.

**Output:** `{ platform: "offerup", listings: [...], status: "success" | "blocked" }`

---

### 6.9 RankingAgent (BUY)

**Input:** Aggregated listings from all 4 search agents

**Logic:**
- Flatten + deduplicate (same seller + similar price = duplicate)
- Score each listing (0-100):
  - Price vs median: 40% weight (lower = better)
  - Condition: 30% weight (excellent > good > fair)
  - Seller credibility: 20% weight (review count / feedback score)
  - Recency: 10% weight (newer = better)
- Flag haggle targets: listings >15% above platform median with active seller
- Gemini generates one-line summary per top 10 listing
- Return top 10 ranked

**Output:** `{ ranked_listings: [{ ...listing, score, haggle_flag, summary }], median_price }`

---

### 6.10 NegotiationAgent (BUY) — called once per seller

**Input:** Single listing `{ platform, seller, url, price, condition }` + `{ median_price }` from RankingAgent

**Step 1 — Gemini offer generation:**
- Calculate offer: 15-25% below listing price, floor at median
- Generate platform-appropriate message:
  - Polite, specific, reasoned
  - References market data without being aggressive
  - Example: "Hi! Love this piece. Similar ones have sold for around $[median] recently — would you consider $[offer]? Happy to pay right away."

**Step 2 — Browser Use offer sending:**
- Navigate to listing URL
- Open seller message UI
- Type and send generated message
- Confirm sent status

**Output:** `{ seller, platform, listing_url, offer_price, message_sent, status: "sent" | "failed" }`

---

## 7. Mobile App Specification

### 7.1 Stack
- React Native (Expo)
- NativeWind (Tailwind for React Native)
- `react-native-sse` for SSE real-time agent feed
- Python FastAPI backend via REST

### 7.2 Design System

**Style:** Vibrant and block-based — bold, high contrast, geometric, modern.

**Color palette:**
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#7C3AED` | Primary actions, active states, accents |
| `--color-on-primary` | `#FFFFFF` | Text/icons on primary |
| `--color-secondary` | `#A78BFA` | Secondary elements, subtle highlights |
| `--color-accent` | `#16A34A` | CTAs, success, deal-closed |
| `--color-background` | `#FAF5FF` | Page backgrounds (light mode) |
| `--color-foreground` | `#4C1D95` | Primary text |
| `--color-muted` | `#ECEEF9` | Card backgrounds, dividers |
| `--color-border` | `#DDD6FE` | Borders, separators |
| `--color-destructive` | `#DC2626` | Errors, destructive actions |

Dark mode variants defined separately — do not invert light mode values.

**Typography:** Inter across all weights. Headings 700/32px+, section headers 600/18–24px, body 400/16px, labels 500/12–14px. Numeric data uses tabular figures.

**Spacing:** Strict 4/8pt grid — values: 4, 8, 12, 16, 24, 32, 48px.

**Icons:** Single consistent SVG set (e.g. Lucide). No emoji icons. Icon-only buttons require `aria-label`. Standard size: 20–24pt.

**Touch targets:** 44×44pt minimum. Use `hitSlop` where visual size is smaller.

**Animation:** 150–300ms, `transform`/`opacity` only. Respect `prefers-reduced-motion`. Exit ~60–70% of enter duration.

### 7.3 Screen Structure

**Home Screen (Dashboard)**
- Header: app logo left, settings gear icon right
- Two stacked sections: **Buying** (top) and **Selling** (bottom), each with an Inter 600/18px section header
- Horizontal-scroll card grid per section
- **Item card:** rounded corners (12–16px), `--color-muted` background, subtle shadow. Contains: item thumbnail (or initial placeholder), item name (600/16px), target price or best found price (700 tabular accent-colored), status badge (Active = `--color-accent` green, Paused = gray pill), row of platform SVG icons. Entire card tappable → Item Detail. Press state: scale 0.97, 150ms ease-out.
- **Add New card:** same size, `+` icon centered (24pt `--color-primary`), "Add New" label, dashed `--color-border` border. Tapping opens item creation flow (camera for SELL, text input for BUY).
- Empty state per section: Add New card + "No active agents. Tap + to get started."

**Item Creation — SELL** (4 screen states)

**State 1 — Camera Screen:** Full-screen camera viewfinder, "Point at item" helper text, tap to capture.

**State 2 — Agent Feed Screen:** Appears immediately after photo taken.
- Left/top: agent cards with status + live log lines. Vision card activates first, shows item name + confidence as it resolves. Before/after photo strip appears after VisionAgent.
- Right/bottom: empty "Analyzing..." state → eBay comp table fades in after EbayResearchAgent → profit margin number + trend badge + velocity chip appear after PricingAgent.

**State 3 — Listing Review Screen:** Triggered by the **`listing_review_required`** SSE event (authoritative). The backend may also emit legacy **`draft_created`** for compatibility — **ignore it for UX state** if both appear; bind UI to `listing_review_required` and `GET /result` → `sell_listing_review`. Full replacement of agent feed. Contents top-to-bottom:
1. ✓ "Review your listing" (pipeline is **paused** until the user decides)
2. Before/after photo row (raw → clean Nano Banana) when available
3. Generated title + description
4. Price + estimated profit
5. Trend badge + velocity chip when present
6. Depop form screenshot (scrollable) — target: `form_screenshot_b64`; until implemented, URL or placeholder per backend
7. **Primary actions** — call **`POST /sell/listing-decision`** with JSON `{ "session_id", "decision": "confirm_submit" | "revise" | "abort", "revision_instructions"? }`:
   - **Post / confirm** — `confirm_submit` (runs submit step; then `listing_submitted` or failure events)
   - **Request changes** — `revise` + required instructions (max **2** revisions; review window **15 minutes**, refreshed after each successful revise)
   - **Abort** — `abort` (cleanup + `pipeline_complete`)
8. **"Open Depop"** secondary CTA — attempts `depop://selling/drafts` if `draft_url` present, else `depop://sell` / `https://www.depop.com/sell/`.
9. "Copy listing details" — copies title, description, price, condition to clipboard.

**State 4 — Error State:** Shows which step failed, partial results collected, "Try again" button.

**Item Creation — BUY**
- Text input: paste link or describe item
- Submit → BUY pipeline starts
- Agent activity bottom sheet shows 4 platform search agents firing sequentially with platform badges

**Item Detail Page**
Opened by tapping any item card.
- Header: back arrow (restores scroll position), item name as title, Active/Paused toggle (pill, right)
- **Item Overview:** large item image, name (700/24px), description (400/16px), condition label, quantity
- **Item Settings** (card-grouped iOS-style rows):
  - Target Price, Min/Max Acceptable Price, Auto-Accept Threshold — editable numeric fields
  - Active Platforms — multi-select toggle (platform icon + label)
  - Negotiation Style — segmented: Aggressive / Moderate / Passive
  - Reply Tone — segmented: Professional / Casual / Firm
  - Auto-Relist — toggle
  - Schedule Start / End — date picker rows
- **Market Overview:** per-platform cards (horizontal scroll or stacked) showing platform name + icon, current market price (large tabular 700), listing volume, trend indicator (up/down + % change)
- **Active Conversations:** list grouped by platform. Each row: platform icon, username (500/15px), last message preview (1 line muted), timestamp (right-aligned 12px muted), unread badge. Tapping → Chat Log. Empty state: "No active conversations yet."

**SELL Result (within Item Detail)**
- Before/after photo strip (raw vs. clean Nano Banana image)
- Comp table: sold prices from eBay, filtered and ranked
- Profit margin hero number (large, `--color-accent`)
- Depop form preview — fully populated, **review loop**: user confirms via **`POST /sell/listing-decision`** (not a blind single "Post" without backend contract)
- CTAs aligned with `confirm_submit` / `revise` / `abort` and SSE follow-up (`listing_submitted`, `pipeline_complete`, etc.)

**BUY Result (within Item Detail)**
- Ranked listing cards: platform badge, price, condition, score, haggle flag
- "Send Offers" CTA → NegotiationAgent fires per flagged seller
- Per-seller offer tracker: status badge (Sent / Replied / Accepted)

**Chat Log Page**
Read-only conversation log between agent and one seller/buyer.
- Header: back arrow → Item Detail (restores scroll), two-line title (item name top, platform + username bottom bold)
- Agent messages: right-aligned bubble, `--color-primary` bg, white text
- Counterparty messages: left-aligned bubble, `--color-muted` bg, `--color-foreground` text
- Timestamps below each message (or centered date chips between groups)
- System events (e.g. "Offer sent: $45") as centered muted pills
- No compose area — read-only log
- Empty state: "No messages yet."

**Settings Page**
Accessible from home header gear icon.
- **Appearance:** Light / Dark / System Default segmented control
- **Account:** profile photo (tappable with Edit overlay), display name, email
- **Connected Platforms:** per platform (eBay, Depop, Mercari, OfferUp) — logo, name, Connected/Not Connected badge, account username if connected, Connect/Disconnect control, API key status indicator
- **Global Defaults:** Auto-reply toggle, Response delay (Instant / 1 min / 5 min / 15 min / 1 hr), Default negotiation style
- **Notifications:** New message received (on), Price drop detected (on), Deal closed (on), Listing expired (off)
- **Usage stats (2×2 grid):** Active Listings, Messages This Month, Deals Closed, API Usage — each cell: large 700/28px `--color-primary` number + 400/13px muted label

### 7.4 General UX Rules

- Back navigation always restores previous scroll position and open filters/state
- Loading: skeleton shimmer for any content >300ms to load. Never blank screen.
- Destructive actions (delete agent, disconnect platform) require confirmation dialog with `--color-destructive` confirm button
- Disabled controls: 40% opacity + non-interactive semantics
- Error messages: inline near field, state cause, suggest fix — no generic "Something went wrong"
- Empty states: always include short explanation + clear action
- All interactive elements have visible pressed/hover state, 150–300ms ease-out
- Contrast: primary text ≥4.5:1, muted text ≥3:1, both light and dark
- Safe areas: no interactive UI behind notch, status bar, or gesture indicator bar

### 7.5 Agent Activity Feed (pipeline in progress)

Shown as an animated bottom sheet during pipeline execution (both SELL and BUY item creation flows).
- One row per agent: name, status (idle / active / complete / error), live summary line
- Active agent: pulsing animation
- Complete agent: green checkmark + one-line result
- Error agent: red indicator + fallback note

### 7.6 SSE Event Types

**Canonical source:** `backend/orchestrator.py` and `API_CONTRACT.md`. Event names use **snake_case** (underscores).

**Core lifecycle (all pipelines):**

```
pipeline_started   { input, mode }
agent_started      { agent_name, attempt, mode }   # shape may include step/pipeline per payload
agent_retrying     { agent_name, attempt, max_attempts }
agent_completed    { agent_name, summary, output }
agent_error        { agent_name, attempt, max_attempts, error, category }
pipeline_complete  { mode, pipeline, outputs }
pipeline_failed    { error, partial_result, ... }
pipeline_resumed   # sell correction and listing-decision resume paths
```

**Vision pause (when implemented end-to-end):** `vision_low_confidence` — session may stay `running` until `POST /sell/correct`.

**SELL listing review (authoritative handoff from Agent Feed → Listing Review UI):**

- **`listing_review_required`** — includes `review_state`, `allowed_decisions`, listing preview fields, `output` / Depop payload. **Use this** to transition to State 3.
- **`draft_created`** — **legacy compatibility** from the listing agent; do not treat as the sole source of truth if `listing_review_required` is present.

**After `POST /sell/listing-decision`:** `listing_decision_received`, `listing_submission_approved`, `listing_submit_requested`, `listing_submitted` or `listing_submission_failed`, `listing_revision_requested`, `listing_revision_applied`, `listing_submission_aborted`, `listing_abort_requested`, `listing_aborted`, `listing_review_expired`, cleanup events, then `pipeline_complete` or `pipeline_failed` as applicable.

**Product insight:** Vision and pricing **do not** emit separate `vision_result` / `pricing_result` event types today — the UI should read **`agent_completed`** and inspect `output` (and `step` in the event payload) for each stage.

Frontend updates in real time on each event. No polling. Fallback: poll `GET /result/{session_id}` if SSE drops (result includes `events`, `sell_listing_review`, and `status`).

---

## 8. Backend Specification

### 8.1 Stack
- Python (FastAPI)
- uAgents framework (Fetch.ai) — all 10 agents
- Browser Use (Playwright + playwright-stealth)
- Hosted on Render (paid tier — free tier memory insufficient for headed Chromium)

### 8.2 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/sell/start` | POST | Accepts photo (base64), triggers SELL pipeline, returns `{ session_id }` |
| `/buy/start` | POST | Accepts `{ query }` or `{ url }`, triggers BUY pipeline, returns `{ session_id }` |
| `/stream/{session_id}` | GET | SSE stream — stays open until `pipeline_complete` event |
| `/result/{session_id}` | GET | Full final result for session |
| `/health` | GET | Backend health check |

### 8.3 Session Management
- Unique session ID per pipeline invocation (UUID)
- Results stored in-memory dict keyed by session ID
- SSE stream closes on `pipeline_complete` or 5-minute timeout
- No database needed for hackathon

### 8.4 Agent-to-Backend Communication
- Each agent emits SSE events to FastAPI via internal HTTP POST to `/internal/event/{session_id}`
- FastAPI buffers events per session and streams them to connected mobile SSE client
- Agents run as separate async processes alongside FastAPI on same Render instance

### 8.5 Browser Use Configuration
- All Browser Use tasks: headed Chromium + playwright-stealth
- Separate browser context per agent invocation (no shared state)
- Realistic randomized delays between actions (500ms-2000ms)
- Hard timeout per agent: 30 seconds
- SELL agents: sequential, one context at a time
- BUY search agents: sequential, one context at a time (sequential-but-fast)

### 8.6 Agentverse Registration
- All 10 agents: local uAgents registered via Agentverse Mailbox
- Each agent runs with `mailbox=True` flag
- Mailbox buffers messages during any brief unavailability
- Each agent registered at startup, stays Active as long as Render instance is running
- Agent addresses logged to README.md for Fetch.ai deliverables

---

## 9. Demo Script

**Pre-demo setup:**
- All 10 agents running on Render, Active on Agentverse
- Depop seller account: logged in, session warm
- OfferUp + Depop buyer accounts: logged in for messaging
- SELL demo item: Air Jordan 1s / AirPods / North Face jacket (20+ eBay sold comps, clear margin)
- BUY demo item: specific niche sneaker with active listings on Depop + Mercari + eBay
- Test seller account pre-staged to show offer response during BUY demo
- Backend health check confirmed

**Demo Arc 1 — SELL (90 seconds):**
1. Open app to dashboard. "You just found this at Goodwill. Is it worth buying?"
2. Tap "+" in Selling section → camera opens. Take photo.
3. Agent activity sheet rises: VisionAgent fires — item identified, clean product photo appears. "It knows exactly what this is."
4. EbayResearchAgent: comp table populates in the sheet. "Real sold prices from eBay."
5. PricingAgent: profit margin appears. "After fees, you make $Y."
6. DepopListingAgent: form populated. Item card appears in Selling dashboard — "Ready to Post."
7. Tap item card → Item Detail. Show Depop form screenshot + comp table + profit margin. "One tap to post."

**Demo Arc 2 — BUY (90 seconds):**
1. Tap "+" in Buying section. "You want these specific Jordan 1s but refuse to pay asking price."
2. Paste product link. Submit.
3. Agent activity sheet rises: DepopSearchAgent, EbaySearchAgent, MercariSearchAgent fire sequentially — platform badges animate. "Checking every resale platform."
4. RankingAgent: ranked listing cards appear in the sheet, haggle targets flagged. "Found 31 listings. These 5 are below market."
5. Item card appears in Buying dashboard. Tap it → Item Detail → "Send Offers" CTA.
6. NegotiationAgent fires per flagged seller. Offer tracker shows "Sent" badges.
7. Open Chat Log for one seller — show pre-staged reply. "One already replied."

**Fallbacks:**
- eBay blocks SELL → fallback event emits, Mercari fires, demo continues
- OfferUp blocked BUY → "OfferUp unavailable" badge, other 3 platforms show
- No live seller reply → pre-staged test account reply visible

---

## 10. Track Submission Requirements

| Track | Requirement | How Satisfied |
|---|---|---|
| Browser Use | Core functionality relies on Browser Use | SELL: eBay scraping + Depop form. BUY: 4 platform searches + offer sending. 6 of 10 agents use Browser Use. |
| Fetch.ai | Agents registered on Agentverse, Chat Protocol, ASI:One session URL | 10 registered agents, Chat Protocol on all, ASI:One session URL as deliverable, Mailbox registration |
| Gemini | Gemini API as reasoning backbone | Gemini Vision (VisionAgent), Gemini reasoning (PricingAgent description, RankingAgent summaries, HagglingAgent offer generation) |
| Enchanted Commerce | Revolutionize commerce | Full two-sided autonomous resale marketplace — buying and selling both automated end-to-end |
| Best AI/ML | Push AI/ML boundaries | 10-agent orchestration, vision model, semantic ranking, generative negotiation |
| Best UI/UX | Beautiful and intuitive UX | Persistent dashboard, item detail with market data + conversations, chat log, settings — full product feel with polished design system |
| Best Mobile Hack | Standout mobile app | Full Expo React Native — camera integration, in-store use case, real mobile UX |
| Best .Tech Domain | Register .tech domain | Register day one |

---

## 11. Technical Risks + Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| eBay bot detection (SELL research) | High | playwright-stealth + headed mode + delays; Mercari fallback built into EbayResearchAgent |
| OfferUp bot detection (BUY search) | High | Hard 30s timeout, returns empty gracefully, frontend shows "unavailable" badge — not a crash |
| Depop form photo upload via Browser Use | High | Test file input specifically first — known edge case. Pre-stage photo in fixed path. |
| New account messaging restrictions | High | Verify Depop + OfferUp messaging works on new accounts TONIGHT before hackathon |
| Render memory (headed Chromium) | High | Use paid Render tier. Each agent spins up/tears down context — don't keep 10 browsers open simultaneously |
| Agent Mailbox registration latency | Medium | Register all agents at hackathon start, verify Active status before building anything else |
| react-native-sse stability | Medium | Test SSE polyfill on both iOS + Android early. Have polling fallback via `/result` endpoint. |
| HagglingAgent message flagged as spam | Medium | Gemini generates unique message per seller. Don't reuse identical text across sends. |
| BUY search returning no results | Medium | Cap minimum — if all platforms return <3 results combined, surface "no listings found" gracefully |
| Pre-staged seller reply timing | Low | Control test account yourself. Have reply pre-typed and ready to send at right moment in demo. |

---

## 12. Out of Scope

- Actual Depop listing submission (pause at submit — intentional)
- Real-time push notifications for offer replies
- Multi-item batch scanning (SELL)
- Facebook Marketplace (too aggressive for demo reliability)
- Authentication / user accounts
- Database persistence
- Price history over time
- In-app payments

---

## 13. Build Priority Order

**Must have — demo blockers (build first):**
1. Expo app shell: Home dashboard, Item Detail, camera (SELL), text input (BUY)
2. FastAPI backend + SSE infrastructure
3. VisionAgent — Gemini Vision identification
4. EbayResearchAgent — sold comp scraping
5. PricingAgent — margin calculation
6. Agent activity bottom sheet in UI (SSE-driven)
7. DepopSearchAgent + EbaySearchAgent + MercariSearchAgent

**Should have:**
8. DepopListingAgent — Depop form population
9. RankingAgent — scored listing feed in Item Detail
10. NegotiationAgent — offer sending
11. Chat Log page per seller conversation
12. Nano Banana — clean photo generation
13. All 10 agents registered on Agentverse via Mailbox

**Nice to have:**
14. OfferUpSearchAgent
15. Mercari fallback inside EbayResearchAgent
16. Market Overview cards per platform in Item Detail
17. Settings page (appearance, platforms, global defaults, notifications, usage stats)
18. Offer status tracker with pre-staged reply demo

---

## 14. Team Split (Recommended)

| Person | Owns |
|---|---|
| 1 | Fetch.ai + agent architecture: uAgents setup, Mailbox registration, Chat Protocol, all agent scaffolding, ASI:One integration |
| 2 | Browser Use: EbayResearchAgent, DepopListingAgent, all 4 BUY search agents, NegotiationAgent — Browser Use specialist |
| 3 | AI pipeline: VisionAgent (Gemini Vision + Nano Banana), PricingAgent, RankingAgent (Gemini), offer message generation |
| 4 | Mobile frontend: Expo app, camera, SSE feed, agent activity bottom sheet, Home dashboard, Item Detail (settings + market overview + conversations), Chat Log, Settings, SELL and BUY result views |

FastAPI backend split between persons 1 and 2 — 1 owns session management + SSE infrastructure, 2 owns Browser Use execution endpoints.

---

## 15. Hackathon Checklist

**Accounts:**
- [ ] Create Depop seller account — verify listing creation works immediately (no identity gate)
- [ ] Create Depop buyer account — verify messaging works on new account
- [ ] Create OfferUp account — verify messaging works on new account
- [ ] Create test seller account on Depop — will use to pre-stage offer reply during BUY demo

**Demo validation:**
- [ ] Select SELL demo item — verify 20+ eBay sold comps in last 90 days
- [ ] Verify SELL demo item has >$20 profit margin at $8 thrift cost
- [ ] Select BUY demo item — verify active listings on Depop + eBay + Mercari simultaneously
- [ ] Pre-type offer reply in test seller account — ready to send during demo

**API credentials:**
- [ ] Gemini API key
- [ ] Nano Banana API key
- [ ] Agentverse account created

**Environment:**
- [ ] Browser Use installed, basic navigation test passes
- [ ] playwright-stealth installed, tested on eBay sold listings
- [ ] Expo CLI installed, blank app running on device
- [ ] Render account set up (paid tier confirmed)
- [ ] Register .tech domain