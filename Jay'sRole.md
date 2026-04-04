# My Role — Backend + Fetch.ai Infrastructure
**DiamondHacks 2026 | Personal Execution Guide**

---

## Overview of What I Own

- FastAPI server + SSE infrastructure (the backbone everything plugs into)
- All 10 uAgents scaffolded with Chat Protocol
- Agentverse Mailbox registration for all 10 agents
- Session management (session ID → event queue → SSE stream)
- Internal event routing (agents → FastAPI → mobile app)
- Render deployment
- ASI:One verification for Fetch.ai judging

Everything other teammates build plugs into contracts I define. I need to be done with Phase 1 + 2 before anyone else can integrate.

---

## Project Structure

```
backend/
├── main.py                  # FastAPI app + SSE endpoints
├── session.py               # Session management
├── agents/
│   ├── base_agent.py        # Shared agent template
│   ├── vision_agent.py      # Agent 1
│   ├── ebay_research_agent.py   # Agent 2
│   ├── pricing_agent.py     # Agent 3
│   ├── depop_listing_agent.py   # Agent 4
│   ├── depop_search_agent.py    # Agent 5
│   ├── ebay_search_agent.py     # Agent 6
│   ├── mercari_search_agent.py  # Agent 7
│   ├── offerup_search_agent.py  # Agent 8
│   ├── ranking_agent.py     # Agent 9
│   └── haggling_agent.py    # Agent 10
├── run_agents.py            # Starts all agents as subprocesses
├── requirements.txt
├── .env
└── render.yaml
```

---

## Phase 1 — Environment Setup
**Target: 20 minutes**

### 1.1 Install dependencies

```bash
mkdir backend && cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install fastapi uvicorn sse-starlette uagents uagents-core python-dotenv httpx
```

### 1.2 Create .env

```env
# Agentverse
AGENTVERSE_API_KEY=your_agentverse_api_key_here

# API Keys (other teammates will fill these in)
GEMINI_API_KEY=your_gemini_key
NANO_BANANA_API_KEY=your_nano_banana_key

# Agent seed phrases (one per agent — must be unique)
VISION_AGENT_SEED=vision-agent-unique-seed-phrase-2026
EBAY_RESEARCH_AGENT_SEED=ebay-research-agent-seed-2026
PRICING_AGENT_SEED=pricing-agent-unique-seed-2026
DEPOP_LISTING_AGENT_SEED=depop-listing-agent-seed-2026
DEPOP_SEARCH_AGENT_SEED=depop-search-agent-seed-2026
EBAY_SEARCH_AGENT_SEED=ebay-search-agent-unique-2026
MERCARI_SEARCH_AGENT_SEED=mercari-search-agent-seed-2026
OFFERUP_SEARCH_AGENT_SEED=offerup-search-agent-seed-2026
RANKING_AGENT_SEED=ranking-agent-unique-seed-2026
HAGGLING_AGENT_SEED=haggling-agent-unique-seed-2026

# Internal
INTERNAL_SECRET=hackathon-internal-secret-2026
```

### 1.3 Get Agentverse API key
> **Browser step:** Go to https://agentverse.ai → Sign in → Top right avatar → API Keys → Create new key → Copy into .env

### 1.4 Create requirements.txt

```
fastapi
uvicorn[standard]
sse-starlette
uagents
uagents-core
python-dotenv
httpx
```

---

## Phase 2 — FastAPI + SSE Infrastructure
**Target: 45 minutes. This is the most critical piece. Everything else plugs into this.**

### 2.1 Session Manager (session.py)

```python
import asyncio
from typing import Dict
import json

# In-memory store: session_id -> asyncio.Queue
sessions: Dict[str, asyncio.Queue] = {}

def create_session(session_id: str):
    sessions[session_id] = asyncio.Queue()

def get_session(session_id: str) -> asyncio.Queue | None:
    return sessions.get(session_id)

async def push_event(session_id: str, event_type: str, data: dict):
    """Called by agents to push events into the session queue."""
    q = sessions.get(session_id)
    if q:
        await q.put({"event": event_type, "data": data})

async def close_session(session_id: str):
    q = sessions.get(session_id)
    if q:
        await q.put(None)  # None = sentinel, tells SSE stream to close
    sessions.pop(session_id, None)
```

