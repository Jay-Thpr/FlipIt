# Backend Codebase Problems

This is an operator-ready backlog of the remaining backend problems after the Fetch merge and Browser Use sell-review work.

## Implemented, not live-validated

These have **automated tests** and run in CI; they still need **real marketplace / Agentverse** validation where noted.

- [x] **Sell listing review lifecycle** — pause at `ready_for_confirmation`, `confirm_submit`, `revise` (max 2 revisions), `abort`, expiry after `deadline_at`, revision window refresh after each successful revise. **Code:** `backend/orchestrator.py`. **Tests:** `tests/test_sell_listing_review_orchestration.py`, `tests/test_sell_listing_decision_endpoint.py`, `tests/test_sell_listing_review_result_contract.py`. **Live gap:** real Depop Browser Use submit / revise / abort.
- [x] **Background expiry for abandoned paused reviews** — timer-driven sweep calls `expire_sell_listing_review_if_needed` (default interval `SELL_REVIEW_CLEANUP_INTERVAL` seconds). **Code:** `backend/main.py`, `backend/session.py`. **Tests:** `tests/test_sell_review_background_cleanup.py`.
- [x] **Fetch runtime bridge** — SELL chain and BUY path with parallel search + no-results short-circuit (`backend/fetch_runtime.py`). **Tests:** `tests/test_fetch_runtime.py`, `tests/test_browser_use_fetch_compatibility.py`. **Live gap:** mailbox, ASI:One, discoverability.
- [x] **Fetch agent manifest** — `GET /fetch-agents`. **Tests:** `tests/test_contracts_and_execution.py`.

## P0 — Blockers (prioritized)

1. [ ] **Make SELL Browser Use stop deterministically at the ready-to-submit checkpoint.**
   - Current issue: the review loop exists, but the browser task still depends on prompt wording instead of a deterministic stop action.
   - References:
     - [backend/agents/browser_use_marketplaces.py](backend/agents/browser_use_marketplaces.py)
     - [backend/agents/browser_use_support.py](backend/agents/browser_use_support.py)
     - [BROWSER-USE-GAPS.md](BROWSER-USE-GAPS.md)

2. [ ] **Replace the placeholder screenshot artifact with real screenshot capture.**
   - Current issue: the code still uses `form_screenshot_url` rather than a real captured artifact where needed.
   - References:
     - [backend/schemas.py](backend/schemas.py)
     - [backend/agents/browser_use_marketplaces.py](backend/agents/browser_use_marketplaces.py)
     - [BROWSER-USE-GAPS.md](BROWSER-USE-GAPS.md)

3. [ ] **Replace the heuristic vision parser with the planned image pipeline.**
   - Current issue: vision still infers from text and URLs instead of using real image understanding.
   - References:
     - [backend/agents/vision_agent.py](backend/agents/vision_agent.py)
     - [PRD.md](PRD.md)

4. [ ] **Align the vision output schema with the fields downstream code already expects.**
   - Current issue: the orchestrator may emit fields not defined on `VisionAnalysisOutput`.
   - References:
     - [backend/orchestrator.py](backend/orchestrator.py)
     - [backend/schemas.py](backend/schemas.py)

## P1 — Product Gaps

- [x] **Background cleanup for abandoned paused SELL review sessions** — **Done:** lazy expiry on `/result`, `/stream`, `/sell/listing-decision`, plus periodic sweep in `backend/main.py`.

- [ ] Reduce the amount of synthetic fallback data on the default success path.
  - Current issue: the happy path still relies heavily on fabricated or estimator-based results.
  - References:
    - [backend/agents/search_support.py](backend/agents/search_support.py)
    - [backend/agents/ebay_sold_comps_agent.py](backend/agents/ebay_sold_comps_agent.py)
    - [backend/agents/pricing_agent.py](backend/agents/pricing_agent.py)
    - [tests/test_pipelines.py](tests/test_pipelines.py)

- [ ] Make the search docs match the actual execution order.
  - Current issue: the code runs HTTP/API first, then Browser Use, then fallback, but some older docs still imply Browser Use-first behavior.
  - References:
    - [backend/agents/depop_search_agent.py](backend/agents/depop_search_agent.py)
    - [backend/README.md](backend/README.md)

- [ ] Strengthen negotiation so it is not just a fixed template.
  - References:
    - [backend/agents/negotiation_agent.py](backend/agents/negotiation_agent.py)
    - [PRD.md](PRD.md)

- [ ] Unify pricing/event contracts.
  - Current issue: the orchestrator emits `median_price` from `validated_output.get("median_sold_price")`, but `PricingOutput` may not define `median_sold_price`.
  - References:
    - [backend/orchestrator.py](backend/orchestrator.py)
    - [backend/schemas.py](backend/schemas.py)

## P2 — Reliability Gaps

- [ ] Replace the placeholder local `/chat` surface with something Chat Protocol-capable.
  - Reference: [backend/agents/base.py](backend/agents/base.py)

- [ ] Make the default SELL fallback path honor the review loop instead of bypassing it.
  - References:
    - [backend/agents/depop_listing_agent.py](backend/agents/depop_listing_agent.py)
    - [tests/test_pipelines.py](tests/test_pipelines.py)

- [ ] Improve abort cleanup so failure state is explicit and not best-effort.
  - Reference: [backend/orchestrator.py](backend/orchestrator.py)

- [ ] Make temporary-file cleanup for remote-image uploads deterministic.
  - Reference: [backend/agents/depop_listing_agent.py](backend/agents/depop_listing_agent.py)

## P3 — Documentation Drift

- [x] Update `PRD.md` where it still describes ASI:One as the orchestrator instead of FastAPI plus the in-process orchestrator.

- [x] Update `PRD.md` where it still describes BUY search as sequential instead of parallel (where applicable).

- [x] Replace old `listing_ready` language with the actual sell review terms (`listing_review_required`, `POST /sell/listing-decision`).

- [x] Keep the legacy `draft_created` event noted as compatibility-only.

## Verification Notes

- **Automated:** `make check` — includes `tests/test_sell_listing_review_orchestration.py`, `tests/test_sell_listing_decision_endpoint.py`, `tests/test_sell_review_background_cleanup.py`, `tests/test_browser_use_fetch_compatibility.py`, `tests/test_contracts_and_execution.py` (fetch manifest), and expanded pipeline tests.
- **Still manual / ops:** live Agentverse mailbox and discoverability; live Browser Use on warmed accounts; deterministic browser-level checkpoint (not yet implemented).

## Note on Fetch BUY `previous_outputs`

The earlier concern about non-empty `previous_outputs` for search agents is **addressed in the Fetch chat path**: `backend/fetch_runtime.py` runs the four search agents with `previous_outputs={}` and builds the dict for ranking/negotiation. Remaining Fetch work is mostly **live registration**, **chat parsing**, and **surfacing execution_mode** in responses — see [FETCH_INTEGRATION.md](FETCH_INTEGRATION.md).
