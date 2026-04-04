# Browser Use Status

## Overview

This file tracks the current state of Browser Use integration in the DiamondHacks backend. The repo still uses a FastAPI-first execution model where Browser Use runs behind agent `/task` handlers, while Fetch.ai Chat Protocol support remains scaffold-level.

## Completed Changes

- Standardized the backend event contract to PRD-style underscore events:
  - `pipeline_started`
  - `agent_started`
  - `agent_completed`
  - `agent_error`
  - `agent_retrying`
  - `pipeline_complete`
  - `pipeline_failed`
- Expanded BUY-side contracts so search, ranking, and negotiation can carry:
  - seller identity
  - seller credibility (`seller_score`)
  - recency (`posted_at`)
  - listing URL
  - offer status
- Updated ranking logic to score listings using price fit, condition, seller credibility, and recency.
- Updated negotiation output from simple message drafts to structured per-offer records.
- Hardened agent HTTP execution so runtime failures and output-validation failures return structured failed `AgentTaskResponse` payloads instead of opaque 500s.
- Added the first real Browser Use execution path to `ebay_sold_comps_agent` with deterministic fallback when Browser Use or Gemini credentials are unavailable.
- Updated `BROWSER_USE_GUIDE.md` to reflect the repo’s real contract, event naming, and current Fetch.ai limitations.

## Current Agent Status

### Real Browser Use

- `ebay_sold_comps_agent`
  - Attempts live Browser Use extraction for eBay sold comps.
  - Falls back to deterministic local estimation if Browser Use dependencies are missing or the live run fails.

### Deterministic Scaffold Logic

- `depop_listing_agent`
- `depop_search_agent`
- `ebay_search_agent`
- `mercari_search_agent`
- `offerup_search_agent`
- `negotiation_agent`

These agents still use deterministic local logic and have not yet been replaced with real Browser Use task execution.

## Verification

- Targeted backend and agent suite passing:
  - `82` tests passed
- Validation run used:

```bash
./.venv/bin/python -m pytest -q tests/test_buy_decision_agents_real.py tests/test_contracts_and_execution.py tests/test_pipelines.py tests/test_orchestrator_resilience.py tests/test_http_execution_and_launcher.py tests/test_agents.py
```

## Remaining Work

- Replace deterministic Browser Use placeholders in search, listing, and negotiation agents with real browser automation.
- Implement real frontend-facing custom Browser Use events such as `listing_found` and `offer_sent` where needed.
- Add true Fetch.ai Chat Protocol/uAgent integration; current `/chat` endpoints are still placeholders.
- Reconcile runtime dependencies for Browser Use in `requirements.txt` or installation flow if live execution is expected by default.
- End-to-end test the HTTP agent mode with real Browser Use enabled, not just local in-process execution.

## Key Risks

- Browser Use reliability on eBay, Depop, and OfferUp remains the main operational risk.
- Fetch.ai integration is still incomplete, so Browser Use work is currently validated through FastAPI contracts rather than real agent-network messaging.
- The eBay sold comps live path depends on Browser Use packages and `GOOGLE_API_KEY`; without them, the fallback path is used.
