"""Tests for the Supabase foundation slice.

Covers:
- is_supabase_configured()
- fetch_jwks()
- get_supabase_client()
- get_current_user FastAPI dependency

No real network calls are made.

Design note
-----------
backend/config.py, backend/supabase.py, and backend/auth.py all read their
Supabase settings from os.getenv() *at call time* for is_supabase_configured()
and _decode_hs256(), but the module-level constants (SUPABASE_URL, etc.) are
captured once at import time.  get_supabase_client() and SupabaseClient.__init__
use the module-level constants directly.

Strategy:
  * For is_supabase_configured() — monkeypatch env vars (it calls os.getenv).
  * For get_supabase_client() — patch the module-level constants in
    backend.supabase and backend.config in addition to setting env vars.
  * For get_current_user — patch module-level constants in backend.auth and
    backend.config so _decode_hs256 / _issuer() see the right values.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

FAKE_URL = "https://xyzproject.supabase.co"
FAKE_SERVICE_KEY = "fake-service-role-key-abc123"
FAKE_JWT_SECRET = "super-secret-hs256-key-for-testing-long-enough"
FAKE_AUDIENCE = "authenticated"
FAKE_ISSUER = f"{FAKE_URL}/auth/v1"
FAKE_USER_ID = "user-abc-123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mint_token(
    subject: str = FAKE_USER_ID,
    secret: str = FAKE_JWT_SECRET,
    issuer: str = FAKE_ISSUER,
    audience: str = FAKE_AUDIENCE,
    exp_offset: int = 3600,
    extra: dict | None = None,
) -> str:
    """Mint an HS256 JWT for testing."""
    import time as _time

    payload: dict = {
        "sub": subject,
        "iss": issuer,
        "aud": audience,
        "iat": int(_time.time()),
        "exp": int(_time.time()) + exp_offset,
        "email": "test@example.com",
        "role": "authenticated",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm="HS256")


def _expired_token() -> str:
    return _mint_token(exp_offset=-3600)


@contextmanager
def _supabase_configured_patches(mock_jwks_fetch: bool = False):
    """Patch all module-level constants so the full Supabase stack is configured.

    When mock_jwks_fetch=True, also patch fetch_jwks to raise InvalidSignatureError
    so that any RS256 fallback (reached after HS256 failure) produces a clean 401
    instead of a real network call.
    """
    patches = [
        patch("backend.config.SUPABASE_URL", FAKE_URL),
        patch("backend.config.SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY),
        patch("backend.config.SUPABASE_JWT_SECRET", FAKE_JWT_SECRET),
        patch("backend.supabase.SUPABASE_URL", FAKE_URL),
        patch("backend.supabase.SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY),
        patch("backend.auth.SUPABASE_URL", FAKE_URL),
        patch("backend.auth.SUPABASE_JWT_SECRET", FAKE_JWT_SECRET),
        patch("backend.auth.SUPABASE_JWT_AUDIENCE", FAKE_AUDIENCE),
    ]
    if mock_jwks_fetch:
        patches.append(
            patch(
                "backend.auth.fetch_jwks",
                new=AsyncMock(side_effect=jwt.InvalidSignatureError("mocked RS256 failure")),
            )
        )
    started = [p.start() for p in patches]
    try:
        yield started
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------
# Fixture: clean env for each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure Supabase env vars start unset before each test."""
    for var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET", "SUPABASE_JWT_AUDIENCE"):
        monkeypatch.delenv(var, raising=False)
    yield


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset JWKS cache before every test."""
    from backend.supabase import clear_jwks_cache
    clear_jwks_cache()
    yield
    clear_jwks_cache()


# ---------------------------------------------------------------------------
# 1. is_supabase_configured()
# ---------------------------------------------------------------------------

class TestIsSupabaseConfigured:
    """is_supabase_configured() reads os.getenv() at call time — env vars work."""

    def test_true_when_both_vars_set(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)
        from backend.config import is_supabase_configured
        assert is_supabase_configured() is True

    def test_false_when_url_missing(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)
        from backend.config import is_supabase_configured
        assert is_supabase_configured() is False

    def test_false_when_service_key_missing(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        from backend.config import is_supabase_configured
        assert is_supabase_configured() is False

    def test_false_when_both_missing(self):
        from backend.config import is_supabase_configured
        assert is_supabase_configured() is False

    def test_false_when_url_is_whitespace(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "   ")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)
        from backend.config import is_supabase_configured
        assert is_supabase_configured() is False

    def test_false_when_service_key_is_whitespace(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "   ")
        from backend.config import is_supabase_configured
        assert is_supabase_configured() is False


# ---------------------------------------------------------------------------
# 2. fetch_jwks()
# ---------------------------------------------------------------------------

class TestFetchJwks:
    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        from backend.supabase import fetch_jwks
        with pytest.raises(RuntimeError, match="not configured"):
            await fetch_jwks()

    @pytest.mark.asyncio
    async def test_returns_dict_when_configured(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)

        fake_jwks = {"keys": [{"kty": "RSA", "kid": "key1"}]}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=fake_jwks)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.supabase.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.supabase.SUPABASE_URL", FAKE_URL):
                from backend.supabase import fetch_jwks
                result = await fetch_jwks()

        assert result == fake_jwks
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_cache_within_ttl(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)

        fake_jwks = {"keys": [{"kty": "RSA", "kid": "key1"}]}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=fake_jwks)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.supabase.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.supabase.SUPABASE_URL", FAKE_URL):
                from backend.supabase import fetch_jwks
                first = await fetch_jwks()
                second = await fetch_jwks()

        assert first == second
        # HTTP client should have been called only once (second call hits cache)
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_force_refetches_even_within_ttl(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)

        fake_jwks = {"keys": []}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=fake_jwks)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.supabase.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.supabase.SUPABASE_URL", FAKE_URL):
                from backend.supabase import fetch_jwks
                await fetch_jwks()           # primes cache
                await fetch_jwks(force=True) # should re-fetch despite fresh cache

        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_refetches_after_ttl_expires(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)

        fake_jwks = {"keys": []}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=fake_jwks)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        import backend.supabase as supabase_mod

        with patch("backend.supabase.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.supabase.SUPABASE_URL", FAKE_URL):
                from backend.supabase import fetch_jwks
                await fetch_jwks()
                # Manually expire the cache by backdating _jwks_fetched_at
                supabase_mod._jwks_fetched_at = time.monotonic() - supabase_mod._JWKS_TTL_SECONDS - 1
                await fetch_jwks()

        assert mock_client.get.call_count == 2


# ---------------------------------------------------------------------------
# 3. get_supabase_client()
# ---------------------------------------------------------------------------

class TestGetSupabaseClient:
    def test_raises_when_not_configured(self):
        from backend.supabase import get_supabase_client
        with pytest.raises(RuntimeError, match="not configured"):
            get_supabase_client()

    def test_returns_client_when_configured(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)
        with patch("backend.supabase.SUPABASE_URL", FAKE_URL), \
             patch("backend.supabase.SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY):
            from backend.supabase import get_supabase_client, SupabaseClient
            client = get_supabase_client()
        assert isinstance(client, SupabaseClient)

    def test_client_has_correct_base_url(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL + "/")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)
        # Use the URL with trailing slash — SupabaseClient.__init__ calls rstrip('/')
        url_with_slash = FAKE_URL + "/"
        with patch("backend.supabase.SUPABASE_URL", url_with_slash), \
             patch("backend.supabase.SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY):
            from backend.supabase import get_supabase_client
            client = get_supabase_client()
        assert client._base == FAKE_URL

    def test_client_headers_contain_service_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", FAKE_URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY)
        with patch("backend.supabase.SUPABASE_URL", FAKE_URL), \
             patch("backend.supabase.SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_KEY):
            from backend.supabase import get_supabase_client
            client = get_supabase_client()
        assert client._headers["apikey"] == FAKE_SERVICE_KEY
        assert FAKE_SERVICE_KEY in client._headers["Authorization"]


# ---------------------------------------------------------------------------
# 4. get_current_user dependency
# ---------------------------------------------------------------------------

def _make_app() -> FastAPI:
    """Build a minimal FastAPI app that uses get_current_user."""
    from backend.auth import get_current_user, AuthenticatedUser

    app = FastAPI()

    @app.get("/protected")
    async def protected(user: AuthenticatedUser = Depends(get_current_user)):
        return {"user_id": user.user_id, "email": user.email, "role": user.role}

    return app


class TestGetCurrentUser:
    # ------------------------------------------------------------------ setup
    def _client(self) -> TestClient:
        return TestClient(_make_app(), raise_server_exceptions=False)

    # -------------------------------------------- missing authorization header
    def test_missing_auth_header_returns_401(self):
        resp = self._client().get("/protected")
        assert resp.status_code == 401

    # -------------------------------------------------------- valid HS256 token
    def test_valid_hs256_token_returns_user(self):
        with _supabase_configured_patches():
            token = _mint_token()
            resp = self._client().get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == FAKE_USER_ID
        assert body["email"] == "test@example.com"
        assert body["role"] == "authenticated"

    # --------------------------------------------------------- expired token
    def test_expired_token_returns_401(self):
        # The HS256 path swallows ExpiredSignatureError (subclass of PyJWTError)
        # via the broad `except jwt.PyJWTError: pass` and falls through to RS256.
        # We patch the RS256 fallback to re-raise ExpiredSignatureError so that
        # get_current_user's dedicated handler produces the "Token expired" detail.
        with _supabase_configured_patches():
            exp_patch = patch(
                "backend.auth.fetch_jwks",
                new=AsyncMock(side_effect=jwt.ExpiredSignatureError("Signature has expired")),
            )
            with exp_patch:
                token = _expired_token()
                resp = self._client().get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    # ------------------------------------------------- tampered/invalid token
    def test_invalid_token_returns_401(self):
        with _supabase_configured_patches(mock_jwks_fetch=True):
            token = _mint_token() + "tampered"
            resp = self._client().get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self):
        with _supabase_configured_patches(mock_jwks_fetch=True):
            # Token signed with a different secret — validation must fail
            token = _mint_token(secret="completely-wrong-secret-value-x")
            resp = self._client().get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    # ----------------------------------------- RS256 path / not configured → 503
    def test_rs256_path_not_configured_returns_503(self):
        """When no JWT secret and Supabase not fully configured, expect 503."""
        # All module-level constants remain empty (no patches). env vars are
        # unset by the autouse fixture. The token is signed with *something*,
        # but since SUPABASE_JWT_SECRET is empty the code falls through to the
        # RS256 path, finds Supabase not configured, and raises 503.
        token = _mint_token(secret="any-secret-at-all-long-enough-32b")
        resp = self._client().get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 503

    # ------------------------------------------------ wrong audience → 401
    def test_wrong_audience_returns_401(self):
        with _supabase_configured_patches(mock_jwks_fetch=True):
            token = _mint_token(audience="wrong-audience")
            resp = self._client().get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    # ---------------------------------------- token missing sub claim → 401
    def test_missing_sub_returns_401(self):
        with _supabase_configured_patches():
            import time as _time
            payload = {
                "iss": FAKE_ISSUER,
                "aud": FAKE_AUDIENCE,
                "iat": int(_time.time()),
                "exp": int(_time.time()) + 3600,
            }
            token = jwt.encode(payload, FAKE_JWT_SECRET, algorithm="HS256")
            resp = self._client().get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "sub" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Direct async dependency tests
# ---------------------------------------------------------------------------

class TestGetCurrentUserAsync:
    """Call the async dependency directly without TestClient."""

    @pytest.mark.asyncio
    async def test_valid_token_direct_call(self):
        from fastapi.security import HTTPAuthorizationCredentials
        from backend.auth import get_current_user

        with _supabase_configured_patches():
            token = _mint_token()
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            user = await get_current_user(credentials=creds)

        assert user.user_id == FAKE_USER_ID
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_none_credentials_raises_401(self):
        from fastapi import HTTPException
        from backend.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
