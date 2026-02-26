"""
Utility functions for CodeVault API.
"""

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
    sanitized = msg.replace("\n", " ").replace("\r", " ").replace("\x00", "")
    # Remove other control characters (ASCII 0-31 except space)
    sanitized = "".join(c if ord(c) >= 32 or c == " " else " " for c in sanitized)
    # Limit length
    return sanitized[:max_length]


# Regex pattern for valid project IDs (32 hex characters)
PROJECT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


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
        raise SecurityError("Invalid project ID format: must be 32 hex characters")

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

        # Decode percent-encoded sequences to catch traversal attempts
        try:
            from urllib.parse import unquote

            decoded = part_str
            for _ in range(3):
                new_decoded = unquote(decoded)
                if new_decoded == decoded:
                    break
                decoded = new_decoded
        except Exception:
            decoded = part_str

        # Reject overlong UTF-8 encodings for dot segments (e.g. %c0%ae)
        if re.search(r"%c0%ae", part_str, flags=re.IGNORECASE):
            raise SecurityError(f"Path traversal detected in: {part_str}")

        if "\x00" in decoded:
            raise SecurityError("Null byte detected in path component")

        part_path = Path(decoded)

        # Reject absolute paths or drive-letter paths
        if (
            "://" in decoded
            or part_path.is_absolute()
            or re.match(r"^[a-zA-Z]:", decoded)
        ):
            raise SecurityError(f"Absolute path detected in: {decoded}")

        # Reject traversal components
        for segment in part_path.parts:
            if segment in ("..", ".", "") or ".." in segment:
                raise SecurityError(f"Path traversal detected in: {decoded}")

        cleaned_parts.append(decoded)

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

    # Remove path separators, null bytes, and control characters
    filename = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
    filename = re.sub(r"[\x00-\x1f]", "", filename)
    filename = re.sub(r"[<>:\"|?*]", "_", filename)

    # Remove traversal sequences
    while ".." in filename:
        filename = filename.replace("..", "_")

    # Remove leading dots (hidden files) and parent references
    while filename.startswith("."):
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
        segment = "".join(secrets.choice(chars) for _ in range(4))
        parts.append(segment)
    return "-".join(parts)


