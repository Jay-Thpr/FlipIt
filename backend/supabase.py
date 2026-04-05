"""Thin backend Supabase helper — httpx-based, no supabase-py SDK dependency."""
from __future__ import annotations

import time
from typing import Any

import httpx

from backend.config import (
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    is_supabase_configured,
)

# ---------------------------------------------------------------------------
# JWKS cache (module-level, in-process)
# ---------------------------------------------------------------------------
_jwks_cache: dict[str, Any] | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS: float = 300.0  # re-fetch every 5 minutes


def jwks_url() -> str:
    """Return the JWKS endpoint for the configured Supabase project."""
    base = SUPABASE_URL.rstrip("/")
    return f"{base}/auth/v1/.well-known/jwks.json"


async def fetch_jwks(force: bool = False) -> dict[str, Any]:
    """Fetch (or return cached) JWKS from Supabase Auth.

    Raises RuntimeError if Supabase is not configured.
    Raises httpx.HTTPError on network failure.
    """
    global _jwks_cache, _jwks_fetched_at

    if not is_supabase_configured():
        raise RuntimeError("Supabase is not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing)")

    now = time.monotonic()
    if not force and _jwks_cache is not None and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url())
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.monotonic()
        return _jwks_cache


def clear_jwks_cache() -> None:
    """Reset in-process JWKS cache (useful in tests)."""
    global _jwks_cache, _jwks_fetched_at
    _jwks_cache = None
    _jwks_fetched_at = 0.0


# ---------------------------------------------------------------------------
# Simple service-role client wrapper
# ---------------------------------------------------------------------------

class SupabaseClient:
    """Minimal httpx wrapper for service-role REST calls."""

    def __init__(self, url: str, service_role_key: str) -> None:
        self._base = url.rstrip("/")
        self._headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(f"{self._base}{path}", headers=self._headers, **kwargs)

    async def post(self, path: str, json: Any = None, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(f"{self._base}{path}", headers=self._headers, json=json, **kwargs)

    async def patch(self, path: str, json: Any = None, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.patch(f"{self._base}{path}", headers=self._headers, json=json, **kwargs)


def get_supabase_client() -> SupabaseClient:
    """Return a service-role SupabaseClient. Raises if not configured."""
    if not is_supabase_configured():
        raise RuntimeError("Supabase is not configured")
    return SupabaseClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
