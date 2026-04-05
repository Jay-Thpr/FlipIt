# Agentverse Profile Setup — Exact Steps
**Do this after all 10 Fetch uAgents are running locally** in this repository.

**Canonical mapping:** Slug, port, seed env var, and `*_AGENTVERSE_ADDRESS` names live in [AGENTVERSE_IMPLEMENTATION_PLAN.md](AGENTVERSE_IMPLEMENTATION_PLAN.md) (§2). [FETCH_INTEGRATION.md](FETCH_INTEGRATION.md) covers the full Fetch bridge.

---

## This repository (DiamondHacks backend)

- Fetch **uAgents** are built by [`backend/fetch_agents/builder.py`](backend/fetch_agents/builder.py) from [`FETCH_AGENT_SPECS`](backend/fetch_runtime.py). There are **no** per-agent scripts such as `python run_agents.py` or `agents/vision_agent.py`.
- **Python:** use **`make venv-fetch`** (defaults to `python3.12`) so `uagents` runs outside the main app venv. Main app: `make install` (`.venv`).
- **Run all ten:** load `.env` into your shell (`set -a && source .env && set +a` in bash/zsh), then **`make run-fetch-agents`**. [`backend/run_fetch_agents.py`](backend/run_fetch_agents.py) does not call `load_dotenv`; the shell must export `AGENTVERSE_API_KEY` and all `*_FETCH_AGENT_SEED` vars.
- **uAgent listen ports** in this repo are **9201–9210** (one port per slug). Optional HTTP `/task` microservices for the same logical agents use **9101–9110** ([`backend/config.py`](backend/config.py)) — a **separate** process from the Fetch uAgent.

---

## Prerequisites

Before Agentverse profile work:

- All 10 Fetch agents running via **`make run-fetch-agents`** (after `make venv-fetch` and env loaded), or debug one with `PYTHONPATH=$PWD .venv-fetch/bin/python -m backend.fetch_agents.launch <slug>`.
- **`.env`:** `AGENTVERSE_API_KEY`, ten unique **`_*_FETCH_AGENT_SEED`** values, `FETCH_USE_LOCAL_ENDPOINT=false` for mailbox mode ([`.env.example`](.env.example)).
- Agentverse account at https://agentverse.ai and API key stored only in `.env` (never commit).

**ngrok:** Optional. Use **`ngrok http 8000`** only if you need a **public URL for the FastAPI app** (e.g. mobile). It is **not** required for mailbox-backed uAgents on ports **920x**.

---

## How Registration Works

This repo uses **`mailbox=True`** on each uAgent (see [`build_fetch_agent`](backend/fetch_agents/builder.py)). Agentverse buffers messages; you do **not** need a public inbound URL for each uAgent for normal mailbox operation.

- **One process per slug:** each Fetch agent listens on a **single** uAgent port from the spec (**9201–9210**), not a legacy “task port + uAgent port” pair. The FastAPI orchestrator on **8000** is separate.
- If you set **`FETCH_USE_LOCAL_ENDPOINT=true`**, the builder adds a local **`endpoint`** for inspector-style debugging ([`FETCH_INTEGRATION.md`](FETCH_INTEGRATION.md)). Default is **`false`** (mailbox).

Older patterns (per-uAgent ngrok tunnels or LAN IP endpoints) are unnecessary for the default mailbox flow in this codebase.

---

## Step 1 — Agent implementation in this repo

You **do not** edit per-agent Python entrypoints. Seeds and ports come from **`FETCH_AGENT_SPECS`** and environment variables.

[`backend/fetch_agents/builder.py`](backend/fetch_agents/builder.py) constructs each `Agent` with (conceptually):

- `name` / `port` / `seed` from the spec and matching `*_FETCH_AGENT_SEED` env var  
- `mailbox=True`  
- `publish_agent_details=True`  
- optional local `endpoint` when **`FETCH_USE_LOCAL_ENDPOINT=true`**

There is **no** `readme_path` in the builder today — profile and README text visible on Agentverse come from the **dashboard** (and/or copy-paste from Step 2 templates below). Optional future `readme_path` wiring is described in [AGENTVERSE_IMPLEMENTATION_PLAN.md](AGENTVERSE_IMPLEMENTATION_PLAN.md) Phase D.

