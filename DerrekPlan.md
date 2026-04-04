# Implementation Delta — What Changed + What to Build
**Supersedes assumptions in PRD v3 and previous role files**
**Read this alongside MY_ROLE.md and BROWSER_USE_GUIDE.md**

---

## What This Doc Is

Everything decided after the PRD was written that changes how things get built. Covers:
- Vision implementation (Person 3)
- Search agent architecture overhaul (Person 2)
- Market trend analysis (Person 3 / PricingAgent)
- Hosting + infrastructure (everyone)
- Browser Use concurrency decision (Person 2)

---

## 1. Vision Agent — Full Implementation (Person 3)

### 1.1 Item Identification — Gemini Vision

Use `gemini-2.0-flash`. One API call, clean JSON output. The `search_query` field is critical — Gemini generates the optimal eBay search string so EbayResearchAgent doesn't have to guess.

```python
import google.generativeai as genai
import json
import os

async def identify_item(image_b64: str) -> dict:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash")

    response = model.generate_content([{
        "parts": [
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_b64
                }
            },
            {
                "text": """Identify this thrift store item for resale. Return JSON only, no markdown:
{
  "brand": "Nike",
  "item_name": "Air Jordan 1 Retro High OG",
  "model": "Air Jordan 1",
  "category": "sneakers",
  "condition": "good",
  "condition_notes": "slight creasing on toe box",
  "confidence": 0.92,
  "color": "Chicago colorway red/black/white",
  "size_visible": "10.5",
  "search_query": "Nike Air Jordan 1 Retro High OG Chicago"
}

Rules:
- condition must be exactly one of: excellent / good / fair
- confidence is a float 0.0-1.0
- search_query must be optimized for eBay sold listing search — brand + model + key variant
- If brand is unknown use "Unknown"
- Return JSON only, absolutely no markdown or preamble"""
            }
        ]
    }])

    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)
```

### 1.2 Confidence Gate

If confidence < 0.70, pause the pipeline and ask the user to confirm or correct before proceeding. Don't silently continue with a bad identification — everything downstream depends on this.

```python
async def run_vision_pipeline(image_b64: str, session_id: str) -> dict:
    await push_log(session_id, "Identifying item with Gemini Vision...")
    result = await identify_item(image_b64)

    if result["confidence"] < 0.70:
        # Pause pipeline — emit event for frontend to show correction UI
        await push_event(session_id, "vision_low_confidence", {
            "suggestion": result,
            "message": f"Not sure — is this a {result['brand']} {result['item_name']}?"
        })
        # Pipeline waits here for user_correction event from frontend
        # Frontend sends POST /sell/correct with corrected item details
        return None  # Signals orchestrator to wait

    await push_log(session_id, f"Identified: {result['brand']} {result['item_name']} ({int(result['confidence']*100)}% confidence)")
    return result
```

**Frontend handles this:** show a confirmation card with "Is this a [brand] [item]?" + Yes / No + text field to correct. On confirm, pipeline resumes. On correction, user types the right item and pipeline continues with corrected data.

**Demo prep:** always use an unambiguous demo item (Air Jordan 1, AirPods, North Face jacket) so this gate is never triggered during judging.

### 1.3 Clean Photo — Nano Banana

Runs after identification, uses same `image_b64`. Verify exact endpoint from Nano Banana docs at the hackathon.

```python
import httpx

async def generate_clean_photo(image_b64: str) -> str:
    """Remove background and generate clean white-bg product shot."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.nanobanana.io/v1/remove-background",  # CONFIRM endpoint from docs
            headers={"Authorization": f"Bearer {os.getenv('NANO_BANANA_API_KEY')}"},
            json={"image": image_b64}
        )
        data = resp.json()
        return data.get("url", "")  # CONFIRM response field name from docs
```

### 1.4 VisionAgent Task Handler — Full Flow

```python
async def handle_vision_task(image_b64: str, session_id: str) -> dict:
    # Step 1: Identify
    identification = await run_vision_pipeline(image_b64, session_id)
    if not identification:
        return None  # Low confidence — waiting for user correction

    # Step 2: Clean photo (parallel-ish — start while identification result is being logged)
    await push_log(session_id, "Generating clean product photo...")
    clean_photo_url = await generate_clean_photo(image_b64)

    result = {
        **identification,
        "clean_photo_url": clean_photo_url
    }

    await push_log(session_id, "Vision complete")
    return result
```

