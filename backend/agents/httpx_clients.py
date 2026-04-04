"""Lightweight httpx search clients for marketplace APIs.

These bypass Browser Use entirely — faster, no Chromium, no stealth needed.
Each function returns a list of normalized listing dicts on success, or None
on any failure (non-200, timeout, network error). Callers fall through to
Browser Use or deterministic fallback when None is returned.
"""
from __future__ import annotations

import base64
import os
from datetime import datetime, timezone

import httpx

_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

_DEFAULT_TIMEOUT = 15.0


async def search_depop_httpx(query: str, limit: int = 15) -> list[dict] | None:
    """Search Depop via their internal web API. Returns normalized listings or None."""
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                "https://webapi.depop.com/api/v2/search/products/",
                params={"q": query, "country": "us", "currency": "USD", "limit": limit},
                headers={
                    "User-Agent": _MOBILE_UA,
                    "Accept": "application/json",
                    "Referer": "https://www.depop.com/",
                },
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            products = data.get("products", [])
            today = datetime.now(timezone.utc).date().isoformat()

            return [
                {
                    "platform": "depop",
                    "title": (p.get("description") or "Depop listing")[:100],
                    "price": float(
                        p.get("price", {}).get("priceAmount", 0)
                        if isinstance(p.get("price"), dict)
                        else p.get("price", 0)
                    ),
                    "url": f"https://www.depop.com/products/{p.get('slug', p.get('id', ''))}",
                    "condition": (
                        p.get("attributes", {}).get("variant", {}).get("condition", "Used")
                        if isinstance(p.get("attributes"), dict)
                        else "Used"
                    ),
                    "seller": (
                        p.get("seller", {}).get("username", "unknown")
                        if isinstance(p.get("seller"), dict)
                        else "unknown"
                    ),
                    "seller_score": int(
                        p.get("seller", {}).get("reviewsTotal", 0)
                        if isinstance(p.get("seller"), dict)
                        else 0
                    ),
                    "posted_at": today,
                }
                for p in products
            ]
    except Exception:
        return None


async def search_mercari_httpx(query: str, limit: int = 15) -> list[dict] | None:
    """Search Mercari via their internal API. Returns normalized listings or None."""
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                "https://api.mercari.com/v2/entities:search",
                params={"keyword": query, "status": "STATUS_ON_SALE", "limit": limit},
                headers={
                    "User-Agent": _MOBILE_UA,
                    "X-Platform": "web",
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            items = data.get("items", [])
            today = datetime.now(timezone.utc).date().isoformat()

            return [
                {
                    "platform": "mercari",
                    "title": (item.get("name") or "Mercari listing")[:100],
                    "price": float(item.get("price", 0)),
                    "url": f"https://www.mercari.com/item/{item.get('id', '')}",
                    "condition": item.get("itemCondition", "Used"),
                    "seller": str(item.get("sellerId", "unknown")),
                    "seller_score": 0,
                    "posted_at": today,
                }
                for item in items
            ]
    except Exception:
        return None


async def get_ebay_oauth_token() -> str | None:
    """Get an eBay OAuth application token via client credentials flow."""
    app_id = os.getenv("EBAY_APP_ID")
    cert_id = os.getenv("EBAY_CERT_ID")
    if not app_id or not cert_id:
        return None

    credentials = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                "https://api.ebay.com/identity/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
            )
            if resp.status_code != 200:
                return None
            return resp.json().get("access_token")
    except Exception:
        return None


async def search_ebay_browse_api(query: str, limit: int = 15) -> list[dict] | None:
    """Search eBay active listings via official Browse API. Returns normalized listings or None."""
    token = await get_ebay_oauth_token()
    if not token:
        return None

    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                "https://api.ebay.com/buy/browse/v1/item_summary/search",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                    "Content-Type": "application/json",
                },
                params={
                    "q": query,
                    "filter": "buyingOptions:{FIXED_PRICE}",
                    "sort": "price",
                    "limit": limit,
                    "fieldgroups": "MATCHING_ITEMS",
                },
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            items = data.get("itemSummaries", [])
            today = datetime.now(timezone.utc).date().isoformat()

            return [
                {
                    "platform": "ebay",
                    "title": (item.get("title") or "eBay listing")[:100],
                    "price": float(item.get("price", {}).get("value", 0)),
                    "url": item.get("itemWebUrl", ""),
                    "condition": item.get("condition", "Used"),
                    "seller": item.get("seller", {}).get("username", "unknown"),
                    "seller_score": int(
                        item.get("seller", {}).get("feedbackScore", 0)
                    ),
                    "posted_at": today,
                }
                for item in items
            ]
    except Exception:
        return None
