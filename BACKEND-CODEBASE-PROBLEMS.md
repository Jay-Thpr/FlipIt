# Backend Codebase Problems

This file lists the substantive backend problems that are still open after the current Fetch merge and Browser Use sell-review work.

## Critical

- Fetch BUY bridge is broken after the first search step.
  - `run_fetch_query()` passes non-empty `previous_outputs` into search agents whose contracts still require empty `previous_outputs`.
  - References:
    - [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py#L220)
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L263)
  - Impact:
    - `ebay_search_agent`, `mercari_search_agent`, `offerup_search_agent`, `ranking_agent`, and `negotiation_agent` do not currently run cleanly through the Fetch adapter path.

- Vision is still a heuristic text/url parser rather than the planned image pipeline.
  - References:
    - [backend/agents/vision_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/vision_agent.py#L62)
    - [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L137)
  - Impact:
    - No Gemini image understanding
    - No clean-photo generation
    - No real model/variant extraction

- Vision output contract is missing fields that downstream code assumes.
  - The orchestrator emits `model`, `clean_photo_url`, and `search_query`, but the vision output schema does not define them.
  - References:
    - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L348)
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L144)

- SELL Browser Use still lacks a deterministic ready-to-submit checkpoint.
  - The backend review loop exists, but the browser task still relies on prompt wording instead of a custom deterministic stop action.
  - References:
    - [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py#L94)
    - [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py#L143)
    - [BROWSER-USE-GAPS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-GAPS.md#L44)

- Real screenshot capture is still missing.
  - The code still uses `form_screenshot_url` rather than a real `form_screenshot_b64` artifact.
  - References:
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L193)
    - [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py#L27)
    - [BROWSER-USE-GAPS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-GAPS.md#L51)

## High

- The default success path is still mostly synthetic fallback data rather than real market execution.
  - Search fallback fabricates listings:
    - [backend/agents/search_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/search_support.py#L125)
  - Sold comps fallback is estimator-based:
    - [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py#L100)
  - Pricing synthesizes comp history:
    - [backend/agents/pricing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/pricing_agent.py#L72)
  - Main pipeline tests still treat fallback as the default green path:
    - [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py#L85)
    - [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py#L164)

- Search agents are not Browser Use-first even though some docs still describe them that way.
  - Actual behavior is HTTP/API first, then Browser Use, then fallback.
  - References:
    - [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py#L28)
    - [backend/agents/ebay_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_search_agent.py#L29)
    - [backend/agents/mercari_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/mercari_search_agent.py#L29)
    - [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md#L20)

- Negotiation is still template-based and shallow relative to the product goal.
  - It only targets up to 3 prioritized listings and uses one fixed message template.
  - References:
    - [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py#L47)
    - [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py#L145)
    - [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L68)

- Pricing/event contracts still drift from each other.
  - The orchestrator emits `median_price` from `validated_output.get("median_sold_price")`, but `PricingOutput` does not define `median_sold_price`.
  - References:
    - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L365)
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L177)

- The SELL review loop is implemented but not hardened.
  - `deadline_at` exists in schema but is unused.
  - `revision_count` increments but is not enforced.
  - There is no timed cleanup for abandoned paused sell sessions.
  - References:
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L322)
    - [backend/session.py](/Users/jt/Desktop/diamondhacks/backend/session.py#L14)
    - [BROWSER-USE-SELL-CONFIRMATION-PLAN.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-SELL-CONFIRMATION-PLAN.md#L209)

## Medium

- Empty BUY results still become a pipeline failure instead of a graceful “no matches” outcome.
  - References:
    - [backend/agents/ranking_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ranking_agent.py#L65)
    - [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py#L58)

- The per-agent FastAPI `/chat` endpoint is still placeholder-only.
  - References:
    - [backend/agents/base.py](/Users/jt/Desktop/diamondhacks/backend/agents/base.py#L82)
  - Impact:
    - The separate `uAgents` layer exists, but the local per-agent FastAPI surface is not actually Chat Protocol-capable.

- The default SELL fallback path bypasses the review loop.
  - Fallback listings set `ready_for_confirmation=False`.
  - References:
    - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L89)
    - [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py#L108)

- Abort cleanup is best-effort and weakly modeled.
  - The abort branch marks the session completed before cleanup runs, and cleanup failure does not currently produce a dedicated failure state.
  - References:
    - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L725)

- Temporary files downloaded for remote-image upload are only best-effort managed.
  - References:
    - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L234)

## Doc Drift

- [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L82) still describes ASI:One as the orchestrator, while the actual product path is FastAPI plus the in-process orchestrator.
- [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L109) still describes BUY search as sequential, while the implementation runs BUY search in parallel:
  - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L214)
- Some older docs still center `listing_ready`, while the implemented sell review loop centers `listing_review_required` and `POST /sell/listing-decision`.
- The sell agent still emits the legacy `draft_created` event:
  - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L135)

## Test Gap Summary

- The new test suites now cover Fetch builder/launcher/supervisor behavior and additional Browser Use sell-checkpoint behavior.
- Remaining hard-to-automate gaps are still mostly:
  - live Agentverse mailbox/discoverability validation
  - live Browser Use marketplace execution on warmed real accounts
  - deterministic browser-level checkpoint behavior that has not yet been implemented