### 1.5 New FastAPI endpoint — User Correction

Add this to `main.py` for when confidence gate fires:

```python
class CorrectionRequest(BaseModel):
    session_id: str
    corrected_item: dict  # { brand, item_name, model, condition, search_query }

@app.post("/sell/correct")
async def sell_correct(req: CorrectionRequest):
    """Called by frontend when user corrects a low-confidence identification."""
    # Resume pipeline with corrected data
    asyncio.create_task(
        resume_sell_pipeline(req.session_id, req.corrected_item)
    )
    return {"ok": True}
```

---

## 2. Search Agent Architecture Overhaul (Person 2)

### 2.1 Decision Summary

**Don't use Browser Use for read-only search.** Use APIs and httpx instead. Browser Use is reserved for tasks that genuinely require it.

| Agent | Old approach | New approach | Why |
|---|---|---|---|
| EbaySearchAgent (BUY active listings) | Browser Use | **eBay Browse API** | Free official API, clean JSON |
| EbayResearchAgent (SELL sold comps) | Browser Use | **Browser Use** (keep) | Browse API doesn't expose sold listings |
| DepopSearchAgent | Browser Use | **httpx internal API** | Faster, no Chromium needed |
| MercariSearchAgent | Browser Use | **httpx internal API** | No public API, but internal endpoints work |
| OfferUpSearchAgent | Browser Use | **Drop or Browser Use** | No API, high detection risk |
| DepopListingAgent | Browser Use | **Browser Use** (keep) | No public API for listing creation |
| HagglingAgent | Browser Use | **Browser Use** (keep) | Auth + form interaction required |

**Browser Use sessions at any point in time: maximum 1 (sequential).**

### 2.2 eBay Browse API — EbaySearchAgent (BUY mode)

Register at https://developer.ebay.com → get App ID + secret → OAuth client credentials flow.

```python
import httpx
import os

async def get_ebay_token() -> str:
    """Get OAuth app token for Browse API."""
    import base64
    credentials = base64.b64encode(
        f"{os.getenv('EBAY_APP_ID')}:{os.getenv('EBAY_CERT_ID')}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"}
        )
        return resp.json()["access_token"]

async def search_ebay_active(query: str) -> list:
    """Search eBay active Buy It Now listings via Browse API."""
    token = await get_ebay_token()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                "Content-Type": "application/json"
            },
            params={
                "q": query,
                "filter": "buyingOptions:{FIXED_PRICE},conditions:{USED|GOOD|VERY_GOOD}",
                "sort": "price",
                "limit": 15,
                "fieldgroups": "MATCHING_ITEMS"
            }
        )
        data = resp.json()
        items = data.get("itemSummaries", [])
        return [
            {
                "platform": "ebay",
                "price": float(item.get("price", {}).get("value", 0)),
                "condition": item.get("condition", "Used"),
                "seller": item.get("seller", {}).get("username", ""),
                "url": item.get("itemWebUrl", ""),
                "title": item.get("title", ""),
                "feedback_score": item.get("seller", {}).get("feedbackScore", 0)
            }
            for item in items
        ]
```

**Add to .env:**
```
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
```

**Register at:** https://developer.ebay.com/my/keys

### 2.3 Depop Internal API — DepopSearchAgent (BUY mode)

Spike this first — if it returns 403, fall back to Browser Use.

