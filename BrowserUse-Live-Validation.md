# Browser Use Live Validation Checklist

Use this checklist after the backend test suite is green and before any demo that depends on live Browser Use execution.

## Start Services

Run the backend in one terminal and keep it up while validating:

```bash
make run
```

If you also need the Fetch path for the same demo window, start it in a second terminal:

```bash
make run-fetch-agents
```

Expected ports:

- FastAPI backend: `8000`
- Per-agent FastAPI apps: `9101-9110`
- Fetch agents: `9201-9210`

## Preconditions

- `AGENT_EXECUTION_MODE=local_functions`.
- `INTERNAL_API_TOKEN` is non-default.
- `GOOGLE_API_KEY` is set.
- Chromium is installed through `python -m patchright install chromium`.
- Warmed profiles exist under `profiles/depop`, `profiles/ebay`, `profiles/mercari`, and `profiles/offerup` as needed.
- `BROWSER_USE_PROFILE_ROOT=profiles` unless you intentionally store profiles elsewhere.
- `BROWSER_USE_FORCE_FALLBACK=false`.
- Runtime audit passes:
  - `./.venv/bin/python -m backend.browser_use_runtime_audit --require-live`
- Harness smoke run passes for the target flow:
  - `./.venv/bin/python -m backend.browser_use_validation --group buy_search --require-live`

## BUY Flow

1. Run `depop_search`, `ebay_search`, `mercari_search`, and `offerup_search` through the validation harness.
2. Confirm each result shows `execution_mode=browser_use` when live credentials and profiles are present.
3. Confirm each live result includes real titles, prices, and URLs, not fabricated fallback listings.
4. Run `ranking_agent` against the same query if you want the BUY chain end-to-end.
5. Run `negotiation` with a safe test listing or sandbox account.
6. Confirm:
   - `offer_prepared` appears for each candidate
   - `offer_sent` appears only after a successful browser action
   - `conversation_url` is captured when the platform exposes one

## SELL Flow

1. Run `ebay_sold_comps` and confirm the output is `execution_mode=browser_use`.
2. Run `depop_listing` against a warmed Depop profile.
3. Confirm the session pauses at the listing review checkpoint with:
   - `status=paused`
   - `sell_listing_review.state=ready_for_confirmation`
   - `listing_review_required` in the session history
4. Confirm the agent still emits `draft_created` for compatibility, but treat `listing_review_required` as the authoritative review-loop event.
5. Exercise the review loop end-to-end:
   - send `confirm_submit` and confirm `listing_submitted` plus `pipeline_complete`
   - send `revise` with text and confirm `listing_revision_requested`, `listing_revision_applied`, and a return to `listing_review_required`
   - send `abort` and confirm `listing_aborted` plus `pipeline_complete`
6. Verify the draft is populated but not published until `confirm_submit` is sent.
7. Verify the backend still emits `draft_created` for compatibility, but treat `listing_review_required` as the authoritative operator checkpoint.

## SELL Live Validation — Step-by-Step

Use `APP_BASE_URL` (default `http://localhost:8000`). Replace `SESSION_ID` with the `session_id` from `POST /sell/start`. Watch events on `GET /stream/{SESSION_ID}` or inspect `GET /result/{SESSION_ID}` after each step.

Constants (from `backend/orchestrator.py`): review window **15 minutes** (`SELL_LISTING_REVIEW_TIMEOUT_MINUTES`); max **2** revisions (`SELL_LISTING_MAX_REVISIONS`).

### 1. Prepare listing

```bash
curl -sS -X POST "$APP_BASE_URL/sell/start" \
  -H "Content-Type: application/json" \
  -d '{"input":{"image_urls":["https://example.com/item.jpg"],"notes":"Test item"}}' | jq .
```

**SSE (order may interleave agent steps):** `pipeline_started` → per-step `agent_started` / `agent_completed` through `depop_listing` → **`listing_review_required`**. `draft_created` may appear for backward compatibility; treat **`listing_review_required`** as the checkpoint.

**`GET /result/{SESSION_ID}` assertions:**

- `status` = `"paused"`
- `sell_listing_review.state` = `"ready_for_confirmation"`
- `sell_listing_review.deadline_at` is ~15 minutes after `sell_listing_review.paused_at` (ISO timestamps)
- `result.outputs.depop_listing.ready_for_confirmation` = `true`
- `result.outputs.depop_listing.listing_status` = `"ready_for_confirmation"`

