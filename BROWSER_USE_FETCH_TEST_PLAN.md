# Browser Use + Fetch.ai Agent Test Plan

Exhaustive test suite for live Browser Use and Fetch.ai agent validation. These tests require Chromium, `GOOGLE_API_KEY`, warmed browser profiles, and (for Fetch tests) Python 3.12/3.13 with uagents installed.

**Prerequisites:**
- `make install` completed
- `GOOGLE_API_KEY` set
- `BROWSER_USE_FORCE_FALLBACK=false` (or unset)
- Browser profiles warmed at `profiles/{depop,ebay,mercari,offerup}`
- For Fetch tests: `make venv-fetch`, agent seeds set, `FETCH_ENABLED=true`

---

## 1. Browser Use Core (`backend/agents/browser_use_support.py`)

### 1.1 `run_structured_browser_task` — Happy Path
| ID | Test | Expected |
|----|------|----------|
| BU-CORE-01 | Call with a simple eBay search task, `output_model=BrowserUseSearchResult`, `max_steps=12` | Returns dict matching Pydantic model, no exception |
| BU-CORE-02 | Verify `Agent()` receives correct `llm` (ChatGoogle with `BROWSER_USE_GEMINI_MODEL`) | LLM type is ChatGoogle, model matches env var or default `gemini-2.5-flash` |
| BU-CORE-03 | Verify `BrowserSession` is created with `BrowserProfile(user_data_dir=...)` when `user_data_dir` provided | Session uses the profile directory |
| BU-CORE-04 | Verify `max_steps` defaults to `BROWSER_USE_MAX_STEPS` env (default 15) when not passed | Agent.max_steps == 15 or env override |
| BU-CORE-05 | Verify `session.stop()` is called in `finally` block even on success | Session cleanup confirmed |
| BU-CORE-06 | Verify `session.stop()` is called in `finally` block on exception | Session cleanup confirmed |

### 1.2 `run_structured_browser_task` — Failure Modes
| ID | Test | Expected |
|----|------|----------|
| BU-CORE-07 | `BROWSER_USE_FORCE_FALLBACK=true` | Raises `BrowserUseRuntimeUnavailable("Browser Use fallback forced by environment")` |
| BU-CORE-08 | `GOOGLE_API_KEY` unset | Raises `BrowserUseRuntimeUnavailable("GOOGLE_API_KEY is not configured")` |
| BU-CORE-09 | `browser_use` package not importable | Raises `BrowserUseRuntimeUnavailable("Browser Use dependencies are not installed")` |
| BU-CORE-10 | Agent returns `None` from `history.final_result()` | Raises `BrowserUseTaskExecutionError` |
| BU-CORE-11 | Agent output fails Pydantic validation | Raises `ValidationError` |

### 1.3 `classify_browser_use_failure`
| ID | Test | Expected |
|----|------|----------|
| BU-CORE-12 | Pass `BrowserUseRuntimeUnavailable` | Returns `"runtime_unavailable"` |
| BU-CORE-13 | Pass `BrowserUseTaskExecutionError` | Returns `"result_invalid"` |
| BU-CORE-14 | Pass `ValidationError` | Returns `"result_invalid"` |
| BU-CORE-15 | Pass `ValueError` | Returns `"result_invalid"` |
| BU-CORE-16 | Pass exception with "profile" in message | Returns `"profile_missing"` |
| BU-CORE-17 | Pass exception with "revision" in message | Returns `"revision_failed"` |
| BU-CORE-18 | Pass exception with "submit" in message | Returns `"submit_failed"` |
| BU-CORE-19 | Pass exception with "publish" in message | Returns `"submit_failed"` |
| BU-CORE-20 | Pass exception with "abort" in message | Returns `"abort_failed"` |
| BU-CORE-21 | Pass exception with "discard" in message | Returns `"abort_failed"` |
| BU-CORE-22 | Pass generic exception with `operation="prepare_listing_for_review"` | Returns `"review_checkpoint_failed"` |
| BU-CORE-23 | Pass generic exception with `operation="apply_listing_revision"` | Returns `"revision_failed"` |
| BU-CORE-24 | Pass generic exception with `operation="submit_prepared_listing"` | Returns `"submit_failed"` |
| BU-CORE-25 | Pass generic exception with `operation="abort_prepared_listing"` | Returns `"abort_failed"` |
| BU-CORE-26 | Pass completely unknown exception | Returns `"browser_error"` |

