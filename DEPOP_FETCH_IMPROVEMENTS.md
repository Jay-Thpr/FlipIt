# Depop And Fetch Improvement Brief

## Goal
Consolidate the current findings around Fetch.ai agent exposure, Depop search quality, and the claimed versus actual image-generation workflow into one implementation-focused document.

This file is based on the current repository state in:

- [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py)
- [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py)
- [backend/agents/httpx_clients.py](/Users/jt/Desktop/diamondhacks/backend/agents/httpx_clients.py)
- [backend/agents/vision_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/vision_agent.py)
- [backend/image_generation.py](/Users/jt/Desktop/diamondhacks/backend/image_generation.py)
- [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py)
- [tests/test_httpx_search_clients.py](/Users/jt/Desktop/diamondhacks/tests/test_httpx_search_clients.py)

## Executive Summary
The highest-value direction is to narrow scope and make Depop excellent rather than spreading effort across multi-marketplace Browser Use search. The current codebase already supports that direction:

- Fetch public-agent exposure for the sell-side Agentverse set is now aligned in code, but some tests and docs still describe the old state.
- Depop search should be treated as an API-first path, not a Browser Use path.
- The repo does have Gemini image generation code, but it is not integrated into the sell pipeline in the way some docs imply.
- The current Depop buy-side implementation has improved raw data extraction in `httpx_clients.py`, but `depop_search_agent.py` still contains stale Browser Use-oriented logic and interface bugs.

## 1. Fetch Public-Agent Launch Set

### Current issue
`make run-fetch-agents` launches whatever `list_public_fetch_agent_slugs()` returns. That list is derived from `FetchAgentSpec.is_public` in [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py).

The intended public submission set is:

- `resale_copilot_agent`
- `vision_agent`
- `pricing_agent`
- `depop_listing_agent`

That aligns with the existing readmes in:

- [backend/fetch_agents/readmes/resale_copilot_agent.md](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/readmes/resale_copilot_agent.md)
- [backend/fetch_agents/readmes/vision_agent.md](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/readmes/vision_agent.md)
- [backend/fetch_agents/readmes/pricing_agent.md](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/readmes/pricing_agent.md)
- [backend/fetch_agents/readmes/depop_listing_agent.md](/Users/jt/Desktop/diamondhacks/backend/fetch_agents/readmes/depop_listing_agent.md)

### Current code status
The runtime spec now marks these four as public and launchable in [backend/fetch_runtime.py](/Users/jt/Desktop/diamondhacks/backend/fetch_runtime.py).

### Remaining improvements
- Update stale tests in [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py), which still assert that only `resale_copilot_agent` is public and launchable.
- Update stale docs that still describe the old public/private split.

### Why it matters
Without test and doc cleanup, the repo will keep presenting contradictory information about what `make run-fetch-agents` is supposed to launch.

## 2. Nano Banana / Image Generation Is Not Integrated Into The Sell Flow

### What the docs imply
Some docs describe a workflow where the vision step both identifies the item and generates a cleaner white-background product image.

### What the code actually does
[backend/image_generation.py](/Users/jt/Desktop/diamondhacks/backend/image_generation.py) contains a real Gemini image-generation path:

- `build_professional_photo_prompt(...)`
- `professionalize_photo(...)`
- `store_generated_photo(...)`

This is configured through `NANO_BANANA_MODEL` in [backend/config.py](/Users/jt/Desktop/diamondhacks/backend/config.py).

However, the sell pipeline does not use that generated output during vision analysis. In [backend/agents/vision_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/vision_agent.py), `VisionAgent._select_clean_photo_url(...)` just returns the first input URL:

- no Gemini call
- no background removal
- no photo selection logic beyond first non-empty URL
- no generated image handoff into pricing or listing

### Improvement needed
Choose one of these paths and make it explicit:

1. Integrate photo professionalization into the actual sell pipeline before listing generation.
2. Or remove/soften docs that claim this already happens automatically.

### Recommended implementation direction
If Depop quality is the priority, the better path is:

- keep image generation as an explicit listing-prep step
- store the generated asset in Supabase
- pass that URL into the listing step as the preferred cover photo
- avoid pretending the current vision step is doing image enhancement

## 3. Depop Search Should Be API-First, Not Browser Use-First

### Strategic recommendation
If the goal is to focus on Depop and make one marketplace excellent, the search path should not depend on Browser Use unless there is no viable API route left.

### Why
Browser Use adds all of the following costs for Depop search:

- slower execution
- Chromium dependency
- brittle DOM/selectors
- more infrastructure variance
- no clear value if the internal API already returns the required fields

For Depop search specifically, the internal API path in [backend/agents/httpx_clients.py](/Users/jt/Desktop/diamondhacks/backend/agents/httpx_clients.py) is the right foundation.

## 4. Depop Search: Current Problems And Open Work

## 4.1 `httpx_clients.py`

### What is already improved
[backend/agents/httpx_clients.py](/Users/jt/Desktop/diamondhacks/backend/agents/httpx_clients.py) now already does several important things correctly in `search_depop_httpx(...)`:

