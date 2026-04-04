# PRD — Autonomous Resale Swarm Mobile (FILLER)
**DiamondHacks 2026 | April 5–6 | UCSD**

---

## 1. Overview

A mobile-first autonomous resale assistant built in React Native. A user snaps or uploads a photo of a thrift store item, the app identifies it, researches live resale comps, estimates margin, and helps the user decide whether the item is worth selling. If the numbers look good, the user taps `Sell This Item` and a Fetch.ai-powered agent swarm takes over: marketplace bots scrape live competitor listings, determine the lowest competitive price above a profit floor, generate haggle responses, and prepare marketplace drafts for the user to approve.

**One-liner:** Snap it. Price it. Let the swarm sell it.

---

## 2. Goals

- Win: Browser Use (primary sponsor), Fetch.ai, Gemini, Enchanted Commerce (main track), Best AI/ML, Best UI/UX, Best Mobile Hack, Best .Tech Domain
- Deliver a mobile demo that feels native, fast, and reliable in under 3 minutes
- Make every API load-bearing, with no decorative integrations
- Center the core user decision: is this item worth selling right now?
- Make the post-decision selling workflow explicitly multi-agent and Fetch-native
- Price items to become the lowest competitive listing without violating a minimum profit threshold
- Feel like a real resale product, not a hackathon toy

---

## 3. Target User

Someone who thrift-flips from their phone while shopping in person. They walk through Goodwill or Salvation Army, see an item, take a quick picture, and want an immediate answer on whether they should buy and resell it. Today they manually search comps, estimate fees in their head, compare competing listings across apps, and later create listings by hand. This app compresses that workflow into a mobile decision tool plus a selling swarm that prices and prepares listings competitively.

---

## 4. Core User Flow

```
User opens mobile app and takes or uploads a photo
        ↓
Vision Agent identifies item and condition (Gemini Vision)
        ↓
Research Agent pulls sold comps from eBay (Browser Use)
        ↓
Pricing Agent computes median price, fees, and profit margin
        ↓
Sell Item component shows:
- recommended listing price
- estimated profit
- confidence + comp breakdown
- Sell This Item / Skip This Item decision
        ↓
If user taps Sell This Item:
Swarm Orchestrator dispatches marketplace agents
        ↓
Marketplace Scout Agents scrape active competitor listings
        ↓
Price Optimizer Agent sets lowest competitive live price above floor
        ↓
Negotiation + Listing Agent prepares haggle strategy and marketplace draft(s)
        ↓
Mobile app shows swarm actions, pricing strategy, and Ready to Post state
```

---

## 5. Agent Architecture

### 5.1 Agent Breakdown

Six distinct uAgents registered on Agentverse, each implementing the Chat Protocol:

| Agent | Responsibility | Key APIs |
|---|---|---|
| Vision Agent | Item identification and condition detection | Gemini Vision |
| Research Agent | eBay sold comp scraping and data extraction | Browser Use |
| Pricing Agent | Median price calculation, fee breakdown, profit margin | Python logic, Gemini |
| Swarm Orchestrator Agent | Coordinates downstream selling agents and shared state | Fetch.ai uAgents |
| Marketplace Scout Agents | Scrape live active listings across marketplaces | Browser Use |
| Negotiation + Listing Agent | Generates haggle logic and populates draft(s) up to submit | Browser Use, Gemini |

### 5.2 Sequencing

```
Vision Agent → Research Agent → Pricing Agent → Sell Item component
                                                ↓
                                   Swarm Orchestrator Agent
                                                ↓
                            [Marketplace Scouts + Price Optimizer]
                                                ↓
                              Negotiation + Listing Agent(s)
```

- Vision completes before research begins
- Pricing starts after research returns comps
- The `Sell Item` component is the human decision checkpoint
- The selling swarm begins only if the user explicitly chooses to sell
- Marketplace scouts can run in parallel across target platforms
- Price optimization computes the lowest competitive live listing that still clears the profit floor
- Negotiation logic prepares counteroffers or haggle scripts per marketplace
- Each agent emits status events to the mobile frontend as it progresses

### 5.3 Fetch.ai Integration

