import pytest
import time
import secrets
import json
import sys
import os
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure server is in path (like conftest does)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from main import app
from utils import generate_nonce
import database 

# --- Mock Database ---
class MockDB:
    def __init__(self):
        self.projects = {}
        self.licenses = {}
        self.bindings = {}
        self.logs = {}
    
    async def fetchrow(self, query, *args):
        # Mock logic based on query content
        q = query.strip().lower()
        
        # Get Project
        if "select id, name from projects" in q:
            pid = args[0]
            if pid in self.projects:
                return {"id": self.projects[pid]["id"], "name": self.projects[pid]["name"]}
            return None
            
        # Get User Tier Limits
        if "select plan_tier from subscriptions" in q:
            return None # Default to free
        if "select plan from users" in q:
            return {"plan": "business"} # Admin is business
            
        # License queries joined with projects
        if "from licenses l" in q and "join projects p" in q:
            if "where l.license_key" in q:
                key = args[0]
                for l in self.licenses.values():
                    if l["license_key"] == key:
                        project = self.projects.get(l["project_id"])
                        return {
                            "id": l["id"],
                            "license_key": l["license_key"],
                            "status": l["status"],
                            "expires_at": l["expires_at"],
                            "max_machines": l["max_machines"],
                            "features": l["features"],
                            "license_mode": l.get("license_mode", "static"),
                            "max_concurrent": l.get("max_concurrent", 1),
                            "project_id": l["project_id"],
                            "signing_secret": project.get("signing_secret") if project else None,
                            "signing_private_key": project.get("signing_private_key") if project else None,
                            "user_id": project.get("user_id") if project else "mock_user",
                        }
                return None
            if "where l.id" in q:
                lid = args[0]
                if lid in self.licenses:
                    l = self.licenses[lid]
                    p = self.projects[l["project_id"]]
                    return {**l, "project_name": p["name"], "project_id": p["id"]}
                return None
            
        # Check HWID Binding
        if "select id, is_active from hardware_bindings" in q:
            lid, hwid = args[0], args[1]
            for b_id, b in self.bindings.items():
                if b["license_id"] == lid and b["hwid"] == hwid:
                    return b
            return None
            
        # User auth check (get_current_user)
        if "select id, email, name, plan, role, api_key from users" in q:
            return {
                "id": args[0], "email": "admin@example.com", "name": "Admin",
                "plan": "business", "role": "admin", "api_key": "mock_key"
            }

        return None

    async def fetchval(self, query, *args):
        q = query.strip().lower()
        
        # Count projects
        if "select count(*) from projects" in q:
            return len(self.projects)
            
        # Count licenses
        if "select count(*) from licenses" in q:
            return len(self.licenses)
            
        # Count bindings
        if "select count(*) from hardware_bindings" in q:
            lid = args[0]
            count = 0
            for b in self.bindings.values():
                if b["license_id"] == lid and b.get("is_active", True):
                    count += 1
            return count
            
        return 0

    async def execute(self, query, *args):
        q = query.strip().lower()
        
        # Insert Project
        if "insert into projects" in q:
            self.projects[args[0]] = {
                "id": args[0], "user_id": args[1], "name": args[2], 
                "description": args[3], "language": args[4],
                "signing_secret": "test_signing_secret"
            }
            return
            
        # Insert License
        if "insert into licenses" in q:
            self.licenses[args[0]] = {
                "id": args[0], "project_id": args[1], "license_key": args[2],
                "status": "active", "expires_at": args[3], "max_machines": args[4],
                "features": args[5],
                "client_name": args[6],
                "client_email": args[7],
                "notes": args[8]
            }
            return

        # Insert Binding
        if "insert into hardware_bindings" in q:
            self.bindings[args[0]] = {
                "id": args[0], "license_id": args[1], "hwid": args[2], 
                "machine_name": args[3], "ip_address": args[4], "is_active": True
            }
            return

        # Delete Bindings (Reset)
        if "delete from hardware_bindings" in q:
            lid = args[0]
            keys_to_del = [k for k,v in self.bindings.items() if v["license_id"] == lid]
            for k in keys_to_del:
                del self.bindings[k]
            return

# --- Fixtures ---

@pytest.fixture
def mock_db():
    db = MockDB()
    connection = MagicMock()
    connection.fetchrow = db.fetchrow
    connection.fetchval = db.fetchval
    connection.execute = db.execute
    connection.fetch = AsyncMock(return_value=[])
    
    # Patch database.db_pool (not server.database.db_pool)
    mock_pool = MagicMock()
    mock_pool.acquire = AsyncMock(return_value=connection)
    mock_pool.release = AsyncMock()
    
    original_pool = database.db_pool
    database.db_pool = mock_pool
    
    yield db
    
    database.db_pool = original_pool

# --- Test ---

@pytest.mark.asyncio
async def test_hwid_locking_flow(mock_db, admin_auth_token: str):
    """
    Test the complete HWID locking lifecycle:
    Bind -> Verify -> Block (Mismatch) -> Reset -> Rebind
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # 1. Create Project
        resp = await client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Core Test"},
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        if resp.status_code != 200:
            print(f"DEBUG ERROR Create Project: {resp.text}")
        assert resp.status_code == 200
        project_id = resp.json()["id"]

        # 2. Create License
        resp = await client.post(
            "/api/v1/licenses",
            json={
                "project_id": project_id,
                "max_machines": 1,
                "client_name": "Test Client"
            },
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        if resp.status_code != 200:
            print(f"DEBUG ERROR Create License: {resp.text}")
        assert resp.status_code == 200
        license_key = resp.json()["license_key"]
        license_id = resp.json()["id"]

        hwid_a = "hwid_machine_a"
        hwid_b = "hwid_machine_b"
        
        # 3. First Validation (HWID A) - Should Succeed and Bind
        resp = await client.post(
            "/api/v1/license/validate",
            json={
                "license_key": license_key,
                "hwid": hwid_a,
                "nonce": generate_nonce(),
                "timestamp": int(time.time()),
                "machine_name": "Machine A"
            }
        )
        if resp.status_code != 200:
            print(f"DEBUG ERROR Validate 1: {resp.text}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "valid"

        # 4. Second Validation (HWID A) - Should Succeed (Existing Binding)
        resp = await client.post(
            "/api/v1/license/validate",
            json={
                "license_key": license_key,
                "hwid": hwid_a,
                "nonce": generate_nonce(),
                "timestamp": int(time.time()),
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "valid"

        # 5. Third Validation (HWID B) - Should Fail (Limit Reached)
        resp = await client.post(
            "/api/v1/license/validate",
            json={
                "license_key": license_key,
                "hwid": hwid_b,
                "nonce": generate_nonce(),
                "timestamp": int(time.time()),
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "hwid_mismatch"

        # 6. Reset HWID
        resp = await client.post(
            f"/api/v1/licenses/{license_id}/reset-hwid",
            json={"reason": "User requested reset"},
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        assert resp.status_code == 200

        # 7. Fourth Validation (HWID B) - Should Succeed (Rebind)
        resp = await client.post(
            "/api/v1/license/validate",
            json={
                "license_key": license_key,
                "hwid": hwid_b,
                "nonce": generate_nonce(),
                "timestamp": int(time.time()),
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "valid"
