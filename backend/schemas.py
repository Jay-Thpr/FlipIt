from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PipelineStartRequest(BaseModel):
    user_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineStartResponse(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    pipeline: Literal["sell", "buy"]
    status: str
    stream_url: str
    result_url: str
    created_at: str = Field(default_factory=utc_now_iso)


class AgentTaskRequest(BaseModel):
    session_id: str
    pipeline: Literal["sell", "buy"]
    step: str
    input: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentTaskResponse(BaseModel):
    session_id: str
    step: str
    status: Literal["completed", "failed"] = "completed"
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class EmptyPreviousOutputs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SellPipelineInput(BaseModel):
    image_urls: list[str] = Field(default_factory=list)
    notes: str | None = None


class BuyPipelineInput(BaseModel):
    query: str | None = None
    budget: float | None = None


class AgentOutputBase(BaseModel):
    agent: str
    display_name: str
    summary: str


class BrowserUseMetadata(BaseModel):
    mode: Literal["browser_use", "fallback", "skipped"]
    attempted_live_run: bool = False
    profile_name: str | None = None
    profile_available: bool | None = None
    error_category: str | None = None
    detail: str | None = None


class SearchListing(BaseModel):
    platform: Literal["depop", "ebay", "mercari", "offerup"]
    title: str
    price: float
    url: str
    condition: str
    seller: str
    seller_score: int = 0
    posted_at: str


class RankedListing(BaseModel):
    platform: Literal["depop", "ebay", "mercari", "offerup"]
    title: str
    price: float
    score: float
    reason: str
    url: str
    seller: str
    seller_score: int = 0
    posted_at: str


class NegotiationAttempt(BaseModel):
    platform: Literal["depop", "ebay", "mercari", "offerup"]
    seller: str
    listing_url: str
    listing_title: str
    target_price: float
    message: str
    status: Literal["sent", "failed", "prepared"]
    failure_reason: str | None = None
    conversation_url: str | None = None
    execution_mode: Literal["browser_use", "deterministic"] = "deterministic"
    browser_use_error: str | None = None
    attempt_source: Literal["prepared", "browser_use"] = "prepared"
    failure_category: str | None = None


class VisionAnalysisOutput(AgentOutputBase):
    detected_item: str
    brand: str
    category: str
    condition: str


class EbaySoldCompsOutput(AgentOutputBase):
    median_sold_price: float
    low_sold_price: float
    high_sold_price: float
    sample_size: int
    execution_mode: Literal["browser_use", "fallback"] = "fallback"
    browser_use_error: str | None = None
    browser_use: BrowserUseMetadata | None = None


class PricingOutput(AgentOutputBase):
    recommended_list_price: float
    expected_profit: float
    pricing_confidence: float


class DepopListingPreview(BaseModel):
    title: str
    price: float
    description: str


class DepopListingOutput(AgentOutputBase):
    title: str
    description: str
    suggested_price: float
    category_path: str
    draft_status: str | None = None
    form_screenshot_url: str | None = None
    listing_preview: DepopListingPreview | None = None
    execution_mode: Literal["browser_use", "fallback"] = "fallback"
    browser_use_error: str | None = None
    browser_use: BrowserUseMetadata | None = None


class SearchResultsOutput(AgentOutputBase):
    results: list[SearchListing] = Field(default_factory=list)
    execution_mode: Literal["browser_use", "fallback"] = "fallback"
    browser_use_error: str | None = None
    browser_use: BrowserUseMetadata | None = None


class RankingOutput(AgentOutputBase):
    top_choice: RankedListing
    candidate_count: int
    ranked_listings: list[RankedListing] = Field(default_factory=list)
    median_price: float


class NegotiationOutput(AgentOutputBase):
    offers: list[NegotiationAttempt] = Field(default_factory=list)
    browser_use: BrowserUseMetadata | None = None


class VisionAgentInput(BaseModel):
    original_input: SellPipelineInput = Field(default_factory=SellPipelineInput)
    previous_outputs: EmptyPreviousOutputs = Field(default_factory=EmptyPreviousOutputs)


class EbaySoldCompsPreviousOutputs(BaseModel):
    vision_analysis: VisionAnalysisOutput


class EbaySoldCompsAgentInput(BaseModel):
    original_input: SellPipelineInput = Field(default_factory=SellPipelineInput)
    previous_outputs: EbaySoldCompsPreviousOutputs


class PricingPreviousOutputs(BaseModel):
    vision_analysis: VisionAnalysisOutput
    ebay_sold_comps: EbaySoldCompsOutput


class PricingAgentInput(BaseModel):
    original_input: SellPipelineInput = Field(default_factory=SellPipelineInput)
    previous_outputs: PricingPreviousOutputs


class DepopListingPreviousOutputs(BaseModel):
    vision_analysis: VisionAnalysisOutput
    ebay_sold_comps: EbaySoldCompsOutput
    pricing: PricingOutput


class DepopListingAgentInput(BaseModel):
    original_input: SellPipelineInput = Field(default_factory=SellPipelineInput)
    previous_outputs: DepopListingPreviousOutputs


class DepopSearchAgentInput(BaseModel):
    original_input: BuyPipelineInput = Field(default_factory=BuyPipelineInput)
    previous_outputs: EmptyPreviousOutputs = Field(default_factory=EmptyPreviousOutputs)


class EbaySearchPreviousOutputs(BaseModel):
    depop_search: SearchResultsOutput


class EbaySearchAgentInput(BaseModel):
    original_input: BuyPipelineInput = Field(default_factory=BuyPipelineInput)
    previous_outputs: EbaySearchPreviousOutputs


class MercariSearchPreviousOutputs(BaseModel):
    depop_search: SearchResultsOutput
    ebay_search: SearchResultsOutput


class MercariSearchAgentInput(BaseModel):
    original_input: BuyPipelineInput = Field(default_factory=BuyPipelineInput)
    previous_outputs: MercariSearchPreviousOutputs


class OfferupSearchPreviousOutputs(BaseModel):
    depop_search: SearchResultsOutput
    ebay_search: SearchResultsOutput
    mercari_search: SearchResultsOutput


class OfferupSearchAgentInput(BaseModel):
    original_input: BuyPipelineInput = Field(default_factory=BuyPipelineInput)
    previous_outputs: OfferupSearchPreviousOutputs


class RankingPreviousOutputs(BaseModel):
    depop_search: SearchResultsOutput
    ebay_search: SearchResultsOutput
    mercari_search: SearchResultsOutput
    offerup_search: SearchResultsOutput


class RankingAgentInput(BaseModel):
    original_input: BuyPipelineInput = Field(default_factory=BuyPipelineInput)
    previous_outputs: RankingPreviousOutputs


class NegotiationPreviousOutputs(BaseModel):
    depop_search: SearchResultsOutput
    ebay_search: SearchResultsOutput
    mercari_search: SearchResultsOutput
    offerup_search: SearchResultsOutput
    ranking: RankingOutput


class NegotiationAgentInput(BaseModel):
    original_input: BuyPipelineInput = Field(default_factory=BuyPipelineInput)
    previous_outputs: NegotiationPreviousOutputs


class InternalEventRequest(BaseModel):
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class SessionEvent(BaseModel):
    session_id: str
    event_type: str
    pipeline: Literal["sell", "buy"] | None = None
    step: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=utc_now_iso)


