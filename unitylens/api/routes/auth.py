"""Authentication API routes: login, logout, me, and user management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from unitylens.auth.deps import current_user, require_admin
from unitylens.auth.service import (
    SESSION_COOKIE_NAME,
    SESSION_TTL,
    authenticate,
    create_session,
    create_user,
    delete_session,
    get_user_by_username,
    list_users,
    set_password,
)
from unitylens.store import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=4)


class AdminPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=4)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=4)
    role: str = Field(pattern="^(admin|viewer)$")


# ---------------------------------------------------------------------------
# Public auth endpoints
# ---------------------------------------------------------------------------


@router.post("/login")
def login(req: LoginRequest, response: Response) -> dict[str, Any]:
    conn = db.get_connection()
    try:
        user = authenticate(conn, req.username, req.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        session = create_session(conn, user["user_id"])
    finally:
        conn.close()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session["token"],
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return {
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
        }
    }


@router.post("/logout")
def logout(
    response: Response, user: dict[str, Any] = Depends(current_user)
) -> dict[str, str]:
    # current_user dep guarantees we have a valid session cookie; tear it down.
    from fastapi import Request  # local import to avoid circulars

    # We need the raw cookie value, but `current_user` doesn't return it.
    # Easiest: clear the cookie client-side and best-effort delete by user.
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    conn = db.get_connection()
    try:
        # Clear all sessions for this user (log out everywhere).
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ?", (user["user_id"],)
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "logged_out"}


@router.get("/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return user


@router.post("/password")
def change_own_password(
    req: PasswordChangeRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, str]:
    """Change the current user's own password."""
    if not req.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_password is required",
        )
    conn = db.get_connection()
    try:
        full = get_user_by_username(conn, user["username"])
        if not full:
            raise HTTPException(status_code=404, detail="User not found")
        from unitylens.auth.passwords import verify_password

        if not verify_password(
            req.current_password, full["password_hash"], full["password_salt"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current password is incorrect",
            )
        set_password(conn, full["user_id"], req.new_password)
    finally:
        conn.close()
    return {"status": "password_updated"}


# ---------------------------------------------------------------------------
# Admin-only user management
# ---------------------------------------------------------------------------


@router.get("/users")
def get_users(
    _: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    conn = db.get_connection()
    try:
        return list_users(conn)
    finally:
        conn.close()


@router.post("/users")
def create_new_user(
    req: CreateUserRequest,
    _: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    conn = db.get_connection()
    try:
        if get_user_by_username(conn, req.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User '{req.username}' already exists",
            )
        return create_user(conn, req.username, req.password, req.role)
    finally:
        conn.close()


@router.post("/users/{username}/password")
def admin_reset_password(
    username: str,
    req: AdminPasswordResetRequest,
    _: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    conn = db.get_connection()
    try:
        target = get_user_by_username(conn, username)
        if not target:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        set_password(conn, target["user_id"], req.new_password)
    finally:
        conn.close()
    return {"status": "password_updated", "username": username}


@router.delete("/users/{username}")
def delete_user(
    username: str,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    if username == actor["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    conn = db.get_connection()
    try:
        target = get_user_by_username(conn, username)
        if not target:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        conn.execute("DELETE FROM users WHERE user_id = ?", (target["user_id"],))
        conn.commit()
    finally:
        conn.close()
    return {"status": "deleted", "username": username}
