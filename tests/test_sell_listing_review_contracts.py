from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas import SellListingDecisionRequest, SellListingReviewState, SessionState


def test_sell_listing_decision_accepts_confirm_submit_without_revision_text() -> None:
    request = SellListingDecisionRequest(
        session_id="sell-review-session",
        decision="confirm_submit",
    )

    assert request.session_id == "sell-review-session"
    assert request.decision == "confirm_submit"
    assert request.revision_instructions is None


def test_sell_listing_decision_requires_revision_text_for_revise() -> None:
    with pytest.raises(ValidationError, match="revision_instructions is required"):
        SellListingDecisionRequest(
            session_id="sell-review-session",
            decision="revise",
            revision_instructions="   ",
        )


def test_sell_listing_decision_trims_revision_text() -> None:
    request = SellListingDecisionRequest(
        session_id="sell-review-session",
        decision="revise",
        revision_instructions="  lower the price to $85 and shorten the description  ",
    )

    assert request.revision_instructions == "lower the price to $85 and shorten the description"


def test_session_state_supports_paused_sell_listing_review_metadata() -> None:
    session = SessionState.model_validate(
        {
            "session_id": "sell-review-session",
            "pipeline": "sell",
            "status": "paused",
            "request": {"input": {"image_urls": ["https://example.com/item.jpg"]}},
            "sell_listing_review": {
                "state": "ready_for_confirmation",
                "step": "depop_listing",
                "platform": "depop",
                "latest_decision": "revise",
                "revision_instructions": "change the condition to good",
                "revision_count": 1,
                "paused_at": "2026-04-04T12:00:00+00:00",
                "deadline_at": "2026-04-04T12:05:00+00:00",
            },
        }
    )

    assert session.status == "paused"
    assert session.sell_listing_review is not None
    assert session.sell_listing_review.state == "ready_for_confirmation"
    assert session.sell_listing_review.latest_decision == "revise"
    assert session.sell_listing_review.revision_count == 1


def test_sell_listing_review_state_defaults_step_and_platform() -> None:
    review = SellListingReviewState(state="filling_form")

    assert review.step == "depop_listing"
    assert review.platform == "depop"
    assert review.revision_count == 0
