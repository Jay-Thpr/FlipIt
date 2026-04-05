"""Supabase JWT auth dependency for FastAPI.

Usage:
    from backend.auth import get_current_user, AuthenticatedUser

    @app.get("/protected")
    async def protected(user: AuthenticatedUser = Depends(get_current_user)):
        return {"user_id": user.user_id}
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import (
    SUPABASE_JWT_AUDIENCE,
    SUPABASE_JWT_SECRET,
    SUPABASE_URL,
    is_supabase_configured,
)
from backend.supabase import fetch_jwks

_bearer = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Authenticated user object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None
    role: str | None
    raw_claims: dict[str, Any]


# ---------------------------------------------------------------------------
# JWT validation helpers
# ---------------------------------------------------------------------------

def _issuer() -> str:
    return f"{SUPABASE_URL.rstrip('/')}/auth/v1"


def _decode_hs256(token: str) -> dict[str, Any]:
    """Validate with the symmetric SUPABASE_JWT_SECRET (HS256)."""
    secret = os.getenv("SUPABASE_JWT_SECRET", SUPABASE_JWT_SECRET)
    audience = os.getenv("SUPABASE_JWT_AUDIENCE", SUPABASE_JWT_AUDIENCE)
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=audience,
        issuer=_issuer(),
        options={"verify_exp": True},
    )


async def _decode_rs256(token: str) -> dict[str, Any]:
    """Validate with RS256 keys fetched from Supabase JWKS endpoint."""
    audience = os.getenv("SUPABASE_JWT_AUDIENCE", SUPABASE_JWT_AUDIENCE)
    jwks_data = await fetch_jwks()
    keys = jwks_data.get("keys", [])
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    matching = [k for k in keys if k.get("kid") == kid] if kid else keys
    if not matching:
        raise jwt.InvalidKeyError("No matching JWK found for token kid")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(matching[0])
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=audience,
        issuer=_issuer(),
        options={"verify_exp": True},
    )


async def _validate_token(token: str) -> dict[str, Any]:
    """Try HS256 first (if secret configured), then RS256 via JWKS."""
    secret = os.getenv("SUPABASE_JWT_SECRET", SUPABASE_JWT_SECRET)
    if secret.strip():
        try:
            return _decode_hs256(token)
        except jwt.PyJWTError as exc:
            logger.warning("HS256 decode failed: %s", exc)
            # fall through to RS256

    if not is_supabase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured",
        )
    return await _decode_rs256(token)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    """FastAPI dependency — resolves a Supabase bearer token to an AuthenticatedUser.

    Raises HTTP 401 on missing/invalid token, 503 if auth is not configured.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = await _validate_token(credentials.credentials)
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )

    return AuthenticatedUser(
        user_id=user_id,
        email=claims.get("email"),
        role=claims.get("role"),
        raw_claims=claims,
    )
