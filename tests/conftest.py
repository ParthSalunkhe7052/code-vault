"""
Pytest Configuration and Shared Fixtures for CodeVault.

This module provides reusable fixtures for testing the CodeVault application,
including database connections, authenticated clients, mock factories, and
security test utilities.
"""

import pytest
import os
import sys
import secrets
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


# =============================================================================
# Basic Test Client Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def app():
    """Create a FastAPI test application instance."""
    try:
        from main import app as fastapi_app
        return fastapi_app
    except ImportError as e:
        pytest.skip(f"Could not import main app: {e}")


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create an async test client for the FastAPI app."""
    try:
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    except ImportError:
        pytest.skip("httpx not installed - install with: pip install httpx")


# =============================================================================
# Mock User and Authentication Fixtures
# =============================================================================

@pytest.fixture
def mock_user() -> Dict[str, Any]:
    """Generate a mock user for testing."""
    return {
        "id": secrets.token_hex(16),
        "email": f"test_{secrets.token_hex(4)}@example.com",
        "name": "Test User",
        "role": "user",
        "tier": "free",
        "stripe_customer_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_key": secrets.token_hex(32),
    }


@pytest.fixture
def mock_admin_user() -> Dict[str, Any]:
    """Generate a mock admin user for testing."""
    return {
        "id": secrets.token_hex(16),
        "email": f"admin_{secrets.token_hex(4)}@example.com",
        "name": "Admin User",
        "role": "admin",
        "tier": "enterprise",
        "stripe_customer_id": f"cus_{secrets.token_hex(14)}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_key": secrets.token_hex(32),
    }


@pytest.fixture
def auth_token(mock_user) -> str:
    """Generate a valid JWT token for testing."""
    try:
        import jwt
        from config import JWT_SECRET

        payload = {
            "sub": mock_user["id"],
            "email": mock_user["email"],
            "role": mock_user["role"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    except ImportError:
        return "test_token_" + secrets.token_hex(16)


@pytest.fixture
def admin_auth_token(mock_admin_user) -> str:
    """Generate a valid admin JWT token for testing."""
    try:
        import jwt
        from config import JWT_SECRET

        payload = {
            "sub": mock_admin_user["id"],
            "email": mock_admin_user["email"],
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    except ImportError:
        return "admin_token_" + secrets.token_hex(16)


@pytest.fixture
def auth_headers(auth_token) -> Dict[str, str]:
    """Generate authentication headers for API requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_auth_headers(admin_auth_token) -> Dict[str, str]:
    """Generate admin authentication headers for API requests."""
    return {"Authorization": f"Bearer {admin_auth_token}"}


# =============================================================================
# Mock Project and License Fixtures
# =============================================================================

