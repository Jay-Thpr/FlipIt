# Judging-Criteria Implementation Plan

**DiamondHacks 2026 | April 5–6 | UCSD**

This plan is organized around what the judges actually score — not phases, not workstreams. Every task maps to a specific prize and criterion.

---

## Prize Priority Ranking

| Prize | Criteria Gap | Effort | Value |
|-------|-------------|--------|-------|
| **Browser Use** — 2x iPhone 17 Pro + Hacker House | Live eBay scrape + Depop form population demo-ready | Medium | 🏆 Highest |
| **Enchanted Commerce** (main) | Full sell flow working, polished UX | Low (mostly done) | High |
| **Fetch.ai** — $300 cash | Agentverse registration + Chat Protocol + ASI:One URL | High | Medium |
| **Best Mobile Hack** | Expo app with SELL flow + listing_ready screen | High (stretch) | Medium |
| **Best AI/ML Hack** | Already satisfied by architecture | Zero | Low |
| **Best UI/UX Hack** | Agent feed animations, polished transitions | Low | Low |
| **Gemini MLH** | Already using Gemini Vision | Zero | Low |
| **.Tech Domain** | Register one domain | Zero | Free |

---

## Track 1: Browser Use (Top Priority)

**What judges score:** Core functionality relies on Browser Use agents actively interacting with real web environments. Working prototype for live demo.

**Current state:** Browser Use wired, fallback working. Needs live eBay scrape + Depop form population confirmed working locally.

### BU-1: Verify live eBay comps scrape (Jay — tonight)
- Run `python -m backend.warm_profiles` → log into eBay in local Chromium
- Smoke test: `POST /sell/start` with a real Air Jordan photo URL
- Verify `ebay_sold_comps_agent` SSE event shows `execution_mode: "browser_use"` (not `"fallback"`)
- If blocked: confirm httpx fallback returns real data, not zeros

### BU-2: Verify live Depop form population (Jay — tonight)
- Warm Depop profile in local Chromium (logged in, ready to list)
- Run sell pipeline end to end
- Watch `depop_listing_agent` populate form fields and pause before submit
- Verify `listing_ready` SSE event fires with `form_screenshot_b64` present

### BU-3: Demo rehearsal flow
- Pre-stage: Air Jordan 1 photo at known absolute path
- Pre-warm: Chromium profiles active for eBay + Depop
- Demo sequence: photo upload → Vision identifies → eBay opens live → comps appear → Depop form populates → pauses → screenshot shown
- **Judge-facing narrative:** "It's not scraping — it's doing. Watch it click."

**Acceptance criteria for Browser Use prize:** Judges see real Chromium automation happen live for eBay and Depop. Even one partial live action scores better than pure fallback.

---

## Track 2: Enchanted Commerce (Main Track)

**What judges score:** Idea, Experience, Implementation, Demo/Presentation.

**Current state:** Both SELL and BUY pipelines work end-to-end in fallback mode. Backend is solid. Frontend integration needed.

### EC-1: Frontend SSE integration (frontend teammate)
- Connect to `GET /stream/{session_id}` via EventSource
- Render agent cards as events arrive: `agent_started` → spinner, `agent_completed` → checkmark + data
- Surface `vision_low_confidence` pause UX (ask user to confirm item)
- Show profit number prominently on `pricing_result` event
- Show `listing_ready` screen with form screenshot + "Open Depop to Post" CTA

