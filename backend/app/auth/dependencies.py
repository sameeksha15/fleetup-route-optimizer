"""FastAPI dependency that resolves the current user from the session cookie."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from .security import COOKIE_NAME, decode_session_token

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Cookie"},
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise _UNAUTH
    payload = decode_session_token(token)
    if not payload or "sub" not in payload:
        raise _UNAUTH
    user = db.get(models.User, int(payload["sub"]))
    if user is None:
        raise _UNAUTH
    return user


def get_current_org_id(user: models.User = Depends(get_current_user)) -> int:
    """The organization that owns the caller's data — the tenant scope for every query."""
    return user.organization_id