```python
async def search_depop(query: str) -> list:
    """Search Depop via reverse-engineered internal API."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                "https://webapi.depop.com/api/v2/search/products/",
                params={
                    "q": query,
                    "country": "us",
                    "currency": "USD",
                    "limit": 15
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
                    "Accept": "application/json",
                    "Referer": "https://www.depop.com/"
                }
            )
            if resp.status_code != 200:
                return []  # Caller falls back to Browser Use

            data = resp.json()
            products = data.get("products", [])
            return [
                {
                    "platform": "depop",
                    "price": float(p.get("price", {}).get("nationalShippingCost", {}).get("amount", 0) or p.get("price", {}).get("priceAmount", 0)),
                    "condition": p.get("attributes", {}).get("variant", {}).get("condition", "Used"),
                    "seller": p.get("seller", {}).get("username", ""),
                    "url": f"https://www.depop.com/products/{p.get('slug', '')}",
                    "title": p.get("description", "")[:100],
                    "reviews": p.get("seller", {}).get("reviewsTotal", 0)
                }
                for p in products
            ]
        except Exception:
            return []  # Caller falls back to Browser Use
```

### 2.4 Mercari Internal API — MercariSearchAgent (BUY mode)

```python
async def search_mercari(query: str) -> list:
    """Search Mercari via internal API."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                "https://api.mercari.com/v2/entities:search",
                params={
                    "keyword": query,
                    "status": "STATUS_ON_SALE",
                    "limit": 15
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
                    "X-Platform": "web",
                    "Accept": "application/json"
                }
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            items = data.get("items", [])
            return [
                {
                    "platform": "mercari",
                    "price": float(item.get("price", 0)),
                    "condition": item.get("itemCondition", "Used"),
                    "seller": item.get("sellerId", ""),
                    "url": f"https://www.mercari.com/item/{item.get('id', '')}",
                    "title": item.get("name", ""),
                    "reviews": 0
                }
                for item in items
            ]
        except Exception:
            return []
```

### 2.5 Spike These Before Hackathon Starts

Run these right now to confirm they work:

```bash
python -c "
import httpx, json

# Test Depop
r = httpx.get('https://webapi.depop.com/api/v2/search/products/', 
    params={'q': 'air jordan 1', 'country': 'us', 'currency': 'USD'},
    headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
print('Depop status:', r.status_code)
if r.status_code == 200:
    print('Depop products:', len(r.json().get('products', [])))

# Test Mercari
r = httpx.get('https://api.mercari.com/v2/entities:search',
    params={'keyword': 'air jordan 1', 'status': 'STATUS_ON_SALE'},
    headers={'User-Agent': 'Mozilla/5.0', 'X-Platform': 'web'})
print('Mercari status:', r.status_code)
"
```

**If Depop returns 200:** use httpx, no Browser Use needed for search.
**If Depop returns 403:** use Browser Use for DepopSearchAgent (as in BROWSER_USE_GUIDE.md).
**Same logic for Mercari.**

### 2.6 Concurrency Decision — Sequential

**Run all agents sequentially. No parallel Browser Use sessions.**

Reasons:
- Demo is 3 minutes — speed difference is invisible while you're narrating
- One Browser Use session at a time = zero memory pressure, zero session conflicts
- Simpler code, easier to debug at 3am
- The visual agent feed animating sequentially looks fine to judges

The BUY pipeline runs:
```
DepopSearch → EbaySearch → MercariSearch → OfferUp → Ranking → Haggling ×N
```
Each completes before the next starts. Total BUY search phase: ~45-60 seconds.

---

## 3. Market Trend Analysis (Person 3 — PricingAgent)

Add this to PricingAgent output. Zero new API calls — uses comps data already pulled by EbayResearchAgent.

### 3.1 Trend Calculation

```python
from datetime import datetime, timedelta
from statistics import median
from dateutil import parser as dateparser

def compute_trend(comps: list) -> dict:
    """Compare recent vs older median prices to detect trend."""
    now = datetime.now()

    def parse_date(date_str: str) -> datetime:
        try:
            return dateparser.parse(date_str)
        except Exception:
            return now - timedelta(days=45)  # Default to middle bucket if unparseable

    recent = [c["price"] for c in comps
              if parse_date(c["date_sold"]) > now - timedelta(days=30)]
    older = [c["price"] for c in comps
             if now - timedelta(days=90) < parse_date(c["date_sold"]) <= now - timedelta(days=30)]

    if len(recent) < 2 or len(older) < 2:
        return {"trend": "neutral", "delta_pct": 0.0, "signal": "Insufficient data"}

    recent_median = median(recent)
    older_median = median(older)
    delta_pct = ((recent_median - older_median) / older_median) * 100

    if delta_pct > 5:
        trend = "rising"
        signal = f"↑ Up {delta_pct:.1f}% last 30 days"
    elif delta_pct < -5:
        trend = "falling"
        signal = f"↓ Down {abs(delta_pct):.1f}% last 30 days"
    else:
        trend = "stable"
        signal = f"→ Stable (±{abs(delta_pct):.1f}%)"

    return {
        "trend": trend,
        "delta_pct": round(delta_pct, 1),
        "recent_median": round(recent_median, 2),
        "older_median": round(older_median, 2),
        "signal": signal
    }
```

