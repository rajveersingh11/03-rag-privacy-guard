"""Shared authentication and rate-limiting dependencies."""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Cookie, Depends, HTTPException, Request, Header
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from aegisVault.db.session import get_db


SESSION_COOKIE_NAME = "aegis_session"


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: str
    username: str
    role: str
    tenant_id: str

    @property
    def roles(self) -> list[str]:
        return [self.role]


def _session_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def rate_limit_key(request: Request) -> str:
    """Prefer authenticated identity; otherwise isolate by session or client IP."""
    principal = getattr(request.state, "current_user", None)
    if principal is not None:
        return f"user:{principal.user_id}"

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        return f"session:{_session_hash(token)}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key)


# API keys remain available only for explicit service-to-service integrations.
# Every configured full digest is compared so lookup behavior does not disclose
# a prefix and two keys can never collide merely because their prefixes match.
_API_KEYS_HASHED: list[tuple[str, bytes]] = []


def init_api_keys() -> None:
    global _API_KEYS_HASHED
    configured: list[tuple[str, bytes]] = []
    keys = os.environ.get("API_KEYS", os.environ.get("API_KEY", ""))
    for key in keys.split(","):
        key = key.strip()
        if key:
            digest = hashlib.sha256(key.encode("utf-8")).digest()
            configured.append((digest.hex()[:12], digest))
    _API_KEYS_HASHED = configured


init_api_keys()


def verify_api_key(
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> str:
    """Verify a service API key using full, constant-time digest comparisons."""
    if not _API_KEYS_HASHED:
        raise HTTPException(status_code=503, detail="API keys are not configured")

    actual_hash = hashlib.sha256(x_api_key.encode("utf-8")).digest()
    matches = [
        fingerprint
        for fingerprint, expected_hash in _API_KEYS_HASHED
        if secrets.compare_digest(actual_hash, expected_hash)
    ]
    if not matches:
        raise HTTPException(status_code=401, detail="Invalid API key")

    request.state.api_key_fingerprint = matches[0]
    return matches[0]


def get_current_user(
    request: Request,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    """Resolve authorization exclusively from a server-side session."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    row = db.execute(
        text(
            """
            SELECT u.id, u.username, u.role, u.tenant_id, s.expires_at, s.revoked_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = :token_hash
            """
        ),
        {"token_hash": _session_hash(session_token)},
    ).fetchone()

    if not row or row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = row.expires_at
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired")

    principal = AuthPrincipal(
        user_id=row.id,
        username=row.username,
        role=row.role,
        tenant_id=row.tenant_id,
    )
    request.state.current_user = principal
    return principal


def require_admin(principal: AuthPrincipal = Depends(get_current_user)) -> AuthPrincipal:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return principal


def get_auth_principal_or_api_key(
    request: Request,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> AuthPrincipal | str:
    """Resolve auth via session cookie (returns AuthPrincipal) or API key (returns fingerprint string)."""
    if session_token:
        try:
            return get_current_user(request, session_token, db)
        except HTTPException:
            if not x_api_key:
                raise
    if x_api_key:
        return verify_api_key(request, x_api_key)
    raise HTTPException(status_code=401, detail="Authentication required (session cookie or X-API-Key required)")
