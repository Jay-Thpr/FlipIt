from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend import orchestrator
from backend.schemas import (
    AgentTaskResponse,
    PipelineStartRequest,
    SearchResultsOutput,
)
from backend.session import session_manager


@pytest.mark.asyncio
async def test_buy_search_agent_retries_once_and_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"depop_search_agent": 0}

    valid_search_output = SearchResultsOutput(
        agent="depop_search_agent",
        display_name="Depop Search Agent",
        summary="Recovered on retry",
        results=[
            {
                "platform": "depop",
                "title": "Retry listing",
                "price": 40.0,
                "url": "https://depop.example/retry-listing",
                "condition": "great",
                "seller": "retry_depop_seller",
                "seller_score": 29,
                "posted_at": "2026-04-02",
            }
        ],
    ).model_dump()

    async def fake_run_agent_task(agent_slug: str, request: Any) -> AgentTaskResponse:
        if agent_slug == "depop_search_agent":
            attempts["depop_search_agent"] += 1
            if attempts["depop_search_agent"] == 1:
                raise RuntimeError("temporary search failure")
            return AgentTaskResponse(
                session_id=request.session_id,
                step=request.step,
                status="completed",
                output=valid_search_output,
            )

        if agent_slug == "ebay_search_agent":
            output = SearchResultsOutput(
                agent=agent_slug,
                display_name="eBay Search Agent",
                summary="eBay okay",
                results=[
                    {
                        "platform": "ebay",
                        "title": "eBay listing",
                        "price": 39.0,
                        "url": "https://ebay.example/retry-listing",
                        "condition": "good",
                        "seller": "retry_ebay_seller",
                        "seller_score": 710,
                        "posted_at": "2026-04-03",
                    }
                ],
            ).model_dump()
        elif agent_slug == "mercari_search_agent":
            output = SearchResultsOutput(
                agent=agent_slug,
                display_name="Mercari Search Agent",
                summary="Mercari okay",
                results=[
                    {
                        "platform": "mercari",
                        "title": "Mercari listing",
                        "price": 38.5,
                        "url": "https://mercari.example/retry-listing",
                        "condition": "excellent",
                        "seller": "retry_mercari_seller",
                        "seller_score": 62,
                        "posted_at": "2026-04-03",
                    }
                ],
            ).model_dump()
        elif agent_slug == "offerup_search_agent":
            output = SearchResultsOutput(
                agent=agent_slug,
                display_name="OfferUp Search Agent",
                summary="OfferUp okay",
                results=[
                    {
                        "platform": "offerup",
                        "title": "OfferUp listing",
                        "price": 37.0,
                        "url": "https://offerup.example/retry-listing",
                        "condition": "good",
                        "seller": "retry_offerup_seller",
                        "seller_score": 18,
                        "posted_at": "2026-03-29",
                    }
                ],
            ).model_dump()
        elif agent_slug == "ranking_agent":
            output = {
                "agent": "ranking_agent",
                "display_name": "Ranking Agent",
                "summary": "Ranked 4 listings and selected offerup as the top choice",
                "top_choice": {
                    "platform": "offerup",
                    "title": "OfferUp listing",
                    "price": 37.0,
                    "score": 0.88,
                    "reason": "Good condition with strong budget fit on offerup",
                    "url": "https://offerup.example/retry-listing",
                    "seller": "retry_offerup_seller",
                    "seller_score": 18,
                    "posted_at": "2026-03-29",
                },
                "candidate_count": 4,
                "ranked_listings": [
                    {
                        "platform": "offerup",
                        "title": "OfferUp listing",
                        "price": 37.0,
                        "score": 0.88,
                        "reason": "Good condition with strong budget fit on offerup",
                        "url": "https://offerup.example/retry-listing",
                        "seller": "retry_offerup_seller",
                        "seller_score": 18,
                        "posted_at": "2026-03-29",
                    }
                ],
                "median_price": 38.63,
            }
        else:
            output = {
                "agent": "negotiation_agent",
                "display_name": "Negotiation Agent",
                "summary": "Prepared 1 negotiation attempt starting with retry_offerup_seller on offerup",
                "offers": [
                    {
                        "platform": "offerup",
                        "seller": "retry_offerup_seller",
                        "listing_url": "https://offerup.example/retry-listing",
                        "listing_title": "OfferUp listing",
                        "target_price": 38.63,
                        "message": "Hi! I love this listing. Would you consider $33.3 for OfferUp listing?",
                        "status": "prepared",
                    }
                ],
            }

        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="completed",
            output=output,
        )

    monkeypatch.setattr(orchestrator, "run_agent_task", fake_run_agent_task)
    monkeypatch.setenv("BUY_AGENT_MAX_RETRIES", "1")

    request = PipelineStartRequest(
        user_id="buy-user",
        input={"query": "Nike vintage tee size M", "budget": 45},
        metadata={"source": "retry-test"},
    )
    session_id = "buy-retry-session"
    await session_manager.create_session(session_id=session_id, pipeline="buy", request=request)

    await orchestrator.run_pipeline(session_id, "buy", request)

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.status == "completed"
    assert attempts["depop_search_agent"] == 2
    event_types = [event.event_type for event in session.events]
    assert "agent_error" in event_types
    assert "agent_retrying" in event_types
    retry_event = next(event for event in session.events if event.event_type == "agent_retrying")
    assert retry_event.data == {"agent_name": "depop_search_agent", "attempt": 2, "max_attempts": 2}


@pytest.mark.asyncio
async def test_timeout_failure_records_agent_failure_category(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_run_agent_task(agent_slug: str, request: Any) -> AgentTaskResponse:
        await asyncio.sleep(0.05)
        return AgentTaskResponse(
            session_id=request.session_id,
            step=request.step,
            status="completed",
            output={},
        )

    monkeypatch.setattr(orchestrator, "run_agent_task", slow_run_agent_task)
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "0.01")

    request = PipelineStartRequest(
        user_id="sell-user",
        input={"image_urls": ["https://example.com/item.jpg"]},
        metadata={"source": "timeout-test"},
    )
    session_id = "timeout-session"
    await session_manager.create_session(session_id=session_id, pipeline="sell", request=request)

    await orchestrator.run_pipeline(session_id, "sell", request)

    session = await session_manager.get_session(session_id)
    assert session is not None
    assert session.status == "failed"
    assert session.result == {"pipeline": "sell", "outputs": {}}
    assert session.events[-1].event_type == "pipeline_failed"
    failure_event = next(event for event in session.events if event.event_type == "agent_error")
    assert failure_event.data["category"] == "timeout"
    assert failure_event.data["agent_name"] == "vision_agent"
