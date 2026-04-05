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