### 2.2 Main FastAPI App (main.py)

```python
import asyncio
import json
import uuid
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from session import create_session, get_session, push_event, close_session
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

# CORS — needed for mobile app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")

# ── Request models ──────────────────────────────────────────────

class SellRequest(BaseModel):
    image_b64: str  # base64 encoded photo from camera

class BuyRequest(BaseModel):
    query: str      # item description or extracted from URL

class InternalEventRequest(BaseModel):
    secret: str
    session_id: str
    event_type: str
    data: dict

# ── Health check ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}

# ── SELL pipeline ───────────────────────────────────────────────

@app.post("/sell/start")
async def sell_start(req: SellRequest):
    session_id = str(uuid.uuid4())
    create_session(session_id)
    # Kick off SELL pipeline as background task
    asyncio.create_task(run_sell_pipeline(session_id, req.image_b64))
    return {"session_id": session_id}

async def run_sell_pipeline(session_id: str, image_b64: str):
    """Orchestrates SELL agents sequentially."""
    await push_event(session_id, "pipeline_started", {"mode": "sell"})

    # Step 1: Vision Agent
    vision_result = await call_agent("vision_agent", session_id, {
        "image_b64": image_b64
    })
    if not vision_result:
        await close_session(session_id)
        return

    # Step 2: eBay Research Agent
    research_result = await call_agent("ebay_research_agent", session_id, {
        "item_name": vision_result["item_name"],
        "brand": vision_result["brand"],
        "model": vision_result["model"],
        "condition": vision_result["condition"]
    })
    if not research_result:
        await close_session(session_id)
        return

    # Step 3: Pricing Agent
    pricing_result = await call_agent("pricing_agent", session_id, {
        "comps": research_result["comps"],
        "condition": vision_result["condition"],
        "item_name": vision_result["item_name"],
        "brand": vision_result["brand"]
    })
    if not pricing_result:
        await close_session(session_id)
        return

    # Step 4: Depop Listing Agent
    listing_result = await call_agent("depop_listing_agent", session_id, {
        "item_name": vision_result["item_name"],
        "brand": vision_result["brand"],
        "model": vision_result["model"],
        "condition": vision_result["condition"],
        "clean_photo_url": vision_result["clean_photo_url"],
        "recommended_price": pricing_result["recommended_price"],
        "listing_description": pricing_result["listing_description"]
    })

    await push_event(session_id, "pipeline_complete", {"mode": "sell"})
    await close_session(session_id)

# ── BUY pipeline ────────────────────────────────────────────────

@app.post("/buy/start")
async def buy_start(req: BuyRequest):
    session_id = str(uuid.uuid4())
    create_session(session_id)
    asyncio.create_task(run_buy_pipeline(session_id, req.query))
    return {"session_id": session_id}

async def run_buy_pipeline(session_id: str, query: str):
    """Orchestrates BUY agents sequentially."""
    await push_event(session_id, "pipeline_started", {"mode": "buy"})

    all_listings = []

    # Search agents run sequentially
    for agent_name in ["depop_search_agent", "ebay_search_agent",
                        "mercari_search_agent", "offerup_search_agent"]:
        result = await call_agent(agent_name, session_id, {"query": query})
        if result and result.get("listings"):
            all_listings.extend(result["listings"])

    if not all_listings:
        await push_event(session_id, "pipeline_error", {"message": "No listings found"})
        await close_session(session_id)
        return

    # Ranking Agent
    ranking_result = await call_agent("ranking_agent", session_id, {
        "listings": all_listings
    })
    if not ranking_result:
        await close_session(session_id)
        return

    # Haggling Agent — called once per target seller
    haggle_targets = [l for l in ranking_result["ranked_listings"] if l.get("haggle_flag")]
    for listing in haggle_targets[:5]:  # cap at 5 offers
        await call_agent("haggling_agent", session_id, {
            "listing": listing,
            "median_price": ranking_result["median_price"]
        })

    await push_event(session_id, "pipeline_complete", {"mode": "buy"})
    await close_session(session_id)

# ── Agent caller ────────────────────────────────────────────────

# Agent address registry — filled in after Mailbox registration
AGENT_ADDRESSES = {
    "vision_agent":          "agent1q...",  # Fill in after registration
    "ebay_research_agent":   "agent1q...",
    "pricing_agent":         "agent1q...",
    "depop_listing_agent":   "agent1q...",
    "depop_search_agent":    "agent1q...",
    "ebay_search_agent":     "agent1q...",
    "mercari_search_agent":  "agent1q...",
    "offerup_search_agent":  "agent1q...",
    "ranking_agent":         "agent1q...",
    "haggling_agent":        "agent1q...",
}

# Agent local ports (for direct HTTP fallback during development)
AGENT_PORTS = {
    "vision_agent":          8001,
    "ebay_research_agent":   8002,
    "pricing_agent":         8003,
    "depop_listing_agent":   8004,
    "depop_search_agent":    8005,
    "ebay_search_agent":     8006,
    "mercari_search_agent":  8007,
    "offerup_search_agent":  8008,
    "ranking_agent":         8009,
    "haggling_agent":        8010,
}

async def call_agent(agent_name: str, session_id: str, payload: dict) -> dict | None:
    """
    Sends payload to a local agent via HTTP.
    Agents listen on their assigned port for direct task messages from FastAPI.
    This is separate from the Chat Protocol (which is for ASI:One discoverability).
    """
    port = AGENT_PORTS[agent_name]
    await push_event(session_id, "agent_started", {"agent_name": agent_name})
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"http://localhost:{port}/task",
                json={"session_id": session_id, "payload": payload}
            )
            if response.status_code == 200:
                result = response.json()
                await push_event(session_id, "agent_completed", {
                    "agent_name": agent_name,
                    "summary": result.get("summary", "Done")
                })
                return result
            else:
                await push_event(session_id, "agent_error", {
                    "agent_name": agent_name,
                    "error": f"HTTP {response.status_code}"
                })
                return None
    except Exception as e:
        await push_event(session_id, "agent_error", {
            "agent_name": agent_name,
            "error": str(e)
        })
        return None

# ── SSE stream endpoint ──────────────────────────────────────────

@app.get("/stream/{session_id}")
async def stream(session_id: str, request: Request):
    q = get_session(session_id)
    if not q:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                if event is None:  # sentinel — pipeline complete
                    break
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"])
                }
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield {"event": "ping", "data": "{}"}

    return EventSourceResponse(event_generator())

# ── Internal event endpoint (agents → FastAPI) ───────────────────

@app.post("/internal/event/{session_id}")
async def internal_event(session_id: str, req: InternalEventRequest):
    """
    Agents call this to push events into the SSE queue.
    Protected by internal secret so only our agents can call it.
    """
    if req.secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    await push_event(session_id, req.event_type, req.data)
    return {"ok": True}

# ── Result endpoint (fallback if SSE drops) ──────────────────────

results_store: dict = {}

@app.post("/internal/result/{session_id}")
async def store_result(session_id: str, req: dict):
    results_store[session_id] = req
    return {"ok": True}

@app.get("/result/{session_id}")
async def get_result(session_id: str):
    result = results_store.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result
```

