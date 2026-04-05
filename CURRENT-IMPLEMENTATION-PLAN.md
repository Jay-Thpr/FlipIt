# Current Implementation Plan

Date: 2026-04-04

## Purpose

This is the current execution plan for the repo based on the live Claude/Codex split, the sponsor-track priorities, and the codebase status as of today.

It is intentionally narrower than the older repo-wide implementation plans. The goal is to make the next set of actions obvious without creating overlap with Claude's active Browser Use and Fetch operations work.

## Current Objective

Finish sponsor-ready proof for:

- Best Use of Browser Use
- Best Use of Fetch.ai

Then use the remaining time on the highest-value product gaps that improve demo credibility without destabilizing the live path.

## Source of Truth Constraints

The no-overlap ownership rules in [CLAUDE-CODEX-NO-OVERLAP-PLAN.md](/Users/jt/Desktop/diamondhacks/CLAUDE-CODEX-NO-OVERLAP-PLAN.md) remain in force.

Codex should not edit these files while Claude is using them for live validation:

- [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py)
- [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
- [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
- [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)
- `.env`

## Repo Status Summary

### Browser Use

- The Browser Use sell path is structurally implemented.
- The remaining work is live validation and sponsor-proof capture.
- This remains Claude-owned.

Primary references:

- [BROWSER-USE-STATUS.md](/Users/jt/Desktop/diamondhacks/BROWSER-USE-STATUS.md)
- [BrowserUse-Live-Validation.md](/Users/jt/Desktop/diamondhacks/BrowserUse-Live-Validation.md)
- [BACKEND-CODEBASE-PROBLEMS.md](/Users/jt/Desktop/diamondhacks/BACKEND-CODEBASE-PROBLEMS.md)

### Fetch

- The runtime currently defines 11 Fetch specs.
- The public Agentverse-facing surface is 4 agents:
  - `resale_copilot_agent`
  - `vision_agent`
  - `pricing_agent`
  - `depop_listing_agent`
- The remaining Fetch work is operational:
  - Agentverse profile URLs
  - ASI:One shared URL
  - mailbox/registration verification

Primary references:

- [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py)
- [backend/run_fetch_agents.py](/Users/jt/Desktop/diamondhacks/backend/run_fetch_agents.py)
- [docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md](/Users/jt/Desktop/diamondhacks/docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md)

### Product Gaps Still Open

- Vision is still heuristic-heavy rather than real image understanding.
- Search results still rely heavily on synthetic fallback behavior.
- Pricing still uses synthetic comps and heuristic rationale.
- Negotiation is functional but template-heavy.
- Some listing artifact handling is still placeholder-level.

## Execution Tracks

## Track 1: Claude-Owned Critical Path

These tasks are the highest priority, but they are not Codex-safe right now.

### 1. Browser Use live validation

Owner: Claude

Deliverables:

1. Run the sell pipeline end to end.
2. Confirm `ebay_sold_comps` actually uses Browser Use.
3. Confirm `depop_listing` actually uses Browser Use.
4. Capture logs, screenshots, and operator notes suitable for sponsor proof.

Primary files:

- [backend/agents/ebay_sold_comps_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/ebay_sold_comps_agent.py)
- [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
- [backend/agents/browser_use_marketplaces.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_marketplaces.py)
- [backend/agents/browser_use_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/browser_use_support.py)

### 2. Fetch sponsor proof

Owner: Claude

Deliverables:

1. Launch and verify the public Fetch agents.
2. Capture final Agentverse profile URL(s).
3. Capture final ASI:One shared URL.
4. Confirm registration and mailbox flow are working.

## Track 2: Codex-Safe Immediate Work

These are the best tasks to execute in parallel right now.

### 1. Final sponsor-doc consistency pass

Owner: Codex

Status:

- Initial doc alignment is already done.
- Final pass should happen once Claude supplies the real proof URLs.

Files:

- [FETCH-BROWSER-USE-TRACK-AUDIT.md](/Users/jt/Desktop/diamondhacks/FETCH-BROWSER-USE-TRACK-AUDIT.md)
- [docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md](/Users/jt/Desktop/diamondhacks/docs/AGENTVERSE_DELIVERABLES_TEMPLATE.md)
- [README.md](/Users/jt/Desktop/diamondhacks/README.md)
- [FETCH_INTEGRATION.md](/Users/jt/Desktop/diamondhacks/FETCH_INTEGRATION.md)
- [backend/README.md](/Users/jt/Desktop/diamondhacks/backend/README.md)

Definition of done:

- Placeholder URLs are replaced with real proof links.
- Browser Use and Fetch docs tell the same story.
- Public-agent lineup matches runtime reality.

### 2. Improve negotiation quality

Owner: Codex

Primary file:

- [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py)

Work:

1. Make negotiation responses less template-like.
2. Improve counteroffer reasoning and concession logic.
3. Clarify fallback behavior when live profile automation is unavailable.
4. Add tests for more realistic negotiation branches.

Why this is next:

- High demo value
- Low overlap risk
- Isolated enough to complete cleanly

### 3. Improve search realism

Owner: Codex

Primary file:

- [backend/agents/search_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/search_support.py)

Work:

1. Reduce obviously synthetic fallback results.
2. Improve consistency of marketplace result data.
3. Keep outputs deterministic enough for tests.
4. Add tests that validate plausible output shape and ordering.

### 4. Improve pricing realism

Owner: Codex

Primary file:

- [backend/agents/pricing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/pricing_agent.py)

Work:

1. Tighten comp selection heuristics.
2. Improve rationale for list-price recommendations.
3. Align synthetic comps more closely with category and condition.
4. Add tests for more credible pricing outputs.

## Track 3: Good Work, But Wait For Claude To Clear The File

These should wait unless Claude explicitly hands them off.

### 1. Temp-file cleanup in listing flow

Primary file:

- [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)

Work:

1. Clean up temporary files from remote image downloads.
2. Cover success and failure cleanup paths with tests.

### 2. Replace placeholder screenshot artifact handling

Primary files:

- [backend/agents/depop_listing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_listing_agent.py)
- [backend/schemas.py](/Users/jt/Desktop/diamondhacks/backend/schemas.py)

Work:

1. Move beyond a loose screenshot URL pass-through.
2. Define a clearer artifact contract if the live path needs one.

## Track 4: Medium-Priority Platform Cleanup

These are valuable, but not ahead of sponsor proof or the safer demo-quality improvements above.

### 1. Improve local `/chat` behavior for per-agent apps

Primary file:

- [backend/agents/base.py](/Users/jt/Desktop/diamondhacks/backend/agents/base.py)

Work:

1. Replace placeholder `not_implemented` behavior with a minimal useful local chat surface.
2. Add endpoint tests.

### 2. Rebalance fallback-heavy test assumptions

Primary file:

- [tests/test_pipelines.py](/Users/jt/Desktop/diamondhacks/tests/test_pipelines.py)

Work:

1. Distinguish intended fallback behavior from preferred realistic behavior.
2. Avoid encoding weak defaults as the normal expected path.

### 3. Upgrade vision toward real image understanding

Primary file:

- [backend/agents/vision_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/vision_agent.py)

Work:

1. Add a real vision-provider path.
2. Preserve the current heuristics as fallback.
3. Add contract coverage for both paths.

## Recommended Execution Order

1. Claude finishes Browser Use live proof.
2. Claude finishes Fetch registration and captures final URLs.
3. Codex updates sponsor docs with the final proof links.
4. Codex improves [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py) and adds tests.
5. Codex improves [backend/agents/search_support.py](/Users/jt/Desktop/diamondhacks/backend/agents/search_support.py) and adds tests.
6. Codex improves [backend/agents/pricing_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/pricing_agent.py) and adds tests.
7. Revisit listing-flow cleanup work only after Claude is clear of the live path.
8. Do platform cleanup after sponsor-critical work is stable.

## Best Next Safe Step

If Codex is asked to start implementation immediately, the first code task should be:

1. Improve [backend/agents/negotiation_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/negotiation_agent.py)
2. Add focused negotiation tests
3. Run `make check`

## Definition of Done

This plan is complete when:

- Browser Use live validation is complete and documented.
- Fetch sponsor proof is complete and documented.
- Sponsor-facing docs include the real proof URLs and match runtime reality.
- Negotiation, search, and pricing outputs are materially more credible.
- Remaining post-demo work is clearly separated from the sponsor-critical path.
