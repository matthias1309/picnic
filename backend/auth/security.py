"""
Password hashing and session token utilities.

Traces: ARCH-006
"""

import hashlib
import hmac
import secrets

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16
TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    """Hash a password as `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a hash produced by `hash_password`."""
    try:
        algorithm, iterations_str, salt_hex, digest_hex = password_hash.split("$")
    except ValueError:
        return False
    if algorithm != PBKDF2_ALGORITHM:
        return False

    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations_str))
    return hmac.compare_digest(expected.hex(), digest_hex)


def generate_token() -> str:
    """Generate a random, high-entropy session token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Hash a session token for storage (so a DB leak doesn't expose live sessions)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
