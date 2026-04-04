# API Contract — Frontend ⇔ Backend

This document defines the interface for the backend REST endpoints and the real-time Server-Sent Events (SSE) stream.

## Base URLs
- **Local:** `http://localhost:8000`
- **Current ngrok:** Ask backend developer for the tunnel URL
- **Production Render:** `https://diamondhacks-backend.onrender.com` (note: may be too slow for Browser Use tasks on free tier)

---

## 1. REST Endpoints

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
Typically, the frontend just listens to the SSE stream until `pipeline_complete`. But if you need to fetch the final snapshot later:

**`GET /result/{session_id}`**

**Response (200 OK):**
```json
{
  "session_id": "...",
  "status": "complete",
  "final_outputs": { ... }
}
```

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
  "pipeline": "sell",
  "error": "Timeout waiting for agent",
  "partial_outputs": { ... }
}
```

### 2.2 Agent Level Events

**`agent_started`**
```json
{
  "agent_name": "pricing_agent",
  "attempt_number": 1,
  "max_attempts": 1,
  "pipeline": "sell"
}
```

**`agent_completed`**
```json
{
  "agent_name": "pricing_agent",
  "summary": "Priced item at $50",
  "output": {
    "recommended_list_price": 50.0,
    "expected_profit": 20.0,
    ...
  }
}
```

**`agent_error`**
```json
{
  "agent_name": "ebay_sold_comps_agent",
  "attempt_number": 1,
  "max_attempts": 1,
  "error": "Timeouts exceeded",
  "category": "runtime_unavailable"
}
```

### 2.3 Specialized Events (For UI Badges/Cards)

**`vision_low_confidence`**
Fired in the SELL pipeline if Gemini is unsure. The frontend should display a correction form and call `POST /sell/correct`.
```json
{
  "suggestion": {
    "brand": "Nike",
    "item_name": "Hoodie",
    "confidence": 0.45,
    ...
  },
  "message": "Not sure — is this a Nike Hoodie?"
}
```

**`search_method`**
Fired by search agents to tell the frontend how the search was performed. Use this to render a "Live scraping", "Fallback", or "API" badge.
```json
{
  "agent_name": "depop_search_agent",
  "platform": "depop",
  "method": "httpx"  // Either "httpx", "browser_use", or "fallback"
}
```

**`draft_created`**
Fired by `depop_listing_agent`.
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