- All agents are built with the uAgents framework in Python
- Agents are registered on Agentverse with Chat Protocol implemented
- ASI:One is used for judge-facing validation and direct invocation of the swarm
- The mobile app is the consumer-facing product surface
- Agentverse profile URLs and ASI:One chat session URL are generated as Fetch.ai deliverables

---

## 6. Feature Specifications

### 6.1 Vision Agent

**Input:** Raw thrift-store photo from camera or gallery

**Behavior:**
- Identify brand, product name, model or variant, and condition (`excellent`, `good`, `fair`)
- Output a confidence score
- If confidence is below 70%, prompt the user to correct the item name before continuing

**Output:** `{ item_name, brand, model, condition, confidence }`

### 6.2 Research Agent

**Input:** Item identification from Vision Agent

**Browser Use behavior:**
- Navigate to eBay sold listings
- Search `[brand] [model] [condition]`
- Extract sold price, sold date, condition, and result count
- Filter to the last 90 days and condition-matching items
- Wait for dynamic content before extraction
- Run in headed mode with stealth protections enabled

**Fallback:** If eBay blocks or fails, fall back to Mercari sold listings using the same extraction schema

**Output:** `{ comps: [{ price, date, condition, title }], raw_count }`

### 6.3 Pricing Agent

**Input:** Vision output plus comps from Research Agent

**Logic:**
- Remove outliers greater than 2 standard deviations from the mean
- Compute median sold price from filtered comps
- Apply condition adjustment: `excellent` (+5%), `good` (0%), `fair` (-15%)
- Compute thrift cost using a default of $8, editable by the user in the app
- Compute profit margin: `recommended_price - shipping_estimate - depop_fee - thrift_cost`
- Depop fee assumption: 10%
- Shipping estimate: flat $5 default for lightweight items

**Output:**
- Recommended listing price
- Estimated profit margin
- Fee breakdown
- Comp table for display in the app

### 6.4 Marketplace Scout Agents

**Input:** Item details, recommended price, and user-confirmed `Sell This Item` action

**Browser Use behavior:**
- Open target marketplaces in separate browser contexts
- Search active listings for the same or nearest comparable item
- Extract current listing price, shipping, condition, title, recency, and platform
- Normalize comparable active listings into a shared schema
- Return the lowest competitive live listings per marketplace

**Output:** `{ active_listings: [{ marketplace, title, price, shipping, condition, url }] }`

### 6.5 Price Optimizer Agent

**Input:** Sold comps, active listings, thrift cost, and required profit floor

**Logic:**
- Set a minimum profit floor, defaulting to $15 and editable by the user
- Identify the cheapest relevant live listing on each marketplace
- Undercut the cheapest relevant listing by a small configurable increment
- Never recommend a price below the profit floor
- If the market is too compressed, return `skip_listing` or `hold_price` instead of forcing a race to zero

**Output:**
- Best marketplace to list on first
- Recommended live listing price
- Undercut delta
- Whether the item qualifies for aggressive pricing, hold pricing, or skip

### 6.6 Negotiation + Listing Agent

**Input:** Item details, optimized price, marketplace selection, and user-confirmed `Sell This Item` action

**Behavior:**
- Generate a marketplace-specific title and description
- Prepare negotiation rules: minimum accepted offer, ideal counteroffer, and response templates
- If supported in the demo flow, prepare haggle messages or counteroffer text for incoming buyer offers
- Open the target marketplace in a pre-warmed logged-in session
- Populate the listing draft sequentially:
  1. Upload listing photo
  2. Select category
  3. Fill title
  4. Fill description
  5. Set optimized price
  6. Select condition
  7. Fill size if applicable
- Pause at submit and never post automatically
- Capture a screenshot of the populated draft for the mobile UI

**Output:** Draft preview screenshot, negotiation settings, and `ready_to_post` status

### 6.7 Sell Item Component

This is the core mobile decision component and the main user-facing conversion moment.

**Purpose:**
- Help the user decide whether the item is worth buying and reselling
- Turn research output into a clear `sell / skip` action
- Gate the selling swarm behind explicit user intent

