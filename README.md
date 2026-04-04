# DiamondHacks

FastAPI backend scaffold for the DiamondHacks resale-agent demo. The current repo state is a working backend with in-memory sessions, SSE streaming, 10 agent services, and an automated test suite.
Agent inputs and outputs are validated against step-specific schemas so pipeline contracts stay structurally stable as real logic is added. The sell flow now supports image-to-product analysis through Gemini, optional Gemini image cleanup for listing photos, and low-confidence correction resumes through the orchestrator.

Supabase persistence scaffolding is also present in the repo for the next backend phase:

- [supabase/README.md](supabase/README.md)
- [supabase/migrations/20260404145000_init_session_persistence.sql](supabase/migrations/20260404145000_init_session_persistence.sql)
- [backend/supabase_repo.py](backend/supabase_repo.py)

## Quick Start

```bash
make install
make check
```

Run the backend:

```bash
make run
```

Run the separate agent apps:

```bash
make run-agents
```

For local development, copy `.env.example` to `.env` and set `INTERNAL_API_TOKEN`. If the frontend runs on Expo Go or another device, set `PUBLIC_APP_BASE_URL` to a phone-reachable URL such as `http://192.168.x.x:8000` while leaving `APP_BASE_URL` on the backend address used by internal agent callbacks. Live Gemini image analysis requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`; Gemini clean-photo generation also uses that same key and can be tuned with `GEMINI_IMAGE_MODEL`. Set `CLEAN_PHOTO_PROVIDER=nano_banana` to force the clean-photo step through a Nano Banana endpoint or local mock while keeping Gemini enabled for recognition. Live Browser Use flows still require warmed profiles under `profiles/` and Chromium installed by `make install`.

## Core Commands

- `make install` creates `.venv` and installs dependencies.
- `make test` runs the pytest suite.
- `make compile` byte-compiles backend and tests as a quick build sanity check.
- `make check` runs tests plus compile checks.
- `make ci` matches the local CI flow.
- `./.venv/bin/python scripts/browser_use_validation.py --group buy_search` runs backend-only Browser Use smoke validation for the search agents.
- `./.venv/bin/python -m backend.browser_use_validation --mode fallback --scenario depop_listing` forces deterministic fallback for a targeted validation case.
- `./.venv/bin/python -m backend.browser_use_validation --require-live --group sell` fails if the selected sell-side scenarios do not execute in live Browser Use mode.
- `./.venv/bin/python -m backend.browser_use_runtime_audit` audits Chromium, env vars, profile directories, and runtime settings before live Browser Use runs.

## Current API

- `GET /health`
- `GET /agents`
- `GET /pipelines`
- `POST /sell/start`
- `POST /sell/correct`
- `POST /buy/start`
- `GET /stream/{session_id}`
- `GET /result/{session_id}`
- `POST /internal/event/{session_id}`

## Browser Use Deployment Notes

- Browser Use agents run behind the FastAPI task layer and fall back to deterministic logic if Browser Use dependencies, auth profiles, or `GOOGLE_API_KEY` are missing.
- The sell pipeline falls back to deterministic heuristics when Gemini image analysis is unavailable, and it pauses with `vision_low_confidence` when Gemini confidence is below the configured threshold.
- Render builds must install Chromium with `python -m patchright install chromium`.
- Headed Chromium needs a paid Render instance for demo reliability; the free tier is not sufficient for live Browser Use runs.
- Set `INTERNAL_API_TOKEN` and `GOOGLE_API_KEY` or `GEMINI_API_KEY` in the Render dashboard as secrets instead of committing values into `render.yaml`.
- Use the validation harness before demos: fallback mode checks contract stability, and `--require-live` confirms that selected flows actually executed through Browser Use.
- Use `BrowserUse-Live-Validation.md` as the manual pre-demo checklist for warmed profiles and platform-specific smoke tests.