### 1.4 `browser_use_runtime_ready`
| ID | Test | Expected |
|----|------|----------|
| BU-CORE-27 | All conditions met (key set, deps importable, fallback off) | Returns `True` |
| BU-CORE-28 | `BROWSER_USE_FORCE_FALLBACK=true` | Returns `False` |
| BU-CORE-29 | `GOOGLE_API_KEY` unset | Returns `False` |

---

## 2. Marketplace Search Tasks (`backend/agents/browser_use_marketplaces.py`)

### 2.1 `run_marketplace_search` — Live Per-Platform
| ID | Test | Expected |
|----|------|----------|
| BU-MKT-01 | `run_marketplace_search("depop", "vintage nike tee")` | Returns list of dicts with keys: title, price, url, condition, seller, seller_score, posted_at. URLs contain `depop.com` |
| BU-MKT-02 | `run_marketplace_search("ebay", "vintage nike tee")` | Same shape. URLs contain `ebay.com` |
| BU-MKT-03 | `run_marketplace_search("mercari", "vintage nike tee")` | Same shape. URLs contain `mercari.com` |
| BU-MKT-04 | `run_marketplace_search("offerup", "vintage nike tee")` | Same shape. URLs contain `offerup.com` |
| BU-MKT-05 | Each result has `price` > 0 and is numeric | Validated per platform |
| BU-MKT-06 | Each result has non-empty `title` and `url` | Validated per platform |
| BU-MKT-07 | `max_results=3` returns at most 3 results | Validated |

### 2.2 `build_marketplace_search_task` — Task String
| ID | Test | Expected |
|----|------|----------|
| BU-MKT-08 | Depop task contains `https://www.depop.com/search/?q=` | Confirmed |
| BU-MKT-09 | eBay task contains `https://www.ebay.com/sch/i.html?_nkw=` | Confirmed |
| BU-MKT-10 | Mercari task contains `https://www.mercari.com/search/?keyword=` | Confirmed |
| BU-MKT-11 | OfferUp task contains `https://offerup.com/search?q=` | Confirmed |
| BU-MKT-12 | Query with special characters is URL-encoded in task | Confirmed |

### 2.3 Depop Listing Tasks
| ID | Test | Expected |
|----|------|----------|
| BU-MKT-13 | `build_depop_listing_prepare_task(title, price, desc, condition, image_url)` — task string navigates to depop.com/sell, fills form, does NOT submit | Task string contains "do not submit" or "do not publish" |
| BU-MKT-14 | `build_depop_listing_revision_task(baseline, revision_instructions)` — preserves baseline values, applies revisions | Task string references baseline and instructions |
| BU-MKT-15 | `build_depop_listing_submit_task()` — task publishes the listing | Task string contains "publish" or "submit" |
| BU-MKT-16 | `build_depop_listing_abort_task()` — task discards draft | Task string contains "discard" or "abandon" |

### 2.4 Negotiation Task
| ID | Test | Expected |
|----|------|----------|
| BU-MKT-17 | `build_negotiation_task(platform, listing_url, message, target_price)` — task navigates to URL, sends message, sets offer price | Task string contains all parameters |

---

## 3. Depop Search Agent (`backend/agents/depop_search_agent.py`)

### 3.1 Three-Tier Fallback
| ID | Test | Expected |
|----|------|----------|
| BU-DEPOP-01 | Live: httpx succeeds | `execution_mode == "httpx"`, results non-empty, each listing has `platform == "depop"` |
| BU-DEPOP-02 | Live: httpx fails, Browser Use succeeds | `execution_mode == "browser_use"`, results valid |
| BU-DEPOP-03 | Live: both fail, fallback used | `execution_mode == "fallback"`, exactly 2 deterministic results, `browser_use_error` populated |
| BU-DEPOP-04 | Full `build_output` returns valid `SearchResultsOutput` shape | All required fields present |
| BU-DEPOP-05 | `search_method` SSE event emitted with correct method | Event data matches `execution_mode` |
| BU-DEPOP-06 | `listing_found` events emitted for each result | Count matches results length |
| BU-DEPOP-07 | `browser_use_fallback` event emitted when Browser Use fails | Event contains error category |

---

## 4. eBay Search Agent (`backend/agents/ebay_search_agent.py`)

