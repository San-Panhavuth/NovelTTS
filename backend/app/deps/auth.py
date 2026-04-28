from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk, jwt
from jose.utils import base64url_decode

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None


def _raise_unauthorized(detail: str = "Invalid authentication credentials") -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _read_env_value_from_file(path: Path, key: str) -> str | None:
    if not path.exists():
        return None

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        current_key, value = stripped.split("=", 1)
        if current_key.strip() == key:
            return value.strip().strip('"').strip("'")
    return None


def _read_first_env_key_from_file(path: Path, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _read_env_value_from_file(path, key)
        if value:
            return value
    return None


def _resolve_supabase_url() -> str:
    env_keys = ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")

    if settings.supabase_url:
        return settings.supabase_url

    from_env = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    if from_env:
        return from_env

    backend_root = Path(__file__).resolve().parents[2]
    workspace_root = backend_root.parent

    from_local = _read_first_env_key_from_file(backend_root / ".env.local", env_keys)
    if from_local:
        return from_local

    from_env_file = _read_first_env_key_from_file(backend_root / ".env", env_keys)
    if from_env_file:
        return from_env_file

    from_workspace_local = _read_first_env_key_from_file(workspace_root / ".env.local", env_keys)
    if from_workspace_local:
        return from_workspace_local

    from_workspace_env = _read_first_env_key_from_file(workspace_root / ".env", env_keys)
    if from_workspace_env:
        return from_workspace_env

    return ""


def get_supabase_url_debug() -> tuple[bool, str]:
    if settings.supabase_url:
        return True, "settings.supabase_url"

    if os.getenv("SUPABASE_URL"):
        return True, "env:SUPABASE_URL"

    if os.getenv("NEXT_PUBLIC_SUPABASE_URL"):
        return True, "env:NEXT_PUBLIC_SUPABASE_URL"

    backend_root = Path(__file__).resolve().parents[2]
    workspace_root = backend_root.parent
    env_keys = ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")

    if _read_first_env_key_from_file(backend_root / ".env.local", env_keys):
        return True, "backend/.env.local"

    if _read_first_env_key_from_file(backend_root / ".env", env_keys):
        return True, "backend/.env"

    if _read_first_env_key_from_file(workspace_root / ".env.local", env_keys):
        return True, "root/.env.local"

    if _read_first_env_key_from_file(workspace_root / ".env", env_keys):
        return True, "root/.env"

    return False, "missing"


@lru_cache(maxsize=1)
def _get_supabase_jwks() -> dict:
    supabase_url = _resolve_supabase_url()
    if not supabase_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing SUPABASE_URL")

    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        with urlopen(jwks_url, timeout=5) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch Supabase JWKS",
        ) from exc


def _verify_supabase_jwt(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except Exception:  # noqa: BLE001
        _raise_unauthorized("Malformed token header")

    kid = header.get("kid")
    if not kid:
        _raise_unauthorized("Missing token key id")

    keys = _get_supabase_jwks().get("keys", [])
    matching_key = next((key for key in keys if key.get("kid") == kid), None)
    if not matching_key:
        _raise_unauthorized("Signing key not found")

    try:
        public_key = jwk.construct(matching_key)
        message, encoded_signature = token.rsplit(".", 1)
        decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
        if not public_key.verify(message.encode("utf-8"), decoded_signature):
            _raise_unauthorized("Invalid signature")

        claims = jwt.get_unverified_claims(token)
    except Exception:  # noqa: BLE001
        _raise_unauthorized("Token verification failed")

    aud_claim = claims.get("aud")
    if isinstance(aud_claim, list):
        aud_ok = settings.supabase_jwt_aud in aud_claim
    else:
        aud_ok = aud_claim == settings.supabase_jwt_aud
    if not aud_ok:
        _raise_unauthorized("Token audience mismatch")

    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or exp < time.time():
        _raise_unauthorized("Token is expired")

    user_id = claims.get("sub")
    if not user_id:
        _raise_unauthorized("Missing subject claim")

    return claims


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthUser:
    if credentials is None:
        _raise_unauthorized("Missing bearer token")

    claims = _verify_supabase_jwt(credentials.credentials)
    return AuthUser(id=claims["sub"], email=claims.get("email"))


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str:
    """Extract and return just the user ID from JWT."""
    if credentials is None:
        _raise_unauthorized("Missing bearer token")

    claims = _verify_supabase_jwt(credentials.credentials)
    return claims["sub"]


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
