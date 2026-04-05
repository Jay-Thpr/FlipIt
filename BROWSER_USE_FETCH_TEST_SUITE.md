# Browser Use + Fetch.ai Comprehensive Test Suite

This document defines an intensive test suite covering all Browser Use and Fetch.ai agent flows. These tests require a Mac/Linux environment with Chromium, `browser-use` installed, `GOOGLE_API_KEY` set, and browser profiles warmed. They cannot run on Windows.

## Prerequisites

```bash
# 1. Install browser-use (not in requirements.txt)
pip install browser-use

# 2. Install Chromium via Playwright/Patchright
python -m patchright install chromium
# or: python -m playwright install chromium

# 3. Set environment variables
export GOOGLE_API_KEY="<your-gemini-key>"
export EBAY_APP_ID="<your-ebay-app-id>"
export EBAY_CERT_ID="<your-ebay-cert-id>"
export BROWSER_USE_FORCE_FALLBACK=false
export AGENT_EXECUTION_MODE=local_functions
export AGENT_TIMEOUT_SECONDS=60
export FETCH_ENABLED=true

# 4. Warm browser profiles (manual login required once per platform)
mkdir -p profiles/depop profiles/ebay profiles/mercari profiles/offerup
# Then manually log into each platform via:
# python -c "from browser_use import BrowserSession, BrowserProfile; ..."

# 5. Set Fetch.ai agent seeds
export VISION_FETCH_AGENT_SEED="test-seed-vision"
export EBAY_SOLD_COMPS_FETCH_AGENT_SEED="test-seed-comps"
export PRICING_FETCH_AGENT_SEED="test-seed-pricing"
export DEPOP_LISTING_FETCH_AGENT_SEED="test-seed-listing"
export DEPOP_SEARCH_FETCH_AGENT_SEED="test-seed-depop"
export EBAY_SEARCH_FETCH_AGENT_SEED="test-seed-ebay"
export MERCARI_SEARCH_FETCH_AGENT_SEED="test-seed-mercari"
export OFFERUP_SEARCH_FETCH_AGENT_SEED="test-seed-offerup"
export RANKING_FETCH_AGENT_SEED="test-seed-ranking"
export NEGOTIATION_FETCH_AGENT_SEED="test-seed-negotiation"
export RESALE_COPILOT_FETCH_AGENT_SEED="test-seed-copilot"
```

---

## Section 1: Runtime Audit & Environment Checks

### T1.1 — All runtime audit checks pass

```
Pre: GOOGLE_API_KEY set, browser-use installed, Chromium present, profiles/ exists with 4 subdirs
Run: python -m backend.browser_use_runtime_audit
Assert:
  - Exit code 0
  - All checks report PASS:
    - agent_timeout >= 30
    - browser_use_max_steps > 0
    - google_api_key is set
    - execution_mode == local_functions
    - forced_fallback == false
    - browser_use_dependencies importable
    - profile_root exists
    - platform_profiles: depop, ebay, mercari, offerup all exist
    - chromium_installation detected
```

### T1.2 — Audit fails gracefully when GOOGLE_API_KEY missing

```
Pre: Unset GOOGLE_API_KEY
Run: python -m backend.browser_use_runtime_audit
Assert:
  - google_api_key check reports FAIL
  - Other checks still run (no early exit)
  - Exit code non-zero
```

### T1.3 — Audit detects missing browser profiles

```
Pre: Rename profiles/depop → profiles/depop_bak
Run: python -m backend.browser_use_runtime_audit
Assert:
  - platform_profiles check reports FAIL for depop
  - Other platforms still report PASS
Cleanup: Rename back
```

### T1.4 — Audit detects missing Chromium

```
Pre: Move Chromium binary out of expected cache path
Run: python -m backend.browser_use_runtime_audit
Assert:
  - chromium_installation check reports FAIL
Cleanup: Restore Chromium
```

### T1.5 — browser_use_runtime_ready() returns correct booleans

```
Test A: All prerequisites met → returns True
Test B: GOOGLE_API_KEY unset → returns False
Test C: BROWSER_USE_FORCE_FALLBACK=true → returns False
Test D: browser-use not installed (mock ImportError) → returns False
```

---

## Section 2: 3-Tier Resolution Path (httpx → Browser Use → Fallback)

### T2.1 — Depop httpx search succeeds with valid response