### 3.2 Sell Velocity

```python
def compute_velocity(comps: list) -> dict:
    """How fast is this item moving? Based on recency of sold listings."""
    now = datetime.now()

    def parse_date(date_str: str) -> datetime:
        try:
            return dateparser.parse(date_str)
        except Exception:
            return now - timedelta(days=45)

    last_30 = sum(1 for c in comps
                  if parse_date(c["date_sold"]) > now - timedelta(days=30))
    ratio = last_30 / len(comps) if comps else 0

    if ratio > 0.6:
        label = "High demand"
        detail = "Selling fast"
    elif ratio > 0.3:
        label = "Moderate demand"
        detail = "Moving steadily"
    else:
        label = "Low demand"
        detail = "Slow mover"

    return {
        "velocity": "high" if ratio > 0.6 else ("medium" if ratio > 0.3 else "low"),
        "label": label,
        "detail": detail,
        "sold_last_30_days": last_30,
        "total_comps": len(comps)
    }
```

### 3.3 Updated PricingAgent Output

Add trend and velocity to the PricingAgent result dict:

```python
def compute_pricing(comps: list, condition: str, thrift_cost: float = 8.0) -> dict:
    prices = [c["price"] for c in comps]

    # Remove outliers
    mean = sum(prices) / len(prices)
    std = (sum((p - mean) ** 2 for p in prices) / len(prices)) ** 0.5
    filtered = [p for p in prices if abs(p - mean) <= 2 * std]

    condition_multiplier = {"excellent": 1.05, "good": 1.00, "fair": 0.85}.get(condition, 1.00)
    median_price = median(filtered) * condition_multiplier
    shipping = 5.0
    depop_fee = median_price * 0.10
    profit = median_price - shipping - depop_fee - thrift_cost

    trend = compute_trend(comps)
    velocity = compute_velocity(comps)

    return {
        "recommended_price": round(median_price, 2),
        "profit_margin": round(profit, 2),
        "median_price": round(median_price, 2),
        "trend": trend,
        "velocity": velocity,
        "summary": f"${profit:.0f} profit · {trend['signal']} · {velocity['label']}"
    }
```

### 3.4 What the UI Shows

Three numbers, all on the same card:

```
$42 estimated profit
↑ Rising 15% last 30 days
High demand — selling fast
```

vs

```
$42 estimated profit
↓ Falling 8% last 30 days
Slow mover
```

Person 4 implements this as a trend badge + velocity chip below the profit margin hero number.

**Add to .env for PricingAgent:**
```
pip install python-dateutil
```

---

## 4. Infrastructure — Everything Changed (Everyone)

### 4.1 No Render. Run Locally.

Drop Render entirely. Run everything on your laptop during the demo.

| Component | How |
|---|---|
| FastAPI backend | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| All agents | `python run_agents.py` |
| Public URL for phone | `ngrok http 8000` |
| Mobile app | Expo Go — `npx expo start`, scan QR |

### 4.2 ngrok Setup

```bash
# Install ngrok
brew install ngrok  # Mac
# or download from https://ngrok.com/download

# Authenticate (free account)
ngrok config add-authtoken YOUR_TOKEN

# Expose backend
ngrok http 8000
# Returns something like: https://abc123.ngrok-free.app
```

Put the ngrok URL in the mobile app as `EXPO_PUBLIC_API_URL`. Every time you restart ngrok you get a new URL — restart it once before judging starts, update the env var, rebuild with Expo.

**Pro tip:** Use a fixed subdomain (ngrok paid) or just restart once and leave it running. Free tier gives you 1 agent (tunnel), which is all you need.

