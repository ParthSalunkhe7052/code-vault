"""
Authentication routes for CodeVault API.
Extracted from main.py for modularity.
"""

import secrets
import bcrypt
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from models import LoginRequest, RegisterRequest, ResetPasswordRequest
from utils import (
    generate_api_key,
    create_jwt_token,
    get_current_user,
    get_current_admin_user,
    utc_now,
)
from database import get_db, release_db
from middleware.rate_limiter import (
    login_rate_limit,
    register_rate_limit,
    api_key_regen_rate_limit,
    password_reset_rate_limit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register")
async def register(
    request: Request,
    data: RegisterRequest,
    _rate_limit: None = Depends(register_rate_limit)
):
    # Normalize email to lowercase for case-insensitive comparison
    data.email = data.email.lower().strip()
    
    conn = await get_db()
    try:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", data.email
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
        user_id = secrets.token_hex(16)
        api_key = generate_api_key()

        await conn.execute(
            """
            INSERT INTO users (id, email, password_hash, name, api_key) VALUES ($1, $2, $3, $4, $5)
        """,
            user_id,
            data.email,
            password_hash,
            data.name,
            api_key,
        )

        token = create_jwt_token(user_id, data.email)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": data.email,
                "name": data.name,
                "plan": "free",
                "api_key": api_key,
            },
        }
    finally:
        await release_db(conn)


@router.post("/login")
async def login(
    request: Request,
    data: LoginRequest,
    _rate_limit: None = Depends(login_rate_limit)
):
    # Normalize email to lowercase for case-insensitive comparison
    data.email = data.email.lower().strip()
    
    conn = await get_db()
    try:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash, name, plan, role, api_key FROM users WHERE email = $1",
            data.email,
        )

        if not user:
            print(f"[Login] User not found: {data.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        try:
            password_match = bcrypt.checkpw(
                data.password.encode(), user["password_hash"].encode()
            )
            if not password_match:
                print(f"[Login] Password mismatch for user: {data.email}")
                raise HTTPException(status_code=401, detail="Invalid email or password")
        except Exception as e:
            print(f"[Login] Password verification error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        print(
            f"[Login] Successful login: {data.email} (role: {user.get('role', 'user')})"
        )
        token = create_jwt_token(user["id"], user["email"])
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "plan": user["plan"],
                "role": user.get("role", "user"),
                "api_key": user["api_key"],
            },
        }
    finally:
        await release_db(conn)


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user with latest subscription tier from database."""
    conn = await get_db()
    try:
        # Fetch latest plan_tier from subscriptions table (authoritative source)
        sub_row = await conn.fetchrow("""
            SELECT plan_tier FROM subscriptions
            WHERE user_id = $1
            ORDER BY created_at DESC LIMIT 1
        """, user["id"])

        # Use subscription tier if exists, otherwise fall back to users.plan
        plan = sub_row["plan_tier"] if sub_row else user.get("plan", "free")

        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "plan": plan,
            "role": user.get("role", "user"),
            "api_key": user.get("api_key"),
            "created_at": utc_now().isoformat(),
        }
    finally:
        await release_db(conn)


@router.post("/regenerate-api-key")
async def regenerate_api_key_endpoint(
    request: Request,
    user: dict = Depends(get_current_user),
    _rate_limit: None = Depends(api_key_regen_rate_limit)
):
    new_api_key = generate_api_key()
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE users SET api_key = $1, updated_at = NOW() WHERE id = $2",
            new_api_key,
            user["id"],
        )
        return {"api_key": new_api_key}
    finally:
        await release_db(conn)


@router.post("/reset-password")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    user: dict = Depends(get_current_user),
    _rate_limit: None = Depends(password_reset_rate_limit)
):
    """Reset password for logged-in user"""
    password_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
            password_hash,
            user["id"],
        )
        return {"message": "Password reset successfully"}
    finally:
        await release_db(conn)


# Pydantic model for admin password reset (fixing security issue #7)
class AdminResetPasswordRequest(BaseModel):
    """Request model for admin password reset with proper validation."""
    email: EmailStr
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/admin-reset-password")
async def admin_reset_password(
    request: Request,
    data: AdminResetPasswordRequest,
    admin_user: dict = Depends(get_current_admin_user),
    _rate_limit: None = Depends(password_reset_rate_limit)
):
    """Admin endpoint to reset any user's password (admin auth required)"""
    # Normalize email to match stored format (consistent with register/login)
    email = data.email.lower().strip()

    conn = await get_db()
    try:
        user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        password_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
        await conn.execute(
            "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
            password_hash,
            user["id"],
        )
        # Use logger instead of print, don't log full email
        logger.info(
            f"[Admin] Password reset for user ID: {user['id'][:8]}... "
            f"(by admin: {admin_user['id'][:8]}...)"
        )
        return {"message": f"Password reset successfully for {email}"}
    finally:
        await release_db(conn)