### EC-2: Polish agent activity feed (frontend teammate)
- Each agent card animates in sequentially as pipeline progresses
- Stagger entry animations (don't show all 4 at once)
- Profit number is the largest text on screen
- Before/after photo strip (original uploaded → Gemini clean photo)

### EC-3: Backend smoke tests before hackathon opens (Jay — tonight)
- `POST /sell/start` → stream → verify all 4 `agent_completed` events
- `POST /buy/start` → stream → verify all 6 agents complete
- `POST /sell/correct` round trip for vision resume path

**Acceptance criteria for main track:** 3-minute demo runs without needing to reload or explain failures to judges.

---

## Track 3: Fetch.ai ($300 cash)

**What judges score:** Agent orchestration + Agentverse registration (mandatory) + Chat Protocol (mandatory) + ASI:One demonstration.

**Current state:** Zero Fetch.ai wiring exists. `/chat` returns placeholder. No Agentverse registration.

**WARNING: This is the highest-effort remaining workstream. Assign dedicated teammate.**

### FA-1: Wire uAgents runtime into one agent (vision_agent first)
```python
# backend/agents/vision_agent.py — add alongside existing FastAPI app
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatMessage, ChatProtocol

agent = Agent(name="vision_agent", seed=os.getenv("VISION_AGENT_SEED"), mailbox=True)
chat_proto = ChatProtocol()

@chat_proto.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatMessage(
        message="Vision Agent: I identify items from photos and return brand, condition, and confidence score."
    ))

agent.include(chat_proto)
```

### FA-2: Add Fetch.ai env vars
In `.env.example` and `backend/config.py`:
```
FETCH_ENABLED=false
AGENTVERSE_API_KEY=
VISION_AGENT_SEED=
EBAY_COMPS_AGENT_SEED=
PRICING_AGENT_SEED=
DEPOP_LISTING_AGENT_SEED=
```

### FA-3: Register all agents on Agentverse
- One Agentverse account, one API key
- Register each agent with name + description matching their actual role
- Confirm mailbox active (green) in Agentverse dashboard
- Screenshot all 4 profile URLs for submission

### FA-4: Verify ASI:One discovery
- Open `https://asi1.ai` (or ASI:One chat)
- Type: "I want to flip a thrift store item. What can you help me with?"
- Confirm Vision Agent / Resale Agent is discovered and responds
- Save chat URL: `https://asi1.ai/shared-chat/...` — this is a required deliverable

### FA-5: Write per-agent profile descriptions for Agentverse
For each of the 4 SELL agents:
- Name, description (2-3 sentences), keywords (e.g. "resale, vision, item-identification, thrift")
- These show on the Agentverse profile page

**Required submission deliverables:**
1. ASI:One Chat session URL
2. 4x Agentverse profile URLs
3. GitHub repo + Devpost video

**Acceptance criteria:** Judges can open each Agentverse URL and see the agent. ASI:One URL is shareable.

---

## Track 4: Best Mobile Hack (Stretch — only if time allows)

**What judges score:** Standout mobile app experience.

**Current state:** PRD documents all 4 SELL screen states. Backend emits `listing_ready` with `form_screenshot_b64`. Needs Expo app.

### MB-1: Minimum viable SELL mobile app
- Camera screen → capture photo → `POST /sell/start`
- Agent feed screen → SSE listener → render 4 agent cards sequentially
- Listing ready screen → show form screenshot + "Open Depop to Post" button
  - If `draft_url` present: `Linking.openURL(depop://selling/drafts)`
  - Else: `Linking.openURL(depop://sell)`

**Skip if:** Frontend web app isn't fully working yet. Don't split attention before main track is demo-ready.

---

## Side Prizes (Zero Extra Effort)

### Best AI/ML Hack
Already satisfied: multi-agent pipeline + Gemini Vision + semantic pricing with trend/velocity analysis. Just mention it in the pitch.

### Best UI/UX Hack
Satisfied by agent feed animations. Make sure the profit number is visually dominant and agent cards have state animations (spinner → checkmark). Mention in pitch.

### Best Use of Gemini (MLH)
Already using `BROWSER_USE_GEMINI_MODEL=gemini-2.0-flash` and Gemini Vision for item identification. Register for MLH prize track. Show in pitch: "Powered by Gemini Vision."

### Best .Tech Domain
Register `resaleagent.tech` or `flippr.tech` tonight. Use code at the MLH table. 10-year domain is free. Required to win this prize.

---

## Critical Path (Hours Remaining Tonight)

**Must do tonight (Jay):**
1. Create `.env` with `GOOGLE_API_KEY` and `INTERNAL_API_TOKEN`
2. Run `make install` → `make check` → verify tests pass
3. Warm Chromium profiles: log into Depop + eBay in local browser
4. Smoke test full SELL pipeline live (not fallback)
5. Smoke test full BUY pipeline
6. Set up ngrok → give URL to frontend teammate

**Must do tonight (Fetch.ai teammate):**
1. Set up Agentverse account + get API key
2. Wire uAgents runtime into vision_agent (FA-1)
3. Register vision_agent on Agentverse, confirm mailbox active
4. Generalize to remaining 3 SELL agents

**Must do tonight (frontend teammate):**
1. Connect EventSource to `GET /stream/{session_id}`
2. Render agent cards for SELL pipeline events
3. Show profit number on `pricing_result`
4. Draft listing_ready screen layout

---

## Demo Script (3 minutes)

**0:00–0:15** "We're at a thrift store. Found these Air Jordans. Is this worth buying to flip? Let's find out in 60 seconds." → upload photo.

**0:15–0:45** Vision Agent fires: item identified, brand, condition, 94% confidence, clean white-background photo appears.

**0:45–1:30** eBay opens live in Chromium. Comps appear: "$145, $152, $138..." Pricing computes: "Median $147. Recommended price $139. Profit: $124 after fees."

**1:30–2:30** Depop opens live. Watch it click: photo uploads, category selected, title typed, description fills in, price entered. Form complete. Pauses before submit. Screenshot sent to phone.

**2:30–3:00** "Every field populated. One click to post." → Click. "Photo in. Listing out. Profit shown. That's the entire flipping workflow — automated."

---

## Submission Checklist

- [ ] GitHub repo public
- [ ] Devpost submission with demo video
- [ ] ASI:One chat session URL (Fetch.ai mandatory deliverable)
- [ ] 4x Agentverse profile URLs (Fetch.ai mandatory deliverable)
- [ ] .Tech domain registered (free prize)
- [ ] MLH Gemini prize track registered
- [ ] Browser Use merch claimed at their table (show what you built)
