# Browser Use Status

## Overview

Browser Use now runs behind the FastAPI `/task` handlers in the DiamondHacks backend. Fetch.ai Chat Protocol support is still separate and scaffold-level; the active execution contract for Browser Use remains the FastAPI agent surface.

## Implemented

- Shared Browser Use runtime/config helpers in [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)
- Shared marketplace prompt/result helpers in [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
- Backend-only validation harness in [backend/browser_use_validation.py](/Users/jt/Desktop/diamondhacks/backend/browser_use_validation.py)
- Live Browser Use with deterministic fallback in:
  - [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py)
  - [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py)
  - [backend/agents/ebay_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_search_agent.py)
  - [backend/agents/mercari_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/mercari_search_agent.py)
  - [backend/agents/offerup_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/offerup_search_agent.py)
  - [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
  - [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py)
- Additive Browser Use metadata in [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py)
- Browser Use runtime coverage in [tests/test_browser_use_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime.py)

## Verification

Phase gates passed:
- runtime/config
- search agents
- Depop listing
- negotiation
- validation harness

Harness:
```bash
./.venv/bin/python -m backend.browser_use_validation --mode dry-run
./.venv/bin/python -m backend.browser_use_validation --mode live --case buy_pipeline
```

Full suite:
```bash
./.venv/bin/python -m pytest -q
```

Result:
- `122 passed`

## Remaining Gaps

- Add frontend-facing Browser Use progress events like `listing_found` and `offer_sent` if the UI needs them.
- Manually validate the live Browser Use flows against warmed marketplace profiles and real DOMs.
- Implement real Fetch.ai Chat Protocol/uAgent runtime support without changing the `/task` contracts.
