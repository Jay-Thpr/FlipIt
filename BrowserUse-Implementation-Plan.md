# Browser Use Implementation Plan

## Goal

Implement the remaining Browser Use agents behind the FastAPI `/task` contract so the SELL and BUY flows match the PRD while staying compatible with the current backend schemas, orchestrator events, and fallback behavior.

## Current State

- `ebay_sold_comps_agent` has a real Browser Use path with deterministic fallback.
- Search, listing, and haggling agents are still deterministic scaffolds.
- FastAPI `/task` execution is the active integration surface; Fetch.ai Chat Protocol is still scaffold-level.
- Event naming is now standardized to underscore-style pipeline events.

## Implementation Order

## 1. Runtime and dependency hardening

- Add or confirm Browser Use runtime dependencies in the backend install flow.
- Standardize environment requirements: `GOOGLE_API_KEY`, browser install steps, persistent profile paths, and timeout defaults.
- Confirm `AGENT_TIMEOUT_SECONDS` aligns with the PRD target for Browser Use tasks.

## 2. Search agents

Implement real Browser Use execution for:
- `depop_search_agent`
- `ebay_search_agent`
- `mercari_search_agent`
- `offerup_search_agent`

Requirements:
- Use exact marketplace search URLs where possible.
- Return structured listings with `price`, `condition`, `seller`, `seller_score`, `url`, and `posted_at`.
- Preserve deterministic fallback behavior for blocked or timed-out runs.
- Emit custom progress events only if they follow the existing FastAPI event contract.

## 3. SELL listing automation

Implement Browser Use in `depop_listing_agent`:
- Use a persisted logged-in profile.
- Populate the listing form up to, but not including, final submit.
- Return preview data and a screenshot or equivalent confirmation artifact.
- Fail safely if login is missing or a form step changes.

## 4. Haggling agent

Implement real Browser Use messaging in `negotiation_agent`:
- One browser run per seller.
- Generate message text before browser navigation.
- Navigate directly to the target listing or seller contact flow.
- Return structured offer results with send status and failure reason when applicable.

## 5. End-to-end verification

- Add agent-level tests for success, timeout, and fallback cases.
- Add pipeline tests that exercise BUY and SELL flows with Browser Use enabled where feasible.
- Manually validate the high-risk flows:
  - eBay sold comps
  - Depop listing form population
  - one marketplace search agent
  - one haggling send attempt

## Deliverables

- Real Browser Use implementations for the remaining marketplace agents.
- Updated guide and status docs after each completed phase.
- Stable structured outputs that the ranking, negotiation, and frontend layers can consume without contract changes.

## Risks to Watch

- Marketplace DOM drift and bot detection.
- Authenticated session persistence, especially for Depop.
- Browser timeouts causing partial or inconsistent outputs.
- Contract drift between Browser Use agents, FastAPI events, and PRD expectations.
