from __future__ import annotations

from backend.frontend_runs import build_run_payload
from backend.run_records import build_agent_run_event_row, build_agent_run_row
from backend.schemas import PipelineStartRequest, SessionEvent, SessionState, SellListingReviewState


def test_session_state_maps_into_persisted_sell_run_row() -> None:
    review = SellListingReviewState(
        state="ready_for_confirmation",
        revision_count=1,
        revision_instructions="Lower the price a little",
        paused_at="2026-04-05T10:00:00+00:00",
        deadline_at="2026-04-05T10:15:00+00:00",
    )
    session = SessionState(
        session_id="run-mapping-sell",
        pipeline="sell",
        status="paused",
        request=PipelineStartRequest(
            user_id="user-1",
            input={"image_urls": ["https://example.com/item.jpg"], "notes": "Vintage hoodie"},
            metadata={"item_id": "item-sell-1"},
        ),
        sell_listing_review=review,
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
                },
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
                    "summary": "Ready for confirmation",
                    "title": "Vintage Nike hoodie",
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

    frontend_view = build_run_payload(session)
    row = build_agent_run_row(
        session_id=session.session_id,
        user_id=session.request.user_id or "user-1",
        pipeline=session.pipeline,
        item_id=session.request.metadata["item_id"],
        status=session.status,
        phase=frontend_view["phase"],
        next_action_type=frontend_view["next_action"]["type"],
        next_action_payload=frontend_view["next_action"]["payload"],
        request_payload=session.request.model_dump(),
        result_payload=frontend_view,
        error=session.error,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )

    assert row["session_id"] == session.session_id
    assert row["item_id"] == "item-sell-1"
    assert row["pipeline"] == "sell"
    assert row["phase"] == "awaiting_listing_review"
    assert row["next_action_type"] == "review_listing"
    assert row["next_action_payload"]["review_state"]["state"] == "ready_for_confirmation"
    assert row["request_payload"]["metadata"]["item_id"] == "item-sell-1"
    assert row["result_payload"]["sell_summary"]["listing_title"] == "Vintage Nike hoodie"
    assert row["result_payload"]["phase"] == frontend_view["phase"]


def test_session_event_maps_into_persisted_run_event_row() -> None:
    event = SessionEvent(
        session_id="run-mapping-buy",
        event_type="agent_completed",
        pipeline="buy",
        step="ranking",
        data={
            "top_choice": {
                "platform": "depop",
                "title": "Vintage tee",
                "price": 30.0,
                "score": 0.94,
                "reason": "Best match",
                "url": "https://example.com/listing",
                "seller": "seller-1",
                "seller_score": 10,
                "posted_at": "2026-04-05T10:00:00+00:00",
            }
        },
    )

    row = build_agent_run_event_row(
        run_id="run-123",
        session_id=event.session_id,
        event_type=event.event_type,
        step=event.step,
        payload=event.data,
        created_at=event.timestamp,
    )

    assert row["run_id"] == "run-123"
    assert row["session_id"] == event.session_id
    assert row["event_type"] == "agent_completed"
    assert row["step"] == "ranking"
    assert row["payload"] == event.data
    assert row["created_at"] == event.timestamp
