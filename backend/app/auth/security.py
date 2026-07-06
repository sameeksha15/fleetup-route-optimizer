"""Password hashing, JWT session tokens, and secure cookie helpers."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Response

from ..config import get_settings

logger = logging.getLogger("fleetup.auth")

_settings = get_settings()
_JWT_ALG = "HS256"

# A real deployment MUST set JWT_SECRET so sessions survive restarts and are
# consistent across processes. In dev we fall back to a random per-process
# secret: still cryptographically strong, but sessions reset on restart.
_SECRET = _settings.jwt_secret or secrets.token_urlsafe(48)
if not _settings.jwt_secret:
    logger.warning(
        "JWT_SECRET is not set — using an ephemeral secret; sessions will not "
        "survive a server restart. Set JWT_SECRET in backend/.env for persistence."
    )

COOKIE_NAME = _settings.cookie_name

# bcrypt rejects secrets longer than 72 bytes; the schema caps password length
# so we never reach that here.


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# A precomputed valid hash used to equalize response timing when the email is
# unknown, so an attacker can't tell registered emails apart by how fast login
# fails (defeats user enumeration via timing).
_DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt())


def dummy_verify() -> None:
    bcrypt.checkpw(b"nonexistent", _DUMMY_HASH)


def create_session_token(user_id: int, org_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "org": org_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=_settings.jwt_expire_hours),
    }
    return jwt.encode(payload, _SECRET, algorithm=_JWT_ALG)


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_JWT_ALG])
    except jwt.PyJWTError:
        return None


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=_settings.jwt_expire_hours * 3600,
        httponly=True,  # not readable by JavaScript -> XSS can't steal it
        secure=_settings.cookie_secure,
        samesite="lax",  # not sent on cross-site requests -> CSRF defense
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