### 4.1 Three-Tier Fallback
| ID | Test | Expected |
|----|------|----------|
| BU-EBAY-01 | Live: eBay Browse API succeeds (requires `EBAY_APP_ID` + `EBAY_CERT_ID`) | `execution_mode == "httpx"`, results from API |
| BU-EBAY-02 | API credentials missing, Browser Use succeeds | `execution_mode == "browser_use"` |
| BU-EBAY-03 | Both fail, fallback used | `execution_mode == "fallback"`, 2 deterministic results |
| BU-EBAY-04 | Each listing has `platform == "ebay"` | Validated |
| BU-EBAY-05 | OAuth token fetch: POST to `api.ebay.com/identity/v1/oauth2/token` | Returns valid bearer token when creds set |
| BU-EBAY-06 | OAuth token fetch: missing creds returns `None` | Graceful fallback |

---

## 5. Mercari Search Agent (`backend/agents/mercari_search_agent.py`)

### 5.1 Three-Tier Fallback
| ID | Test | Expected |
|----|------|----------|
| BU-MERC-01 | Live: httpx succeeds | `execution_mode == "httpx"`, results valid |
| BU-MERC-02 | httpx fails, Browser Use succeeds | `execution_mode == "browser_use"` |
| BU-MERC-03 | Both fail, fallback | `execution_mode == "fallback"`, 2 results |
| BU-MERC-04 | Each listing has `platform == "mercari"` | Validated |

---

## 6. OfferUp Search Agent (`backend/agents/offerup_search_agent.py`)

### 6.1 Two-Tier (No httpx)
| ID | Test | Expected |
|----|------|----------|
| BU-OFUP-01 | Live: Browser Use succeeds | `execution_mode == "browser_use"`, results valid |
| BU-OFUP-02 | Browser Use fails, fallback | `execution_mode == "fallback"`, 2 results |
| BU-OFUP-03 | Each listing has `platform == "offerup"` | Validated |
| BU-OFUP-04 | `try_browser_use_search` with empty query returns `(None, None)` | No Browser Use attempted |

---

## 7. eBay Sold Comps Agent (`backend/agents/ebay_sold_comps_agent.py`)

### 7.1 Browser Use Research
| ID | Test | Expected |
|----|------|----------|
| BU-COMP-01 | Live: `try_browser_use_research(query)` succeeds | Returns dict with `median_sold_price`, `low_sold_price`, `high_sold_price`, `sample_size` |
| BU-COMP-02 | Prices are numeric and `low <= median <= high` | Validated |
| BU-COMP-03 | `sample_size >= 1` | Validated |
| BU-COMP-04 | Browser Use uses `allowed_domains=["ebay.com", "www.ebay.com"]` | Confirmed via task/config |
| BU-COMP-05 | Browser Use uses `max_steps=12, max_failures=3` | Confirmed |
| BU-COMP-06 | Output model is `SoldCompResearch` | Validated |
| BU-COMP-07 | Fallback: returns deterministic pricing from category/brand/condition multipliers | Prices are plausible, `execution_mode == "fallback"` |
| BU-COMP-08 | Error classified correctly on Browser Use failure | `browser_use_error` matches `classify_browser_use_failure` output |

---

## 8. Depop Listing Agent (`backend/agents/depop_listing_agent.py`)

### 8.1 Listing Prepare (Draft Creation)
| ID | Test | Expected |
|----|------|----------|
| BU-LIST-01 | Live: `try_browser_use_listing()` with valid title/price/desc/condition | Returns dict with `title`, `price`, `description`, `condition`, `listing_status`, `ready_for_confirmation=True` |
| BU-LIST-02 | Profile missing at `profiles/depop` | Returns `(None, "profile_missing", False)` |
| BU-LIST-03 | Uses `keep_alive=True` (browser stays open for review) | Confirmed |
| BU-LIST-04 | Uses `max_steps=18, max_failures=3` | Confirmed |
| BU-LIST-05 | Uses `allowed_domains=["depop.com", "www.depop.com"]` | Confirmed |
| BU-LIST-06 | Output model is `BrowserUseListingCheckpointResult` | Validated |
| BU-LIST-07 | `draft_created` SSE event emitted on success | Event contains listing preview |

### 8.2 Listing Revision
| ID | Test | Expected |
|----|------|----------|
| BU-LIST-08 | Live: `apply_browser_use_listing_revision(baseline, instructions)` | Returns updated checkpoint preserving unchanged fields |
| BU-LIST-09 | Revision applies specified changes only | Diff between baseline and result matches instructions |
| BU-LIST-10 | `_infer_listing_operation` returns `"apply_listing_revision"` for revision tasks | Confirmed |
| BU-LIST-11 | Revision failure classified as `"revision_failed"` | Error category matches |

