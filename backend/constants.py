SELL_MODE = "sell"
BUY_MODE = "buy"

SESSION_STATUS_RUNNING = "running"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_FAILED = "failed"
SESSION_STATUS_TIMED_OUT = "timed_out"
SESSION_STATUS_CANCELLED = "cancelled"

EVENT_AGENT_STARTED = "agent_started"
EVENT_AGENT_LOG = "agent_log"
EVENT_AGENT_COMPLETED = "agent_completed"
EVENT_AGENT_ERROR = "agent_error"
EVENT_LISTING_FOUND = "listing_found"
EVENT_OFFER_SENT = "offer_sent"
EVENT_PIPELINE_COMPLETE = "pipeline_complete"
EVENT_PIPELINE_STARTED = "pipeline_started"
EVENT_PING = "ping"

SELL_AGENT_SEQUENCE = [
    "vision_agent",
    "ebay_sold_comps_agent",
    "pricing_agent",
    "depop_listing_agent",
]

BUY_AGENT_SEQUENCE = [
    "depop_search_agent",
    "ebay_search_agent",
    "mercari_search_agent",
    "offerup_search_agent",
    "ranking_agent",
    "negotiation_agent",
]

STREAM_KEEPALIVE_SECONDS = 15.0
SESSION_TIMEOUT_SECONDS = 300
