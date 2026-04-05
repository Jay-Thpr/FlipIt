# Backend Scaffold

This backend gives the team a stable local contract for the resale demo, including Gemini-backed sell-side image analysis and Browser Use marketplace automation.

## Current Endpoints

- `GET /health`
- `GET /agents`
- `GET /items`
- `POST /items`
- `GET /items/{item_id}`
- `GET /items/{item_id}/conversations/{conversation_id}`
- `GET /pipelines`
- `POST /sell/start`
- `POST /sell/correct`
- `POST /buy/start`
- `GET /stream/{session_id}`
- `GET /result/{session_id}`
- `POST /internal/event/{session_id}`

## Current Behavior

- Sessions stay live in memory for SSE delivery and are also written to Supabase when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are configured.
- Frontend-facing listing data is available through in-memory `items` endpoints that match the current Expo screen model.
- `POST /sell/start` accepts image URLs or inline base64 payloads and runs Gemini image analysis when `GEMINI_API_KEY` or `GOOGLE_API_KEY` is configured.
- The vision step can also generate a cleaned resale photo through Gemini image generation and stores the resulting local file path in `vision_analysis.clean_photo_url`.
- Sell sessions pause in `awaiting_input` with a `vision_low_confidence` event when Gemini confidence is below `VISION_LOW_CONFIDENCE_THRESHOLD`, and `POST /sell/correct` resumes the same session.
- The Expo `new-listing` flow can invoke the sell pipeline today and polls `GET /result/{session_id}` for status, structured outputs, pending correction state, and errors.
- Pipelines run in the background; Browser Use-capable agents attempt live browser execution first and fall back to deterministic local logic when the Browser Use runtime or warmed profiles are unavailable.
- Each agent input is validated against a step-specific schema before the orchestrator calls that step.
- Each agent output is validated against a step-specific schema before it is emitted to SSE or saved in `/result`.
- The orchestrator applies per-step timeouts, emits `agent_error` and `agent_retrying` events, retries transient `BUY` search failures once by default, and stores partial results on pipeline failure.
- `AGENT_EXECUTION_MODE=local_functions` keeps the app runnable without launching separate agent processes.
- `python -m backend.run_agents` starts one FastAPI process per agent scaffold when you want to validate the per-agent `/task` apps.
- `make check` is the current local verification path and mirrors CI.

## Persistence Scaffolding

- [supabase/README.md](../supabase/README.md) documents the current session persistence model used by the Expo `new-listing` flow.
- [supabase/migrations/20260404145000_init_session_persistence.sql](../supabase/migrations/20260404145000_init_session_persistence.sql) creates the session-state and event-history tables.
- [supabase_repo.py](supabase_repo.py) persists the current `SessionState` and `SessionEvent` models used by `/result/{session_id}` and `/stream/{session_id}`.

## Frontend Connectivity

- `APP_BASE_URL` is the backend address agents use for internal callbacks.
- `PUBLIC_APP_BASE_URL` is the frontend-facing address returned in `stream_url` and `result_url`.
- `GEMINI_MODEL` controls image-to-product analysis and defaults to `gemini-2.5-flash`.
- `GEMINI_IMAGE_MODEL` controls clean-photo generation and defaults to `gemini-3.1-flash-image-preview`.
- `CLEAN_PHOTO_PROVIDER` accepts `auto`, `gemini`, or `nano_banana` and lets you force the clean-photo step through a mock or external Nano Banana-style service.
- For local Expo Go testing, keep `APP_BASE_URL=http://127.0.0.1:8000` and set `PUBLIC_APP_BASE_URL=http://<your-lan-ip>:8000`.
- On Render, set both values to the deployed HTTPS URL.

## Browser Use Validation Harness

Use the backend-only harness when you need repeatable Browser Use checks without frontend or Fetch.ai in the loop.

```bash
python scripts/browser_use_validation.py --group buy_search
python scripts/browser_use_validation.py --group pipeline --json
python scripts/browser_use_validation.py --scenario depop_listing --require-live
```

- `--group buy_search` runs the four marketplace search agents.
- `--group pipeline` runs full `sell` and `buy` smoke scenarios against the FastAPI app.
- `--scenario ... --require-live` is useful for warmed-profile checks before demos.
- `--mode fallback` forces deterministic fallback mode for quick local sanity checks.

## Next Backend Tasks

- Manually validate the profile-gated Browser Use paths on real logged-in marketplace accounts.
- Add frontend-facing custom Browser Use events such as `listing_found` and `offer_sent` where needed.
- Add actual Fetch.ai uAgent and Chat Protocol registration plus Agentverse verification.
