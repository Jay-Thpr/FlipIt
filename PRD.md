# PRD — Autonomous Resale Agent (FILLER) v3
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

### SELL Flow
```
User opens app → taps SELL → takes photo
        ↓
VisionAgent: identifies item (Gemini Vision) + clean photo (Nano Banana)
        ↓
EbayResearchAgent: pulls sold comps (Browser Use)
        ↓
PricingAgent: computes median price + profit margin (Gemini)
        ↓
DepopListingAgent: populates Depop form (Browser Use)
        ↓
Screen: before/after photo + comp breakdown + profit margin + Depop form preview
User taps Post (manual final step)
```

### BUY Flow
```
User opens app → taps BUY → pastes link or describes item
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
HagglingAgent × N: sends one optimized offer per seller (Browser Use, called once per seller)
        ↓
Screen: ranked listing feed + offer status tracker per seller
```

---

## 5. Agent Architecture

### 5.1 The Orchestration Layer

**ASI:One is the orchestrator.** This is Fetch.ai's own LLM — not a custom agent you build. ASI:One discovers your registered agents on Agentverse and routes tasks to them. Your job is building the specialist agents, registering them, and implementing the Chat Protocol. ASI:One handles coordination automatically.

FastAPI sits alongside this as the bridge between the mobile app and the agent network, receiving SSE events and streaming them to the frontend.

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
| 10 | HagglingAgent | BUY | Generate + send one offer per seller | Browser Use, Gemini |

### 5.3 SELL Sequencing
```
VisionAgent → EbayResearchAgent → PricingAgent → DepopListingAgent
```
Strictly sequential. Each agent completes fully before the next fires. EbayResearchAgent output feeds PricingAgent; PricingAgent output feeds DepopListingAgent.

### 5.4 BUY Sequencing
```
DepopSearchAgent → EbaySearchAgent → MercariSearchAgent → OfferUpSearchAgent
        → RankingAgent
        → HagglingAgent (×N, once per target seller)
```
Search agents run sequentially — one platform at a time. Sequential-but-fast: each platform search takes 10-20 seconds, total search phase ~60 seconds. Results aggregate after all search agents complete, then pass to RankingAgent. HagglingAgent is called independently once per seller, sequentially.

### 5.5 Fetch.ai Integration — Full Detail

**Registration:** All 10 agents run locally on Render as uAgents. Each registers on Agentverse via the Mailbox feature. Mailbox buffers messages during any brief downtime and delivers them when agent reconnects. Once registered, each agent shows as Active in Agentverse Marketplace.

**Chat Protocol:** Every agent implements `uagents_core.contrib.protocols.chat` — receives `ChatMessage`, sends `ChatAcknowledgement`, processes, returns `ChatMessage` with results.

**Discoverability:** All 10 agents discoverable by ASI:One via Agentverse search. ASI:One can route user natural language requests to any of them directly.

**Deliverables:**
- 10 Agentverse profile URLs (one per agent)
- ASI:One Chat session URL demonstrating agents working through ASI:One
- README.md per agent with name, address, capability description
- `![tag:innovationlab]` badge in each README

**Fetch.ai judging story:** 10 distinct registered agents, genuine multi-agent coordination, Browser Use inside uAgents, ASI:One as discovery + orchestration layer. Directly hits "Quantity of Agents Created" and "multi-agent collaboration" judging criteria.

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

**Output:** `{ form_screenshot_url, listing_preview: { title, price, description } }`

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

### 6.10 HagglingAgent (BUY) — called once per seller

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

### 7.2 Screen Structure

**Home Screen:**
Two large mode cards with clear CTAs:
- **SELL** — "Scan something. Know your margin. List it."
- **BUY** — "Find something. Agents hunt it down and haggle."

**SELL Screen:**
- Full-screen camera viewfinder
- Tap to capture → pipeline starts immediately
- Bottom sheet rises with agent activity feed
- Results screen (after pipeline): before/after photo strip, comp table, profit margin hero number, Depop form preview screenshot

