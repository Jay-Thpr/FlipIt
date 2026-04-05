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