---

## Step 2 — Profile / README text (copy-paste)

The markdown blocks below are **templates** for Agentverse discoverability (Overview, description, long-form readme). **Paste** them into each agent’s profile on https://agentverse.ai — they are **not** auto-loaded from `agents/README_*.md` in this repo.

You may keep optional local notes under `docs/` or similar; **Agentverse is the source of truth** for what judges see unless you add `readme_path` support in code later.

### Template (fill in per agent):

```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# [Agent Name]

## Overview

[One paragraph — what this agent does, what problem it solves, why it's useful]

## Key Features

- [Feature 1]
- [Feature 2]
- [Feature 3]

## Usage

Send a message describing what you want this agent to do. The agent accepts
natural language requests and returns structured results.

**Input example:**
"Identify this thrift store item for resale: [description or image context]"

**Output example:**
```json
{
  "brand": "Nike",
  "item_name": "Air Jordan 1 Retro High OG",
  "condition": "good",
  "confidence": 0.92,
  "search_query": "Nike Air Jordan 1 Retro High OG Chicago"
}
```

## Use Cases

- [Use case 1]
- [Use case 2]

## Limitations

- [Limitation 1]
- [Limitation 2]

## Part of

This agent is part of a 10-agent autonomous resale system built for DiamondHacks
2026. It works alongside VisionAgent, EbaySoldCompsAgent, PricingAgent,
DepopListingAgent, DepopSearchAgent, EbaySearchAgent, MercariSearchAgent,
OfferUpSearchAgent, RankingAgent, and NegotiationAgent to automate the full
secondhand marketplace workflow for both buyers and sellers.

**Address:** `agent1q...` (replace after registration)
```

### All 10 agents — pre-written profile content:

---

**VisionAgent** (`vision_agent`, port 9201)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# VisionAgent

## Overview

Identifies thrift store items from photos using Gemini Vision and generates
clean white-background product photos using Nano Banana. The first step in
an autonomous resale pipeline that turns a camera photo into a ready-to-post
listing. Returns structured item data optimized for downstream market research
and listing creation.

## Key Features

- Identifies brand, model, condition, and color from raw thrift store photos
- Returns a confidence score — pauses pipeline if identification is uncertain
- Generates an optimized eBay search query for the identified item
- Produces a clean white-background product photo via Nano Banana

## Usage

Send a photo description or image context. The agent returns structured item
identification data.

**Input:** Photo of a thrift store item (base64 encoded)

**Output:**
```json
{
  "brand": "Nike",
  "item_name": "Air Jordan 1 Retro High OG",
  "model": "Air Jordan 1",
  "condition": "good",
  "confidence": 0.92,
  "search_query": "Nike Air Jordan 1 Retro High OG Chicago",
  "clean_photo_url": "https://..."
}
```

## Use Cases

- Thrift store item identification for resale value assessment
- Automated listing content generation
- Product photo enhancement for marketplace listings

## Limitations

- Confidence may be low for obscure or unlabeled items
- Clean photo generation requires a clear, well-lit source photo
```

---

**EbaySoldCompsAgent** (`ebay_sold_comps_agent`, port 9202)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# EbaySoldCompsAgent

## Overview

Scrapes eBay sold listings using Browser Use to pull real market comps for
a given item. Returns historical sold prices, conditions, and dates to enable
accurate profit margin calculation. Falls back to Mercari if eBay detection
occurs.

## Key Features

- Retrieves up to 15 real sold listings from eBay
- Filters by condition match and last 90 days
- Automatic fallback to Mercari sold listings if eBay blocks
- Returns structured comp data for pricing analysis

## Usage

**Input:** Item brand, model, and condition
**Output:** List of sold comps with price, date, and condition

## Use Cases

- Market price research for secondhand items
- Resale profit margin calculation
- Thrift store buying decision support

## Limitations

- eBay may throttle requests — Mercari fallback handles this
- Sold listing data limited to last 90 days
```

---

**PricingAgent** (`pricing_agent`, port 9203)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# PricingAgent

## Overview

