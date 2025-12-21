"""
Utility functions for CodeVault API.
"""

import time
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import jwt
import bcrypt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import SECRET_KEY, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from database import get_db, release_db
from models import LicenseValidationResponse

# Security
security = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def generate_nonce() -> str:
    """Generate a random nonce for license validation."""
    return secrets.token_hex(16)


def generate_license_key(prefix: str = "LIC") -> str:
    """Generate a license key with the given prefix."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    parts = [prefix]
    for _ in range(4):
        segment = ''.join(secrets.choice(chars) for _ in range(4))
        parts.append(segment)
    return '-'.join(parts)


def generate_api_key() -> str:
    """Generate an API key for user authentication."""
    return f"lw_{secrets.token_hex(24)}"


def compute_signature(data: dict, secret: str) -> str:
    """Compute HMAC-SHA256 signature for license validation response."""
    message = '|'.join(str(v) for v in [
        data.get('status', ''),
        data.get('expires_at', ''),
        data.get('client_nonce', ''),
        data.get('server_nonce', ''),
        data.get('timestamp', '')
    ])
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT token for user authentication."""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": utc_now() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": utc_now()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.exceptions.PyJWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Verify JWT or API key and return user."""
    conn = await get_db()
    try:
        if credentials:
            payload = verify_jwt_token(credentials.credentials)
            if payload:
                user = await conn.fetchrow(
                    "SELECT id, email, name, plan, role, api_key FROM users WHERE id = $1",
                    payload["sub"]
                )
                if user:
                    return dict(user)
        
        if x_api_key:
            user = await conn.fetchrow(
                "SELECT id, email, name, plan, role, api_key FROM users WHERE api_key = $1",
                x_api_key
            )
            if user:
                return dict(user)
        
        raise HTTPException(status_code=401, detail="Not authenticated")
    finally:
        await release_db(conn)


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Verify user is authenticated and has admin role."""
    user = await get_current_user(credentials, x_api_key)
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def create_validation_response(
    status: str, 
    message: str, 
    client_nonce: str,
    expires_at: Optional[int] = None, 
    features: List[str] = None
) -> LicenseValidationResponse:
    """Create a signed license validation response."""
    server_nonce = generate_nonce()
    timestamp = int(time.time())
    response_data = {
        'status': status, 
        'expires_at': expires_at or '',
        'client_nonce': client_nonce, 
        'server_nonce': server_nonce, 
        'timestamp': timestamp
    }
    signature = compute_signature(response_data, SECRET_KEY)
    return LicenseValidationResponse(
        status=status, 
        message=message, 
        expires_at=expires_at,
        features=features or [], 
        client_nonce=client_nonce,
        server_nonce=server_nonce, 
        timestamp=timestamp, 
        signature=signature
    )


async def get_user_tier_limits(user_id: str, conn) -> dict:
    """Get subscription tier limits for a user.
    
    Returns the TIER_LIMITS dict for the user's current subscription tier.
    Defaults to 'free' tier if no subscription found.
    
    Args:
        user_id: The user's ID
        conn: Database connection
        
    Returns:
        dict with tier limits (max_projects, max_licenses_per_project, etc.)
    """
    from config import TIER_LIMITS
    sub = await conn.fetchrow("""
        SELECT plan_tier FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1
    """, user_id)
    tier = sub['plan_tier'] if sub else 'free'
    return TIER_LIMITS.get(tier, TIER_LIMITS['free'])