```
Run: search_depop_httpx("Nike vintage tee size M", limit=5)
Assert:
  - Returns list (not None)
  - Each item has: platform=="depop", title (str), price (float>0), url (contains depop.com), condition, seller, seller_score (int), posted_at (ISO date)
  - At most 5 items returned
  - User-Agent header contains "iPhone"
```

### T2.2 — Depop httpx search returns None on 403/timeout

```
Test A: Mock webapi.depop.com returning 403 → returns None
Test B: Mock 15-second timeout → returns None
Test C: Mock network error (ConnectionError) → returns None
```

### T2.3 — Mercari httpx search succeeds with valid response

```
Run: search_mercari_httpx("Carhartt jacket", limit=5)
Assert:
  - Returns list (not None)
  - Each item has: platform=="mercari", title, price>0, url (contains mercari.com), condition, seller, seller_score==0 (always), posted_at
```

### T2.4 — eBay Browse API search with valid credentials

```
Pre: EBAY_APP_ID + EBAY_CERT_ID set
Run: search_ebay_browse_api("Levi's 501 jeans", limit=5)
Assert:
  - OAuth token obtained successfully (non-None)
  - Returns list (not None)
  - Each item has: platform=="ebay", title, price>0, url (contains ebay.com), condition, seller, seller_score (int), posted_at
  - Filter includes buyingOptions:FIXED_PRICE
```

### T2.5 — eBay Browse API returns None when credentials missing

```
Pre: Unset EBAY_APP_ID
Run: search_ebay_browse_api("test query")
Assert: returns None (get_ebay_oauth_token returns None, search bails)
```

### T2.6 — OfferUp has NO httpx client (Browser Use or fallback only)

```
Assert: No function search_offerup_httpx exists in httpx_clients.py
Assert: OfferUp search agent falls directly to browser_use tier, then fallback
```

### T2.7 — Full 3-tier resolution: httpx succeeds, Browser Use skipped

```
Pre: Mock httpx returning valid results for Depop
Run: depop_search_agent.handle_task(request)
Assert:
  - execution_mode == "httpx"
  - No browser launched
  - Results match httpx output
```

### T2.8 — Full 3-tier resolution: httpx fails, Browser Use succeeds

```
Pre: Mock httpx returning None, Browser Use available
Run: depop_search_agent.handle_task(request)
Assert:
  - execution_mode == "browser_use"
  - Browser was launched (can verify via browser_use metadata)
  - Results are real scraped data
  - search_method SSE event emitted with method=="browser_use"
```

### T2.9 — Full 3-tier resolution: httpx fails, Browser Use fails, fallback used

```
Pre: Mock httpx returning None, BROWSER_USE_FORCE_FALLBACK=true
Run: depop_search_agent.handle_task(request)
Assert:
  - execution_mode == "fallback"
  - Returns exactly 2 listings
  - Listings are deterministic (same input → same output)
  - browser_use_fallback SSE event emitted
  - browser_use metadata includes error_category
```

### T2.10 — Fallback determinism: same input always produces identical output

```
Run A: build_platform_results(platform="depop", query="Nike hoodie", budget=50)
Run B: build_platform_results(platform="depop", query="Nike hoodie", budget=50)
Assert: Run A == Run B (byte-identical)
Run C: build_platform_results(platform="depop", query="Nike hoodie", budget=60)
Assert: Run A != Run C (different budget changes price)
```

### T2.11 — Fallback brand detection accuracy

```
Assert: detect_brand("nike vintage tee") == "Nike"
Assert: detect_brand("ADIDAS hoodie") == "Adidas"
Assert: detect_brand("patagonia fleece") == "Patagonia"
Assert: detect_brand("random item") == "Vintage"  # default
Assert: detect_brand(None) == "Vintage"
Assert: detect_brand("") == "Vintage"
```

### T2.12 — Fallback platform price offsets are correct

```
For each platform in [depop, ebay, mercari, offerup]:
  Run: build_platform_results(platform, query="Nike tee", budget=45)
  Assert:
    - depop price ≈ base * 1.02
    - ebay price ≈ base * 0.94
    - mercari price ≈ base * 0.97
    - offerup price ≈ base * 0.88
    - Second listing price = first + platform gap (5.25, 4.5, 4.95, 3.75)
```

---

## Section 3: Browser Use Live Scraping (Requires Chromium + Profiles)

### T3.1 — Live Depop search returns real listings