### 8.3 Listing Submit
| ID | Test | Expected |
|----|------|----------|
| BU-LIST-12 | Live: `submit_browser_use_listing()` | Returns `listing_status: "submitted"` |
| BU-LIST-13 | Submit failure classified as `"submit_failed"` | Error category matches |

### 8.4 Listing Abort
| ID | Test | Expected |
|----|------|----------|
| BU-LIST-14 | Live: `abort_browser_use_listing()` | Returns without error |
| BU-LIST-15 | Abort failure classified as `"abort_failed"` | Error category matches |

### 8.5 Fallback Behavior
| ID | Test | Expected |
|----|------|----------|
| BU-LIST-16 | Full `build_output` when Browser Use unavailable | Returns deterministic listing with `listing_status != "submitted"`, `ready_for_confirmation=True` |

---

## 9. Negotiation Agent (`backend/agents/negotiation_agent.py`)

### 9.1 Live Offer Sending
| ID | Test | Expected |
|----|------|----------|
| BU-NEG-01 | Live: `try_send_offer(prepared_offer)` on depop listing | Returns `execution_mode: "browser_use"`, `status: "sent"` or `"failed"` |
| BU-NEG-02 | Live: same for ebay | Same shape |
| BU-NEG-03 | Live: same for mercari | Same shape |
| BU-NEG-04 | Live: same for offerup | Same shape |
| BU-NEG-05 | Uses `max_steps=16, max_failures=3, keep_alive=True` | Confirmed |
| BU-NEG-06 | Uses `build_negotiation_task(platform, listing_url, message, target_price)` | Task string contains all params |
| BU-NEG-07 | Output model is `BrowserUseNegotiationResult` | Validated |

### 9.2 Fallback Modes
| ID | Test | Expected |
|----|------|----------|
| BU-NEG-08 | Profile missing for platform | Returns `execution_mode: "deterministic"`, `browser_use_error: "profile_missing"` |
| BU-NEG-09 | `BrowserUseRuntimeUnavailable` caught | Returns `execution_mode: "deterministic"`, error classified |
| BU-NEG-10 | Generic exception caught | Returns `status: "failed"`, `failure_reason` populated, `execution_mode: "browser_use"` |
| BU-NEG-11 | `offer_prepared` event emitted | Event data has `platform`, `target_price`, `message` |
| BU-NEG-12 | `offer_sent` event on success | Event data has `execution_mode` |
| BU-NEG-13 | `offer_failed` event on failure | Event data has error details |

---

## 10. httpx Clients (`backend/agents/httpx_clients.py`)

### 10.1 Depop httpx
| ID | Test | Expected |
|----|------|----------|
| BU-HTTP-01 | Live: `search_depop_httpx("vintage nike tee")` | Returns list of dicts or `None` |
| BU-HTTP-02 | Each result has keys: platform, title, price, url, condition, seller, seller_score, posted_at | Validated |
| BU-HTTP-03 | `platform == "depop"` for all results | Validated |
| BU-HTTP-04 | Network error returns `None` (not exception) | Confirmed |

### 10.2 Mercari httpx
| ID | Test | Expected |
|----|------|----------|
| BU-HTTP-05 | Live: `search_mercari_httpx("vintage nike tee")` | Returns list or `None` |
| BU-HTTP-06 | Each result has same key shape | Validated |
| BU-HTTP-07 | `platform == "mercari"` | Validated |
| BU-HTTP-08 | Network error returns `None` | Confirmed |

### 10.3 eBay Browse API
| ID | Test | Expected |
|----|------|----------|
| BU-HTTP-09 | Live: `search_ebay_browse_api("vintage nike tee")` with valid creds | Returns list or `None` |
| BU-HTTP-10 | `get_ebay_oauth_token()` with valid `EBAY_APP_ID` + `EBAY_CERT_ID` | Returns bearer token string |
| BU-HTTP-11 | `get_ebay_oauth_token()` with missing creds | Returns `None` |
| BU-HTTP-12 | `platform == "ebay"` for all results | Validated |

---

## 11. Deterministic Fallback (`backend/agents/search_support.py`)

