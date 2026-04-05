"""Buy-side durable writeback: projects negotiation results into frontend-visible Supabase records.

Safe to call regardless of Supabase configuration:
- Returns immediately when Supabase is not configured.
- Returns immediately when user_id is missing.
- Each individual write failure is logged and skipped so the pipeline is never blocked.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.config import is_supabase_configured
from backend.repositories.conversations import ConversationRepository
from backend.repositories.messages import MessageRepository
from backend.run_records import utc_now_iso
from backend.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def _extract_sent_offers(outputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all NegotiationAttempt dicts with status='sent' from buy pipeline outputs."""
    negotiation = outputs.get("negotiation")
    if not isinstance(negotiation, dict):
        return []
    offers = negotiation.get("offers")
    if not isinstance(offers, list):
        return []
    return [o for o in offers if isinstance(o, dict) and o.get("status") == "sent"]


def _extract_top_choice_url(outputs: dict[str, Any]) -> str | None:
    """Return the URL of the top_choice from ranking output, or None."""
    ranking = outputs.get("ranking")
    if not isinstance(ranking, dict):
        return None
    top_choice = ranking.get("top_choice")
    if not isinstance(top_choice, dict):
        return None
    url = top_choice.get("url")
    return str(url) if url else None


async def write_back_buy_result(
    *,
    session_id: str,
    user_id: str | None,
    item_id: str | None = None,
    outputs: dict[str, Any],
) -> None:
    """Project buy pipeline negotiation/ranking results into durable frontend records.

    For each sent offer:
    - Upserts a conversation record (user_id + listing_url as natural key).
    - Creates a message record containing the negotiation message.

    A completed_trade is NOT written here — a sent offer does not mean a trade is
    complete. That record should only be created on a real purchase-close signal
    (seller accepts, payment confirmed, etc.).
    """
    if not is_supabase_configured():
        return
    if not user_id:
        return

    sent_offers = _extract_sent_offers(outputs)
    if not sent_offers:
        return

    try:
        client = get_supabase_client()
        conv_repo = ConversationRepository(client)
        msg_repo = MessageRepository(client)
    except Exception:
        logger.exception("buy writeback: failed to initialise Supabase client for session %s", session_id)
        return

    for offer in sent_offers:
        listing_url = offer.get("listing_url")
        if not listing_url:
            continue

        # --- upsert conversation ---
        conv: dict[str, Any] | None = None
        message_text = offer.get("message")
        try:
            conv = conv_repo.upsert_conversation({
                "user_id": user_id,
                "platform": offer.get("platform"),
                "listing_url": listing_url,
                "listing_title": offer.get("listing_title"),
                "seller": offer.get("seller"),
                "status": "offer_sent",
                "item_id": item_id,
                "username": offer.get("seller", ""),
                "last_message": message_text or "",
                "last_message_at": utc_now_iso(),
            })
        except Exception:
            logger.exception(
                "buy writeback: failed to upsert conversation for listing %s session %s",
                listing_url,
                session_id,
            )

        # --- persist negotiation message ---
        if conv and message_text:
            try:
                msg_repo.create_message({
                    "conversation_id": conv["id"],
                    "sender": "agent",
                    "text": message_text,
                    "target_price": offer.get("target_price"),
                })
            except Exception:
                logger.exception(
                    "buy writeback: failed to create message for conversation %s session %s",
                    conv.get("id"),
                    session_id,
                )
