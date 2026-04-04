# FlipBot — Autonomous Resale & Haggling Agent

**DiamondHacks 2026 | April 5–6 | UCSD**

---

## What This Project Is

You take a photo of any item — at a thrift store, garage sale, Facebook Marketplace listing — and the system does everything else:

1. **Identifies the item** using computer vision (Gemini Vision)
2. **Finds what it sells for** by scraping real sold listings across eBay, Mercari, StockX, Poshmark
3. **Determines what you should pay for it** based on profit margin targets
4. **Negotiates the price down** by autonomously messaging sellers on Facebook Marketplace, OfferUp, or Craigslist using Browser Use
5. **Creates a resale listing** pre-filled and ready to post on Depop/eBay once you acquire the item

The core loop: **photo in → fair price known → haggle down → list to flip → profit shown.**

---

## The Haggling Feature (The Differentiator)

Most price comparison tools tell you what something is worth. This one goes further — it **acts on that information**.

When a user sees an item listed on Facebook Marketplace for $80 and the system determines the item sells for $140 on eBay:

- The **Haggling Agent** opens the Facebook Marketplace listing via Browser Use
- It reads the seller's listing details, price, and any posted description
- It composes a contextually appropriate negotiation message (e.g. *"Hey, I noticed this has been listed for a few days — would you take $55? I can pick up today."*)
- It sends the message through Facebook Messenger directly within the Marketplace interface
- It monitors for a reply and can follow up with a counter if the seller rejects the first offer
- The user is notified of the seller's response and can approve or reject the final deal

This is only possible with Browser Use — a scraper alone cannot interact with Messenger. The agent actually clicks, types, and navigates like a human.

### Haggling Strategy Logic (Pricing Agent)

The Pricing Agent computes:
- `median_resale_price` — what the item actually sells for (from comps)
- `target_buy_price` — max price to pay and still clear a target margin (e.g. 40% after fees)
- `opening_offer` — 70% of target buy price (aggressive first anchor)
- `walk_away_price` — target buy price + 10% buffer (absolute max)

The Haggling Agent uses these values to decide how to negotiate. It does not exceed `walk_away_price` under any circumstances.

---

## Tracks This Project Hits

| Track | Type | Why It Qualifies |
|-------|------|-----------------|
| **Enchanted Commerce** | Main | End-to-end resale automation — price research, haggling, listing creation. Novel marketplace UX. |
| **Best Use of Browser Use** | Sponsor (2x iPhone 17 Pro + trip) | Load-bearing: eBay/Mercari comp scraping AND Facebook Marketplace haggling via Messenger |
| **Best Use of Fetch.ai** | Sponsor ($300 cash) | 5 uAgents on Agentverse with Chat Protocol. User can trigger the whole pipeline via ASI:One. |
| **Best Use of Gemini API** | MLH Side | Gemini Vision drives item identification (multimodal — core, not peripheral) |
| **Best AI/ML Hack** | Side | Multi-agent pipeline, vision model, semantic pricing, autonomous negotiation |
| **Best UI/UX Hack** | Side | Real-time agent activity dashboard with animated state transitions |
| **Best .Tech Domain** | Side | Free prize — register flipbot.tech or hagglebot.tech |

**Main track: Enchanted Commerce.** The project is literally a commerce automation engine.

---

## Agent Architecture (5 Agents)

All agents are Fetch.ai uAgents registered on Agentverse with Chat Protocol implemented.

### Agent 1 — Vision Agent
**Does:** Takes the uploaded photo → sends to Gemini Vision → extracts item name, brand, model, condition, keywords, confidence score → also sends to background removal API to generate a clean white-background product photo.

**Output:** `{ name, brand, model, condition, keywords, confidence }` + clean photo URL

---

### Agent 2 — Research Agent
**Does:** Takes the item identification → uses Browser Use to scrape **sold** listings (not just active) from eBay and Mercari → pulls real transaction data: price, condition, date sold, listing title.