@pytest.fixture
def mock_project(mock_user) -> Dict[str, Any]:
    """Generate a mock project for testing."""
    return {
        "id": secrets.token_hex(16),
        "user_id": mock_user["id"],
        "name": f"Test Project {secrets.token_hex(4)}",
        "description": "A test project for unit testing",
        "language": "python",
        "entry_file": "main.py",
        "output_name": "test_app",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_license(mock_project) -> Dict[str, Any]:
    """Generate a mock license for testing."""
    return {
        "id": secrets.token_hex(16),
        "project_id": mock_project["id"],
        "license_key": f"CV-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}",
        "status": "active",
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "max_machines": 3,
        "features": ["basic", "support"],
        "client_name": "Test Client",
        "client_email": "client@example.com",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# Database Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_db_connection():
    """Create a mock database connection for testing."""
    conn = AsyncMock()

    # Mock common database methods
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="INSERT 0 1")

    return conn


@pytest.fixture
def mock_db_pool(mock_db_connection):
    """Create a mock database pool for testing."""
    pool = MagicMock()
    pool.acquire = AsyncMock(return_value=mock_db_connection)
    pool.release = AsyncMock()
    return pool


# =============================================================================
# Temporary File Fixtures
# =============================================================================

@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create basic project structure
        (project_dir / "main.py").write_text("print('Hello, World!')")
        (project_dir / "config.json").write_text('{"entry_file": "main.py"}')

        yield project_dir


@pytest.fixture
def temp_nodejs_project_dir() -> Generator[Path, None, None]:
    """Create a temporary Node.js project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create basic Node.js project structure
        (project_dir / "index.js").write_text("console.log('Hello, World!');")
        (project_dir / "package.json").write_text('''{
            "name": "test-project",
            "version": "1.0.0",
            "main": "index.js"
        }''')

        yield project_dir


# =============================================================================
# Security Test Fixtures
# =============================================================================

@pytest.fixture
def path_traversal_payloads() -> list:
    """Common path traversal attack payloads for security testing."""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
        "..%00/etc/passwd",
        "..%252f..%252f..%252fetc/passwd",
        "/etc/passwd",
        "C:\\Windows\\System32\\config\\SAM",
        "file:///etc/passwd",
        "....\\....\\....\\windows\\system32",
        "%c0%ae%c0%ae/%c0%ae%c0%ae/etc/passwd",
        "..;/etc/passwd",
    ]


@pytest.fixture
def xss_payloads() -> list:
    """Common XSS attack payloads for security testing."""
    return [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "'\"><script>alert('XSS')</script>",
        "<body onload=alert('XSS')>",
    ]


@pytest.fixture
def sql_injection_payloads() -> list:
    """Common SQL injection payloads for security testing."""
    return [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1; DELETE FROM licenses WHERE 1=1; --",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "1' OR '1' = '1",
        "'; EXEC xp_cmdshell('whoami'); --",
    ]


@pytest.fixture
def code_injection_payloads() -> list:
    """Common code injection payloads for testing wrapper generators."""
    return [
        "TEST'''; import os; os.system('id'); '''",
        'TEST"; require("child_process").exec("id"); //',
        "TEST`; $(whoami); `",
        "TEST\\n__import__('os').system('id')\\n",
        "TEST'); console.log(process.env); //",
        "${require('child_process').execSync('id')}",
    ]


@pytest.fixture
def ssrf_payloads() -> list:
    """Common SSRF attack payloads for webhook URL testing."""
    return [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://0.0.0.0/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "http://192.168.1.1/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://localhost.localdomain/",
        "http://127.0.0.1:22/",
        "http://localhost:3306/",
        "file:///etc/passwd",
        "gopher://localhost:9000/",
    ]


# =============================================================================
# Stripe Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_stripe_event() -> Dict[str, Any]:
    """Generate a mock Stripe webhook event."""
    return {
        "id": f"evt_{secrets.token_hex(12)}",
        "object": "event",
        "type": "checkout.session.completed",
        "created": int(datetime.now(timezone.utc).timestamp()),
        "data": {
            "object": {
                "id": f"cs_{secrets.token_hex(12)}",
                "object": "checkout.session",
                "customer": f"cus_{secrets.token_hex(14)}",
                "customer_email": "customer@example.com",
                "metadata": {
                    "user_id": secrets.token_hex(16),
                    "tier": "pro",
                },
                "payment_status": "paid",
                "status": "complete",
            }
        },
        "livemode": False,
    }


@pytest.fixture
def mock_stripe_signature():
    """Generate a mock Stripe webhook signature for testing."""
    import hmac
    import hashlib
    import time

    def generate_signature(payload: str, secret: str) -> str:
        timestamp = int(time.time())
        payload_to_sign = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return f"t={timestamp},v1={signature}"

    return generate_signature


# =============================================================================
# Rate Limiting Test Fixtures
# =============================================================================

@pytest.fixture
def mock_redis():
    """Create a mock Redis client for rate limiting tests."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    return redis_mock


# =============================================================================
# Cleanup and Setup Hooks
# =============================================================================

@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables between tests."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_db: mark test as requiring database")
    config.addinivalue_line("markers", "requires_redis: mark test as requiring Redis")
