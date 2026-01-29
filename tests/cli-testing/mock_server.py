#!/usr/bin/env python3
"""
Mock Backend Server for CodeVault CLI Testing

This is a lightweight FastAPI server that mimics the real CodeVault API
but runs completely locally without database dependencies. Used for
automated CLI testing.

Features:
- In-memory user/project/license storage
- Pre-configured test accounts
- Simulates all API endpoints the CLI uses
- Supports license validation for build testing

Usage:
    python mock_server.py                    # Start on default port 8000
    python mock_server.py --port 8888        # Start on custom port
"""

import argparse
import hashlib
import secrets
import time
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# =============================================================================
# In-Memory Storage
# =============================================================================

# Pre-configured test accounts
TEST_ACCOUNTS = {
    "test@codevault.local": {
        "id": 1,
        "email": "test@codevault.local",
        "password_hash": hashlib.sha256("testpass123".encode()).hexdigest(),
        "name": "Test User",
        "plan": "free",
        "role": "user",
        "build_credits": 100,
        "created_at": "2024-01-01T00:00:00Z",
    },
    "pro@codevault.local": {
        "id": 2,
        "email": "pro@codevault.local",
        "password_hash": hashlib.sha256("propass123".encode()).hexdigest(),
        "name": "Pro User",
        "plan": "pro",
        "role": "user",
        "build_credits": 1000,
        "created_at": "2024-01-01T00:00:00Z",
    },
    "admin@codevault.local": {
        "id": 3,
        "email": "admin@codevault.local",
        "password_hash": hashlib.sha256("adminpass123".encode()).hexdigest(),
        "name": "Admin User",
        "plan": "enterprise",
        "role": "admin",
        "build_credits": 9999,
        "created_at": "2024-01-01T00:00:00Z",
    },
}

# Pre-configured test projects
TEST_PROJECTS = {
    1: {
        "id": 1,
        "user_id": 1,
        "name": "Hello World Test",
        "description": "Simple test project for CLI testing",
        "language": "python",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
    },
    2: {
        "id": 2,
        "user_id": 1,
        "name": "Node Test App",
        "description": "Node.js test project",
        "language": "nodejs",
        "status": "active",
        "created_at": "2024-01-02T00:00:00Z",
    },
    3: {
        "id": 3,
        "user_id": 2,
        "name": "Pro User Project",
        "description": "Project for pro user",
        "language": "python",
        "status": "active",
        "created_at": "2024-01-03T00:00:00Z",
    },
}

# Pre-configured test licenses
TEST_LICENSES = {
    "CV-TEST-0001-AAAA-BBBB": {
        "id": 1,
        "project_id": 1,
        "user_id": 1,
        "key": "CV-TEST-0001-AAAA-BBBB",
        "hwid": None,  # Not bound yet
        "status": "active",
        "max_activations": 3,
        "current_activations": 0,
        "expires_at": None,  # Lifetime
        "created_at": "2024-01-01T00:00:00Z",
    },
    "CV-TEST-0002-CCCC-DDDD": {
        "id": 2,
        "project_id": 1,
        "user_id": 1,
        "key": "CV-TEST-0002-CCCC-DDDD",
        "hwid": None,
        "status": "active",
        "max_activations": 1,
        "current_activations": 0,
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "created_at": "2024-01-01T00:00:00Z",
    },
    "CV-EXPIRED-0001-XXXX-YYYY": {
        "id": 3,
        "project_id": 1,
        "user_id": 1,
        "key": "CV-EXPIRED-0001-XXXX-YYYY",
        "hwid": None,
        "status": "expired",
        "max_activations": 1,
        "current_activations": 0,
        "expires_at": "2023-01-01T00:00:00Z",  # Already expired
        "created_at": "2023-01-01T00:00:00Z",
    },
}

# Active sessions (token -> user_id)
SESSIONS = {}

# Next IDs for auto-increment
NEXT_IDS = {"user": 4, "project": 4, "license": 4, "build": 1}

# Build records
BUILDS = {}

# =============================================================================
# Pydantic Models
# =============================================================================


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    language: str = "python"


class LicenseCreate(BaseModel):
    project_id: int
    expires_days: Optional[int] = None
    max_activations: int = 1


class LicenseValidateRequest(BaseModel):
    license_key: str
    hwid: str
    machine_name: Optional[str] = None
    timestamp: Optional[int] = None
    nonce: Optional[str] = None