Computes recommended listing price, estimated profit margin, market trend
direction, and sell velocity from eBay sold comp data. Uses statistical
outlier removal and condition-based price adjustment. Provides a complete
pricing intelligence report including trend signals and demand indicators.

## Key Features

- Median price calculation with outlier removal
- Condition multiplier adjustment (excellent/good/fair)
- Market trend detection: rising, falling, or stable (last 30 vs 31-90 days)
- Sell velocity: high, medium, or low demand signal
- Gemini-generated listing description

## Usage

**Input:** Sold comps list, item condition, thrift store cost
**Output:** Recommended price, profit margin, trend signal, velocity label

## Use Cases

- Thrift store buy/pass decision support
- Resale pricing optimization
- Market timing for listing creation

## Limitations

- Trend calculation requires at least 4 comps across both time windows
- Profit assumes $5 flat shipping and 10% Depop fee
```

---

**DepopListingAgent** (`depop_listing_agent`, port 9204)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# DepopListingAgent

## Overview

Autonomously populates a complete Depop listing form using Browser Use,
including photo upload, title, description, price, and condition. Stops
before the final submit button and returns a screenshot of the completed
form for user review and approval. Runs against a pre-authenticated Depop
session.

## Key Features

- Navigates Depop's multi-step listing form automatically
- Uploads clean product photo via file input
- Populates all required fields: title, description, price, condition
- Returns form screenshot for mobile preview
- Never submits without explicit user action

## Usage

**Input:** Item details, recommended price, listing description, clean photo URL
**Output:** Screenshot of completed form, listing preview card

## Use Cases

- Automated listing creation for thrift store resellers
- One-tap listing workflow for mobile users
- Resale business automation

## Limitations

- Requires pre-authenticated Depop account session
- Form structure changes may require task prompt updates
- Does not submit — user must approve and post
```

---

**DepopSearchAgent** (`depop_search_agent`, port 9205)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# DepopSearchAgent

## Overview

Searches Depop for active listings matching a query. Returns structured
listing data including price, condition, seller, and URL for ranking and
offer generation. Part of the BUY pipeline that helps users find the best
deals on niche secondhand items.

## Key Features

- Searches Depop active listings by keyword
- Returns up to 15 listings with price, condition, seller, URL
- Structured output ready for ranking and negotiation agents
- Falls back to Browser Use if internal API is unavailable

## Usage

**Input:** Search query string (e.g. "Nike Air Jordan 1 Chicago size 10")
**Output:** List of active Depop listings with metadata

## Use Cases

- Niche item price discovery across Depop
- Multi-platform resale price comparison
- Automated buyer research

## Limitations

- Active listings only — not sold history
- Results limited to first page of Depop search
```

---

**EbaySearchAgent** (`ebay_search_agent`, port 9206)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# EbaySearchAgent

## Overview

Searches eBay active Buy It Now listings via the official eBay Browse API.
Returns clean structured listing data including price, condition, seller
feedback, and listing URL for multi-platform comparison and ranking.

## Key Features

- Uses official eBay Browse API — fast and reliable
- Returns up to 15 active Buy It Now listings
- Includes seller feedback score for credibility ranking
- No browser automation required — pure API call

## Usage

**Input:** Search query string
**Output:** List of active eBay listings with price, condition, seller, URL

## Use Cases

- eBay price discovery for secondhand items
- Cross-platform listing comparison
- Automated buyer research

## Limitations

- Buy It Now listings only — auction listings excluded by default
- Requires eBay developer API credentials
```

---

**MercariSearchAgent** (`mercari_search_agent`, port 9207)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# MercariSearchAgent

## Overview

Searches Mercari for active listings matching a query. Returns structured
listing data for price comparison and ranking. Part of the BUY pipeline
that aggregates listings across multiple secondhand platforms.

## Key Features

- Searches Mercari active listings by keyword
- Returns price, condition, seller, and listing URL
- Structured output compatible with RankingAgent
- Lightweight HTTP-based search

## Usage

**Input:** Search query string
**Output:** List of active Mercari listings

## Use Cases

- Mercari price discovery
- Multi-platform secondhand price comparison
- Automated buyer research

## Limitations