### 4.3 Pre-Session Login (Do Tonight)

Run `setup_sessions.py` from BROWSER_USE_GUIDE.md to log into Depop and OfferUp manually and save sessions to `./profiles/`. These persist as long as the session files exist on your laptop.

### 4.4 .env — Final Complete Version

```env
# Gemini
GEMINI_API_KEY=your_key

# Nano Banana
NANO_BANANA_API_KEY=your_key

# eBay Browse API
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id

# Agentverse
AGENTVERSE_API_KEY=your_key

# Agent seeds (one per agent, must be unique)
VISION_AGENT_SEED=vision-agent-seed-diamondhacks-2026
EBAY_RESEARCH_AGENT_SEED=ebay-research-seed-diamondhacks
PRICING_AGENT_SEED=pricing-agent-seed-diamondhacks
DEPOP_LISTING_AGENT_SEED=depop-listing-seed-diamondhacks
DEPOP_SEARCH_AGENT_SEED=depop-search-seed-diamondhacks
EBAY_SEARCH_AGENT_SEED=ebay-search-seed-diamondhacks
MERCARI_SEARCH_AGENT_SEED=mercari-search-seed-diamondhacks
OFFERUP_SEARCH_AGENT_SEED=offerup-search-seed-diamondhacks
RANKING_AGENT_SEED=ranking-agent-seed-diamondhacks
HAGGLING_AGENT_SEED=haggling-agent-seed-diamondhacks

# Internal
INTERNAL_SECRET=hackathon-internal-2026
FASTAPI_BASE_URL=http://localhost:8000

# Telemetry
ANONYMIZED_TELEMETRY=false
```

---

## 5. Revised Agent Roster — What Actually Uses Browser Use

Only 3 agents use Browser Use now. Everything else is httpx or API calls.

| # | Agent | Port | What it does | Tech |
|---|---|---|---|---|
| 1 | VisionAgent | 8001 | Gemini Vision + Nano Banana | Gemini API + httpx |
| 2 | EbayResearchAgent | 8002 | eBay sold comps | **Browser Use** |
| 3 | PricingAgent | 8003 | Margin + trend + velocity | Python logic |
| 4 | DepopListingAgent | 8004 | Depop form population | **Browser Use** |
| 5 | DepopSearchAgent | 8005 | Active Depop listings | httpx (fallback: Browser Use) |
| 6 | EbaySearchAgent | 8006 | Active eBay listings | eBay Browse API |
| 7 | MercariSearchAgent | 8007 | Active Mercari listings | httpx (fallback: Browser Use) |
| 8 | OfferUpSearchAgent | 8008 | OfferUp listings | Drop or Browser Use |
| 9 | RankingAgent | 8009 | Score + rank listings | Gemini API |
| 10 | HagglingAgent | 8010 | Send offers | **Browser Use** |

**Browser Use is load-bearing and non-replaceable for agents 2, 4, 10.** This is a stronger judging story than using it everywhere — every Browser Use task is genuinely irreplaceable.

---

## 6. New SSE Events to Add (Person 1)

Add these to `main.py` beyond what's already there:

```python
# Confidence gate — frontend shows correction UI
"vision_low_confidence"  → { suggestion: dict, message: str }

# Trend + velocity (emitted by PricingAgent after comps computed)
"trend_computed"  → { trend: str, delta_pct: float, signal: str, velocity: dict }

# API search vs Browser Use (for frontend to show different badge)
"search_method"  → { agent: str, method: "api" | "browser_use" | "httpx" }
```

---

## 7. New Dependencies to Install

```bash
pip install python-dateutil  # For date parsing in trend calculation
pip install ebaysdk          # Optional — eBay official Python SDK
# browser-use already installed
# httpx already installed
# google-generativeai already installed
```

---

## 8. Build Order — Updated Priority

**Spike first (before any agent work):**
1. Test Depop httpx endpoint — returns 200 or 403?
2. Test Mercari httpx endpoint — returns 200 or 403?
3. Register eBay developer account, get credentials, test Browse API call
4. Test Gemini Vision on a photo of your demo item