```
Pre: profiles/depop exists with logged-in session, GOOGLE_API_KEY set
Run: browser_use_validation.py --scenario depop_search --require-live
Assert:
  - execution_mode == "browser_use"
  - At least 1 listing returned
  - Each listing has title, price>0, url starting with https://www.depop.com
  - Browser opened depop.com/search/?q=...
```

### T3.2 — Live eBay search returns real listings

```
Run: browser_use_validation.py --scenario ebay_search --require-live
Assert:
  - execution_mode == "browser_use"
  - Listings contain ebay.com URLs
  - Prices are USD floats
```

### T3.3 — Live Mercari search returns real listings

```
Run: browser_use_validation.py --scenario mercari_search --require-live
Assert:
  - execution_mode == "browser_use"
  - Listings contain mercari.com URLs
```

### T3.4 — Live OfferUp search returns real listings

```
Run: browser_use_validation.py --scenario offerup_search --require-live
Assert:
  - execution_mode == "browser_use"
  - Listings contain offerup.com URLs
  - Note: OfferUp has no httpx tier, so this is the only "real" data path
```

### T3.5 — Live eBay sold comps returns real pricing data

```
Run: browser_use_validation.py --scenario ebay_sold_comps --require-live
Assert:
  - execution_mode == "browser_use"
  - median_sold_price > 0
  - low_sold_price <= median_sold_price <= high_sold_price
  - sample_size >= 1
```

### T3.6 — Live Depop listing draft creation (prepare phase)

```
Pre: profiles/depop exists with logged-in seller account
Run: browser_use_validation.py --scenario depop_listing --require-live
Assert:
  - execution_mode == "browser_use"
  - listing_status == "ready_for_confirmation"
  - ready_for_confirmation == true
  - Browser navigated to depop.com/sell
  - Form fields populated (title, description, price, category)
  - Publish button NOT clicked
  - draft_created SSE event emitted
```

### T3.7 — Depop listing revision (revise phase)

```
Pre: T3.6 completed (draft exists in browser)
Run: revise_sell_listing_for_review(session_id, "Change price to $55 and update description")
Assert:
  - listing_status == "ready_for_confirmation" (still paused)
  - Price field updated to 55
  - Description field updated
  - Still not submitted
```

### T3.8 — Depop listing submit (confirm phase)

```
Pre: T3.6 or T3.7 completed (draft exists)
Run: submit_sell_listing(session_id)
Assert:
  - listing_status == "submitted"
  - draft_status == "submitted"
  - Publish/submit button was clicked
  - offer_prepared or draft_created SSE event confirms submission
Cleanup: Manually delete the test listing from Depop
```

### T3.9 — Depop listing abort (cancel phase)

```
Pre: T3.6 completed (draft exists, not submitted)
Run: abort_sell_listing(session_id)
Assert:
  - listing_status == "aborted"
  - draft_status == "aborted"
  - draft_url == null
  - Browser form closed/discarded
```

### T3.10 — Depop listing fails when profile directory missing

```
Pre: Rename profiles/depop → profiles/depop_bak
Run: depop_listing_agent.handle_task(request)
Assert:
  - execution_mode == "fallback"
  - browser_use.error_category == "profile_missing"
  - ready_for_confirmation == false
  - Listing metadata still generated (title, description, price)
Cleanup: Rename back
```

### T3.11 — Negotiation agent sends offer via Browser Use

```
Pre: profiles/ exist with buyer account logged in
Run: browser_use_validation.py --scenario negotiation --require-live
Assert:
  - Offer status is "sent" or "failed" (graceful either way)
  - If sent: conversation_url is a valid URL
  - If failed: failure_reason explains why (e.g., "seller not accepting offers")
  - offer_sent or offer_failed SSE event emitted
```

### T3.12 — Browser Use max_steps exceeded

```
Pre: Set BROWSER_USE_MAX_STEPS=1 (impossibly low)
Run: depop_search_agent with Browser Use
Assert:
  - Browser Use fails (can't complete in 1 step)
  - Falls back to deterministic data
  - execution_mode == "fallback"
  - error_category is "result_invalid" or "browser_error"
Cleanup: Reset BROWSER_USE_MAX_STEPS=15
```

### T3.13 — Browser Use timeout handling

