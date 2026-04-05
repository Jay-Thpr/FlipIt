# Browser Use Live Validation Checklist

Use this checklist after the backend test suite is green and before any demo that depends on live Browser Use execution.

## Preconditions

- `.env` has `GOOGLE_API_KEY` and a non-default `INTERNAL_API_TOKEN`.
- Chromium is installed through `python -m patchright install chromium`.
- Warmed profiles exist under `profiles/depop`, `profiles/ebay`, `profiles/mercari`, and `profiles/offerup` as needed.
- Runtime audit passes:
  - `./.venv/bin/python -m backend.browser_use_runtime_audit --require-live`
- Harness smoke run passes for the target flow:
  - `./.venv/bin/python -m backend.browser_use_validation --group buy_search`

## BUY Flow

1. Run `depop_search`, `ebay_search`, `mercari_search`, and `offerup_search` through the validation harness.
2. Confirm each result shows `execution_mode=browser_use` when live credentials and profiles are present.
3. Confirm `listing_found` events appear in the session history with real titles, prices, and URLs.
4. Run `negotiation` with a safe test listing or sandbox account.
5. Confirm:
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

## Failure Checks

- Expire one profile and confirm the agent falls back cleanly with `browser_use_error`.
- Disconnect the API key and confirm the runtime audit fails in `--require-live` mode.
- Verify the pipeline still completes with deterministic fallback when Browser Use is unavailable.
- Confirm a listing-decision request is rejected when the session is not paused for review.

## Sign-Off

- Save the validation command used, date, and any platform-specific DOM issues in [BrowserUse-Status.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Status.md).
