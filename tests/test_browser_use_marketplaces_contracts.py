from __future__ import annotations

from backend.agents.browser_use_marketplaces import (
    build_depop_listing_abort_task,
    build_depop_listing_prepare_task,
    build_depop_listing_revision_task,
    build_depop_listing_submit_task,
)


def test_depop_listing_prepare_task_pins_non_mobile_review_contract() -> None:
    task = build_depop_listing_prepare_task(
        title="Patagonia hoodie - Excellent Condition",
        description="Prepared description",
        suggested_price=78.43,
        category_path="Men/Tops/Hoodies",
        image_path="/tmp/item.jpg",
    )

    assert "desktop or non-mobile listing layout" in task
    assert 'Upload the local file at path "/tmp/item.jpg" as the first listing photo.' in task
    assert "Stop at the final publish or submit action and do not click it." in task
    assert 'listing_status set to "ready_for_confirmation"' in task
    assert "Never click the final publish or submit button during this prepare phase." in task


def test_depop_listing_revision_task_preserves_review_checkpoint_and_does_not_submit() -> None:
    task = build_depop_listing_revision_task(
        revision_instructions="Lower the price and shorten the description",
        title="Patagonia hoodie - Excellent Condition",
        description="Prepared description",
        suggested_price=78.43,
        category_path="Men/Tops/Hoodies",
    )

    assert "Apply these revision instructions to the current form:" in task
    assert "Lower the price and shorten the description" in task
    assert "Preserve any fields the user did not ask to change." in task
    assert "Do not submit or publish the listing." in task
    assert 'listing_status set to "ready_for_confirmation"' in task


def test_depop_listing_submit_and_abort_tasks_are_explicit() -> None:
    submit_task = build_depop_listing_submit_task()
    abort_task = build_depop_listing_abort_task()

    assert "perform the final publish or submit action" in submit_task
    assert 'listing_status set to "submitted"' in submit_task
    assert 'draft_status set to "submitted"' in submit_task

    assert "Close, discard, or otherwise abandon the draft without publishing it." in abort_task
    assert 'listing_status set to "aborted"' in abort_task
    assert 'draft_status set to "aborted"' in abort_task

