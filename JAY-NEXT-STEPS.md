# Jay's Next Steps

**Scope:** Backend infrastructure only. Do NOT touch frontend, Fetch.ai integration, or Gemini Vision (those are other teammates' workstreams).

**Current state:** 192 tests passing. Core pipelines work end-to-end in fallback mode. Browser Use runtime wired up but requires warmed profiles + GOOGLE_API_KEY to run live.

---

## Task 1 — Fix ranking agent crash on empty results (CRITICAL)

**File:** `backend/agents/ranking_agent.py`

**Bug:** Lines 86–87 crash when all 4 buy-side search agents return zero results:
```python
top_choice = ranked_candidates[0]      # IndexError if empty
median_price = round(...) / len(candidates), 2)  # ZeroDivisionError if empty
```

**Fix:** Guard before both lines. If `ranked_candidates` is empty, return a graceful output:
```python
if not ranked_candidates:
    return {
        "agent": self.slug,
        "display_name": self.display_name,
        "summary": "No listings found across all platforms",
        "top_choice": None,   # but RankingOutput.top_choice is required — see below
        "candidate_count": 0,
        "ranked_listings": [],
        "median_price": 0.0,
    }
```

**Schema issue:** `RankingOutput.top_choice` is `RankedListing` (required, non-optional). Either:
- Make it `Optional[RankedListing]` in `backend/schemas.py` and update `NegotiationAgentInput` to handle `None`, OR
- Raise a clear `ValueError("No search results — cannot rank")` so the pipeline fails with `agent_error` rather than an unhandled crash

The `ValueError` approach is simpler and correct: if there are no candidates, the buy pipeline cannot meaningfully continue. Add a test that verifies this emits `agent_error` (not an unhandled exception).

**Acceptance criteria:** `make test` passes; a new test `test_ranking_agent_empty_candidates` exists.

---

## Task 2 — Add test for vision low-confidence resume flow

**File:** `tests/test_pipelines.py` (or `tests/test_sell_resume.py`)

**Gap:** The `POST /sell/correct` + `resume_sell_pipeline` path exists in code and was shipped, but test coverage is incomplete — there is no test that:
1. Starts a sell session with a low-confidence vision result (confidence < 0.70)
2. Verifies `vision_low_confidence` SSE event fires and pipeline pauses
3. Calls `POST /sell/correct` with a corrected item
4. Verifies the pipeline resumes and completes with `pipeline_complete`

**Acceptance criteria:** `make test` passes with the new test.

---

## Task 3 — Harden buy pipeline when search agents partially fail

**File:** `backend/orchestrator.py`

**Issue:** `_run_buy_search_parallel` uses `asyncio.gather` without `return_exceptions=True`. If one search agent raises (e.g. timeout), the entire gather raises and the other results are discarded. The buy pipeline then fails rather than proceeding with partial results.

**Fix:** Change gather to collect exceptions, then for any failed step inject an empty `SearchResultsOutput`:
```python
results = await asyncio.gather(*[run_one(slug, step) for slug, step in BUY_SEARCH_STEPS], return_exceptions=True)
# For each result: if exception, log agent_error event and substitute empty results
```

**Acceptance criteria:** `make test` passes; a new test verifies one failing search agent still allows ranking to run with partial results (and raises at ranking if all 4 fail).

---

## Manual steps (Jay only — not Codex)

In priority order:

1. **Create `.env`** — copy `.env.example`, fill in `GOOGLE_API_KEY` (from aistudio.google.com) and `INTERNAL_API_TOKEN`
2. **Warm browser profiles** — run `python -m backend.warm_profiles` after logging into Depop, eBay, OfferUp
3. **Spike httpx endpoints** — run the test in `TODO.md §2` to see which marketplaces respond to httpx
4. **Smoke test sell pipeline** — curl `/sell/start` + `/stream/{id}`, verify all 4 `agent_completed` events fire
5. **Smoke test buy pipeline** — verify all 4 search agents + ranking + negotiation complete
6. **Set up ngrok** — `brew install ngrok && ngrok http 8000`, give URL to frontend teammate
7. **Register eBay dev credentials** — `developer.ebay.com` → add `EBAY_APP_ID` + `EBAY_CERT_ID` to `.env`

---

## Codex task order

1. Task 1 (ranking agent crash) — ship immediately
2. Task 2 (sell resume test) — adds test coverage for shipped feature  
3. Task 3 (partial search failure hardening) — increases buy pipeline resilience

Each task must pass `make test` before the next one starts.