```
Pre: Set AGENT_TIMEOUT_SECONDS=5 (too short for real scraping)
Run: Start a sell pipeline
Assert:
  - Agent times out
  - Pipeline does not hang indefinitely
  - Falls back or fails with clear error
Cleanup: Reset AGENT_TIMEOUT_SECONDS=60
```

---

## Section 4: Failure Classification

### T4.1 — classify_browser_use_failure covers all 9 categories

```
Test cases:
  BrowserUseRuntimeUnavailable("key missing") → "runtime_unavailable"
  BrowserUseTaskExecutionError("no result") → "result_invalid"
  ValidationError("bad schema") → "result_invalid"
  ValueError("invalid output") → "result_invalid"
  RuntimeError("profile not found") → "profile_missing"
  RuntimeError("revision could not be applied") → "revision_failed"
  RuntimeError("submit button not found") → "submit_failed"
  RuntimeError("abort dialog failed") → "abort_failed"
  RuntimeError("generic DOM timeout") → "browser_error"
```

### T4.2 — classify_browser_use_failure with operation parameter

```
  classify(RuntimeError("err"), operation="apply_listing_revision") → "revision_failed"
  classify(RuntimeError("err"), operation="submit_prepared_listing") → "submit_failed"
  classify(RuntimeError("err"), operation="abort_prepared_listing") → "abort_failed"
  classify(RuntimeError("err"), operation="prepare_listing_for_review") → "review_checkpoint_failed"
```

### T4.3 — build_browser_use_metadata returns complete structure

```
metadata = build_browser_use_metadata(
    mode="fallback",
    attempted_live_run=True,
    profile_name="depop",
    error_category="profile_missing",
    detail="profiles/depop not found"
)
Assert:
  - metadata["mode"] == "fallback"
  - metadata["attempted_live_run"] == True
  - metadata["profile_name"] == "depop"
  - metadata["profile_available"] == False (since error is profile_missing)
  - metadata["error_category"] == "profile_missing"
  - metadata["detail"] contains "not found"
```

### T4.4 — summarize_browser_use_error truncates long messages

```
long_error = "x" * 500
summary = summarize_browser_use_error(RuntimeError(long_error))
Assert: len(summary) <= 200
```

---

## Section 5: SSE Event Emission

### T5.1 — emit_browser_use_event in local mode appends to session

```
Pre: Create a SessionState in SessionManager
Run: emit_browser_use_event(session_id=sid, pipeline="sell", step="depop_listing", event_type="draft_created", data={...})
Assert:
  - Session events list has new entry
  - Event type matches "draft_created"
  - No HTTP request made
```

### T5.2 — emit_browser_use_event in HTTP mode posts to internal endpoint

```
Pre: Set AGENT_EXECUTION_MODE=local_http, mock /internal/event/{session_id}
Run: emit_browser_use_event(session_id=sid, ...)
Assert:
  - HTTP POST made to {APP_BASE_URL}/internal/event/{sid}
  - Header x-internal-token == INTERNAL_API_TOKEN
  - Body contains event_type and data
```

### T5.3 — emit_browser_use_event with empty session_id is no-op

```
Run: emit_browser_use_event(session_id="", ...)
Assert: No session lookup, no HTTP call, no exception
```

### T5.4 — emit_browser_use_event HTTP failure is silent

```
Pre: Mock /internal/event returning 500
Run: emit_browser_use_event(session_id=sid, ...)
Assert: No exception raised, function returns normally
```

### T5.5 — Browser Use fallback events counted correctly in buy pipeline

```
Run: Full buy pipeline with BROWSER_USE_FORCE_FALLBACK=true
Count all events with event_type == "browser_use_fallback"
Assert: Count >= 4 (one per search agent: depop, ebay, mercari, offerup)
```

---

## Section 6: Full Pipeline Integration (Browser Use Path)

### T6.1 — Sell pipeline end-to-end with live Browser Use

