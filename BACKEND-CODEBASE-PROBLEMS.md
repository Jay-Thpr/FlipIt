# Backend Codebase Problems

This is an operator-ready backlog of the remaining backend problems after the Fetch merge and Browser Use sell-review work.

## P0 - Blockers

- [ ] Fix the Fetch BUY bridge so the search chain runs cleanly through all agents.
  - Current issue: `run_fetch_query()` passes non-empty `previous_outputs` into search agents whose contracts still require empty `previous_outputs`.
  - References:
    - [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py#L220)
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L263)
  - Impact:
    - `ebay_search_agent`, `mercari_search_agent`, `offerup_search_agent`, `ranking_agent`, and `negotiation_agent` do not run cleanly through the Fetch adapter path.

- [ ] Replace the heuristic vision parser with the planned image pipeline.
  - Current issue: vision still infers from text and URLs instead of using real image understanding.
  - References:
    - [backend/agents/vision_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/vision_agent.py#L62)
    - [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L137)
  - Impact:
    - No Gemini image understanding
    - No clean-photo generation
    - No real model or variant extraction

- [ ] Align the vision output schema with the fields downstream code already expects.
  - Current issue: the orchestrator emits `model`, `clean_photo_url`, and `search_query`, but the vision schema does not define them.
  - References:
    - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L348)
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L144)

- [ ] Make SELL Browser Use stop deterministically at the ready-to-submit checkpoint.
  - Current issue: the review loop exists, but the browser task still depends on prompt wording instead of a deterministic stop action.
  - References:
    - [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py#L94)
    - [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py#L143)
    - [BROWSER-USE-GAPS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-GAPS.md#L44)

- [ ] Replace the placeholder screenshot artifact with real screenshot capture.
  - Current issue: the code still uses `form_screenshot_url` rather than a real `form_screenshot_b64` artifact.
  - References:
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L193)
    - [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py#L27)
    - [BROWSER-USE-GAPS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-GAPS.md#L51)

## P1 - Product Gaps

- [ ] Reduce the amount of synthetic fallback data on the default success path.
  - Current issue: the happy path still relies heavily on fabricated or estimator-based results.
  - References:
    - [backend/agents/search_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/search_support.py#L125)
    - [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py#L100)
    - [backend/agents/pricing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/pricing_agent.py#L72)
    - [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py#L85)
    - [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py#L164)

- [ ] Make the search docs match the actual execution order.
  - Current issue: the code runs HTTP/API first, then Browser Use, then fallback, but some older docs still imply Browser Use-first behavior.
  - References:
    - [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py#L28)
    - [backend/agents/ebay_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_search_agent.py#L29)
    - [backend/agents/mercari_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/mercari_search_agent.py#L29)
    - [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md#L20)

- [ ] Strengthen negotiation so it is not just a fixed template.
  - Current issue: negotiation only targets a small set of listings and uses one message template.
  - References:
    - [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py#L47)
    - [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py#L145)
    - [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L68)

- [ ] Unify pricing/event contracts.
  - Current issue: the orchestrator emits `median_price` from `validated_output.get("median_sold_price")`, but `PricingOutput` does not define `median_sold_price`.
  - References:
    - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L365)
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L177)

- [ ] Harden the SELL review loop.
  - Current issue: `deadline_at` exists but is unused, `revision_count` is not enforced, and abandoned paused sessions are not cleaned up on a timer.
  - References:
    - [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py#L322)
    - [backend/session.py](/Users/jt/Desktop/diamondhacks/backend/session.py#L14)
    - [BROWSER-USE-SELL-CONFIRMATION-PLAN.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-SELL-CONFIRMATION-PLAN.md#L209)

## P2 - Reliability Gaps

- [ ] Turn empty BUY results into a graceful no-matches outcome instead of a pipeline failure.
  - References:
    - [backend/agents/ranking_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ranking_agent.py#L65)
    - [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py#L58)

- [ ] Replace the placeholder local `/chat` surface with something Chat Protocol-capable.
  - Current issue: the separate `uAgents` layer exists, but the local per-agent FastAPI surface is still placeholder-only.
  - References:
    - [backend/agents/base.py](/Users/jt/Desktop/diamondhacks/backend/agents/base.py#L82)

- [ ] Make the default SELL fallback path honor the review loop instead of bypassing it.
  - References:
    - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L89)
    - [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py#L108)

- [ ] Improve abort cleanup so failure state is explicit and not best-effort.
  - References:
    - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L725)

- [ ] Make temporary-file cleanup for remote-image uploads deterministic.
  - References:
    - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L234)

## P3 - Documentation Drift

- [ ] Update `PRD.md` where it still describes ASI:One as the orchestrator instead of FastAPI plus the in-process orchestrator.
  - Reference:
    - [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L82)

- [ ] Update `PRD.md` where it still describes BUY search as sequential instead of parallel.
  - Reference:
    - [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md#L109)
    - [backend/orchestrator.py](/Users/jt/Desktop/diamondhacks/backend/orchestrator.py#L214)

- [ ] Replace old `listing_ready` language with the actual sell review terms.
  - Current terms: `listing_review_required` and `POST /sell/listing-decision`.

- [ ] Keep the legacy `draft_created` event noted as compatibility-only.
  - Reference:
    - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py#L135)

## Verification Notes

- The new test suites already cover Fetch builder/launcher/supervisor behavior and additional Browser Use sell-checkpoint behavior.
- The remaining hard-to-automate gaps are still mostly:
  - live Agentverse mailbox/discoverability validation
  - live Browser Use marketplace execution on warmed real accounts
  - deterministic browser-level checkpoint behavior that has not yet been implemented