- No official public Mercari API — uses internal endpoints
- Results may vary based on Mercari's response
```

---

**OfferUpSearchAgent** (`offerup_search_agent`, port 9208)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# OfferUpSearchAgent

## Overview

Attempts to search OfferUp for active local and national listings. Best
effort — includes a hard 30-second timeout and returns gracefully if
OfferUp is unavailable. Part of the BUY pipeline's multi-platform search.

## Key Features

- Searches OfferUp active listings
- Hard 30-second timeout — never blocks the pipeline
- Returns empty list gracefully if blocked
- Sequential with other search agents

## Usage

**Input:** Search query string
**Output:** List of active OfferUp listings, or empty list with status "blocked"

## Limitations

- High bot detection risk on OfferUp
- No public API — relies on web automation
- Results not guaranteed — treat as best effort
```

---

**RankingAgent** (`ranking_agent`, port 9209)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# RankingAgent

## Overview

Scores and ranks aggregated listings from all search agents (Depop, eBay,
Mercari, OfferUp) by price competitiveness, condition, seller credibility,
and recency. Flags listings significantly below market median as haggle
targets. Uses Gemini to generate a one-line summary per listing.

## Key Features

- Composite scoring: price (40%), condition (30%), seller credibility (20%), recency (10%)
- Deduplication across platforms
- Haggle target flagging for listings >15% below median
- Gemini-generated one-line summary per top 10 listing
- Returns median market price for offer generation

## Usage

**Input:** Aggregated listing list from all search agents
**Output:** Ranked top 10 listings with scores, haggle flags, summaries, median price

## Use Cases

- Multi-platform deal finding
- Automated negotiation target identification
- Secondhand market price discovery

## Limitations

- Ranking weights are fixed — not personalized per user
- Requires at least 3 listings across platforms to rank meaningfully
```

---

**NegotiationAgent** (`negotiation_agent`, port 9210)
```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# NegotiationAgent

## Overview

Generates a personalized, human-sounding offer message using Gemini and
sends it to a seller via Browser Use. Called once per seller for each
flagged deal target. Returns offer price, message text, and send status.
Part of the autonomous BUY pipeline that negotiates on behalf of the user.

## Key Features

- Gemini-generated offer message — unique per seller, never templated
- Calculates offer price at 15-25% below asking, floored at market median
- Sends offer via Depop or Mercari messaging UI
- Returns per-seller offer status for mobile tracking UI
- Sounds human — avoids bot-like phrasing

## Usage

**Input:** Single listing (platform, seller, URL, price), market median price
**Output:** Offer price, message text, send status (sent/failed)

## Use Cases

- Automated price negotiation for secondhand buyers
- Bulk offer sending across multiple sellers
- Resale arbitrage automation

## Limitations

- Requires pre-authenticated seller platform account
- Offer acceptance depends on seller — no guarantee
- Depop and Mercari only (OfferUp messaging too unreliable)
```

---

## Step 3 — Registration Process (Per Agent)

Do this for each of the 10 agents. The flow is the same; only the **slug** and **port** change (see Quick Reference below).

### Start one agent (debug):
```bash
set -a && source .env && set +a   # bash/zsh — exports AGENTVERSE_API_KEY and seeds
PYTHONPATH=$PWD .venv-fetch/bin/python -m backend.fetch_agents.launch vision_agent
```

Replace `vision_agent` with any slug (e.g. `negotiation_agent`, `depop_search_agent`).

### Start all ten:
```bash
set -a && source .env && set +a
make run-fetch-agents
```

### What to expect in the terminal

You should see the agent’s **`agent1q...`** address and an **Agent inspector** URL. The **port in the URL matches the uAgent port** for that slug (e.g. VisionAgent → **9201**, NegotiationAgent → **9210**). Example shape:

```
INFO: [VisionAgent]: Agent inspector available at:
  https://agentverse.ai/inspect/?uri=http://127.0.0.1:9201&address=agent1q...
INFO: [mailbox]: Successfully registered as mailbox agent in Agentverse
```

**Copy each `agent1q...` into `.env`** using the matching **`*_AGENTVERSE_ADDRESS`** variable ([AGENTVERSE_IMPLEMENTATION_PLAN.md](AGENTVERSE_IMPLEMENTATION_PLAN.md) §2). Optionally run **`make run`** in another terminal and confirm with **`GET http://localhost:8000/fetch-agents`**. You can also paste the address into the profile template’s **Address** line for your own notes.