```
Pre: All profiles warmed, GOOGLE_API_KEY set, backend running
Run: POST /sell/start with { input: { image_urls: ["https://example.com/nike-hoodie.jpg"], notes: "Nike vintage hoodie size L" } }
Connect to SSE stream
Assert event sequence:
  1. pipeline_started (pipeline=="sell")
  2. agent_started (agent_name=="vision_agent")
  3. agent_completed (agent_name=="vision_agent")
  4. vision_result (brand, detected_item, confidence)
  5. agent_started (agent_name=="ebay_sold_comps_agent")
  6. agent_completed (agent_name=="ebay_sold_comps_agent")
  7. agent_started (agent_name=="pricing_agent")
  8. agent_completed (agent_name=="pricing_agent")
  9. pricing_result (recommended_price>0, profit_margin, median_price)
  10. agent_started (agent_name=="depop_listing_agent")
  11. agent_completed (agent_name=="depop_listing_agent")

If Browser Use succeeded for depop_listing:
  12. listing_review_required (ready_for_confirmation==true)
  Then: POST /sell/listing-decision with decision="abort"
  13. pipeline_complete

If Browser Use fell back:
  12. pipeline_complete (no review pause)

Final GET /result/{session_id}:
  - status == "completed"
  - outputs.vision_analysis.brand == "Nike"
  - outputs.ebay_sold_comps.median_sold_price > 0
  - outputs.pricing.recommended_list_price > 0
  - outputs.depop_listing.title contains "Nike"
```

### T6.2 — Sell pipeline with vision low confidence pause + correction

```
Run: POST /sell/start with { input: { image_urls: ["https://example.com/unknown-item.jpg"], notes: "" } }
Assert:
  - vision_low_confidence event fires (confidence < 0.70)
  - Pipeline status == "paused"
Then: POST /sell/correct with { corrected_item: { brand: "Supreme", item_name: "Box Logo Tee", model: "FW21", condition: "Like New", search_query: "Supreme box logo tee FW21" } }
Assert:
  - Pipeline resumes from ebay_sold_comps_agent (skips vision)
  - Subsequent agents use corrected data
  - pricing_result reflects Supreme pricing (higher than unknown brand)
  - pipeline_complete fires
```

### T6.3 — Sell pipeline listing review: confirm_submit flow

```
Pre: Pipeline paused at listing_review (from T6.1 with Browser Use)
Run: POST /sell/listing-decision with { decision: "confirm_submit" }
Assert:
  - Browser clicks submit/publish button
  - listing_status == "submitted"
  - pipeline_complete fires
  - Final result shows depop_listing.draft_status == "submitted"
```

### T6.4 — Sell pipeline listing review: revise flow

```
Pre: Pipeline paused at listing_review
Run: POST /sell/listing-decision with { decision: "revise", revision_instructions: "Lower price to $40 and add size info to description" }
Assert:
  - Browser modifies form fields
  - Pipeline re-pauses at listing_review (new deadline, +15 min)
  - listing_preview shows updated price and description
Then: POST /sell/listing-decision with { decision: "confirm_submit" }
Assert: Submission succeeds
```

### T6.5 — Sell pipeline listing review: max revisions (2) enforced

```
Pre: Pipeline paused at listing_review
Run: POST /sell/listing-decision with { decision: "revise", ... } (revision 1)
Run: POST /sell/listing-decision with { decision: "revise", ... } (revision 2)
Run: POST /sell/listing-decision with { decision: "revise", ... } (revision 3)
Assert: Third revision rejected (max 2 revisions)
```

### T6.6 — Sell pipeline listing review: abort flow

```
Pre: Pipeline paused at listing_review
Run: POST /sell/listing-decision with { decision: "abort" }
Assert:
  - Browser discards draft
  - listing_status == "aborted"
  - Pipeline completes (not fails)
```

### T6.7 — Sell pipeline listing review: timeout (15 min)

```
Pre: Pipeline paused at listing_review
Wait: > 15 minutes (or mock time)
Assert:
  - Pipeline auto-aborts the draft
  - Session status == "failed"
  - Error reason contains "sell_listing_review_timeout"
```

### T6.8 — Buy pipeline end-to-end with live Browser Use

```
Run: POST /buy/start with { input: { query: "Nike Dunk Low size 10", budget: 120 } }
Connect to SSE stream
Assert event sequence:
  - pipeline_started (pipeline=="buy")
  - 4x agent_started/completed for search agents (depop, ebay, mercari, offerup)
  - Each search agent's execution_mode is "httpx", "browser_use", or "fallback"
  - search_method events emitted for each (with method field)
  - agent_started/completed for ranking_agent
  - agent_started/completed for negotiation_agent
  - pipeline_complete

Final result:
  - outputs.ranking.top_choice has platform, title, price, url
  - outputs.negotiation.offers is a list
  - Total results across all platforms >= 2
```

### T6.9 — Buy pipeline with all search agents falling back