### 2.3 Test the SSE endpoint locally

```bash
# Terminal 1
uvicorn main:app --reload --port 8000

# Terminal 2 — test SSE stream
curl -N http://localhost:8000/stream/test-session-123
# Should hang open (session doesn't exist yet — that's fine, 404 is correct)

# Test health
curl http://localhost:8000/health
# Should return {"status": "ok"}
```

---

## Phase 3 — Base Agent Template
**Target: 30 minutes. Build this once, clone it 9 times.**

Every agent has two responsibilities:
1. **Task endpoint** (`/task`) — receives work from FastAPI, does it, returns results
2. **Chat Protocol** — makes agent discoverable by ASI:One on Agentverse

### 3.1 Base Agent (agents/base_agent.py)

```python
"""
Base agent template. Every agent inherits this pattern.
- Runs a FastAPI task server on its assigned port
- Runs a uAgent with Chat Protocol for Agentverse discoverability
- Both run concurrently via asyncio
"""
import asyncio
import os
import json
import httpx
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI
from uvicorn import Config, Server
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)
from dotenv import load_dotenv

load_dotenv()

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")

async def push_log(session_id: str, agent_name: str, message: str):
    """Push a log event back to FastAPI SSE queue."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{FASTAPI_BASE_URL}/internal/event/{session_id}",
                json={
                    "secret": INTERNAL_SECRET,
                    "session_id": session_id,
                    "event_type": "agent_log",
                    "data": {"agent_name": agent_name, "message": message}
                }
            )
        except Exception:
            pass  # Never let logging crash the agent
```