### Browser steps:

1. Open the Inspector URL from terminal in your browser
2. Click **Connect**
3. Select **Mailbox**
4. Click **OK, got it** — nothing else to do
5. Go to https://agentverse.ai/agents
6. Find your agent (tagged "Mailbox")
7. Click into it → **Edit** or **Overview** tab

### Fill in the profile:

**Name:** Short, under 20 chars, no spaces preferred
| Agent | Name |
|---|---|
| VisionAgent | VisionAgent |
| EbaySoldCompsAgent | EbaySoldComps |
| PricingAgent | PricingAgent |
| DepopListingAgent | DepopListing |
| DepopSearchAgent | DepopSearch |
| EbaySearchAgent | EbaySearch |
| MercariSearchAgent | MercariSearch |
| OfferUpSearchAgent | OfferUpSearch |
| RankingAgent | RankingAgent |
| NegotiationAgent | Negotiation |

**Handle:** Set a custom @handle (under 20 chars)
| Agent | Handle |
|---|---|
| VisionAgent | @visionagent |
| EbaySoldCompsAgent | @ebaysoldcomps |
| PricingAgent | @pricingagent |
| DepopListingAgent | @depoplisting |
| DepopSearchAgent | @depopsearch |
| EbaySearchAgent | @ebaysearch |
| MercariSearchAgent | @mercarisearch |
| OfferUpSearchAgent | @offerupsearch |
| RankingAgent | @rankingagent |
| NegotiationAgent | @negotiationagent |

**Keywords (add 4-6 per agent):**
| Agent | Keywords |
|---|---|
| VisionAgent | vision, image, identification, resale, thrift, gemini |
| EbaySoldCompsAgent | ebay, sold, comps, pricing, resale, research |
| PricingAgent | pricing, margin, profit, trend, resale, analysis |
| DepopListingAgent | depop, listing, resale, automation, sell, browser |
| DepopSearchAgent | depop, search, buy, listings, secondhand, fashion |
| EbaySearchAgent | ebay, search, buy, listings, marketplace, browse |
| MercariSearchAgent | mercari, search, buy, listings, secondhand, price |
| OfferUpSearchAgent | offerup, search, local, listings, secondhand |
| RankingAgent | ranking, scoring, comparison, resale, deals, best |
| NegotiationAgent | negotiation, offer, haggle, resale, buy, price |

**About field (one sentence):**
| Agent | About |
|---|---|
| VisionAgent | Identifies thrift store items from photos and generates clean product images for resale listings. |
| EbaySoldCompsAgent | Scrapes eBay sold listings to pull real market comps for resale pricing. |
| PricingAgent | Calculates profit margins, market trends, and sell velocity from sold comp data. |
| DepopListingAgent | Autonomously populates Depop listing forms and returns a screenshot for user approval. |
| DepopSearchAgent | Searches Depop active listings for a given query and returns structured results. |
| EbaySearchAgent | Searches eBay Buy It Now listings via the official Browse API. |
| MercariSearchAgent | Searches Mercari active listings for a given query. |
| OfferUpSearchAgent | Searches OfferUp listings with a 30-second hard timeout. |
| RankingAgent | Scores and ranks listings from multiple platforms by price, condition, and seller quality. |
| NegotiationAgent | Generates personalized offer messages and sends them to sellers via Browser Use. |

**Upload avatar:** Optional but gives ranking boost. Use any simple icon — a small square PNG. Can use a colored letter icon generated at https://ui-avatars.com/?name=V&background=000&color=fff (change letter per agent).

---

## Step 4 — Trigger 3 Interactions Per Agent

Agentverse requires at least 3 interactions for ranking. Do this for each agent after registration:

```
1. Go to your agent's profile on Agentverse
2. Click "Interactions" tab
3. Click "Evaluate" or use the chat interface
4. Send 3 test messages:
   - "What do you do?"
   - "How do I use you?"
   - "What input do you accept?"
```

This satisfies the "receive at least 3 interactions" ranking criterion.

---

## Step 5 — Generate ASI:One Chat Session URL (Fetch.ai Deliverable)