def generate_api_key() -> str:
    """Generate an API key for user authentication."""
    return f"lw_{secrets.token_hex(24)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256 for storage/comparison.

    We use SHA256 instead of bcrypt because:
    1. API keys are already high-entropy (48 hex chars)
    2. We need to look up by hash on every authenticated request
    3. bcrypt would be too slow for this use case
    """
    # CodeQL: SHA256 is used intentionally for performance on high-entropy keys.
    # This is not a password storage scenario.
    return hashlib.sha256(api_key.encode()).hexdigest()


def _build_signature_message(data: dict) -> str:
    """Build the canonical pipe-delimited message for signing.

    Includes all critical fields to prevent tampering:
    status, expires_at, features, variables, client_nonce, server_nonce, timestamp, server_time.
    """
    import json

    features_json = json.dumps(sorted(data.get("features", [])), sort_keys=True)
    variables_json = json.dumps(data.get("variables", {}), sort_keys=True)

    return "|".join(
        str(v)
        for v in [
            data.get("status", ""),
            data.get("expires_at", "") or "",
            features_json,
            variables_json,
            data.get("client_nonce", ""),
            data.get("server_nonce", ""),
            data.get("timestamp", ""),
            data.get("server_time", ""),
        ]
    )


def compute_signature(data: dict, secret: str) -> str:
    """Compute HMAC-SHA256 signature (legacy, for projects without Ed25519 keys)."""
    message = _build_signature_message(data)
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def compute_ed25519_signature(data: dict, private_key_pem: str) -> str:
    """Compute Ed25519 signature for license validation response.

    Signs the same canonical message as HMAC but with Ed25519 asymmetric keys.
    Returns a base64-encoded signature string.

    The client only needs the PUBLIC key to verify — the private key never
    leaves the server. This eliminates the "skeleton key" vulnerability where
    an attacker could extract the shared secret from a compiled binary.
    """
    import base64
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    message = _build_signature_message(data)
    private_key = load_pem_private_key(private_key_pem.encode(), password=None)
    signature_bytes = private_key.sign(message.encode())
    return base64.b64encode(signature_bytes).decode()


def verify_signature(data: dict, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = compute_signature(data, secret)
    return hmac.compare_digest(expected, signature)


def verify_ed25519_signature(
    data: dict, signature_b64: str, public_key_pem: str
) -> bool:
    """Verify Ed25519 signature."""
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.exceptions import InvalidSignatureError

    try:
        message = _build_signature_message(data)
        public_key = load_pem_public_key(public_key_pem.encode())
        signature_bytes = base64.b64decode(signature_b64.encode())
        public_key.verify(signature_bytes, message.encode())
        return True
    except (InvalidSignatureError, Exception):
        return False


def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT token for user authentication."""
    payload = {
        "sub": user_id,
        "email": email,
        "jti": secrets.token_hex(16),
        "exp": utc_now() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": utc_now(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


_REDIS_UNAVAILABLE_WARNED = False


async def _is_jwt_blacklisted(jti: str) -> bool:
    """Check if a JWT's jti is in the Redis blacklist.

    H2 FIX (previous): If Redis is unavailable, fail CLOSED — treat the token
    as blacklisted to prevent revoked tokens from regaining access during a
    Redis outage.

    C4 FIX: The standard Redis fallback previously called aioredis.from_url()
    on every single authenticated request, creating and immediately closing a
    TCP connection pool each time.  We now prefer the shared _redis_client from
    rate_limiter.py (initialised once at startup) to avoid per-request
    connection churn.  The Upstash REST path is unchanged (it is HTTP-based and
    stateless — constructing the thin client object is negligible).
    """
    global _REDIS_UNAVAILABLE_WARNED
    import logging as _log

    from config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, REDIS_URL

    if not jti:
        return False

    # Try Upstash REST API first (HTTP-based, no persistent connection)
    if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
        try:
            from upstash_redis.asyncio import Redis
            r = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
            result = await r.get(f"jwt_blacklist:{jti}")
            _REDIS_UNAVAILABLE_WARNED = False  # reset on success
            return result is not None
        except Exception as e:
            _log.warning(f"[JWT Blacklist] Upstash unavailable, failing CLOSED: {e}")
            return True  # Fail closed: treat as blacklisted

    # C4 FIX: Reuse the shared connection pool from rate_limiter instead of
    # opening a new TCP connection for every request.
    if REDIS_URL:
        try:
            from middleware.rate_limiter import get_redis_client
            shared_client = await get_redis_client()
            if shared_client is not None:
                result = await shared_client.get(f"jwt_blacklist:{jti}")
                _REDIS_UNAVAILABLE_WARNED = False
                return result is not None
            # Shared client not yet initialised — fall back to direct connection
            import redis.asyncio as aioredis
            r = aioredis.from_url(REDIS_URL)
            result = await r.get(f"jwt_blacklist:{jti}")
            await r.close()
            _REDIS_UNAVAILABLE_WARNED = False
            return result is not None
        except Exception as e:
            _log.warning(f"[JWT Blacklist] Redis unavailable, failing CLOSED: {e}")
            return True  # Fail closed: treat as blacklisted

    # No Redis configured — cannot check blacklist.
    # Log a one-time warning and fail open (best-effort without Redis).
    if not _REDIS_UNAVAILABLE_WARNED:
        _log.warning(
            "[JWT Blacklist] No Redis configured. Token revocation (logout blacklist) "
            "is DISABLED. Configure REDIS_URL or UPSTASH_REDIS_REST_URL to enable it."
        )
        _REDIS_UNAVAILABLE_WARNED = True
    return False


async def blacklist_jwt(jti: str, ttl_seconds: int) -> bool:
    """Add a JWT's jti to the Redis blacklist with TTL.

    C4 FIX: Reuse the shared rate-limiter Redis pool for the standard Redis
    path instead of creating a new connection per call.
    """
    from config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, REDIS_URL
    import logging

    if not jti or ttl_seconds <= 0:
        return False

    # Try Upstash REST API first (HTTP-based, stateless)
    if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
        try:
            from upstash_redis.asyncio import Redis
            r = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
            await r.set(f"jwt_blacklist:{jti}", "1", ex=ttl_seconds)
            return True
        except Exception as e:
            logging.warning(f"[JWT Blacklist] Upstash error: {e}")

    # C4 FIX: Reuse shared connection pool
    if REDIS_URL:
        try:
            from middleware.rate_limiter import get_redis_client
            shared_client = await get_redis_client()
            if shared_client is not None:
                await shared_client.set(f"jwt_blacklist:{jti}", "1", ex=ttl_seconds)
                return True
            # Shared client not available — fall back to direct connection
            import redis.asyncio as aioredis
            r = aioredis.from_url(REDIS_URL)
            await r.set(f"jwt_blacklist:{jti}", "1", ex=ttl_seconds)
            await r.close()
            return True
        except Exception as e:
            logging.warning(f"[JWT Blacklist] Redis error: {e}")

    return False


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload.

    Note: This is synchronous for backwards compatibility.
    For blacklist checking, use verify_jwt_token_async() instead.
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.exceptions.PyJWTError:
        return None


async def verify_jwt_token_async(token: str) -> Optional[dict]:
    """Verify a JWT token with blacklist check and return the payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.exceptions.PyJWTError:
        return None

    # Check if the token's jti is blacklisted (logged out)
    jti = payload.get("jti")
    if jti and await _is_jwt_blacklisted(jti):
        return None

    return payload


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
    x_api_key: Optional[str] = Header(None),
) -> dict:
    """Verify JWT or API key and return user.

    API keys are hashed before comparison with stored hashes for security.
    """
    conn = await get_db()
    try:
        if credentials:
            payload = await verify_jwt_token_async(credentials.credentials)
            if payload:
                user = await conn.fetchrow(
                    "SELECT id, email, name, plan, role, api_key FROM users WHERE id = $1",
                    payload["sub"],
                )
                if user:
                    return dict(user)

        if x_api_key:
            # Hash the incoming API key and compare with stored hash
            hashed_key = hash_api_key(x_api_key)
            user = await conn.fetchrow(
                "SELECT id, email, name, plan, role, api_key FROM users WHERE api_key = $1",
                hashed_key,
            )
            if user:
                return dict(user)

        raise HTTPException(status_code=401, detail="Not authenticated")
    finally:
        await release_db(conn)


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None),
) -> dict:
    """Verify user is authenticated and has admin role."""
    user = await get_current_user(credentials, x_api_key)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def create_validation_response(
    status: str,
    message: str,
    client_nonce: str,
    expires_at: Optional[int] = None,
    features: Optional[List[str]] = None,
    variables: Optional[dict] = None,
    secret: Optional[str] = None,
    private_key_pem: Optional[str] = None,
    license_key: Optional[str] = None,
    jti: Optional[str] = None,
) -> LicenseValidationResponse:
    """Create a signed license validation response (Protocol v2).

    Uses Ed25519 asymmetric signing when private_key_pem is provided (new projects).
    Falls back to HMAC-SHA256 with shared secret for legacy projects only.

    Protocol v2 includes:
    - Nonce binding: client_nonce echoed back for request-response pairing
    - Freshness: issued_at timestamp for replay protection
    - Replay ID (jti): unique identifier to detect replay attacks
    """
    import secrets

    server_nonce = generate_nonce()
    timestamp = int(time.time())
    server_time = timestamp

    # Protocol v2: Use provided jti or generate new one for replay protection
    if jti is None:
        jti = secrets.token_hex(16)
    issued_at = timestamp

    response_data = {
        "status": status,
        "expires_at": expires_at or "",
        "features": features or [],
        "variables": variables or {},
        "client_nonce": client_nonce,
        "server_nonce": server_nonce,
        "timestamp": timestamp,
        "server_time": server_time,
        "issued_at": issued_at,
        "jti": jti,
    }

    # Protocol v2: Require Ed25519 for all new responses (no HMAC fallback)
    if private_key_pem:
        signature = compute_ed25519_signature(response_data, private_key_pem)
    else:
        # HMAC fallback ONLY for legacy projects without Ed25519 keys.
        # H8 WARNING: All legacy projects that lack an Ed25519 signing key share the
        # application-wide SECRET_KEY as their HMAC secret. Compromising SECRET_KEY
        # breaks validation integrity for ALL such projects simultaneously.
        # Mitigation: migrate projects to Ed25519 keys via the admin Ed25519 migration
        # endpoint (/api/v1/admin/migrate-ed25519). New projects always get Ed25519 keys.
        import logging as _log

        _log.getLogger(__name__).warning(
            "[SECURITY H8] HMAC fallback used for license validation response — this "
            "project has no Ed25519 signing key. All HMAC-signed projects share the "
            "global SECRET_KEY; a single key compromise breaks all legacy projects. "
            "Migrate via POST /api/v1/admin/migrate-ed25519."
        )
        active_secret = secret or SECRET_KEY
        signature = compute_signature(response_data, active_secret)

    return LicenseValidationResponse(
        status=status,
        message=message,
        expires_at=expires_at,
        features=features or [],
        variables=variables or {},
        client_nonce=client_nonce,
        server_nonce=server_nonce,
        timestamp=timestamp,
        signature=signature,
        server_time=server_time,
        issued_at=issued_at,
        jti=jti,
        protocol_version="v2",
        lease_token=None,  # Will be set by caller if needed
    )


# =============================================================================
# Protocol v2: Replay Protection
# =============================================================================

RESPONSE_MAX_AGE_SECONDS = 300  # 5 minutes max age for responses


async def check_and_store_jti(jti: str, license_key: str) -> tuple[bool, str]:
    """Check if jti has been used before (replay attack) and store it.

    Uses Redis for fast in-memory lookup. The jti is stored with a TTL
    matching the response max age.

    Returns:
        (is_valid, error_message) - is_valid False if replay detected
    """
    from config import REDIS_URL, UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
    import logging

    redis_key = f"jti:{license_key}:{jti}"

    # O3 FIX: Use SET key value EX ttl NX (set-if-not-exists) for an atomic
    # check-and-store. The previous EXISTS + SETEX pair had a TOCTOU window where
    # two concurrent requests with the same jti could both pass the check before
    # either stored it.  SET NX is a single atomic Redis command.

    # Prefer Upstash REST API for serverless environments (no TCP connection issues)
    if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
        try:
            from upstash_redis.asyncio import Redis

            r = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)

            # SET NX: returns True if key was newly set (jti not seen before),
            # False if key already existed (replay attack).
            was_set = await r.set(redis_key, "1", ex=RESPONSE_MAX_AGE_SECONDS, nx=True)
            if not was_set:
                return False, "Replay attack detected: jti already used"
            return True, ""
        except ImportError:
            logging.warning(
                "[Security] upstash-redis not installed, falling back to redis-py"
            )
        except Exception as e:
            logging.error(f"[Security] Upstash REST API error: {e}")
            # Don't fail license validation on Redis errors — log and continue
            return True, ""

    # Fallback to traditional Redis connection
    if not REDIS_URL:
        logging.warning("[Security] REDIS_URL not set, skipping jti replay check")
        return True, ""

    try:
        import redis.asyncio as redis

        r = redis.from_url(REDIS_URL)

        # SET NX atomic check-and-store
        was_set = await r.set(redis_key, "1", ex=RESPONSE_MAX_AGE_SECONDS, nx=True)
        await r.close()
        if not was_set:
            return False, "Replay attack detected: jti already used"
        return True, ""
    except Exception as e:
        logging.error(f"[Security] Failed to check jti replay: {e}")
        logging.warning("[Security] Allowing validation despite Redis error")
        return True, ""


def validate_response_freshness(
    issued_at: int, max_age: int = RESPONSE_MAX_AGE_SECONDS
) -> tuple[bool, str]:
    """Validate that a response is not stale based on issued_at timestamp.

    Returns:
        (is_fresh, error_message)
    """
    current_time = int(time.time())
    age = current_time - issued_at

    if age > max_age:
        return False, f"Response stale: age {age}s exceeds max {max_age}s"

    if age < -60:
        # Allow 60s clock skew but reject future-dated responses
        return False, f"Response from future: clock skew detected"

    return True, ""


# =============================================================================
# Phase 4: Server-Signed Lease Tokens
# =============================================================================

LEASE_DURATION_SECONDS = 86400  # 24 hours default lease duration


def create_lease_token(
    license_key: str,
    hwid: str,
    expires_at: int,
    private_key_pem: Optional[str] = None,
    secret: Optional[str] = None,
) -> str:
    """Create a server-signed lease token for offline validation.

    The lease token includes:
    - nbf: not before (server_time)
    - exp: expiration timestamp
    - hwid: hardware ID bound to this lease
    - license_id: license key (hashed)
    - jti: unique identifier for anti-replay

    The token is signed with Ed25519 (preferred) or HMAC (legacy).
    """
    import secrets

    server_time = int(time.time())
    jti = secrets.token_hex(16)

    lease_payload = {
        "nbf": server_time,
        "exp": expires_at,
        "hwid": hwid,
        "license_key_hash": hashlib.sha256(license_key.encode()).hexdigest(),
        "jti": jti,
        "server_time": server_time,
    }

    if private_key_pem:
        signature = compute_ed25519_signature(lease_payload, private_key_pem)
    else:
        active_secret = secret or SECRET_KEY
        signature = compute_signature(lease_payload, active_secret)

    import json
    import base64

    token_data = json.dumps({"payload": lease_payload, "signature": signature})

    return base64.b64encode(token_data.encode()).decode()


def validate_lease_token(
    lease_token: str,
    hwid: str,
    public_key_pem: Optional[str] = None,
    secret: Optional[str] = None,
) -> tuple[bool, str]:
    """Validate a server-signed lease token.

    H3 FIX: Parameter renamed from ``private_key_pem`` to ``public_key_pem``.
    Lease tokens are *verified* with the Ed25519 **public** key, not signed
    (signing uses the private key at issuance time in create_lease_token).
    Passing a private key to Ed25519PublicKey.verify() causes a cryptography
    library exception and would silently return False in the old code.

    Args:
        lease_token:    Base64-encoded lease blob returned by create_lease_token.
        hwid:           Hardware ID of the machine attempting to use the lease.
        public_key_pem: Ed25519 PUBLIC key PEM for Ed25519-signed leases.
        secret:         HMAC shared secret for legacy leases without Ed25519.

    Returns:
        (is_valid, error_message)
    """
    import json
    import base64

    try:
        token_data = json.loads(base64.b64decode(lease_token.encode()).decode())
        lease_payload = token_data.get("payload", {})
        signature = token_data.get("signature", "")
    except Exception as e:
        return False, f"Invalid lease token format: {e}"

    current_time = int(time.time())
    exp = lease_payload.get("exp", 0)
    if current_time > exp:
        return False, "Lease expired"

    nbf = lease_payload.get("nbf", 0)
    if current_time < nbf:
        return False, "Lease not yet valid"

    if lease_payload.get("hwid") != hwid:
        return False, "HWID mismatch"

    if public_key_pem:
        is_valid = verify_ed25519_signature(lease_payload, signature, public_key_pem)
    else:
        active_secret = secret or SECRET_KEY
        is_valid = verify_signature(lease_payload, signature, active_secret)

    if not is_valid:
        return False, "Invalid lease signature"

    return True, ""


async def get_user_tier_limits(user_id: str, conn) -> dict:
    """Get subscription tier limits for a user.

    Returns the TIER_LIMITS dict for the user's current subscription tier.
    Checks subscriptions table first, then falls back to users table plan.
    Defaults to 'free' tier if no subscription found and no user plan set.

    Args:
        user_id: The user's ID
        conn: Database connection

    Returns:
        dict with tier limits (max_projects, max_licenses_per_project, etc.)
    """
    from config import TIER_LIMITS

    # Check for active subscription first
    sub = await conn.fetchrow(
        """
        SELECT plan_tier FROM subscriptions 
        WHERE user_id = $1 AND status = 'active'
        ORDER BY created_at DESC LIMIT 1
    """,
        user_id,
    )

    if sub:
        tier = sub["plan_tier"]
    else:
        # Fallback to user's plan column (for manually assigned plans/admins)
        user = await conn.fetchrow("SELECT plan FROM users WHERE id = $1", user_id)
        tier = user["plan"] if user else "free"

    # Normalize tier name to lowercase and handle unknown tiers
    tier = tier.lower() if tier else "free"
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


async def get_user_tier(user_id: str, conn) -> dict:
    """Get user's subscription tier and white-label branding features.

    Returns tier information including whether the user can remove branding
    from their compiled executables.

    Args:
        user_id: The user's ID
        conn: Database connection

    Returns:
        dict with:
            - tier: string ('free', 'pro', 'business')
            - is_pro: bool (True if pro or business)
            - can_remove_branding: bool (True if pro or business)
            - can_custom_branding: bool (True only for business)
    """
    sub = await conn.fetchrow(
        """
        SELECT plan_tier, status 
        FROM subscriptions 
        WHERE user_id = $1 AND status = 'active'
        ORDER BY created_at DESC LIMIT 1
        """,
        user_id,
    )

    # If no active subscription, fallback to users.plan column
    if not sub:
        user = await conn.fetchrow("SELECT plan FROM users WHERE id = $1", user_id)
        tier = user["plan"].lower() if user and user["plan"] else "free"
    else:
        tier = sub["plan_tier"].lower() if sub["plan_tier"] else "free"

    return {
        "tier": tier,
        "is_pro": tier in ["pro", "business"],
        "can_remove_branding": tier in ["pro", "business"],
        "can_custom_branding": tier == "business",
    }
