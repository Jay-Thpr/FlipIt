from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from backend.config import is_supabase_configured
from backend.repositories.items_projection import ItemProjectionRepository
from backend.repositories.market_data import MarketDataRepository
from backend.schemas import SessionState
from backend.supabase import SupabaseClient, get_supabase_client

logger = logging.getLogger(__name__)


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_condition(value: Any) -> str | None:
    condition = _coerce_text(value)
    if condition is None:
        return None
    return condition[:1].upper() + condition[1:]


def _first_number(*values: Any) -> float | None:
    for value in values:
        number = _coerce_number(value)
        if number is not None:
            return number
    return None


def _build_item_name(outputs: Mapping[str, Any]) -> str | None:
    listing = outputs.get("depop_listing")
    if isinstance(listing, Mapping):
        title = _coerce_text(listing.get("title"))
        if title is not None:
            return title

    vision = outputs.get("vision_analysis")
    if not isinstance(vision, Mapping):
        return None
    brand = _coerce_text(vision.get("brand"))
    detected_item = _coerce_text(vision.get("detected_item"))
    if brand is None and detected_item is None:
        return None
    return " ".join(part for part in (brand, detected_item) if part is not None)


def build_sell_item_projection(outputs: Mapping[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}

    name = _build_item_name(outputs)
    if name is not None:
        updates["name"] = name

    listing = outputs.get("depop_listing")
    if isinstance(listing, Mapping):
        description = _coerce_text(listing.get("description"))
        if description is not None:
            updates["description"] = description

        suggested_price = _coerce_number(listing.get("suggested_price"))
        if suggested_price is not None:
            updates["target_price"] = suggested_price

        listing_preview = listing.get("listing_preview")
        if isinstance(listing_preview, Mapping):
            condition = _normalize_condition(listing_preview.get("condition"))
            if condition is not None:
                updates["condition"] = condition

    vision = outputs.get("vision_analysis")
    if "condition" not in updates and isinstance(vision, Mapping):
        condition = _normalize_condition(vision.get("condition"))
        if condition is not None:
            updates["condition"] = condition

    pricing = outputs.get("pricing")
    if "target_price" not in updates and isinstance(pricing, Mapping):
        recommended_price = _coerce_number(pricing.get("recommended_list_price"))
        if recommended_price is not None:
            updates["target_price"] = recommended_price

    comps = outputs.get("ebay_sold_comps")
    if isinstance(comps, Mapping):
        low_price = _coerce_number(comps.get("low_sold_price"))
        high_price = _coerce_number(comps.get("high_sold_price"))
        if low_price is not None:
            updates["min_price"] = low_price
        if high_price is not None:
            updates["max_price"] = high_price

    return updates


def build_sell_market_data_snapshot(outputs: Mapping[str, Any]) -> dict[str, Any] | None:
    comps = outputs.get("ebay_sold_comps")
    pricing = outputs.get("pricing")
    if not isinstance(comps, Mapping) and not isinstance(pricing, Mapping):
        return None

    best_buy_price = None
    if isinstance(comps, Mapping):
        best_buy_price = _first_number(
            comps.get("median_sold_price"),
            comps.get("low_sold_price"),
            comps.get("high_sold_price"),
        )

    best_sell_price = None
    if isinstance(pricing, Mapping):
        best_sell_price = _coerce_number(pricing.get("recommended_list_price"))
    if best_sell_price is None and isinstance(comps, Mapping):
        best_sell_price = _first_number(
            comps.get("high_sold_price"),
            comps.get("median_sold_price"),
        )

    if best_buy_price is None or best_sell_price is None:
        return None

    volume = 0
    if isinstance(comps, Mapping):
        sample_size = comps.get("sample_size")
        if isinstance(sample_size, int) and sample_size >= 0:
            volume = sample_size

    return {
        "platform": "ebay",
        "best_buy_price": best_buy_price,
        "best_sell_price": best_sell_price,
        "volume": volume,
    }


def _session_identifiers(session: SessionState) -> tuple[str | None, str | None]:
    metadata = session.request.metadata if isinstance(session.request.metadata, Mapping) else {}
    item_id = _coerce_text(metadata.get("item_id"))
    user_id = _coerce_text(metadata.get("user_id")) or _coerce_text(session.request.user_id)
    return item_id, user_id


class SellWritebackManager:
    def __init__(
        self,
        *,
        enabled: bool = True,
        client_factory: Callable[[], SupabaseClient] = get_supabase_client,
        item_repository_factory: Callable[[Any], ItemProjectionRepository] = ItemProjectionRepository,
        market_data_repository_factory: Callable[[Any], MarketDataRepository] = MarketDataRepository,
    ) -> None:
        self.enabled = enabled
        self.client_factory = client_factory
        self.item_repository_factory = item_repository_factory
        self.market_data_repository_factory = market_data_repository_factory

    async def persist_session(self, session: SessionState) -> None:
        if not self.enabled or session.pipeline != "sell":
            return

        item_id, user_id = _session_identifiers(session)
        if item_id is None or user_id is None:
            return

        outputs = session.result.get("outputs", {}) if isinstance(session.result, Mapping) else {}
        if not isinstance(outputs, Mapping):
            return

        item_updates = build_sell_item_projection(outputs)
        market_snapshot = build_sell_market_data_snapshot(outputs)
        if not item_updates and market_snapshot is None:
            return

        try:
            client = self.client_factory()
            item_repository = self.item_repository_factory(client)
            market_data_repository = self.market_data_repository_factory(client)
            if item_updates:
                item_repository.update_item_projection(item_id=item_id, user_id=user_id, updates=item_updates)
            if market_snapshot is not None:
                market_data_repository.upsert_market_snapshot(
                    item_id=item_id,
                    platform=str(market_snapshot["platform"]),
                    snapshot={key: value for key, value in market_snapshot.items() if key != "platform"},
                )
        except Exception:
            logger.exception("sell projection writeback failed for session %s", session.session_id)


async def persist_sell_session_projection(session: SessionState) -> None:
    await SellWritebackManager(enabled=is_supabase_configured()).persist_session(session)
