"""
Utility functions for CodeVault API.
"""

import os
import re
import time
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Union

import jwt
import bcrypt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import SECRET_KEY, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from database import get_db, release_db
from models import LicenseValidationResponse


# =============================================================================
# Path Security Utilities (Prevent Path Traversal Attacks)
# =============================================================================

class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


def sanitize_log_message(msg: str, max_length: int = 500) -> str:
    """
    Sanitize a message for safe logging to prevent log injection attacks.
    
    Removes control characters (newlines, carriage returns, etc.) and limits length.
    
    Args:
        msg: The message to sanitize
        max_length: Maximum allowed length (default 500)
        
    Returns:
        Sanitized string safe for logging
    """
    if not isinstance(msg, str):
        msg = str(msg)
    # Remove control characters that could forge log entries
    sanitized = msg.replace('\n', ' ').replace('\r', ' ').replace('\x00', '')
    # Remove other control characters (ASCII 0-31 except space)
    sanitized = ''.join(c if ord(c) >= 32 or c == ' ' else ' ' for c in sanitized)
    # Limit length
    return sanitized[:max_length]


# Regex pattern for valid project IDs (32 hex characters)
PROJECT_ID_PATTERN = re.compile(r'^[a-f0-9]{32}$')


def validate_project_id(project_id: str) -> bool:
    """
    Validate that a project_id is a valid hex string.
    
    Args:
        project_id: The project ID to validate
        
    Returns:
        True if valid
        
    Raises:
        SecurityError: If the project_id is invalid
    """
    if not project_id or not isinstance(project_id, str):
        raise SecurityError("Invalid project ID: empty or not a string")
    
    if not PROJECT_ID_PATTERN.match(project_id):
        raise SecurityError(f"Invalid project ID format: must be 32 hex characters")
    
    return True


def safe_join(base: Path, *parts: str) -> Path:
    """
    Safely join path components, preventing path traversal attacks.
    
    Args:
        base: The base directory (must be absolute)
        *parts: Path components to join
        
    Returns:
        Resolved absolute Path that is guaranteed to be within base
        
    Raises:
        SecurityError: If the resulting path escapes the base directory
    """
    if not base.is_absolute():
        base = base.resolve()
    
    # Clean each part to remove dangerous components
    cleaned_parts = []
    for part in parts:
        if not part:
            continue
        # Convert to string and clean
        part_str = str(part)
        # Reject obvious traversal attempts
        if '..' in part_str or part_str.startswith('/') or part_str.startswith('\\'):
            raise SecurityError(f"Path traversal detected in: {part_str}")
        cleaned_parts.append(part_str)
    
    # Join and resolve the full path
    if cleaned_parts:
        target = base.joinpath(*cleaned_parts).resolve()
    else:
        target = base.resolve()
    
    # Verify the resolved path is within the base
    try:
        target.relative_to(base.resolve())
    except ValueError:
        raise SecurityError(f"Path escapes base directory: {target}")
    
    return target


def validate_safe_path(base: Path, target: Union[Path, str]) -> Path:
    """
    Validate that a target path is safely within a base directory.
    
    Args:
        base: The allowed base directory
        target: The path to validate (can be string or Path)
        
    Returns:
        Resolved absolute Path that is guaranteed to be within base
        
    Raises:
        SecurityError: If the target escapes the base directory
    """
    base_resolved = base.resolve()
    
    if isinstance(target, str):
        target = Path(target)
    
    target_resolved = target.resolve()
    
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise SecurityError(f"Path escapes allowed directory: {target_resolved}")
    
    return target_resolved


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and invalid characters.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "unnamed"
    
    # Remove path separators and null bytes
    filename = filename.replace('/', '_').replace('\\', '_').replace('\x00', '')
    
    # Remove leading dots (hidden files) and parent references
    while filename.startswith('.'):
        filename = filename[1:]
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename or "unnamed"

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
