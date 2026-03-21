# app/api/auth.py
"""
Authentication endpoints: register, login, logout, refresh, me, Google OAuth.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.limiter import limiter
from app.db.postgres import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
REFRESH_TOKEN_EXPIRE_DAYS = 30


# ── Models ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleLoginRequest(BaseModel):
    id_token: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _audit(conn, user_id: Optional[str], action: str, resource_type: Optional[str],
           resource_id: Optional[str], ip: Optional[str], details: Optional[dict] = None):
    try:
        conn.execute(
            """INSERT INTO audit_log (id, user_id, action, resource_type, resource_id,
               ip_address, details, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            [str(uuid.uuid4()), user_id, action, resource_type, resource_id, ip,
             json.dumps(details) if details else None],
        )
    except Exception as e:
        logger.warning(f"Audit log write failed: {e}")


def _make_token_response(user_id: str, role: str, name: str, email: str,
                          request: Request, conn) -> dict:
    access_token = create_access_token(user_id, role)
    refresh_token = create_refresh_token(user_id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")

    conn.execute(
        """INSERT INTO user_sessions (id, user_id, refresh_token_hash, ip_address,
           user_agent, expires_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        [str(uuid.uuid4()), user_id, _hash_token(refresh_token), ip, ua, expires_at],
    )
    conn.execute(
        "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", [user_id]
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"id": user_id, "email": email, "name": name, "role": role},
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@limiter.limit("5/hour")
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: Request, body: RegisterRequest):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", [body.email.lower()]
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO users (id, email, name, password_hash, role, is_active, created_at)
               VALUES (?, ?, ?, ?, 'user', TRUE, CURRENT_TIMESTAMP)""",
            [user_id, body.email.lower(), body.name, hash_password(body.password)],
        )
        _audit(conn, user_id, "register", "user", user_id,
               request.client.host if request.client else None)
        return _make_token_response(user_id, "user", body.name, body.email.lower(), request, conn)


@limiter.limit("10/hour")
@router.post("/login")
def login(request: Request, body: LoginRequest):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, password_hash, role, is_active FROM users WHERE email = ?",
            [body.email.lower()],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user_id, name, pw_hash, role, is_active = row
        if not is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        if not pw_hash or not verify_password(body.password, pw_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        _audit(conn, user_id, "login", "user", user_id,
               request.client.host if request.client else None)
        return _make_token_response(user_id, role, name, body.email.lower(), request, conn)


@router.post("/refresh")
def refresh_token(body: RefreshRequest):
    payload = decode_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    token_hash = _hash_token(body.refresh_token)

    with get_conn() as conn:
        session = conn.execute(
            """SELECT id FROM user_sessions
               WHERE user_id = ? AND refresh_token_hash = ?
                 AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP""",
            [user_id, token_hash],
        ).fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="Session not found or revoked")

        user = conn.execute(
            "SELECT email, name, role, is_active FROM users WHERE id = ?", [user_id]
        ).fetchone()
        if not user or not user[3]:
            raise HTTPException(status_code=401, detail="User not found or disabled")

        email, name, role = user[0], user[1], user[2]
        new_access = create_access_token(user_id, role)
        return {
            "access_token": new_access,
            "token_type": "bearer",
            "user": {"id": user_id, "email": email, "name": name, "role": role},
        }


@router.post("/logout")
def logout(body: RefreshRequest, user: dict = Depends(get_current_user)):
    token_hash = _hash_token(body.refresh_token)
    with get_conn() as conn:
        conn.execute(
            """UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP
               WHERE user_id = ? AND refresh_token_hash = ?""",
            [user["id"], token_hash],
        )
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": user}


@limiter.limit("10/hour")
@router.post("/google")
def google_login(request: Request, body: GoogleLoginRequest):
    """Verify Google ID token and create/login user."""
    try:
        resp = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": body.id_token},
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        info = resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Google verification failed: {e}")

    # Validate audience if GOOGLE_CLIENT_ID is set
    if GOOGLE_CLIENT_ID and info.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token audience mismatch")

    google_id = info.get("sub")
    email = info.get("email", "").lower()
    name = info.get("name", email.split("@")[0])

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, role, is_active FROM users WHERE email = ? OR google_id = ?",
            [email, google_id],
        ).fetchone()

        if row:
            user_id, name, role, is_active = row
            if not is_active:
                raise HTTPException(status_code=403, detail="Account disabled")
            # Update google_id if not set
            conn.execute(
                "UPDATE users SET google_id = ? WHERE id = ? AND google_id IS NULL",
                [google_id, user_id],
            )
        else:
            user_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO users (id, email, name, google_id, role, is_active, created_at)
                   VALUES (?, ?, ?, ?, 'user', TRUE, CURRENT_TIMESTAMP)""",
                [user_id, email, name, google_id],
            )
            role = "user"

        _audit(conn, user_id, "google_login", "user", user_id,
               request.client.host if request.client else None)
        return _make_token_response(user_id, role, name, email, request, conn)
