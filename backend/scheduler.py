"""Background scheduler that continuously runs agent pipelines for active items."""
from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4

from backend.config import is_supabase_configured
from backend.orchestrator import run_pipeline
from backend.repositories.items import ItemRepository
from backend.schemas import PipelineStartRequest
from backend.session import session_manager
from backend.supabase import get_supabase_client

logger = logging.getLogger(__name__)

SCHEDULER_INTERVAL_SECONDS = int(os.environ.get("SCHEDULER_INTERVAL", "300"))

# Item IDs with an in-flight pipeline — prevents duplicate concurrent runs.
_in_flight: set[str] = set()


def _build_sell_input(item: dict) -> dict:
    photos = item.get("item_photos") or []
    photos_sorted = sorted(photos, key=lambda p: p.get("sort_order", 0))
    image_urls = [p["photo_url"] for p in photos_sorted if p.get("photo_url")]
    return {
        "image_urls": image_urls,
        "notes": item.get("description") or item.get("name") or "resale item",
    }


def _build_buy_input(item: dict) -> dict:
    return {
        "query": item.get("name") or "resale item",
        "budget": item.get("initial_price") or item.get("target_price"),
    }


async def _run_item_pipeline(item: dict) -> None:
    """Run the appropriate pipeline for a single item, then remove from in-flight set."""
    item_id: str = item["id"]
    pipeline: str = item.get("type", "buy")
    try:
        input_data = _build_sell_input(item) if pipeline == "sell" else _build_buy_input(item)

        request = PipelineStartRequest(
            user_id=item.get("user_id"),
            input=input_data,
            metadata={
                "item_id": item_id,
                "user_id": item.get("user_id"),
                "source": "scheduler",
            },
        )

        session_id = f"sched-{item_id[:8]}-{uuid4().hex[:8]}"
        await session_manager.create_session(
            session_id=session_id, pipeline=pipeline, request=request,
        )
        await run_pipeline(session_id, pipeline, request)
    except Exception:
        logger.exception("Scheduler pipeline failed for item %s", item_id)
    finally:
        _in_flight.discard(item_id)


async def run_scheduler_sweep() -> None:
    """Query active items and kick off pipelines for any that aren't already running."""
    if not is_supabase_configured():
        return

    client = get_supabase_client()
    repo = ItemRepository(client)
    active_items = repo.list_active_items()

    launched = 0
    for item in active_items:
        item_id = item.get("id")
        if not item_id or item_id in _in_flight:
            continue

        _in_flight.add(item_id)
        asyncio.create_task(_run_item_pipeline(item))
        launched += 1

    if launched:
        logger.info("Scheduler launched %d pipeline(s) (%d still in-flight)", launched, len(_in_flight))


async def scheduler_loop() -> None:
    """Long-running loop — call from the FastAPI lifespan."""
    logger.info("Item scheduler started (interval=%ds)", SCHEDULER_INTERVAL_SECONDS)
    while True:
        try:
            await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
            await run_scheduler_sweep()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduler sweep failed")
