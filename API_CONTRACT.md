# API Contract — Frontend ⇔ Backend

This document defines the interface for the backend REST endpoints and the real-time Server-Sent Events (SSE) stream.

## Changelog

| Date | Notes |
|------|--------|
| 2026-04-04 | Documented all public REST routes; aligned `GET /result` with `SessionState`; clarified `pipeline_failed.partial_result`; noted buy-side marketplace searches may run concurrently (SSE order for those steps is not guaranteed). |
| 2026-04-04 | `GET /health` includes `fetch_enabled` and `agentverse_credentials_present` (booleans, no secrets). |

---

## Base URLs
- **Local:** `http://localhost:8000`
- **Current ngrok:** Ask backend developer for the tunnel URL
- **Production Render:** `https://diamondhacks-backend.onrender.com` (note: may be too slow for Browser Use tasks on free tier)

---

## 0. Route index

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness + execution mode + agent count |
| `GET` | `/agents` | List agent display names, slugs, and HTTP ports |
| `GET` | `/fetch-agents` | List Fetch/Agentverse agent names, slugs, ports, descriptions, and recorded Agentverse addresses |
| `GET` | `/pipelines` | Ordered sell/buy steps (agent slug + step name) |
| `POST` | `/sell/start` | Queue sell pipeline |
| `POST` | `/buy/start` | Queue buy pipeline |
| `POST` | `/sell/correct` | Resume sell pipeline after user corrects low-confidence vision |
| `GET` | `/result/{session_id}` | Full session snapshot (`SessionState`) |
| `GET` | `/stream/{session_id}` | SSE event stream |
| `POST` | `/internal/event/{session_id}` | Inject an SSE event (requires `X-Internal-Token`) |

---

## 1. REST Endpoints

### 1.0 Health

**`GET /health`**

```json
{
  "status": "ok",
  "agent_execution_mode": "local_functions",
  "agent_count": "10"
}
```

### 1.0.1 Agents manifest

**`GET /agents`**

```json
{
  "agents": [
    { "name": "Vision Agent", "slug": "vision_agent", "port": 9101 }
  ]
}
```

### 1.0.2 Fetch agents manifest

**`GET /fetch-agents`**

```json
{
  "agents": [
    {
      "name": "VisionAgent",
      "slug": "vision_agent",
      "port": 9201,
      "agentverse_address": "agent1q...",
      "description": "Identifies a resale item from text or image URLs and summarizes its brand, category, and condition."
    }
  ]
}
```

`agentverse_address` is `null` until the real registered address is recorded in the corresponding `<SLUG>_AGENTVERSE_ADDRESS` environment variable.

### 1.0.3 Pipelines manifest

**`GET /pipelines`**

Returns `{ "sell": [ { "agent", "step" }, ... ], "buy": [ ... ] }` matching the orchestrator’s logical steps. *Note:* During execution, the four buy marketplace search steps may start and complete in parallel; SSE ordering for those steps can interleave—use `data.step` / `data.agent_name` to attribute events.

### 1.1 Start SELL Pipeline
Trigger the pipeline that identifies an item, estimates pricing, and creates a listing.

**`POST /sell/start`**
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "input": {
    "image_urls": ["https://example.com/image.jpg"],
    "notes": "Nike hoodie great condition"
  }
}
```

**Response (200 OK):**
```json
{
  "session_id": "ab12cd34-5678-90ef-ghij",
  "stream_url": "http://localhost:8000/stream/ab12cd34...",
  "result_url": "http://localhost:8000/result/ab12cd34..."
}
```

### 1.2 Start BUY Pipeline
Trigger the pipeline that searches 4 marketplaces, ranks results, and prepares target offers.

**`POST /buy/start`**
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "input": {
    "query": "vintage nike hoodie",
    "budget": 50.0
  }
}
```

**Response (200 OK):** Same shape as SELL pipeline.

### 1.3 Provide User Correction (Sell Pipeline)
Called when the VisionAgent is not confident in its identification.