### 2. Revise once

```bash
curl -sS -X POST "$APP_BASE_URL/sell/listing-decision" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"decision\":\"revise\",\"revision_instructions\":\"Lower the price by five dollars\"}" | jq .
```

**SSE sequence:**

1. `listing_decision_received` — `data.decision` = `"revise"`
2. `pipeline_resumed` — `data.reason` = `"listing_revision_requested"`
3. `listing_revision_requested` — includes `revision_instructions`, `revision_count` (e.g. `1`)
4. `listing_revision_applied` — updated listing `output`, `revision_count`
5. `listing_review_required` — fresh `review_state` (new `paused_at` / `deadline_at`)

**`GET /result/{SESSION_ID}`:** `status` = `"paused"` again; `sell_listing_review.revision_count` = `1`; **`deadline_at` must differ** from the pre-revision value (window refreshed).

A **third** `revise` when `revision_count` is already `2` returns **409** after `listing_revision_limit_reached` and `pipeline_failed`.

### 3. Confirm submit

```bash
curl -sS -X POST "$APP_BASE_URL/sell/listing-decision" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"decision\":\"confirm_submit\"}" | jq .
```

**SSE:** `listing_decision_received` → `pipeline_resumed` → `listing_submission_approved` → `listing_submit_requested` → on success `listing_submitted` → `pipeline_complete`; on failure `listing_submission_failed` → `pipeline_failed`.

**`GET /result/{SESSION_ID}`:** success → `status` = `"completed"`, `sell_listing_review` = `null`; failure → `status` = `"failed"`, `error` set.

### 4. Abort path

```bash
curl -sS -X POST "$APP_BASE_URL/sell/listing-decision" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"decision\":\"abort\"}" | jq .
```

**SSE:** `listing_decision_received` → `listing_submission_aborted` → `listing_abort_requested` → `listing_aborted` → `pipeline_complete`.

**Result:** `status` = `"completed"`, `sell_listing_review` = `null`, `result.outputs.depop_listing.listing_status` = `"aborted"`.

### 5. Expiry path

After `deadline_at` (UTC) passes, the session is failed with the same events as a timeout decision:

- `listing_review_cleanup_completed` or `listing_review_cleanup_failed`
- `listing_review_expired`
- `pipeline_failed`

**`GET /result/{SESSION_ID}`:** `status` = `"failed"`, `error` = `"sell_listing_review_timeout"`, `sell_listing_review` = `null`, `result.outputs.depop_listing.listing_status` = `"expired"`.

**Triggers:** `GET /result/{session_id}`, `GET /stream/{session_id}` (including SSE keepalive loop, ~15s), `POST /sell/listing-decision`, and a **background sweep** every `SELL_REVIEW_CLEANUP_INTERVAL` seconds (default **60**) so abandoned sessions do not stay paused forever with no client.

### 6. HTTP error edge cases

| Case | Response |
|------|----------|
| `POST /sell/listing-decision` when not paused for review | **409** — session not awaiting a sell listing decision |
| `decision: "revise"` with missing/blank `revision_instructions` | **422** validation error |
| `decision: "revise"` at revision limit | **409** after cleanup events and `pipeline_failed` |

**Source of truth:** `backend/orchestrator.py` (`handle_sell_listing_decision`, `fail_sell_listing_review`, `expire_sell_listing_review_if_needed`); tests: `tests/test_sell_listing_review_orchestration.py`, `tests/test_sell_listing_decision_endpoint.py`, `tests/test_sell_review_background_cleanup.py`.

## Failure Checks

- Expire one profile and confirm the agent falls back cleanly with `browser_use_error=profile_missing`.
- Remove `GOOGLE_API_KEY` and confirm the runtime audit fails in `--require-live` mode.
- Set `BROWSER_USE_FORCE_FALLBACK=true` and confirm the harness stays deterministic instead of attempting live browser work.
- Confirm a listing-decision request is rejected when the session is not paused for review.
- Verify the pipeline still completes with deterministic fallback when Browser Use is unavailable.

## Sign-Off

- Save the validation command used, date, and any platform-specific DOM issues in your runbook or team notes.
