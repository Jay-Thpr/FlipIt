from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SellRequest(BaseModel):
    image_b64: str = Field(..., description="Base64-encoded item photo.")


class BuyRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="Search text for the BUY flow.")
    url: Optional[str] = Field(default=None, description="Optional URL to parse for the BUY flow.")


class StartResponse(BaseModel):
    session_id: str
    mode: str


class InternalEventRequest(BaseModel):
    secret: str
    session_id: str
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    agent_name: Optional[str] = None
    summary: Optional[str] = None
    dedupe_key: Optional[str] = None


class InternalResultRequest(BaseModel):
    secret: str
    result_payload: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    supabase_enabled: bool
    memory_sessions: int


class EventEnvelope(BaseModel):
    event: str
    data: Dict[str, Any]


class SessionSummary(BaseModel):
    session_id: str
    mode: Optional[str] = None
    status: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    error_summary: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SessionEvent(BaseModel):
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class SessionDetail(SessionSummary):
    events: list[SessionEvent] = Field(default_factory=list)
    result_payload: Optional[Dict[str, Any]] = None
