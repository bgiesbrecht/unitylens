"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from typing import Any

from fastapi import Cookie, Depends, HTTPException, status

from unitylens.auth.service import (
    SESSION_COOKIE_NAME,
    get_session,
    get_user_by_id,
    touch_session,
)
from unitylens.store import db


def current_user(
    unitylens_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    """Resolve the authenticated user from the session cookie.

    Slides the session expiry forward on every successful request
    (rolling session window).
    """
    if not unitylens_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    conn = db.get_connection()
    try:
        session = get_session(conn, unitylens_session)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
            )
        user = get_user_by_id(conn, session["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists",
            )
        # Slide expiry forward.
        touch_session(conn, unitylens_session)
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
        }
    finally:
        conn.close()


def require_admin(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
