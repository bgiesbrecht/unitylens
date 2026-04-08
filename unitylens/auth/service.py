"""Database-backed user and session management."""

from __future__ import annotations

import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from unitylens.auth.passwords import hash_password, verify_password

logger = logging.getLogger(__name__)

SESSION_TTL = timedelta(days=7)
SESSION_COOKIE_NAME = "unitylens_session"
VALID_ROLES = {"admin", "viewer"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def create_user(
    conn: sqlite3.Connection, username: str, password: str, role: str
) -> dict[str, Any]:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Expected one of {VALID_ROLES}")
    pw_hash, pw_salt = hash_password(password)
    now = _iso(_now())
    cur = conn.execute(
        """
        INSERT INTO users (username, password_hash, password_salt, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, pw_hash, pw_salt, role, now, now),
    )
    conn.commit()
    return {
        "user_id": cur.lastrowid,
        "username": username,
        "role": role,
        "created_at": now,
        "updated_at": now,
    }


def get_user_by_username(
    conn: sqlite3.Connection, username: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def list_users(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT user_id, username, role, created_at, updated_at FROM users ORDER BY username"
    ).fetchall()
    return [dict(r) for r in rows]


def set_password(
    conn: sqlite3.Connection, user_id: int, new_password: str
) -> None:
    pw_hash, pw_salt = hash_password(new_password)
    conn.execute(
        """
        UPDATE users
           SET password_hash = ?, password_salt = ?, updated_at = ?
         WHERE user_id = ?
        """,
        (pw_hash, pw_salt, _iso(_now()), user_id),
    )
    # Invalidate any existing sessions for this user — force re-login.
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()


def authenticate(
    conn: sqlite3.Connection, username: str, password: str
) -> dict[str, Any] | None:
    user = get_user_by_username(conn, username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"], user["password_salt"]):
        return None
    return user


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def create_session(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    now = _now()
    expires = now + SESSION_TTL
    conn.execute(
        """
        INSERT INTO sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (token, user_id, _iso(now), _iso(expires)),
    )
    conn.commit()
    return {
        "token": token,
        "user_id": user_id,
        "created_at": _iso(now),
        "expires_at": _iso(expires),
    }


def get_session(
    conn: sqlite3.Connection, token: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    if not row:
        return None
    session = dict(row)
    if _parse_iso(session["expires_at"]) < _now():
        # Expired — clean up.
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return None
    return session


def touch_session(conn: sqlite3.Connection, token: str) -> str:
    """Slide the session expiry forward and return the new ISO expiry."""
    new_expiry = _iso(_now() + SESSION_TTL)
    conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE token = ?",
        (new_expiry, token),
    )
    conn.commit()
    return new_expiry


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


def purge_expired_sessions(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "DELETE FROM sessions WHERE expires_at < ?", (_iso(_now()),)
    )
    conn.commit()
    return cur.rowcount


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def seed_default_users(conn: sqlite3.Connection) -> None:
    """Create default admin and public accounts if no users exist."""
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        return

    admin_password = os.environ.get("UNITYLENS_ADMIN_PASSWORD", "adminpwd")
    viewer_password = os.environ.get("UNITYLENS_VIEWER_PASSWORD", "public")

    create_user(conn, "admin", admin_password, "admin")
    create_user(conn, "public", viewer_password, "viewer")

    logger.warning(
        "Seeded default accounts: admin/%s and public/%s. "
        "Change them via the Admin page or set UNITYLENS_ADMIN_PASSWORD / UNITYLENS_VIEWER_PASSWORD.",
        "*****" if "UNITYLENS_ADMIN_PASSWORD" in os.environ else admin_password,
        "*****" if "UNITYLENS_VIEWER_PASSWORD" in os.environ else viewer_password,
    )