**`POST /sell/correct`**
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "session_id": "ab12cd34-...",
  "corrected_item": {
    "brand": "Nike",
    "item_name": "Vintage Hoodie",
    "model": "Red Tag",
    "condition": "good",
    "search_query": "Vintage Nike Hoodie Red Tag"
  }
}
```

**Response (200 OK):**
```json
{ "ok": true }
```

### 1.4 Get Full Session Result (Optional)
Typically, the frontend listens to SSE until `pipeline_complete` or `pipeline_failed`. This endpoint returns the full persisted **`SessionState`** (same model the backend uses internally).

**`GET /result/{session_id}`**

**Response (200 OK)** — shape matches `backend/schemas.py` `SessionState`:

| Field | Type | Notes |
|-------|------|--------|
| `session_id` | string | |
| `pipeline` | `"sell"` \| `"buy"` | |
| `status` | `"queued"` \| `"running"` \| `"completed"` \| `"failed"` | Sell flow may stay `"running"` after `vision_low_confidence` until `POST /sell/correct` |
| `created_at`, `updated_at` | ISO string | UTC |
| `request` | object | Original `PipelineStartRequest` (`user_id`, `input`, `metadata`) |
| `result` | object | When present: `{ "pipeline", "outputs" }` — partial while running, final when completed |
| `error` | string \| null | Set when `status` is `failed` |
| `events` | array | Historical `SessionEvent` records (for debugging; prefer live SSE for UX) |

**404** if the session id is unknown.

### 1.5 Internal event injection

**`POST /internal/event/{session_id}`**

Headers: `X-Internal-Token: <INTERNAL_API_TOKEN>` (must match server config).

Body: `{ "event_type": "string", "data": { } }`

Appends a `SessionEvent` to the session and fans it out to active SSE subscribers. Used for agent-originated auxiliary events (e.g. `listing_found`, `search_method`).

**401** invalid/missing token. **404** unknown session.

---

## 2. Server-Sent Events (SSE) Stream

After calling a `/start` endpoint, the frontend should immediately open an `EventSource` connection to the provided `stream_url`. Note: Nginx/proxies require a keep-alive; the backend will occasionally yield `": ping\n\n"` lines which the `EventSource` automatically ignores.

**`GET /stream/{session_id}`**
**Accept:** `text/event-stream`

### 2.1 General Lifecycle Events

**`pipeline_started`**
Fired immediately upon connection.
```json
{
  "session_id": "...",
  "pipeline": "sell",
  "input": { "image_urls": [...], "notes": "..." }
}
```

**`pipeline_complete`**
Fired when the final agent finishes. The `outputs` dict contains the results from all agents.
```json
{
  "pipeline": "sell",
  "outputs": {
    "vision_analysis": { ... },
    "ebay_sold_comps": { ... },
    "pricing": { ... },
    "depop_listing": { ... }
  }
}
```

**`pipeline_failed`**
```json
{
  "mode": "sell",
  "error": "Timeout waiting for agent",
  "partial_result": {
    "pipeline": "sell",
    "outputs": { }
  }
}
```

(`partial_result` mirrors the last saved step outputs where available.)

### 2.1.1 Error categories (`agent_error`, `pipeline_failed`)

Orchestrator `data.category` on `agent_error` is one of:

- `timeout` — `asyncio` timeout waiting for the agent
- `validation` — typically `ValueError` from contract validation
- `agent_execution` — other failures (agent returned `failed`, runtime errors, etc.)

### 2.2 Agent Level Events

**`agent_started`** — `data` includes `agent_name`, `attempt`, `mode` (pipeline name).

**`agent_completed`** — `data` includes `agent_name`, `summary`, `output` (validated agent output dict).

**`agent_error`** — `data` includes `agent_name`, `attempt`, `max_attempts`, `error`, `category`.

**`agent_retrying`** — `data` includes `agent_name`, `attempt`, `max_attempts` (buy search retries).

*`pipeline` is on the outer SSE payload (`SessionEvent`), not necessarily duplicated inside every `data` object—clients should read the top-level JSON for each SSE message.*

### 2.3 Specialized Events (For UI Badges/Cards)

**`vision_low_confidence`**
Fired in the SELL pipeline when vision `confidence` is below the threshold (default **0.70**). Session remains **`running`**. The frontend should prompt for correction and call `POST /sell/correct`.

Payload is under the standard event envelope; `data` includes:

- `suggestion` — full `vision_analysis` output (includes `detected_item`, `brand`, `category`, `condition`, `confidence`, …)
- `message` — human-readable prompt string

**`pipeline_resumed`**
Emitted when the sell pipeline continues after `POST /sell/correct` (before subsequent agents run).

**`search_method`**
Fired by search agents to tell the frontend how the search was performed. Use this to render a "Live scraping", "Fallback", or "API" badge.
```json
{
  "agent_name": "depop_search_agent",
  "platform": "depop",
  "method": "httpx"  // Either "httpx", "browser_use", or "fallback"
}
```

**`draft_created`** *(legacy / compatibility)*
May be fired by `depop_listing_agent` for older clients. **Authoritative sell-side checkpoint:** use **`listing_review_required`** from the orchestrator (see below) and `GET /result/{session_id}` → `sell_listing_review` for paused-session UX.
```json
{
  "agent_name": "depop_listing_agent",
  "platform": "depop",
  "title": "Nike Hoodie - Good Condition",
  "suggested_price": 50.0,
  "draft_status": "success",
  "form_screenshot_url": "https://...",
  "source": "browser_use"
}
```

**`listing_review_required`**
Emitted when the SELL pipeline pauses for human review before submit. Transition the UI from the agent feed to the listing review screen. Payload includes `review_state`, `allowed_decisions` (`confirm_submit`, `revise`, `abort`), listing preview fields, and full Depop `output` as applicable. User continues via **`POST /sell/listing-decision`**.

Follow-on events after a decision include `listing_decision_received`, `listing_submission_approved`, `listing_submit_requested`, `listing_submitted` or `listing_submission_failed`, `listing_revision_requested`, `listing_revision_applied`, `listing_submission_aborted`, `listing_abort_requested`, `listing_aborted`, and expiry/cleanup events — see `BrowserUse-Live-Validation.md` and `backend/orchestrator.py`.

**`offer_prepared` / `offer_sent` / `offer_failed`**
Fired sequentially by `negotiation_agent` on the BUY pipeline.
```json
{
  "agent_name": "negotiation_agent",
  "platform": "depop",
  "seller": "thrift_king",
  "listing_title": "Vintage Hoodie",
  "target_price": 45.0,
  "status": "prepared", // Later: "sent" or "failed"
  "source": "browser_use"
}
```

---

## 3. Canonical Run Identifier (`session_id` / `run_id`)

The **canonical external run identifier** surfaced to the frontend is `session_id` (referred to as `run_id` in the authenticated frontend contract — both names refer to the same value).

- `POST /sell/start` and `POST /buy/start` return `session_id` in their response.
- `POST /items/{item_id}/sell/run` and `POST /items/{item_id}/buy/run` return the same value as `run_id`.
- All SSE payloads include `session_id` at the top level.
- The authenticated endpoints (`GET /runs/{run_id}`, `GET /runs/{run_id}/stream`, `POST /runs/{run_id}/sell/correct`, `POST /runs/{run_id}/sell/listing-decision`) accept this value as the `run_id` path parameter.

> **Important:** The `agent_runs.id` UUID stored in the database is an **internal storage identity** and must never be surfaced to the frontend. Always use `session_id` / `run_id`.

---

## 4. Legacy Endpoints

The following endpoints remain available for backward compatibility, developer tooling, and tests. They are **NOT** the primary frontend contract. They bypass auth and item ownership enforcement.

The primary frontend contract uses the `/items/{item_id}/...` and `/runs/{run_id}/...` authenticated endpoints.

| Method | Path | Preferred replacement |
|--------|------|-----------------------|
| `POST` | `/sell/start` | `POST /items/{item_id}/sell/run` |
| `POST` | `/buy/start` | `POST /items/{item_id}/buy/run` |
| `POST` | `/sell/correct` | `POST /runs/{run_id}/sell/correct` |
| `POST` | `/sell/listing-decision` | `POST /runs/{run_id}/sell/listing-decision` |
| `GET` | `/result/{session_id}` | `GET /runs/{run_id}` |
| `GET` | `/stream/{session_id}` | `GET /runs/{run_id}/stream` |
