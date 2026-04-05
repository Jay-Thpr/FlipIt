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
# PostgREST query builder
# ---------------------------------------------------------------------------

class _QueryResult:
    """Wrapper around a PostgREST response so callers can use .data."""

    def __init__(self, data: Any) -> None:
        self.data = data


class TableQueryBuilder:
    """Fluent PostgREST query builder returned by SupabaseClient.table()."""

    def __init__(self, client: SupabaseClient, table_name: str) -> None:
        self._client = client
        self._table = table_name
        self._select_cols: str = "*"
        self._filters: list[tuple[str, str]] = []  # (column, "eq.value")
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._limit_n: int | None = None
        self._payload: Any = None
        self._operation: str = "select"  # "select", "insert", "update"

    # --- builder methods ---------------------------------------------------

    def select(self, *columns: str) -> TableQueryBuilder:
        self._select_cols = ",".join(columns) if columns else "*"
        self._operation = "select"
        return self

    def eq(self, column: str, value: Any) -> TableQueryBuilder:
        self._filters.append((column, str(value)))
        return self

    def order(self, column: str, desc: bool = False) -> TableQueryBuilder:
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, count: int) -> TableQueryBuilder:
        self._limit_n = count
        return self

    def insert(self, payload: Any) -> TableQueryBuilder:
        self._payload = payload
        self._operation = "insert"
        return self

    def update(self, payload: Any) -> TableQueryBuilder:
        self._payload = payload
        self._operation = "update"
        return self

    # --- internal helpers --------------------------------------------------

    def _build_params(self) -> dict[str, str]:
        params: dict[str, str] = {}

        if self._operation == "select":
            params["select"] = self._select_cols

        # eq filters apply to select and update (not insert)
        if self._operation != "insert":
            for col, val in self._filters:
                params[col] = f"eq.{val}"

        if self._order_col is not None:
            direction = "desc" if self._order_desc else "asc"
            params["order"] = f"{self._order_col}.{direction}"

        if self._limit_n is not None:
            params["limit"] = str(self._limit_n)

        return params

    # --- execute -----------------------------------------------------------

    def execute(self) -> _QueryResult:
        path = f"/rest/v1/{self._table}"
        params = self._build_params()
        prefer_header = {"Prefer": "return=representation"}

        if self._operation == "select":
            resp = self._client._sync_get(path, params=params)
            resp.raise_for_status()
            return _QueryResult(resp.json())

        if self._operation == "insert":
            resp = self._client._sync_post(
                path,
                json=self._payload,
                params=None,
                extra_headers=prefer_header,
            )
            resp.raise_for_status()
            return _QueryResult(resp.json())

        if self._operation == "update":
            resp = self._client._sync_patch(
                path,
                json=self._payload,
                params=params,
                extra_headers=prefer_header,
            )
            resp.raise_for_status()
            return _QueryResult(resp.json())

        raise ValueError(f"Unknown operation: {self._operation!r}")


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

    # --- sync helpers for TableQueryBuilder --------------------------------

    def _sync_get(self, path: str, params: dict | None = None) -> httpx.Response:
        with httpx.Client(timeout=10.0) as client:
            return client.get(f"{self._base}{path}", headers=self._headers, params=params)

    def _sync_post(
        self,
        path: str,
        json: Any = None,
        params: dict | None = None,
        extra_headers: dict | None = None,
    ) -> httpx.Response:
        headers = {**self._headers, **(extra_headers or {})}
        with httpx.Client(timeout=10.0) as client:
            return client.post(f"{self._base}{path}", headers=headers, json=json, params=params)

    def _sync_patch(
        self,
        path: str,
        json: Any = None,
        params: dict | None = None,
        extra_headers: dict | None = None,
    ) -> httpx.Response:
        headers = {**self._headers, **(extra_headers or {})}
        with httpx.Client(timeout=10.0) as client:
            return client.patch(f"{self._base}{path}", headers=headers, json=json, params=params)

    def table(self, name: str) -> TableQueryBuilder:
        return TableQueryBuilder(self, name)


def get_supabase_client() -> SupabaseClient:
    """Return a service-role SupabaseClient. Raises if not configured."""
    if not is_supabase_configured():
        raise RuntimeError("Supabase is not configured")
    return SupabaseClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
