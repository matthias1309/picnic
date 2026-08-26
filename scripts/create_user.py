"""
Maintenance script: create a dashboard login, or reset an existing one's password.

REQ-006 deliberately has no self-registration and no password-reset UI —
accounts are managed directly by the developer. This script is that path.

The password is never taken as a command-line argument: it would land in the
shell history and in the process list. It is prompted for instead, twice, and
only its PBKDF2 hash is ever written to the database.

Usage:
    python -m scripts.create_user <username>
    python -m scripts.create_user <username> --reset
"""

import getpass
import sys

from backend.auth.security import hash_password
from backend.database import SessionLocal, init_db
from backend.models import User

MIN_PASSWORD_LENGTH = 8


def prompt_for_password() -> str:
    """Ask for a password twice, returning it only once both entries agree."""
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match")

    return password


def create_user(username: str, *, reset: bool = False) -> None:
    """Create `username`, or replace its password when `reset` is set."""
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()

        if existing is None and reset:
            raise SystemExit(f"User {username!r} does not exist — omit --reset to create it")

        if existing is not None and not reset:
            raise SystemExit(
                f"User {username!r} already exists — pass --reset to set a new password"
            )

        password_hash = hash_password(prompt_for_password())

        if existing is None:
            db.add(User(username=username, password_hash=password_hash))
            action = "Created"
        else:
            existing.password_hash = password_hash
            # Existing sessions keep working; a password change is not a logout.
            action = "Updated password for"

        db.commit()
        print(f"{action} user {username!r}")
    finally:
        db.close()


if __name__ == "__main__":
    arguments = sys.argv[1:]
    reset_requested = "--reset" in arguments
    positional = [argument for argument in arguments if argument != "--reset"]

    if len(positional) != 1:
        raise SystemExit("Usage: python -m scripts.create_user <username> [--reset]")

    create_user(positional[0], reset=reset_requested)
