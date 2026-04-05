"""Tests for backend/buy_writeback.py — buy-side durable writeback into Supabase."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
import pytest

from backend.buy_writeback import (
    _extract_sent_offers,
    _extract_top_choice_url,
    write_back_buy_result,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_offer(
    *,
    status: str = "sent",
    listing_url: str = "https://depop.example/1",
    listing_title: str = "Vintage tee",
    platform: str = "depop",
    seller: str = "seller-1",
    target_price: float = 32.0,
    message: str = "Would you take $32?",
    conversation_url: str | None = "https://messages.example/1",
) -> dict[str, Any]:
    return {
        "platform": platform,
        "seller": seller,
        "listing_url": listing_url,
        "listing_title": listing_title,
        "target_price": target_price,
        "message": message,
        "status": status,
        "conversation_url": conversation_url,
    }


def _make_outputs(
    *,
    offers: list[dict] | None = None,
    top_choice_url: str | None = "https://depop.example/1",
) -> dict[str, Any]:
    ranking: dict[str, Any] = {}
    if top_choice_url:
        ranking["top_choice"] = {"url": top_choice_url, "platform": "depop", "price": 38.0}

    negotiation: dict[str, Any] = {}
    if offers is not None:
        negotiation["offers"] = offers

    return {"ranking": ranking, "negotiation": negotiation}


# ---------------------------------------------------------------------------
# Unit: _extract_sent_offers
# ---------------------------------------------------------------------------

def test_extract_sent_offers_returns_only_sent():
    outputs = _make_outputs(offers=[
        _make_offer(status="sent"),
        _make_offer(status="failed", listing_url="https://depop.example/2"),
        _make_offer(status="prepared", listing_url="https://depop.example/3"),
    ])
    result = _extract_sent_offers(outputs)
    assert len(result) == 1
    assert result[0]["listing_url"] == "https://depop.example/1"


def test_extract_sent_offers_empty_when_no_negotiation():
    assert _extract_sent_offers({}) == []


def test_extract_sent_offers_empty_when_offers_not_list():
    assert _extract_sent_offers({"negotiation": {"offers": "bad"}}) == []


def test_extract_sent_offers_skips_non_dict_entries():
    outputs = {"negotiation": {"offers": [None, "string", _make_offer(status="sent")]}}
    result = _extract_sent_offers(outputs)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Unit: _extract_top_choice_url
# ---------------------------------------------------------------------------

def test_extract_top_choice_url_returns_url():
    outputs = _make_outputs(top_choice_url="https://depop.example/1")
    assert _extract_top_choice_url(outputs) == "https://depop.example/1"


def test_extract_top_choice_url_none_when_no_ranking():
    assert _extract_top_choice_url({}) is None


def test_extract_top_choice_url_none_when_no_top_choice():
    assert _extract_top_choice_url({"ranking": {}}) is None


# ---------------------------------------------------------------------------
# async: write_back_buy_result — no-op paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_back_no_op_when_supabase_not_configured():
    with patch("backend.buy_writeback.is_supabase_configured", return_value=False):
        with patch("backend.buy_writeback.get_supabase_client") as mock_client:
            await write_back_buy_result(
                session_id="s1",
                user_id="user-1",
                outputs=_make_outputs(offers=[_make_offer()]),
            )
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_write_back_no_op_when_user_id_missing():
    with patch("backend.buy_writeback.is_supabase_configured", return_value=True):
        with patch("backend.buy_writeback.get_supabase_client") as mock_client:
            await write_back_buy_result(
                session_id="s1",
                user_id=None,
                outputs=_make_outputs(offers=[_make_offer()]),
            )
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_write_back_no_op_when_no_sent_offers():
    with patch("backend.buy_writeback.is_supabase_configured", return_value=True):
        with patch("backend.buy_writeback.get_supabase_client") as mock_client:
            await write_back_buy_result(
                session_id="s1",
                user_id="user-1",
                outputs=_make_outputs(offers=[_make_offer(status="failed")]),
            )
    mock_client.assert_not_called()


# ---------------------------------------------------------------------------
# async: write_back_buy_result — successful writeback
# ---------------------------------------------------------------------------

def _make_mock_repos():
    """Return (conv_repo, msg_repo, trade_repo) mocks wired to return predictable rows."""
    conv_repo = MagicMock()
    conv_row = {"id": "conv-id-1", "listing_url": "https://depop.example/1"}
    conv_repo.upsert_conversation.return_value = conv_row

    msg_repo = MagicMock()
    msg_repo.create_message.return_value = {"id": "msg-id-1"}

    trade_repo = MagicMock()
    trade_repo.create_trade.return_value = {"id": "trade-id-1"}

    return conv_repo, msg_repo, trade_repo


@pytest.mark.asyncio
async def test_write_back_calls_upsert_conversation_for_sent_offer():
    conv_repo, msg_repo, trade_repo = _make_mock_repos()

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(offers=[_make_offer()]),
        )

    conv_repo.upsert_conversation.assert_called_once()
    call_kwargs = conv_repo.upsert_conversation.call_args[0][0]
    assert call_kwargs["user_id"] == "user-1"
    assert call_kwargs["listing_url"] == "https://depop.example/1"
    assert call_kwargs["platform"] == "depop"
    assert call_kwargs["status"] == "active"


@pytest.mark.asyncio
async def test_write_back_creates_message_when_conv_and_message_present():
    conv_repo, msg_repo, trade_repo = _make_mock_repos()

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(offers=[_make_offer(message="Would you take $32?")]),
        )

    msg_repo.create_message.assert_called_once()
    msg_kwargs = msg_repo.create_message.call_args[0][0]
    assert msg_kwargs["conversation_id"] == "conv-id-1"
    assert msg_kwargs["role"] == "user"
    assert msg_kwargs["content"] == "Would you take $32?"
    assert msg_kwargs["target_price"] == 32.0


@pytest.mark.asyncio
async def test_write_back_creates_completed_trade_for_top_choice():
    conv_repo, msg_repo, trade_repo = _make_mock_repos()

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(
                offers=[_make_offer(listing_url="https://depop.example/1")],
                top_choice_url="https://depop.example/1",
            ),
        )

    trade_repo.create_trade.assert_called_once()
    trade_kwargs = trade_repo.create_trade.call_args[0][0]
    assert trade_kwargs["user_id"] == "user-1"
    assert trade_kwargs["listing_url"] == "https://depop.example/1"
    assert trade_kwargs["final_price"] == 32.0
    assert trade_kwargs["run_id"] == "s1"
    assert trade_kwargs["conversation_id"] == "conv-id-1"


@pytest.mark.asyncio
async def test_write_back_no_trade_when_top_choice_url_does_not_match():
    conv_repo, msg_repo, trade_repo = _make_mock_repos()

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(
                offers=[_make_offer(listing_url="https://depop.example/1")],
                top_choice_url="https://depop.example/DIFFERENT",
            ),
        )

    trade_repo.create_trade.assert_not_called()


@pytest.mark.asyncio
async def test_write_back_no_trade_when_no_top_choice():
    conv_repo, msg_repo, trade_repo = _make_mock_repos()

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(
                offers=[_make_offer()],
                top_choice_url=None,
            ),
        )

    trade_repo.create_trade.assert_not_called()


@pytest.mark.asyncio
async def test_write_back_trade_written_only_once_for_multiple_sent_offers():
    """Even if multiple sent offers match the top_choice URL, only one trade is created."""
    conv_repo, msg_repo, trade_repo = _make_mock_repos()
    conv_repo.upsert_conversation.return_value = {"id": "conv-id-1"}

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(
                offers=[
                    _make_offer(listing_url="https://depop.example/1"),
                    _make_offer(listing_url="https://depop.example/1"),  # duplicate
                ],
                top_choice_url="https://depop.example/1",
            ),
        )

    assert trade_repo.create_trade.call_count == 1


# ---------------------------------------------------------------------------
# async: write_back_buy_result — partial data / missing fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_back_skips_offer_with_no_listing_url():
    conv_repo, msg_repo, trade_repo = _make_mock_repos()

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        offer_no_url = {**_make_offer(), "listing_url": None}
        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(offers=[offer_no_url]),
        )

    conv_repo.upsert_conversation.assert_not_called()


@pytest.mark.asyncio
async def test_write_back_skips_message_when_offer_has_no_message():
    conv_repo, msg_repo, trade_repo = _make_mock_repos()

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        offer_no_message = {**_make_offer(), "message": ""}
        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(offers=[offer_no_message]),
        )

    msg_repo.create_message.assert_not_called()


@pytest.mark.asyncio
async def test_write_back_still_creates_trade_when_conv_upsert_fails():
    """If conversation upsert throws, the trade record is still attempted (without conversation_id)."""
    conv_repo, msg_repo, trade_repo = _make_mock_repos()
    conv_repo.upsert_conversation.side_effect = RuntimeError("db error")

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(
                offers=[_make_offer(listing_url="https://depop.example/1")],
                top_choice_url="https://depop.example/1",
            ),
        )

    # Trade attempted with conversation_id=None because conv was None
    trade_repo.create_trade.assert_called_once()
    assert trade_repo.create_trade.call_args[0][0]["conversation_id"] is None


@pytest.mark.asyncio
async def test_write_back_continues_after_message_write_failure():
    """Message write failure must not prevent subsequent offers from being processed."""
    conv_repo, msg_repo, trade_repo = _make_mock_repos()
    # Second conv upsert returns a different id
    conv_repo.upsert_conversation.side_effect = [
        {"id": "conv-1"},
        {"id": "conv-2"},
    ]
    msg_repo.create_message.side_effect = RuntimeError("message db error")

    with patch("backend.buy_writeback.is_supabase_configured", return_value=True), \
         patch("backend.buy_writeback.get_supabase_client"), \
         patch("backend.buy_writeback.ConversationRepository", return_value=conv_repo), \
         patch("backend.buy_writeback.MessageRepository", return_value=msg_repo), \
         patch("backend.buy_writeback.CompletedTradeRepository", return_value=trade_repo):

        await write_back_buy_result(
            session_id="s1",
            user_id="user-1",
            outputs=_make_outputs(
                offers=[
                    _make_offer(listing_url="https://depop.example/1"),
                    _make_offer(listing_url="https://depop.example/2", status="sent"),
                ],
                top_choice_url="https://depop.example/1",
            ),
        )

    # Both conversations were attempted
    assert conv_repo.upsert_conversation.call_count == 2
    # Trade still created for the top-choice
    trade_repo.create_trade.assert_called_once()