**BUY Screen:**
- Text input: paste link or describe item
- Submit → pipeline starts
- Agent activity feed: 4 platform search agents show sequentially with platform badges
- Results: ranked listing cards (platform badge, price, condition, score, haggle flag)
- "Send Offers" CTA → HagglingAgent fires per seller
- Offer tracker: per-seller status badge (Sent / Replied / Accepted)

### 7.3 Agent Activity Feed (both modes)
- Persistent animated bottom sheet
- One card per agent: name, status (idle / active / complete / error), live log line
- Active agent: pulsing animation
- Complete agent: green checkmark + one-line result summary
- Error agent: red indicator + fallback note

### 7.4 SSE Event Types

```
agent_started      { agent_name, mode }
agent_log          { agent_name, message }       # live log line
agent_completed    { agent_name, summary }       # one-line result
agent_error        { agent_name, error, fallback }
listing_found      { platform, listing }         # BUY: streams as found
offer_sent         { seller, platform, status }  # BUY: per seller
pipeline_complete  { mode, session_id }
```

Frontend updates in real time on each event. No polling.

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
1. Open app, tap SELL. "You just found this at Goodwill. Is it worth buying?"
2. Take photo.
3. VisionAgent: item identified on screen, clean product photo appears. "It knows exactly what this is."
4. EbayResearchAgent: comp table populates. "Real sold prices from eBay."
5. PricingAgent: profit margin appears large. "After fees, you make $Y."
6. DepopListingAgent: Depop form screenshot appears, fully populated. "Your listing is ready. One tap to post."

**Demo Arc 2 — BUY (90 seconds):**
1. Tap BUY. "You want these specific Jordan 1s but refuse to pay asking price."
2. Paste product link.
3. DepopSearchAgent, EbaySearchAgent, MercariSearchAgent fire sequentially — platform badges animate. "Checking every resale platform."
4. RankingAgent: ranked listing cards appear, haggle targets flagged. "Found 31 listings. These 5 are below market."
5. Tap Send Offers. HagglingAgent fires. "Sent personalized offers to 5 sellers."
6. Show pre-staged reply from test account. "One already replied."

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
| Best UI/UX | Beautiful and intuitive UX | Native mobile polish, live agent feed, progressive results, before/after photo, ranked cards |
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
1. Expo app shell: Home, SELL screen, BUY screen, camera
2. FastAPI backend + SSE infrastructure
3. VisionAgent — Gemini Vision identification
4. EbayResearchAgent — sold comp scraping
5. PricingAgent — margin calculation
6. Agent activity feed in mobile UI (SSE-driven)
7. DepopSearchAgent + EbaySearchAgent + MercariSearchAgent

**Should have:**
8. DepopListingAgent — Depop form population
9. RankingAgent — scored listing feed
10. HagglingAgent — offer sending
11. Nano Banana — clean photo generation
12. All 10 agents registered on Agentverse via Mailbox

**Nice to have:**
13. OfferUpSearchAgent
14. Mercari fallback inside EbayResearchAgent
15. User-adjustable thrift cost field
16. Offer status tracker with pre-staged reply demo

---

## 14. Team Split (Recommended)

| Person | Owns |
|---|---|
| 1 | Fetch.ai + agent architecture: uAgents setup, Mailbox registration, Chat Protocol, all agent scaffolding, ASI:One integration |
| 2 | Browser Use: EbayResearchAgent, DepopListingAgent, all 4 BUY search agents, HagglingAgent — Browser Use specialist |
| 3 | AI pipeline: VisionAgent (Gemini Vision + Nano Banana), PricingAgent, RankingAgent (Gemini), offer message generation |
| 4 | Mobile frontend: Expo app, camera, SSE feed, agent activity UI, SELL results screen, BUY results + ranking cards |

FastAPI backend split between persons 1 and 2 — 1 owns session management + SSE infrastructure, 2 owns Browser Use execution endpoints.

---

## 15. Checklist

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