class BuildCreate(BaseModel):
    project_id: int
    license_key: Optional[str] = None
    entry_file: Optional[str] = None


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="CodeVault Mock API",
    description="Mock server for CLI testing",
    version="1.0.0-mock",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Auth Dependency
# =============================================================================


def get_current_user(authorization: Optional[str] = Header(None)):
    """Verify token and return current user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    if token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = SESSIONS[token]
    for user in TEST_ACCOUNTS.values():
        if user["id"] == user_id:
            return user

    raise HTTPException(status_code=401, detail="User not found")


# =============================================================================
# Routes: Health & Status
# =============================================================================


@app.get("/health")
def health_check():
    return {"status": "healthy", "mode": "mock", "version": "1.0.0-mock"}


@app.get("/api/v1/status")
def api_status():
    return {
        "status": "ok",
        "mode": "mock",
        "users": len(TEST_ACCOUNTS),
        "projects": len(TEST_PROJECTS),
        "licenses": len(TEST_LICENSES),
    }


# =============================================================================
# Routes: Auth
# =============================================================================


@app.post("/api/v1/auth/login")
def login(req: LoginRequest):
    """Login and return JWT token."""
    email = req.email.lower()
    password_hash = hashlib.sha256(req.password.encode()).hexdigest()

    user = TEST_ACCOUNTS.get(email)
    if not user or user["password_hash"] != password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate token (simple for mock - real server uses JWT)
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user["id"]

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "plan": user["plan"],
            "role": user["role"],
        },
    }


@app.post("/api/v1/auth/register")
def register(req: RegisterRequest):
    """Register a new user."""
    global NEXT_IDS

    email = req.email.lower()
    if email in TEST_ACCOUNTS:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = NEXT_IDS["user"]
    NEXT_IDS["user"] += 1

    new_user = {
        "id": user_id,
        "email": email,
        "password_hash": hashlib.sha256(req.password.encode()).hexdigest(),
        "name": req.name,
        "plan": "free",
        "role": "user",
        "build_credits": 10,
        "created_at": datetime.now().isoformat(),
    }
    TEST_ACCOUNTS[email] = new_user

    return {"id": user_id, "email": email, "name": req.name, "plan": "free"}


@app.get("/api/v1/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "plan": user["plan"],
        "role": user["role"],
        "build_credits": user["build_credits"],
    }


# =============================================================================
# Routes: Projects
# =============================================================================


@app.get("/api/v1/projects")
def list_projects(user: dict = Depends(get_current_user)):
    """List user's projects."""
    user_projects = [p for p in TEST_PROJECTS.values() if p["user_id"] == user["id"]]
    return {"projects": user_projects, "total": len(user_projects)}


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: int, user: dict = Depends(get_current_user)):
    """Get a specific project."""
    project = TEST_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return project


