"""
Login rate limiting (lockout after repeated failed attempts).

Traces: ARCH-007
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.models import LoginAttempt

MAX_FAILED_ATTEMPTS = 5
ATTEMPT_WINDOW = timedelta(minutes=15)
LOCKOUT_DURATION = timedelta(minutes=15)


def is_locked_out(db: Session, username: str) -> bool:
    """Return True if `username` is currently within an active lockout."""
    attempt = db.query(LoginAttempt).filter_by(username=username).first()
    if attempt is None or attempt.locked_until is None:
        return False
    return attempt.locked_until > datetime.utcnow()


def record_failed_attempt(db: Session, username: str) -> None:
    """Record a failed login attempt, locking the account if the
    threshold is reached within the attempt window."""
    now = datetime.utcnow()
    attempt = db.query(LoginAttempt).filter_by(username=username).first()

    if attempt is None or now - attempt.first_failed_at > ATTEMPT_WINDOW:
        attempt = LoginAttempt(username=username, failed_count=0, first_failed_at=now)
        db.add(attempt)

    attempt.failed_count += 1
    if attempt.failed_count >= MAX_FAILED_ATTEMPTS:
        attempt.locked_until = now + LOCKOUT_DURATION

    db.commit()


def reset_attempts(db: Session, username: str) -> None:
    """Clear any tracked failed attempts for `username` (successful login)."""
    db.query(LoginAttempt).filter_by(username=username).delete()
    db.commit()