### 11.1 `build_platform_results`
| ID | Test | Expected |
|----|------|----------|
| BU-FALL-01 | Each platform returns exactly 2 listings | `len(results) == 2` |
| BU-FALL-02 | Prices use `PLATFORM_PRICE_OFFSETS` (depop: 1.02, ebay: 0.94, mercari: 0.97, offerup: 0.88) | Price ratios match |
| BU-FALL-03 | Second listing offset by `SECOND_RESULT_PRICE_GAP` | Difference matches platform gap |
| BU-FALL-04 | Condition matches `CONDITION_BY_PLATFORM` per platform | Validated |
| BU-FALL-05 | Seller scores use `SELLER_SCORE_BASE` + ordinal offsets | Validated |
| BU-FALL-06 | `posted_at` dates use `POSTED_DAYS_AGO` offsets | Dates match expected deltas |
| BU-FALL-07 | Brand detection: "nike" query produces "Nike" brand | Validated |
| BU-FALL-08 | Budget parameter affects base price | Results scale with budget |
| BU-FALL-09 | `previous_prices` affects base price calculation | Cross-platform price coherence |
| BU-FALL-10 | URL format: `https://{platform}.example/{slug}` | Pattern validated |
| BU-FALL-11 | Results are identical across runs (deterministic) | Two calls produce same output |

---

## 12. Browser Use Events (`backend/agents/browser_use_events.py`)

| ID | Test | Expected |
|----|------|----------|
| BU-EVT-01 | `emit_browser_use_event` posts to `POST /internal/event/{session_id}` | Returns 200, event appears in session |
| BU-EVT-02 | Event uses `INTERNAL_API_TOKEN` header | Confirmed |
| BU-EVT-03 | Invalid session_id fails gracefully | No crash, error logged |

---

## 13. Runtime Audit (`backend/browser_use_runtime_audit.py`)

| ID | Test | Expected |
|----|------|----------|
| BU-AUD-01 | Run audit with all prereqs met | All checks pass |
| BU-AUD-02 | Checks GOOGLE_API_KEY presence | Reports pass/fail |
| BU-AUD-03 | Checks browser_use importability | Reports pass/fail |
| BU-AUD-04 | Checks each platform profile directory exists | Reports per-platform |
| BU-AUD-05 | Checks Chromium installed | Reports pass/fail |
| BU-AUD-06 | Checks AGENT_TIMEOUT_SECONDS >= 30 | Reports pass/fail |
| BU-AUD-07 | Checks BROWSER_USE_FORCE_FALLBACK is false | Reports pass/fail |

---

## 14. Validation Harness (`backend/browser_use_validation.py`)

### 14.1 Scenario Validation
| ID | Test | Expected |
|----|------|----------|
| BU-VAL-01 | `--group buy_search` in fallback mode | All 4 search agents complete with `execution_mode == "fallback"` |
| BU-VAL-02 | `--group buy_search --require-live` | All 4 search agents complete with `execution_mode == "browser_use"` |
| BU-VAL-03 | `--scenario depop_listing --mode fallback` | Listing agent completes in fallback |
| BU-VAL-04 | `--scenario depop_listing --require-live` | Listing agent uses live Browser Use |
| BU-VAL-05 | `--group sell` in fallback mode | All sell agents complete |
| BU-VAL-06 | `--group sell --require-live` | All sell agents use live Browser Use |
| BU-VAL-07 | `--scenario negotiation --require-live` | Negotiation agent sends live offer |

---

## 15. Fetch.ai Runtime (`backend/fetch_runtime.py`)

### 15.1 Agent Spec Registry
| ID | Test | Expected |
|----|------|----------|
| FE-RT-01 | `list_fetch_agent_slugs()` returns all 11 slugs | Count == 11, includes vision, pricing, depop_listing, 4 search, ranking, negotiation, ebay_sold_comps, resale_copilot |
| FE-RT-02 | `list_public_fetch_agent_slugs()` returns only `["resale_copilot_agent"]` | Exactly 1 entry |
| FE-RT-03 | Each spec has non-empty: slug, name, port, seed_env_var, description, persona | Validated for all 11 |
| FE-RT-04 | Ports range 9201–9211 with no overlaps | Validated |
| FE-RT-05 | `get_fetch_agent_spec("unknown")` raises ValueError | Confirmed |
| FE-RT-06 | Only `resale_copilot_agent` has `is_launchable=True` | Confirmed |

### 15.2 `execute_agent`
| ID | Test | Expected |
|----|------|----------|
| FE-RT-07 | Creates session_id matching `"fetch-{slug}-{uuid4}"` pattern | Regex validated |
| FE-RT-08 | Calls `run_local_agent_task(agent_slug, request)` with correct AgentTaskRequest | Request has session_id, pipeline, step, input, context |
| FE-RT-09 | Validates output with `validate_agent_output()` | Valid output passes, invalid raises |
| FE-RT-10 | Non-"completed" status raises RuntimeError | Confirmed |

