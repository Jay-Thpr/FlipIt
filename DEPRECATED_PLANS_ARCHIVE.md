# Deprecated Plans Archive

This file contains the aggregated contents of various implementation plans, checklists, and status documents that are no longer actively used.



# --- ARCHIVED FILE: AGENTVERSE_IMPLEMENTATION_PLAN.md ---

# Agentverse + Fetch uAgents — Implementation Plan

**Purpose:** Executable plan to run the current Fetch topology locally, register the public Agentverse agents in mailbox mode, keep repo docs aligned with code, and collect sponsor deliverables (ASI:One chat URL plus public profile URLs). Complements **`IMPLEMENTATION-PLAN.md`** Phase 6 and the profile guide **`AGENTVERSE_SETUP.md`**.

**Related docs:** [`FETCH_INTEGRATION.md`](FETCH_INTEGRATION.md), [`backend/README.md`](backend/README.md) (Fetch section), [`.env.example`](.env.example), [`API_CONTRACT.md`](API_CONTRACT.md) (`GET /fetch-agents`).

**Non-goals:** Rewriting uAgent business logic; changing `/task` or SSE contracts; owning ASI:One product behavior (discovery is best-effort).

---

## 1. Success criteria

| Outcome | Verification |
|--------|----------------|
| Public Fetch uAgents start under `.venv-fetch` without import errors | Four successful launch logs for `resale_copilot_agent`, `vision_agent`, `pricing_agent`, and `depop_listing_agent`; ports `9211`, `9201`, `9203`, and `9204` not conflicting |
| Mailbox registration succeeds | Logs include successful mailbox / Agentverse registration for each public agent |
| Addresses captured | Each public `agent1q...` stored in the matching `*_AGENTVERSE_ADDRESS` in `.env` |
| Backend catalog accurate | `GET /fetch-agents` returns the full 11-agent catalog with correct `is_public` flags and the recorded public addresses |
| `make check` still passes | CI / local default `FETCH_ENABLED=false` |
| Docs match repo | `AGENTVERSE_SETUP.md` and `FETCH_INTEGRATION.md` describe the 4 public agents plus internal workers accurately |
| Deliverables collected | ASI:One chat session URL + 4 public Agentverse agent URLs documented for submission |

---

## 2. Canonical agent catalog (single source of truth)

Derived from [`backend/fetch_runtime.py`](backend/fetch_runtime.py) `FETCH_AGENT_SPECS` and [`.env.example`](.env.example). Use this table for Agentverse display names, CLI launch, `.env` keys, and the public/private split.

| Display name (uAgent `name`) | Slug (`launch` arg) | Port | Public | Seed env var | Agentverse address env var |
|------------------------------|---------------------|------|--------|--------------|----------------------------|
| ResaleCopilotAgent | `resale_copilot_agent` | 9211 | yes | `RESALE_COPILOT_FETCH_AGENT_SEED` | `RESALE_COPILOT_AGENT_AGENTVERSE_ADDRESS` |
| VisionAgent | `vision_agent` | 9201 | yes | `VISION_FETCH_AGENT_SEED` | `VISION_AGENT_AGENTVERSE_ADDRESS` |
| EbaySoldCompsAgent | `ebay_sold_comps_agent` | 9202 | no | `EBAY_SOLD_COMPS_FETCH_AGENT_SEED` | `EBAY_SOLD_COMPS_AGENT_AGENTVERSE_ADDRESS` |
| PricingAgent | `pricing_agent` | 9203 | yes | `PRICING_FETCH_AGENT_SEED` | `PRICING_AGENT_AGENTVERSE_ADDRESS` |
| DepopListingAgent | `depop_listing_agent` | 9204 | yes | `DEPOP_LISTING_FETCH_AGENT_SEED` | `DEPOP_LISTING_AGENT_AGENTVERSE_ADDRESS` |
| DepopSearchAgent | `depop_search_agent` | 9205 | no | `DEPOP_SEARCH_FETCH_AGENT_SEED` | `DEPOP_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| EbaySearchAgent | `ebay_search_agent` | 9206 | no | `EBAY_SEARCH_FETCH_AGENT_SEED` | `EBAY_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| MercariSearchAgent | `mercari_search_agent` | 9207 | no | `MERCARI_SEARCH_FETCH_AGENT_SEED` | `MERCARI_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| OfferUpSearchAgent | `offerup_search_agent` | 9208 | no | `OFFERUP_SEARCH_FETCH_AGENT_SEED` | `OFFERUP_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| RankingAgent | `ranking_agent` | 9209 | no | `RANKING_FETCH_AGENT_SEED` | `RANKING_AGENT_AGENTVERSE_ADDRESS` |
| NegotiationAgent | `negotiation_agent` | 9210 | no | `NEGOTIATION_FETCH_AGENT_SEED` | `NEGOTIATION_AGENT_AGENTVERSE_ADDRESS` |

**Naming note for judges:** Repo uses **NegotiationAgent**, not “HagglingAgent”; **EbaySoldCompsAgent**, not “EbayResearchAgent”. Update Agentverse handles/keywords accordingly.

---

## Phase A — Local Fetch runtime (blocking)

**Owner:** anyone running the stack.

1. Install main app: `make install` (`.venv`; may be Python 3.14).
2. Ensure **Python 3.12** available as `python3.12` (or set `FETCH_PYTHON` for `venv-fetch`).
3. `make venv-fetch` → creates `.venv-fetch` with **`requirements.txt`** (backend deps + `uagents`, so `backend.fetch_runtime` imports cleanly).
4. Copy [`.env.example`](.env.example) to `.env` if needed; set:
   - `AGENTVERSE_API_KEY`
   - the 4 public-agent seed vars used by `make run-fetch-agents`
   - any additional internal-worker seed vars you plan to launch manually
   - `FETCH_USE_LOCAL_ENDPOINT=false` (mailbox)
5. **Load env in the shell** before Fetch commands (`run_fetch_agents` does not call `load_dotenv`):
   - e.g. `set -a && source .env && set +a`
6. Smoke-test **one** agent:
   - `PYTHONPATH=$PWD .venv-fetch/bin/python -m backend.fetch_agents.launch depop_search_agent`
   - Confirm no `Missing *_FETCH_AGENT_SEED` / import errors.
7. Run **all** agents: `make run-fetch-agents` (same shell with env loaded).

**Exit:** All ten processes healthy; mailbox registration messages in logs.

---

## Phase B — Agentverse registration and address capture (blocking)

**Owner:** Fetch / demo lead.

For **each** row in §2 (or in parallel once comfortable):

