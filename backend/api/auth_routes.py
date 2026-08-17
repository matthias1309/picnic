"""
Authentication routes: login, logout, current user.

Traces: ARCH-006
Implements: REQ-006 (AC-006-01, AC-006-02, AC-006-04, AC-006-05, AC-006-06)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.api.dependencies import SESSION_COOKIE_NAME, get_current_user, get_db
from backend.auth import rate_limit
from backend.auth.service import authenticate_user, create_session, delete_session
from backend.config import settings
from backend.models import User
from backend.schemas import LoginRequest, UserOut

SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60

auth_router = APIRouter(prefix="/auth")


def _cookie_path() -> str:
    """The session cookie's Path attribute, read fresh from settings on
    every call (REQ-019) rather than cached at import time — it must match
    whatever prefix routes are *actually* mounted under right now, or
    browsers won't send the cookie back on requests to those routes. An
    empty url_prefix (prod, its own domain root) needs Path=/, not Path=""
    (not a valid cookie path)."""
    return settings.url_prefix or "/"


@auth_router.post("/login", response_model=UserOut)
def login(credentials: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    """Authenticate with username/password and set a session cookie."""
    if rate_limit.is_locked_out(db, credentials.username):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    user = authenticate_user(db, credentials.username, credentials.password)
    if user is None:
        rate_limit.record_failed_attempt(db, credentials.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    rate_limit.reset_attempts(db, credentials.username)
    token = create_session(db, user)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path=_cookie_path(),
    )
    return UserOut(id=user.id, username=user.username)


@auth_router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Invalidate the current session, if any, and clear the cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME, path=_cookie_path())
    return {"ok": True}


@auth_router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the currently authenticated user."""
    return UserOut(id=current_user.id, username=current_user.username)
