"""
Authentication service: user lookup and session lifecycle.

Traces: ARCH-006
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.auth.security import generate_token, hash_token, verify_password
from backend.models import User, UserSession

SESSION_DURATION = timedelta(days=30)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Return the user if the username/password combination is valid, else None."""
    user = db.query(User).filter_by(username=username).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: User) -> str:
    """Create a new session for `user` and return the raw session token."""
    token = generate_token()
    db.add(
        UserSession(
            token_hash=hash_token(token),
            user_id=user.id,
            expires_at=datetime.utcnow() + SESSION_DURATION,
        )
    )
    db.commit()
    return token


def get_session(db: Session, token: str) -> User | None:
    """Return the user for a valid, unexpired session token, else None."""
    session = db.query(UserSession).filter_by(token_hash=hash_token(token)).first()
    if session is None or session.expires_at < datetime.utcnow():
        return None
    return session.user


def delete_session(db: Session, token: str) -> None:
    """Invalidate a session token, if it exists."""
    db.query(UserSession).filter_by(token_hash=hash_token(token)).delete()
    db.commit()