1. Keep that agent running (or run all via `make run-fetch-agents`).
2. Open the **Agent inspector** URL from logs (port is **9201–9210**, not 81xx).
3. Connect via **Mailbox** flow per Agentverse UI.
4. In [Agentverse](https://agentverse.ai), confirm agent appears; edit profile (name, handle, keywords, about, optional avatar) — reuse narrative from [`AGENTVERSE_SETUP.md`](AGENTVERSE_SETUP.md) but **names/slugs/ports from §2 above**.
5. Copy `agent1q...` into the matching **address env var** in `.env`.
6. Optional: start FastAPI (`make run`) and verify `GET http://localhost:8000/fetch-agents` reflects addresses.

**Exit:** The 4 public `*_AGENTVERSE_ADDRESS` values are set; profiles are visible and Active where expected. Internal workers are optional and can be registered separately if needed.

---

## Phase C — Documentation alignment (high value, low risk)

**Owner:** docs / whoever edits markdown.

1. **Edit [`AGENTVERSE_SETUP.md`](AGENTVERSE_SETUP.md)** near the top:
   - Replace prerequisites that reference `python run_agents.py`, `agents/vision_agent.py`, ports **8001/8101**, with this repo’s commands and **9201–9210**.
   - Add a pointer to §2 of **this file** for the slug ↔ env var matrix.
   - Replace “EbayResearchAgent” / “HagglingAgent” tables with **EbaySoldCompsAgent** / **NegotiationAgent** where they describe *this* codebase.
2. **Cross-link** from [`FETCH_INTEGRATION.md`](FETCH_INTEGRATION.md) “Validation checklist” to this plan’s Phase A–B.
3. **`IMPLEMENTATION-PLAN.md`** Phase 6.3: mark Agentverse steps as tracked here.

**Exit:** A new teammate can follow `AGENTVERSE_SETUP.md` + this plan without wrong ports or scripts.

---

## Phase D — Optional: published README files on the uAgent (nice-to-have)

**Owner:** backend (Fetch builder).

Today [`backend/fetch_agents/builder.py`](backend/fetch_agents/builder.py) already passes `readme_path` into `Agent()` when a Fetch spec defines one. README content in [`backend/fetch_agents/readmes`](backend/fetch_agents/readmes) helps populate Agent metadata, but the Agentverse dashboard is still the final sponsor-facing source of truth.

**Tasks (choose one):**

- **D1 — Docs-only:** In `AGENTVERSE_SETUP.md`, state explicitly that teams should still polish the Agentverse dashboard text even though public agents already have README-backed metadata.
- **D2 — Code:** Expand README coverage to every public slug, tighten naming/location conventions, and verify the public uAgents still start cleanly on Python 3.12.

**Exit:** Either the manual profile-polish process is clearly documented or README coverage is complete and validated for every public agent.

---

## Phase E — Judging and ASI:One deliverables (blocking for submission)

**Owner:** demo lead.

1. Complete **≥3 interactions** per agent on Agentverse (per [`AGENTVERSE_SETUP.md`](AGENTVERSE_SETUP.md)).
2. Run ASI:One chat scenario; collect **chat session URL**.
3. Collect the **4 public** Agentverse agent profile URLs.
4. Fill the submission matrix (ASI:One URL + 4 public agent URLs); store in team vault / Devpost.

**Exit:** All URLs collected; backup screenshots if live demo risky.

---

## Phase F — Optional: orchestrator via Fetch

**Owner:** integration.

Only if the demo requires FastAPI to route steps through Fetch:

1. Set `FETCH_ENABLED=true` in the environment for `make run`.
2. Run backend + Fetch agents; exercise sell/buy smoke; confirm no regression with `FETCH_ENABLED=false` in CI.

**Exit:** Documented env matrix and a short manual smoke checklist.

---

## 3. Risk register

| Risk | Mitigation |
|------|------------|
| Python 3.14 used for uAgents | Always use `.venv-fetch` / `make run-fetch-agents` |
| `.env` not loaded in shell | `set -a && source .env && set +a` before `make run-fetch-agents` |
| ASI:One does not auto-discover agents | Keywords, interactions, direct `@handle` prompts; screenshots |
| Port in use | `lsof -i :9205` (example); stop stale processes |
| Secret leak | Rotate `AGENTVERSE_API_KEY` and seeds if exposed |

---

## 4. Command cheat sheet

```bash
# One-time
make install
make venv-fetch

# Every session (Fetch)
set -a && source .env && set +a
make run-fetch-agents

# Single agent debug
PYTHONPATH=$PWD .venv-fetch/bin/python -m backend.fetch_agents.launch negotiation_agent

# E2E mailbox client → destination agent (after address known)
.venv-fetch/bin/python scripts/fetch_demo.py --address agent1q... --message "Your prompt"

# Catalog (with make run in another terminal)
curl -s http://localhost:8000/fetch-agents | python -m json.tool
```

---

## 5. Maintenance

When adding or renaming a Fetch agent:

1. Update `FETCH_AGENT_SPECS` in [`backend/fetch_runtime.py`](backend/fetch_runtime.py).
2. Update [`.env.example`](.env.example) and **§2** in this file.
3. Update `AGENT_OUTPUT_MODELS` / registry only if orchestration changes (separate from Agentverse metadata).


# --- ARCHIVED FILE: BROWSER-USE-GAPS.md ---

# Browser Use — Missing Features Implementation Plan

## Important Update: SELL Flow Is Changing

This file originally assumed a mobile-first "listing ready" handoff: Browser Use fills the Depop form, stops before submit, sends a screenshot artifact back to the app, and the user finishes posting from mobile.

That is no longer the target flow for SELL.

### New target behavior

- Browser Use runs on a separate non-mobile device during SELL flows.
- It fills the entire marketplace listing form up to the final submit/post button.
- At the final confirmation point, the system pauses and asks the user whether the populated information is correct.
- If the user confirms `yes`, the Browser Use agent proceeds with the actual submit/post action.
- If the user answers `no`, they can either:
  - abort the listing entirely, or
  - provide free-text correction instructions describing what should change.
- The Browser Use agent must interpret those instructions, edit the listing form accordingly, and return to the same ready-to-submit checkpoint.
- This review/correction loop may repeat until the user confirms submission or aborts.

### What this changes

Several gaps below still describe real deficiencies in the current codebase, but the product target has shifted:

- The stop point is no longer the end state. It is now a checkpoint in a multi-step confirmation loop.
- `draft_created` / mobile deep-link assumptions are no longer the core sell-side handoff.
- The backend now needs explicit pause/resume state for Browser Use listing submission, not just a one-shot "fill form and stop" flow.
- Free-text correction instructions are now part of the backend contract, even if frontend details are handled separately.

Use this file as historical gap context plus current-state notes. The concrete next-step plan for the new flow is in [BROWSER-USE-SELL-CONFIRMATION-PLAN.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-SELL-CONFIRMATION-PLAN.md).

What's planned/documented vs what's actually in the code.

## Current SELL Confirmation Loop Status

Implemented in the backend:

- The sell pipeline now pauses at `ready_for_confirmation`.
- `POST /sell/listing-decision` handles `confirm_submit`, `revise`, and `abort`.
- Session state stores nested `sell_listing_review` metadata.
- The orchestrator emits the review-loop events needed for the backend contract.
- The resume path rehydrates Browser Use from persisted listing output and review metadata instead of keeping a live browser session open.

Still open:

- A deterministic browser-level checkpoint action that is not prompt-only.
- Real screenshot capture for `form_screenshot_b64`.

---

## Gap 1: `form_screenshot_b64` not captured (SELL — critical)

**What the PRD says:** `DepopListingAgent` output includes `form_screenshot_b64: str` — a base64 PNG of the populated Depop form. This is what the mobile app shows on the Listing Ready screen.

**What exists:**
- `BrowserUseListingDraftResult.form_screenshot_url: str | None` — described in the task prompt as "a descriptive artifact string" (i.e., the LLM just makes up a string)
- `DepopListingOutput.form_screenshot_url: str | None` — same problem, not a real screenshot

**What's missing:**
- A real base64 PNG taken after form population
- The `capture_and_stop` custom Browser Use action discussed in PRD — a deterministic `@action` that: takes a full-page screenshot via Playwright, encodes it as base64, returns it, and sets `is_done=True` so the agent stops without submitting

**Files to change:**
- `backend/agents/browser_use_support.py` — add `capture_and_stop` custom action
- `backend/agents/browser_use_marketplaces.py` — update `BrowserUseListingDraftResult` to include `form_screenshot_b64: str | None`; update `build_depop_listing_task()` to instruct agent to use the custom action at form completion
- `backend/schemas.py` — rename `form_screenshot_url` → `form_screenshot_b64` in `DepopListingOutput`
- `backend/agents/depop_listing_agent.py` — pass `form_screenshot_b64` through to output

**Implementation sketch:**
```python
# backend/agents/browser_use_support.py
from browser_use import action

@action("Capture a full-page screenshot and stop. Call this when the form is fully populated.")
async def capture_and_stop(browser: BrowserContext) -> dict:
    page = await browser.get_current_page()
    screenshot_bytes = await page.screenshot(full_page=True)
    b64 = base64.b64encode(screenshot_bytes).decode()
    return {"screenshot_b64": b64, "status": "form_complete"}
```

Then pass `registered_actions=[capture_and_stop]` to the `Agent(...)` call in `run_structured_browser_task`.

---

## Gap 2: `draft_url` never populated (SELL — high, now lower priority)

**What the PRD says:** `DepopListingOutput` includes `draft_url: str | None`. If the agent successfully saves a Depop draft, this is the URL for mobile deep-linking to `depop://selling/drafts`. If not, it's `None` and mobile falls back to `depop://sell`.

**What exists:**
- `draft_status: str | None` — just the string `"ready"` or `"fallback"`, no URL
- No instruction in `build_depop_listing_task()` to save as draft or return a URL

**What's missing:**
- Instruction in the Depop task string to attempt saving as draft before stopping
- `draft_url` field in `BrowserUseListingDraftResult` and `DepopListingOutput`
- Agent returning the Depop draft URL from the browser session

**Files to change:**
- `backend/agents/browser_use_marketplaces.py` — add `draft_url: str | None` to `BrowserUseListingDraftResult`; update `build_depop_listing_task()` to add: "If a 'Save as draft' button is visible, click it and return its URL. Otherwise return draft_url as null."
- `backend/schemas.py` — add `draft_url: str | None = None` to `DepopListingOutput`
- `backend/agents/depop_listing_agent.py` — pass through `draft_url` from browser result

---

## Gap 3: `listing_ready` SSE event not emitted (SELL — critical for old mobile flow, not sufficient for new confirmation flow)

**What the PRD says:** After `depop_listing_agent` completes, a `listing_ready` event fires with `form_screenshot_b64`, `listing_preview`, and `draft_url`. This is the event that triggers the mobile Listing Ready screen.

**What exists:**
- `draft_created` event is emitted by `depop_listing_agent` — but it carries `form_screenshot_url` (fake string) and no `form_screenshot_b64`
- No `listing_ready` event anywhere

**What's missing:**
- Either: rename `draft_created` → `listing_ready` and update its payload, OR emit `listing_ready` as a second event after `agent_completed` fires for the `depop_listing` step
- Payload must include: `form_screenshot_b64`, `listing_preview` (with `title`, `price`, `description`, `condition`, `clean_photo_url`), `draft_url`

**Files to change:**
- `backend/agents/depop_listing_agent.py` — change `draft_created` event type to `listing_ready` and update data payload
- `backend/agents/browser_use_events.py` — no changes needed (event type is a string)
- `CLAUDE.md` — add `listing_ready` to the SSE event contract

---

## Gap 4: `vision_result` and `pricing_result` SSE events not emitted (SELL — high for mobile)

**What the PRD says:**
- After `vision_analysis` step: emit `vision_result` with `{ brand, item_name, model, condition, confidence, clean_photo_url, search_query }`
- After `pricing` step: emit `pricing_result` with `{ recommended_price, profit_margin, median_price, trend, velocity }`

**What exists:**
- Orchestrator emits `agent_completed` for every step (with `output` in the data) — but the frontend/mobile has to dig into `agent_completed.data.output` to find this data
- No dedicated `vision_result` or `pricing_result` events

**What's missing:**
- Two additional `publish()` calls in `orchestrator.py` inside the SELL pipeline step loop: one after `vision_analysis` completes, one after `pricing` completes

**Files to change:**
- `backend/orchestrator.py` — add after each relevant step in `run_pipeline`:

```python
# After vision_analysis step completes:
if pipeline == "sell" and step_name == "vision_analysis":
    await publish(session_id, "vision_result", pipeline="sell", step="vision_analysis", data={
        "brand": validated_output.get("brand"),
        "item_name": validated_output.get("detected_item"),
        "model": validated_output.get("model"),
        "condition": validated_output.get("condition"),
        "confidence": validated_output.get("confidence"),
        "clean_photo_url": validated_output.get("clean_photo_url"),
        "search_query": validated_output.get("search_query"),
    })

# After pricing step completes:
if pipeline == "sell" and step_name == "pricing":
    await publish(session_id, "pricing_result", pipeline="sell", step="pricing", data={
        "recommended_price": validated_output.get("recommended_list_price"),
        "profit_margin": validated_output.get("expected_profit"),
        "median_price": validated_output.get("median_price"),
        "trend": validated_output.get("trend"),
        "velocity": validated_output.get("velocity"),
    })
```

---

## Gap 5: `DepopListingPreview` missing `condition` and `clean_photo_url` (SELL — medium)

**What the PRD says:** `listing_preview` inside `DepopListingOutput` should include `condition: str` and `clean_photo_url: str` so the mobile Listing Ready screen can render the full card.

**What exists:**
```python
class DepopListingPreview(BaseModel):
    title: str
    price: float
    description: str
```

**What's missing:** `condition: str` and `clean_photo_url: str | None`

**Files to change:**
- `backend/schemas.py` — add fields to `DepopListingPreview`
- `backend/agents/depop_listing_agent.py` — populate `condition` from `vision_analysis["condition"]` and `clean_photo_url` from `vision_analysis.get("clean_photo_url")`

---

## Gap 6: Image upload requires local file path — breaks for remote URLs (SELL — medium)

**What exists now:** the listing agent resolves remote image URLs to temp files before handing them to Browser Use, and still falls back to local filesystem paths when they already exist.

**Current status:** implemented in [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py). Remote image upload is no longer a blocking gap for the SELL review loop.

**Remaining caveat:** temp-file cleanup is still best-effort and could be hardened later if live demos begin accumulating artifacts.

**Implementation sketch:**
```python
async def resolve_image_to_local_path(image_urls: list[str]) -> str | None:
    for url in image_urls:
        if url.startswith(("http://", "https://")):
            # Download to temp file
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                if resp.status_code == 200:
                    suffix = ".jpg" if "jpg" in url or "jpeg" in url else ".png"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                        f.write(resp.content)
                        return f.name
        else:
            path = Path(url)
            if path.exists():
                return str(path.resolve())
    return None
```

**Files changed:**
- `backend/agents/depop_listing_agent.py` — async `resolve_image_to_local_path` now downloads remote images before Browser Use upload

---

## Gap 7: `capture_and_stop` not in task string (SELL — high reliability, still required as the ready-to-submit checkpoint)

**What exists:** `build_depop_listing_task()` task string ends with:
> "Stop before the final publish or submit action."

This is LLM-instructed behavior — unreliable. The agent might click submit anyway, or might stop too early.

**What's missing:** A deterministic custom `@action` that the agent is explicitly told to call when the form is ready. This guarantees: screenshot is taken, base64 is returned, and the agent stops without any submit click.

The task string should be updated to:
> "When all form fields are populated and you are ready to submit, call the `capture_and_stop` action instead of clicking submit. Do not click the post or publish button."

This pairs with Gap 1 above.

---

## Gap 8: OfferUp Browser Use (BUY — low, best-effort)

**What exists:** `run_marketplace_search("offerup", query)` with task string navigating to `https://offerup.com/search?q={query}`. OfferUp heavily blocks automated access and requires login for most features.

**What's missing:**
- OfferUp has no reliable httpx path (returns 403 or empty for unauthenticated requests)
- Browser Use fallback likely fails silently
- No logged-in profile warming instructions for OfferUp in the guide

**Recommendation:** Accept fallback as primary for OfferUp. Document in `BrowserUse-Live-Validation.md` that OfferUp is best-effort. Focus demo on Depop/eBay/Mercari.

---

## New SELL Confirmation-Loop Status

| Gap | Severity | What is missing |
|-----|----------|-----------------|
| 9. Review checkpoint state machine | Implemented | The backend now has explicit `ready_for_confirmation`, `submitted`, `aborted`, and paused review metadata. |
| 10. User confirmation endpoint/contract | Implemented | `POST /sell/listing-decision` accepts `confirm_submit`, `revise`, and `abort`. |
| 11. Browser Use resume/edit loop | Partially implemented | The backend rehydrates the listing flow on resume; it does not keep a live browser session open across the pause. |
| 12. Free-text correction handling | Implemented | Revision instructions are accepted and routed through the review loop. |
| 13. Final submit action separation | Implemented at the orchestration layer | Confirmed submission is an explicit gated action. The Browser Use runtime still lacks a deterministic checkpoint action. |
| 14. Confirmation/audit events | Implemented | The SSE layer now exposes the review and submission events needed for the loop. |

## Summary Table

| Gap | Pipeline | Severity | Files |
|-----|----------|----------|-------|
| 1. `form_screenshot_b64` not captured | SELL | Critical | `browser_use_support.py`, `browser_use_marketplaces.py`, `schemas.py`, `depop_listing_agent.py` |
| 2. `draft_url` never populated | SELL | High | `browser_use_marketplaces.py`, `schemas.py`, `depop_listing_agent.py` |
| 3. `listing_ready` event not emitted | SELL | Low relevance now | `depop_listing_agent.py` |
| 4. `vision_result`/`pricing_result` events missing | SELL | Low relevance now | `orchestrator.py` |
| 5. `listing_preview` missing `condition`/`clean_photo_url` | SELL | Medium | `schemas.py`, `depop_listing_agent.py` |
| 6. Remote image URL not downloaded for upload | SELL | Implemented | `depop_listing_agent.py` |
| 7. `capture_and_stop` not in task string | SELL | High (reliability) | `browser_use_support.py`, `browser_use_marketplaces.py` |
| 8. OfferUp Browser Use unreliable | BUY | Low | docs only |
| 9. Review checkpoint state machine | SELL | Implemented | `schemas.py`, `session.py`, `orchestrator.py`, `main.py`, `depop_listing_agent.py` |
| 10. User confirmation endpoint/contract | SELL | Implemented | `schemas.py`, `main.py`, `orchestrator.py` |
| 11. Browser Use resume/edit loop | SELL | Partially implemented | `browser_use_support.py`, `browser_use_marketplaces.py`, `depop_listing_agent.py` |
| 12. Free-text correction handling | SELL | Implemented | `schemas.py`, `main.py`, `orchestrator.py`, `depop_listing_agent.py` |
| 13. Final submit action separation | SELL | Implemented at orchestration layer | `browser_use_support.py`, `browser_use_marketplaces.py`, `depop_listing_agent.py` |
| 14. Confirmation/audit events | SELL | Implemented | `orchestrator.py`, `depop_listing_agent.py`, event docs |

---

## Recommended Implementation Order

1. **Gaps 1 + 7** (`capture_and_stop` + screenshot) — still the highest-value live Browser Use hardening work
2. **Gap 2** (`draft_url`) — useful metadata if the marketplace exposes it reliably
3. **Gap 8** (OfferUp) — document and treat as best-effort


# --- ARCHIVED FILE: BROWSER-USE-SELL-CONFIRMATION-PLAN.md ---

# Browser Use SELL Confirmation Flow Implementation Plan

This document captures the updated sell-side Browser Use flow. It is intentionally backend-focused and does not prescribe frontend implementation details.

## Goal

Change the SELL flow from "populate form and stop" to "populate form, pause for user confirmation, then either submit, abort, or revise and retry."

## Current Implementation Status

The backend review loop is implemented. The current codebase already pauses the sell pipeline at `ready_for_confirmation`, persists nested review metadata on the session, exposes `POST /sell/listing-decision`, and resumes through explicit `confirm_submit`, `revise`, and `abort` decisions.

The browser-context strategy is to rehydrate on resume rather than keep a live browser session open across the review pause. The persisted state is the prepared listing output plus review metadata in session state.

## Target Flow

1. SELL pipeline reaches `depop_listing_agent`.
2. Browser Use opens the logged-in marketplace session on a non-mobile device.
3. It fills the complete listing form, including all fields that would normally be required for submission.
4. It stops immediately before the final submit/post click.
5. The backend marks the listing as `ready_for_confirmation` and emits an event telling the client that user input is required.
6. The user chooses one of three actions:
   - `confirm_submit`
   - `abort`
   - `revise`
7. If the user chooses `confirm_submit`, Browser Use performs only the final submit/post action.
8. If the user chooses `abort`, the backend closes the listing run without submitting.
9. If the user chooses `revise`, the user sends free-text change instructions. Browser Use edits the existing form, returns to the same ready-to-submit checkpoint, and waits again.
10. The loop repeats until the listing is either submitted or aborted.

## Required Backend Changes

### 1. Introduce explicit sell-listing review states

The current sell pipeline does not model the review loop as a state machine. That needs to change first.

Suggested states:

- `filling_form`
- `ready_for_confirmation`
- `awaiting_revision`
- `applying_revision`
- `submitting`
- `submitted`
- `aborted`
- `failed`

Likely files:

- `backend/schemas.py`
- `backend/session.py`
- `backend/orchestrator.py`

### 2. Split "prepare listing" from "submit listing"

The current Browser Use prompt only says to stop before submit. That is not enough for a gated workflow.

The new contract should treat these as separate actions:

- `prepare_listing_for_review`
- `submit_prepared_listing`
- `apply_listing_revision`
- `abort_prepared_listing`

That separation matters because the final submit action must only happen after an explicit user decision.

Likely files:

- `backend/agents/browser_use_support.py`
- `backend/agents/browser_use_marketplaces.py`
- `backend/agents/depop_listing_agent.py`

### 3. Add a user-decision API contract

There is currently no endpoint for continuing a Browser Use listing after a user review.

Add a backend contract for a sell-listing decision payload with:

- `decision`: `confirm_submit | revise | abort`
- `revision_instructions`: optional free text, required when `decision=revise`

Likely files:

- `backend/schemas.py`
- `backend/main.py`
- `backend/orchestrator.py`

### 4. Preserve in-progress Browser Use context across the review loop

The current code path is one-shot. After the Browser Use listing step returns, there is no durable backend notion of:

- which session is paused,
- which platform form is open,
- whether the browser task can resume safely,
- what checkpoint was last reached.

The implementation needs a resumable handoff strategy. That can be done in one of two ways:

Option A: Keep the Browser Use run alive while awaiting user confirmation.

- Best UX and least re-navigation.
- Higher operational risk: longer-lived browser sessions, timeout handling, cleanup complexity.

Option B: Store enough state to reopen the listing page, rehydrate context, and continue from a deterministic checkpoint.

- Operationally safer.
- More engineering work and potentially less reliable if the site changes.

Current implementation: Option B. The backend rehydrates the listing flow on each decision using the saved listing output and review metadata, rather than keeping a browser session alive through the pause.

Likely files:

- `backend/agents/browser_use_support.py`
- `backend/session.py`
- `backend/agents/depop_listing_agent.py`

### 5. Add a deterministic ready-to-submit checkpoint action

The existing gap around `capture_and_stop` remains valid, but its role changes. It is no longer just for a screenshot artifact. It becomes the explicit "pause here for user review" checkpoint.

That action should:

- verify the form is fully populated,
- optionally capture evidence of the current page state,
- mark the task as paused at the final submit boundary,
- return structured data proving the form is ready,
- never click submit.

Likely files:

- `backend/agents/browser_use_support.py`
- `backend/agents/browser_use_marketplaces.py`

### 6. Add free-text revision handling

When the user says something like "change the price to $85 and shorten the description" or "mark the condition as good instead of excellent," the backend must route that instruction back into the listing agent.

The first implementation should keep this narrow:

- single text field from user,
- Browser Use edits the existing form,
- system returns to `ready_for_confirmation`,
- no attempt to build a separate frontend field-by-field editor.

Important guardrails:

- reject empty revision instructions,
- track latest revision text in session state,
- limit revision loop count to avoid infinite retries,
- emit clear failure state if Browser Use cannot apply the revision safely.

Likely files:

- `backend/schemas.py`
- `backend/main.py`
- `backend/orchestrator.py`
- `backend/agents/depop_listing_agent.py`

### 7. Expand SSE events around the review loop

The current events are not expressive enough for this flow.

Add dedicated events for:

- `listing_review_required`
- `listing_revision_requested`
- `listing_revision_applied`
- `listing_submission_approved`
- `listing_submission_aborted`
- `listing_submitted`
- `listing_submission_failed`

These should be emitted in addition to existing generic step events, not as a replacement.

The current implementation already emits the review-loop events needed for the backend contract, including `listing_review_required`, `listing_revision_requested`, `listing_revision_applied`, `listing_submit_requested`, `listing_submitted`, `listing_abort_requested`, and `listing_aborted`.

Likely files:

- `backend/orchestrator.py`
- `backend/agents/depop_listing_agent.py`
- event contract docs

## Suggested Execution Order

### Phase 1: Contracts and state machine

- Define the new review states.
- Define the user-decision schema.
- Define the new SSE event names and payloads.

### Phase 2: Browser Use checkpoint split

- Add the deterministic ready-to-submit action.
- Separate "prepare" from "submit."
- Ensure submit is impossible without an explicit continuation path.

### Phase 3: Pause/resume orchestration

- Persist paused listing-review state in session memory.
- Add the resume endpoint.
- Wire decisions into the orchestrator.

### Phase 4: Revision loop

- Accept free-text revision instructions.
- Apply revisions in the existing open form.
- Return to the ready-for-confirmation checkpoint.

### Phase 5: Hardening

- Add timeout cleanup for abandoned paused sessions.
- Add retry limits and failure events.
- Validate behavior with live warmed profiles.

## Testing Plan

Add tests before live validation.

### Unit / contract tests

- decision schema accepts `confirm_submit`, `revise`, `abort`
- `revise` requires non-empty revision text
- invalid state transitions are rejected

### Orchestrator tests

- sell pipeline pauses at `ready_for_confirmation`
- confirm path resumes and reaches `submitted`
- abort path stops cleanly without submission
- revise path loops back to `ready_for_confirmation`
- timed-out paused sessions clean up correctly

### Agent tests

- Browser Use listing task stops at the deterministic checkpoint
- submit action is never taken during the prepare phase
- revision instructions are routed back into the listing agent

### Live validation

- prepared listing reaches the final submit boundary on the non-mobile device
- `confirm_submit` clicks the real submit/post control
- `revise` updates the already-populated form correctly
- `abort` leaves the listing unpublished

## Out of Scope For This Plan

- frontend popup design or UI implementation
- mobile deep-link behavior
- broad marketplace generalization beyond the current Depop sell flow

## Notes On Existing Docs

The current PRD and related Browser Use notes still emphasize screenshot handoff and mobile review. Those docs should now be treated as partially outdated for SELL. The backend implementation should follow this confirmation-loop design instead.


# --- ARCHIVED FILE: BROWSER-USE-SELL-IMPLEMENTATION-CHECKLIST.md ---

# Browser Use SELL Confirmation Flow Implementation Checklist

This checklist tracks the current backend state for the SELL confirmation loop.

The implemented design is:

1. Browser Use runs on a separate non-mobile device for SELL.
2. It fills the listing form up to the final submit/post boundary.
3. The backend pauses for review at `ready_for_confirmation`.
4. The user can `confirm_submit`, `revise`, or `abort`.
5. The backend rehydrates the listing flow on resume instead of keeping a live browser session open across the pause.

## Current State

- Implemented: review-loop session state, `POST /sell/listing-decision`, pause/resume orchestration, review SSE events, confirm/revise/abort handling, remote image download for listing uploads, and structured Browser Use error categories for the sell review loop.
- Still open: deterministic browser-level checkpointing and real screenshot capture.

## Phase 1: Contracts And Session State

### `backend/schemas.py`

- [x] Add a dedicated sell-listing decision request model next to [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L29).
- [x] Support these decisions:
  - `confirm_submit`
  - `revise`
  - `abort`
- [x] Require non-empty revision text when `decision=revise`.
- [x] Add explicit review-loop state to session data near [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L291).
- [x] Use a dedicated nested `sell_listing_review` object for the review state.
- [x] Add fields for paused listing-review metadata:
  - current review state
  - current step name
  - platform name
  - latest user decision
  - latest revision instructions
  - revision count
  - paused timestamp
  - optional timeout/deadline
- [x] Extend [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L165) `DepopListingOutput` so it can represent the new checkpoint-oriented flow.
- [ ] Replace or de-emphasize old mobile-oriented fields if they are no longer primary:
  - `draft_status`
  - `form_screenshot_url`
- [x] Add review-checkpoint fields as needed:
  - `listing_status`
  - `ready_for_confirmation`

### `backend/session.py`

- [x] Extend the session manager to persist the new review-loop state added in [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L291).
- [x] Confirm `update_status()` in [backend/session.py](/Users/jt/Desktop/diamondhacks/backend/session.py#L35) can update partial review metadata without clobbering unrelated result data.
- [x] Add helper methods if needed for:
  - marking a session as awaiting listing confirmation
  - storing latest revision instructions
  - clearing paused review state after submit or abort
- [ ] Decide where timeout cleanup metadata should live for abandoned paused sessions.

## Phase 2: API Endpoints

### `backend/main.py`

- [x] Keep [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py#L97) `POST /sell/correct` unchanged for the vision-confidence flow.
- [x] Add a new sell-listing decision endpoint next to it in [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py#L97).
- [x] Route the new endpoint into orchestrator logic instead of putting decision logic directly in the HTTP handler.
- [x] Validate these cases:
  - session exists
  - session belongs to `sell`
  - session is actually waiting on listing confirmation
  - `revise` includes text
- [x] Return an explicit accepted payload with the queued action, decision, session status, and review state.
- [x] Do not modify SSE transport in [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py#L140); it already supports paused sessions.

## Phase 3: Orchestrator Pause/Resume Logic

### `backend/orchestrator.py`

- [x] Reuse the existing pause/resume pattern from [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L20) and [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L308).
- [x] Add a second pause reason for the Depop listing review checkpoint.
- [x] Use a dedicated listing-review pause exception rather than overloading `LowConfidencePause`.
- [x] After the `depop_listing` step in [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L232), detect when the output means "ready for confirmation" and pause instead of completing the pipeline.
- [x] Persist partial outputs before pausing, as already done in [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L256).
- [x] Emit a dedicated SSE event for the new pause state.
- [x] Add an orchestrator entrypoint to handle user listing decisions:
  - confirm submit
  - revise
  - abort
- [x] Reuse the old sell resume path only where it still reads clearly; the review loop uses a separate handler.
- [x] Ensure confirm/abort/revise decisions are rejected if the session is not paused at the correct step.
- [x] Keep the sell step list in [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L23) unchanged.

## Phase 4: Browser Use Runtime Refactor

### `backend/agents/browser_use_support.py`

- [ ] Refactor [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py#L129) so the listing flow is not only a one-shot `run_structured_browser_task()`.
- [x] Separate the current combined flow into explicit operations:
  - prepare listing for review
  - apply listing revision
  - submit prepared listing
  - abort prepared listing
- [ ] Introduce a deterministic ready-to-submit checkpoint action instead of relying on prompt text alone.
- [ ] Ensure the checkpoint action never clicks submit.
- [x] Decide how to preserve browser context across the review pause:
  - keep Browser Use alive, or
  - rebuild context on resume
- [ ] If keeping the session alive:
  - do not immediately stop the browser session in `finally` as currently done in [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py#L175)
  - add cleanup guarantees for timeout/abort/failure
- [x] If rebuilding context:
  - define exactly what state must be persisted to resume safely
  - make the resume flow deterministic enough for live demo use
- [x] Add structured error categories for:
  - review checkpoint failure
  - revision application failure
  - submit failure
  - abort cleanup failure

### `backend/agents/browser_use_marketplaces.py`

- [x] Replace [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py#L27) `BrowserUseListingDraftResult` with a checkpoint-oriented output model.
- [x] Update [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py#L91) `build_depop_listing_task()` to instruct the agent to:
  - fill all required fields
  - stop only at the deterministic ready-for-review checkpoint
  - never click submit during the prepare phase
- [x] Add separate task builders or structured instructions for:
  - apply revision
  - submit listing
  - abort listing
- [x] Keep prompt wording narrow and operational. Do not rely on vague “stop before submit” phrasing.

## Phase 5: Depop Listing Agent Changes

### `backend/agents/depop_listing_agent.py`

- [x] Replace the current one-pass draft preparation flow in [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L71) with the new checkpoint flow at the agent level.
- [x] Split the current behavior into explicit agent-level operations:
  - prepare listing
  - apply user revision
  - submit listing
  - abort listing
- [x] Update the output built in [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L79) to describe checkpoint readiness instead of only `draft_status`.
- [ ] Replace the old `draft_created` event emitted at [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L117) with new confirmation-loop events.
- [x] Preserve useful derived fields already created here:
  - title
  - description
  - suggested price
  - category path
  - listing preview
- [x] Keep image resolution/download in the listing agent for now, and make it compatible with the new review loop.

## Phase 6: SSE Event Contract

### `backend/orchestrator.py` and `backend/agents/browser_use_events.py`

- [x] Keep using [backend/agents/browser_use_events.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_events.py#L11) for event emission.
- [x] Add dedicated event names for the new flow:
  - `listing_review_required`
  - `listing_revision_requested`
  - `listing_revision_applied`
  - `listing_submit_requested`
  - `listing_submitted`
  - `listing_abort_requested`
  - `listing_aborted`
- [x] Decide which of those events originate from orchestrator versus `depop_listing_agent`.
- [x] Keep existing generic events such as `agent_started`, `agent_completed`, and `pipeline_complete` unless they create ambiguity.
- [x] Make the pause event payload include enough data for review:
  - title
  - price
  - description
  - category path
  - condition if available
  - optional screenshot/proof artifact
  - session review state

## Phase 7: Result Semantics

### Session result payload

- [x] Decide what `GET /result/{session_id}` should show while waiting for confirmation.
- [x] Ensure [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py#L110) can return a session result that clearly distinguishes:
  - running normally
  - paused for vision correction
  - paused for listing confirmation
  - submitted
  - aborted
- [x] Keep partial outputs visible while paused so the client can render the latest listing state.

## Phase 8: Tests

### New or updated tests

- [x] Add contract tests for the new listing-decision request model in `tests/`.
- [x] Mirror the structure of [tests/test_sell_correct_endpoint.py](/Users/jt/Desktop/diamondhacks/tests/test_sell_correct_endpoint.py#L16) for the new confirmation-loop endpoint.
- [x] Add orchestrator tests for:
  - pause at listing review checkpoint
  - confirm path resumes and completes
  - abort path stops without submit
  - revise path loops back to review checkpoint
  - invalid decisions are rejected when not paused
- [x] Add agent-level tests for:
  - prepare flow never submits
  - submit flow only performs final gated action
  - revision text is routed back into the listing flow
- [x] Add session-state tests for:
  - paused review metadata is persisted
  - pause state is cleared after completion or abort
  - timeout cleanup works if implemented
- [x] Update any tests that currently assume `draft_created` is the sell-side terminal event.

## Phase 9: Docs To Update After Implementation

- [x] Update [BROWSER-USE-GAPS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-GAPS.md#L1) to mark the new flow as implemented.
- [x] Update [BROWSER-USE-SELL-CONFIRMATION-PLAN.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-SELL-CONFIRMATION-PLAN.md#L1) with any design decisions made during implementation.
- [x] Update [BrowserUse-Live-Validation.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Live-Validation.md#L1) to validate:
  - prepare-to-review checkpoint
  - confirm submit path
  - revise path
  - abort path
- [x] Update any older docs that still describe SELL as a mobile screenshot handoff if that is no longer accurate.

## Open Design Decision

- [x] Will the Browser Use session stay alive while the backend waits for user confirmation, or will the system reconstruct the state on resume?

Implemented decision: the backend reconstructs Browser Use state on resume from the persisted listing output and review metadata. It does not keep a live browser session open across the pause.


# --- ARCHIVED FILE: BROWSER-USE-STATUS.md ---

# Browser Use Status

## What Was Fixed

Five bugs were blocking browser_use from running in the server process.

### Bug 1 — `.env` never loaded at server startup
**File:** `backend/main.py`

`make run` → `./start.sh` → `uvicorn` — none of these source `.env`. The server
process had no `GOOGLE_API_KEY`, so `browser_use_runtime_ready()` returned `False`
immediately and every agent fell back silently.

**Fix:** Added `from dotenv import load_dotenv; load_dotenv()` at the top of
`backend/main.py`. `python-dotenv` was already in `requirements.txt` — it just
wasn't being called.

---

### Bug 2 — Wrong LLM class (`langchain_google_genai` vs `browser_use` native)
**File:** `backend/agents/browser_use_support.py`

`import_browser_use_dependencies()` imported `ChatGoogleGenerativeAI` from
`langchain_google_genai`. `browser_use 0.12.6` expects `llm.provider` to exist on
the LLM object; `langchain_google_genai 4.2.1` does not expose this attribute.

Error: `AttributeError: 'ChatGoogleGenerativeAI' object has no attribute 'provider'`

**Fix:** Switched to `browser_use`'s own Google wrapper:
```python
from browser_use.llm.google.chat import ChatGoogle
```
This class has `provider = "google"` as a property.

---

### Bug 3 — `ChatGoogle` does not auto-read `GOOGLE_API_KEY` from env
**File:** `backend/agents/browser_use_support.py`

Unlike `langchain_google_genai`, `ChatGoogle` requires the key to be passed
explicitly. Without it, all Gemini API calls silently fail.

**Fix:** Pass `api_key=os.getenv("GOOGLE_API_KEY")` when constructing the LLM:
```python
llm = ChatGoogle(model=get_browser_use_model(), api_key=os.getenv("GOOGLE_API_KEY"))
```

---

### Bug 4 — `AgentHistoryList.final_result()` API changed in browser_use 0.12.6
**File:** `backend/agents/browser_use_support.py`

The code called `history.final_result(output_model)` but the method now takes no
arguments and returns a JSON string, not a model instance.

Error: `TypeError: AgentHistoryList.final_result() takes 1 positional argument but 2 were given`

**Fix:**
```python
result = history.final_result()           # no argument
if isinstance(result, str):
    result = json.loads(result)           # parse JSON string → dict
return output_model.model_validate(result).model_dump()
```

---

### Bug 5 — `gemini-2.0-flash` deprecated for new API keys; timeout too short
**Files:** `.env`, `backend/agents/browser_use_support.py`

- `gemini-2.0-flash` and `gemini-2.0-flash-001` return HTTP 404 for new API keys:
  `"This model is no longer available to new users."`
- `AGENT_TIMEOUT_SECONDS=30` timed out every browser_use run before it could
  finish — the pipeline completed but all agents showed `category: timeout` in SSE
  events, and fell back to mock data.

**Fix:**
- `.env`: `BROWSER_USE_GEMINI_MODEL=gemini-2.5-flash` (confirmed working)
- `.env`: `AGENT_TIMEOUT_SECONDS=180`
- `browser_use_support.py`: Default fallback model updated from `gemini-2.0-flash`
  to `gemini-2.5-flash`

---

## Current State

| Check | Status |
|---|---|
| `browser_use_runtime_ready()` returns `True` in server process | ✅ |
| `ChatGoogle` constructs with correct `provider` and `api_key` | ✅ |
| Chromium launches when pipeline runs | ✅ |
| `final_result()` parses without error | ✅ |
| `gemini-2.5-flash` responds to API calls | ✅ |
| Server loads `.env` on startup without manual `source` | ✅ |
| Search agents report `execution_mode=browser_use` | ✅ (pipeline reaches browser_use) |
| Search agents return actual listings | ⚠️ returning 0 results (see below) |

---

## What Still Needs Testing

### 1. ~~Profiles not wired up for search agents~~ ✅ Fixed

`run_marketplace_search()` now imports `get_browser_profile_path` and passes
`user_data_dir=get_browser_profile_path(platform)` to `run_structured_browser_task()`.
Logged-in profiles under `profiles/depop`, `profiles/ebay`, `profiles/mercari` are
now used. `profiles/offerup` directory created (empty — no login session, but
patchright won't error on missing dir).

**To verify:** Restart server and re-run buy pipeline. Check `results` count > 0 in
the SSE `agent_completed` events for at least depop/mercari.

### 2. Sell pipeline browser_use (depop listing agent)

The `depop_listing_agent` does pass `user_data_dir` to `run_structured_browser_task`.
It has not been tested since the fixes were applied. Run:
```bash
curl -s -X POST http://localhost:8000/sell/start \
  -H "Content-Type: application/json" \
  -d '{"input":{"image_url":"https://images.depop.com/sample.jpg","item_description":"vintage levi jacket"}}' \
  | python3 -m json.tool
```
Then poll `/result/<session_id>` and check `depop_listing.listing_status` and
`depop_listing.execution_mode`.

### 3. eBay sold comps agent

Uses browser_use to scrape eBay sold listings (sell pipeline step 2). Has not been
tested. Same concern as above — verify it reaches `execution_mode=browser_use` and
returns real comps, not fallback.

### 4. OfferUp search — no profile exists

`profiles/offerup` was never created (skipped during profile setup). The offerup
search agent will launch an anonymous session. Either:
- Create the profile: `python scripts/create_browser_profile.py --platform offerup`
- Or accept fallback for offerup and document it as a known gap

### 5. eBay search — placeholder API keys

`EBAY_APP_ID=your_ebay_app_id_here` is a placeholder, so the httpx path fails
immediately and the agent must fall back to browser_use. This should now work after
the fixes but has not been confirmed with a real run.

### 6. Negotiation agent profile paths

`negotiation_agent.py` passes `user_data_dir` using the platform name as the profile
key. Verify the profile directory names match what the agent expects.

### 7. Run `make verify-browser` after all fixes

```bash
make verify-browser
```
The audit should now pass all checks given the model and env var changes. Confirm
there are no remaining `fail` entries.

### 8. L5 — Fetch.ai end-to-end

**Setup complete:**
- Python 3.12 venv at `.venv312/` with uagents installed
- `RESALE_COPILOT_FETCH_AGENT_SEED=resale-copilot-fetch-agent-seed` added to `.env`
- ResaleCopilotAgent address: `agent1qf5jz5x85m3u7agf6u6pv9knu8wkpfjl4udvq0nru636juwqllasctl580k`
- `RESALE_COPILOT_AGENT_AGENTVERSE_ADDRESS` added to `.env`

**To run and get deliverable URLs (requires manual steps):**

1. Start the backend server first:
   ```bash
   make run
   ```

2. In a second terminal, launch the resale copilot agent with Python 3.12:
   ```bash
   set -a && source .env && set +a
   .venv312/bin/python -m backend.fetch_agents.launch resale_copilot_agent
   ```
   Wait for it to log its address and confirm mailbox connection to Agentverse.

3. Go to https://agentverse.ai and find the agent by address:
   `agent1qf5jz5x85m3u7agf6u6pv9knu8wkpfjl4udvq0nru636juwqllasctl580k`
   → Copy the profile URL: `https://agentverse.ai/agents/details/<address>/profile`

4. Go to https://asi1.ai (ASI:One), chat with the agent:
   - Send: "Help me flip a vintage Nike tee I found at a thrift store"
   - After it responds, share the chat session → copy the share URL

5. Save both URLs as Fetch.ai deliverables on Devpost.


# --- ARCHIVED FILE: CLAUDE-CODEX-NO-OVERLAP-PLAN.md ---

# Claude + Codex No-Overlap Plan

Date: 2026-04-04

## Purpose

This file defines a clean division of labor between Claude and Codex so both can work in parallel without colliding on the same files, validation steps, or sponsor-critical workstreams.

The immediate objective is to maximize sponsor-track readiness for:

- Best Use of Browser Use
- Best Use of Fetch.ai

## Current Situation

Claude has already identified the most prize-critical remaining work:

- `ebay_sold_comps_agent` still needs the eBay browser profile wired in
- the sell pipeline needs a real post-fix live run
- Fetch agent registration and ASI:One deliverables still require manual completion

Those are tightly coupled tasks. They should stay with one owner.

## Ownership Decision

Claude owns the Browser Use prize-critical path end to end.

Codex avoids those files and focuses on non-overlapping support work:

- submission docs
- sponsor-story consistency
- deliverables packaging
- optional Fetch metadata polish only if it does not interfere with Claude’s live registration/testing work

## Claude-Owned Scope

Claude owns these tasks:

1. Wire eBay profile usage into `ebay_sold_comps_agent`.
2. Run regression tests for that change.
3. Run the live sell pipeline end to end.
4. Confirm Browser Use is actually used in the sell flow:
   - `ebay_sold_comps`
   - `depop_listing`
5. Run Fetch registration/manual verification.
6. Capture final sponsor deliverables:
   - Agentverse profile URL(s)
   - ASI:One shared chat URL

Claude-owned files:

- [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py)
- any tests Claude adds for that agent
- `.env` if needed for live validation
- any live-run notes directly tied to Browser Use validation or Fetch registration

Claude should also be treated as the owner of the live validation path for these files while testing is in progress:

- [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
- [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
- [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)

Even if Claude is not editing all of them immediately, they are too close to the live Browser Use path to risk parallel edits.

## Codex-Owned Scope

Codex should avoid the live Browser Use execution files above and instead own support work that does not block Claude.

### 1. Docs and submission packaging

Codex-owned docs:

- [FETCH-BROWSER-USE-TRACK-AUDIT.md](/Users/jt/Desktop/diamondhacks/FETCH-BROWSER-USE-TRACK-AUDIT.md)
- [docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md](/Users/jt/Desktop/diamondhacks/docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md)
- [README.md](/Users/jt/Desktop/diamondhacks/README.md)
- [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md)
- [FETCH_INTEGRATION.md](/Users/jt/Desktop/diamondhacks/FETCH_INTEGRATION.md)
- [BrowserUse-Live-Validation.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Live-Validation.md)

Goals:

- remove story drift between “4 public agents” and “10 agents”
- align docs with the actual public Fetch surface
- prepare a clean final sponsor-facing submission checklist
- update templates once Claude provides final URLs

### 2. Fetch narrative and public surface cleanup

Codex may touch these only if Claude is not editing them for live registration work:

- [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py)
- [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py)
- [backend/fetch_agents/readmes](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/readmes)

Goals:

- improve capability reporting
- keep the public-agent lineup explicit
- tighten the sponsor narrative around specialized public agents

Codex should not touch launch or mailbox registration flow while Claude is actively using it.

### 3. Optional backend improvements outside Claude’s path

Only after confirming no conflict, Codex can work on lower-risk backlog items such as:

- [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py)
- [backend/agents/search_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/search_support.py)
- [backend/agents/vision_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/vision_agent.py)

These are lower priority than sponsor-proof work and should not distract from the main path.

## Do-Not-Touch List For Codex

Until Claude finishes the live Browser Use and Fetch registration path, Codex should not edit:

- [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py)
- [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
- [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
- [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)
- `.env`
- any manual runbook Claude is actively using for live validation

If a task requires one of those files, assume Claude owns it unless explicitly handed off.

## Recommended Work Sequence

### Phase 1: Claude lands the live-path code fix

Claude:

1. Update [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py) to use the eBay profile.
2. Run focused regression tests.
3. Commit that slice.

Codex:

1. Do not touch Browser Use runtime files.
2. Start doc cleanup and deliverables packaging.

### Phase 2: Claude validates the live Browser Use path

Claude:

1. Run the sell pipeline manually.
2. Confirm:
   - `ebay_sold_comps` uses `execution_mode=browser_use`
   - `depop_listing` uses `execution_mode=browser_use`
3. Capture notes/screenshots/log evidence.

Codex:

1. Keep working on docs and sponsor-story consistency.
2. Do not change the live validation path while Claude is rehearsing it.

### Phase 3: Claude completes Fetch ops work

Claude:

1. Launch the public Fetch agent(s).
2. Register and verify on Agentverse.
3. Run ASI:One interaction.
4. Capture:
   - Agentverse profile URL(s)
   - ASI:One shared chat URL

Codex:

1. Prepare final docs/templates to receive these URLs.
2. Avoid changing registration flow or launch behavior.

### Phase 4: Codex finalizes sponsor-facing docs

Once Claude provides the final URLs and confirms the live runs:

Codex:

1. Update the deliverables template.
2. Update sponsor-facing docs with the final public-agent lineup.
3. Fold in the real proof links and validation notes.
4. Make one final consistency pass across Browser Use and Fetch docs.

## Merge Order

Recommended merge order to minimize conflicts:

1. Claude lands the eBay sold comps profile fix and its tests.
2. Claude completes the live Browser Use sell validation.
3. Claude captures Fetch deliverable URLs.
4. Codex updates docs/templates with the final URLs and aligned sponsor narrative.
5. One final pass checks all sponsor-facing docs for consistency.

## Coordination Rules

1. Before each commit, state the exact file list being touched.
2. No one edits a file the other person is actively using for live testing.
3. If a change touches Browser Use runtime files, assume Claude owns it.
4. If a change only affects docs/templates/audit packaging, assume Codex owns it.
5. Treat Agentverse URLs and ASI:One URL capture as Claude-owned source-of-truth inputs for final docs.

## Final Working Split

Claude:

- Browser Use live proof
- eBay profile fix
- sell-flow validation
- Fetch registration
- ASI:One proof links

Codex:

- submission docs
- audit consolidation
- deliverables template cleanup
- sponsor-story consistency
- optional Fetch metadata polish if it does not touch Claude’s live path

## Success Condition

This plan is working if:

- Claude can complete live Browser Use and Fetch ops work without merge conflicts
- Codex can improve submission readiness in parallel
- the final sponsor-facing docs reflect the real, validated state of the system


# --- ARCHIVED FILE: DerrekPlan.md ---

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



# --- ARCHIVED FILE: FETCH-AGENT-SPECIALIZATION-IMPLEMENTATION-PLAN.md ---

# Fetch Agent Specialization Implementation Plan

## Target State

The end state should be a real Agentverse-facing system, not ten thin wrappers over local functions. The public surface should feel like a set of specialized agents that ASI:One can discover and route intelligently, while the existing backend agents remain the execution layer. Today the main gaps are the generic chat wrapper in [backend/fetch_agents/builder.py](backend/fetch_agents/builder.py), the transport-oriented fetch runtime in [backend/fetch_runtime.py](backend/fetch_runtime.py), and the lack of agent-specific Agentverse metadata or README assets.

Fetch's docs and hackathon materials push toward discoverable, customized, domain-expert agents with strong metadata, README quality, Chat Protocol support, and ASI:One usability:

- Agent setup/discovery: <https://docs.agentverse.ai/documentation/agent-discovery/agent-setup-guide>
- README guidance: <https://docs.agentverse.ai/documentation/agent-discovery/readme-guidelines>
- Evaluation/ranking signals: <https://docs.agentverse.ai/documentation/agent-discovery/agent-evaluations>
- Chat Protocol: <https://docs.agentverse.ai/documentation/getting-started/enable-chat-protocol>
- Hackathon expectations: <https://www.fetch.ai/events/hackathons/la-hacks-2026/hackpack>

## Implementation Plan

1. Define the public agent topology.

   Decide that only 4-5 agents are public on Agentverse: `resale_copilot_agent`, `vision_agent`, `pricing_agent`, `market_search_agent` or the marketplace-specific search agents, and `depop_listing_agent`. Keep `ranking_agent` and `negotiation_agent` as backend workers unless they become independently useful to ASI:One users. The public topology should map to user intents, not internal pipeline steps.

2. Introduce a Fetch-specific agent specification model.

   Expand `FetchAgentSpec` in [backend/fetch_runtime.py](backend/fetch_runtime.py) to include `persona`, `capabilities`, `example_prompts`, `input_contract`, `output_contract`, `tags`, `readme_path`, and `is_public`. This becomes the single source of truth for both runtime behavior and Agentverse presentation.

3. Split transport from specialization in the fetch builder.

   Refactor [backend/fetch_agents/builder.py](backend/fetch_agents/builder.py) so it no longer acts as a generic "pass text through" shim. Add per-agent chat handlers that:

   - classify the user's intent
   - validate whether the request is in-scope for that agent
   - ask for missing required inputs in a deterministic way
   - construct structured execution input
   - format the output in a role-specific way

   The builder should still share common chat-plumbing code, but not a single generic behavioral path.

4. Add an agent-specific natural-language contract for each public agent.

   Create a small module such as `backend/fetch_agents/chat_profiles.py` and optionally `backend/fetch_agents/intent_parsing.py`. Each profile should define:

   - scope
   - accepted intents
   - rejected intents
   - required fields
   - clarification prompts
   - response style
   - escalation or handoff rules

   Example: `vision_agent` should accept item-identification requests and reject pricing or negotiation-only prompts. `pricing_agent` should expect either raw item description or prior `vision_analysis` data. `depop_listing_agent` should clearly distinguish draft creation, revision, submit, and abort.

5. Create a public orchestrator agent for hackathon/demo use.

   Add `resale_copilot_agent` as the primary Agentverse-discoverable entrypoint. Its job is to interpret broad user requests like "help me flip this item" or "find the best place to buy this under $80," then route to the existing backend flow. This agent should expose a coherent expert persona and hide internal pipeline complexity.

6. Add real Agentverse-facing README assets.

   Create one README per public agent under a directory like `backend/fetch_agents/readmes/`. Each README should include:

   - one-line specialization
   - concrete use cases
   - example prompts ASI:One users might issue
   - input requirements
   - output examples
   - limitations
   - why this agent is different from the others

   These are important because Fetch explicitly uses README and metadata as discovery signals.

7. Attach README and metadata during agent construction.

   Update the uAgents construction path in [backend/fetch_agents/builder.py](backend/fetch_agents/builder.py) to include the agent README and any supported manifest metadata fields exposed by the runtime. If the local uAgents version supports `readme_path`, `metadata`, `avatar`, or Agentverse-oriented parameters, wire them in now. If a field is unsupported, capture it as a version-dependent follow-up and document the constraint.

8. Rework fetch runtime around explicit task families.

   Refactor [backend/fetch_runtime.py](backend/fetch_runtime.py) so it stops treating all user text as one opaque string. Add explicit task families:

   - `sell_identify`
   - `sell_price`
   - `sell_list`
   - `buy_search`
   - `buy_rank`
   - `buy_negotiate`
   - `resale_copilot`

   The runtime should map chat intents into these task families before invoking local backend agents.

9. Add structured handoff behavior between public agents.

   Public agents should not just fail out-of-scope requests. They should return a precise handoff recommendation. Example: `vision_agent` should say "this looks like a pricing request; ask `pricing_agent` or the `resale_copilot_agent`." If supported, include exact discoverable agent names or handles in the response.

10. Improve marketplace specialization instead of generic search wrappers.

    The marketplace search agents in [backend/agents/depop_search_agent.py](backend/agents/depop_search_agent.py), [backend/agents/ebay_search_agent.py](backend/agents/ebay_search_agent.py), [backend/agents/mercari_search_agent.py](backend/agents/mercari_search_agent.py), and [backend/agents/offerup_search_agent.py](backend/agents/offerup_search_agent.py) already differ operationally. Make that visible at the Fetch layer by encoding platform-specific expertise, trust boundaries, and examples into metadata and chat behavior rather than exposing them as nearly identical transport endpoints.

11. Make `depop_listing_agent` a strong hackathon showcase agent.

    This is one of the best candidates for a customized Agentverse demo because it has concrete Browser Use integration and user-visible results in [backend/agents/depop_listing_agent.py](backend/agents/depop_listing_agent.py). Make its Fetch-facing behavior explicitly about:

    - creating drafts
    - revising drafts
    - pausing for review
    - publishing after confirmation

    This should read like a real listing assistant, not an internal workflow node.

12. Make the orchestrator capable of progressive clarification.

    For public chat UX, implement missing-input clarification before execution. Example:

    - no image or description for `vision_agent`
    - no budget for buy search
    - no listing URL for negotiation
    - no Depop account or profile status for live listing actions

    This makes the agents feel interactive and customized instead of brittle.

13. Add source-aware formatting and explainability.

    Public responses should include concise rationale in domain language. Example:

    - `pricing_agent`: "priced from sold comps, condition multiplier, and estimated fees"
    - `ranking_agent` or orchestrator: "ranked on price fit, condition, seller credibility, and recency"
    - `depop_listing_agent`: "draft prepared and paused before submit"

    That maps better to ASI:One and hackathon demos than raw JSON dumps.

14. Preserve the current backend contracts and treat Fetch as an adaptation layer.

    Do not rewrite the local backend agents first. Keep [backend/agents/base.py](backend/agents/base.py) and the current agent execution contracts stable. The specialization work should happen at the Fetch specification, metadata, chat intent, and orchestration boundary so the Agentverse posture improves without destabilizing the core app.

15. Add a capability registry endpoint for verification.

    Expose a local diagnostic path that lists every Fetch-facing agent with `is_public`, capabilities, sample prompts, README path, and runtime health. This makes it easy to verify that the Agentverse-facing layer is coherent before demoing.

16. Add tests for specialized behavior, not just process launch.

    Extend [tests/test_fetch_agent_builder_and_runner.py](tests/test_fetch_agent_builder_and_runner.py) with tests that verify:

    - each public agent has non-empty specialization metadata
    - each public agent has a README path
    - out-of-scope requests are rejected or handed off correctly
    - missing-input clarification is deterministic
    - role-specific formatting is used instead of the generic response path
    - `resale_copilot_agent` maps broad prompts to the correct task family

    Add additional tests for the new intent parser and chat profiles.

17. Add content quality tests for the README and discovery layer.

    Write tests that ensure every public agent README contains:

    - description
    - example prompts
    - limitations
    - input requirements
    - output summary

    This directly supports Fetch's discovery and ranking guidance and prevents regressions in hackathon polish.

18. Add a demo script for hackathon judging.

    Create a simple script and doc flow that:

    - launches the public Fetch agents
    - prints their handles and ports
    - demonstrates 3-5 exemplar prompts
    - shows what should be asked through ASI:One

    This should become the judge path.

19. Update docs to reflect the public/private split.

    Revise [backend/README.md](backend/README.md) and [README.md](README.md) so they explain:

    - which agents are Agentverse-facing
    - which agents are internal workers
    - how ASI:One should interact with the system
    - what makes each public agent specialized

    Without this, the code may improve while the project story remains weak.

20. Roll out in three passes.

    Pass 1: spec model, README assets, public/private split, and `resale_copilot_agent`.

    Pass 2: specialized chat handlers, intent parsing, handoffs, and output formatting.

    Pass 3: tests, docs, demo script, and polish for Agentverse submission.

## Acceptance Criteria

The implementation is done when:

- every public agent has unique metadata, README content, example prompts, and a clear specialization
- the fetch builder no longer relies on one generic chat behavior for all agents
- `resale_copilot_agent` exists and routes broad user requests cleanly
- public responses are domain-specific and explainable, not raw JSON-only dumps
- out-of-scope and missing-input behavior is deterministic and tested
- docs clearly tell a Fetch/ASI:One story suitable for a hackathon demo

## Recommended First PR

Start with the structural PR, not the full behavior rewrite:

- expand `FetchAgentSpec`
- add public/private agent designation
- add per-agent README assets
- add `resale_copilot_agent`
- refactor `builder.py` so specialization hooks exist even if behavior is initially simple
- add tests enforcing metadata and README completeness

That first PR gives the biggest hackathon credibility jump with the least execution risk. After that, the agent-specific chat specialization becomes an incremental series of improvements instead of a disruptive rewrite.


# --- ARCHIVED FILE: FETCH-BROWSER-USE-COMPATIBILITY-PLAN.md ---

# Fetch + Browser Use Compatibility Plan

## Goal

Keep the product-facing FastAPI backend and the parallel Fetch adapter path behaviorally aligned while Browser Use remains the marketplace execution layer.

## Completed

- Fixed brittle BUY tests that drifted with relative dates and ranking math updates.
- Routed `FETCH_ENABLED=true` orchestration through the Fetch adapter with structured `AgentTaskRequest` inputs.
- Preserved real pipeline `session_id` and `context` when Fetch-backed steps execute, so Browser Use events still attach to the active FastAPI session.
- Added end-to-end compatibility coverage for:
  - SELL with `BROWSER_USE_FORCE_FALLBACK=true`
  - BUY with `BROWSER_USE_FORCE_FALLBACK=true`
  - local SELL review loop with revise then confirm
  - BUY with `FETCH_ENABLED=true` and `BROWSER_USE_FORCE_FALLBACK=true`
- Updated the Makefile so `make run-fetch-agents` uses the dedicated `.venv-fetch` virtualenv instead of the main `.venv`.
- Documented port and virtualenv coexistence for `make run`, `make run-agents`, and `make run-fetch-agents`.

## Verified

- Focused compatibility suite covering Browser Use fallback, Fetch routing, and project scaffold expectations
- Broader pipeline and event suite covering main FastAPI flows, Browser Use progress events, and Fetch runtime behavior

## Remaining

- Live Browser Use validation on real logged-in marketplace profiles
- Agentverse / mailbox verification for the Fetch agents in a real networked environment
- Real browser-level checkpoint hardening for the SELL review boundary
- Timeout and cleanup hardening for abandoned paused SELL review sessions


# --- ARCHIVED FILE: FETCH-BROWSER-USE-TEST-SUITES.md ---

# Fetch + Browser Use Test Suites

This file lists the current Fetch.ai and Browser Use backend test coverage, with emphasis on the suites that validate the integration seams rather than just the pure Python fallback logic.

## How To Run

Targeted verification:

```bash
./.venv/bin/python -m pytest -q \
  tests/test_fetch_agent_builder_and_runner.py \
  tests/test_fetch_runtime_additional.py \
  tests/test_fetch_runtime.py \
  tests/test_browser_use_marketplaces_contracts.py \
  tests/test_browser_use_sell_checkpoint_additional.py \
  tests/test_browser_use_runtime.py \
  tests/test_browser_use_support_additional.py \
  tests/test_depop_listing_agent_real.py
```

Result from the latest local run:

- `38 passed`
- `1 xfailed`

The single xfail is intentional. It documents a known Fetch BUY-bridge bug without breaking the suite.

## Fetch Test Suites

### New

- [tests/test_fetch_agent_builder_and_runner.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_agent_builder_and_runner.py)
  - Covers `build_fetch_agent()` seed validation
  - Verifies mailbox and `publish_agent_details` wiring
  - Verifies optional `FETCH_USE_LOCAL_ENDPOINT` behavior
  - Tests the chat-handler path: acknowledgement, runtime execution, formatted response, and end-session signaling
  - Covers `backend.fetch_agents.launch.main()` usage, failure, and success paths
  - Covers `backend.run_fetch_agents.main()` subprocess spawning and cleanup

- [tests/test_fetch_runtime_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime_additional.py)
  - Verifies the SELL-side Fetch bridge runs the chain in order for `depop_listing_agent`
  - Verifies `execute_agent()` builds Fetch session IDs and fetch-specific context correctly
  - Includes an `xfail` test documenting the broken BUY bridge after the first search step

### Existing

- [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py)
  - Covers text parsing helpers
  - Covers basic search and pricing Fetch runtime paths
  - Covers current empty-ranking failure behavior

- [tests/test_http_execution_and_launcher.py](/Users/jt/Desktop/diamondhacks/tests/test_http_execution_and_launcher.py)
  - Covers the non-Fetch multi-process FastAPI launcher
  - Useful as a comparison point for process-supervision behavior

## Browser Use Test Suites

### New

- [tests/test_browser_use_marketplaces_contracts.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_marketplaces_contracts.py)
  - Pins the Depop Browser Use task strings for prepare, revise, submit, and abort
  - Verifies non-mobile wording and the no-submit contract in prepare and revise phases

- [tests/test_browser_use_sell_checkpoint_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_sell_checkpoint_additional.py)
  - Verifies Browser Use session cleanup when `final_result()` is missing
  - Verifies Depop listing checkpoint operations call the Browser Use runner with the expected `operation_name`, `keep_alive=True`, profile path, and domain allowlist

### Existing

- [tests/test_browser_use_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime.py)
  - Covers runtime readiness checks, fallback forcing, Browser Use kwargs, timeout behavior, and failure categorization

- [tests/test_browser_use_support_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_support_additional.py)
  - Covers session cleanup when the Browser Use agent raises
  - Covers additional error classification behavior
  - Covers remote-image download and local-path fallback in the sell listing agent

- [tests/test_depop_listing_agent_real.py](/Users/jt/Desktop/diamondhacks/tests/test_depop_listing_agent_real.py)
  - Covers sell listing output construction
  - Covers live Browser Use checkpoint metadata
  - Covers fallback listing behavior and sell pipeline use of the listing agent

- [tests/test_browser_use_progress_events.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_progress_events.py)
  - Covers Browser Use-related SSE events for search, draft creation, and sell review flow events

- [tests/test_buy_search_agents_real.py](/Users/jt/Desktop/diamondhacks/tests/test_buy_search_agents_real.py)
  - Covers live/fallback search-agent behavior across marketplaces

- [tests/test_ebay_sold_comps_agent_real.py](/Users/jt/Desktop/diamondhacks/tests/test_ebay_sold_comps_agent_real.py)
  - Covers eBay sold-comps live/fallback behavior

- [tests/test_browser_use_validation_harness.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_validation_harness.py)
  - Covers the backend Browser Use validation harness behavior

- [tests/test_browser_use_runtime_audit.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime_audit.py)
  - Covers runtime-audit reporting for Browser Use prerequisites

- [tests/test_browser_use_runtime_verifier.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime_verifier.py)
  - Covers Browser Use runtime verification helpers

## What The New Coverage Adds

- It tests the Fetch `uAgents` adapter layer directly, which was largely untested before.
- It tests the Fetch subprocess supervisor directly.
- It pins the sell review-loop Browser Use operation split more explicitly.
- It adds visible automated coverage for one known Fetch BUY bridge failure without turning the whole suite red.

## Known Limits

- Live Agentverse discovery and mailbox attachment are still not covered by local pytest.
- Real Browser Use interaction with warmed marketplace profiles is still only partially covered; some paths remain validated through harnesses and manual rehearsal rather than pure unit tests.
- The deterministic Browser Use checkpoint action and real screenshot capture are still not implemented, so the tests currently validate prompt contracts and orchestration behavior rather than that missing browser primitive.



# --- ARCHIVED FILE: FETCH-BROWSER-USE-TRACK-AUDIT.md ---

# Fetch + Browser Use Track Audit

Date: 2026-04-04

## Scope

This audit reviews the current repository state for the two sponsor tracks most relevant to the project:

- Best Use of Browser Use
- Best Use of Fetch.ai

It compares:

- DiamondHacks judging and deliverable requirements in [DiamondHacks Important Info.md](/Users/jt/Desktop/diamondhacks/DiamondHacks%20Important%20Info.md)
- The team’s intended submission narrative in [DiamondHacks Important Info.md](/Users/jt/Desktop/diamondhacks/DiamondHacks%20Important%20Info.md), [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md), and [JUDGING-PLAN.md](/Users/jt/Desktop/diamondhacks/JUDGING-PLAN.md)
- Current implementation, tests, and runbooks under `backend/`, `tests/`, and the Fetch / Browser Use docs

I did not need additional Notion research because the local DiamondHacks brief already contains the sponsor requirements and deliverables used for this audit.

## Executive Summary

The repo is in a credible state for both tracks, but it is not yet fully submission-complete for either one.

For Browser Use, the strongest point is that Browser Use is actually load-bearing in the intended architecture and there is substantial backend support for live browser automation, sell review pause/resume, runtime audits, and validation harnesses. The main weakness is that the highest-visibility claims are still not fully live-validated in a judge-proof way. The sell listing checkpoint is still prompt-driven instead of deterministic, real screenshot capture is still not implemented, and several Browser Use flows are documented as needing real account/profile validation.

For Fetch.ai, the codebase is much stronger than the older planning docs imply. The repo now has real `uAgents` wiring, Chat Protocol handling, public Agentverse-facing agents, metadata, README assets, a capability registry, and a demo script. The main weakness is operational completion: Agentverse registration, mailbox verification, ASI:One proof, and final submission URLs are still not checked in or documented as complete. There is also documentation drift between the old “10 public agents” narrative and the current “4 public specialized agents + internal workers” implementation.

Bottom line:

- Browser Use track: technically plausible and potentially strong, but the submission gets materially stronger only after one live eBay/Depop demo path is rehearsed and captured.
- Fetch.ai track: architecturally aligned and probably good enough for the sponsor’s product direction, but not yet deliverable-complete until Agentverse and ASI:One proof exists.

## Sources Reviewed

Primary requirements and judging context:

- [DiamondHacks Important Info.md](/Users/jt/Desktop/diamondhacks/DiamondHacks%20Important%20Info.md)
- [JUDGING-PLAN.md](/Users/jt/Desktop/diamondhacks/JUDGING-PLAN.md)
- [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md)

Fetch implementation and runbooks:

- [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py)
- [backend/fetch_agents/builder.py](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/builder.py)
- [backend/fetch_agents/chat_profiles.py](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/chat_profiles.py)
- [backend/run_fetch_agents.py](/Users/jt/Desktop/diamondhacks/backend/run_fetch_agents.py)
- [scripts/fetch_demo.py](/Users/jt/Desktop/diamondhacks/scripts/fetch_demo.py)
- [FETCH_INTEGRATION.md](/Users/jt/Desktop/diamondhacks/FETCH_INTEGRATION.md)
- [AGENTVERSE_IMPLEMENTATION_PLAN.md](/Users/jt/Desktop/diamondhacks/AGENTVERSE_IMPLEMENTATION_PLAN.md)
- [AGENTVERSE_SETUP.md](/Users/jt/Desktop/diamondhacks/AGENTVERSE_SETUP.md)
- [docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md](/Users/jt/Desktop/diamondhacks/docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md)

Browser Use implementation and runbooks:

- [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)
- [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
- [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
- [backend/browser_use_runtime_audit.py](/Users/jt/Desktop/diamondhacks/backend/browser_use_runtime_audit.py)
- [backend/browser_use_validation.py](/Users/jt/Desktop/diamondhacks/backend/browser_use_validation.py)
- [BrowserUse-Live-Validation.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Live-Validation.md)
- [BROWSER-USE-GAPS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-GAPS.md)
- [BROWSER-USE-STATUS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-STATUS.md)
- [BACKEND-CODEBASE-PROBLEMS.md](/Users/jt/Desktop/diamondhacks/BACKEND-CODEBASE-PROBLEMS.md)

Relevant tests:

- [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py)
- [tests/test_fetch_runtime_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime_additional.py)
- [tests/test_fetch_agent_builder_and_runner.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_agent_builder_and_runner.py)
- [tests/test_browser_use_fetch_compatibility.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_fetch_compatibility.py)
- [tests/test_browser_use_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime.py)
- [tests/test_browser_use_runtime_verifier.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime_verifier.py)
- [tests/test_browser_use_sell_checkpoint_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_sell_checkpoint_additional.py)

## Current Workspace Notes

The working tree contains uncommitted Browser Use-related changes that matter to this audit:

- [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
- [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)
- [backend/browser_use_runtime_audit.py](/Users/jt/Desktop/diamondhacks/backend/browser_use_runtime_audit.py)
- [BROWSER-USE-STATUS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-STATUS.md)

Those local changes improve the Browser Use story:

- search agents now use per-platform browser profiles
- Browser Use support has been updated to the newer `browser_use` Google wrapper and JSON `final_result()` parsing
- default Browser Use model is now `gemini-2.5-flash`
- runtime audit now checks macOS cache locations too

These changes strengthen the submission, but because they are not all committed yet, they should not be treated as locked deliverables until they are committed and retested.

## Browser Use Requirement Audit

Track requirements from [DiamondHacks Important Info.md](/Users/jt/Desktop/diamondhacks/DiamondHacks%20Important%20Info.md):

- Meaningful impact
- Core functionality must rely on Browser Use agents actively interacting with web environments
- Working software prototype for a live demo

### Requirement 1: Meaningful impact

Status: Mostly covered

Why:

- The project has a clear commerce problem and target user narrative in [DiamondHacks Important Info.md](/Users/jt/Desktop/diamondhacks/DiamondHacks%20Important%20Info.md): thrift-store flipping research and listing automation.
- The backend supports a real sell flow and a buy flow through orchestrated agents in [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py).
- The project fits Enchanted Commerce cleanly and has a judge-friendly story: identify, comp, price, list, and optionally negotiate.

What still weakens this:

- The strongest browser-powered end state is still partially simulated or fallback-backed in some paths.
- Vision is still heuristic-heavy rather than actual image understanding, which weakens the “full stack of AI + browser execution” story.

### Requirement 2: Core functionality relies on Browser Use

Status: Partially covered, but not yet fully proved

What is strong:

- Browser Use is embedded in the core architecture, not bolted on as a side feature.
- The intended load-bearing Browser Use steps are clear in [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md) and [DiamondHacks Important Info.md](/Users/jt/Desktop/diamondhacks/DiamondHacks%20Important%20Info.md):
  - eBay sold comps
  - Depop listing creation
  - marketplace search
  - negotiation
- There is concrete Browser Use code in:
  - [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)
  - [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
  - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
- There is a runtime audit and validation harness:
  - [backend/browser_use_runtime_audit.py](/Users/jt/Desktop/diamondhacks/backend/browser_use_runtime_audit.py)
  - [backend/browser_use_validation.py](/Users/jt/Desktop/diamondhacks/backend/browser_use_validation.py)
- There is end-to-end compatibility coverage between Browser Use fallback and Fetch-backed orchestration in [tests/test_browser_use_fetch_compatibility.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_fetch_compatibility.py).

What is still missing or risky:

- Live Browser Use validation is still explicitly listed as a remaining task in:
  - [FETCH-BROWSER-USE-COMPATIBILITY-PLAN.md](/Users/jt/Desktop/diamondhacks/FETCH-BROWSER-USE-COMPATIBILITY-PLAN.md)
  - [BACKEND-CODEBASE-PROBLEMS.md](/Users/jt/Desktop/diamondhacks/BACKEND-CODEBASE-PROBLEMS.md)
  - [BrowserUse-Live-Validation.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Live-Validation.md)
- The sell listing review checkpoint is still not deterministic at the browser runtime level. This is a known blocker in [BACKEND-CODEBASE-PROBLEMS.md](/Users/jt/Desktop/diamondhacks/BACKEND-CODEBASE-PROBLEMS.md) and [BROWSER-USE-GAPS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-GAPS.md).
- Screenshot handoff is still placeholder-style `form_screenshot_url`, not a real captured artifact.
- OfferUp profile / reliability is still called out as weak.
- Several Browser Use flows depend on warmed profiles and live accounts, which is fine for the track, but fragile unless rehearsed.

Assessment:

The Browser Use requirement is substantively addressed in architecture and code, but the project still needs one judge-safe live path to make the claim indisputable. Right now it is a strong implementation story, not yet a fully closed demo story.

### Requirement 3: Working software prototype for a live demo

Status: Covered in fallback mode, partially covered in live mode

What is working:

- The backend, pipelines, SSE, sell review loop, and fallback-compatible Browser Use codepaths are well scaffolded.
- The sell review lifecycle is well tested and documented:
  - [tests/test_sell_listing_review_orchestration.py](/Users/jt/Desktop/diamondhacks/tests/test_sell_listing_review_orchestration.py)
  - [BrowserUse-Live-Validation.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Live-Validation.md)
- The runtime audit and validation harness create a strong pre-demo checklist.

What is not yet fully demonstrated:

- There is no checked-in evidence of a successful live eBay comps run, successful live Depop listing prepare/revise/submit loop, or live offer sending.
- The Browser Use status doc itself still says several items “need testing” in [BROWSER-USE-STATUS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-STATUS.md).

Assessment:

This is demoable now if the team accepts a controlled fallback-heavy demo. It becomes genuinely strong for Browser Use judges only after one live rehearsal path is validated on the exact demo machine and accounts.

## Fetch.ai Requirement Audit

Track requirements from [DiamondHacks Important Info.md](/Users/jt/Desktop/diamondhacks/DiamondHacks%20Important%20Info.md):

- Agent orchestration demonstrating reasoning, tool execution, and solving a real-world problem
- Use any agentic framework
- Agentverse registration
- Chat Protocol mandatory
- Payment Protocol optional
- Demonstrate through ASI:One directly
- Deliverables: ASI:One chat session URL, Agentverse profile URL(s), public repo, demo video

### Requirement 1: Agent orchestration solving a real-world problem

Status: Covered

Why:

- The repo has an actual multi-agent pipeline for sell and buy flows in [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py).
- The Fetch layer adapts the same backend workflows through [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py).
- There is a real-world commerce problem with concrete outcomes.

Additional strength:

- The project now has a cleaner public Agentverse topology than some older docs: public specialists plus a public `resale_copilot_agent`, with internal worker agents behind the scenes.
- That is closer to what Fetch tends to want than ten identical wrappers.

### Requirement 2: Framework flexibility

Status: Covered

Why:

- The implementation uses plain Python plus `uAgents`.
- This is explicitly allowed by the sponsor brief.

### Requirement 3: Agentverse registration

Status: Not yet complete

What exists:

- `uAgents` construction and mailbox-compatible setup in [backend/fetch_agents/builder.py](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/builder.py)
- launch support in [backend/fetch_agents/launch.py](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/launch.py) and [backend/run_fetch_agents.py](/Users/jt/Desktop/diamondhacks/backend/run_fetch_agents.py)
- metadata, README paths, and capability registry in [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py) and [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py)
- runbooks for registration and deliverables in:
  - [AGENTVERSE_IMPLEMENTATION_PLAN.md](/Users/jt/Desktop/diamondhacks/AGENTVERSE_IMPLEMENTATION_PLAN.md)
  - [AGENTVERSE_SETUP.md](/Users/jt/Desktop/diamondhacks/AGENTVERSE_SETUP.md)
  - [docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md](/Users/jt/Desktop/diamondhacks/docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md)

What is missing:

- Actual recorded Agentverse profile URLs
- Confirmed mailbox registration for the final public agent set
- Confirmed `*_AGENTVERSE_ADDRESS` values in environment for the final lineup

Assessment:

The code is prepared for Agentverse registration. The deliverable is not complete until the agents are actually registered and the URLs are captured.

### Requirement 4: Chat Protocol mandatory

Status: Covered in code

Why:

- [backend/fetch_agents/builder.py](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/builder.py) uses `chat_protocol_spec`, `ChatMessage`, `ChatAcknowledgement`, `TextContent`, and `EndSessionContent`.
- Tests verify message handling, acknowledgements, handoff behavior, and clarification behavior in [tests/test_fetch_agent_builder_and_runner.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_agent_builder_and_runner.py).

Assessment:

This requirement appears satisfied at the code level.

### Requirement 5: Payment Protocol optional

Status: Not implemented, but not required

Observation:

- I found no Payment Protocol implementation or related wiring in the current code or docs.

Assessment:

This is not a compliance blocker. It is an optional feature that could strengthen the pitch only if the team has time.

### Requirement 6: ASI:One demonstration

Status: Not yet complete

What exists:

- public agent metadata, prompts, and demo tooling
- [scripts/fetch_demo.py](/Users/jt/Desktop/diamondhacks/scripts/fetch_demo.py) for exercising the chat path
- a strong `resale_copilot_agent` entrypoint for natural-language prompts

What is missing:

- a real ASI:One shared chat URL
- evidence that ASI:One can discover and route to the registered agents

Assessment:

This is the biggest remaining Fetch deliverable gap.

### Required Fetch deliverables

Status:

- Public GitHub repo: likely covered outside this audit
- Demo video: outside repo scope
- ASI:One chat session URL: missing
- Agentverse profile URL(s): missing

## What Is Strong Right Now

### Browser Use strengths

- Browser Use is not cosmetic. It is used in the actual marketplace-facing design.
- There is serious backend scaffolding for audits, validation, fallback safety, and review-loop orchestration.
- The sell review loop is a good judge-facing differentiator because it shows controlled automation instead of reckless auto-posting.
- The local uncommitted Browser Use fixes improve runtime realism materially.

### Fetch strengths

- Fetch is no longer placeholder-only. The repo has real `uAgents`, Chat Protocol, metadata, README assets, specialization logic, and a public entrypoint.
- The public/private split is stronger than the older “all agents are public” idea because it makes the Agentverse surface more coherent.
- The capability registry endpoints in [backend/main.py](/Users/jt/Desktop/diamondhacks/backend/main.py) are useful for internal verification and demos.

### Cross-track strengths

- The best story for this project is the combination:
  - Fetch for agent discoverability and ASI:One interaction
  - Browser Use for real executed web actions
  - commerce framing for a clear user problem

That is a stronger combined pitch than either track in isolation.

## Main Gaps and Risks

### 1. Browser Use live-demo risk is still the biggest practical weakness

The Browser Use track judges care less about elegant architecture than whether they can watch the browser do something real. The repo is close, but the current state still has these gaps:

- deterministic checkpoint action missing
- real screenshot capture missing
- live profile/account rehearsal not yet documented as passed
- OfferUp and some negotiation paths remain weak or best-effort

If these are not closed, the Browser Use submission remains vulnerable to looking fallback-driven even if the architecture is strong.

### 2. Fetch deliverables are not complete until URLs exist

For Fetch, the repo may already satisfy most technical expectations, but that does not matter if the submission package lacks:

- Agentverse profile URLs
- ASI:One shared chat URL

This is the difference between “implemented” and “submittable.”

### 3. There is documentation drift that can hurt the team’s story

Important drift points:

- Older docs still describe 10 public Fetch agents, while current code launches 4 public agents via [backend/run_fetch_agents.py](/Users/jt/Desktop/diamondhacks/backend/run_fetch_agents.py).
- [docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md](/Users/jt/Desktop/diamondhacks/docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md) still expects URLs for 10 agents.
- Some older docs still assume a different Fetch maturity level or Browser Use-first execution order.

This matters because sponsor judges respond to clear narratives. If the repo tells conflicting stories, the demo explanation gets weaker.

### 4. Vision remains a product-story weakness

The commerce demo is strongest when the first step feels real. The current backend backlog still lists the heuristic vision parser as a remaining problem in [BACKEND-CODEBASE-PROBLEMS.md](/Users/jt/Desktop/diamondhacks/BACKEND-CODEBASE-PROBLEMS.md).

That does not directly hurt Fetch or Browser Use compliance, but it weakens the overall “AI agent that really understands the item” story.

## Is The Track Submission Covered Right Now?

### Browser Use

Short answer: almost, but not confidently enough for a top submission yet.

Covered:

- meaningful use case
- Browser Use integrated into core workflow
- working backend prototype
- validation harnesses and audits

Not fully covered:

- judge-safe live proof of the most important Browser Use paths
- deterministic ready-to-submit stop
- real screenshot artifact

### Fetch.ai

Short answer: technically mostly yes, operationally not yet.

Covered:

- multi-agent orchestration
- `uAgents`
- Chat Protocol
- specialized public agents
- Agentverse-oriented metadata and README surface

Not fully covered:

- live Agentverse registration completion
- ASI:One discoverability proof
- submission URLs

## Highest-Leverage Additions To Make The Submission Stronger

These are the best next additions if the goal is sponsor-track strength rather than backend completeness.

### Priority 0: Close the deliverable gaps

1. Register the final public Fetch agents and capture the URLs.
2. Run one successful ASI:One session and save the shared chat URL.
3. Commit a filled version of the Agentverse deliverables matrix or a private equivalent team record.
4. Rehearse one live Browser Use demo path on the exact machine and accounts intended for judging.

Without these, both sponsor submissions remain incomplete regardless of code quality.

### Priority 1: Make Browser Use visibly real to judges

1. Implement deterministic sell checkpointing in the Browser Use runtime.
2. Replace `form_screenshot_url` placeholders with an actual screenshot artifact or schema-backed captured file.
3. Validate:
   - live eBay sold comps
   - live Depop draft creation
   - revise
   - confirm submit
4. Pre-stage one known-good demo item and account setup.

If only one Browser Use enhancement is completed, deterministic checkpoint plus a real screenshot artifact is the most leverage.

### Priority 2: Tighten the Fetch sponsor story

1. Align all docs around the current public surface:
   - `resale_copilot_agent`
   - `vision_agent`
   - `pricing_agent`
   - `depop_listing_agent`
2. Decide whether the submission says:
   - “4 public specialized agents + internal worker agents”
   - or “10 registered agents”

Right now the code and docs are split between those narratives. Pick one and make all sponsor-facing docs agree.

My recommendation:

- Use the stronger current narrative: 4 public customized Agentverse agents, backed by a larger internal worker graph.
- If 10 agents are actually going to be registered, update the public launch path and docs to match.

### Priority 3: Expose Browser Use status more clearly in Fetch responses

This is already noted in [FETCH_INTEGRATION.md](/Users/jt/Desktop/diamondhacks/FETCH_INTEGRATION.md) as a desirable next step.

Adding explicit Browser Use execution summaries in Fetch responses would make the ASI:One story better:

- whether browser automation actually ran
- which marketplace was touched
- whether the result came from live browser execution or fallback

This would help judges see that the agents do more than summarize backend state.

### Priority 4: Clean up sponsor-story inconsistencies

Recommended edits:

- Update [docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md](/Users/jt/Desktop/diamondhacks/docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md) to match the chosen public agent lineup.
- Update older “10 public agents” and “zero Fetch wiring exists” docs so they stop contradicting the current implementation.
- Keep one canonical sponsor-status document for the final demo state.

## Recommended Submission Narrative

If the goal is to maximize both sponsor tracks at once, the strongest narrative is:

“DiamondHacks is an autonomous resale copilot. Through Fetch.ai, users can discover and interact with specialized resale agents on Agentverse and ASI:One. Under the hood, Browser Use agents perform real marketplace actions: researching sold comps, preparing live Depop listings, and sourcing listings across marketplaces. The product solves a real commerce problem end to end, from item identification to executed listing preparation.”

This works because:

- Fetch gets the agentic web / discoverability / ASI:One story
- Browser Use gets the “watch it actually do the task in the browser” story
- Commerce judges get a clear real-world user benefit

## Final Assessment

### Browser Use submission readiness

Score: Medium-high, but with live-demo execution risk

This can become a very strong Browser Use submission. The repo already has serious Browser Use integration and a clear commerce workflow. The remaining issue is not conceptual fit; it is live-proof reliability.

### Fetch submission readiness

Score: Medium-high technically, medium operationally

The implementation is now much more aligned with Fetch’s likely expectations than the older docs suggest. The remaining work is mostly operational and narrative:

- register
- verify
- capture URLs
- make the docs tell one consistent story

## Concrete Next Actions

1. Commit the local Browser Use runtime fixes and rerun the focused Browser Use suite.
2. Run the Browser Use runtime audit in live-required mode on the demo machine.
3. Execute and record one live sell flow:
   - eBay sold comps
   - Depop draft to review checkpoint
4. Register the final Fetch public agents on Agentverse and record the addresses.
5. Run one ASI:One conversation through `resale_copilot_agent` and save the shared URL.
6. Update sponsor-facing docs so the public Fetch lineup and required deliverables are internally consistent.

## Recommended Verdict

If submission happened right now:

- Browser Use track: viable but weaker than it should be because the strongest live proof is not yet locked
- Fetch.ai track: viable in architecture, but incomplete in deliverables

If the next work focuses on live proof and deliverable capture instead of more backend expansion, the project can become a legitimately strong dual-track submission.


# --- ARCHIVED FILE: HANDOFF-IMPLEMENTATION-PLAN.md ---

# Handoff Implementation Plan

**Continuation of work from two prior agents.** This plan covers the remaining docs-only tasks and the runtime background-cleanup task that were scoped but not completed.

**Constraint:** Tasks 1–4 are docs-only. Task 5 is runtime code. Neither track edits `backend/orchestrator.py` (docs track) or docs (runtime track) — they are fully independent and can execute in parallel.

**Repo baseline at handoff (HEAD = `0c64c91`):**

- Sell listing review lifecycle is complete: pause at `ready_for_confirmation`, `confirm_submit`, `revise` (with `revision_count` and limit of 2), `abort`, and request-time expiry after 15-minute `deadline_at`.
- Revision deadline refresh landed: `_refresh_sell_listing_review_pause` resets `paused_at`/`deadline_at` after each successful revision so the user gets a fresh 15-minute window.
- Expiry is checked when a client hits `GET /result/{session_id}`, `GET /stream/{session_id}`, the SSE keepalive loop, or `POST /sell/listing-decision`, **and** via a **background sweep** (`SELL_REVIEW_CLEANUP_INTERVAL`, default 60s) implemented after this plan was written.
- Fetch runtime bridge (`backend/fetch_runtime.py`) passes chat text into the local agent registry. BUY search agents are called with `previous_outputs={}` (parallel in the Fetch path). SELL agents chain sequentially: vision → comps → pricing → listing. No-results flow produces synthetic ranking/negotiation outputs.
- Test suites added: `test_sell_listing_review_orchestration.py`, `test_sell_listing_decision_endpoint.py`, `test_browser_use_fetch_compatibility.py`. Contract tests aligned for Fetch manifest.
- Docs partially updated but contain inconsistencies flagged below.

---

## Track A — Docs Only (Tasks 1–4)

### Scope

Edit **only** these files:
- `BrowserUse-Live-Validation.md`
- `FETCH_INTEGRATION.md`
- `backend/README.md`
- `BACKEND-CODEBASE-PROBLEMS.md`

Do **not** edit any file under `backend/` except `backend/README.md`.

---

### Task 1: SELL live validation checklist in `BrowserUse-Live-Validation.md`

**Current state:** The SELL section (lines 52–67) covers the general review loop but lacks an exact step-by-step operator script with specific HTTP calls, expected SSE event sequences, and session field assertions.

**What to write:**

Add a subsection **"SELL Live Validation — Step-by-Step"** after the current SELL section. Structure it as a numbered operator checklist:

#### 1a. Prepare listing

- `POST /sell/start` with `{ "input": { "image_urls": [...], "notes": "..." } }`
- Wait for SSE: `pipeline_started` → `agent_started` (vision) → `agent_completed` (vision) → … → `agent_started` (depop_listing) → `agent_completed` (depop_listing) → `listing_review_required`
- Legacy `draft_created` may also appear — note it as compatibility-only.
- Assert `GET /result/{session_id}` returns:
  - `status: "paused"`
  - `sell_listing_review.state: "ready_for_confirmation"`
  - `sell_listing_review.deadline_at` is ~15 minutes from `sell_listing_review.paused_at`
  - `result.outputs.depop_listing.ready_for_confirmation: true`
  - `result.outputs.depop_listing.listing_status: "ready_for_confirmation"`

#### 1b. Revise once

- `POST /sell/listing-decision` with `{ "session_id": "...", "decision": "revise", "revision_instructions": "Lower the price by $5" }`
- Expected SSE sequence:
  1. `listing_decision_received` (`data.decision: "revise"`)
  2. `pipeline_resumed` (`data.reason: "listing_revision_requested"`)
  3. `listing_revision_requested` (`data.revision_instructions`, `data.revision_count: 1`)
  4. `listing_revision_applied` (`data.revision_count: 1`, updated `data.output`)
  5. `listing_review_required` (re-emitted with fresh `review_state`)
- Assert `GET /result/{session_id}`:
  - `status: "paused"` again
  - `sell_listing_review.state: "ready_for_confirmation"`
  - `sell_listing_review.revision_count: 1`
  - **New** `deadline_at` (refreshed — not the original timestamp)
- Note: max revisions = 2. A third revise attempt will trigger `listing_revision_limit_reached` → `pipeline_failed`.

#### 1c. Confirm submit

- `POST /sell/listing-decision` with `{ "session_id": "...", "decision": "confirm_submit" }`
- Expected SSE sequence:
  1. `listing_decision_received` (`data.decision: "confirm_submit"`)
  2. `pipeline_resumed`
  3. `listing_submission_approved`
  4. `listing_submit_requested`
  5. On success: `listing_submitted` → `pipeline_complete`
  6. On failure: `listing_submission_failed` → `pipeline_failed`
- Assert `GET /result/{session_id}`:
  - Success: `status: "completed"`, `sell_listing_review: null`
  - Failure: `status: "failed"`, `error` set

#### 1d. Abort path

- `POST /sell/listing-decision` with `{ "session_id": "...", "decision": "abort" }`
- Expected SSE sequence:
  1. `listing_decision_received`
  2. `listing_submission_aborted`
  3. `listing_abort_requested`
  4. `listing_aborted`
  5. `pipeline_complete`
- Assert: `status: "completed"`, `sell_listing_review: null`, `depop_listing.listing_status: "aborted"`

#### 1e. Expiry path

- Let a paused session sit past `deadline_at` (15 minutes).
- **Today's behavior:** expiry fires only when client polls:
  - `GET /result/{session_id}` checks `expire_sell_listing_review_if_needed`
  - `GET /stream/{session_id}` checks on connect and in the SSE keepalive loop (~15s ticks)
  - `POST /sell/listing-decision` checks before processing
- Expected events on trigger: `listing_review_cleanup_completed` (or `listing_review_cleanup_failed`), `listing_review_expired`, `pipeline_failed`
- Assert: `status: "failed"`, `error: "sell_listing_review_timeout"`, `sell_listing_review: null`, `depop_listing.listing_status: "expired"`
- **Known gap:** If no client ever polls after deadline, the session remains paused indefinitely in memory. A background cleanup task is planned (see Task 5) but is not yet implemented.

#### 1f. Error edge cases to document

- `POST /sell/listing-decision` when `status != "paused"` → 409
- `POST /sell/listing-decision` with `decision: "revise"` but empty `revision_instructions` → 422
- `POST /sell/listing-decision` when `revision_count >= 2` and `decision: "revise"` → 409 after `listing_revision_limit_reached` + `pipeline_failed`

**Source of truth for event sequences:** `backend/orchestrator.py` lines 683–940 (`handle_sell_listing_decision`), tests in `tests/test_sell_listing_review_orchestration.py`, and `tests/test_sell_listing_decision_endpoint.py`.

**Acceptance:** The checklist is copy-pasteable by an operator with `curl`/`httpie` against a running `make run` instance. Every assertion maps to an actual field in `SessionState` or `SellListingReviewState`.

---

### Task 2: Fetch setup docs in `FETCH_INTEGRATION.md` and `backend/README.md`

**Current inconsistency identified:**

| Topic | `FETCH_INTEGRATION.md` says | `Makefile` actually does | `backend/README.md` says |
|-------|---------------------------|-------------------------|-------------------------|
| `.venv-fetch` creation | `pip install -r requirements.txt` | `pip install uagents uagents-core` (only 2 packages) | `make venv-fetch` (correct) |
| Python version | 3.12 or 3.13 | `FETCH_PYTHON ?= python3.12` | 3.12 or 3.13 |
| `FETCH_ENABLED` default | Not explicit | Not in Makefile; `config.py` has getter | `false` |

**What to fix:**

#### 2a. `.venv-fetch` setup section (both files)

Write the exact sequence:

```
make venv-fetch           # creates .venv-fetch with python3.12, installs uagents + uagents-core only
```

**Remove** the `pip install -r requirements.txt` instruction from `FETCH_INTEGRATION.md` § "Important Environment Note" — the Fetch venv intentionally does **not** install the full backend requirements. The Fetch agents import from the backend via `PYTHONPATH=$PWD` set by the Makefile target, which means the Fetch processes need the backend packages accessible on the system or via `PYTHONPATH` pointing at the `.venv` site-packages. **Clarify** this: the Fetch processes rely on `PYTHONPATH=$PWD` to reach `backend/` source, but they run under `.venv-fetch`'s Python where `uagents` is installed. If a Fetch agent transitively imports a backend dependency (e.g. `pydantic`, `httpx`), that dependency must also be in `.venv-fetch` or reachable. **Document** whether this currently works or whether the operator needs `pip install -r requirements.txt` in `.venv-fetch` as well — test by running `make run-fetch-agents` in a clean `.venv-fetch` and noting any `ImportError`.

#### 2b. Ports/process model (both files)

Write a clear table:

| Process | Command | Venv | Ports | Purpose |
|---------|---------|------|-------|---------|
| FastAPI backend | `make run` | `.venv` | 8000 | Product API, SSE, orchestrator |
| Per-agent FastAPI apps | `make run-agents` | `.venv` | 9101–9110 | Optional; validates per-agent `/task` surface |
| Fetch uAgents | `make run-fetch-agents` | `.venv-fetch` | 9201–9210 | Agentverse/ASI:One exposure |

All three can run concurrently without port collisions.

#### 2c. `make run` + `make run-fetch-agents` coexistence

Document: two terminal windows, two shells. Backend shell: standard env with `FETCH_ENABLED=false` (default — Fetch routing is opt-in). Fetch shell: export `AGENTVERSE_API_KEY` + all 10 seed vars, then `make run-fetch-agents`.

If you want the **backend orchestrator** to route through Fetch instead of local registry: set `FETCH_ENABLED=true` in the **backend** shell. This is only needed for integration testing; normal demos use both processes independently.

#### 2d. Live validation for `FETCH_ENABLED=true`

Numbered checklist:

1. `make run` — confirm `GET /health` shows `fetch_enabled: false` by default.
2. In Fetch shell: `make run-fetch-agents` — confirm ports 9201–9210 occupied.
3. Smoke one search agent: `python scripts/fetch_demo.py 9205 "Vintage Nike tee under $45"`.
4. Restart backend with `FETCH_ENABLED=true`.
5. `GET /health` now shows `fetch_enabled: true`.
6. `POST /buy/start` — confirm the pipeline completes; SSE events appear.
7. For mailbox mode: `FETCH_USE_LOCAL_ENDPOINT=false` (default). Confirm Agentverse registration in Fetch agent stdout.
8. For local inspector mode: `FETCH_USE_LOCAL_ENDPOINT=true`. Document that this is debug-only, not mailbox-backed.

**Acceptance:** An operator can follow the numbered steps from a clean clone, both with and without `FETCH_ENABLED=true`, and know exactly what output to expect at each step.

---

### Task 3: Refresh `BACKEND-CODEBASE-PROBLEMS.md`

**Current state:** 4 P0s, 4 P1s, 4 P2s, 3 P3s. Several items were addressed in the last 5 commits but not marked.

**Changes to make:**

#### 3a. Mark completed items

These are **done** (code + tests landed):

- ~~P1: "Add background cleanup for abandoned paused SELL review sessions"~~ — **Partially done.** Request-time expiry works. The backlog item should be updated to reflect: "request-time expiry is implemented; background timer-driven cleanup is not." **Do not mark fully complete.**

Actually on closer review, **nothing in the last 5 commits fully closes any P0/P1 item**. The work added sell-review lifecycle hardening and test coverage, but the four P0 items (Fetch BUY bridge, vision heuristic, vision schema alignment, deterministic browser checkpoint, placeholder screenshot) remain open. The revision-limit and expiry logic is new capability, not a fix to an existing backlog item.

#### 3b. Add "Implemented but not live-validated" section

Create a new section between P1 and P2:

**Implemented, Not Live-Validated:**

- [x] Sell listing review lifecycle: pause, confirm, revise (with revision limit = 2), abort, request-time expiry (15 min deadline). **Code:** `backend/orchestrator.py` lines 85–215, 683–940. **Tests:** `test_sell_listing_review_orchestration.py`, `test_sell_listing_decision_endpoint.py`. **Not validated:** against a real Depop browser session with live Browser Use submit/revise/abort actions.
- [x] Revision deadline refresh: `_refresh_sell_listing_review_pause` resets window after each successful revision. **Tests:** `test_sell_listing_review_orchestration.py`. **Not validated:** against a live revision where Browser Use modifies form fields.
- [x] Fetch runtime bridge: SELL chain (vision → comps → pricing → listing) and BUY chain (parallel search → ranking → negotiation) with no-results short-circuit. **Tests:** `test_fetch_runtime.py`, `test_browser_use_fetch_compatibility.py`. **Not validated:** actual Agentverse mailbox discovery or ASI:One prompt-response cycle.
- [x] Fetch agent manifest: `GET /fetch-agents` returns all 10 specs. **Tests:** `test_contracts_and_execution.py`. **Not validated:** live agent registration on Agentverse.

#### 3c. Update P1 item for background cleanup

Rewrite the item:

> **Add background cleanup for abandoned paused SELL review sessions.**
> Current state: request-time expiry is implemented — `expire_sell_listing_review_if_needed` runs from `/result`, `/stream`, SSE loop, and `/sell/listing-decision`. Sessions that are never polled after `deadline_at` remain paused indefinitely. A timer-driven cleanup task is needed to sweep these.
> References: `backend/orchestrator.py` L201–215, `backend/main.py` L248.

#### 3d. Keep remaining items prioritized

P0s stay P0. Reorder within P0 by actionability:

1. Deterministic Browser Use submit checkpoint (blocks live SELL demo)
2. Real screenshot capture (blocks listing preview UX)
3. Fix Fetch BUY bridge `previous_outputs` contract (blocks Fetch BUY demo)
4. Vision heuristic → real image pipeline (blocks Gemini story)
5. Vision output schema alignment (blocks confidence pause)

#### 3e. Add verification notes update

Update the "Verification Notes" section at the bottom to list the new test files from the last 5 commits:

- `test_sell_listing_review_orchestration.py` (7 tests)
- `test_sell_listing_decision_endpoint.py` (5+ tests)
- `test_browser_use_fetch_compatibility.py` (3+ tests)
- Expanded `test_contracts_and_execution.py` (fetch agent manifest)
- Expanded `test_pipelines.py` (sell listing review pause test)

**Acceptance:** Each backlog item clearly states whether it is a **code gap** or an **ops/validation gap**. No item is marked done unless both code and tests landed.

---

### Task 4: Commit

Stage only:
- `BrowserUse-Live-Validation.md`
- `FETCH_INTEGRATION.md`
- `backend/README.md`
- `BACKEND-CODEBASE-PROBLEMS.md`

Commit message: `Update validation checklists, Fetch setup docs, and backlog status`

Verify: `make check` still passes (docs-only changes should not affect tests, but confirm).

---

## Track B — Runtime: Background Session Expiry (Task 5)

### Scope

Edit **only**:
- `backend/main.py` (startup/shutdown lifecycle)
- `backend/session.py` (if a new query method is needed)
- `tests/test_sell_listing_review_orchestration.py` (or new test file)

Do **not** edit `backend/orchestrator.py` — reuse existing `expire_sell_listing_review_if_needed`.
Do **not** edit any doc file.

---

### Task 5: Timer-driven cleanup for abandoned paused sell-review sessions

#### 5a. Design

**Approach:** Add an `asyncio` background task that starts on FastAPI app startup (via `lifespan` or `@app.on_event("startup")`) and runs a periodic sweep.

**Sweep logic:**

```
every CLEANUP_INTERVAL_SECONDS (default: 60):
    for each session_id in session_manager.list_paused_sell_sessions():
        session = await session_manager.get_session(session_id)
        if session is None:
            continue
        if session.status != "paused" or session.sell_listing_review is None:
            continue
        await expire_sell_listing_review_if_needed(session_id)
```

This reuses the existing `expire_sell_listing_review_if_needed` function, which already:
- Checks `sell_listing_review_is_expired(review)` against `deadline_at`
- Calls `fail_sell_listing_review` with `sell_listing_review_timeout` error
- Emits `listing_review_expired` + cleanup events + `pipeline_failed`
- Calls `session_manager.clear_sell_listing_review`
- Marks session `status: "failed"`, `error: "sell_listing_review_timeout"`

No new orchestrator logic needed.

#### 5b. Session manager changes

`backend/session.py` currently stores sessions in a dict. Add one method:

```python
async def list_paused_sell_review_session_ids(self) -> list[str]:
    """Return session IDs that are paused with an active sell_listing_review."""
    return [
        sid for sid, session in self._sessions.items()
        if session.status == "paused"
        and session.pipeline == "sell"
        and session.sell_listing_review is not None
    ]
```

This is a read-only scan of the in-memory dict. No locking issues since the dict mutation and this scan both run on the same event loop.

#### 5c. Background task in `backend/main.py`

Add to the app lifecycle:

```python
CLEANUP_INTERVAL_SECONDS = int(os.environ.get("SELL_REVIEW_CLEANUP_INTERVAL", "60"))

async def _sell_review_cleanup_loop():
    from backend.orchestrator import expire_sell_listing_review_if_needed
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            session_ids = await session_manager.list_paused_sell_review_session_ids()
            for sid in session_ids:
                await expire_sell_listing_review_if_needed(sid)
        except Exception:
            pass  # log but never crash the cleanup loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_sell_review_cleanup_loop())
    yield
    task.cancel()
```

If `main.py` already uses `@app.on_event("startup")` instead of `lifespan`, adapt to the existing pattern. The key constraint: the task must be cancellable on shutdown and must not raise.

#### 5d. Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SELL_REVIEW_CLEANUP_INTERVAL` | `60` | Seconds between sweep runs |

The existing `SELL_LISTING_REVIEW_TIMEOUT_MINUTES` (15) controls when a session is considered expired. The cleanup interval only controls how frequently the sweep checks — worst-case a session stays alive up to `CLEANUP_INTERVAL_SECONDS` past its deadline.

#### 5e. Tests

Add to `tests/test_sell_listing_review_orchestration.py` (or a new `tests/test_sell_review_background_expiry.py`):

**Test 1: Background sweep expires an abandoned session**

```
1. Create session, set status="paused", sell_listing_review with deadline_at in the past.
2. Do NOT call any endpoint (simulating zero client activity).
3. Directly call the sweep function (or the expiry function it delegates to).
4. Assert session.status == "failed", error == "sell_listing_review_timeout",
   sell_listing_review is None.
5. Assert events include "listing_review_expired" and "pipeline_failed".
```

**Test 2: Background sweep skips non-expired sessions**

```
1. Create session, set status="paused", sell_listing_review with deadline_at 10 minutes in the future.
2. Run sweep.
3. Assert session.status == "paused" (unchanged).
```

**Test 3: Background sweep skips non-sell sessions**

```
1. Create a buy session with status="running".
2. Run sweep.
3. Assert no state change.
```

**Test 4: Regression — existing sell review orchestration still works**

```
Run existing test suite: make test
All tests in test_sell_listing_review_orchestration.py,
test_sell_listing_decision_endpoint.py, and test_pipelines.py pass.
```

**Test 5: Cleanup loop does not crash on empty session store**

```
1. Ensure no sessions exist.
2. Run one sweep iteration.
3. Assert no errors.
```

#### 5f. What NOT to do

- Do not add expiry to `run_pipeline` — that would couple pipeline execution with cleanup.
- Do not add a `deadline_at` watcher per session (over-engineered for in-memory store).
- Do not change the existing lazy-expiry behavior in `/result`, `/stream`, `/sell/listing-decision` — the background task is additive, not a replacement.
- Do not edit `backend/orchestrator.py` — all expiry logic already exists there.

#### 5g. Commit

Stage: `backend/main.py`, `backend/session.py`, new/modified test files.

Commit message: `Add background cleanup for abandoned paused sell-review sessions`

Verify: `make check` passes.

---

## Execution Order

Both tracks are independent. If executing sequentially:

1. **Track A (docs)** first — faster, no test risk, clarifies the state of the world.
2. **Track B (runtime)** second — small code surface, reuses existing functions, focused tests.

If executing in parallel: assign to two agents. No file overlap.

---

## Post-Completion Checklist

After both tracks land:

- [ ] `make check` passes
- [ ] `BACKEND-CODEBASE-PROBLEMS.md` P1 "background cleanup" item can be marked done
- [ ] `BrowserUse-Live-Validation.md` SELL checklist can be walked through against `make run` with fallback mode
- [ ] `FETCH_INTEGRATION.md` setup instructions match `Makefile` exactly
- [ ] No runtime files were edited by the docs track
- [ ] No doc files were edited by the runtime track

---

## Out of Scope (flagged for future)

These are **not** part of this plan:

- Deterministic Browser Use submit checkpoint (P0 code gap — needs `browser_use_marketplaces.py` changes)
- Real screenshot capture (P0 code gap — needs `browser_use_support.py` + schema changes)
- Fetch BUY bridge `previous_outputs` fix (P0 code gap — needs `schemas.py` contract relaxation)
- Vision heuristic → Gemini (separate workstream)
- Live Agentverse mailbox/discoverability validation (ops task, not code)
- Full end-to-end live validation against real marketplace accounts (ops task)


# --- ARCHIVED FILE: IMPLEMENTATION-PLAN.md ---

# DiamondHacks Backend — In-Depth Implementation Plan

**Document purpose:** A single, execution-oriented plan for finishing the resale-agent backend and integrating it cleanly with parallel workstreams (Fetch.ai, Gemini vision, mobile frontend). It is meant to be sliced into tickets and owned by individuals without duplicating effort.

**Repo baseline:** FastAPI app in `backend/`, in-memory sessions, SSE progress, ten agents behind a stable `/task` contract, `AGENT_EXECUTION_MODE` of `local_functions` (default) or `http` for per-process microservices.

**Related documents:** `PROJECT-CONTEXT.md`, `PRD.md`, `API_CONTRACT.md`, `FetchAI-Status.md`, `FETCH_INTEGRATION.md`, `AGENTVERSE_IMPLEMENTATION_PLAN.md`, `AGENTVERSE_SETUP.md`, `AGENTS.md`, `CLAUDE.md`, `BROWSER_USE_GUIDE.md`, `BrowserUse-Live-Validation.md`.

---

## Table of Contents

1. [Goals and success criteria](#1-goals-and-success-criteria)
2. [Architecture invariants](#2-architecture-invariants-non-negotiables)
3. [Workstream ownership matrix](#3-workstream-ownership-matrix)
4. [Phase 0 — Alignment and contract baselines](#phase-0--alignment-and-contract-baselines)
5. [Phase 1 — Frontend integration readiness](#phase-1--frontend-integration-readiness)
6. [Phase 2 — Vision contract, low-confidence pause, and resume](#phase-2--vision-contract-low-confidence-pause-and-resume)
7. [Phase 3 — Buy pipeline performance and search quality](#phase-3--buy-pipeline-performance-and-search-quality)
8. [Phase 4 — Sell pipeline depth (post-vision)](#phase-4--sell-pipeline-depth-post-vision)
9. [Phase 5 — Browser Use reliability and demo hardening](#phase-5--browser-use-reliability-and-demo-hardening)
10. [Phase 6 — Fetch.ai integration support](#phase-6--fetchai-integration-support-glue-only)
11. [Phase 7 — Deployment, observability, and operations](#phase-7--deployment-observability-and-operations)
12. [Testing strategy](#12-testing-strategy)
13. [Risk register](#13-risk-register)
14. [Appendix A — Canonical file map](#appendix-a--canonical-file-map)
15. [Appendix B — Environment variables](#appendix-b--environment-variables)
16. [Appendix C — SSE event catalog](#appendix-c--sse-event-catalog)

---

## 1. Goals and success criteria

### 1.1 Product goals

- **Sell path:** User provides image URL(s) and notes → system identifies item, pulls comps, prices, prepares Depop listing (with optional human confirmation when identification is uncertain).
- **Buy path:** User provides query and budget → system searches four marketplaces, ranks, prepares/sends negotiation actions (with clear disclosure when automation is simulated or fallback).
- **Realtime:** Client receives structured SSE events for every meaningful state transition without polling the orchestrator internals.
- **Sponsor tracks:** Browser Use and Fetch.ai remain demonstrable without breaking the primary FastAPI contract.

### 1.2 Technical success criteria (definition of done for “backend ready for demo”)

| Criterion | Verification |
|-----------|----------------|
| `make check` passes locally and in CI | GitHub Actions workflow green |
| `API_CONTRACT.md` matches observable HTTP + SSE behavior | Manual diff + contract tests |
| Sell pipeline completes in `local_functions` with fallback where Browser Use unavailable | `tests/test_pipelines.py` + smoke |
| Buy pipeline completes with deterministic or httpx/browser_use paths | Same |
| Low-confidence vision path is **schema-valid**, test-covered, and documented | New tests; frontend can implement UX against fixed payloads |
| Optional: four buy searches complete faster than sequential baseline | Timing log or benchmark test (non-flaky bounds) |
| Deployed staging URL documented with required secrets | Runbook section filled in |

---

## 2. Architecture invariants (non-negotiables)

These protect parallel development.

1. **`/task` request/response shape** — The orchestrator always builds `AgentTaskRequest` with `input.original_input` and `input.previous_outputs`. Agent outputs must validate against `AGENT_OUTPUT_MODELS` in `backend/schemas.py`. Fetch or Gemini work must not remove or rename these fields without a versioned migration plan.

2. **SSE event names** — Use underscore-delimited names as emitted today (`pipeline_started`, `agent_completed`, etc.). Renaming requires explicit frontend agreement and a deprecation window.

3. **Agent slugs and ports** — Defined in `backend/config.py`. Agentverse metadata should reference the same slugs.

4. **Execution modes** — `local_functions` vs `http` must remain behaviorally equivalent for the same inputs (within limits of subprocess isolation and timing). Integration tests should run the default mode; at least one CI job or documented manual step should exercise `http` mode periodically.

5. **Browser Use failures are not pipeline failures** — Agents should return structured `execution_mode: "fallback"` (or equivalent) when live automation is unavailable, unless the product decision is to hard-fail (document if changed).

---

## 3. Workstream ownership matrix

| Workstream | Primary owner | Backend buddy responsibilities |
|------------|---------------|--------------------------------|
| Fetch.ai uAgents, `/chat`, Agentverse | Dedicated teammate | Config stubs, health flags, CI secrets layout, “do not break `/task`” reviews |
| Gemini / vision identification | Dedicated teammate | Pydantic fields, pause threshold, tests that mock vision output, merge order after schema lands |
| Mobile frontend (Expo) | Dedicated teammate | Accurate `API_CONTRACT.md`, example payloads, CORS if web tooling used, SSE samples |
| Orchestration, contracts, perf, tests, deploy | You (recommended) | This plan’s Phases 0–5, 7; selective Phase 6 |

---

## Phase 0 — Alignment and contract baselines

**Objective:** Eliminate drift between docs, tests, and runtime before building new features.

### 0.1 Audit documentation against code

**Tasks:**

1. Reconcile `PROJECT-CONTEXT.md` with `backend/main.py`:
   - CORS: `main.py` already mounts `CORSMiddleware` (`allow_origins=["*"]`). Update `PROJECT-CONTEXT.md` “Known Bugs” if it still claims CORS is missing.
   - SSE keepalive: `iter_session_events` yields `: ping\n\n` on timeout. Update any doc that claims no keepalive.

2. Reconcile execution mode naming: `backend/config.py` uses `AGENT_EXECUTION_MODE` values `local_functions` and `http`. If any doc says `local_http`, standardize on `http`.

3. Map every public route in `main.py` to a section in `API_CONTRACT.md`:
   - `GET /health`, `GET /agents`, `GET /pipelines`
   - `POST /sell/start`, `POST /buy/start`, `POST /sell/correct`
   - `GET /stream/{session_id}`, `GET /result/{session_id}`
   - `POST /internal/event/{session_id}`

**Acceptance criteria:** PR that only updates markdown (and optionally adds a CI check or script that fails if a route is removed without updating `API_CONTRACT.md` — optional stretch).

**Files:** `PROJECT-CONTEXT.md`, `API_CONTRACT.md`, `README.md`, `backend/README.md`.

---

### 0.2 Establish a “contract changelog” convention

**Tasks:**

1. Add a short subsection to `API_CONTRACT.md`: **Changelog** with date, author, and bullet list of breaking vs additive changes.

2. For any future schema change to `SessionState` or event payloads, require a one-line changelog entry.

**Acceptance criteria:** Changelog section exists; team agrees in standup.

---

## Phase 1 — Frontend integration readiness

**Objective:** Minimize frontend integration time and surprise.

### 1.1 Normalize `GET /result/{session_id}` documentation

**Current behavior:** Returns full `SessionState.model_dump()` including `status`, `request`, `result`, `error`, `events`, timestamps.

**Tasks:**

1. Update `API_CONTRACT.md` §1.4 to show the **actual** JSON shape (not a simplified `final_outputs` placeholder unless you add a dedicated field).

2. Optionally add a stable `GET /result/{session_id}/summary` that returns only `{session_id, status, pipeline, error, outputs}` — **only if** the frontend wants a smaller payload. If added, it must be tested and documented; otherwise prefer documenting the full shape.

**Acceptance criteria:** Frontend developer can implement result polling from the doc alone.

**Files:** `API_CONTRACT.md`, optionally `backend/main.py`, `tests/test_health_and_sessions.py` or new test file.

---

### 1.2 SSE payload examples (golden files)

**Tasks:**

1. Add `tests/fixtures/sse/` (or `docs/examples/sse/`) with **redacted** example JSON bodies for:
   - `pipeline_started` (sell and buy)
   - `agent_completed` for each step name
   - `agent_error` and `pipeline_failed`
   - `vision_low_confidence` (after Phase 2 fixes)
   - `pipeline_resumed` (sell correction path)

2. Optionally add a pytest that parses these fixtures with the same `parse_sse_events` helper style as `tests/test_pipelines.py`.

**Acceptance criteria:** Frontend can copy-paste types from examples.

---

### 1.3 Error semantics for the UI

**Tasks:**

1. Document in `API_CONTRACT.md` how to interpret:
   - `session.status === "failed"` vs in-progress
   - `agent_error.data.category` (`timeout`, `validation`, `agent_execution`) from `backend/orchestrator.py` `classify_error`
   - Partial `result.outputs` on failure (orchestrator already attaches `partial_result` on `pipeline_failed`)

2. If the product needs **stable machine-readable codes**, extend `agent_error` / `pipeline_failed` `data` with optional `code: str` fields (additive only). Coordinate with frontend before shipping.

**Acceptance criteria:** Documented; optional code fields behind explicit decision.

**Files:** `API_CONTRACT.md`, possibly `backend/orchestrator.py`.

---

## Phase 2 — Vision contract, low-confidence pause, and resume

**Objective:** Make the sell-side “uncertain identification → user corrects → pipeline continues” flow **end-to-end correct** and testable, independent of whether Gemini or a stub produces vision output.

### 2.1 Problem statement (as of repo survey)

- `backend/orchestrator.py` after `vision_analysis` checks `validated_output.get("confidence", …)` and may emit `vision_low_confidence` and pause.
- `VisionAnalysisOutput` in `backend/schemas.py` does **not** define `confidence` (or related fields). `validate_agent_output` uses strict output models; extra keys from agents may not survive validation depending on Pydantic configuration.
- `backend/agents/vision_agent.py` currently performs **heuristic** extraction from notes and image URL strings; it does not emit `confidence`.

**Result:** The pause path is unlikely to behave as designed until schema + agent output align.

### 2.2 Schema design

**Tasks:**

1. Extend `VisionAnalysisOutput` with:
   - `confidence: float` — required, range `0.0`–`1.0`, or optional with default `1.0` for backward compatibility (prefer **required** once Gemini owns it, with stub setting explicit values).
   - Optional: `identification_notes: str | None`, `raw_model_response_ref: str | None` (for debug only; avoid PII).

2. Update `AGENT_OUTPUT_MODELS` entry (already points at `VisionAnalysisOutput`).

3. Ensure `CorrectionRequest.corrected_item` is documented to match **either** a superset of vision fields or the exact shape the frontend will POST. Align with `resume_sell_pipeline`, which assigns `outputs["vision_analysis"] = corrected_item`. The downstream agents expect `VisionAnalysisOutput` fields (`detected_item`, `brand`, `category`, `condition`). **Require** corrected payloads to include those keys or define a normalization function in `resume_sell_pipeline` that maps `item_name` → `detected_item` etc.

### 2.3 Normalization layer for user corrections

**Tasks:**

1. Implement `normalize_vision_correction(corrected_item: dict) -> dict` (e.g. in `backend/schemas.py` or `backend/orchestrator.py`) that:
   - Accepts frontend-friendly keys (`item_name`, `search_query`, …)
   - Produces a dict that validates as `VisionAnalysisOutput` (or merge into existing output)

2. Call this from `resume_sell_pipeline` before persisting `outputs["vision_analysis"]`.

**Acceptance criteria:** `tests/test_sell_correct_endpoint.py` asserts downstream-valid shape, not only dict equality with arbitrary keys.

**Files:** `backend/orchestrator.py`, `backend/schemas.py`, `tests/test_sell_correct_endpoint.py`.

---

### 2.4 Orchestrator pause semantics

**Tasks:**

1. Replace string comparison `str(exc) == "low_confidence_pause"` with a **typed exception** (e.g. `class LowConfidencePause(Exception): pass`) raised from a dedicated branch after emitting `vision_low_confidence`.

2. Ensure session `status` remains **`running`** (not `failed`) when pausing, and `result` retains partial outputs for resume. Verify `session_manager.update_status` behavior matches product expectation (frontend may poll `/result` while waiting for user).

3. Document whether **`pipeline_failed`** should **never** fire for low-confidence pause (current design: no).

4. Align `vision_low_confidence` payload with `API_CONTRACT.md`: include everything the UI needs (`suggestion`, `message`, scores, optional bounding fields).

**Acceptance criteria:** Unit/integration test: force low confidence → stream shows `vision_low_confidence` → session still `running` → `POST /sell/correct` → `pipeline_complete`.

**Files:** `backend/orchestrator.py`, `tests/test_pipelines.py` (new case), `API_CONTRACT.md`.

---

### 2.5 Stub and Gemini handoff

**Tasks:**

1. Until Gemini merges: update **heuristic** `vision_agent` to emit `confidence` (e.g. lower when brand is `Unknown` or token count is low).

2. After Gemini merges: ensure model output maps to `VisionAnalysisOutput` including calibrated `confidence`.

**Acceptance criteria:** Single source of truth for output shape; Gemini PR only changes `vision_agent.py` (and possibly prompts), not orchestrator logic.

---

## Phase 3 — Buy pipeline performance and search quality

**Objective:** Reduce wall-clock time for buy flows and improve usefulness of results when Browser Use is unavailable.

### 3.1 Parallelize the four search agents

**Current:** `run_pipeline` loops sequentially; each search agent only *needs* prior search outputs for schema chaining, but **each agent’s input model** encodes cumulative `previous_outputs` (eBay needs Depop, Mercari needs Depop+eBay, etc.). **Ranking** needs all four.

**Design options:**

| Option | Pros | Cons |
|--------|------|------|
| A. `asyncio.gather` on four tasks with **synthetic empty** previous_outputs where the contract allows | Fast | Violates current `AGENT_INPUT_CONTRACTS` unless relaxed |
| B. Change input models so each search agent only needs `BuyPipelineInput` | Clean, parallel | Breaking change to `validate_agent_task_request`; must update all agents |
| C. Parallelize only the **httpx** attempt layer inside a new composite step | Keeps orchestrator | Larger refactor |

**Recommended path for hackathon velocity:** **Option B (contract simplification)** if team accepts a one-time breaking internal contract:

1. Change `DepopSearchAgentInput`, `EbaySearchAgentInput`, etc. to use `previous_outputs: EmptyPreviousOutputs` (or a single shared model).

2. Update each search agent’s `build_output` to ignore cross-agent prior outputs.

3. In `run_pipeline`, replace the four-step loop with one orchestration block:
   - `gather` four coroutines wrapping `execute_step` for each slug with **synthetic** per-agent task requests **or** a new meta-agent `marketplace_search_fanout` that returns a dict of four result lists (bigger change).

4. Map results into `outputs` keys `depop_search`, `ebay_search`, … for `ranking_agent` unchanged.

**Tasks (detailed):**

1. Update `backend/schemas.py` input models for the four search agents.

2. Update `backend/agents/*_search_agent.py` to stop reading `previous_outputs` from other platforms.

3. Refactor `BUY_STEPS` or introduce `run_buy_search_phase` in `orchestrator.py` that runs four steps concurrently, then continues sequentially to ranking and negotiation.

4. SSE ordering: today events are strictly sequential. Parallel execution will interleave `agent_started` / `agent_completed`. **Document** this for the frontend (UI should key off `step` + `agent_name`, not global order).

5. Retries: `get_max_attempts` applies per agent; concurrent retries remain independent.

**Acceptance criteria:**

- Tests updated; `make test` passes.
- Optional: assert four searches start within same event loop “tick” (weak signal) or log timestamps.

**Files:** `backend/orchestrator.py`, `backend/schemas.py`, four search agent modules, `tests/test_contracts_and_execution.py`, `tests/test_pipelines.py`.

---

### 3.2 Tier-1 (httpx) coverage expansion

**Tasks:**

1. Audit `backend/agents/httpx_clients.py` for each marketplace. For any stub returning `None` too often, implement or improve internal API scraping **within ToS**.

2. Wire `EBAY_APP_ID` / `EBAY_CERT_ID` where Browse API is partially implemented; document failure modes when unset.

3. Ensure every search agent emits `search_method` (already pattern in `depop_search_agent`) for observability.

**Acceptance criteria:** With `BROWSER_USE_FORCE_FALLBACK=true`, buy pipeline still returns non-empty ranked results for a canned test query (may use deterministic mock data — document).

---

## Phase 4 — Sell pipeline depth (post-vision)

**Objective:** Maximize perceived quality of comps, pricing, and listing copy without blocking the Gemini teammate.

### 4.1 eBay sold comps

**Tasks:**

1. Review `ebay_sold_comps_agent` for consistency between Browser Use, httpx, and fallback.

2. Ensure `EbaySoldCompsOutput` always includes defensible `sample_size` and price spread when in fallback.

3. Add unit tests for edge cases: empty query, vision output with `Unknown` brand.

**Files:** `backend/agents/ebay_sold_comps_agent.py`, `tests/`.

---

### 4.2 Pricing agent

**Tasks:**

1. Validate `TrendData` / `VelocityData` are populated whenever comp dates/prices allow (`pricing_agent.py`, `trend_analysis.py`).

2. Ensure `pricing_confidence` reflects data quality (sample size, spread) for frontend display.

**Files:** `backend/agents/pricing_agent.py`, `backend/agents/trend_analysis.py`, `tests/test_trend_analysis.py`, `tests/test_pricing_agent_real.py`.

---

### 4.3 Depop listing agent

**Tasks:**

1. Confirm `draft_created`-style events if the frontend expects listing preview milestones (see `browser_use_events` and `API_CONTRACT.md`).

2. Align `DepopListingOutput.listing_preview` with what the mobile UI can render offline.

**Files:** `backend/agents/depop_listing_agent.py`, `backend/agents/browser_use_events.py`, `API_CONTRACT.md`.

---

## Phase 5 — Browser Use reliability and demo hardening

**Objective:** Repeatable demos on target hardware and hosting.

### 5.1 Profile and environment validation

**Tasks:**

1. Run `backend/browser_use_runtime_audit.py` (and `scripts/browser_use_runtime_audit.py` if duplicated — consider consolidating to avoid drift).

2. Document in `BrowserUse-Live-Validation.md` the **minimum** profile state for Depop listing and negotiation.

3. Add a `make verify-browser` target that runs audit + optional `--mode fallback` validation (fast CI) vs `--require-live` (manual pre-demo).

**Files:** `Makefile`, `BrowserUse-Live-Validation.md`, `README.md`.

---

### 5.2 Render / paid tier constraints

**Tasks:**

1. Confirm `render.yaml` installs Chromium via patchright as in README.

2. Document headed vs headless flags and env vars for production.

3. Define `BROWSER_USE_FORCE_FALLBACK=true` for Render free tier smoke, `false` for paid demo.

**Files:** `render.yaml`, `README.md`.

---

### 5.3 DOM drift playbook

**Tasks:**

1. For each Browser Use agent, maintain a short “last verified” note in `BrowserUse-Status.md` or agent module docstring.

2. On failure, ensure `browser_use_error` and `BrowserUseMetadata` surface enough for judges without leaking secrets.

---

## Phase 6 — Fetch.ai integration support (glue only)

**Objective:** Support the Fetch teammate without owning uAgent internals.

### 6.1 Configuration and feature flags

**Tasks:**

1. Add placeholder env vars to `.env.example` (no real secrets): e.g. `FETCH_ENABLED`, `AGENTVERSE_API_KEY`, per-agent seed names if required.

2. In `backend/config.py`, expose typed getters that return `None` when unset.

3. Optional: extend `GET /health` with `fetch_configured: bool` (never expose secret values).

---

### 6.2 Review gate

**Tasks:**

1. On each Fetch-related PR, verify:
   - `POST /task` still accepts `AgentTaskRequest` unchanged.
   - Local tests pass with `FETCH_ENABLED=false`.

---

### 6.3 Documentation

**Tasks:**

1. Link `FetchAI-Status.md` from this plan; ensure ASI:One verification steps are copy-paste ready.

2. Execute **`AGENTVERSE_IMPLEMENTATION_PLAN.md`** for Agentverse alignment: canonical slug/port/env table, local `make run-fetch-agents` runbook, doc fixes to `AGENTVERSE_SETUP.md`, and submission URL collection.

---

## Phase 7 — Deployment, observability, and operations

### 7.1 Staging URL and secrets matrix

**Tasks:**

1. Table: variable name, required for which feature, who owns rotation, where stored (Render dashboard, 1Password, etc.).

2. Document `INTERNAL_API_TOKEN` usage for `POST /internal/event/{session_id}`.

---

### 7.2 Logging

**Tasks:**

1. Standardize structured logs for: `session_id`, `pipeline`, `step`, `agent_slug`, `execution_mode`.

2. Avoid logging full PII from `original_input`; truncate image URLs if logged.

**Files:** `backend/orchestrator.py`, `backend/main.py`, agent base classes.

---

### 7.3 Rate limiting and abuse (stretch)

**Tasks:**

1. If public demo URL is shared, consider basic rate limits on `/sell/start` and `/buy/start` (e.g. `slowapi`) or API key header — product decision.

---

## 12. Testing strategy

### 12.1 Layers

| Layer | Scope | Tools |
|-------|--------|--------|
| Contract | `AGENT_INPUT_CONTRACTS`, `AGENT_OUTPUT_MODELS` | `tests/test_contracts_and_execution.py` |
| Orchestrator | Retries, failures, ordering | `tests/test_orchestrator_resilience.py`, `tests/test_pipelines.py` |
| Agents | Individual `build_output` with mocks | `tests/test_agents.py`, `tests/test_*_real.py` |
| HTTP | Main app routes | `TestClient` |
| Browser Use | Live vs fallback | `browser_use_validation.py`, marked optional in CI |

### 12.2 New tests required by this plan

1. **Vision pause/resume E2E** (TestClient + stream parsing): low confidence → `vision_low_confidence` → correct → `pipeline_complete`.

2. **Correction normalization**: invalid `corrected_item` → `422` or normalized output (explicit product choice).

3. **Parallel buy search** (if Phase 3 ships): ordering-agnostic assertions on final `ranking` input.

4. **Regression:** `AGENT_EXECUTION_MODE=http` smoke script (optional nightly): start `run_agents` + one pipeline.

---

## 13. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Frontend depends on strict SSE ordering | Medium | High | Document interleaved events after parallel search; UI keys off `step` |
| Gemini latency exceeds `AGENT_TIMEOUT_SECONDS` | Medium | High | Raise timeout for vision only, or async vision job (out of scope — then increase global timeout for demo) |
| Marketplace blocks automation mid-demo | High | Medium | Fallback paths + judge-facing narrative |
| Schema drift between mobile and backend | Medium | High | `API_CONTRACT.md` changelog + contract tests |
| Fetch registration fails in prod | Medium | Medium | Recorded video + Agentverse screenshots as backup demo |

---

## Appendix A — Canonical file map

| Path | Responsibility |
|------|----------------|
| `backend/main.py` | Routes, SSE, session lifecycle |
| `backend/orchestrator.py` | Pipelines, retries, events, resume |
| `backend/session.py` | In-memory state |
| `backend/schemas.py` | Pydantic contracts |
| `backend/config.py` | Env and agent table |
| `backend/agent_client.py` | Local vs HTTP dispatch |
| `backend/agents/registry.py` | Local agent registry |
| `backend/agents/base.py` | `BaseAgent`, per-agent FastAPI app factory |
| `backend/run_agents.py` | Multi-uvicorn launcher |
| `tests/conftest.py` | Shared fixtures |
| `API_CONTRACT.md` | Frontend contract |

---

## Appendix B — Environment variables

| Variable | Purpose |
|----------|---------|
| `AGENT_EXECUTION_MODE` | `local_functions` or `http` |
| `APP_BASE_URL` | URLs returned to client |
| `INTERNAL_API_TOKEN` | Internal event auth |
| `AGENT_TIMEOUT_SECONDS` | Per-agent wall clock |
| `BUY_AGENT_MAX_RETRIES` | Buy search retries |
| `BROWSER_USE_FORCE_FALLBACK` | Skip live Browser Use |
| `BROWSER_USE_PROFILE_ROOT` | Profile directory |
| `GOOGLE_API_KEY` | Gemini / Browser Use stacks as applicable |
| `EBAY_APP_ID`, `EBAY_CERT_ID` | eBay Browse API |

*(Extend table when Fetch vars land.)*

---

## Appendix C — SSE event catalog

Events observed from orchestration and agents (non-exhaustive for agent-emitted internal events):

| Event | Source | Notes |
|-------|--------|------|
| `pipeline_started` | Orchestrator | |
| `agent_started` | Orchestrator | |
| `agent_retrying` | Orchestrator | Buy search agents |
| `agent_error` | Orchestrator | |
| `agent_completed` | Orchestrator | |
| `pipeline_complete` | Orchestrator | |
| `pipeline_failed` | Orchestrator | Includes `partial_result` |
| `vision_low_confidence` | Orchestrator | Sell pause path |
| `pipeline_resumed` | Orchestrator | After `/sell/correct` |
| `search_method` | Search agents | Via internal event helper |
| `browser_use_fallback` | Various | Per `CLAUDE.md` / agent code |

**Note:** Agents may emit additional events through `POST /internal/event/{session_id}`; maintain a single list in `API_CONTRACT.md` as new events appear.

---

## Suggested execution order (summary)

1. **Phase 0** — Doc/code alignment (fast, reduces confusion).
2. **Phase 2** — Vision schema + pause/resume + normalization (unblocks Gemini + frontend UX).
3. **Phase 1** — Golden SSE examples and result payload docs (parallel with Phase 2).
4. **Phase 3** — Parallel buy searches if time permits (coordinate SSE expectations).
5. **Phases 4–5** — Depth + demo reliability.
6. **Phases 6–7** — Fetch glue + deploy/runbook.

---

*End of implementation plan. Update this document when phases complete or priorities change.*


# --- ARCHIVED FILE: JUDGING-PLAN.md ---

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


# --- ARCHIVED FILE: MERGE-DIFF-SUMMARY.md ---

# Merge Diff Summary: Eliot → Jay Branch

**Merge commit:** `6487173`  
**Parents:** `66ce6d1` (jay) ← `6cba084` (eliot)  
**Net change:** +1,374 insertions / −8,077 deletions across 81 files

---

## What Was Added (Eliot's Contributions)

### New Files

| File | Purpose |
|------|---------|
| `backend/fetch_runtime.py` | Core Fetch.ai runtime — defines `FetchAgentSpec` dataclass, `FETCH_AGENT_SPECS` registry (10 agents, ports 9201–9210), `run_fetch_query()`, and `format_fetch_response()` |
| `backend/fetch_agents/builder.py` | Builds `uAgents`-based chat agents from any registered slug. Handles `ChatMessage`/`ChatAcknowledgement` protocol, env-based seed loading, and local endpoint flag |
| `backend/fetch_agents/launch.py` | Entry point that builds and runs a single Fetch agent by slug from CLI args |
| `backend/fetch_agents/__init__.py` | Package init |
| `backend/run_fetch_agents.py` | Starts all 10 Fetch agent processes in parallel using `multiprocessing` |
| `tests/test_fetch_runtime.py` | 78-line test suite covering `FETCH_AGENT_SPECS` completeness, `run_fetch_query`, and `format_fetch_response` |
| `FETCH_INTEGRATION.md` | 439-line integration guide documenting the Fetch.ai agent architecture, setup, and usage |

### Modified Files

| File | Change |
|------|--------|
| `.env.example` | Replaced old `FETCH_ENABLED`/eBay keys with 10 per-agent seed env vars (`VISION_FETCH_AGENT_SEED`, etc.) and `FETCH_USE_LOCAL_ENDPOINT` |
| `.gitignore` | Expanded from 4 lines to 41 — added `.venv-fetch/`, `profiles/`, `playwright-report/`, IDE dirs, OS files, `.agents/` |
| `Makefile` | Added `run-fetch-agents` target |
| `backend/README.md` | Added Fetch.ai integration section |
| `backend/agents/ranking_agent.py` | Minor addition (3 lines) |
| `requirements.txt` | Added `uagents` and `uagents-core` dependencies |

---

## What Was Removed (Jay's Cleanup / Eliot Overwrote)

### Deleted Documentation Files
- `API_CONTRACT.md` — full REST + SSE API contract (287 lines)
- `BROWSER-USE-GAPS.md` — browser-use gap analysis (285 lines)
- `BROWSER-USE-SELL-CONFIRMATION-PLAN.md` (254 lines)
- `BROWSER-USE-SELL-IMPLEMENTATION-CHECKLIST.md` (224 lines)
- `BrowserUse-Deep-Implementation-Plan.md`, `BrowserUse-Execution-Strict.md`, `BrowserUse-Implementation-Strict.md`
- `IMPLEMENTATION-PLAN.md` (561 lines), `JAY-PLAN.md` (252 lines)

### Deleted Test Files (Browser-Use-Specific)
- `tests/test_browser_use_events.py`
- `tests/test_browser_use_progress_events.py` (405 lines)
- `tests/test_browser_use_runtime.py`
- `tests/test_browser_use_runtime_audit.py`
- `tests/test_browser_use_runtime_verifier.py`
- `tests/test_browser_use_support_additional.py`
- `tests/test_browser_use_validation_harness.py`
- `tests/test_sell_correct_endpoint.py`
- `tests/test_sell_listing_decision_endpoint.py` (159 lines)
- `tests/test_sell_listing_review_contracts.py`
- `tests/test_sell_listing_review_orchestration.py` (253 lines)
- `tests/test_sell_listing_review_result_contract.py`
- `tests/test_httpx_search_clients.py` (316 lines)
- `tests/test_trend_analysis.py` (170 lines)
- `tests/test_infrastructure.py` (108 lines)
- `tests/test_buy_decision_agents_real.py`

### Deleted Backend Files
- `backend/agents/httpx_clients.py` (188 lines)
- `backend/agents/trend_analysis.py` (119 lines)
- `backend/agents/browser_use_events.py` (47 lines)
- `backend/browser_use_runtime_audit.py` (261 lines)
- `backend/browser_use_validation.py` (522 lines)
- `scripts/browser_use_runtime_audit.py`, `scripts/browser_use_validation.py`, `scripts/setup_sessions.py`
- `render.yaml`

### Heavily Trimmed Backend Files
- `backend/orchestrator.py` — gutted from ~600 lines to ~20 (sell listing review loop removed)
- `backend/schemas.py` — stripped from ~200 lines to ~60 (many output models removed)
- `backend/main.py` — reduced by ~73 lines (sell listing review endpoints removed)
- `backend/agents/depop_listing_agent.py`, `depop_search_agent.py`, `ebay_search_agent.py`, `mercari_search_agent.py`, `offerup_search_agent.py`, `negotiation_agent.py` — all significantly reduced

---

## Summary

The merge brings in Eliot's **Fetch.ai / uAgents runtime** — a second execution layer alongside the existing `local_functions` and `http` modes. Each of the 10 pipeline agents can now be deployed as an autonomous `uAgent` on the Agentverse network with its own seed/port.

In exchange, a large body of **browser-use sell-confirmation loop** code (listing review, pause/resume, correction loop, associated tests and docs) was dropped from the jay branch — either intentionally cleaned up before the merge or overwritten by eliot's leaner branch state.


# --- ARCHIVED FILE: ORCHESTRATOR-IMPLEMENTATION-PLAN.md ---

# Orchestrator Implementation Plan (Handoff)

**Audience:** A coordinating agent or human lead slicing work to executors.  
**Repo:** DiamondHacks backend — FastAPI, in-memory sessions, SSE, ten agents, optional Fetch uAgents.  
**Baseline:** `make check` must stay green after each merge; default verification is `make install` then `make check`.

---

## 1. Ground truth (do not contradict)

| Fact | Detail |
|------|--------|
| **Product API** | FastAPI in `backend/main.py` — mobile SSE/HTTP path. **PRD / judging:** ASI:One is the orchestrator for the Agentverse story; FastAPI runs the **same** agent graph in-process for Expo. |
| **Pipelines** | `POST /sell/start`, `POST /buy/start`; progress via `GET /stream/{session_id}` (underscore SSE event names). |
| **Sell review** | Pauses at `listing_review_required`; user drives `POST /sell/listing-decision` (`confirm_submit` \| `revise` \| `abort`). Max **2** revisions; **15**-minute review window per pause (refreshed after each successful revise). |
| **Expiry** | Lazy checks on `/result`, `/stream`, `/sell/listing-decision` **plus** background sweep: `SELL_REVIEW_CLEANUP_INTERVAL` (default 60s). |
| **Agent execution** | `AGENT_EXECUTION_MODE=local_functions` (default) or `http` + `make run-agents`. |
| **Fetch** | Parallel layer: `make venv-fetch` + `make run-fetch-agents` (ports 9201–9210). `FETCH_ENABLED=true` routes orchestrator through Fetch adapter when testing that path. |
| **Contracts** | Pydantic models in `backend/schemas.py`; agent registry in `backend/agents/registry.py`. |

**Canonical references:** `AGENTS.md`, `CLAUDE.md`, `API_CONTRACT.md`, `FETCH_INTEGRATION.md`, `BrowserUse-Live-Validation.md`, `BACKEND-CODEBASE-PROBLEMS.md`, `IMPLEMENTATION-PLAN.md`.

---

## 2. Already implemented (automated; live validation still optional)

- Sell listing review loop, revision limit, deadline refresh, expiry (request + background).
- Fetch runtime bridge, parallel BUY search in Fetch chat path, no-results short-circuit.
- `GET /fetch-agents` manifest; health flags for Fetch / Agentverse key presence.
- Test coverage: sell review orchestration, listing-decision endpoint, result contract, background cleanup, fetch compatibility, contracts.

**Do not re-scope these unless a regression appears.**

---

## 3. Priority workstreams (recommended order)

Execute in phases; each phase should end with `make check` and a short changelog note in the PR or commit message.

### Phase A — Browser Use demo hardening (P0)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| A1 | Deterministic stop at sell listing **ready-to-submit** (not prompt-luck). | `browser_use_marketplaces.py`, `browser_use_support.py`, `BROWSER-USE-GAPS.md` | Live or harness: listing reaches `ready_for_confirmation` reliably; tests or harness scenario still pass with `BROWSER_USE_FORCE_FALLBACK=true`. |
| A2 | Replace placeholder listing screenshot with real capture (or schema-backed artifact). | `schemas.py` (Depop listing output), `browser_use_marketplaces.py` | Contract tests + at least one agent test assert non-placeholder behavior when mock provides bytes. |

**Dependency:** A1 before relying on A2 in demos.

### Phase B — Vision + schema truth (P0 / unblocks PRD + frontend)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| B1 | Real Gemini (or agreed) vision path for images — retire heuristic-only identification where product requires it. | `vision_agent.py`, config/env | `VisionAnalysisOutput` validates; pipeline uses real fields. |
| B2 | Align `VisionAnalysisOutput` with orchestrator/frontend (e.g. `confidence`, fields PRD promises). | `schemas.py`, `orchestrator.py` | No extra keys dropped by strict validation; low-confidence pause path testable. |
| B3 | Normalize `POST /sell/correct` payload → valid vision output (if not done). | `orchestrator.py`, `schemas.py`, tests | `tests/test_sell_correct_endpoint.py` (or equivalent) covers shape. |

See `IMPLEMENTATION-PLAN.md` Phase 2 for detailed subtasks.

### Phase C — Product depth (P1)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| C1 | Reduce synthetic fallback on default happy path (search, comps, pricing) where PRD demands real data. | `search_support.py`, `ebay_sold_comps_agent.py`, `pricing_agent.py` | Document behavior when keys missing; tests updated. |
| C2 | Unify pricing SSE/result fields with `PricingOutput` (`median_sold_price` vs `median_price`, etc.). | `orchestrator.py`, `schemas.py` | Contract + pipeline tests. |
| C3 | Negotiation: move beyond single template / small listing set (product-dependent). | `negotiation_agent.py` | Tests + safe demo behavior. |
| C4 | Docs: execution order (httpx → browser_use → fallback) consistent in `backend/README.md` and agent docstrings. | README, search agents | No “Browser Use first” drift. |

### Phase D — Reliability + SELL fallback (P2)

| ID | Task | Primary files | Acceptance |
|----|------|---------------|------------|
| D1 | SELL fallback listing path honors review loop (no silent bypass of human checkpoint). | `depop_listing_agent.py`, `test_pipelines.py` | Test asserts paused review when required. |
| D2 | Abort / cleanup semantics explicit in session result and events. | `orchestrator.py` | Tests for failure vs completed abort. |
| D3 | Deterministic temp file cleanup for remote image URLs in listing agent. | `depop_listing_agent.py` | Unit test or integration hook. |

### Phase E — Fetch + Agentverse (ops + glue)

| ID | Task | Notes |
|----|------|------|
| E1 | Mailbox registration and one end-to-end ASI:One smoke per agent (start with `depop_search_agent` per `FETCH_INTEGRATION.md`). | Mostly ops; code only if bridge gaps found. |
| E2 | Surface `execution_mode` / fallback reason in Fetch chat responses (optional P1 polish). | `fetch_runtime.py`, response formatting. |

### Phase F — Documentation (P3, can parallelize)

| ID | Task | File | Status |
|----|------|------|--------|
| F1 | PRD §5: **ASI:One as orchestrator** for Fetch/judging; FastAPI as mobile execution path for the same agents. | `PRD.md` | Done |
| F2 | PRD BUY search: match **code** (sequential in main pipeline vs parallel in Fetch path — state both accurately). | `PRD.md` | Done |
| F3 | Replace legacy **listing_ready** language with `listing_review_required` + `/sell/listing-decision`. | `PRD.md`, any stray docs | Done (PRD §7.3, §7.6) |
| F4 | Note **draft_created** as compatibility-only vs `listing_review_required`. | `PRD.md`, `API_CONTRACT.md` | Done |

### Phase G — Performance (optional; from `IMPLEMENTATION-PLAN.md` Phase 3)

- Parallelize four BUY search steps in **main** orchestrator only after contract change and frontend agreement on interleaved SSE ordering.

---

## 4. Workstream boundaries (avoid merge pain)

| Stream | Owns | Touch only if necessary |
|--------|------|-------------------------|
| Browser Use | `browser_use_*`, listing/search agents’ browser paths | Schemas — coordinate with contract stream |
| Vision / Gemini | `vision_agent.py`, vision schemas | Orchestrator pause/resume |
| Contracts / SSE | `schemas.py`, `orchestrator.py` event payloads | Frontend + `API_CONTRACT.md` |
| Fetch | `fetch_agents/`, `fetch_runtime.py`, `run_fetch_agents.py` | Core `/task` shape |
| Docs | `PRD.md`, `README.md`, `API_CONTRACT.md` | No behavior change without code PR |

---

## 5. Definition of done (demo / judging)

- [ ] `make check` green on main branch.
- [ ] SELL: vision → comps → pricing → Depop draft → **review** → submit/revise/abort path demonstrable (fallback or live).
- [ ] BUY: four searches → rank → negotiation path demonstrable.
- [ ] Browser Use sponsor story: at least one **live** flow documented in `BrowserUse-Live-Validation.md` with sign-off notes.
- [ ] Fetch: 10 agents registered; at least one **live** ASI:One or Agentverse proof captured (screenshot/log) per team process.
- [ ] `PRD.md` architecture section matches implementation (ASI:One as orchestrator for Agentverse + FastAPI as same-agent mobile path — no contradiction).

---

## 6. Out of scope for this plan (unless product changes)

- Frontend / Expo app implementation (consume `API_CONTRACT.md` + SSE).
- Production deploy hardening beyond existing `render.yaml` / README (track separately).
- Replacing in-memory sessions with durable storage.

---

## 7. Suggested first sprint for an executor pool

1. **A1** (deterministic listing checkpoint) + tests/harness update.  
2. **B2** + **B3** (vision schema + correction normalization) if Gemini lands in parallel.  
3. **F1–F4** (PRD doc fix) in a docs-only PR to unblock judges reading PRD.  
4. **E1** (one Fetch agent live) as ops parallel track.

---

*Generated for handoff. Update `BACKEND-CODEBASE-PROBLEMS.md` when P0/P1 items close.*


# --- ARCHIVED FILE: JAY-NEXT-STEPS.md ---

# Jay's Next Steps

**Scope:** Backend infrastructure only. Do NOT touch frontend, Fetch.ai integration, or Gemini Vision (those are other teammates' workstreams).

**Current state:** 192 tests passing. Core pipelines work end-to-end in fallback mode. Browser Use runtime wired up but requires warmed profiles + GOOGLE_API_KEY to run live.

---

## Task 1 — Fix ranking agent crash on empty results (CRITICAL)

**File:** `backend/agents/ranking_agent.py`

**Bug:** Lines 86–87 crash when all 4 buy-side search agents return zero results:
```python
top_choice = ranked_candidates[0]      # IndexError if empty
median_price = round(...) / len(candidates), 2)  # ZeroDivisionError if empty
```

**Fix:** Guard before both lines. If `ranked_candidates` is empty, return a graceful output:
```python
if not ranked_candidates:
    return {
        "agent": self.slug,
        "display_name": self.display_name,
        "summary": "No listings found across all platforms",
        "top_choice": None,   # but RankingOutput.top_choice is required — see below
        "candidate_count": 0,
        "ranked_listings": [],
        "median_price": 0.0,
    }
```

**Schema issue:** `RankingOutput.top_choice` is `RankedListing` (required, non-optional). Either:
- Make it `Optional[RankedListing]` in `backend/schemas.py` and update `NegotiationAgentInput` to handle `None`, OR
- Raise a clear `ValueError("No search results — cannot rank")` so the pipeline fails with `agent_error` rather than an unhandled crash

The `ValueError` approach is simpler and correct: if there are no candidates, the buy pipeline cannot meaningfully continue. Add a test that verifies this emits `agent_error` (not an unhandled exception).

**Acceptance criteria:** `make test` passes; a new test `test_ranking_agent_empty_candidates` exists.

---

## Task 2 — Add test for vision low-confidence resume flow

**File:** `tests/test_pipelines.py` (or `tests/test_sell_resume.py`)

**Gap:** The `POST /sell/correct` + `resume_sell_pipeline` path exists in code and was shipped, but test coverage is incomplete — there is no test that:
1. Starts a sell session with a low-confidence vision result (confidence < 0.70)
2. Verifies `vision_low_confidence` SSE event fires and pipeline pauses
3. Calls `POST /sell/correct` with a corrected item
4. Verifies the pipeline resumes and completes with `pipeline_complete`

**Acceptance criteria:** `make test` passes with the new test.

---

## Task 3 — Harden buy pipeline when search agents partially fail

**File:** `backend/orchestrator.py`

**Issue:** `_run_buy_search_parallel` uses `asyncio.gather` without `return_exceptions=True`. If one search agent raises (e.g. timeout), the entire gather raises and the other results are discarded. The buy pipeline then fails rather than proceeding with partial results.

**Fix:** Change gather to collect exceptions, then for any failed step inject an empty `SearchResultsOutput`:
```python
results = await asyncio.gather(*[run_one(slug, step) for slug, step in BUY_SEARCH_STEPS], return_exceptions=True)
# For each result: if exception, log agent_error event and substitute empty results
```

**Acceptance criteria:** `make test` passes; a new test verifies one failing search agent still allows ranking to run with partial results (and raises at ranking if all 4 fail).

---

## Manual steps (Jay only — not Codex)

In priority order:

1. **Create `.env`** — copy `.env.example`, fill in `GOOGLE_API_KEY` (from aistudio.google.com) and `INTERNAL_API_TOKEN`
2. **Warm browser profiles** — run `python -m backend.warm_profiles` after logging into Depop, eBay, OfferUp
3. **Spike httpx endpoints** — run the test in `TODO.md §2` to see which marketplaces respond to httpx
4. **Smoke test sell pipeline** — curl `/sell/start` + `/stream/{id}`, verify all 4 `agent_completed` events fire
5. **Smoke test buy pipeline** — verify all 4 search agents + ranking + negotiation complete
6. **Set up ngrok** — `brew install ngrok && ngrok http 8000`, give URL to frontend teammate
7. **Register eBay dev credentials** — `developer.ebay.com` → add `EBAY_APP_ID` + `EBAY_CERT_ID` to `.env`

---

## Codex task order

1. Task 1 (ranking agent crash) — ship immediately
2. Task 2 (sell resume test) — adds test coverage for shipped feature  
3. Task 3 (partial search failure hardening) — increases buy pipeline resilience

Each task must pass `make test` before the next one starts.


# --- ARCHIVED FILE: Backend-Test-Plan.md ---

# Backend Test Plan

## Key Risks To Validate First

- `SSE delivery breaks or stalls`: if the stream does not emit start, step, and completion events in order, the frontend demo will feel dead even when the backend is running.
- `Session state diverges from events`: `/result/{session_id}` and `/stream/{session_id}` must tell the same story.
- `Pipeline ordering regresses`: `SELL` and `BUY` both depend on strict step ordering.
- `Agent contract drift`: each agent must accept the same request envelope and return the same response shape.
- `Background task failure is invisible`: failed tasks must surface cleanly in both session state and SSE.
- `In-memory state edge cases`: bad session IDs, reconnects, duplicate requests, and process restarts need predictable behavior.
- `Fallback execution path breaks`: `AGENT_EXECUTION_MODE=local_functions` is the current default and must remain reliable.
- `Separate agent apps drift from in-process execution`: `/task` behavior should match whether the backend calls local functions or per-agent FastAPI apps.

## Purpose

This document defines a comprehensive set of tests to validate the backend scaffold for Jay's role. It is designed to answer three questions:

1. Does each individual step work?
2. Does each step produce the right shape of output for the next step?
3. Does the whole system behave reliably under demo conditions?

## Scope

This plan covers:

- FastAPI backend endpoints
- In-memory session lifecycle
- SSE streaming behavior
- SELL pipeline orchestration
- BUY pipeline orchestration
- Each of the 10 agent scaffolds
- Internal event routing
- Local multi-process agent startup
- Render-readiness checks

This plan does not yet cover:

- Real Browser Use flows
- Real Fetch.ai Agentverse registration
- Real Gemini output quality
- End-to-end mobile frontend rendering

## Environments

### Local Backend Only

- `AGENT_EXECUTION_MODE=local_functions`
- Run `uvicorn backend.main:app --reload`
- Use this mode for the fastest API and orchestration validation

### Local Multi-Process

- `AGENT_EXECUTION_MODE=http`
- Run `python -m backend.run_agents`
- Run `uvicorn backend.main:app --reload`
- Use this mode to verify that per-agent `/task` apps behave correctly over HTTP

### Render Smoke

- Deploy backend only
- Keep `AGENT_EXECUTION_MODE=local_functions`
- Use this mode to verify deployment and demo survivability before introducing more moving parts

## Core Contracts To Freeze

Before adding real logic, these contracts should be treated as stable and regression-tested:

- `POST /sell/start`
- `POST /buy/start`
- `GET /stream/{session_id}`
- `GET /result/{session_id}`
- `POST /internal/event/{session_id}`
- `POST /task` on every agent app
- Session event names:
  - `pipeline.started`
  - `agent.started`
  - `agent.completed`
  - `pipeline.completed`
  - `pipeline.failed`

## Test Data

### SELL Input Fixture

```json
{
  "user_id": "demo-user-1",
  "input": {
    "image_urls": ["https://example.com/shirt.jpg"],
    "notes": "Vintage Nike tee"
  },
  "metadata": {
    "source": "manual-test"
  }
}
```

### BUY Input Fixture

```json
{
  "user_id": "demo-user-2",
  "input": {
    "query": "Nike vintage tee size M",
    "budget": 45,
    "target_platforms": ["depop", "ebay", "mercari", "offerup"]
  },
  "metadata": {
    "source": "manual-test"
  }
}
```

## Test Matrix

### 1. Boot And Health Checks

#### T1. Backend health endpoint

- Goal: confirm the API process boots
- Setup: run `uvicorn backend.main:app --reload`
- Action: call `GET /health`
- Expected:
  - status code `200`
  - body contains `{"status":"ok"}`
- Failure signals:
  - import error on boot
  - non-200 response
  - malformed JSON

#### T2. Every agent app health endpoint

- Goal: confirm all 10 agent processes boot independently
- Setup: run `python -m backend.run_agents`
- Action: call `GET /health` on ports `9101` through `9110`
- Expected:
  - each returns `200`
  - body includes `status=ok`
  - body includes the correct `agent` slug
- Failure signals:
  - missing process
  - wrong agent slug on a port
  - port collision

### 2. Session Lifecycle

#### T3. SELL start creates a session

- Goal: confirm session creation contract
- Action: call `POST /sell/start` with the SELL fixture
- Expected:
  - status code `200`
  - response contains:
    - `session_id`
    - `pipeline = sell`
    - `status = queued`
    - usable `stream_url`
    - usable `result_url`
- Follow-up:
  - call `GET /result/{session_id}`
- Expected follow-up:
  - session exists
  - `pipeline = sell`
  - `status` becomes `running` or `completed`

#### T4. BUY start creates a session

- Goal: confirm BUY session creation contract
- Action: call `POST /buy/start` with the BUY fixture
- Expected:
  - same guarantees as `T3`, but `pipeline = buy`

#### T5. Unknown session returns 404

- Goal: confirm clean handling of bad IDs
- Action:
  - call `GET /result/not-a-real-session`
  - call `GET /stream/not-a-real-session`
- Expected:
  - both return `404`
  - error payload is clear and stable

### 3. SSE Behavior

#### T6. SELL stream emits the full event sequence

- Goal: confirm frontend-visible event flow for SELL
- Setup:
  - create a SELL session
  - connect to `GET /stream/{session_id}`
- Expected event order:
  1. `pipeline.started`
  2. `agent.started` for `vision_analysis`
  3. `agent.completed` for `vision_analysis`
  4. `agent.started` for `ebay_sold_comps`
  5. `agent.completed` for `ebay_sold_comps`
  6. `agent.started` for `pricing`
  7. `agent.completed` for `pricing`
  8. `agent.started` for `depop_listing`
  9. `agent.completed` for `depop_listing`
  10. `pipeline.completed`
- Validate:
  - each event includes the same `session_id`
  - timestamps are present
  - step names match orchestration order
  - final event terminates the stream cleanly

#### T7. BUY stream emits the full event sequence

- Goal: confirm frontend-visible event flow for BUY
- Expected event order:
  1. `pipeline.started`
  2. `agent.started` for `depop_search`
  3. `agent.completed` for `depop_search`
  4. `agent.started` for `ebay_search`
  5. `agent.completed` for `ebay_search`
  6. `agent.started` for `mercari_search`
  7. `agent.completed` for `mercari_search`
  8. `agent.started` for `offerup_search`
  9. `agent.completed` for `offerup_search`
  10. `agent.started` for `ranking`
  11. `agent.completed` for `ranking`
  12. `agent.started` for `negotiation`
  13. `agent.completed` for `negotiation`
  14. `pipeline.completed`

#### T8. Stream replay includes prior events

- Goal: confirm reconnect behavior after partial progress
- Setup:
  - start a session
  - let at least two events happen
  - connect to the stream after progress has already begun
- Expected:
  - existing session events are replayed first
  - new events continue after replay
- Failure signal:
  - reconnecting users miss already-emitted steps

### 4. Result Integrity

#### T9. Completed SELL result matches streamed steps

- Goal: confirm no divergence between SSE and stored state
- Action:
  - complete a SELL run
  - compare `GET /result/{session_id}` against the streamed events
- Expected:
  - `status = completed`
  - `result.pipeline = sell`
  - `result.outputs` contains:
    - `vision_analysis`
    - `ebay_sold_comps`
    - `pricing`
    - `depop_listing`
  - `events` includes the same step names and order as the stream

#### T10. Completed BUY result matches streamed steps

- Goal: same integrity check for BUY
- Expected:
  - `status = completed`
  - `result.pipeline = buy`
  - `result.outputs` contains:
    - `depop_search`
    - `ebay_search`
    - `mercari_search`
    - `offerup_search`
    - `ranking`
    - `negotiation`

### 5. Individual Agent Contract Tests

Run the following tests against each agent app and, separately, against the in-process local registry path.

#### T11. Agent accepts the standard task envelope

- Goal: confirm request shape consistency
- Action: `POST /task` with:

```json
{
  "session_id": "test-session",
  "pipeline": "sell",
  "step": "test-step",
  "input": {
    "sample": true
  },
  "context": {
    "source": "contract-test"
  }
}
```

- Expected:
  - status code `200`
  - response contains:
    - `session_id`
    - `step`
    - `status`
    - `output`

#### T12. Agent returns its correct identity

- Goal: catch copy-paste mistakes between scaffolds
- Expected:
  - `output.agent` matches the app being called
  - `output.display_name` matches the intended agent name

#### T13. Agent completes without unexpected fields missing

- Goal: confirm minimum downstream-safe output
- Expected:
  - `status = completed`
  - `output.summary` exists
  - output shape is a JSON object, not a list or string

#### Agent-Specific Efficacy Checks

##### T14. Vision Agent

- Validate:
  - returns `detected_item`
  - returns category-like metadata
  - output is useful as resale-identification input

##### T15. eBay Sold Comps Agent

- Validate:
  - returns sold-price summary
  - returns sample size or equivalent confidence indicator
  - output is usable by pricing logic

##### T16. Pricing Agent

- Validate:
  - returns a proposed list price
  - returns profit or margin signal
  - output is usable by listing generation

##### T17. Depop Listing Agent

- Validate:
  - returns listing title
  - returns listing description
  - output is usable by the frontend listing review flow

##### T18. Depop Search Agent

- Validate:
  - returns a `results` array
  - each result looks like a listing candidate

##### T19. eBay Search Agent

- Validate:
  - same expectations as the Depop search agent

##### T20. Mercari Search Agent

- Validate:
  - same expectations as the Depop search agent

##### T21. OfferUp Search Agent

- Validate:
  - same expectations as the Depop search agent

##### T22. Ranking Agent

- Validate:
  - returns a top choice
  - returns candidate count or ranking metadata
  - output is usable by negotiation logic

##### T23. Negotiation Agent

- Validate:
  - returns at least one message or offer payload
  - output is usable by a messaging or offer-sending step

### 6. Orchestration Behavior

#### T24. SELL executes in strict order

- Goal: confirm no out-of-order execution
- Method:
  - inspect event order from the stream
  - confirm the next step does not start before the prior step completes
- Expected:
  - exactly one active step at a time

#### T25. BUY executes in strict order

- Goal: same ordering guarantee for BUY
- Expected:
  - ranking does not start before all search agents complete
  - negotiation does not start before ranking completes

#### T26. Previous outputs are passed forward

- Goal: confirm step chaining
- Method:
  - instrument or inspect agent input in a test harness
  - verify `previous_outputs` grows as the pipeline progresses
- Expected:
  - each later step receives all earlier outputs in its input envelope

### 7. Error Handling

#### T27. Forced agent failure marks the session failed

- Goal: confirm failure visibility
- Setup:
  - temporarily modify one agent to return `status = failed`
- Expected:
  - stream emits `pipeline.failed`
  - `/result/{session_id}` shows `status = failed`
  - `/result/{session_id}` includes a meaningful `error`

#### T28. Stream closes on terminal failure

- Goal: prevent hanging frontend subscriptions
- Expected:
  - after `pipeline.failed`, the stream ends cleanly

#### T29. Invalid internal token is rejected

- Goal: verify internal event endpoint protection
- Action:
  - call `POST /internal/event/{session_id}` with no token
  - call with a bad token
- Expected:
  - both return `401`

#### T30. Valid internal event is appended to session history

- Goal: verify internal event routing
- Action:
  - call `POST /internal/event/{session_id}` with the correct `x-internal-token`
- Expected:
  - response is accepted
  - event appears in session history
  - if a stream is connected, the event is emitted live

### 8. Execution Mode Parity

#### T31. Local function mode works end-to-end

- Goal: protect the default demo path
- Setup:
  - `AGENT_EXECUTION_MODE=local_functions`
- Expected:
  - full SELL and BUY flows complete without running `backend.run_agents`

#### T32. HTTP mode works end-to-end

- Goal: protect future distributed execution
- Setup:
  - `AGENT_EXECUTION_MODE=http`
  - run `python -m backend.run_agents`
- Expected:
  - full SELL and BUY flows complete through HTTP `/task` calls

#### T33. Output parity across execution modes

- Goal: ensure the same agent logic is exposed both ways
- Method:
  - run the same input through both modes
  - compare response shapes
- Expected:
  - same field names
  - same status values
  - materially equivalent outputs

### 9. Concurrency And Stability

#### T34. Two sessions can run concurrently

- Goal: catch shared-state bugs
- Action:
  - start two SELL sessions, or one SELL and one BUY, nearly simultaneously
- Expected:
  - both complete
  - events do not leak between session IDs
  - result data stays isolated

#### T35. Multiple stream subscribers can attach to one session

- Goal: validate frontend reconnect or multi-observer behavior
- Action:
  - connect two stream clients to the same session
- Expected:
  - both receive the same event sequence

#### T36. Process restart behavior is explicit

- Goal: document the in-memory state limitation
- Action:
  - create a session
  - restart the backend process
  - request the same session
- Expected:
  - session is gone
  - behavior is understood and documented as an intentional current limitation

### 10. Deployment Readiness

#### T37. `start.sh` launches the app successfully

- Goal: validate deployment entrypoint
- Action:
  - run `./start.sh`
- Expected:
  - server boots with no missing-module errors

#### T38. Render config is internally consistent

- Goal: catch deployment configuration drift early
- Validate:
  - `render.yaml` references `requirements.txt`
  - `render.yaml` uses `./start.sh`
  - `APP_PORT` and `APP_BASE_URL` assumptions are coherent

## Suggested Automation Split

### Priority 1: Immediate Automated Tests

- Health endpoints
- Session creation
- Unknown session 404s
- SELL event order
- BUY event order
- Session/result integrity
- Internal token rejection
- Internal event acceptance
- Local function end-to-end flow

### Priority 2: Next Automated Tests

- HTTP execution mode end-to-end flow
- Per-agent `/task` contract tests
- Concurrent sessions
- Multi-subscriber SSE behavior
- Forced failure propagation

### Priority 3: Manual Demo Rehearsal Tests

- Full SELL run while watching live SSE output
- Full BUY run while watching live SSE output
- Repeat runs back-to-back
- Restart/recovery expectations
- Hosted Render smoke run

## Pass Criteria

The scaffold should be considered stable enough for teammate integration when all of the following are true:

- All health checks pass
- SELL and BUY both complete in local function mode
- SSE events arrive in the correct order
- `/result/{session_id}` matches the streamed execution history
- All 10 agents pass the standard `/task` contract test
- Invalid session and invalid token cases fail cleanly
- At least one concurrent-session test passes

## Failure Triage Guide

If a test fails, classify it immediately:

- `Contract failure`: wrong schema, missing field, bad status code
- `Ordering failure`: steps execute out of order
- `State failure`: session result and event history disagree
- `Transport failure`: SSE or HTTP call path breaks
- `Deployment failure`: boot, env, or start command issues
- `Agent logic failure`: step returns unusable output

This classification matters because the highest-priority fixes should be contract and transport issues first, then ordering and state issues, then agent logic quality.

## Recommended Next Step

Turn the Priority 1 section into actual automated tests first. That gives the team a fast safety net before real Browser Use and AI logic start changing the scaffold.


# --- ARCHIVED FILE: UI_REQUIREMENTS.md ---

# UI Requirements

## Overview

A mobile marketplace agent app where users set up automated buy/sell agents across multiple platforms. The UI should feel polished, professional, and data-forward — purpose-built for a power user who wants to monitor and manage deals at a glance.

---

## Design System

### Style
**Vibrant & Block-based** — bold, energetic, high color contrast, geometric shapes, modern. Every screen should feel intentional and structured, not cluttered.

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#7C3AED` | Primary actions, active states, key accents |
| `--color-on-primary` | `#FFFFFF` | Text/icons on primary backgrounds |
| `--color-secondary` | `#A78BFA` | Secondary UI elements, subtle highlights |
| `--color-accent` | `#16A34A` | CTAs, success states, deal-closed indicators |
| `--color-background` | `#FAF5FF` | Page backgrounds (light mode) |
| `--color-foreground` | `#4C1D95` | Primary text |
| `--color-muted` | `#ECEEF9` | Card backgrounds, dividers |
| `--color-border` | `#DDD6FE` | Borders, separators |
| `--color-destructive` | `#DC2626` | Errors, destructive actions |

Dark mode variants must be defined separately — do not invert light mode values.

### Typography
**Font:** Inter (all weights)
- Display/Headings: Inter 700, 32px+
- Section headers: Inter 600, 18–24px
- Body: Inter 400, 16px, line-height 1.5
- Labels/captions: Inter 500, 12–14px
- Numeric data (prices, counts): tabular figures to prevent layout shift

### Spacing
Use a strict 4/8pt spacing system. Common values: 4, 8, 12, 16, 24, 32, 48px.

### Icons
Use a single consistent SVG icon set (e.g. Lucide). No emojis as icons. All icon-only buttons must have an `aria-label`. Icon size: 20–24pt standard, 16pt small.

### Touch Targets
All tappable elements minimum 44×44pt. Use `hitSlop` where visual size is smaller.

### Animation
Micro-interactions: 150–300ms. Use `transform`/`opacity` only (no width/height animation). Respect `prefers-reduced-motion`. Exit animations ~60–70% of enter duration.

---

## Pages

---

### 1. Home Page

The main dashboard. Gives the user an immediate read on all active buying and selling agents.

#### Header Bar
- App name/logo on the left
- Settings icon (gear, SVG) on the right — tapping navigates to the Settings page
- Visible pressed state on the settings icon (opacity or scale 0.9)

#### Layout
- Two stacked sections: **Buying** (top) and **Selling** (bottom)
- Each section has a section header ("Buying" / "Selling") in Inter 600, 18px
- Horizontal scroll grid of cards within each section (or 2-column grid if screen width allows)
- Sections are visually separated with a 32px gap or a subtle divider

#### Item Card (Buy or Sell)
Each card is a solid block with rounded corners (12–16px radius), subtle shadow, and `--color-muted` background.

Contents:
- Item image (square thumbnail, top of card) or a placeholder with item initial
- Item name — Inter 600, 16px
- Target price or price range — Inter 700, tabular figures, accent-colored
- Status badge — pill shape: green (`--color-accent`) for Active, gray for Paused
- Row of small platform icons (SVG) at the bottom of the card showing which platforms it's active on
- Entire card is tappable → navigates to Item Detail page
- Pressed state: scale to 0.97, 150ms ease-out

#### Add New Card
- Same size and shape as item cards
- Centered `+` icon (24pt, `--color-primary`) with "Add New" label below
- Dashed border in `--color-border`
- Tapping opens the new item creation flow

#### Empty State (no items yet)
- If a section has no items, show only the Add New card plus a short helper text: "No active agents. Tap + to get started."

---

### 2. Item Detail Page

Opened when a user taps a buy or sell card. Full context on one item.

#### Header Bar
- Back arrow (left) — tapping returns to Home, preserving scroll position
- Item name as title (truncate with ellipsis if too long)
- Status toggle (Active / Paused) — pill toggle, right side of header

#### Section: Item Overview
- Item image (full-width or large square, top of page)
- Item name — Inter 700, 24px
- Description — Inter 400, 16px, line-height 1.6
- Condition label (e.g. "Used – Good") — muted text, 14px
- Quantity — "x3 units" or "Buying up to 2"

#### Section: Item Settings
Presented as a card-grouped settings list (similar to iOS Settings rows). Each row has a label on the left and a value/control on the right.

| Setting | Control Type |
|---------|-------------|
| Target Price | Editable text field (numeric keyboard) |
| Min Acceptable Price | Editable text field |
| Max Acceptable Price | Editable text field |
| Auto-Accept Threshold | Editable text field |
| Active Platforms | Multi-select toggle row (platform icons + label) |
| Negotiation Style | Segmented control: Aggressive / Moderate / Passive |
| Reply Tone | Dropdown or segmented: Professional / Casual / Firm |
| Auto-Relist | Toggle switch |
| Schedule Start | Date picker row |
| Schedule End | Date picker row |

Validation: show error inline below the field on blur. Required fields marked with a subtle asterisk. Numeric inputs use `inputmode="numeric"`.

#### Section: Market Overview
Per-platform cards in a horizontal scroll or stacked list. Each card shows:
- Platform name + SVG icon
- Current market price (large, tabular Inter 700)
- Volume / active listing count
- A subtle trend indicator (up/down arrow + % change) if available

#### Section: Active Conversations
List of people the agent is currently talking to, grouped by platform with a platform header row.

Each conversation row:
- Platform icon (16pt)
- Username/handle — Inter 500, 15px
- Last message preview — truncated to 1 line, muted text
- Timestamp — right-aligned, muted, 12px
- Unread badge (dot or count) if there are new messages

Tapping a row navigates to the Chat Log page.

Empty state: "No active conversations yet."

---

### 3. Chat Log Page

A read-only view of the conversation between the agent and one counterparty.

#### Header Bar
- Back arrow → returns to Item Detail, restoring scroll position
- Two-line title: item name (top, smaller) + platform + username (bottom, bold)

#### Chat Log
- Chronological message list, oldest at top, newest at bottom
- **Agent messages** (our side): right-aligned bubble, `--color-primary` background, white text
- **Counterparty messages**: left-aligned bubble, `--color-muted` background, `--color-foreground` text
- Timestamp below each message (or grouped by date with a centered date chip)
- Bubble corner radius: 16px, with the "tail" corner 4px on the sending side
- No compose or reply area — this is a log only
- System events (e.g. "Offer sent: $45", "Listing marked sold") shown as centered pills in muted style

#### Empty State
"No messages yet." centered in the log area.

---

### 4. Settings Page

App-wide settings. Must look complete and professional — not everything needs to be fully wired up, but it should feel like a real, polished product.

Navigation: accessible from the Home Page header settings icon. Uses a standard back arrow to return.

---

#### Appearance
| Setting | Control |
|---------|---------|
| Theme | Segmented control: Light / Dark / System Default |

---

#### Account
| Setting | Control |
|---------|---------|
| Profile photo | Tappable avatar with "Edit" overlay |
| Display name | Editable text row |
| Email address | Editable text row |

---

#### Platforms
Section header: "Connected Platforms"

For each supported marketplace (eBay, Facebook Marketplace, Craigslist, OfferUp, Depop, etc.):
- Platform logo/icon (SVG, 24pt)
- Platform name — Inter 500
- Connection status badge: "Connected" (green) or "Not Connected" (muted)
- If connected: account username shown in muted text below
- Connect / Disconnect button on the right (text button or chevron that opens an auth flow)
- API key status indicator where applicable (green dot = valid, red dot = expired/missing)

---

#### Agent Behavior
Section header: "Global Defaults" with a subheading: "These apply to all agents unless overridden per item."

| Setting | Control |
|---------|---------|
| Auto-reply | Toggle switch |
| Response delay | Stepper or dropdown: Instant / 1 min / 5 min / 15 min / 1 hr |
| Default negotiation style | Segmented: Aggressive / Moderate / Passive |

---

#### Notifications
Toggle rows, each with an icon (SVG), label, and toggle switch on the right:

| Notification | Default |
|---|---|
| New message received | On |
| Price drop detected | On |
| Deal closed | On |
| Listing expired | Off |

---

#### Usage
Displayed as a 2×2 stats grid. Each cell:
- Large number — Inter 700, 28px, `--color-primary`
- Label below — Inter 400, 13px, muted

| Stat | Label |
|------|-------|
| Active listings count | "Active Listings" |
| Messages this month | "Messages This Month" |
| Deals closed | "Deals Closed" |
| API calls used | "API Usage" |

---

### 5. Master Agent Button (Persistent)

A floating action button (FAB) visible on all primary screens (Home, Item Detail, Settings) that opens the `resale_copilot_agent` on ASI:One in a new browser tab. This gives judges and users a direct line to the master Fetch.ai agent without navigating away from the app.

#### Placement
- Fixed position: bottom-right corner, 24px from the right edge and 24px above the bottom safe area / nav bar
- Layered above all other content (`z-index` above cards and lists, below modals/dialogs)
- Does not obscure primary CTAs — if a screen has a bottom action bar, the FAB sits above it

#### Visual Design
- Circular button, 56×56px
- Background: `--color-primary` (`#7C3AED`)
- Icon: Fetch.ai logo SVG or a chat/agent SVG (20×20px, white) — centered
- Label tooltip: "Chat with your AI agent" — shown on long-press (mobile) or hover (web), 300ms delay
- Shadow: `0 4px 12px rgba(124, 58, 237, 0.4)` — elevated feel
- Pressed state: scale to 0.93, 150ms ease-out, shadow collapses

#### Behavior
- Tapping opens `https://asi1.ai/chat?agent=<RESALE_COPILOT_AGENT_ADDRESS>` in a new tab
- The agent address is a static config value — hardcoded from the stable `agent1q...` address generated by `RESALE_COPILOT_AGENT_SEED`
- No loading state needed — it's just an external link

#### Accessibility
- `aria-label="Chat with AI agent on ASI:One"`
- Keyboard focusable, `role="link"` or `role="button"` depending on implementation
- Must pass 4.5:1 contrast for the icon against `--color-primary`

---

## General UX Rules

- **Back navigation** always restores the previous scroll position and any open filters/state.
- **Loading states**: show a skeleton screen (shimmer) for any content that takes >300ms to load. Never show a blank screen.
- **Destructive actions** (archive, delete agent, disconnect platform) require a confirmation dialog before executing. Use `--color-destructive` for the confirm button.
- **Disabled controls** use 40% opacity + `cursor: not-allowed` (web) or non-interactive semantics (native). They must still be visually distinguishable.
- **Error messages** appear inline near the relevant field, state the cause, and suggest a fix. Never show a generic "Something went wrong."
- **Empty states** always include a short explanation and a clear action to resolve them.
- **All interactive elements** have a visible pressed/hover state. Transitions: 150–300ms ease-out.
- **Contrast**: primary text ≥4.5:1, secondary/muted text ≥3:1, in both light and dark modes.
- **Safe areas**: no interactive UI behind the notch, status bar, or gesture indicator bar.