# Backend

This is the first runnable backend scaffold for the DiamondHacks project.

What it does now:

- exposes the planned FastAPI endpoints
- keeps live SSE queues in memory
- persists sessions, events, and final results to Supabase when configured
- runs stub SELL and BUY pipelines so the database wiring can be tested immediately

## Files

- [main.py](/Users/derek/.superset/worktrees/Diamond Hacks/helpful-sagittarius/backend/main.py)
- [session.py](/Users/derek/.superset/worktrees/Diamond Hacks/helpful-sagittarius/backend/session.py)
- [supabase_repo.py](/Users/derek/.superset/worktrees/Diamond Hacks/helpful-sagittarius/backend/supabase_repo.py)
- [requirements.txt](/Users/derek/.superset/worktrees/Diamond Hacks/helpful-sagittarius/backend/requirements.txt)
- [.env.example](/Users/derek/.superset/worktrees/Diamond Hacks/helpful-sagittarius/backend/.env.example)

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
uvicorn backend.main:app --reload --port 8000
```

## Required Env

- `INTERNAL_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

If Supabase env vars are missing, the backend still runs, but persistence falls back to in-memory only.

## Quick Verification

Health check:

```bash
curl http://localhost:8000/health
```

Start a SELL session:

```bash
curl -X POST http://localhost:8000/sell/start \
  -H 'Content-Type: application/json' \
  -d '{"image_b64":"demo"}'
```

Connect to the SSE stream:

```bash
curl -N http://localhost:8000/stream/<session_id>
```

Fetch the final result:

```bash
curl http://localhost:8000/result/<session_id>
```

## Notes

- The current pipeline behavior is stubbed so the persistence layer can be exercised immediately.
- The next backend step is replacing `run_stub_pipeline()` in [main.py](/Users/derek/.superset/worktrees/Diamond Hacks/helpful-sagittarius/backend/main.py) with real agent orchestration.