**Displayed data:**
- Item identity and confidence
- Recommended listing price
- Estimated profit in large, high-contrast type
- Thrift cost field, editable in place
- Profit floor field, editable in place
- Fee breakdown: sale price, Depop fee, shipping, net profit
- Comp summary: median, lowest, highest, number of relevant sold listings
- Live market summary: cheapest active listing by marketplace
- Quick verdict badge: `Strong Flip`, `Borderline`, or `Skip`

**Primary actions:**
- `Sell This Item` starts the agent swarm
- `Skip This Item` ends the flow without starting listing automation
- `Adjust Cost` recalculates margin instantly
- `Adjust Floor` recalculates swarm pricing instantly

---

## 7. Mobile App Specification

### 7.1 Stack

- React Native with Expo
- Expo Router for navigation
- TypeScript
- NativeWind for styling
- React Native Reanimated for motion
- SSE client for live agent status updates
- Python backend via REST API

### 7.2 Core Screens

**1. Capture Screen**
- Full-screen camera or gallery picker
- Single primary action: take photo or upload photo
- Lightweight framing guide to encourage clean item shots

**2. Analysis Screen**
- Agent activity feed at the top
- Item photo and identification state
- Progressive comp loading and pricing updates
- Transition into the Sell Item component as soon as pricing completes
- Expand into swarm activity once the user starts selling

**3. Draft Screen**
- Shown only after `Sell This Item`
- Swarm timeline showing scout, optimize, negotiate, and draft steps
- Marketplace draft screenshot preview
- Listing summary: marketplace, title, price, condition, haggle floor
- `Ready to Post` state shown prominently

### 7.3 Interaction Model

- The app should be usable one-handed in a thrift store aisle
- Important numbers are thumb-reachable and visually obvious
- The estimated profit is the hero metric
- The cheapest competitive live price above the profit floor is the key selling metric
- Motion should clarify progression between capture, analysis, and sell decision
- The user should never need to type before seeing whether an item is worth selling

### 7.4 Sell Item UX

The `Sell Item` component lives near the bottom of the Analysis Screen as a sticky action card once pricing is available.

**Component structure:**
- Header with item name and confidence
- Profit hero number
- Recommended listing price
- Inline thrift cost editor
- Inline profit floor editor
- Comp carousel or compact table
- Active marketplace price strip
- Decision badge
- Two large buttons: `Sell This Item` and `Skip`

**Why it matters:**
- This is the product's core value, not the draft generation alone
- It makes the app useful even if the user never posts a listing
- It cleanly supports the demo fallback: even if listing automation breaks, the app still answers the resale decision and proposes a swarm pricing strategy

### 7.5 Real-Time Updates

- Backend emits `agent_started`, `agent_log`, `agent_completed`, and `agent_error`
- The app subscribes to a session-specific event stream
- Agent states update live without polling, including per-agent swarm progress
- If the stream drops, the app retries and can restore state via the result endpoint

---

## 8. Backend Specification

### 8.1 Stack

- Python with FastAPI
- uAgents framework
- Browser Use with Playwright
- Hosted on Render or similar hackathon-friendly infra

### 8.2 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/upload` | POST | Accepts mobile photo upload, triggers Vision Agent, returns session ID |
| `/stream/{session_id}` | GET | SSE stream of agent status events |
| `/result/{session_id}` | GET | Returns current or final session results |
| `/sell/{session_id}` | POST | Confirms user intent to sell and triggers the Fetch swarm |
| `/reprice/{session_id}` | POST | Recomputes margin after thrift cost adjustment |
| `/swarm/config/{session_id}` | POST | Updates target marketplaces, undercut delta, and profit floor |

### 8.3 Session Management

- Each upload creates a unique session ID
- Session state is stored in memory for the hackathon
- Results include image metadata, comps, active listings, pricing output, negotiation settings, and draft status

### 8.4 Browser Use Configuration

- Headed Chromium with stealth protections
- Separate browser contexts for research, marketplace scouts, and listing
- Depop session is pre-warmed and logged in before demo time
- Listing actions run only after the mobile app sends explicit sell confirmation
- Marketplace scout sessions can run in parallel for speed

---

## 9. Demo Script

**Pre-demo setup:**
- Depop account is logged in and session is warm
- Demo item is something easy to identify with abundant comps
- Backend is already running
- Mobile build is installed on device or simulator

**Demo arc:**

