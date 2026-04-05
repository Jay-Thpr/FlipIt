# Fetch + Browser Use Test Suites

This file lists the current Fetch.ai and Browser Use backend test coverage, with emphasis on the suites that validate the integration seams rather than just the pure Python fallback logic.

## How To Run

Targeted verification:

```bash
./.venv/bin/python -m pytest -q \
  tests/test_fetch_agent_builder_and_runner.py \
  tests/test_fetch_runtime_additional.py \
  tests/test_fetch_runtime.py \
  tests/test_browser_use_marketplaces_contracts.py \
  tests/test_browser_use_sell_checkpoint_additional.py \
  tests/test_browser_use_runtime.py \
  tests/test_browser_use_support_additional.py \
  tests/test_depop_listing_agent_real.py
```

Result from the latest local run:

- `38 passed`
- `1 xfailed`

The single xfail is intentional. It documents a known Fetch BUY-bridge bug without breaking the suite.

## Fetch Test Suites

### New

- [tests/test_fetch_agent_builder_and_runner.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_agent_builder_and_runner.py)
  - Covers `build_fetch_agent()` seed validation
  - Verifies mailbox and `publish_agent_details` wiring
  - Verifies optional `FETCH_USE_LOCAL_ENDPOINT` behavior
  - Tests the chat-handler path: acknowledgement, runtime execution, formatted response, and end-session signaling
  - Covers `backend.fetch_agents.launch.main()` usage, failure, and success paths
  - Covers `backend.run_fetch_agents.main()` subprocess spawning and cleanup

- [tests/test_fetch_runtime_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime_additional.py)
  - Verifies the SELL-side Fetch bridge runs the chain in order for `depop_listing_agent`
  - Verifies `execute_agent()` builds Fetch session IDs and fetch-specific context correctly
  - Includes an `xfail` test documenting the broken BUY bridge after the first search step

### Existing

- [tests/test_fetch_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_fetch_runtime.py)
  - Covers text parsing helpers
  - Covers basic search and pricing Fetch runtime paths
  - Covers current empty-ranking failure behavior

- [tests/test_http_execution_and_launcher.py](/Users/jt/Desktop/diamondhacks/tests/test_http_execution_and_launcher.py)
  - Covers the non-Fetch multi-process FastAPI launcher
  - Useful as a comparison point for process-supervision behavior

## Browser Use Test Suites

### New

- [tests/test_browser_use_marketplaces_contracts.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_marketplaces_contracts.py)
  - Pins the Depop Browser Use task strings for prepare, revise, submit, and abort
  - Verifies non-mobile wording and the no-submit contract in prepare and revise phases

- [tests/test_browser_use_sell_checkpoint_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_sell_checkpoint_additional.py)
  - Verifies Browser Use session cleanup when `final_result()` is missing
  - Verifies Depop listing checkpoint operations call the Browser Use runner with the expected `operation_name`, `keep_alive=True`, profile path, and domain allowlist

### Existing

- [tests/test_browser_use_runtime.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime.py)
  - Covers runtime readiness checks, fallback forcing, Browser Use kwargs, timeout behavior, and failure categorization

- [tests/test_browser_use_support_additional.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_support_additional.py)
  - Covers session cleanup when the Browser Use agent raises
  - Covers additional error classification behavior
  - Covers remote-image download and local-path fallback in the sell listing agent

- [tests/test_depop_listing_agent_real.py](/Users/jt/Desktop/diamondhacks/tests/test_depop_listing_agent_real.py)
  - Covers sell listing output construction
  - Covers live Browser Use checkpoint metadata
  - Covers fallback listing behavior and sell pipeline use of the listing agent

- [tests/test_browser_use_progress_events.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_progress_events.py)
  - Covers Browser Use-related SSE events for search, draft creation, and sell review flow events

- [tests/test_buy_search_agents_real.py](/Users/jt/Desktop/diamondhacks/tests/test_buy_search_agents_real.py)
  - Covers live/fallback search-agent behavior across marketplaces

- [tests/test_ebay_sold_comps_agent_real.py](/Users/jt/Desktop/diamondhacks/tests/test_ebay_sold_comps_agent_real.py)
  - Covers eBay sold-comps live/fallback behavior

- [tests/test_browser_use_validation_harness.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_validation_harness.py)
  - Covers the backend Browser Use validation harness behavior

- [tests/test_browser_use_runtime_audit.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime_audit.py)
  - Covers runtime-audit reporting for Browser Use prerequisites

- [tests/test_browser_use_runtime_verifier.py](/Users/jt/Desktop/diamondhacks/tests/test_browser_use_runtime_verifier.py)
  - Covers Browser Use runtime verification helpers

## What The New Coverage Adds

- It tests the Fetch `uAgents` adapter layer directly, which was largely untested before.
- It tests the Fetch subprocess supervisor directly.
- It pins the sell review-loop Browser Use operation split more explicitly.
- It adds visible automated coverage for one known Fetch BUY bridge failure without turning the whole suite red.

## Known Limits

- Live Agentverse discovery and mailbox attachment are still not covered by local pytest.
- Real Browser Use interaction with warmed marketplace profiles is still only partially covered; some paths remain validated through harnesses and manual rehearsal rather than pure unit tests.
- The deterministic Browser Use checkpoint action and real screenshot capture are still not implemented, so the tests currently validate prompt contracts and orchestration behavior rather than that missing browser primitive.