```
Pre: BROWSER_USE_FORCE_FALLBACK=true, no EBAY_APP_ID (httpx also fails for eBay)
Run: Full buy pipeline
Assert:
  - All 4 search agents report execution_mode == "fallback"
  - browser_use_fallback events emitted >= 4
  - Ranking still works (on fallback data)
  - Negotiation still works (prepares offers, even if can't send)
  - pipeline_complete (not failed)
```

---

## Section 7: Fetch.ai Agent Layer

### T7.1 — Agent builder requires seed environment variable

```
Pre: Unset VISION_FETCH_AGENT_SEED
Run: build_fetch_agent("vision_agent")
Assert: Raises RuntimeError matching "Missing.*SEED"
```

### T7.2 — Agent builder creates valid agent with correct metadata

```
Pre: Set VISION_FETCH_AGENT_SEED
Run: agent = build_fetch_agent("vision_agent")
Assert:
  - Agent has mailbox enabled
  - Agent has chat protocol attached with publish_manifest=True
  - Agent metadata matches FetchAgentSpec for vision_agent
```

### T7.3 — Only resale_copilot_agent is launchable

```
For each agent_slug in all 11 agents:
  spec = get_spec(agent_slug)
  if slug == "resale_copilot_agent":
    assert spec.is_launchable == True
    assert spec.is_public == True
  else:
    assert spec.is_launchable == False
```

### T7.4 — Launch CLI rejects non-launchable agents

```
Run: python -m backend.fetch_agents.launch vision_agent
Assert: Error message about non-launchable agent, exit code non-zero
```

### T7.5 — Fetch agent ports don't overlap with FastAPI agent ports

```
Run: assert_fetch_agent_ports_do_not_overlap()
Assert: No exception (fetch ports 9201-9211 don't overlap with 9101-9110)
```

### T7.6 — Resale copilot routing: sell keywords

```
Test cases:
  "What's this item worth?" → task_family: "sell_price"
  "Price this tee for me" → task_family: "sell_price"
  "List this on Depop" → task_family: "sell_list"
  "Create a draft listing" → task_family: "sell_list"
  "Identify this item" → task_family: "sell_identify" (default)
```

### T7.7 — Resale copilot routing: buy keywords

```
Test cases:
  "Find me a Nike hoodie under $50" → task_family: "buy_rank"
  "Search for vintage tees" → task_family: "buy_rank"
  "Send an offer to this seller" → task_family: "buy_negotiate"
  "Negotiate the price down" → task_family: "buy_negotiate"
```

### T7.8 — run_fetch_query sell chain execution order

```
Run: await run_fetch_query("resale_copilot_agent", "Price this Nike hoodie")
Assert:
  - Execution chain: vision_agent → ebay_sold_comps_agent → pricing_agent
  - Each agent receives previous_outputs from prior step
  - Final result includes pricing.recommended_list_price > 0
```

### T7.9 — run_fetch_query buy chain with parallel search

```
Run: await run_fetch_query("resale_copilot_agent", "Find Nike Dunk Low under $100")
Assert:
  - All 4 search agents executed
  - ranking_agent receives combined results
  - negotiation_agent receives top-ranked listings
  - Final result includes ranking.top_choice
```

### T7.10 — run_fetch_query with explicit task_request

```
Run: await run_fetch_query("vision_agent", task_request={
    "session_id": "test-123",
    "pipeline": "sell",
    "original_input": { "image_urls": ["https://example.com/photo.jpg"], "notes": "Nike hoodie" },
    "previous_outputs": {}
})
Assert:
  - Agent uses task_request context (not free-text routing)
  - Returns VisionAnalysisOutput with detected_item, brand, confidence
```

### T7.11 — run_fetch_query empty results handling

```
Run: await run_fetch_query("depop_search_agent", "xyznonexistent12345")
Assert:
  - Returns valid output (not None, not exception)
  - Results list may be empty or contain fallback items
  - No crash on zero results
```

### T7.12 — URL and budget extraction from natural language

```
Assert: extract_urls("Find me this https://depop.com/item/123") == ["https://depop.com/item/123"]
Assert: extract_urls("No URLs here") == []
Assert: extract_budget("Under $45") == 45.0
Assert: extract_budget("budget 100") == 100.0
Assert: extract_budget("Find me a tee") == None
Assert: extract_budget("$0") == 0.0
```