### 3.2 Vision Agent — Full Example (agents/vision_agent.py)

This is the most complete example. All other agents follow the same structure.

```python
import asyncio
import os
import json
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, EndSessionContent, TextContent, chat_protocol_spec
)
from dotenv import load_dotenv
import httpx
import base64

load_dotenv()

AGENT_NAME = "VisionAgent"
AGENT_PORT = 8001
AGENT_SEED = os.getenv("VISION_AGENT_SEED")
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NANO_BANANA_API_KEY = os.getenv("NANO_BANANA_API_KEY")

# ── FastAPI task server ──────────────────────────────────────────

task_app = FastAPI()

class TaskRequest(BaseModel):
    session_id: str
    payload: dict

@task_app.post("/task")
async def handle_task(req: TaskRequest):
    session_id = req.session_id
    image_b64 = req.payload.get("image_b64")

    await push_log(session_id, AGENT_NAME, "Analyzing item with Gemini Vision...")

    # Call Gemini Vision — Person 3 implements this function
    vision_result = await identify_item(image_b64, session_id)

    await push_log(session_id, AGENT_NAME, f"Identified: {vision_result['brand']} {vision_result['model']}")
    await push_log(session_id, AGENT_NAME, "Generating clean product photo...")

    # Call Nano Banana — Person 3 implements this function
    clean_photo_url = await generate_clean_photo(image_b64, session_id)

    result = {**vision_result, "clean_photo_url": clean_photo_url, "summary": f"Identified as {vision_result['brand']} {vision_result['model']}"}
    return JSONResponse(content=result)

async def push_log(session_id: str, agent_name: str, message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{FASTAPI_BASE_URL}/internal/event/{session_id}", json={
                "secret": INTERNAL_SECRET,
                "session_id": session_id,
                "event_type": "agent_log",
                "data": {"agent_name": agent_name, "message": message}
            })
        except Exception:
            pass

# ── Stub functions — Person 3 fills these in ────────────────────

async def identify_item(image_b64: str, session_id: str) -> dict:
    """Person 3 implements this using Gemini Vision API."""
    # STUB — returns mock data until Person 3 implements
    return {
        "item_name": "Air Jordan 1 Retro High OG",
        "brand": "Nike",
        "model": "Air Jordan 1",
        "condition": "good",
        "confidence": 0.92
    }

async def generate_clean_photo(image_b64: str, session_id: str) -> str:
    """Person 3 implements this using Nano Banana API."""
    # STUB — returns placeholder until Person 3 implements
    return "https://placeholder.com/clean_photo.jpg"

# ── uAgent with Chat Protocol (for ASI:One discoverability) ─────

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT + 100,  # uAgent runs on 8101, task server on 8001
    mailbox=True,
    publish_agent_details=True,
)

chat_proto = Protocol(spec=chat_protocol_spec)

@chat_proto.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Handles messages from ASI:One for judge verification."""
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id
    ))
    # Extract text from message
    text = ""
    for item in msg.content:
        if isinstance(item, TextContent):
            text = item.text
            break

    # Respond with agent capability description
    response = f"I am the VisionAgent. I identify items from photos using Gemini Vision and generate clean product photos. Send me a photo description and I'll analyze it. Query received: '{text}'"

    await ctx.send(sender, ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=response), EndSessionContent(type="end-session")]
    ))

agent.include(chat_proto, publish_manifest=True)

# ── Run both servers concurrently ───────────────────────────────

async def run_task_server():
    config = uvicorn.Config(task_app, host="0.0.0.0", port=AGENT_PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def run_uagent():
    await agent.run_async()

async def main():
    print(f"[{AGENT_NAME}] Starting task server on port {AGENT_PORT}")
    print(f"[{AGENT_NAME}] uAgent address: {agent.address}")
    await asyncio.gather(run_task_server(), run_uagent())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Phase 4 — Scaffold All 10 Agents
**Target: 60 minutes. Copy vision_agent.py, change names/ports/stubs.**

### Port assignments:

| Agent | Task Port | uAgent Port |
|---|---|---|
| vision_agent | 8001 | 8101 |
| ebay_research_agent | 8002 | 8102 |
| pricing_agent | 8003 | 8103 |
| depop_listing_agent | 8004 | 8104 |
| depop_search_agent | 8005 | 8105 |
| ebay_search_agent | 8006 | 8106 |
| mercari_search_agent | 8007 | 8107 |
| offerup_search_agent | 8008 | 8108 |
| ranking_agent | 8009 | 8109 |
| haggling_agent | 8010 | 8110 |

### For each agent, change:
1. `AGENT_NAME` string
2. `AGENT_PORT` integer
3. `AGENT_SEED` env var name
4. `/task` handler — what it receives and what it returns
5. Chat Protocol response text — describe agent's capability
6. Stub functions — leave as stubs, teammates implement

### Stub /task handlers for each agent:

**ebay_research_agent** — receives `{item_name, brand, model, condition}`, returns `{comps: [...], platform, raw_count, summary}`

**pricing_agent** — receives `{comps, condition, item_name, brand}`, returns `{recommended_price, profit_margin, median_price, listing_description, summary}`

**depop_listing_agent** — receives `{item_name, brand, model, condition, clean_photo_url, recommended_price, listing_description}`, returns `{form_screenshot_url, listing_preview, summary}`

**depop_search_agent** — receives `{query}`, returns `{platform: "depop", listings: [...], summary}`

**ebay_search_agent** — receives `{query}`, returns `{platform: "ebay", listings: [...], summary}`

**mercari_search_agent** — receives `{query}`, returns `{platform: "mercari", listings: [...], summary}`

**offerup_search_agent** — receives `{query}`, returns `{platform: "offerup", listings: [...], status, summary}`

**ranking_agent** — receives `{listings: [...]}`, returns `{ranked_listings: [...], median_price, summary}`

**haggling_agent** — receives `{listing, median_price}`, returns `{seller, platform, offer_price, status, summary}`

---

## Phase 5 — Agent Runner
**Target: 15 minutes.**

```python
# run_agents.py — starts all 10 agents as subprocesses
import subprocess
import sys
import os

