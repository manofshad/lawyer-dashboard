from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urljoin

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClientConnectionError

from .settings import Settings, get_settings


security = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    token: str
    claims: dict[str, Any]


@lru_cache
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    jwks_url = urljoin(supabase_url.rstrip("/") + "/", "auth/v1/.well-known/jwks.json")
    return jwt.PyJWKClient(jwks_url)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase URL is not configured on the backend.",
        )

    token = credentials.credentials

    try:
        unverified_header = jwt.get_unverified_header(token)
        algorithm = unverified_header.get("alg", "RS256")
        signing_key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            issuer=urljoin(settings.supabase_url.rstrip("/") + "/", "auth/v1"),
            options={"verify_aud": False},
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch Supabase signing keys.",
        ) from exc

    return AuthenticatedUser(token=token, claims=claims)
