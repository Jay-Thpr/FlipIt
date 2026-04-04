# Browser Use — Implementation Guide (Person 2)
**DiamondHacks 2026 | Complete execution reference**

---

## What You Own

Every Browser Use task in the project:

| Agent | Task Port | What it does |
|---|---|---|
| EbayResearchAgent | 8002 | Scrape eBay sold listings for comps |
| DepopListingAgent | 8004 | Populate Depop listing form up to submit |
| DepopSearchAgent | 8005 | Find active Depop listings for query |
| EbaySearchAgent | 8006 | Find active eBay listings for query |
| MercariSearchAgent | 8007 | Find active Mercari listings for query |
| OfferUpSearchAgent | 8008 | Find active OfferUp listings (best effort) |
| HagglingAgent | 8010 | Send one offer message to one seller |

Each agent is a FastAPI task server (receives work from Person 1's orchestrator) that runs Browser Use internally. You do not build the uAgent wrapper — Person 1 owns that shell. You implement the `/task` handler and the Browser Use logic inside it.

---

## Choose the Right Browser Use Path

This guide is for the **open-source local `browser-use` library** running inside this repo's FastAPI task servers.

Browser Use also offers a separate **Cloud** product with managed browsers, proxies, CAPTCHA solving, live preview, persistent profiles, and a different SDK/API surface. If you want the fastest path to managed production infrastructure, Browser Use Cloud may be the better fit. If you want tight control inside the existing FastAPI agent architecture, local `browser-use` remains the correct approach for this repo.

Use this rule of thumb:
- **Local OSS `browser-use`**: best for hackathon builds, local debugging, custom FastAPI orchestration, and direct control over browser sessions.
- **Browser Use Cloud**: best for managed stealth infrastructure, residential proxies, live preview, workspaces/files, and lower browser-ops overhead.

If this repo adopts Browser Use Cloud later, use **API v3 only**. Browser Use documents v2 as legacy and not recommended for new integrations.

---

## Current Repo Contract (Read This Before Copying Any Snippet)

The code examples in this guide show Browser Use patterns, but the **actual repo contract** is defined by the current FastAPI scaffold:

- Browser Use agents must accept `backend.schemas.AgentTaskRequest`, not a custom `{ session_id, payload }` shape.
- Browser Use agents must return `backend.schemas.AgentTaskResponse`.
- Step names and pipeline wiring come from `backend.schemas.AGENT_INPUT_CONTRACTS`; do not invent new step names or rename fields ad hoc.
- Keep Browser Use logic behind the `/task` handler for now. The Fetch.ai Chat Protocol wrapper is still scaffold-level in this repo, so Browser Use work should not depend on direct uAgent message handling yet.
- Audit live runtime prerequisites with `./.venv/bin/python -m backend.browser_use_runtime_audit`.
- Validate agent and pipeline behavior with `python scripts/browser_use_validation.py --group pipeline` before running targeted live cases.

Current orchestrator events use underscore names such as:
- `pipeline_started`
- `agent_started`
- `agent_completed`
- `agent_error`
- `agent_retrying`
- `pipeline_complete`
- `pipeline_failed`

If you add custom Browser Use events such as `listing_found` or `offer_sent`, make sure FastAPI, mobile UI, and PRD event naming stay aligned.

Also note that the PRD's BUY flow needs richer fields than the current scaffold exposes. Before implementing final ranking or haggling behavior, confirm the schema can carry seller identity, seller credibility metrics, recency, listing URL, and send status.

The current shared Browser Use helpers live in:
- `backend/agents/browser_use_support.py` for lazy runtime setup, profile paths, and structured Browser Use execution
- `backend/agents/browser_use_marketplaces.py` for marketplace URL builders, task strings, and Browser Use-specific result schemas

Prefer extending those helpers instead of re-embedding Browser Use setup inside each agent.

---

## Phase 0 — Installation (Do This First)

These installation steps are for the **local open-source Browser Use workflow only**. They do **not** apply to Browser Use Cloud.

```bash
cd backend
source venv/bin/activate

# Install browser-use and dependencies
pip install browser-use langchain-google-genai patchright

# Install Chromium (browser-use's default browser)
uvx browser-use install
# OR
playwright install chromium --with-deps

# Install patchright for stealth (separate install)
python -m patchright install chromium
```

If you switch to Browser Use Cloud later, install the Cloud SDK instead:

```bash
pip install --upgrade browser-use-sdk
```

Add to `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key
ANONYMIZED_TELEMETRY=false
```

### Verify installation works:

```python
# test_browser.py — run this first before touching agents
import asyncio
from browser_use import Agent, BrowserSession
from browser_use.browser import BrowserProfile
from langchain_google_genai import ChatGoogleGenerativeAI

async def test():
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    profile = BrowserProfile(headless=False, stealth=True)
    session = BrowserSession(browser_profile=profile)

    agent = Agent(
        task="Go to google.com and tell me the title of the page",
        llm=llm,
        browser_session=session
    )
    history = await agent.run(max_steps=5)
    print(history.final_result())

asyncio.run(test())
```

If you see the page title printed, you're good. If not, check Chromium path.

### Cloud API key safety

If Browser Use Cloud is ever added to this repo, only send Browser Use API keys to:
- `api.browser-use.com`
- `cloud.browser-use.com`

Do not send `bu_...` keys to any other domain.

---

## Core Concepts (Read Before Writing Any Agent)

### How Browser Use Works

Browser Use is a Python library that gives an LLM real hands on a browser. It:
1. Takes a natural language `task` string
2. Shows the LLM the current page state (DOM structure + optional screenshot)
3. LLM decides what to click, type, scroll, or extract
4. Executes the action via Playwright
5. Loops until task is complete or `max_steps` is hit

You describe what you want in plain English. The LLM figures out how to do it.

### The Three Key Classes

```python
from browser_use import Agent, BrowserSession
from browser_use.browser import BrowserProfile

# BrowserProfile — static config template
profile = BrowserProfile(
    headless=False,        # False = visible browser (more stealth, required for some sites)
    stealth=True,          # Uses patchright instead of plain Playwright (anti-bot)
    user_data_dir="./profiles/depop",  # Persists cookies/login across runs
    keep_alive=True,       # Don't close browser between agent.run() calls
)

# BrowserSession — runtime instance
session = BrowserSession(browser_profile=profile)

# Agent — the LLM-powered actor
agent = Agent(
    task="Your task description",
    llm=llm,
    browser_session=session,
    max_steps=20,
)

history = await agent.run()
result = history.final_result()  # The extracted content from last step
```

### Result Extraction

```python
history = await agent.run()

history.final_result()        # String — last extracted content
history.is_done()             # Bool — did agent declare completion?
history.has_errors()          # Bool — any errors?
history.extracted_content()   # List of all extracted content across steps
history.urls()                # List of URLs visited
```

### Structured Output (Pydantic)

When you need structured JSON back, use `output_model_schema`:

```python
from pydantic import BaseModel
from typing import List

class Listing(BaseModel):
    price: float
    condition: str
    seller: str
    url: str

class SearchResult(BaseModel):
    listings: List[Listing]
    platform: str

agent = Agent(
    task="Search Depop for Air Jordan 1 and extract the top 10 listings",
    llm=llm,
    browser_session=session,
    output_model_schema=SearchResult,
)
history = await agent.run()
result = history.final_result(SearchResult)  # Returns SearchResult instance
```

### Task Prompt Engineering

Task strings are the most important thing you write. Be extremely specific:

**Bad task:**
```
"Search eBay for sold Jordan 1s and get the prices"
```

**Good task:**
```
"Navigate to https://www.ebay.com/sch/i.html?_nkw=Nike+Air+Jordan+1+Retro+High&LH_Sold=1&LH_Complete=1&LH_ItemCondition=3000&_sop=13&_ipg=48
Wait for results to load.
Extract from the first 15 sold listings: sold price (numbers only, in USD), date sold, item condition, listing title.
Only include listings sold within the last 90 days.
Return results as a JSON list."
```

Rules for good tasks:
- Provide the exact URL — don't make the agent search for it
- Be explicit about what to wait for
- Specify exactly what data to extract and in what format
- Include filters (date range, condition) in the task
- Say "Return results as JSON" to get clean output

---

## Pre-Session Setup — Login Persistence

**Critical:** Depop, eBay, OfferUp all need to be logged in before the demo. You'll pre-warm sessions using `user_data_dir` so login persists across agent runs.

### Step 1 — Create login profiles (do this once, before hackathon)

```python
# setup_sessions.py — run this ONCE manually to log in to each platform
import asyncio
from browser_use import BrowserSession
from browser_use.browser import BrowserProfile

async def setup_depop_session():
    """Open browser, log in manually, then close. Session saved to disk."""
    profile = BrowserProfile(
        headless=False,
        stealth=True,
        user_data_dir="./profiles/depop",
        keep_alive=False
    )
    session = BrowserSession(browser_profile=profile)
    await session.start()
    page = await session.get_current_page()
    await page.goto("https://www.depop.com/login/")

    print("LOG IN TO DEPOP MANUALLY IN THE BROWSER WINDOW")
    print("Press Enter here when you're logged in...")
    input()

    await session.stop()
    print("Depop session saved to ./profiles/depop")

async def setup_offerup_session():
    profile = BrowserProfile(
        headless=False,
        stealth=True,
        user_data_dir="./profiles/offerup",
        keep_alive=False
    )
    session = BrowserSession(browser_profile=profile)
    await session.start()
    page = await session.get_current_page()
    await page.goto("https://offerup.com/login/")

    print("LOG IN TO OFFERUP MANUALLY IN THE BROWSER WINDOW")
    print("Press Enter here when you're logged in...")
    input()

    await session.stop()
    print("OfferUp session saved to ./profiles/offerup")

async def main():
    await setup_depop_session()
    await setup_offerup_session()

asyncio.run(main())
```

Run this now:
```bash
python setup_sessions.py
```

### Step 2 — Use saved sessions in agents

```python
# In DepopListingAgent and DepopSearchAgent:
profile = BrowserProfile(
    headless=False,
    stealth=True,
    user_data_dir="./profiles/depop",  # Already logged in
    keep_alive=True
)
```

The agent will load this profile and be pre-authenticated. No login step needed.

---

## BrowserProfile Configuration Reference

```python
from browser_use.browser import BrowserProfile

profile = BrowserProfile(
    # --- Stealth (critical for eBay/Depop) ---
    stealth=True,              # Use patchright — anti-detection
    headless=False,            # Visible browser = more human-like fingerprint
                               # headless=True will get blocked by eBay

    # --- Session persistence ---
    user_data_dir="./profiles/depop",  # Persist cookies and login
    keep_alive=True,           # Don't close between agent.run() calls

    # --- Security ---
    allowed_domains=["depop.com", "www.depop.com"],  # Lock agent to one site

    # --- Performance ---
    viewport={"width": 1280, "height": 800},

    # --- Disable telemetry ---
    # Set ANONYMIZED_TELEMETRY=false in .env
)
```

**Key insight:** `stealth=True` switches from Playwright to Patchright under the hood. Patchright patches Chrome's CDP detection signals — the same signals eBay and Depop use to detect bots. Always use it.

---

## Agent-by-Agent Implementation

### Agent 1 — EbayResearchAgent (SELL, Port 8002)

This agent searches eBay **sold listings** to pull real market comps.

```python
# agents/ebay_research_agent.py
import asyncio
import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn
import httpx
from browser_use import Agent, BrowserSession
from browser_use.browser import BrowserProfile
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

AGENT_NAME = "EbayResearchAgent"
AGENT_PORT = 8002
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")

task_app = FastAPI()

class TaskRequest(BaseModel):
    session_id: str
    payload: dict

# Pydantic output schema
class Comp(BaseModel):
    price: float
    condition: str
    date_sold: str
    title: str

class ResearchResult(BaseModel):
    comps: List[Comp]
    platform: str
    raw_count: int

async def push_log(session_id: str, message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{FASTAPI_BASE_URL}/internal/event/{session_id}", json={
                "secret": INTERNAL_SECRET,
                "session_id": session_id,
                "event_type": "agent_log",
                "data": {"agent_name": AGENT_NAME, "message": message}
            })
        except Exception:
            pass

@task_app.post("/task")
async def handle_task(req: TaskRequest):
    session_id = req.session_id
    brand = req.payload.get("brand", "")
    model = req.payload.get("model", "")
    condition = req.payload.get("condition", "good")

    await push_log(session_id, f"Searching eBay sold listings for {brand} {model}...")

    # Map condition to eBay condition codes
    condition_map = {
        "excellent": "1000",  # New / Like New
        "good": "3000",       # Used
        "fair": "5000"        # For parts
    }
    condition_code = condition_map.get(condition, "3000")

    # Build exact eBay sold listings URL
    query = f"{brand}+{model}".replace(" ", "+")
    url = (
        f"https://www.ebay.com/sch/i.html"
        f"?_nkw={query}"
        f"&LH_Sold=1"          # Sold listings only
        f"&LH_Complete=1"      # Completed listings
        f"&LH_ItemCondition={condition_code}"
        f"&_sop=13"            # Sort by most recently sold
        f"&_ipg=48"            # 48 results per page
    )

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    profile = BrowserProfile(
        headless=False,
        stealth=True,
        allowed_domains=["ebay.com", "www.ebay.com"]
    )
    session = BrowserSession(browser_profile=profile)

    task = f"""
Navigate to: {url}

Wait for the search results to fully load (look for listing cards with prices).

Extract from the FIRST 15 sold listings only:
- sold_price: the final sold price as a number in USD (strip $ and commas)
- condition: the item condition shown (New, Used, Good, etc.)
- date_sold: when it sold (e.g. "Mar 15, 2025")
- title: the full listing title

IMPORTANT rules:
- Only include listings that show a SOLD price (green or strikethrough price is NOT what we want — look for the price that appears under "Sold" listings)
- Skip any "Best Offer" listings where final price isn't shown
- If the page shows fewer than 5 results, still return what you have

Return a JSON object with this exact structure:
{{
  "comps": [
    {{"price": 145.00, "condition": "Used", "date_sold": "Mar 15, 2025", "title": "Nike Air Jordan 1..."}}
  ],
  "platform": "ebay",
  "raw_count": 15
}}
"""

    try:
        agent = Agent(
            task=task,
            llm=llm,
            browser_session=session,
            output_model_schema=ResearchResult,
            max_steps=15,
            max_failures=3
        )
        history = await agent.run()

        if history.has_errors() and not history.final_result():
            await push_log(session_id, "eBay blocked — trying Mercari fallback...")
            return await mercari_fallback(session_id, brand, model)

        result = history.final_result(ResearchResult)
        if result:
            await push_log(session_id, f"Found {len(result.comps)} sold comps from eBay")
            return JSONResponse(content={
                "comps": [c.dict() for c in result.comps],
                "platform": "ebay",
                "raw_count": result.raw_count,
                "summary": f"Found {len(result.comps)} sold comps — median will be calculated"
            })
        else:
            # Parse from raw text if structured output failed
            raw = history.final_result()
            await push_log(session_id, "Parsing raw eBay results...")
            return JSONResponse(content={
                "comps": [],
                "platform": "ebay",
                "raw_count": 0,
                "raw_text": raw,
                "summary": "eBay returned results — parsing needed"
            })

    except Exception as e:
        await push_log(session_id, f"eBay error: {str(e)[:100]} — trying Mercari...")
        return await mercari_fallback(session_id, brand, model)
    finally:
        await session.stop()

async def mercari_fallback(session_id: str, brand: str, model: str) -> JSONResponse:
    """Fallback to Mercari if eBay blocks."""
    await push_log(session_id, f"Searching Mercari for {brand} {model}...")

    query = f"{brand} {model}".replace(" ", "%20")
    url = f"https://www.mercari.com/search/?keyword={query}&status=sold_out"

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    profile = BrowserProfile(headless=False, stealth=True)
    session = BrowserSession(browser_profile=profile)

    task = f"""
Navigate to: {url}
Wait for sold listings to load.
Extract the first 15 sold listings: price (number, USD), condition, title.
Return as JSON: {{"comps": [{{"price": 0.0, "condition": "", "date_sold": "recent", "title": ""}}], "platform": "mercari", "raw_count": 0}}
"""
    try:
        agent = Agent(task=task, llm=llm, browser_session=session, max_steps=12)
        history = await agent.run()
        raw = history.final_result() or "[]"
        await push_log(session_id, "Mercari fallback complete")
        return JSONResponse(content={
            "comps": [],
            "platform": "mercari",
            "raw_count": 0,
            "raw_text": raw,
            "summary": "Mercari fallback — results available"
        })
    finally:
        await session.stop()

if __name__ == "__main__":
    uvicorn.run(task_app, host="0.0.0.0", port=AGENT_PORT, log_level="warning")
```

---

### Agent 2 — DepopListingAgent (SELL, Port 8004)

This agent opens Depop, navigates to listing creation, populates the entire form, and pauses before submit.

```python
# agents/depop_listing_agent.py
import asyncio
import os
import base64
import tempfile
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx
from browser_use import Agent, BrowserSession, Tools, ActionResult
from browser_use.browser import BrowserProfile
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

AGENT_NAME = "DepopListingAgent"
AGENT_PORT = 8004
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")

task_app = FastAPI()

class TaskRequest(BaseModel):
    session_id: str
    payload: dict

async def push_log(session_id: str, message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{FASTAPI_BASE_URL}/internal/event/{session_id}", json={
                "secret": INTERNAL_SECRET,
                "session_id": session_id,
                "event_type": "agent_log",
                "data": {"agent_name": AGENT_NAME, "message": message}
            })
        except Exception:
            pass

@task_app.post("/task")
async def handle_task(req: TaskRequest):
    session_id = req.session_id
    p = req.payload

    item_name = p.get("item_name", "Item")
    brand = p.get("brand", "")
    model_name = p.get("model", "")
    condition = p.get("condition", "good")
    clean_photo_url = p.get("clean_photo_url", "")
    recommended_price = p.get("recommended_price", 20.0)
    listing_description = p.get("listing_description", f"{brand} {model_name} in {condition} condition.")

    await push_log(session_id, "Opening Depop listing form...")

    # Map condition to Depop UI options
    condition_map = {
        "excellent": "Like New",
        "good": "Good",
        "fair": "Fair"
    }
    depop_condition = condition_map.get(condition, "Good")

    # Download clean photo to temp file for upload
    photo_path = await download_photo(clean_photo_url)

    # Custom tool to pause before submit
    tools = Tools()

    @tools.action("Pause before final submit — stop here and take screenshot")
    async def pause_before_submit(browser_session: BrowserSession) -> ActionResult:
        page = await browser_session.get_current_page()
        screenshot = await page.screenshot(full_page=False)
        # Save screenshot
        screenshot_path = f"/tmp/depop_listing_{session_id}.png"
        with open(screenshot_path, "wb") as f:
            f.write(screenshot)
        await push_log(session_id, "Listing form populated — paused before submit")
        return ActionResult(
            extracted_content=f"Form populated. Screenshot saved. Ready to post at price ${recommended_price}",
            is_done=True  # Tell agent to stop here
        )

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    profile = BrowserProfile(
        headless=False,
        stealth=True,
        user_data_dir="./profiles/depop",  # Pre-logged in session
        keep_alive=False,
        allowed_domains=["depop.com", "www.depop.com"]
    )
    session = BrowserSession(browser_profile=profile)

    title = f"{brand} {model_name} - {depop_condition.title()}"

    task = f"""
You are filling out a Depop listing form. Follow these steps EXACTLY in order:

1. Navigate to https://www.depop.com/sell/
2. Wait for the listing form to load
3. Upload the photo: click the photo upload area, upload the file at path: {photo_path}
4. Wait for the photo to appear in the preview
5. Fill in the item details:
   - Title: "{title}"
   - Description: "{listing_description}"
   - Category: select the most appropriate category for "{item_name}"
   - Condition: select "{depop_condition}"
   - Price: enter "{recommended_price}" (numbers only, no $ sign)
6. If there are size fields, skip them or select "One Size"
7. Once ALL fields are filled, call the pause_before_submit tool
8. DO NOT click the final "List Item" or "Post" button — stop at step 7

Important:
- If you can't find a field, skip it and continue
- The form may have multiple steps — complete each before moving to next
- If any step fails, log what failed and continue with the next step
"""

    try:
        agent = Agent(
            task=task,
            llm=llm,
            browser_session=session,
            tools=tools,
            max_steps=25,
            max_failures=5,
            use_vision=True  # Need vision to see form fields
        )
        history = await agent.run()

        screenshot_path = f"/tmp/depop_listing_{session_id}.png"
        screenshot_b64 = ""
        if os.path.exists(screenshot_path):
            with open(screenshot_path, "rb") as f:
                screenshot_b64 = base64.b64encode(f.read()).decode()

        return JSONResponse(content={
            "form_screenshot_b64": screenshot_b64,
            "listing_preview": {
                "title": title,
                "price": recommended_price,
                "description": listing_description,
                "condition": depop_condition
            },
            "summary": f"Depop listing ready — '{title}' at ${recommended_price}"
        })
    finally:
        await session.stop()
        if photo_path and os.path.exists(photo_path):
            os.unlink(photo_path)

async def download_photo(url: str) -> str:
    """Download photo to temp file, return path."""
    if not url or url.startswith("https://placeholder"):
        # Create a dummy photo for testing
        import PIL.Image
        img = PIL.Image.new("RGB", (400, 400), color=(200, 200, 200))
        path = f"/tmp/listing_photo_{os.getpid()}.jpg"
        img.save(path)
        return path

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=30)
            path = f"/tmp/listing_photo_{os.getpid()}.jpg"
            with open(path, "wb") as f:
                f.write(resp.content)
            return path
        except Exception:
            return ""

if __name__ == "__main__":
    uvicorn.run(task_app, host="0.0.0.0", port=AGENT_PORT, log_level="warning")
```

---

### Agent 3 — DepopSearchAgent (BUY, Port 8005)

```python
# agents/depop_search_agent.py
import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import uvicorn
import httpx
from browser_use import Agent, BrowserSession
from browser_use.browser import BrowserProfile
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

AGENT_NAME = "DepopSearchAgent"
AGENT_PORT = 8005
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")

task_app = FastAPI()

class TaskRequest(BaseModel):
    session_id: str
    payload: dict

class DepopListing(BaseModel):
    price: float
    condition: str
    seller: str
    url: str
    title: str
    reviews: int = 0

class DepopSearchResult(BaseModel):
    platform: str
    listings: List[DepopListing]

async def push_log(session_id: str, message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{FASTAPI_BASE_URL}/internal/event/{session_id}", json={
                "secret": INTERNAL_SECRET,
                "session_id": session_id,
                "event_type": "agent_log",
                "data": {"agent_name": AGENT_NAME, "message": message}
            })
        except Exception:
            pass

@task_app.post("/task")
async def handle_task(req: TaskRequest):
    session_id = req.session_id
    query = req.payload.get("query", "")

    await push_log(session_id, f"Searching Depop for: {query}")

    encoded_query = query.replace(" ", "%20")
    url = f"https://www.depop.com/search/?q={encoded_query}&currency=USD"

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    profile = BrowserProfile(
        headless=False,
        stealth=True,
        allowed_domains=["depop.com", "www.depop.com"]
    )
    session = BrowserSession(browser_profile=profile)

    task = f"""
Navigate to: {url}

Wait for the search results grid to load (you should see product cards with photos and prices).

From the first 15 visible product listings, extract:
- price: the price as a number in USD (strip $ signs)
- condition: item condition if shown, otherwise "Used"
- seller: the seller's username
- url: the full URL of the listing (starts with https://www.depop.com/products/)
- title: the item title/description
- reviews: number of seller reviews if visible, otherwise 0

Return ONLY active listings that are currently for sale (not sold).
Return as JSON:
{{
  "platform": "depop",
  "listings": [
    {{"price": 45.0, "condition": "Good", "seller": "username123", "url": "https://www.depop.com/products/...", "title": "Air Jordan 1...", "reviews": 12}}
  ]
}}
"""

    try:
        agent = Agent(
            task=task,
            llm=llm,
            browser_session=session,
            output_model_schema=DepopSearchResult,
            max_steps=12,
            max_failures=3
        )
        history = await agent.run()
        result = history.final_result(DepopSearchResult)

        if result:
            await push_log(session_id, f"Found {len(result.listings)} Depop listings")
            # Emit individual listing_found events for frontend
            for listing in result.listings:
                async with httpx.AsyncClient() as client:
                    try:
                        await client.post(f"{FASTAPI_BASE_URL}/internal/event/{session_id}", json={
                            "secret": INTERNAL_SECRET,
                            "session_id": session_id,
                            "event_type": "listing_found",
                            "data": {"platform": "depop", "listing": listing.dict()}
                        })
                    except Exception:
                        pass
            return JSONResponse(content={
                "platform": "depop",
                "listings": [l.dict() for l in result.listings],
                "summary": f"Found {len(result.listings)} Depop listings"
            })
        else:
            raw = history.final_result() or ""
            return JSONResponse(content={
                "platform": "depop",
                "listings": [],
                "raw_text": raw,
                "summary": "Depop search complete"
            })
    except Exception as e:
        await push_log(session_id, f"Depop search error: {str(e)[:80]}")
        return JSONResponse(content={"platform": "depop", "listings": [], "summary": "Depop search failed"})
    finally:
        await session.stop()

if __name__ == "__main__":
    uvicorn.run(task_app, host="0.0.0.0", port=AGENT_PORT, log_level="warning")
```

---

### Agent 4 — EbaySearchAgent (BUY, Port 8006)

Same pattern as DepopSearchAgent — eBay active listings only.

```python
# Key differences from DepopSearchAgent:
AGENT_NAME = "EbaySearchAgent"
AGENT_PORT = 8006

# eBay active listings URL (NOT sold — this is BUY mode)
url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_BIN=1&_sop=15"
# LH_BIN=1 = Buy It Now only
# _sop=15 = Sort by lowest price

task = f"""
Navigate to: {url}
Wait for results to load.
Extract first 15 active BUY IT NOW listings:
- price (number, USD, exclude shipping)
- condition (New/Used/Good/etc.)
- seller (seller username)
- url (full listing URL starting with https://www.ebay.com/itm/)
- title (listing title)
- feedback_score (seller feedback number if visible, else 0)

Return JSON: {{"platform": "ebay", "listings": [...]}}
"""
```

---

### Agent 5 — MercariSearchAgent (BUY, Port 8007)

```python
# Key differences:
AGENT_NAME = "MercariSearchAgent"
AGENT_PORT = 8007

url = f"https://www.mercari.com/search/?keyword={encoded_query}&status=on_sale"

task = f"""
Navigate to: {url}
Wait for listing cards to load.
Extract first 15 active listings:
- price (number, USD)
- condition (item condition shown)
- seller (seller username/handle)
- url (full listing URL)
- title (item title)
- rating (seller rating number if visible, else 0)

Return JSON: {{"platform": "mercari", "listings": [...]}}
"""
```

---

### Agent 6 — OfferUpSearchAgent (BUY, Port 8008)

OfferUp is highest-risk. Hard 30s timeout, graceful failure.

```python
# Key differences:
AGENT_NAME = "OfferUpSearchAgent"
AGENT_PORT = 8008

url = f"https://offerup.com/search/?q={encoded_query}"

# Hard timeout wrapper
async def handle_task(req: TaskRequest):
    session_id = req.session_id
    query = req.payload.get("query", "")
    await push_log(session_id, f"Trying OfferUp for: {query} (best effort)")
    try:
        result = await asyncio.wait_for(
            run_offerup_search(session_id, query),
            timeout=30.0  # Hard 30-second timeout
        )
        return JSONResponse(content=result)
    except asyncio.TimeoutError:
        await push_log(session_id, "OfferUp timed out (30s) — skipping")
        return JSONResponse(content={
            "platform": "offerup",
            "listings": [],
            "status": "blocked",
            "summary": "OfferUp unavailable"
        })
    except Exception as e:
        await push_log(session_id, f"OfferUp unavailable: {str(e)[:50]}")
        return JSONResponse(content={
            "platform": "offerup",
            "listings": [],
            "status": "blocked",
            "summary": "OfferUp unavailable"
        })
```

---

### Agent 7 — HagglingAgent (BUY, Port 8010)

Called once per seller. Receives a single listing, generates an offer, sends it.

```python
# agents/haggling_agent.py
import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx
from browser_use import Agent, BrowserSession, Tools, ActionResult
from browser_use.browser import BrowserProfile
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

AGENT_NAME = "HagglingAgent"
AGENT_PORT = 8010
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

task_app = FastAPI()

class TaskRequest(BaseModel):
    session_id: str
    payload: dict

async def push_log(session_id: str, message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{FASTAPI_BASE_URL}/internal/event/{session_id}", json={
                "secret": INTERNAL_SECRET,
                "session_id": session_id,
                "event_type": "agent_log",
                "data": {"agent_name": AGENT_NAME, "message": message}
            })
        except Exception:
            pass

async def generate_offer_message(listing: dict, median_price: float) -> tuple[float, str]:
    """Use Gemini to generate a natural offer message."""
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    listing_price = listing.get("price", median_price)
    offer_price = round(max(listing_price * 0.80, median_price * 0.90), 2)  # 20% below asking, floor at 90% of median

    prompt = f"""
Write a short, friendly, natural-sounding offer message for a resale item.

Listing price: ${listing_price}
Your offer: ${offer_price}
Market median price: ${median_price}
Item: {listing.get("title", "this item")}
Platform: {listing.get("platform", "depop")}

Rules:
- 2-3 sentences max
- Be polite and specific about your offer price
- Reference that you've done market research (don't sound aggressive)
- Sound like a real buyer, not a bot
- Do NOT use emojis
- Do NOT mention "median" or "market data" explicitly

Example tone: "Hi! I love this piece. I noticed similar ones have been selling for around ${median_price:.0f} — would you consider ${offer_price:.0f}? Happy to pay right away."

Write the message only, no preamble.
"""
    response = model.generate_content(prompt)
    return offer_price, response.text.strip()

@task_app.post("/task")
async def handle_task(req: TaskRequest):
    session_id = req.session_id
    listing = req.payload.get("listing", {})
    median_price = req.payload.get("median_price", 50.0)

    platform = listing.get("platform", "depop")
    seller = listing.get("seller", "seller")
    listing_url = listing.get("url", "")

    await push_log(session_id, f"Generating offer for {seller} on {platform}...")

    offer_price, message = await generate_offer_message(listing, median_price)

    await push_log(session_id, f"Sending ${offer_price:.0f} offer to {seller}...")

    # Route to correct platform messaging flow
    if platform == "depop":
        result = await send_depop_offer(session_id, listing_url, message, offer_price)
    elif platform == "mercari":
        result = await send_mercari_offer(session_id, listing_url, message, offer_price)
    else:
        result = {"status": "unsupported_platform"}

    # Emit offer_sent event for frontend tracker
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{FASTAPI_BASE_URL}/internal/event/{session_id}", json={
                "secret": INTERNAL_SECRET,
                "session_id": session_id,
                "event_type": "offer_sent",
                "data": {
                    "seller": seller,
                    "platform": platform,
                    "offer_price": offer_price,
                    "status": result.get("status", "sent")
                }
            })
        except Exception:
            pass

    return JSONResponse(content={
        "seller": seller,
        "platform": platform,
        "offer_price": offer_price,
        "message": message,
        "status": result.get("status", "sent"),
        "summary": f"Offer of ${offer_price:.0f} sent to {seller} on {platform}"
    })

async def send_depop_offer(session_id: str, listing_url: str, message: str, offer_price: float) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    profile = BrowserProfile(
        headless=False,
        stealth=True,
        user_data_dir="./profiles/depop",
        allowed_domains=["depop.com", "www.depop.com"]
    )
    session = BrowserSession(browser_profile=profile)

    task = f"""
Navigate to: {listing_url}

Find and click the "Make Offer" button or message the seller.
If there's a "Make Offer" feature, enter the price: {offer_price}
If there's only a message button, click it and send this exact message:
"{message}"

After sending, confirm the message was sent successfully.
Return "sent" if successful, "failed" if not.
"""
    try:
        agent = Agent(task=task, llm=llm, browser_session=session, max_steps=12, use_vision=True)
        history = await agent.run()
        result_text = history.final_result() or ""
        status = "sent" if "sent" in result_text.lower() or history.is_done() else "failed"
        return {"status": status}
    except Exception as e:
        await push_log(session_id, f"Offer send error: {str(e)[:80]}")
        return {"status": "failed"}
    finally:
        await session.stop()

async def send_mercari_offer(session_id: str, listing_url: str, message: str, offer_price: float) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    profile = BrowserProfile(
        headless=False,
        stealth=True,
        allowed_domains=["mercari.com", "www.mercari.com"]
    )
    session = BrowserSession(browser_profile=profile)

    task = f"""
Navigate to: {listing_url}
Find the "Make Offer" button. Click it.
Enter the offer price: {offer_price}
In the message field if present, type: "{message}"
Click submit/send.
Return "sent" if successful.
"""
    try:
        agent = Agent(task=task, llm=llm, browser_session=session, max_steps=10, use_vision=True)
        history = await agent.run()
        return {"status": "sent" if history.is_done() else "failed"}
    except Exception:
        return {"status": "failed"}
    finally:
        await session.stop()

if __name__ == "__main__":
    uvicorn.run(task_app, host="0.0.0.0", port=AGENT_PORT, log_level="warning")
```

---

## Task Prompt Engineering — Critical Notes

### eBay bot avoidance
Always provide the **exact URL** with all parameters pre-built. Don't make the agent type in a search box — too many interaction points for detection. Navigate directly to the pre-filtered results URL.

### Depop form population
Depop's listing form is multi-step and dynamic. Fields appear conditionally. The task must say "fill fields sequentially" and "skip if field not found" — otherwise the agent panics when optional fields don't appear.

### File upload (Depop photo)
Browser Use handles file inputs via Playwright's `set_input_files`. The task just says "upload the file at path: X" and the LLM figures out where the file input is. Make sure the photo path is a real local file path, not a URL — the browser input needs a local file.

### Making offers
The offer message must sound human. Generate it with Gemini separately before the browser agent runs — the browser agent just types the pre-generated message. Never have the browser agent write the message itself during navigation.

---

## Repo-Specific Implementation Rules

### Adapt every example to the scaffold's request/response models
The examples below are implementation sketches, not copy-paste contracts. In this repo:
- Read user input from `request.input["original_input"]`
- Read prior step outputs from `request.input["previous_outputs"]`
- Return a validated `AgentTaskResponse`
- Keep output fields compatible with `backend.schemas`

### Keep contracts stable before adding Browser Use complexity
Browser Use instability is manageable. Contract drift is worse. Before wiring a real browser task into an agent:
- confirm the target output model already contains every field the next step needs
- confirm the step name matches `AGENT_INPUT_CONTRACTS`
- confirm timeout and retry behavior matches the pipeline expectation

### Match timeout settings to the PRD
The PRD assumes a 30 second hard timeout per Browser Use agent. Make sure runtime configuration reflects that before demo testing:

```bash
export AGENT_TIMEOUT_SECONDS=30
```

The repo now defaults `AGENT_TIMEOUT_SECONDS` to `30`, and Browser Use helper code enforces a 30-second floor for browser tasks.

### Handle external-process failures as structured agent failures
When agents move from in-process local functions to separate HTTP task servers, unhandled exceptions become transport errors. Catch Browser Use failures and return structured failure payloads where possible instead of relying on uncaught 500s.

---

## Error Handling Patterns

### Pattern 1 — Timeout wrapper
```python
try:
    result = await asyncio.wait_for(run_agent(), timeout=30.0)
except asyncio.TimeoutError:
    return {"status": "timeout", "listings": []}
```

### Pattern 2 — Fallback chain
```python
result = await try_ebay()
if not result:
    result = await try_mercari()
if not result:
    return empty_result()
```

### Pattern 3 — Graceful structured output failure
```python
result = history.final_result(MyModel)  # Try structured
if not result:
    raw = history.final_result()  # Fall back to raw text
    # Return raw for Person 3 (Pricing Agent) to parse
```

---

## Testing Each Agent

Test each agent in isolation before wiring to the full stack:

```bash
# Start just one agent
python agents/ebay_research_agent.py

# In another terminal, test it directly
curl -X POST http://localhost:8002/task \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "payload": {
      "brand": "Nike",
      "model": "Air Jordan 1",
      "condition": "good"
    }
  }'
```

You should see a browser open, navigate to eBay, extract data, and return JSON.

Then test it against the repo's real contract:
- run the FastAPI backend and execute the full SELL or BUY pipeline
- verify the agent's output passes `backend.schemas.validate_agent_output`
- verify SSE events and final `/result/{session_id}` payloads still match the pipeline contract
- verify retries, timeouts, and fallback behavior under `AGENT_EXECUTION_MODE=http`

---

## Build Order

Do these in exactly this order:

1. **EbayResearchAgent** — simplest, no auth, read-only. Proves your Browser Use setup works.
2. **DepopSearchAgent** — slightly more complex DOM, no auth needed for search.
3. **MercariSearchAgent** — same pattern as Depop, low bot risk.
4. **DepopListingAgent** — needs auth session + file upload. Do this after search agents work.
5. **EbaySearchAgent** — eBay active listings, moderate bot risk.
6. **HagglingAgent** — most complex, needs auth + offer logic. Do last.
7. **OfferUpSearchAgent** — lowest priority, high failure rate. Do only if time allows.

---

## Common Issues + Fixes

### "Browser didn't launch"
```bash
# Reinstall browsers
uvx browser-use install
playwright install chromium --with-deps
```

### "eBay blocking agent"
- Ensure `stealth=True` and `headless=False` in BrowserProfile
- Add random delay: pass a task that includes "wait 2 seconds between actions"
- If still blocked, switch to Mercari fallback

### "Structured output is None but agent ran"
The LLM returned text but not in the expected JSON format. Use `history.final_result()` (no schema) to get raw text, log it, and return raw. The Pricing/Ranking agents can parse it.

### "File upload not working on Depop"
- Ensure photo path is absolute, not relative: `os.path.abspath("./photo.jpg")`
- Ensure file exists before starting agent
- Add `use_vision=True` so agent can visually confirm upload succeeded

### "Session not persisting login"
- Run `setup_sessions.py` again — session may have expired
- Verify `user_data_dir` path exists and has files in it
- Try navigating to the site's homepage first, then the form — some sites need cookies to be "warmed up"

### Port conflict
```bash
lsof -ti:8002 | xargs kill -9
```

---

## Key URLs

| Resource | URL |
|---|---|
| Browser Use docs | https://docs.browser-use.com |
| Browser Use GitHub | https://github.com/browser-use/browser-use |
| Browser Use Cloud LLM guide | https://docs.browser-use.com/cloud/llms.txt |
| Browser Use Cloud API v3 spec | https://docs.browser-use.com/cloud/openapi/v3.json |
| Browser Use Cloud Chat UI tutorial | https://docs.browser-use.com/cloud/tutorials/chat-ui |
| Browser settings reference | https://docs.browser-use.com/customize/browser-settings |
| Output format reference | https://docs.browser-use.com/customize/agent/output-format |
| BrowserSession / BrowserProfile | https://docs.browser-use.com/customize/browser-settings |
| eBay sold listings URL builder | https://www.ebay.com/sch — add LH_Sold=1&LH_Complete=1 |
| Depop search | https://www.depop.com/search/?q=QUERY |
| Mercari search | https://www.mercari.com/search/?keyword=QUERY |