### 15.3 `run_fetch_query`
| ID | Test | Expected |
|----|------|----------|
| FE-RT-11 | Empty text returns friendly message, no agent execution | Confirmed |
| FE-RT-12 | Sell-side agent (e.g. `vision_agent`) routes through `_run_sell_chain` | Chain executes vision → comps → pricing → listing in order |
| FE-RT-13 | Buy-side agent (e.g. `depop_search_agent`) routes through `_run_buy_chain` | Chain executes search (parallel) → ranking → negotiation |
| FE-RT-14 | `resale_copilot_agent` routes through `_run_resale_copilot_query` | Infers task family and dispatches |
| FE-RT-15 | Structured `AgentTaskRequest` input is accepted alongside free text | Both paths produce valid output |

### 15.4 Sell Chain (`_run_sell_chain`)
| ID | Test | Expected |
|----|------|----------|
| FE-RT-16 | Vision → ebay_sold_comps → pricing → depop_listing executed in sequence | Each step receives `previous_outputs` from all prior steps |
| FE-RT-17 | Requesting `vision_agent` returns vision output only | Does not execute downstream |
| FE-RT-18 | Requesting `pricing_agent` executes vision + comps + pricing | 3 agents called |
| FE-RT-19 | Requesting `depop_listing_agent` executes full chain | All 4 agents called |

### 15.5 Buy Chain (`_run_buy_chain`)
| ID | Test | Expected |
|----|------|----------|
| FE-RT-20 | 4 search agents run concurrently via `_run_fetch_search_agents()` | All 4 called, results merged |
| FE-RT-21 | Empty results from all searches → `build_buy_no_results_output()` | No-results output returned |
| FE-RT-22 | Search results passed to ranking_agent as `previous_outputs` | Ranking receives all search outputs |
| FE-RT-23 | Ranking results passed to negotiation_agent | Negotiation receives ranking + search outputs |

### 15.6 `format_fetch_response`
| ID | Test | Expected |
|----|------|----------|
| FE-RT-24 | Returns human-readable text with JSON body | Contains agent name, formatted result |

---

## 16. Fetch Agent Builder (`backend/fetch_agents/builder.py`)

### 16.1 `build_fetch_agent`
| ID | Test | Expected |
|----|------|----------|
| FE-BLD-01 | Missing seed env var raises RuntimeError | Error names the missing var |
| FE-BLD-02 | Agent created with `mailbox=True, publish_agent_details=True` | Kwargs confirmed |
| FE-BLD-03 | `FETCH_USE_LOCAL_ENDPOINT=true` sets endpoint to `["http://127.0.0.1:{port}/submit"]` | Endpoint present |
| FE-BLD-04 | `FETCH_USE_LOCAL_ENDPOINT` unset or false → no endpoint kwarg | Endpoint absent |
| FE-BLD-05 | Metadata includes description, persona, capabilities, tags, task_family, is_public, handoff_targets | All fields present |
| FE-BLD-06 | readme_path set from spec if file exists | Path resolves to actual file |
| FE-BLD-07 | Protocol registered with `publish_manifest=True` | Confirmed |

### 16.2 ChatMessage Handler
| ID | Test | Expected |
|----|------|----------|
| FE-BLD-08 | Incoming ChatMessage → immediate ChatAcknowledgement sent | Ack includes timestamp and msg_id |
| FE-BLD-09 | Text extracted from message content items | Handles TextContent correctly |
| FE-BLD-10 | `decide_chat_request()` returns `kind="execute"` → `run_fetch_query()` called | Query executed, response sent |
| FE-BLD-11 | `decide_chat_request()` returns `kind="handoff"` → decision.message used as response | No query execution |
| FE-BLD-12 | `decide_chat_request()` returns `kind="clarify"` → decision.message used as response | No query execution |
| FE-BLD-13 | Response ChatMessage includes TextContent + EndSessionContent | Both content types present |
| FE-BLD-14 | Exception during execution → error summary sent as ChatMessage | No crash, error in response text |
| FE-BLD-15 | ChatAcknowledgement handler logs debug message | Log contains sender and acknowledged_msg_id |

### 16.3 uAgents Import
| ID | Test | Expected |
|----|------|----------|
| FE-BLD-16 | Python 3.12: imports succeed | `Agent`, `Context`, `Protocol`, chat types all available |
| FE-BLD-17 | Python 3.14: import fails | RuntimeError with version hint |

---