**Browser Use workflow:**
- Navigate to `ebay.com/sch/` with `LH_Sold=1` filter
- Search `"{brand} {model}"` 
- Extract top 10–15 sold results
- Fall back to Mercari if eBay rate-limits the session

**Output:** Array of comp objects `[{ price, condition, date, title, source }]`

---

### Agent 3 — Pricing Agent
**Does:** Takes comp array → filters outliers → computes median sale price → calculates target buy price, opening offer, and walk-away price → generates full listing copy (title, description, category, price recommendation).

**Output:** `{ median_resale, target_buy_price, opening_offer, walk_away_price, recommended_listing_price, estimated_profit, listing_copy }`

---

### Agent 4 — Haggling Agent *(the novel piece)*
**Does:** If the item was found on Facebook Marketplace or OfferUp (user pastes URL, or agent searches for it), this agent opens the listing using Browser Use, reads the current price and description, composes a negotiation message calibrated to the pricing data, and sends it via the platform's built-in messaging system.

**Browser Use workflow (Facebook Marketplace):**
1. Navigate to the listing URL
2. Read: current asking price, description, how long listed, seller rating
3. Compose opening message using the `opening_offer` from Pricing Agent
4. Click "Message Seller" → type and send the message
5. Wait and monitor for reply (poll or webhook)
6. If rejected: counter with a value between `opening_offer` and `walk_away_price`
7. If accepted: notify user with next steps (arrange pickup, complete purchase)
8. If at `walk_away_price` and still rejected: notify user to walk away

**Negotiation message templates (dynamically filled):**
- Opening: *"Hi! Would you take $[opening_offer]? I can pick up [today/this weekend] — cash ready."*
- Counter: *"I understand — could we meet at $[midpoint]? That works better for me and I can come quickly."*
- Final: *"Best I can do is $[walk_away_price] — let me know!"*

**Output:** Negotiation status, agreed price (if any), conversation thread

---

### Agent 5 — Listing Agent
**Does:** Takes the clean photo, item data, and recommended listing price → uses Browser Use to open Depop listing creation → populates every field automatically → pauses at submit for user confirmation.

**Output:** Depop form fully populated, awaiting user click to post

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, shadcn/ui, Tailwind CSS |
| Real-time updates | SSE (Server-Sent Events) |
| Backend | Python + FastAPI |
| Agent framework | Fetch.ai uAgents |
| Agent registry | Agentverse (Chat Protocol on all 5 agents) |
| Item identification | Gemini Vision API (multimodal) |
| Background removal / clean photo | remove.bg API or PhotoRoom API |
| Browser automation | Browser Use (Playwright) |
| Comp scraping | Browser Use → eBay sold listings + Mercari fallback |
| Haggling | Browser Use → Facebook Marketplace Messenger |
| Listing creation | Browser Use → Depop form population |
| Hosting | Render or Vultr (free hackathon credits) |

---

## Integrations Breakdown

### Browser Use
The most critical integration. Used in **three distinct workflows:**
1. **Comp scraping** — navigate eBay/Mercari, extract sold listing data
2. **Haggling** — open Marketplace listing, click Message Seller, type and send negotiation message, read replies
3. **Listing creation** — open Depop, fill form fields, upload photo, pause at submit

Browser Use is what makes this project impossible to build with a simple API. No public API exists for Facebook Marketplace messaging. Browser Use is the only way to programmatically send a Messenger message from a Marketplace listing. This is the demonstration judges need to see.