### T7.13 — Chat protocol message handling

```
Simulate: Send ChatMessage to built agent
Assert:
  - ChatAcknowledgement sent immediately
  - Agent processes request
  - Response ChatMessage contains result
  - EndSessionContent present in final message
```

### T7.14 — Chat protocol error handling

```
Simulate: Send ChatMessage that causes internal exception
Assert:
  - Error is caught and logged
  - Response ChatMessage contains error description (not stack trace)
  - EndSessionContent still sent (session not left hanging)
```

---

## Section 8: Cross-Cutting Concerns

### T8.1 — Concurrent buy pipelines don't interfere

```
Run in parallel:
  Pipeline A: POST /buy/start with query="Nike Dunk" budget=100
  Pipeline B: POST /buy/start with query="Adidas Samba" budget=80
Assert:
  - Both complete independently
  - Pipeline A results contain "Nike" or "Dunk"
  - Pipeline B results contain "Adidas" or "Samba"
  - No cross-contamination of results
  - Session IDs are different
```

### T8.2 — Concurrent sell pipelines with shared browser profiles

```
Run in parallel:
  Pipeline A: POST /sell/start with Nike hoodie image
  Pipeline B: POST /sell/start with Adidas jacket image
Assert:
  - Both eventually complete (one may queue while other uses browser)
  - No browser profile corruption
  - Each gets correct pricing for their item
```

### T8.3 — Pipeline SSE stream reconnection after disconnect

```
Run: Start sell pipeline, connect to SSE stream
After agent_started for vision_agent: disconnect SSE
Wait 5 seconds, reconnect to same stream URL
Assert:
  - Missed events are recoverable via GET /result/{session_id}
  - Stream resumes from current position (or returns full event history)
```

### T8.4 — Stale listing URL during negotiation

```
Setup: Run buy pipeline, get ranked results
Before negotiation: ensure listing URL returns 404 (item delisted)
Run: negotiation_agent attempts to send offer
Assert:
  - Offer status is "failed"
  - failure_reason explains page not found / listing unavailable
  - Pipeline completes (doesn't crash)
  - offer_failed SSE event emitted
```

### T8.5 — Pipeline with mixed execution modes across agents

```
Pre: EBAY_APP_ID set (httpx works for eBay), no profiles for Depop (Browser Use fails)
Run: Full buy pipeline
Assert:
  - ebay_search_agent: execution_mode == "httpx"
  - depop_search_agent: execution_mode == "fallback"
  - mercari_search_agent: may be "httpx" or "fallback"
  - offerup_search_agent: execution_mode == "fallback" (no httpx)
  - Ranking and negotiation still work with mixed data sources
```

### T8.6 — BROWSER_USE_FORCE_FALLBACK=true overrides everything

```
Pre: All profiles exist, GOOGLE_API_KEY set, but BROWSER_USE_FORCE_FALLBACK=true
Run: Full sell pipeline + full buy pipeline
Assert:
  - Every agent that uses Browser Use reports execution_mode == "fallback"
  - No Chromium process launched
  - Pipelines complete successfully with deterministic data
  - browser_use_runtime_ready() returns False
```

### T8.7 — Agent retry logic (BUY_AGENT_MAX_RETRIES)

```
Pre: BUY_AGENT_MAX_RETRIES=2, mock depop_search_agent to fail first 2 times then succeed
Run: Buy pipeline
Assert:
  - depop_search_agent attempted 3 times (1 initial + 2 retries)
  - agent_retrying SSE events emitted for each retry
  - Final result uses the successful attempt
```

### T8.8 — Agent retry exhaustion falls to fallback

```
Pre: BUY_AGENT_MAX_RETRIES=1, mock depop_search_agent to always fail
Run: Buy pipeline
Assert:
  - depop_search_agent attempted 2 times (1 initial + 1 retry)
  - Falls back to deterministic data
  - Pipeline completes (not fails)
  - agent_error SSE event emitted with retry info
```

---

## Section 9: Marketplace Task Prompt Contracts

### T9.1 — Search task prompts contain required instructions

```
For each platform in [depop, ebay, mercari, offerup]:
  task = build_marketplace_search_task(platform, "Nike tee", max_results=10)
  Assert:
    - Contains platform-specific search URL
    - Contains "JSON" (structured output instruction)
    - Contains fields: title, price, url, condition, seller
    - Contains max_results limit
```

