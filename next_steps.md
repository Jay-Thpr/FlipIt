# Next Steps: Merging `frontend` + `jay` and Completing AgentMarket

> This document is the single source of truth for merging the two main development branches and finishing the project.

---

## Table of Contents

1. [Branch Overview](#1-branch-overview)
2. [The Merge: Step-by-Step](#2-the-merge-step-by-step)
3. [Schema Reconciliation](#3-schema-reconciliation)
4. [Frontend-Backend Integration Work](#4-frontend-backend-integration-work)
5. [Hackathon Track Deliverables](#5-hackathon-track-deliverables)
6. [Final Checklist](#6-final-checklist)

---

## 1. Branch Overview

### `frontend` branch (current, 12 commits)
- Complete React Native/Expo mobile app in `frontend/`
- Supabase schema (`supabase_schema.sql`) with 10 tables, RLS, triggers, realtime
- Seed data (`seed_demo_data.sql`) with 5 demo items, conversations, trades
- SQL migration files for incremental schema changes
- Docs: `BACKEND_REQUIREMENTS.md`, `UI_REQUIREMENTS.md`, updated `PRD.md`
- All frontend screens: auth, home, item detail, chat, trades, new listing, settings
- Uses **Supabase directly** for all CRUD, auth, storage, and realtime

### `jay` branch (remote, 108 commits)
- Complete Python/FastAPI backend in `backend/`
- 10+ AI agents: vision, eBay comps, pricing, Depop listing, 4 marketplace searches, ranking, negotiation
- Sell pipeline (4 sequential agents) and buy pipeline (6 agents, parallel search)
- Browser Use integration with fallback to httpx
- Fetch.ai runtime with 4 public Agentverse agents
- Supabase persistence layer (`supabase/migrations/`) for agent_runs, frontend tables, RLS
- 395+ passing tests
- SSE streaming for real-time progress
- Docs: `API_CONTRACT.md`, `BACKEND-FRONTEND-INTEGRATION-PLAN.md`, `CLAUDE.md`, etc.

### Common ancestor
Both branches diverged from commit `dfb9799` ("jay's roles").

---

## 2. The Merge: Step-by-Step

### 2.1 Create a merge branch

```bash
git checkout frontend
git checkout -b merge/frontend-jay
git merge origin/jay
```

### 2.2 Resolve the 4 conflicts

There are **zero code conflicts** (frontend lives in `frontend/`, backend in `backend/`). All 4 conflicts are docs/config:

#### Conflict 1: `.gitignore` (add/add conflict — both branches created this file independently)
**Action:** Combine both versions.
- `frontend` branch has: Node/Expo ignores, Supabase ignores
- `jay` branch has: Python/venv ignores, Browser Use profiles, `.env`
- Keep ALL entries from both. Remove duplicates. Order by section (Python, Node, IDE, env).

#### Conflict 2: `PRD.md`
**Action:** Use `jay`'s version as the base (it evolved through 108 commits), then add these frontend-specific sections that only exist in the `frontend` branch:
- The detailed "Frontend Architecture" section describing Expo Router, NativeWind, screen structure
- The "UI Design System" section with color palette, typography, dark theme specs
- The "Supabase Schema" section with the full table definitions the frontend uses
- The P&L calculation logic (sell: `price - initial_price`, buy: `initial_price - price`)

#### Conflict 3: `FRONTEND-BACKEND-CORE-DIFFERENCES.md` (add/add conflict — both branches created this file independently)
**Action:** Keep `jay`'s version. It was written with knowledge of the actual backend implementation and contains the authoritative gap analysis with 14 numbered mismatches and recommendations. The `frontend` branch version covers the same ground but from a spec-only perspective.

#### Conflict 4: `FRONTEND-BACKEND-RECONCILIATION-PLAN.md` (add/add conflict — both branches created this file independently)
**Action:** Keep `jay`'s version. It has the 7-phase implementation plan grounded in real backend code (endpoints, schemas, persistence layers). It is the authoritative merge blueprint.

### 2.3 Non-conflicting additions from jay

These are new files/directories added by jay that will merge cleanly (no action needed, but be aware):
- `.env.example` — comprehensive env var template
- `.github/workflows/backend-ci.yml` — GitHub Actions CI (runs `pytest` on push/PR)
- `backend/` — entire backend codebase (no overlap with `frontend/`)
- `supabase/migrations/` — jay's migration files (will need reconciliation with `supabase_schema.sql` — see Section 3)
- `Makefile` — backend dev commands (`make check`, `make test`, `make run`)
- `requirements.txt`, `pytest.ini`, `render.yaml`, `start.sh`
- Multiple documentation files (`API_CONTRACT.md`, `CLAUDE.md`, `TODO.md`, etc.)

### 2.4 Handle deleted files

Both branches delete `Jay'sRole.md` and `JaysRole-Implementation-Plan.md`. Git will auto-resolve these (both agree on deletion). Verify they're gone after merge.

### 2.5 Commit the merge

```bash
git add -A
git commit -m "Merge jay backend into frontend branch"
```

---

## 3. Schema Reconciliation

This is the **highest-risk area**. Both branches define Supabase tables, and the column names don't perfectly align.

### 3.1 Tables that exist in both branches

| Table | Frontend schema (`supabase_schema.sql`) | Jay schema (`supabase/migrations/`) | Mismatches |
|-------|----------------------------------------|-------------------------------------|------------|
| `items` | Full entity: `type`, `name`, `description`, `condition`, `image_color`, `target_price`, `min_price`, `max_price`, `auto_accept_threshold`, `initial_price`, `status`, `quantity`, `negotiation_style`, `reply_tone`, `best_offer`, `last_viewed_at` | Simpler: `name`, `description`, `target_price`, `condition`, `min_price`, `max_price`, `draft_url`, `listing_screenshot_url`, `listing_preview_payload`, `status` | **Jay is missing many frontend columns.** Frontend schema is the authority for item shape. |
| `market_data` | `item_id`, `platform`, `best_buy_price`, `best_sell_price`, `volume` | `item_id`, `platform`, `best_buy_price`, `best_sell_price`, `volume` | Match. |
| `conversations` | `item_id`, `username`, `platform`, `last_message`, `last_message_at`, `unread` | `user_id`, `platform`, `listing_url`, `listing_title`, `seller`, `status` | **Different columns.** Frontend links conversations to items; jay links to users. Need to merge both column sets. |
| `messages` | `conversation_id`, `sender` ('agent'\|'them'), `text` | `conversation_id`, `role` ('user'\|'assistant'\|'system'), `content`, `target_price` | **Column name mismatch.** `sender` vs `role`, `text` vs `content`. Frontend code uses `sender`/`text`. |
| `completed_trades` | `user_id`, `item_id`, `name`, `type` ('Sold'\|'Bought'), `platform`, `price`, `initial_price`, `listed_at`, `completed_at` | `user_id`, `platform`, `listing_url`, `listing_title`, `final_price`, `seller`, `conversation_id`, `run_id` | **Different columns.** Need to merge both: keep `item_id`, `name`, `type`, `price`, `initial_price` from frontend AND `listing_url`, `conversation_id`, `run_id` from jay. |

### 3.2 Tables only in jay (new)

| Table | Purpose | Action |
|-------|---------|--------|
| `agent_runs` | Tracks workflow state (session_id, user_id, item_id, pipeline, status, phase, next_action, result/request payloads) | **Keep as-is.** Frontend will read this to show agent progress. |
| `agent_run_events` | Durable event history per run | **Keep as-is.** Enables stream replay and debugging. |

### 3.3 Tables only in frontend

| Table | Purpose | Action |
|-------|---------|--------|
| `profiles` | User display name, email, avatar | **Keep.** Jay's backend doesn't manage profiles. |
| `user_settings` | Theme, auto-reply, negotiation style, notification prefs | **Keep.** Jay's backend doesn't manage settings. |
| `platform_connections` | Tracks which marketplace accounts are connected | **Keep.** Jay's backend doesn't manage connections. |
| `item_platforms` | Many-to-many items-to-platforms | **Keep.** Jay references platforms differently (inside agent runs). |
| `item_photos` | Ordered photos per item | **Keep.** Jay doesn't handle photo management. |

### 3.4 Required resolution: Unified schema

**Create a single `supabase_schema.sql`** that:

1. **Uses the frontend's `items` table** as the base (it has all the columns the app needs), then **adds jay's columns**: `draft_url`, `listing_screenshot_url`, `listing_preview_payload`
2. **Merges `conversations`**: Keep frontend's columns (`item_id`, `username`, `last_message`, `last_message_at`, `unread`) AND add jay's (`user_id`, `listing_url`, `listing_title`, `seller`, `status`)
3. **Standardizes `messages`**: Use the frontend's column names (`sender`, `text`) since the frontend code is already written against them. Add jay's `target_price` column. Update backend code to write `sender`/`text` instead of `role`/`content`.
4. **Merges `completed_trades`**: Use frontend column names (`price`, `name`, `type`, `initial_price`) AND add jay's (`listing_url`, `conversation_id`, `run_id`, `seller`). Rename jay's `final_price` writes to `price`.
5. **Keeps all frontend-only tables** (`profiles`, `user_settings`, `platform_connections`, `item_platforms`, `item_photos`)
6. **Keeps all jay-only tables** (`agent_runs`, `agent_run_events`)
7. **Updates jay's migration files** to match the unified schema
8. **Preserves all RLS policies** from both branches (frontend's user-scoped + jay's service-role bypass)
9. **Preserves triggers** (auto-create profile/settings on signup from frontend, updated_at from both)
10. **Preserves realtime** publication on conversations, messages, items

---

## 4. Frontend-Backend Integration Work

After the merge is clean, these are the tasks to wire the frontend to the backend.

### 4.1 Backend changes needed (in `backend/`)

| # | Task | Files to change | Priority |
|---|------|----------------|----------|
| 1 | **Update column names in writeback code** to match frontend schema: `sender`/`text` instead of `role`/`content` in messages, `price` instead of `final_price` in completed_trades. Note: the repository classes (`MessageRepository`, `CompletedTradeRepository`) are generic dict-passthrough — the actual column names are set in the writeback files | `backend/buy_writeback.py`, `backend/sell_writeback.py` | P0 |
| 2 | **Add missing item columns to items repository** — backend must read/write `type`, `image_color`, `initial_price`, `negotiation_style`, `reply_tone`, `quantity`, `best_offer`, `last_viewed_at` | `backend/repositories/items.py`, `backend/repositories/items_projection.py` | P0 |
| 3 | **Set CORS `ALLOWED_ORIGINS`** to the Expo dev server URL (typically `http://localhost:8081` or the device IP) and any deployed frontend URL | `backend/config.py`, `backend/main.py` | P0 |
| 4 | **Add `item_id` to conversation writes** — backend currently doesn't link conversations to items; frontend requires `conversations.item_id` | `backend/buy_writeback.py`, `backend/repositories/conversations.py` | P0 |
| 5 | **Ensure `completed_trades` includes `item_id`, `name`, `type`, `initial_price`** — frontend needs these for P&L chart | `backend/buy_writeback.py`, `backend/sell_writeback.py` | P1 |
| 6 | ~~**Fix buy writeback timing**~~ — **Already fixed on jay.** The `buy_writeback.py` code explicitly does NOT write `completed_trades` at offer-send time (defers to real purchase-close signal). Verify this remains correct after merge. | `backend/buy_writeback.py` | Done |
| 7 | ~~**Add `/config` endpoint**~~ — **Already exists on jay.** Returns `resale_copilot_agent_address` from env var `RESALE_COPILOT_AGENT_ADDRESS`. Verify the env var is set with the correct Fetch.ai agent address. | `backend/main.py` | Done |
| 8 | **Update `API_CONTRACT.md`** — The contract doc on jay is missing the newer authenticated endpoints: `POST /items/{item_id}/sell/run`, `POST /items/{item_id}/buy/run`, `GET /runs/{run_id}`, `GET /items/{item_id}/runs/latest`, `GET /runs/{run_id}/stream`, `POST /runs/{run_id}/sell/correct`, `POST /runs/{run_id}/sell/listing-decision`. These are the endpoints the frontend should actually use (item-scoped, auth-enforced). | `API_CONTRACT.md` | P0 |

### 4.1.1 Important: Authenticated vs Legacy Endpoints

Jay's backend has **two endpoint layers**:

| Layer | Endpoints | Auth | Use case |
|-------|-----------|------|----------|
| **Legacy** | `POST /sell/start`, `POST /buy/start`, `GET /result/{session_id}`, `GET /stream/{session_id}`, `POST /sell/correct`, `POST /sell/listing-decision` | None | Quick testing, demo scripts |
| **Authenticated** | `POST /items/{item_id}/sell/run`, `POST /items/{item_id}/buy/run`, `GET /runs/{run_id}`, `GET /items/{item_id}/runs/latest`, `GET /runs/{run_id}/stream`, `POST /runs/{run_id}/sell/correct`, `POST /runs/{run_id}/sell/listing-decision` | Supabase JWT | **Frontend should use these** |

The authenticated layer enforces item ownership (user must own the item) and persists runs to Supabase with `user_id` and `item_id`. The frontend API service should target these endpoints exclusively.

### 4.2 Frontend changes needed (in `frontend/`)

| # | Task | Files to change | Priority |
|---|------|----------------|----------|
| 1 | **Create API service layer** for backend calls — wrap fetch calls to the **authenticated** FastAPI endpoints: `POST /items/{item_id}/sell/run`, `POST /items/{item_id}/buy/run`, `GET /runs/{run_id}`, `GET /items/{item_id}/runs/latest`, `GET /runs/{run_id}/stream`, `POST /runs/{run_id}/sell/correct`, `POST /runs/{run_id}/sell/listing-decision`. These are the item-scoped, auth-enforced endpoints (not the legacy `/sell/start`, `/buy/start` endpoints). | New: `frontend/lib/api.ts` | P0 |
| 2 | **Add SSE client** for streaming agent progress — use EventSource or polyfill for React Native to connect to `GET /runs/{run_id}/stream` | New: `frontend/lib/sse.ts` | P0 |
| 3 | **Add agent run UI to item detail screen** — show current run status, phase, progress bar, agent steps completing in real-time | `frontend/app/item/[id].tsx` | P0 |
| 4 | **Wire "Start Selling" / "Start Buying" buttons** to backend — POST to `/items/{id}/sell/run` or `/items/{id}/buy/run` with item data as input | `frontend/app/item/[id].tsx` | P0 |
| 5 | **Handle sell flow pauses** — when `phase=awaiting_user_correction`, show correction UI; when `phase=awaiting_listing_review`, show listing preview with confirm/revise/abort buttons | `frontend/app/item/[id].tsx` or new screen | P0 |
| 6 | **Handle buy flow results** — display `search_summary`, `top_choice`, `offer_summary` from the run result | `frontend/app/item/[id].tsx` | P1 |
| 7 | **Add auth token to backend requests** — extract Supabase session token and send as `Authorization: Bearer <token>` header on all FastAPI calls | `frontend/lib/api.ts`, `frontend/contexts/AuthContext.tsx` | P0 |
| 8 | **Add backend URL configuration** — env var or config for FastAPI base URL (`http://localhost:8000` for dev) | `frontend/lib/api.ts` or `frontend/constants/config.ts` | P0 |
| 9 | **Wire settings screen agent controls** — the agents settings screen currently uses mock data; connect to `/agents` and `/fetch-agents` endpoints | `frontend/app/settings/agents.tsx` | P2 |

### 4.3 Environment setup

Jay's branch includes a comprehensive `.env.example` with all required and optional variables. Copy it and fill in secrets:

```bash
cp .env.example .env
```

Both the frontend and backend need a shared `.env` configuration. Key variables:

```env
# Shared Supabase instance
SUPABASE_URL=https://fmcwulonjlmwffpkxekl.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>

# Backend
APP_HOST=0.0.0.0
APP_PORT=8000
APP_BASE_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:8081,exp://192.168.x.x:8081
AGENT_EXECUTION_MODE=local_functions
INTERNAL_API_TOKEN=dev-internal-token
GOOGLE_API_KEY=<for-browser-use>

# eBay API (for buy pipeline)
EBAY_APP_ID=<your-ebay-app-id>
EBAY_CERT_ID=<your-ebay-cert-id>

# Fetch.ai / Agentverse (optional)
FETCH_ENABLED=false
AGENTVERSE_API_KEY=<from-agentverse>
RESALE_COPILOT_AGENT_ADDRESS=<registered-agent-address>

# Browser Use tuning
BROWSER_USE_FORCE_FALLBACK=false
BROWSER_USE_MAX_STEPS=15
AGENT_TIMEOUT_SECONDS=30
BUY_AGENT_MAX_RETRIES=1
```

See `.env.example` for the full list including Fetch.ai agent seeds, Agentverse addresses, and Browser Use config.

---

## 5. Hackathon Track Deliverables

Based on `DiamondHacks Important Info.md`, the project targets two sponsor tracks:

### 5.1 Browser Use Track

| Deliverable | Status | What's needed |
|-------------|--------|---------------|
| Agents actively browse the web | Done (jay) | Vision agent, eBay comps, Depop listing, marketplace searches all use Browser Use |
| Live demo of browser interaction | Needs testing | Warm browser profiles for Depop/eBay, test with real `GOOGLE_API_KEY` |
| Fallback when Browser Use fails | Done (jay) | httpx fallback clients for all search agents |

**Remaining work:**
- [ ] Test Browser Use agents end-to-end with real credentials
- [ ] Create/warm browser profiles under `profiles/` directory
- [ ] Record demo video showing browser automation

### 5.2 Fetch.ai Track

| Deliverable | Status | What's needed |
|-------------|--------|---------------|
| Agents registered on Agentverse | Partially done (jay) | 4 public agents built, need actual registration |
| Chat Protocol implemented | Done (jay) | Fetch agent chat profiles exist |
| Demo via ASI:One | Not done | Need Agentverse API key, register agents, get ASI:One chat URL |
| Master Agent FAB in app | Done (frontend) | Opens `https://asi1.ai/chat?agent={address}` |

**Remaining work:**
- [ ] Get `AGENTVERSE_API_KEY` and register all agents
- [ ] Obtain agent addresses for ASI:One URLs
- [ ] Wire addresses into `/config` endpoint so Master Agent FAB works
- [ ] Test ASI:One chat interaction with registered agents
- [ ] Capture Agentverse agent profile screenshots for submission

### 5.3 Demo Script

**90-second sell demo:**
1. Open app, sign in
2. Tap "+" to create new listing, take photo of item
3. Tap "Start Selling" - show agent progress in real-time (SSE stream)
4. Vision agent identifies item (show browser automation)
5. Pricing agent recommends price based on eBay comps
6. Listing review pause - user confirms listing
7. Depop listing created automatically

**90-second buy demo:**
1. Create a buy listing (e.g., "Canon AE-1 camera under $100")
2. Tap "Start Buying" - 4 marketplace searches run in parallel
3. Show ranked results with best deal highlighted
4. Negotiation agent sends offer
5. Show offer in chat view

---

## 6. Final Checklist

### Merge (do first)
- [ ] Create `merge/frontend-jay` branch from `frontend`
- [ ] Run `git merge origin/jay`
- [ ] Resolve `.gitignore` (combine both)
- [ ] Resolve `PRD.md` (jay base + frontend additions)
- [ ] Resolve `FRONTEND-BACKEND-CORE-DIFFERENCES.md` (keep jay's)
- [ ] Resolve `FRONTEND-BACKEND-RECONCILIATION-PLAN.md` (keep jay's)
- [ ] Commit the merge

### Schema (do second)
- [ ] Create unified `supabase_schema.sql` with all tables from both branches
- [ ] Reconcile `conversations` columns (merge both sets)
- [ ] Reconcile `messages` columns (`sender`/`text` as canonical names)
- [ ] Reconcile `completed_trades` columns (merge both sets, `price` not `final_price`)
- [ ] Add `draft_url`, `listing_screenshot_url`, `listing_preview_payload` to frontend's items table
- [ ] Update jay's migration files to match unified schema
- [ ] Run schema against fresh Supabase project to verify
- [ ] Re-seed demo data

### Backend integration (do third)
- [ ] Update writeback files (`buy_writeback.py`, `sell_writeback.py`) to use frontend column names (`sender`/`text`, `price`)
- [ ] Add `item_id` linkage to conversation writes
- [ ] Add full item columns to item repository reads/writes
- [ ] Set CORS for Expo dev server
- [x] `/config` endpoint already exists on jay — verify `RESALE_COPILOT_AGENT_ADDRESS` env var is set
- [x] Buy writeback timing already fixed on jay — completed_trades deferred to real purchase close
- [ ] Update `API_CONTRACT.md` to document the authenticated endpoints (`/items/{item_id}/*`, `/runs/{run_id}/*`)
- [ ] Run `make check` — all 395+ tests must still pass

### Frontend integration (do fourth)
- [ ] Create `frontend/lib/api.ts` with typed FastAPI client targeting **authenticated endpoints** (`/items/{item_id}/sell/run`, `/runs/{run_id}`, etc.)
- [ ] Create `frontend/lib/sse.ts` for EventSource streaming (`GET /runs/{run_id}/stream`)
- [ ] Add backend URL config (env var or constants file)
- [ ] Add Supabase JWT auth token injection to all backend calls (`Authorization: Bearer <token>`)
- [ ] Add "Start Selling"/"Start Buying" buttons to item detail
- [ ] Build agent progress UI (real-time step tracker from SSE events)
- [ ] Handle sell pauses (vision correction UI via `POST /runs/{run_id}/sell/correct`, listing review UI via `POST /runs/{run_id}/sell/listing-decision`)
- [ ] Handle buy results (search summary, top choice, offers)
- [ ] Wire agents settings screen to real endpoints (`GET /agents`, `GET /fetch-agents`)
- [ ] Test full sell flow end-to-end
- [ ] Test full buy flow end-to-end

### Hackathon submission (do last)
- [ ] Test Browser Use agents with real credentials
- [ ] Warm browser profiles for Depop/eBay
- [ ] Register Fetch.ai agents on Agentverse
- [ ] Wire ASI:One URL into Master Agent FAB
- [ ] Test ASI:One chat with registered agents
- [ ] Record demo video (sell flow + buy flow)
- [ ] Push merged branch to `main`
- [ ] Submit: GitHub repo, demo video, ASI:One chat URL, Agentverse profiles