agents = [
    "agents/vision_agent.py",
    "agents/ebay_research_agent.py",
    "agents/pricing_agent.py",
    "agents/depop_listing_agent.py",
    "agents/depop_search_agent.py",
    "agents/ebay_search_agent.py",
    "agents/mercari_search_agent.py",
    "agents/offerup_search_agent.py",
    "agents/ranking_agent.py",
    "agents/haggling_agent.py",
]

procs = []
for agent in agents:
    p = subprocess.Popen([sys.executable, agent], env=os.environ.copy())
    procs.append(p)
    print(f"Started {agent} (PID {p.pid})")

print("\nAll agents started. Press Ctrl+C to stop all.\n")
try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    print("\nStopping all agents...")
    for p in procs:
        p.terminate()
```

### Test the full stack locally:

```bash
# Terminal 1 — Start all agents
python run_agents.py

# Terminal 2 — Start FastAPI
uvicorn main:app --reload --port 8000

# Terminal 3 — Test SELL pipeline end to end
curl -X POST http://localhost:8000/sell/start \
  -H "Content-Type: application/json" \
  -d '{"image_b64": "fake_base64_for_testing"}'
# Returns {"session_id": "some-uuid"}

# Terminal 4 — Listen to SSE stream (replace UUID)
curl -N http://localhost:8000/stream/some-uuid
# Should see events streaming as pipeline runs
```

---

## Phase 6 — Agentverse Mailbox Registration
**Target: 30 minutes. Browser + terminal steps.**

Do this for each of the 10 agents. The process is identical for all.

### Prerequisites:
- All agents must be running locally (`python run_agents.py`)
- You must be signed into https://agentverse.ai

### Registration steps (repeat for each agent):

**Step 1:** Run the agent and copy the Inspector URL from terminal output:
```
INFO: [VisionAgent]: Agent inspector available at https://agentverse.ai/inspect/?uri=http://127.0.0.1:8101&address=agent1q...
```

**Step 2:** Open the Inspector URL in your browser

**Step 3:** Click **Connect** → Select **Mailbox** → Click **OK, got it**

**Step 4:** Terminal output should show:
```
INFO: [VisionAgent]: Mailbox access token acquired
INFO: [mailbox]: Successfully registered as mailbox agent in Agentverse
```

**Step 5:** Go to https://agentverse.ai → **Agents** tab → Find your agent (tagged "Mailbox")

**Step 6:** Click agent → **Edit** → Add description and keywords:

| Agent | Description | Keywords |
|---|---|---|
| VisionAgent | Identifies items from photos using Gemini Vision and generates clean product images | vision, image, identification, resale |
| EbayResearchAgent | Scrapes eBay sold listings to find real market comps for items | ebay, research, pricing, comps |
| PricingAgent | Calculates profit margins and recommends listing prices for resale | pricing, margin, resale, profit |
| DepopListingAgent | Automatically populates Depop listing forms with item details | depop, listing, resale, automation |
| DepopSearchAgent | Searches Depop for active listings matching a query | depop, search, buy, listings |
| EbaySearchAgent | Searches eBay active listings matching a query | ebay, search, buy, listings |
| MercariSearchAgent | Searches Mercari active listings matching a query | mercari, search, buy, listings |
| OfferUpSearchAgent | Searches OfferUp active listings matching a query | offerup, search, buy, listings |
| RankingAgent | Ranks resale listings by price, condition, and seller credibility | ranking, scoring, resale, comparison |
| HagglingAgent | Generates and sends optimized offer messages to resale sellers | haggling, negotiation, offer, resale |

**Step 7:** Copy each agent's address from the terminal output and paste into `AGENT_ADDRESSES` dict in `main.py`

```
agent1q... → AGENT_ADDRESSES["vision_agent"]
```

### Verify all 10 are Active:
> **Browser step:** Go to https://agentverse.ai/agents → Filter by "Mailbox" → Confirm all 10 show green Active badge

---

## Phase 7 — Render Deployment
**Target: 20 minutes.**

### 7.1 Create render.yaml in backend/

```yaml
services:
  - type: web
    name: resale-agent-backend
    env: python
    plan: starter  # paid — needed for headed Chromium memory
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: AGENTVERSE_API_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: NANO_BANANA_API_KEY
        sync: false
      - key: INTERNAL_SECRET
        sync: false
      - key: VISION_AGENT_SEED
        sync: false
      - key: EBAY_RESEARCH_AGENT_SEED
        sync: false
      - key: PRICING_AGENT_SEED
        sync: false
      - key: DEPOP_LISTING_AGENT_SEED
        sync: false
      - key: DEPOP_SEARCH_AGENT_SEED
        sync: false
      - key: EBAY_SEARCH_AGENT_SEED
        sync: false
      - key: MERCARI_SEARCH_AGENT_SEED
        sync: false
      - key: OFFERUP_SEARCH_AGENT_SEED
        sync: false
      - key: RANKING_AGENT_SEED
        sync: false
      - key: HAGGLING_AGENT_SEED
        sync: false
      - key: FASTAPI_BASE_URL
        value: https://your-app-name.onrender.com  # update after first deploy
