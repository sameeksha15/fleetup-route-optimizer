"""Authentication endpoints: signup, login, logout, and current-user."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models
from ..auth import schemas
from ..auth.dependencies import get_current_user
from ..auth.security import (
    clear_session_cookie,
    create_session_token,
    dummy_verify,
    hash_password,
    set_session_cookie,
    verify_password,
)
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Brute-force throttling: lock an account for a while after repeated failures.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _utcnow() -> datetime:
    """Naive UTC, matching how SQLite stores DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.SignupRequest, response: Response, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    if db.query(models.User).filter(models.User.email == email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    # The first user of a new signup creates the organization and owns it.
    org = models.Organization(name=payload.company_name.strip())
    db.add(org)
    db.flush()  # assign org.id without a second round trip
    user = models.User(
        organization_id=org.id,
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    set_session_cookie(response, create_session_token(user.id, org.id, email))
    return user


@router.post("/login", response_model=schemas.UserOut)
def login(payload: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    user = db.query(models.User).filter(models.User.email == email).first()
    now = _utcnow()

    # Generic error + dummy hash for unknown emails: no timing/enumeration leak.
    if user is None:
        dummy_verify()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")

    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed attempts. Please try again later.",
        )

    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_attempts = 0
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")

    # Success: reset throttling state and stamp the login.
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    db.refresh(user)

    set_session_cookie(response, create_session_token(user.id, user.organization_id, user.email))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    clear_session_cookie(response)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
