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
from backend.repositories.completed_trades import CompletedTradeRepository
from backend.repositories.conversations import ConversationRepository
from backend.repositories.messages import MessageRepository
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
    outputs: dict[str, Any],
) -> None:
    """Project buy pipeline negotiation/ranking results into durable frontend records.

    For each sent offer:
    - Upserts a conversation record (user_id + listing_url as natural key).
    - Creates a message record containing the negotiation message.

    For the top-choice listing where an offer was sent:
    - Creates one completed_trade record per session.
    """
    if not is_supabase_configured():
        return
    if not user_id:
        return

    sent_offers = _extract_sent_offers(outputs)
    if not sent_offers:
        return

    top_choice_url = _extract_top_choice_url(outputs)

    try:
        client = get_supabase_client()
        conv_repo = ConversationRepository(client)
        msg_repo = MessageRepository(client)
        trade_repo = CompletedTradeRepository(client)
    except Exception:
        logger.exception("buy writeback: failed to initialise Supabase client for session %s", session_id)
        return

    trade_written = False

    for offer in sent_offers:
        listing_url = offer.get("listing_url")
        if not listing_url:
            continue

        # --- upsert conversation ---
        conv: dict[str, Any] | None = None
        try:
            conv = conv_repo.upsert_conversation({
                "user_id": user_id,
                "platform": offer.get("platform"),
                "listing_url": listing_url,
                "listing_title": offer.get("listing_title"),
                "seller": offer.get("seller"),
                "status": "active",
            })
        except Exception:
            logger.exception(
                "buy writeback: failed to upsert conversation for listing %s session %s",
                listing_url,
                session_id,
            )

        # --- persist negotiation message ---
        message_text = offer.get("message")
        if conv and message_text:
            try:
                msg_repo.create_message({
                    "conversation_id": conv["id"],
                    "role": "user",
                    "content": message_text,
                    "target_price": offer.get("target_price"),
                })
            except Exception:
                logger.exception(
                    "buy writeback: failed to create message for conversation %s session %s",
                    conv.get("id"),
                    session_id,
                )

        # --- persist completed trade for the top-choice listing (once per session) ---
        if not trade_written and top_choice_url and listing_url == top_choice_url:
            try:
                trade_repo.create_trade({
                    "user_id": user_id,
                    "platform": offer.get("platform"),
                    "listing_url": listing_url,
                    "listing_title": offer.get("listing_title"),
                    "final_price": offer.get("target_price"),
                    "seller": offer.get("seller"),
                    "conversation_id": conv["id"] if conv else None,
                    "run_id": session_id,
                })
                trade_written = True
            except Exception:
                logger.exception(
                    "buy writeback: failed to create completed_trade for session %s",
                    session_id,
                )
