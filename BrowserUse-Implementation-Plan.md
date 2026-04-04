# Browser Use Implementation Plan

## Goal

Implement Browser Use behind the existing FastAPI `/task` contract so SELL and BUY flows match [PRD.md](/Users/jt/Desktop/diamondhacks/PRD.md) without breaking the current backend schemas, orchestrator events, or fallback behavior documented in [BROWSER_USE_GUIDE.md](/Users/jt/Desktop/diamondhacks/BROWSER_USE_GUIDE.md) and [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md).

## Phases

### 1. Runtime Hardening

- Centralize Browser Use imports, profile configuration, model selection, and structured task execution.
- Keep Browser Use optional at runtime so CI and local development still pass without Chromium or Gemini credentials.
- Align `AGENT_TIMEOUT_SECONDS` with the PRD target of 30 seconds.

Test gate:
- `tests/test_browser_use_runtime.py`

### 2. BUY Search Agents

- Add Browser Use-first execution to:
  - `depop_search_agent`
  - `ebay_search_agent`
  - `mercari_search_agent`
  - `offerup_search_agent`
- Preserve deterministic fallback through `search_support.py`.
- Keep outputs compatible with `SearchResultsOutput`.

Test gate:
- `tests/test_buy_search_agents_real.py`

### 3. SELL Listing Automation

- Add Depop draft creation through a warmed persisted profile.
- Keep title, description, price, and category generation deterministic before browser navigation.
- Return additive draft metadata without breaking the existing output contract.

Test gate:
- `tests/test_depop_listing_agent_real.py`

### 4. Negotiation

- Keep candidate selection and offer text generation deterministic.
- Run Browser Use once per prepared offer when profiles are available.
- Return `sent`, `failed`, or `prepared` with structured failure metadata.

Test gate:
- `tests/test_buy_decision_agents_real.py`

### 5. Final Verification

- Run pipeline tests after each phase where relevant.
- Run the full backend suite before closing the work.

Verification:
- `./.venv/bin/python -m pytest -q`
