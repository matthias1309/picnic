"""
CLI to create or update Picnic Expense Tracker user accounts.

Traces: ARCH-006 (Key Decision 5) — one-off admin tool, not unit-tested
(TDD exception per .claude/rules/v-model.md); password hashing itself is
covered by TEST-006 (backend/tests/test_auth.py).

Usage:
    python -m backend.scripts.manage_users create <username>
    python -m backend.scripts.manage_users set-password <username>
"""

import getpass
import sys

from backend.auth.security import hash_password
from backend.database import SessionLocal, init_db
from backend.models import User


def _read_password() -> str:
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    return password


def create_user(username: str) -> None:
    password = _read_password()
    db = SessionLocal()
    try:
        if db.query(User).filter_by(username=username).first() is not None:
            raise SystemExit(f"User '{username}' already exists")
        db.add(User(username=username, password_hash=hash_password(password)))
        db.commit()
        print(f"Created user '{username}'")
    finally:
        db.close()


def set_password(username: str) -> None:
    password = _read_password()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if user is None:
            raise SystemExit(f"User '{username}' not found")
        user.password_hash = hash_password(password)
        db.commit()
        print(f"Updated password for '{username}'")
    finally:
        db.close()


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ("create", "set-password"):
        raise SystemExit(
            "Usage: python -m backend.scripts.manage_users <create|set-password> <username>"
        )

    init_db()
    command, username = sys.argv[1], sys.argv[2]
    if command == "create":
        create_user(username)
    else:
        set_password(username)


if __name__ == "__main__":
    main()
