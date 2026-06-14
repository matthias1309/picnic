"""
Shared FastAPI dependencies for API routes.

Traces: ARCH-003, ARCH-006
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.auth.service import get_session
from backend.database import get_db
from backend.models import User

SESSION_COOKIE_NAME = "picnic_session"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the logged-in user from the session cookie, or raise 401 (AC-006-04)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_session(db, token) if token else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


__all__ = ["get_db", "get_current_user", "SESSION_COOKIE_NAME"]
