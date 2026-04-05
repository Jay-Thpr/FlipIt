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
