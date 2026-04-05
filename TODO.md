# TODO — Jay's Manual Checklist

Everything here requires your hands — browser logins, account registration, terminal commands, or teammate conversations. Ordered by priority.

---

## 🔴 Before Demo (Must Do)

### 1. Push to GitHub
```bash
git push origin jay
```
- [ ] Done

### 2. Spike Depop/Mercari httpx Endpoints
Test whether the internal APIs actually respond. If they 403, the agents automatically fall to Browser Use → deterministic fallback — no code changes needed.
```bash
cd /Users/jt/Desktop/diamondhacks && . .venv/bin/activate && python -c "
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
- [ ] Depop returns 200
- [ ] Mercari returns 200
- [ ] If either returns 403: no action needed (fallback handles it)

### 3. Create `.env` File
Copy `.env.example` and fill in real values:
```bash
cp .env.example .env
```
Fill in:
- [ ] `GOOGLE_API_KEY` — from Google AI Studio (https://aistudio.google.com/app/apikey)
- [ ] `INTERNAL_API_TOKEN` — any random string
- [ ] Leave `EBAY_APP_ID` and `EBAY_CERT_ID` blank for now (fallback works)

### 4. Warm Browser Profiles (Depop + OfferUp)
This is required for DepopListingAgent and NegotiationAgent to actually work with Browser Use.
```bash
# Create profiles directory
mkdir -p profiles/depop profiles/ebay profiles/offerup

# Launch Chromium manually with patchright
. .venv/bin/activate && python -c "
import asyncio
from patchright.async_api import async_playwright

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch_persistent_context(
        user_data_dir='./profiles/depop',
        headless=False
    )
    page = browser.pages[0] if browser.pages else await browser.new_page()
    await page.goto('https://www.depop.com/login')
    print('Log into Depop manually, then press Enter here...')
    input()
    await browser.close()
    await pw.stop()
    print('Depop profile saved!')

asyncio.run(main())
"
```
Repeat for eBay (`./profiles/ebay`, `https://www.ebay.com/signin`) and OfferUp (`./profiles/offerup`, `https://offerup.com/login`).
- [ ] Depop profile saved
- [ ] eBay profile saved
- [ ] OfferUp profile saved

### 5. End-to-End Smoke Test — SELL Pipeline
```bash
# Start the backend
make run

# In another terminal:
curl -X POST http://localhost:8000/sell/start \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "image_urls": ["https://example.com/nike-hoodie.jpg"],
      "notes": "Nike hoodie great condition"
    }
  }'

# Copy the session_id from the response, then:
curl -N http://localhost:8000/stream/<SESSION_ID>
```
Watch the SSE stream. Verify:
- [ ] `pipeline_started` event fires
- [ ] `agent_completed` fires for vision_agent
- [ ] `agent_completed` fires for ebay_sold_comps_agent
- [ ] `agent_completed` fires for pricing_agent (should include `trend` and `velocity`)
- [ ] `agent_completed` fires for depop_listing_agent
- [ ] `pipeline_complete` fires with full outputs

### 6. End-to-End Smoke Test — BUY Pipeline
```bash
curl -X POST http://localhost:8000/buy/start \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "query": "nike air jordan 1",
      "budget": 150.0
    }
  }'

# Stream:
curl -N http://localhost:8000/stream/<SESSION_ID>
```
Verify:
- [ ] All 4 search agents complete
- [ ] `ranking` agent completes with `top_choice`
- [ ] `negotiation` agent completes with `offers`
- [ ] `pipeline_complete` fires

### 7. Coordinate SSE Contract with Frontend Teammate
Send them this:
```
SSE Events (underscore-delimited):
- pipeline_started    → { input, mode: "sell"|"buy" }
- agent_started       → { agent_name, attempt, mode }
- agent_completed     → { agent_name, summary, output }
- agent_error         → { agent_name, attempt, max_attempts, error, category }
- pipeline_complete   → { mode, pipeline, outputs }
- pipeline_failed     → { mode, error, partial_result }

Endpoints:
- POST /sell/start    → { session_id, stream_url, result_url }
- POST /buy/start     → { session_id, stream_url, result_url }
- GET  /stream/{id}   → SSE stream
- GET  /result/{id}   → Full session dump
```
- [ ] Frontend teammate has the SSE event contract
- [ ] Frontend teammate has the backend URL (localhost or ngrok)

---

## 🟡 Important (Strengthens Demo)

### 8. Register eBay Developer Credentials
1. Go to https://developer.ebay.com/my/keys
2. Sign in / create account
3. Create a "Production" key set
4. Copy App ID (Client ID) and Cert ID (Client Secret)
5. Add to `.env`:
   ```
   EBAY_APP_ID=Production-xxxxx
   EBAY_CERT_ID=PRD-xxxxx
   ```
- [ ] Registered at developer.ebay.com
- [ ] Credentials added to `.env`
- [ ] Re-test BUY pipeline — eBay search should show `execution_mode: "httpx"`

### 9. Set Up ngrok
```bash
# Install
brew install ngrok

# Authenticate (free account at ngrok.com)
ngrok config add-authtoken YOUR_TOKEN

# Expose backend
ngrok http 8000
```
Copy the `https://xxxx.ngrok-free.app` URL and give it to the frontend teammate.
- [ ] ngrok installed
- [ ] Tunnel running
- [ ] Frontend teammate has the URL

### 10. Test Browser Use with GOOGLE_API_KEY
```bash
# Set env and run ONE agent with Browser Use enabled
BROWSER_USE_FORCE_FALLBACK=false GOOGLE_API_KEY=your_key \
  python -c "
import asyncio
from backend.agents.ebay_sold_comps_agent import agent
from backend.schemas import AgentTaskRequest

request = AgentTaskRequest(
    session_id='test',
    pipeline='sell',
    step='ebay_sold_comps',
    input={
        'original_input': {'image_urls': [], 'notes': 'Nike hoodie'},
        'previous_outputs': {
            'vision_analysis': {
                'agent': 'vision_agent',
                'display_name': 'Vision Agent',
                'summary': 'Inferred Nike hoodie',
                'detected_item': 'hoodie',
                'brand': 'Nike',
                'category': 'apparel',
                'condition': 'good',
            }
        }
    }
)
result = asyncio.run(agent.build_output(request))
print('Mode:', result['execution_mode'])
print('Comps:', result['sample_size'])
"
```
- [ ] Chromium launches
- [ ] eBay sold comps page loads
- [ ] `execution_mode: "browser_use"` in output

---

## 🟢 Nice to Have

### 11. Render Deployment (Only If Needed)
Only do this if ngrok isn't viable for the demo.
- [ ] Upgrade Render to Standard plan ($25/mo) for Chromium memory
- [ ] Set secrets in Render dashboard: `GOOGLE_API_KEY`, `INTERNAL_API_TOKEN`, `EBAY_APP_ID`, `EBAY_CERT_ID`
- [ ] Deploy and test health endpoint: `curl https://diamondhacks-backend.onrender.com/health`

### 12. Demo Rehearsal
- [ ] Practice SELL flow narration (photograph → identify → comps → price → list)
- [ ] Practice BUY flow narration (search → rank → negotiate)
- [ ] Time both flows — should fit in 3 minutes total
- [ ] Have backup items ready if demo item fails
