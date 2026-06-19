"""Cookie-based authentication endpoints."""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from aegisVault.app.deps import (
    SESSION_COOKIE_NAME,
    AuthPrincipal,
    _session_hash,
    get_current_user,
    limiter,
)
from aegisVault.db.session import get_db
from aegisVault.utils.common import get_logger

logger = get_logger(__name__)
router = APIRouter()

PBKDF2_ITERATIONS = 600_000
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(..., min_length=12, max_length=256)


class AuthResponse(BaseModel):
    status: str
    user_id: str
    username: str
    role: str
    tenant_id: str
    expires_at: datetime


class UserResponse(BaseModel):
    user_id: str
    username: str
    role: str
    tenant_id: str


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        if encoded.startswith("pbkdf2_sha256$"):
            _, iterations_raw, salt_hex, key_hex = encoded.split("$")
            salt = bytes.fromhex(salt_hex)
        else:
            # Compatibility with the original salt$iterations$key format.
            salt_raw, iterations_raw, key_hex = encoded.split("$")
            salt = salt_raw.encode("utf-8")
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations_raw)
        )
        return secrets.compare_digest(key.hex(), key_hex)
    except (TypeError, ValueError):
        return False


def _password_needs_rehash(encoded: str) -> bool:
    try:
        parts = encoded.split("$")
        iterations = int(parts[1] if encoded.startswith("pbkdf2_sha256$") else parts[1])
        return not encoded.startswith("pbkdf2_sha256$") or iterations < PBKDF2_ITERATIONS
    except (IndexError, ValueError):
        return True


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.environ.get("APP_ENV") == "production",
        samesite="strict",
        path="/",
    )


def _issue_session(db: Session, user_id: str, response: Response) -> datetime:
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS)
    db.execute(
        text(
            """
            INSERT INTO auth_sessions (id, user_id, token_hash, expires_at)
            VALUES (:id, :user_id, :token_hash, :expires_at)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "token_hash": _session_hash(raw_token),
            "expires_at": expires_at,
        },
    )
    _set_session_cookie(response, raw_token)
    return expires_at


@router.post("/signup", response_model=AuthResponse)
@limiter.limit("10/15minutes")
def signup(request: Request, req: AuthRequest, response: Response, db: Session = Depends(get_db)):
    try:
        if db.execute(
            text("SELECT 1 FROM users WHERE username = :username"),
            {"username": req.username},
        ).fetchone():
            raise HTTPException(status_code=400, detail="Username is already taken")

        user_id = str(uuid.uuid4())
        tenant_id = os.environ.get("DEFAULT_TENANT_ID", "default")
        db.execute(
            text(
                """
                INSERT INTO users (id, username, password_hash, role, tenant_id)
                VALUES (:id, :username, :password_hash, :role, :tenant_id)
                """
            ),
            {
                "id": user_id,
                "username": req.username,
                "password_hash": hash_password(req.password),
                "role": "admin",
                "tenant_id": tenant_id,
            },
        )
        expires_at = _issue_session(db, user_id, response)
        db.commit()
        return AuthResponse(
            status="success",
            user_id=user_id,
            username=req.username,
            role="admin",
            tenant_id=tenant_id,
            expires_at=expires_at,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        logger.exception("Signup failed")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database registration failed")


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/15minutes")
def login(request: Request, req: AuthRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = db.execute(
            text(
                """
                SELECT id, username, password_hash, role, tenant_id
                FROM users WHERE username = :username
                """
            ),
            {"username": req.username},
        ).fetchone()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if _password_needs_rehash(user.password_hash):
            db.execute(
                text("UPDATE users SET password_hash = :password_hash WHERE id = :id"),
                {"password_hash": hash_password(req.password), "id": user.id},
            )

        expires_at = _issue_session(db, user.id, response)
        db.commit()
        return AuthResponse(
            status="success",
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_id=user.tenant_id,
            expires_at=expires_at,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        logger.exception("Login failed")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database login check failed")


@router.get("/me", response_model=UserResponse)
def me(principal: AuthPrincipal = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**principal.__dict__)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if session_token:
        db.execute(
            text(
                """
                UPDATE auth_sessions SET revoked_at = :revoked_at
                WHERE token_hash = :token_hash AND revoked_at IS NULL
                """
            ),
            {"revoked_at": datetime.now(UTC), "token_hash": _session_hash(session_token)},
        )
        db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", samesite="strict")
    response.delete_cookie("aegis_csrf", path="/", samesite="strict")
    response.status_code = 204
    return response