1. Open the mobile app and show the camera-first landing screen.
2. Take or upload a photo of a demo item found at Goodwill.
3. Vision Agent identifies the item and condition.
4. Research and pricing complete, then the Sell Item component appears.
5. Show the hero profit number, live market floor, and explain whether the item is worth flipping.
6. Tap `Sell This Item`.
7. The Fetch swarm fans out across marketplaces, finds the cheapest live competitor, and recommends the best price above the profit floor.
8. The listing agent fills the marketplace draft and returns a `Ready to Post` preview plus haggle settings.

**Fallback if eBay blocks:** Use Mercari fallback and continue the demo.

**Fallback if listing automation fails:** End on the Sell Item component and swarm pricing dashboard. The resale decision workflow remains complete and useful.

---

## 10. Track Submission Requirements

| Track | Requirement | How We Satisfy It |
|---|---|---|
| Browser Use | Core functionality must rely on Browser Use agents interacting with the web | Sold-comp research, active marketplace scouting, and draft creation all depend on Browser Use |
| Fetch.ai | Agent registration, Chat Protocol, ASI:One demo | The selling flow is explicitly swarm-based and coordinated by Fetch.ai agents |
| Gemini | Gemini must be load-bearing | Gemini Vision handles item identification and condition |
| Enchanted Commerce | Build a standout commerce experience | Mobile resale assistant for real-time flipping and competitive marketplace selling |
| Best AI/ML | Strong AI or ML depth | Multi-agent orchestration, vision, live market analysis, and pricing optimization |
| Best UI/UX | Beautiful and intuitive product UX | Mobile-first flow, live swarm feedback, clear sell decision component |
| Best Mobile Hack | Standout mobile experience | React Native app designed for on-the-go thrift shopping |
| Best .Tech Domain | Register a .tech domain | Register on day one |

---

## 11. Technical Risks + Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| eBay bot detection | High | Stealth mode, realistic delays, Mercari fallback |
| Marketplace anti-automation friction | High | Limit demo to draft creation, pre-warm sessions, and show swarm logs even if one platform fails |
| Depop form changes | Medium | Pre-map draft flow for one demo category |
| Mobile network instability | Medium | Session-based resume via `/result` and SSE reconnect |
| Depop upload edge cases | Medium | Test image upload handling before demo day |
| Over-undercutting harms margin | Medium | Enforce editable profit floor and hard stop below threshold |
| Live haggling is not uniformly supported | Medium | Use generated counteroffer templates and marketplace-specific negotiation settings as the demo baseline |
| Gemini misidentification | Medium | Show confidence and allow correction before research |
| New Depop account restrictions | High | Verify account readiness before the event |

---

## 12. Out of Scope

- Automatic final posting to Depop
- Fully autonomous buyer messaging on every marketplace
- Multi-item batch scanning
- User authentication
- Database persistence
- Native marketplace integrations beyond the Browser Use listing flow
- Guaranteed automatic cross-posting to multiple marketplaces

---

## 13. Build Priority Order

**Must have:**
1. React Native capture and upload flow
2. Vision Agent with Gemini item identification
3. Research Agent with eBay sold comps
4. Pricing Agent with profit calculation
5. Sell Item component with editable thrift cost
6. Swarm orchestrator with at least one marketplace scout
7. Live mobile session updates

**Should have:**
8. Price optimizer with undercut logic and profit floor
9. Negotiation + listing agent for marketplace draft population
10. Mercari fallback
11. Fetch.ai registration and ASI:One validation

**Nice to have:**
12. Local history of scanned items
13. Push notification when draft is ready
14. Multi-marketplace sell recommendations

---

## 14. Pre-Hackathon Checklist

- [ ] Create and verify Depop account
- [ ] Confirm Depop draft creation works for a new account
- [ ] Pick a demo item with 20+ sold comps in the last 90 days
- [ ] Verify target item has meaningful resale profit
- [ ] Get Gemini API key
- [ ] Install and validate Browser Use
- [ ] Create Agentverse account and review Chat Protocol docs
- [ ] Choose target marketplaces for the swarm and verify at least one draft flow
- [ ] Define default undercut delta and profit floor for the demo
- [ ] Set up mobile Expo project and confirm device build works
- [ ] Register .tech domain
- [ ] Set up backend hosting