### T9.2 — Depop listing prepare task stops before submit

```
task = build_depop_listing_prepare_task(title="Test", description="desc", suggested_price=50, ...)
Assert:
  - Contains "depop.com/sell"
  - Contains "Stop at the final publish" or equivalent
  - Contains "ready_for_confirmation"
  - Contains "do not click" submit/publish
```

### T9.3 — Depop listing revision task preserves unmentioned fields

```
task = build_depop_listing_revision_task(revision_instructions="Change price to $40")
Assert:
  - Contains instruction to preserve fields not mentioned
  - Contains baseline values for comparison
  - Still stops before submit
```

### T9.4 — Depop listing submit task clicks publish

```
task = build_depop_listing_submit_task()
Assert:
  - Contains instruction to find and click publish/submit
  - Contains "listing_status": "submitted" in expected output
```

### T9.5 — Negotiation task includes message and offer price

```
task = build_negotiation_task(listing_url="https://depop.com/item/123", message="Is $40 ok?", offer_price=40)
Assert:
  - Contains the listing URL
  - Contains the exact message text
  - Contains the offer price
  - Contains expected output format: status, conversation_url, failure_reason
```

---

## Section 10: Fetch.ai + Browser Use Integration

### T10.1 — Fetch-enabled sell pipeline uses Browser Use when available

```
Pre: FETCH_ENABLED=true, all Browser Use prerequisites met
Run: POST /sell/start (or via run_fetch_query)
Assert:
  - Fetch.ai agent chain executes: vision → comps → pricing → listing
  - ebay_sold_comps_agent execution_mode == "browser_use" (or "httpx")
  - depop_listing_agent execution_mode == "browser_use"
  - Results contain real scraped data
```

### T10.2 — Fetch-enabled pipeline gracefully falls back

```
Pre: FETCH_ENABLED=true, BROWSER_USE_FORCE_FALLBACK=true
Run: Full sell and buy pipelines
Assert:
  - All agents fall back to deterministic data
  - Fetch.ai routing still works correctly
  - No uAgents protocol errors
  - Pipeline completes successfully
```

### T10.3 — Fetch-enabled buy pipeline parallel search

```
Pre: FETCH_ENABLED=true
Run: await run_fetch_query("resale_copilot_agent", "Find vintage Nike tee under $45")
Assert:
  - All 4 search agents invoked
  - Results aggregated correctly
  - ranking_agent receives combined results from all platforms
  - Top choice has valid platform, title, price
```

### T10.4 — fetch_integration_flags() returns non-secret info

```
Run: flags = fetch_integration_flags()
Assert:
  - "fetch_enabled" key exists (bool)
  - "agent_execution_mode" key exists (str)
  - No secret keys (no API keys, no seeds, no tokens)
```

### T10.5 — /health endpoint includes fetch status

```
Run: GET /health
Assert:
  - Response includes agent_execution_mode
  - If FETCH_ENABLED: includes fetch agent count
  - Status is "ok"
```

---

## Test Execution Summary

| Section | Tests | Requires Browser Use | Requires Fetch |
|---------|-------|---------------------|----------------|
| 1. Runtime Audit | 5 | No | No |
| 2. 3-Tier Resolution | 12 | Partial (T2.8) | No |
| 3. Live Scraping | 13 | Yes | No |
| 4. Failure Classification | 4 | No | No |
| 5. SSE Events | 5 | No | No |
| 6. Full Pipeline | 9 | Yes | No |
| 7. Fetch.ai Layer | 14 | No | Yes |
| 8. Cross-Cutting | 8 | Mixed | No |
| 9. Task Prompts | 5 | No | No |
| 10. Fetch + Browser Use | 5 | Yes | Yes |
| **Total** | **80** | | |

### Recommended execution order

1. Section 1 (audit) — validates environment is ready
2. Section 4 (failure classification) — unit tests, no external deps
3. Section 5 (SSE events) — unit tests with mocks
4. Section 9 (task prompts) — contract tests, no browser
5. Section 2 (3-tier resolution) — mix of unit + integration
6. Section 7 (Fetch.ai) — requires seeds but not browser
7. Section 3 (live scraping) — requires full Browser Use setup
8. Section 6 (full pipeline) — end-to-end
9. Section 8 (cross-cutting) — concurrency and edge cases
10. Section 10 (Fetch + Browser Use) — full integration