### Fetch.ai / Agentverse
Five uAgents registered on Agentverse. Each implements the Chat Protocol. This means:
- Users can interact with the system directly through **ASI:One** (Fetch.ai's consumer AI)
- ASI:One discovers the agents via Agentverse and orchestrates them
- No custom frontend required for the Fetch.ai demo — judges can type "find me the best price for Air Jordan 1s and haggle the seller down" directly into ASI:One and watch it work

**For the Fetch.ai deliverable:** demonstrate via ASI:One text interface. Show the custom Next.js UI as the primary demo, then show ASI:One as secondary proof.

### Gemini Vision API (MLH)
Handles item identification from the uploaded photo. Gemini is multimodal — it sees the image and returns structured data: item name, brand, model, estimated condition, relevant search keywords. This drives every downstream agent. Not a peripheral use — the entire pipeline depends on Gemini's output.

### remove.bg / PhotoRoom API
Takes the original photo and generates a clean white-background product photo suitable for a marketplace listing. This matters for the UX — the listing looks professional without the user doing any editing.

---

## What Makes This Interesting to Judges

**Browser Use track:** The haggling workflow is a genuinely novel use case for browser automation. Sending negotiation messages through Facebook Marketplace Messenger is not something any existing tool does. The judges want to see agents that *do the thing*, not just recommend it. This agent does the thing.

**Fetch.ai track:** Five coordinated agents with real orchestration logic — not one agent doing everything. The pipeline has genuine parallelism (Research + early Pricing run concurrently after Vision), sequential dependencies (Listing waits for Pricing), and external side effects (Haggling sends real messages). This is the multi-agent orchestration they're looking for.

**Enchanted Commerce track:** This is exactly what the track description asks for — "novel marketplace innovations," "price comparison engines," "seamless shopping experiences." Automating the buy-low-sell-high workflow end-to-end is a direct fit.

---

## User Flow

1. User opens the app
2. User uploads a photo of an item (or pastes a Facebook Marketplace listing URL)
3. **If photo:** Vision Agent identifies the item → Research Agent finds comps → Pricing Agent computes value
4. **If URL:** Skip Vision → Research Agent scrapes the listing price → Pricing Agent determines if it's worth haggling
5. Agent activity feed updates in real time — each agent lights up as it activates
6. Pricing results appear: median resale value, recommended buy price, estimated profit margin
7. User clicks **"Haggle"** → Haggling Agent opens the listing, sends opening offer via Messenger
8. App shows the message sent and waits for a reply
9. Reply comes in → agent proposes counter or notifies user of acceptance
10. If accepted: Listing Agent fires → Depop form populates → user clicks "Post"
11. Deal done. Item not yet in hand → item flipped → profit realized.

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Facebook Marketplace blocks automated browser session | High | Use a pre-warmed, aged Facebook account in Browser Use; test login persistence tonight |
| Facebook Messenger flow changes / CAPTCHA on message send | High | Spike on this specifically first — if blocked, fall back to OfferUp (simpler messaging flow) |
| eBay rate-limits Browser Use session during demo | High | Pre-cache comps for demo item; fall back to Mercari |
| Depop form structure changes or breaks | High | Map form manually pre-hackathon; hardcode field sequence for demo item category |
| Gemini misidentifies demo item | Medium | Use unambiguous item (Air Jordan 1s); show confidence score |
| Agent sequencing race condition | Medium | Enforce sequential pipeline; no agent starts without confirmed prior completion signal |
| SSE drops during demo | Low | Reconnection logic + test on demo machine |
| Facebook account flagged/suspended | High | Have 2 backup accounts ready; keep messaging volume low pre-demo |

---

## Pre-Hackathon Checklist

- [ ] Spike on Browser Use Facebook Marketplace messaging — this is the highest-risk piece
- [ ] Create and pre-warm 2–3 Facebook accounts for Marketplace messaging
- [ ] Create Depop seller account, verify email, test listing creation permissions
- [ ] Select demo item with abundant eBay comps and clear profit margin ($50+) — Air Jordan 1s recommended
- [ ] Obtain Gemini API key
- [ ] Set up Agentverse account, test uAgent deployment
- [ ] Obtain remove.bg or PhotoRoom API key
- [ ] Test eBay sold listing scraping with Browser Use
- [ ] Register .tech domain (use DiamondHacks code)
- [ ] Set up Vultr account for free cloud credits

---

## One-Liner for Judges

*"Take a photo. We tell you what it's worth, message the seller to haggle the price down, and build the listing to flip it — fully automated."*
