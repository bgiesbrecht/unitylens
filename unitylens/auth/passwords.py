"""Password hashing using stdlib pbkdf2_hmac (no external dependencies)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGO = "sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> tuple[str, str]:
    """Return (hash_hex, salt_hex) for a new password."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _ALGO, password.encode("utf-8"), salt, _ITERATIONS
    )
    return digest.hex(), salt.hex()


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Constant-time verification of a password against stored hash + salt."""
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        _ALGO, password.encode("utf-8"), salt, _ITERATIONS
    )
    return hmac.compare_digest(candidate, expected)