```

### 7.2 Add startup script for agents

Since Render runs one process, you need to start agents alongside FastAPI in a startup script.

Create `start.sh`:
```bash
#!/bin/bash
# Start all agents in background
python run_agents.py &
# Start FastAPI
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Update render.yaml startCommand:
```yaml
startCommand: bash start.sh
```

### 7.3 Deploy to Render

> **Browser steps:**
> 1. Go to https://render.com → New → Web Service
> 2. Connect GitHub repo → Select your backend repo
> 3. Render auto-detects Python
> 4. Set Start Command: `bash start.sh`
> 5. Add all environment variables from .env (one by one in dashboard)
> 6. Select **Starter** plan (not free — needs memory for Chromium)
> 7. Click **Create Web Service**
> 8. Wait for deploy (3-5 minutes)
> 9. Copy the `.onrender.com` URL
> 10. Update `FASTAPI_BASE_URL` env var with this URL
> 11. Trigger redeploy

### 7.4 Verify deployment

```bash
curl https://your-app.onrender.com/health
# Should return {"status": "ok"}
```

### 7.5 Update FASTAPI_BASE_URL in all agent .env files

After getting the Render URL, update `.env`:
```
FASTAPI_BASE_URL=https://your-app.onrender.com
```

Push to repo → Render auto-redeploys.