class SessionState(BaseModel):
    session_id: str
    pipeline: Literal["sell", "buy"]
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    request: PipelineStartRequest
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    events: list[SessionEvent] = Field(default_factory=list)


AGENT_OUTPUT_MODELS = {
    "vision_agent": VisionAnalysisOutput,
    "ebay_sold_comps_agent": EbaySoldCompsOutput,
    "pricing_agent": PricingOutput,
    "depop_listing_agent": DepopListingOutput,
    "depop_search_agent": SearchResultsOutput,
    "ebay_search_agent": SearchResultsOutput,
    "mercari_search_agent": SearchResultsOutput,
    "offerup_search_agent": SearchResultsOutput,
    "ranking_agent": RankingOutput,
    "negotiation_agent": NegotiationOutput,
}

AGENT_INPUT_CONTRACTS = {
    "vision_agent": {
        "pipeline": "sell",
        "step": "vision_analysis",
        "input_model": VisionAgentInput,
    },
    "ebay_sold_comps_agent": {
        "pipeline": "sell",
        "step": "ebay_sold_comps",
        "input_model": EbaySoldCompsAgentInput,
    },
    "pricing_agent": {
        "pipeline": "sell",
        "step": "pricing",
        "input_model": PricingAgentInput,
    },
    "depop_listing_agent": {
        "pipeline": "sell",
        "step": "depop_listing",
        "input_model": DepopListingAgentInput,
    },
    "depop_search_agent": {
        "pipeline": "buy",
        "step": "depop_search",
        "input_model": DepopSearchAgentInput,
    },
    "ebay_search_agent": {
        "pipeline": "buy",
        "step": "ebay_search",
        "input_model": EbaySearchAgentInput,
    },
    "mercari_search_agent": {
        "pipeline": "buy",
        "step": "mercari_search",
        "input_model": MercariSearchAgentInput,
    },
    "offerup_search_agent": {
        "pipeline": "buy",
        "step": "offerup_search",
        "input_model": OfferupSearchAgentInput,
    },
    "ranking_agent": {
        "pipeline": "buy",
        "step": "ranking",
        "input_model": RankingAgentInput,
    },
    "negotiation_agent": {
        "pipeline": "buy",
        "step": "negotiation",
        "input_model": NegotiationAgentInput,
    },
}


def validate_agent_output(agent_slug: str, output: dict[str, Any]) -> dict[str, Any]:
    model = AGENT_OUTPUT_MODELS[agent_slug]
    return TypeAdapter(model).validate_python(output).model_dump()


def validate_agent_task_request(agent_slug: str, request: AgentTaskRequest) -> AgentTaskRequest:
    contract = AGENT_INPUT_CONTRACTS[agent_slug]
    if request.pipeline != contract["pipeline"]:
        raise ValueError(
            f"{agent_slug} expected pipeline {contract['pipeline']!r}, received {request.pipeline!r}"
        )
    if request.step != contract["step"]:
        raise ValueError(f"{agent_slug} expected step {contract['step']!r}, received {request.step!r}")

    validated_input = TypeAdapter(contract["input_model"]).validate_python(request.input).model_dump()
    return request.model_copy(update={"input": validated_input})
