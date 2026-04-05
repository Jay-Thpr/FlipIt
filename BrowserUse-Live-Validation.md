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

## Failure Checks

- Expire one profile and confirm the agent falls back cleanly with `browser_use_error=profile_missing`.
- Remove `GOOGLE_API_KEY` and confirm the runtime audit fails in `--require-live` mode.
- Set `BROWSER_USE_FORCE_FALLBACK=true` and confirm the harness stays deterministic instead of attempting live browser work.
- Confirm a listing-decision request is rejected when the session is not paused for review.
- Verify the pipeline still completes with deterministic fallback when Browser Use is unavailable.

## Sign-Off

- Save the validation command used, date, and any platform-specific DOM issues in [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md).
