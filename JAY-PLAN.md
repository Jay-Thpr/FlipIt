# Jay's Implementation Plan

Items to implement in priority order. Do not start implementation until this plan is reviewed.

---

## 4. Add CORS Middleware to `main.py`

**Why:** The frontend (Expo web or any browser client) will be blocked by CORS on the first request to any endpoint. This needs to land before any frontend integration test.

**File:** `backend/main.py`

**Change:** Add `CORSMiddleware` immediately after `app = FastAPI(...)`.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins=["*"]` is acceptable for a hackathon. Do not add `allow_credentials=True` together with wildcard origins in production — for the demo this is fine.

**Verification:** Start the backend, then from a browser console or curl with an `Origin` header, confirm the response includes `Access-Control-Allow-Origin: *`.

---

## 5. Add SSE Keepalive Pings to `main.py`

**Why:** Browser Use tasks take 30–60 seconds. The current `event_generator` calls `queue.get()` with no timeout, which blocks indefinitely. Nginx on Render and most HTTP proxies will drop idle connections after 60 seconds. The frontend SSE connection will die mid-pipeline before any agent completes.

**File:** `backend/main.py`

**Current code in `event_generator` (lines ~113–126):**
```python
while True:
    event = await queue.get()
    yield format_sse(event)
    if event.event_type in {"pipeline_complete", "pipeline_failed"}:
        break
```

**Replace with:**
```python
KEEPALIVE_INTERVAL = 15.0  # seconds

while True:
    try:
        event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_INTERVAL)
        yield format_sse(event)
        if event.event_type in {"pipeline_complete", "pipeline_failed"}:
            break
    except asyncio.TimeoutError:
        yield ": ping\n\n"
```

**How it works:** `asyncio.wait_for` raises `TimeoutError` if no event arrives within 15 seconds. The `": ping\n\n"` string is an SSE comment — browsers and proxies see it as activity and reset the idle timer, but the frontend EventSource ignores it (comments are not dispatched as events).

**Define `KEEPALIVE_INTERVAL` at module level** so it is easy to tune.

**Verification:** Start the backend with a slow or no-op agent (or increase `AGENT_TIMEOUT_SECONDS` to 60), connect to a stream, and confirm `: ping` lines appear every 15 seconds in the raw HTTP response before any agent event fires.

---

## 6. Pin `browser-use` in `requirements.txt`

**Why:** `browser-use` is currently unpinned. The API changed significantly across 0.x releases (parameter names, `Agent` constructor signature, `history.final_result()` call shape). An unpinned install on Render or a fresh teammate machine may pull a different version than what was tested locally, silently breaking the one agent with real Browser Use logic.

**Steps:**

1. Check the currently installed version:
   ```bash
   . .venv/bin/activate && pip show browser-use
   ```

2. In `requirements.txt`, replace:
   ```
   browser-use
   ```
   with:
   ```
   browser-use==<version from step 1>
   ```

3. Do the same for `langchain-google-genai` and `patchright` — both are also unpinned and both have non-trivial APIs. Run:
   ```bash
   pip show langchain-google-genai patchright
   ```

**Verification:** Delete `.venv`, run `make install`, confirm the same versions install and `make check` still passes.

---

## 7. Create `.env.example`

**Why:** No documented env var list exists anywhere. Any teammate who clones the repo and tries to run the backend without asking someone for the right vars will get confusing failures that look like bugs.

**File:** `.env.example` at the project root (not inside `backend/`).

**Full content to include** (derived from `backend/config.py`, `backend/agents/browser_use_support.py`, `backend/agents/base.py`, and `render.yaml`):

```dotenv
# ── FastAPI ────────────────────────────────────────────────────────────────
APP_HOST=0.0.0.0
APP_PORT=8000
APP_BASE_URL=http://localhost:8000

# ── Internal security ──────────────────────────────────────────────────────
# Token required for POST /internal/event/{session_id}
# Generate any random string for local dev; use a real secret in production.
INTERNAL_API_TOKEN=dev-internal-token

# ── Agent execution ────────────────────────────────────────────────────────
# local_functions = run agents in-process (default, no subprocesses needed)
# local_http      = orchestrator POSTs to per-agent FastAPI apps on ports 9101-9110
AGENT_EXECUTION_MODE=local_functions

# Per-agent call timeout in seconds (Browser Use tasks need 30+ seconds)
AGENT_TIMEOUT_SECONDS=30

# How many times to retry transient BUY search agent failures
BUY_AGENT_MAX_RETRIES=1

# ── Browser Use / Gemini ───────────────────────────────────────────────────
# Required for Browser Use agents (ebay_sold_comps, search agents, negotiation, depop_listing)
GOOGLE_API_KEY=your_google_api_key_here

# Disable anonymous telemetry from the browser-use library
ANONYMIZED_TELEMETRY=false

# Gemini model used by Browser Use agents
BROWSER_USE_GEMINI_MODEL=gemini-2.0-flash

# Directory for persistent browser profile data (relative to project root)
BROWSER_USE_PROFILE_ROOT=profiles