## 17. Chat Profiles (`backend/fetch_agents/chat_profiles.py`)

### 17.1 `decide_chat_request`
| ID | Test | Expected |
|----|------|----------|
| FE-CHAT-01 | Empty text → `kind="clarify"` | Message prompts for input |
| FE-CHAT-02 | Out-of-scope task for agent → `kind="handoff"` | Message references handoff_targets |
| FE-CHAT-03 | `vision_agent` with URLs → `kind="execute"` | Proceed |
| FE-CHAT-04 | `vision_agent` with single word (no URL) → `kind="clarify"` | Needs more input |
| FE-CHAT-05 | `vision_agent` with 2+ words → `kind="execute"` | Proceed |
| FE-CHAT-06 | `pricing_agent` with URLs → `kind="execute"` | Proceed |
| FE-CHAT-07 | `pricing_agent` with 2 words → `kind="clarify"` | Needs 3+ words |
| FE-CHAT-08 | `depop_listing_agent` with 3+ words → `kind="execute"` | Proceed |
| FE-CHAT-09 | `resale_copilot_agent` buy task without budget → `kind="clarify"` | Asks for budget |
| FE-CHAT-10 | `resale_copilot_agent` sell task without image/description → `kind="clarify"` | Asks for details |
| FE-CHAT-11 | `resale_copilot_agent` with valid buy query + budget → `kind="execute"` | Proceed |

---

## 18. Fetch Agent Launcher (`backend/fetch_agents/launch.py`)

| ID | Test | Expected |
|----|------|----------|
| FE-LAUNCH-01 | No args → usage error, exit 1 | Error message shown |
| FE-LAUNCH-02 | Unknown slug → ValueError | Error names slug |
| FE-LAUNCH-03 | Non-launchable agent slug → error | Only resale_copilot allowed |
| FE-LAUNCH-04 | Valid slug with seed set → `agent.run()` starts | Agent event loop running |

---

## 19. Multi-Agent Runner (`backend/run_fetch_agents.py`)

| ID | Test | Expected |
|----|------|----------|
| FE-RUN-01 | `assert_fetch_agent_ports_do_not_overlap()` passes | No port conflicts between 9101-9110 and 9201-9211 |
| FE-RUN-02 | Only public agents spawned as subprocesses | Only `resale_copilot_agent` launched |
| FE-RUN-03 | PYTHONPATH set to cwd in subprocess env | Confirmed |
| FE-RUN-04 | SIGTERM terminates all child processes | Graceful shutdown within 5s |

---

## 20. Orchestrator Fetch Integration (`backend/orchestrator.py`)

### 20.1 FETCH_ENABLED Routing
| ID | Test | Expected |
|----|------|----------|
| FE-ORCH-01 | `FETCH_ENABLED=true`: sell pipeline calls `run_fetch_query` instead of `run_agent_task` | All 4 sell agents go through Fetch path |
| FE-ORCH-02 | `FETCH_ENABLED=true`: buy pipeline calls `run_fetch_query` | All 6 buy agents go through Fetch path |
| FE-ORCH-03 | `FETCH_ENABLED=false`: normal `run_agent_task` path used | Direct agent registry |
| FE-ORCH-04 | `task_request` passed to `run_fetch_query` preserves session_id, pipeline, step | All fields match |
| FE-ORCH-05 | Output validated by `validate_agent_output()` regardless of path | Both paths validate |

### 20.2 Retry Logic with Fetch
| ID | Test | Expected |
|----|------|----------|
| FE-ORCH-06 | Search agent failure with retries enabled: retries through Fetch path | `agent_retrying` event emitted |
| FE-ORCH-07 | Max attempts exhausted → exception propagated | `agent_error` event with final attempt |
| FE-ORCH-08 | Timeout via `asyncio.wait_for` applies to Fetch execution | `TimeoutError` classified as `"timeout"` |

---

## 21. Browser Use + Fetch Compatibility

### 21.1 Cross-Cutting Scenarios
| ID | Test | Expected |
|----|------|----------|
| COMPAT-01 | `FETCH_ENABLED=true` + `BROWSER_USE_FORCE_FALLBACK=true`: sell pipeline completes | All agents use fallback, Fetch routing works |
| COMPAT-02 | `FETCH_ENABLED=true` + `BROWSER_USE_FORCE_FALLBACK=true`: buy pipeline completes | All search agents use fallback |
| COMPAT-03 | `FETCH_ENABLED=true` + live Browser Use: sell pipeline uses browser_use | `execution_mode == "browser_use"` where applicable |
| COMPAT-04 | `FETCH_ENABLED=true` + live Browser Use: buy pipeline uses browser_use/httpx | Mixed modes allowed |
| COMPAT-05 | Sell listing review loop works with `FETCH_ENABLED=true` | Pause → confirm/revise/abort all work |
| COMPAT-06 | `execution_mode` and `browser_use_error` metadata propagated through Fetch path | Fields present in final output |
| COMPAT-07 | Vision low-confidence pause works through Fetch path | `LowConfidencePause` raised, correction flow works |

