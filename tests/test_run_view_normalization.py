from __future__ import annotations

from backend.frontend_runs import build_run_payload, derive_next_action, derive_phase, derive_result_source
from backend.schemas import PipelineStartRequest, SellListingReviewState, SessionEvent, SessionState


def test_sell_paused_for_low_confidence_maps_to_correction_phase() -> None:
    session = SessionState(
        session_id="sell-correction",
        pipeline="sell",
        status="paused",
        request=PipelineStartRequest(input={"image_urls": ["https://example.com/item.jpg"]}),
        result={
            "pipeline": "sell",
            "outputs": {
                "vision_analysis": {
                    "agent": "vision_agent",
                    "display_name": "Vision Agent",
                    "summary": "Low confidence result",
                    "detected_item": "hoodie",
                    "brand": "Nike",
                    "category": "tops",
                    "condition": "good",
                    "confidence": 0.42,
                }
            },
        },
        events=[
            SessionEvent(
                session_id="sell-correction",
                event_type="vision_low_confidence",
                pipeline="sell",
                step="vision_analysis",
                data={"message": "Is this a Nike hoodie?"},
            )
        ],
    )

    view = build_run_payload(session)

    assert derive_phase(session) == "awaiting_user_correction"
    assert derive_next_action(session)["type"] == "submit_correction"
    assert view["progress"] == {"step": "vision_analysis", "event_type": "vision_low_confidence"}
    assert view["sell_summary"] == {
        "detected_item": "hoodie",
        "brand": "Nike",
        "confidence": 0.42,
        "recommended_price": None,
        "listing_title": None,
        "listing_price": None,
        "listing_status": None,
        "ready_for_confirmation": False,
    }
    assert view["result_source"] is None


def test_sell_paused_for_listing_review_maps_to_review_action() -> None:
    review = SellListingReviewState(
        state="ready_for_confirmation",
        revision_count=1,
        revision_instructions="Lower the price",
        paused_at="2026-04-05T10:00:00+00:00",
        deadline_at="2026-04-05T10:15:00+00:00",
    )
    session = SessionState(
        session_id="sell-review",
        pipeline="sell",
        status="paused",
        request=PipelineStartRequest(input={"image_urls": ["https://example.com/item.jpg"]}),
        sell_listing_review=review,
        result={
            "pipeline": "sell",
            "outputs": {
                "pricing": {
                    "agent": "pricing_agent",
                    "display_name": "Pricing Agent",
                    "summary": "Priced item",
                    "recommended_list_price": 72.0,
                    "expected_profit": 30.0,
                    "pricing_confidence": 0.8,
                },
                "depop_listing": {
                    "agent": "depop_listing_agent",
                    "display_name": "Depop Listing Agent",
                    "summary": "Listing ready",
                    "title": "Vintage hoodie",
                    "description": "Good condition",
                    "suggested_price": 72.0,
                    "category_path": "Men/Tops/Hoodies",
                    "listing_status": "ready_for_confirmation",
                    "ready_for_confirmation": True,
                    "execution_mode": "browser_use",
                },
            },
        },
    )

    view = build_run_payload(session)

    assert derive_phase(session) == "awaiting_listing_review"
    assert derive_next_action(session)["type"] == "review_listing"
    assert view["next_action"]["payload"]["review_state"]["state"] == "ready_for_confirmation"
    assert view["progress"] == {"step": "depop_listing", "event_type": "listing_review_required"}
    assert derive_result_source(session) == "browser_use"
    assert view["sell_summary"]["listing_title"] == "Vintage hoodie"
    assert view["sell_summary"]["ready_for_confirmation"] is True