@app.post("/api/v1/projects")
def create_project(req: ProjectCreate, user: dict = Depends(get_current_user)):
    """Create a new project."""
    global NEXT_IDS

    project_id = NEXT_IDS["project"]
    NEXT_IDS["project"] += 1

    new_project = {
        "id": project_id,
        "user_id": user["id"],
        "name": req.name,
        "description": req.description,
        "language": req.language,
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    TEST_PROJECTS[project_id] = new_project

    return new_project


# =============================================================================
# Routes: Licenses
# =============================================================================


@app.get("/api/v1/licenses")
def list_licenses_query(
    project_id: Optional[str] = None, user: dict = Depends(get_current_user)
):
    """List licenses (CLI uses this endpoint with query param)."""
    if project_id:
        # Filter by project_id if provided
        try:
            pid = int(project_id) if project_id.isdigit() else None
        except (ValueError, AttributeError):
            pid = None

        if pid:
            project = TEST_PROJECTS.get(pid)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            if project["user_id"] != user["id"] and user["role"] != "admin":
                raise HTTPException(status_code=403, detail="Access denied")

            project_licenses = [
                {
                    "license_key": l["key"],
                    "status": l["status"],
                    "client_name": l.get("client_name"),
                    "expires_at": l["expires_at"],
                    **l,
                }
                for l in TEST_LICENSES.values()
                if l["project_id"] == pid
            ]
            return project_licenses

    # Return all user licenses
    user_licenses = [
        {
            "license_key": l["key"],
            "status": l["status"],
            "client_name": l.get("client_name"),
            "expires_at": l["expires_at"],
            **l,
        }
        for l in TEST_LICENSES.values()
        if l["user_id"] == user["id"]
    ]
    return user_licenses


@app.get("/api/v1/projects/{project_id}/licenses")
def list_licenses(project_id: int, user: dict = Depends(get_current_user)):
    """List licenses for a project."""
    project = TEST_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    project_licenses = [
        l for l in TEST_LICENSES.values() if l["project_id"] == project_id
    ]
    return {"licenses": project_licenses, "total": len(project_licenses)}


@app.post("/api/v1/licenses")
def create_license(req: LicenseCreate, user: dict = Depends(get_current_user)):
    """Create a new license."""
    global NEXT_IDS

    project = TEST_PROJECTS.get(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    license_id = NEXT_IDS["license"]
    NEXT_IDS["license"] += 1

    key = f"CV-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"

    expires_at = None
    if req.expires_days:
        expires_at = (datetime.now() + timedelta(days=req.expires_days)).isoformat()

    new_license = {
        "id": license_id,
        "project_id": req.project_id,
        "user_id": user["id"],
        "key": key,
        "hwid": None,
        "status": "active",
        "max_activations": req.max_activations,
        "current_activations": 0,
        "expires_at": expires_at,
        "created_at": datetime.now().isoformat(),
    }
    TEST_LICENSES[key] = new_license

    return new_license


@app.post("/api/v1/licenses/validate")
def validate_license(req: LicenseValidateRequest):
    """Validate a license key (public endpoint - no auth required)."""
    license_data = TEST_LICENSES.get(req.license_key)

    if not license_data:
        return {
            "status": "invalid",
            "message": "License key not found",
            "timestamp": int(time.time()),
            "server_time": int(time.time()),
        }

    # Check if expired
    if license_data["status"] == "expired":
        return {
            "status": "invalid",
            "message": "License has expired",
            "timestamp": int(time.time()),
            "server_time": int(time.time()),
        }

    if license_data["expires_at"]:
        expires = datetime.fromisoformat(
            license_data["expires_at"].replace("Z", "+00:00")
        )
        if datetime.now(expires.tzinfo) > expires:
            license_data["status"] = "expired"
            return {
                "status": "invalid",
                "message": "License has expired",
                "timestamp": int(time.time()),
                "server_time": int(time.time()),
            }

    # Check HWID binding
    if license_data["hwid"] and license_data["hwid"] != req.hwid:
        return {
            "status": "invalid",
            "message": "License bound to different machine",
            "timestamp": int(time.time()),
            "server_time": int(time.time()),
        }

    # Check activation count
    if not license_data["hwid"]:
        if license_data["current_activations"] >= license_data["max_activations"]:
            return {
                "status": "invalid",
                "message": "Maximum activations reached",
                "timestamp": int(time.time()),
                "server_time": int(time.time()),
            }
        # Bind to this HWID
        license_data["hwid"] = req.hwid
        license_data["current_activations"] += 1

    return {
        "status": "valid",
        "message": "License is valid",
        "timestamp": int(time.time()),
        "server_time": int(time.time()),
        "license_id": license_data["id"],
        "project_id": license_data["project_id"],
        "expires_at": license_data["expires_at"],
    }


# =============================================================================
# Routes: Builds (for completeness)
# =============================================================================


@app.post("/api/v1/builds")
def create_build(req: BuildCreate, user: dict = Depends(get_current_user)):
    """Create a build record (mock - doesn't actually build)."""
    global NEXT_IDS

    project = TEST_PROJECTS.get(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    build_id = NEXT_IDS["build"]
    NEXT_IDS["build"] += 1

    build = {
        "id": build_id,
        "project_id": req.project_id,
        "user_id": user["id"],
        "status": "completed",
        "license_key": req.license_key,
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
    }
    BUILDS[build_id] = build

    return build


@app.get("/api/v1/builds/{build_id}")
def get_build(build_id: int, user: dict = Depends(get_current_user)):
    """Get build status."""
    build = BUILDS.get(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if build["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return build


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="CodeVault Mock API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    print(f"""
============================================================
         CodeVault Mock API Server (Testing Mode)
============================================================
  Server: http://{args.host}:{args.port}
  Mode:   MOCK (no database required)
------------------------------------------------------------
  Test Accounts:
    - test@codevault.local / testpass123   (free)
    - pro@codevault.local  / propass123    (pro)
    - admin@codevault.local / adminpass123 (admin)
------------------------------------------------------------
  Test License Keys:
    - CV-TEST-0001-AAAA-BBBB  (active, lifetime)
    - CV-TEST-0002-CCCC-DDDD  (active, 30 days)
    - CV-EXPIRED-0001-XXXX-YYYY (expired)
============================================================
    """)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
