"""Tests for httpx marketplace search clients and agent integration.

Covers Topics 1 (Depop), 2 (Mercari), and 3 (eBay Browse API) from the
implementation plan. All external HTTP calls are mocked — no real API
credentials or network access required.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from backend.agents.httpx_clients import (
    search_depop_httpx,
    search_ebay_browse_api,
    search_mercari_httpx,
    get_ebay_oauth_token,
)
from backend.schemas import EbaySoldCompsOutput, SearchResultsOutput


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_depop_response() -> dict:
    return {
        "products": [
            {
                "description": "Vintage Nike hoodie great condition",
                "price": {"priceAmount": 42.0},
                "slug": "vintage-nike-hoodie-1",
                "attributes": {"variant": {"condition": "Good"}},
                "seller": {"username": "thrift_king", "reviewsTotal": 23},
            },
            {
                "description": "Nike Air Force 1 sneakers",
                "price": {"priceAmount": 65.0},
                "slug": "nike-af1-white",
                "attributes": {},
                "seller": {"username": "sneaker_vault", "reviewsTotal": 99},
            },
        ]
    }


def _mock_mercari_response() -> dict:
    return {
        "items": [
            {
                "name": "Carhartt WIP jacket XL",
                "price": 55,
                "id": "m123",
                "itemCondition": "Like New",
                "sellerId": "shop_456",
            },
            {
                "name": "Vintage Levi's 501",
                "price": 38,
                "id": "m789",
                "itemCondition": "Good",
                "sellerId": "denim_deals",
            },
        ]
    }


def _mock_ebay_browse_response() -> dict:
    return {
        "itemSummaries": [
            {
                "title": "Nike Air Jordan 1 Retro High OG",
                "price": {"value": "145.00"},
                "itemWebUrl": "https://www.ebay.com/itm/12345",
                "condition": "Used",
                "seller": {"username": "kicks_empire", "feedbackScore": 1200},
            },
        ]
    }


def _make_httpx_response(status_code: int, json_data: dict | None = None) -> httpx.Response:
    resp = httpx.Response(status_code=status_code)
    if json_data is not None:
        resp._content = __import__("json").dumps(json_data).encode()
        resp.headers["content-type"] = "application/json"
    return resp


# ── Topic 1: Depop httpx ────────────────────────────────────────────────────


class TestSearchDepopHttpx:
    def test_returns_normalized_listings(self):
        mock_resp = _make_httpx_response(200, _mock_depop_response())
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = asyncio.run(search_depop_httpx("nike hoodie"))

        assert results is not None
        assert len(results) == 2
        for r in results:
            assert r["platform"] == "depop"
            assert "title" in r
            assert "price" in r
            assert "url" in r
            assert "condition" in r
            assert "seller" in r
            assert "seller_score" in r
            assert "posted_at" in r
        assert results[0]["price"] == 42.0
        assert results[0]["seller"] == "thrift_king"

    def test_returns_none_on_403(self):
        mock_resp = _make_httpx_response(403)
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = asyncio.run(search_depop_httpx("nike hoodie"))

        assert results is None

    def test_returns_none_on_timeout(self):
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = asyncio.run(search_depop_httpx("nike hoodie"))

        assert results is None

    def test_returns_none_on_network_error(self):
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = asyncio.run(search_depop_httpx("nike hoodie"))

        assert results is None


# ── Topic 2: Mercari httpx ──────────────────────────────────────────────────


class TestSearchMercariHttpx:
    def test_returns_normalized_listings(self):
        mock_resp = _make_httpx_response(200, _mock_mercari_response())
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = asyncio.run(search_mercari_httpx("carhartt jacket"))

        assert results is not None
        assert len(results) == 2
        for r in results:
            assert r["platform"] == "mercari"
            assert "title" in r
            assert "price" in r
            assert "url" in r
        assert results[0]["price"] == 55.0
        assert "m123" in results[0]["url"]

    def test_returns_none_on_non_200(self):
        mock_resp = _make_httpx_response(500)
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = asyncio.run(search_mercari_httpx("carhartt jacket"))

        assert results is None

    def test_returns_none_on_timeout(self):
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = asyncio.run(search_mercari_httpx("carhartt jacket"))

        assert results is None


# ── Topic 3: eBay Browse API ────────────────────────────────────────────────


class TestGetEbayOauthToken:
    def test_returns_token_on_success(self):
        mock_resp = _make_httpx_response(200, {"access_token": "v^1.1#i^1#p^1#bearer_token"})
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch.dict("os.environ", {"EBAY_APP_ID": "test_id", "EBAY_CERT_ID": "test_cert"}):
                token = asyncio.run(get_ebay_oauth_token())

        assert token == "v^1.1#i^1#p^1#bearer_token"

    def test_returns_none_without_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            # Also clear any existing vars
            import os
            old_app = os.environ.pop("EBAY_APP_ID", None)
            old_cert = os.environ.pop("EBAY_CERT_ID", None)
            try:
                token = asyncio.run(get_ebay_oauth_token())
                assert token is None
            finally:
                if old_app:
                    os.environ["EBAY_APP_ID"] = old_app
                if old_cert:
                    os.environ["EBAY_CERT_ID"] = old_cert

    def test_returns_none_on_auth_failure(self):
        mock_resp = _make_httpx_response(401)
        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch.dict("os.environ", {"EBAY_APP_ID": "bad_id", "EBAY_CERT_ID": "bad_cert"}):
                token = asyncio.run(get_ebay_oauth_token())

        assert token is None


class TestSearchEbayBrowseApi:
    def test_returns_normalized_listings(self):
        token_resp = _make_httpx_response(200, {"access_token": "test_token"})
        search_resp = _make_httpx_response(200, _mock_ebay_browse_response())

        with patch("backend.agents.httpx_clients.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=token_resp)
            instance.get = AsyncMock(return_value=search_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch.dict("os.environ", {"EBAY_APP_ID": "test_id", "EBAY_CERT_ID": "test_cert"}):
                results = asyncio.run(search_ebay_browse_api("air jordan 1"))

        assert results is not None
        assert len(results) == 1
        assert results[0]["platform"] == "ebay"
        assert results[0]["price"] == 145.0
        assert results[0]["seller"] == "kicks_empire"

    def test_returns_none_on_no_credentials(self):
        import os
        old_app = os.environ.pop("EBAY_APP_ID", None)
        old_cert = os.environ.pop("EBAY_CERT_ID", None)
        try:
            results = asyncio.run(search_ebay_browse_api("air jordan 1"))
            assert results is None
        finally:
            if old_app:
                os.environ["EBAY_APP_ID"] = old_app
            if old_cert:
                os.environ["EBAY_CERT_ID"] = old_cert


# ── Schema validation ───────────────────────────────────────────────────────


class TestSchemaHttpxMode:
    def test_search_results_accepts_httpx_mode(self):
        output = SearchResultsOutput(
            agent="depop_search_agent",
            display_name="Depop Search Agent",
            summary="Found 5 listings",
            execution_mode="httpx",
        )
        assert output.execution_mode == "httpx"

    def test_ebay_comps_accepts_httpx_mode(self):
        output = EbaySoldCompsOutput(
            agent="ebay_sold_comps_agent",
            display_name="eBay Sold Comps Agent",
            summary="Found 10 comps",
            median_sold_price=50.0,
            low_sold_price=30.0,
            high_sold_price=70.0,
            sample_size=10,
            execution_mode="httpx",
        )
        assert output.execution_mode == "httpx"