- supports `max_price`
- reads `createdAt` into `posted_at`
- extracts first image URL from `pictures`
- extracts size from `attributes.variant.size`

That means part of the originally identified work has already landed.

### Remaining improvement
The tests in [tests/test_httpx_search_clients.py](/Users/jt/Desktop/diamondhacks/tests/test_httpx_search_clients.py) do not yet fully lock in those newer fields and filters. They should be expanded to verify:

- `maxPrice` is actually sent when budget is provided
- `posted_at` comes from Depop data rather than today by default
- `image_url` is extracted when present
- `size` is extracted when present

## 4.2 `depop_search_agent.py`

### Current problems
[backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py) still has several concrete problems:

1. `build_output()` calls `_resolve_results(query=query, budget=budget)`, but `_resolve_results()` currently only accepts `query`.
2. `build_output()` expects `results, result_source = ...`, but `_resolve_results()` returns three values.
3. `browser_use_error` is referenced in `build_output()` but is never defined in that scope.
4. Budget is read from input but not passed into `search_depop_httpx(query, max_price=...)`.
5. Browser Use is still treated as a search tier for Depop even though the preferred direction is API-first.
6. `build_runtime_metadata()` contains stale wording such as "Skipped Browser Use search because no query was provided," even when the issue is just missing query input rather than Browser Use behavior.
7. Fallback event semantics are still oriented around Browser Use failure, not the more relevant distinction of API success versus API fallback.

### Why this matters
This file is the main place where the Depop search strategy is expressed. Right now it mixes:

- an API-first architecture
- stale Browser Use assumptions
- inconsistent return-shape handling

That combination makes the implementation harder to trust and harder to evolve.

### Recommended target state
Refactor [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py) to:

- use `httpx` as the primary and normal path
- pass budget through to `search_depop_httpx(..., max_price=budget)`
- remove Browser Use as tier 2 for Depop search
- fall back directly to deterministic mock/fallback results only when API search fails
- emit execution metadata that accurately reports `httpx` versus `fallback`
- rename Browser Use-specific telemetry fields or keep them only for backward compatibility

## 5. Schema And Ranking Implications

### Context
Depop search data quality affects ranking quality downstream. If `posted_at`, `size`, and `image_url` are missing or fake, ranking quality suffers.

### Specific impact
The earlier behavior of hardcoding `posted_at` to today's date made the ranking agent's recency component effectively meaningless, because all listings looked equally recent.

### Improvement needed
If the buy-side UI and ranking flow are going to rely more heavily on Depop:

- keep `posted_at` real whenever possible
- expose `image_url` and `size` on listing results as optional fields
- keep this backward-compatible for other marketplaces by allowing `None`

If those fields are not already represented in the listing/result schema, add them there and ensure all non-Depop providers return `None`.

## 6. Documentation Drift

### Current drift
Several docs still describe an earlier state of the codebase:

- Browser Use-centric Depop search
- broader multi-marketplace emphasis
- public-agent launch assumptions that no longer match the runtime
- Nano Banana described as if already integrated into the sell pipeline

### Improvement needed
Update the docs to reflect the current intended product direction:

- Depop-first quality over broad marketplace breadth
- API-first search for Depop
- Browser Use reserved for cases where it actually adds value
- explicit distinction between "photo professionalization endpoint exists" and "sell pipeline automatically uses it"

## 7. Testing Improvements Needed

### Fetch tests
Update [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py) so it matches the current public-agent launch set.

### Depop client tests
Expand [tests/test_httpx_search_clients.py](/Users/jt/Desktop/diamondhacks/tests/test_httpx_search_clients.py) to verify:

- `max_price` request param behavior
- `posted_at` extraction from `createdAt`
- `image_url` extraction from `pictures`
- `size` extraction from variant attributes

### Depop agent tests
Add or strengthen tests around [backend/agents/depop_search_agent.py](/Users/jt/Desktop/diamondhacks/backend/agents/depop_search_agent.py) for:

- budget propagation
- API success path
- deterministic fallback path
- metadata correctness
- no Browser Use dependency in the normal path

## 8. Recommended Priority Order

1. Fix `depop_search_agent.py` so it is internally consistent and API-first.
2. Expand Depop search tests to lock in the improved data shape.
3. Clean up stale Fetch runtime tests for the public launch set.
4. Update docs so they match the actual code and product direction.
5. Decide whether Nano Banana should become a real pipeline step or remain an explicit separate endpoint.

## 9. Concrete Product Direction

If the product direction is "focus only on Depop and make this one as good as possible," the repo should converge on:

- Depop as the primary listing destination
- Depop search via API, not Browser Use
- Depop messaging/inbox automation where Browser Use actually adds unique value
- pricing and ranking tuned around Depop market reality
- optional image professionalization feeding directly into listing quality

That is a clearer and more defensible product than trying to maintain broad but weaker marketplace coverage everywhere.