def test_buy_completed_builds_search_and_offer_summaries_with_mixed_result_source() -> None:
    session = SessionState(
        session_id="buy-complete",
        pipeline="buy",
        status="completed",
        request=PipelineStartRequest(input={"query": "vintage nike tee", "budget": 45}),
        result={
            "pipeline": "buy",
            "outputs": {
                "depop_search": {
                    "agent": "depop_search_agent",
                    "display_name": "Depop Search Agent",
                    "summary": "Found Depop listings",
                    "results": [
                        {
                            "platform": "depop",
                            "title": "Nike tee depop",
                            "price": 28.0,
                            "url": "https://depop.example/1",
                            "condition": "good",
                            "seller": "seller-a",
                            "seller_score": 120,
                            "posted_at": "2026-04-05T09:00:00+00:00",
                        }
                    ],
                    "execution_mode": "browser_use",
                },
                "ebay_search": {
                    "agent": "ebay_search_agent",
                    "display_name": "eBay Search Agent",
                    "summary": "Found eBay listings",
                    "results": [
                        {
                            "platform": "ebay",
                            "title": "Nike tee ebay",
                            "price": 30.0,
                            "url": "https://ebay.example/1",
                            "condition": "good",
                            "seller": "seller-b",
                            "seller_score": 450,
                            "posted_at": "2026-04-05T09:05:00+00:00",
                        }
                    ],
                    "execution_mode": "httpx",
                },
                "mercari_search": {
                    "agent": "mercari_search_agent",
                    "display_name": "Mercari Search Agent",
                    "summary": "Mercari fallback no results",
                    "results": [],
                    "execution_mode": "fallback",
                },
                "offerup_search": {
                    "agent": "offerup_search_agent",
                    "display_name": "OfferUp Search Agent",
                    "summary": "OfferUp fallback no results",
                    "results": [],
                    "execution_mode": "fallback",
                },
                "ranking": {
                    "agent": "ranking_agent",
                    "display_name": "Ranking Agent",
                    "summary": "Selected best listing",
                    "top_choice": {
                        "platform": "ebay",
                        "title": "Nike tee ebay",
                        "price": 30.0,
                        "score": 0.96,
                        "reason": "Best seller reputation",
                        "url": "https://ebay.example/1",
                        "seller": "seller-b",
                        "seller_score": 450,
                        "posted_at": "2026-04-05T09:05:00+00:00",
                    },
                    "candidate_count": 2,
                    "ranked_listings": [],
                    "median_price": 29.0,
                },
                "negotiation": {
                    "agent": "negotiation_agent",
                    "display_name": "Negotiation Agent",
                    "summary": "Prepared offers",
                    "offers": [
                        {
                            "platform": "ebay",
                            "seller": "seller-b",
                            "listing_url": "https://ebay.example/1",
                            "listing_title": "Nike tee ebay",
                            "target_price": 25.0,
                            "message": "Would you take $25?",
                            "status": "sent",
                            "conversation_url": "https://messages.example/1",
                            "execution_mode": "browser_use",
                            "attempt_source": "browser_use",
                        },
                        {
                            "platform": "depop",
                            "seller": "seller-a",
                            "listing_url": "https://depop.example/1",
                            "listing_title": "Nike tee depop",
                            "target_price": 24.0,
                            "message": "Would you take $24?",
                            "status": "failed",
                            "failure_reason": "seller unavailable",
                            "execution_mode": "deterministic",
                            "attempt_source": "prepared",
                        },
                    ],
                },
            },
        },
        events=[
            SessionEvent(
                session_id="buy-complete",
                event_type="agent_error",
                pipeline="buy",
                step="mercari_search",
                data={"step": "mercari_search"},
            ),
            SessionEvent(
                session_id="buy-complete",
                event_type="agent_error",
                pipeline="buy",
                step="offerup_search",
                data={"step": "offerup_search"},
            ),
        ],
    )

    view = build_run_payload(session)

    assert derive_phase(session) == "completed"
    assert derive_result_source(session) == "mixed"
    assert view["progress"] == {"step": "negotiation", "event_type": "agent_completed"}
    assert view["search_summary"] == {
        "total_results": 2,
        "results_by_platform": {"depop": 1, "ebay": 1, "mercari": 0, "offerup": 0},
        "platforms_searched": 2,
        "platforms_failed": 2,
        "median_price": 29.0,
    }
    assert view["top_choice"]["platform"] == "ebay"
    assert view["offer_summary"]["total_offers"] == 2
    assert view["offer_summary"]["offers_sent"] == 1
    assert view["offer_summary"]["offers_failed"] == 1
    assert view["offer_summary"]["best_offer"]["target_price"] == 25.0


def test_terminal_next_actions_map_completed_and_failed_states() -> None:
    completed_view = build_run_payload(
        SessionState(
            session_id="sell-completed",
            pipeline="sell",
            status="completed",
            request=PipelineStartRequest(input={"image_urls": ["https://example.com/item.jpg"]}),
            result={
                "pipeline": "sell",
                "outputs": {
                    "vision_analysis": {
                        "agent": "vision_agent",
                        "display_name": "Vision Agent",
                        "summary": "Done",
                        "detected_item": "hoodie",
                        "brand": "Nike",
                        "category": "apparel",
                        "condition": "good",
                        "confidence": 0.95,
                    }
                },
            },
        )
    )
    failed_view = build_run_payload(
        SessionState(
            session_id="sell-failed",
            pipeline="sell",
            status="failed",
            request=PipelineStartRequest(input={"image_urls": ["https://example.com/item.jpg"]}),
            result={
                "pipeline": "sell",
                "outputs": {
                    "vision_analysis": {
                        "agent": "vision_agent",
                        "display_name": "Vision Agent",
                        "summary": "Failed",
                        "detected_item": "hoodie",
                        "brand": "Nike",
                        "category": "apparel",
                        "condition": "good",
                        "confidence": 0.95,
                    }
                },
            },
        )
    )

    assert completed_view["next_action"]["type"] == "show_result"
    assert failed_view["next_action"]["type"] == "show_error"