---

## 22. API Endpoint Integration Tests

### 22.1 Health & Catalog
| ID | Test | Expected |
|----|------|----------|
| API-01 | `GET /health` with `FETCH_ENABLED=true` | Response includes `fetch_enabled: true`, `agentverse_credentials_present` |
| API-02 | `GET /fetch-agents` | Returns all 11 agent specs with metadata |
| API-03 | `GET /fetch-agent-capabilities` | Returns specs + runtime info (seed presence, readme availability) |

### 22.2 Full Pipeline E2E
| ID | Test | Expected |
|----|------|----------|
| API-04 | `POST /sell/start` with image → SSE stream → all events → `pipeline_complete` | All 4 sell agents fire events, result has pricing + listing |
| API-05 | `POST /buy/start` with query + budget → SSE stream → `pipeline_complete` | Search + ranking + negotiation results |
| API-06 | Sell pipeline with vision confidence < 0.70 → `vision_low_confidence` event → `POST /sell/correct` → pipeline resumes | Full correction flow |
| API-07 | Sell pipeline → `draft_created` → `POST /sell/listing-decision` confirm → `pipeline_complete` | Listing submitted |
| API-08 | Sell pipeline → `draft_created` → `POST /sell/listing-decision` revise → revised draft → confirm | Revision applied then submitted |
| API-09 | Sell pipeline → `draft_created` → `POST /sell/listing-decision` abort → `pipeline_complete` | Listing aborted |
| API-10 | Sell listing review timeout (15 min) | Session auto-expired by cleanup loop |

---

## 23. Fetch.ai Demo Script (`scripts/fetch_demo.py`)

| ID | Test | Expected |
|----|------|----------|
| FE-DEMO-01 | `--catalog` flag prints public agent specs and exits | Output contains resale_copilot_agent |
| FE-DEMO-02 | Send buy query to running resale_copilot_agent | Receives ChatAcknowledgement + response ChatMessage with EndSessionContent |
| FE-DEMO-03 | Send sell query | Receives response with vision/pricing data |
| FE-DEMO-04 | Timeout exceeded | Raises RuntimeError |
| FE-DEMO-05 | Invalid agent address | Error within timeout |

---

## Execution Order Recommendation

Run in this order to progressively validate layers:

1. **Fallback layer first** (Section 11) — no external deps needed
2. **Error classification** (Section 1.3) — unit-level, no network
3. **Runtime checks** (Sections 1.4, 13) — validates environment
4. **httpx clients** (Section 10) — network but no Chromium
5. **Browser Use core** (Section 1.1-1.2) — needs Chromium + API key
6. **Marketplace searches** (Section 2) — live Browser Use per platform
7. **Individual agents** (Sections 3-9) — full agent flows
8. **Validation harness** (Section 14) — grouped scenario validation
9. **Fetch runtime** (Sections 15-17) — needs Python 3.12 + seeds
10. **Fetch builder + launcher** (Sections 16, 18-19) — uAgents instantiation
11. **Orchestrator integration** (Section 20) — Fetch routing
12. **Cross-cutting** (Section 21) — Browser Use + Fetch together
13. **Full E2E** (Sections 22-23) — complete pipeline flows

---

## Environment Configurations to Test

| Config | `FETCH_ENABLED` | `BROWSER_USE_FORCE_FALLBACK` | `GOOGLE_API_KEY` | Profiles | Purpose |
|--------|-----------------|------------------------------|-------------------|----------|---------|
| A: Fallback only | `false` | `true` | unset | absent | Deterministic baseline |
| B: httpx + fallback | `false` | `true` | unset | absent | API tier without Browser Use |
| C: Full Browser Use | `false` | `false` | set | present | Live browser automation |
| D: Fetch + fallback | `true` | `true` | unset | absent | Fetch routing with deterministic agents |
| E: Fetch + Browser Use | `true` | `false` | set | present | Full stack |
| F: Missing profiles | `false` | `false` | set | absent | Profile-missing error paths |