# Max browser steps per agent task before giving up
BROWSER_USE_MAX_STEPS=15

# Set to true to skip Browser Use entirely and use deterministic fallback logic
# Useful for CI, local testing without Chromium, or when GOOGLE_API_KEY is absent
BROWSER_USE_FORCE_FALLBACK=false
```

**Note:** Do not create a real `.env` file. Only `.env.example` is committed. Add `.env` to `.gitignore` if it is not already there.

**Verification:** Confirm `.gitignore` excludes `.env`. Confirm every env var read in `config.py` and `browser_use_support.py` appears in `.env.example`.

---

## 8. Audit and Fix `render.yaml` + `start.sh`

### 8a. `render.yaml` — Missing Environment Variables

**File:** `render.yaml`

The current file only sets `APP_HOST`, `APP_PORT`, `APP_BASE_URL`, and `AGENT_EXECUTION_MODE`. The deployed service will fail or fall back silently without these additions:

Add the following `envVars` entries:

```yaml
      - key: INTERNAL_API_TOKEN
        sync: false          # marks this as a secret — fill it in the Render dashboard
      - key: AGENT_TIMEOUT_SECONDS
        value: "60"          # Browser Use tasks run longer on Render than locally
      - key: BUY_AGENT_MAX_RETRIES
        value: "1"
      - key: GOOGLE_API_KEY
        sync: false          # secret — fill in Render dashboard
      - key: ANONYMIZED_TELEMETRY
        value: "false"
      - key: BROWSER_USE_GEMINI_MODEL
        value: "gemini-2.0-flash"
      - key: BROWSER_USE_MAX_STEPS
        value: "15"
      - key: BROWSER_USE_FORCE_FALLBACK
        value: "false"
```

`sync: false` tells Render this is a secret value that must be set manually in the dashboard rather than hardcoded in the YAML. Do not put real API keys in the YAML.

### 8b. `render.yaml` — Build Command Missing Chromium Install

**Current buildCommand:**
```yaml
buildCommand: pip install -r requirements.txt
```

Browser Use requires Chromium to be installed at build time, not at runtime. Add the install steps:

```yaml
buildCommand: >
  pip install -r requirements.txt &&
  python -m patchright install chromium
```

`uvx browser-use install` (mentioned in CLAUDE.md) does the same thing but requires `uvx`. Using `python -m patchright install chromium` directly is simpler and does not require `uv` to be available in the build environment.

**Note:** Chromium requires significant memory to run headed. Render's free tier will OOM. A Standard instance ($25/month) or higher is required for any demo that actually runs Browser Use. Document this in `README.md` if not already noted.

### 8c. `start.sh` — Current State is Fine for `local_functions` Mode

The current `start.sh` is:
```bash
#!/usr/bin/env bash
set -euo pipefail
uvicorn backend.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}"
```

With `AGENT_EXECUTION_MODE=local_functions` (the Render default), all 10 agents run in-process and no subprocesses need to be started. The current `start.sh` is correct for this mode.

**One issue:** The `APP_PORT` default in `start.sh` is `8000` but `render.yaml` sets `APP_PORT=10000`. These are consistent — Render injects `APP_PORT=10000` and `start.sh` reads it. No change needed.

**If `local_http` mode is ever used on Render:** `start.sh` would need to background all 10 agent processes before starting uvicorn. For the hackathon, stick with `local_functions` on Render.

### 8d. Verification Checklist for Render

- `render.yaml` references `./start.sh` as `startCommand` ✓ (already correct)
- `render.yaml` references `requirements.txt` as `buildCommand` base ✓
- All secrets (`INTERNAL_API_TOKEN`, `GOOGLE_API_KEY`) are marked `sync: false` and must be filled in Render dashboard before deploy
- Confirm Render service is on a paid plan before deploying any Browser Use code

---

## 9. Fix CLAUDE.md SSE Event Names

**Why:** CLAUDE.md currently says SSE events use "dot-delimited names" and lists examples like `pipeline.started`. The actual orchestrator (`backend/orchestrator.py`) emits underscore-delimited events. Any teammate reading CLAUDE.md and writing frontend SSE listeners or tests based on it will build against the wrong event names.

**File:** `CLAUDE.md`

**Find:**
```
- `pipeline.started`, `pipeline.completed`, `pipeline.failed`
- `agent.started`, `agent.completed`, `agent.failed`, `agent.retrying`
```

**Replace with:**
```
- `pipeline_started`, `pipeline_complete`, `pipeline_failed`
- `agent_started`, `agent_completed`, `agent_error`, `agent_retrying`
```

Also update the surrounding prose: change "dot-delimited" to "underscore-delimited".

**Note:** `pipeline_complete` (not `pipeline_completed`) and `agent_error` (not `agent_failed`) — these are the exact strings used in `orchestrator.py`. Verify against `orchestrator.py` before saving.

**Verification:** `grep -r "pipeline\." backend/` should return no matches in orchestrator or agent code. `grep -r "pipeline_" backend/orchestrator.py` should return the correct event names.