Do this after all 10 agents are registered and Active:

```
1. Go to https://asi1.ai/chat
2. Sign in
3. Type: "I found a Nike Air Jordan 1 at Goodwill. Help me figure out if it's worth buying and list it for resale."
4. ASI:One should discover your agents and route the request
5. If agents don't auto-discover, try: "@visionagent identify this thrift store item" or "@negotiationagent help me make an offer"
6. Copy the URL of this chat session
```

This URL is your Fetch.ai deliverable. Paste into Devpost submission.

---

## Step 6 — Collect All Deliverable URLs

After all 10 agents registered, fill this in:

```
ASI:One Chat Session:     https://asi1.ai/chat/...
VisionAgent:              https://agentverse.ai/agents/...
EbaySoldCompsAgent:       https://agentverse.ai/agents/...
PricingAgent:             https://agentverse.ai/agents/...
DepopListingAgent:        https://agentverse.ai/agents/...
DepopSearchAgent:         https://agentverse.ai/agents/...
EbaySearchAgent:          https://agentverse.ai/agents/...
MercariSearchAgent:       https://agentverse.ai/agents/...
OfferUpSearchAgent:       https://agentverse.ai/agents/...
RankingAgent:             https://agentverse.ai/agents/...
NegotiationAgent:         https://agentverse.ai/agents/...
```

Paste all 11 URLs into Devpost submission under Fetch.ai deliverables.

---

## Troubleshooting

**Agent not appearing in Agentverse after registration:**
- Wait 60 seconds — there's a propagation delay
- Verify terminal shows: `Successfully registered as mailbox agent in Agentverse`
- Check agent is still running — inactive agents disappear from Active list
- Try refreshing https://agentverse.ai/agents

**Mailbox registration fails:**
- Check `AGENTVERSE_API_KEY` in `.env` is correct
- Ensure agent is running before opening Inspector URL
- Each agent must have a unique seed phrase

**ASI:One doesn't discover your agents:**
- Check agent profile has keywords set
- Check long-form readme / description is filled in (visible in Overview tab)
- Try tagging agent directly: "@visionagent [query]" or "@negotiationagent [query]"
- Ensure agent status shows Active (green badge)

**Port conflict (example — use the port for the slug you launched):**
```bash
lsof -ti:9201 | xargs kill -9
```

---

## Quick Reference — Fetch uAgents (this repo)

HTTP `/task` microservices (optional) use **9101–9110**; Fetch **uAgents** use **9201–9210**. Launch slug is the second argument to `backend.fetch_agents.launch`.

| Display name | Launch slug | uAgent port | Seed env var |
|---|---|---|---|
| VisionAgent | `vision_agent` | 9201 | `VISION_FETCH_AGENT_SEED` |
| EbaySoldCompsAgent | `ebay_sold_comps_agent` | 9202 | `EBAY_SOLD_COMPS_FETCH_AGENT_SEED` |
| PricingAgent | `pricing_agent` | 9203 | `PRICING_FETCH_AGENT_SEED` |
| DepopListingAgent | `depop_listing_agent` | 9204 | `DEPOP_LISTING_FETCH_AGENT_SEED` |
| DepopSearchAgent | `depop_search_agent` | 9205 | `DEPOP_SEARCH_FETCH_AGENT_SEED` |
| EbaySearchAgent | `ebay_search_agent` | 9206 | `EBAY_SEARCH_FETCH_AGENT_SEED` |
| MercariSearchAgent | `mercari_search_agent` | 9207 | `MERCARI_SEARCH_FETCH_AGENT_SEED` |
| OfferUpSearchAgent | `offerup_search_agent` | 9208 | `OFFERUP_SEARCH_FETCH_AGENT_SEED` |
| RankingAgent | `ranking_agent` | 9209 | `RANKING_FETCH_AGENT_SEED` |
| NegotiationAgent | `negotiation_agent` | 9210 | `NEGOTIATION_FETCH_AGENT_SEED` |

**`*_AGENTVERSE_ADDRESS`:** see [AGENTVERSE_IMPLEMENTATION_PLAN.md](AGENTVERSE_IMPLEMENTATION_PLAN.md) §2 for the exact variable name per slug.