---

## Phase 8 — Integration Contracts for Teammates

Send these to teammates in GC immediately after Phase 2 is done:

### For Person 2 (Browser Use):

Your agents receive tasks at these endpoints:
- `POST http://localhost:8002/task` → EbayResearchAgent
- `POST http://localhost:8004/task` → DepopListingAgent
- `POST http://localhost:8005/task` → DepopSearchAgent
- `POST http://localhost:8006/task` → EbaySearchAgent
- `POST http://localhost:8007/task` → MercariSearchAgent
- `POST http://localhost:8008/task` → OfferUpSearchAgent
- `POST http://localhost:8010/task` → HagglingAgent

Body: `{"session_id": "...", "payload": {...}}`

Use `push_log(session_id, AGENT_NAME, message)` to stream live logs to the frontend.

Return JSON from `/task` with a `summary` field (one sentence, shown in agent feed).

### For Person 3 (AI Pipeline):

Your functions live in:
- `vision_agent.py` → `identify_item()` and `generate_clean_photo()`
- `pricing_agent.py` → `compute_margin()`
- `ranking_agent.py` → `rank_listings()`
- `haggling_agent.py` → `generate_offer_message()`

I've left stubs in each file. Find `# Person 3 implements this` comments and fill them in.

### For Person 4 (Frontend):

Backend base URL (local): `http://localhost:8000`
Backend base URL (Render): `https://your-app.onrender.com`

SSE endpoint: `GET /stream/{session_id}` — connect as EventSource

Event types to handle:
```javascript
"pipeline_started"  → { mode: "sell" | "buy" }
"agent_started"     → { agent_name: string }
"agent_log"         → { agent_name: string, message: string }
"agent_completed"   → { agent_name: string, summary: string }
"agent_error"       → { agent_name: string, error: string }
"listing_found"     → { platform: string, listing: object }  // BUY only
"offer_sent"        → { seller: string, platform: string, status: string }  // BUY only
"pipeline_complete" → { mode: string }
"ping"              → keepalive, ignore
```

Start SELL: `POST /sell/start` body: `{"image_b64": "..."}`
Start BUY: `POST /buy/start` body: `{"query": "Nike Air Jordan 1 Chicago"}`
Both return: `{"session_id": "uuid"}`

---

## Phase 9 — ASI:One Verification (Fetch.ai Deliverable)
**Do this when agents are all registered and backend is live on Render.**

### Generate the ASI:One Chat session URL:

> **Browser steps:**
> 1. Go to https://asi1.ai
> 2. Sign in
> 3. In chat, type: "I want to flip items I find at thrift stores. Can you help me identify an item and list it for resale?"
> 4. ASI:One should discover your agents via Agentverse
> 5. Copy the URL of this chat session
> 6. This is your Fetch.ai deliverable: **ASI:One Chat session URL**

If ASI:One doesn't auto-discover your agents:
> - Go to https://agentverse.ai → Your agents → Verify Chat Protocol is published
> - Check agent README has keywords
> - Try: "@VisionAgent identify this thrift store item for resale"

### Collect all deliverable URLs:

```
ASI:One Chat Session: https://asi1.ai/chat/...
VisionAgent:          https://agentverse.ai/agents/...
EbayResearchAgent:    https://agentverse.ai/agents/...
PricingAgent:         https://agentverse.ai/agents/...
DepopListingAgent:    https://agentverse.ai/agents/...
DepopSearchAgent:     https://agentverse.ai/agents/...
EbaySearchAgent:      https://agentverse.ai/agents/...
MercariSearchAgent:   https://agentverse.ai/agents/...
OfferUpSearchAgent:   https://agentverse.ai/agents/...
RankingAgent:         https://agentverse.ai/agents/...
HagglingAgent:        https://agentverse.ai/agents/...
```

Paste all of these into the Devpost submission.

---

## Phase 10 — README for Each Agent (Fetch.ai Requirement)

Each agent needs a README.md with the `innovationlab` badge. Create `agents/README_TEMPLATE.md` and customize per agent:

```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)

# [Agent Name]

**Address:** `agent1q...`

## Description
[One paragraph description of what this agent does]

## Capabilities
- [Capability 1]
- [Capability 2]

## Input
```json
{ "field": "type description" }
```

## Output
```json
{ "field": "type description" }
```

## Example Query (via ASI:One)
"[Example of how to invoke this agent through natural language]"
```

Upload each README to the agent's Agentverse profile page.

---

## Troubleshooting

### Agent won't start / Port conflict
```bash
lsof -ti:8001 | xargs kill -9  # Kill whatever is on port 8001
```

### Mailbox registration fails
- Check `AGENTVERSE_API_KEY` in .env is correct
- Ensure agent is running before opening Inspector URL
- Check internet connectivity
- Restart agent: `Ctrl+C` then rerun

### Agent not showing in Agentverse
- Wait 30 seconds after registration — there's propagation delay
- Check at https://agentverse.ai/agents → filter "Local" or "Mailbox"
- Verify agent logs show: `Successfully registered as mailbox agent in Agentverse`

### SSE stream closes immediately
- Check session was created before connecting to `/stream/{session_id}`
- Verify `create_session()` called before returning session_id from `/sell/start`

### Render deploy fails
- Check requirements.txt includes all packages
- Check start command: `bash start.sh`
- Check all env vars are set in Render dashboard
- Check logs in Render dashboard for specific error

### Agent address not in AGENT_ADDRESSES dict
- Run agents first, copy address from terminal output
- Format: `agent1q...` (starts with `agent1q`)
- Paste into `AGENT_ADDRESSES` in `main.py`

---

## Priority Order

If time gets tight, here's what to cut:

**Must ship:**
1. FastAPI + SSE infrastructure (Phase 2) — everything else dead without this
2. All 10 agents scaffolded with stubs (Phase 4) — teammates can't integrate without
3. At least VisionAgent + EbayResearchAgent + PricingAgent + DepopListingAgent registered (SELL pipeline)

**Should ship:**
4. All 10 agents registered on Agentverse
5. Render deployment
6. BUY pipeline agents registered

**Cut if no time:**
7. ASI:One verification session URL (generate last 30 min before submission)
8. Per-agent README files (do minimum viable version)

---

## Key URLs

| Resource | URL |
|---|---|
| Agentverse dashboard | https://agentverse.ai/agents |
| ASI:One chat | https://asi1.ai/chat |
| Fetch.ai Chat Protocol docs | https://uagents.fetch.ai/docs/examples/asi-1 |
| Mailbox setup docs | https://uagents.fetch.ai/docs/agentverse/mailbox |
| FastAPI SSE docs | https://fastapi.tiangolo.com/tutorial/server-sent-events/ |
| Render deploy docs | https://render.com/docs/deploy-fastapi |
| Devpost submission | https://diamondhacks-2026.devpost.com |
