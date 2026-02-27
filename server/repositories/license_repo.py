"""
License Repository - Data access layer for license-related operations.
"""

import json
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from asyncpg import Connection

class LicenseRepository:
    """Handles all database operations for licenses, bindings, and sessions."""

    @staticmethod
    async def get_license_with_project(conn: Connection, license_key: str) -> Optional[Dict[str, Any]]:
        """Get license and associated project info with a row lock."""
        return await conn.fetchrow(
            """SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features, 
                      l.license_mode, l.max_concurrent,
                      p.id as project_id, p.signing_secret, p.signing_private_key, p.user_id 
               FROM licenses l 
               JOIN projects p ON l.project_id = p.id
               WHERE l.license_key = $1 FOR UPDATE""",
            license_key,
        )

    @staticmethod
    async def verify_binary_hash(conn: Connection, project_id: str, binary_hash: str) -> bool:
        """Verify if a binary hash is registered for a project."""
        match = await conn.fetchval(
            "SELECT 1 FROM binary_hashes WHERE project_id = $1 AND binary_hash = $2",
            project_id,
            binary_hash,
        )
        return bool(match)

    @staticmethod
    async def get_hardware_binding(conn: Connection, license_id: str, hwid: str) -> Optional[Dict[str, Any]]:
        """Get a specific hardware binding."""
        return await conn.fetchrow(
            "SELECT id, is_active FROM hardware_bindings WHERE license_id = $1 AND hwid = $2",
            license_id,
            hwid,
        )

    @staticmethod
    async def count_active_bindings(conn: Connection, license_id: str) -> int:
        """Count active hardware bindings for a license."""
        return await conn.fetchval(
            "SELECT COUNT(*) FROM hardware_bindings WHERE license_id = $1 AND is_active = TRUE",
            license_id,
        )

    @staticmethod
    async def update_hardware_binding(
        conn: Connection, 
        binding_id: str, 
        machine_name: Optional[str], 
        ip_address: str
    ) -> None:
        """Update an existing hardware binding."""
        await conn.execute(
            """UPDATE hardware_bindings 
               SET last_seen_at = NOW(), machine_name = $1, ip_address = $2, is_active = TRUE
               WHERE id = $3""",
            machine_name,
            ip_address,
            binding_id,
        )

    @staticmethod
    async def create_hardware_binding(
        conn: Connection, 
        license_id: str, 
        hwid: str, 
        machine_name: Optional[str], 
        ip_address: str
    ) -> None:
        """Create a new hardware binding."""
        await conn.execute(
            """INSERT INTO hardware_bindings (id, license_id, hwid, machine_name, ip_address, is_active)
               VALUES ($1, $2, $3, $4, $5, TRUE)""",
            secrets.token_hex(16),
            license_id,
            hwid,
            machine_name,
            ip_address,
        )

    @staticmethod
    async def update_last_validated(conn: Connection, license_id: str) -> None:
        """Update the last validated timestamp for a license."""
        await conn.execute(
            "UPDATE licenses SET last_validated_at = NOW() WHERE id = $1",
            license_id,
        )

    @staticmethod
    async def get_active_session(conn: Connection, license_id: str, hwid: str) -> Optional[Dict[str, Any]]:
        """Get an active floating session."""
        return await conn.fetchrow(
            """SELECT session_token FROM license_sessions 
               WHERE license_id = $1 AND hwid = $2 AND is_active = TRUE AND expires_at > NOW()""",
            license_id,
            hwid,
        )

    @staticmethod
    async def update_session_ttl(conn: Connection, license_id: str, hwid: str) -> None:
        """Update the TTL for an active session."""
        await conn.execute(
            """UPDATE license_sessions 
               SET expires_at = NOW() + INTERVAL '360 seconds', last_active_at = NOW() 
               WHERE license_id = $1 AND hwid = $2 AND is_active = TRUE""",
            license_id,
            hwid,
        )

    @staticmethod
    async def count_active_sessions(conn: Connection, license_id: str) -> int:
        """Count active floating sessions for a license."""
        return await conn.fetchval(
            "SELECT COUNT(*) FROM license_sessions WHERE license_id = $1 AND is_active = TRUE AND expires_at > NOW()",
            license_id,
        )

    @staticmethod
    async def create_session(
        conn: Connection, 
        license_id: str, 
        hwid: str, 
        session_token: str, 
        ip_address: str
    ) -> None:
        """Create a new floating session."""
        await conn.execute(
            """INSERT INTO license_sessions (id, license_id, hwid, session_token, ip_address, expires_at)
               VALUES ($1, $2, $3, $4, $5, NOW() + INTERVAL '360 seconds')""",
            secrets.token_hex(16),
            license_id,
            hwid,
            session_token,
            ip_address,
        )

    @staticmethod
    async def get_license_variables(conn: Connection, license_id: str, include_secrets: bool = False) -> Dict[str, Any]:
        """Get license variables as a key-value dictionary."""
        query = """SELECT json_object_agg(key, value) as vars 
                   FROM license_variables 
                   WHERE license_id = $1"""
        if not include_secrets:
            query += " AND is_secret = FALSE"
        
        row = await conn.fetchrow(query, license_id)
        return row["vars"] if row and row["vars"] else {}

    @staticmethod
    async def list_user_licenses(conn: Connection, user_id: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all licenses belonging to a user, optionally filtered by project."""
        query = """
            SELECT l.id, l.license_key, l.status, l.expires_at, l.max_machines, l.features,
                   l.client_name, l.client_email, l.created_at, l.project_id, p.name as project_name,
                   (SELECT COUNT(*) FROM hardware_bindings hb WHERE hb.license_id = l.id AND hb.is_active = TRUE) as active_machines
            FROM licenses l JOIN projects p ON l.project_id = p.id WHERE p.user_id = $1
        """
        params = [user_id]
        if project_id:
            query += " AND l.project_id = $2"
            params.append(project_id)
        query += " ORDER BY l.created_at DESC"

        return await conn.fetch(query, *params)

    @staticmethod
    async def count_licenses_for_project(conn: Connection, project_id: str) -> int:
        """Count all licenses for a project."""
        return await conn.fetchval(
            "SELECT COUNT(*) FROM licenses WHERE project_id = $1", project_id
        )

    @staticmethod
    async def create_license(conn: Connection, data: Dict[str, Any]) -> str:
        """Create a new license and return its ID."""
        license_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO licenses (id, project_id, license_key, expires_at, max_machines, features, client_name, client_email, notes, license_type, license_mode, max_concurrent)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            license_id,
            data['project_id'],
            data['license_key'],
            data['expires_at'],
            data['max_machines'],
            json.dumps(data['features']),
            data['client_name'],
            data['client_email'],
            data['notes'],
            data['license_type'],
            data['license_mode'],
            data['max_concurrent'],
        )
        return license_id

    @staticmethod
    async def revoke_license(conn: Connection, license_id: str, user_id: str) -> bool:
        """Revoke a license if owned by user."""
        result = await conn.execute(
            """
            UPDATE licenses SET status = 'revoked', updated_at = NOW()
            WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)
            """,
            license_id,
            user_id,
        )
        return result != "UPDATE 0"

    @staticmethod
    async def delete_license(conn: Connection, license_id: str, user_id: str) -> bool:
        """Delete a license if owned by user."""
        result = await conn.execute(
            """
            DELETE FROM licenses WHERE id = $1 AND project_id IN (SELECT id FROM projects WHERE user_id = $2)
            """,
            license_id,
            user_id,
        )
        return result != "DELETE 0"

    @staticmethod
    async def get_binding_for_heartbeat(conn: Connection, license_key: str, hwid: str) -> Optional[Dict[str, Any]]:
        """Get binding and project heartbeat settings."""
        return await conn.fetchrow(
            """SELECT hb.id, hb.is_active, p.heartbeat_interval_seconds 
               FROM hardware_bindings hb
               JOIN licenses l ON hb.license_id = l.id
               JOIN projects p ON l.project_id = p.id
               WHERE l.license_key = $1 AND hb.hwid = $2""",
            license_key,
            hwid,
        )

    @staticmethod
    async def update_heartbeat(conn: Connection, binding_id: str) -> None:
        """Increment heartbeat count and update timestamp."""
        await conn.execute(
            """UPDATE hardware_bindings 
               SET last_heartbeat_at = NOW(), 
                   heartbeat_count = heartbeat_count + 1
               WHERE id = $1""",
            binding_id,
        )

    @staticmethod
    async def release_session(conn: Connection, license_key: str, hwid: str, session_token: str) -> bool:
        """Release a floating session."""
        result = await conn.execute(
            """UPDATE license_sessions 
               SET is_active = FALSE, released_at = NOW()
               WHERE license_id = (SELECT id FROM licenses WHERE license_key = $1)
               AND hwid = $2 AND session_token = $3 AND is_active = TRUE""",
            license_key,
            hwid,
            session_token,
        )
        return result != "UPDATE 0"

    @staticmethod
    async def get_reset_history(conn: Connection, license_id: str) -> List[Dict[str, Any]]:
        """Get HWID reset logs."""
        return await conn.fetch(
            """
            SELECT id, bindings_removed, reason, created_at
            FROM hwid_reset_logs
            WHERE license_id = $1
            ORDER BY created_at DESC
            LIMIT 50
            """,
            license_id,
        )

    @staticmethod
    async def get_last_reset(conn: Connection, license_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent HWID reset."""
        return await conn.fetchrow(
            "SELECT created_at FROM hwid_reset_logs WHERE license_id = $1 ORDER BY created_at DESC LIMIT 1",
            license_id,
        )

    @staticmethod
    async def count_total_resets(conn: Connection, license_id: str) -> int:
        """Get total reset count for a license."""
        return await conn.fetchval(
            "SELECT COUNT(*) FROM hwid_reset_logs WHERE license_id = $1", license_id
        )

    @staticmethod
    async def get_license_bindings(conn: Connection, license_id: str) -> List[Dict[str, Any]]:
        """Get all bindings for a license."""
        return await conn.fetch(
            """
            SELECT id, hwid, machine_name, ip_address, first_seen_at, last_seen_at, is_active
            FROM hardware_bindings WHERE license_id = $1 ORDER BY last_seen_at DESC
            """,
            license_id,
        )

    @staticmethod
    async def delete_binding(conn: Connection, binding_id: str, license_id: str) -> None:
        """Delete a machine binding."""
        await conn.execute(
            "DELETE FROM hardware_bindings WHERE id = $1 AND license_id = $2",
            binding_id,
            license_id,
        )

    @staticmethod
    async def get_license_variables_raw(conn: Connection, license_id: str) -> List[Dict[str, Any]]:
        """Get raw variable records for a license."""
        return await conn.fetch(
            """
            SELECT id, key, value, is_secret, created_at, updated_at
            FROM license_variables
            WHERE license_id = $1
            ORDER BY key ASC
            """,
            license_id,
        )

    @staticmethod
    async def create_license_variable(conn: Connection, data: Dict[str, Any]) -> str:
        """Create a new license variable."""
        variable_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO license_variables (id, license_id, key, value, is_secret)
            VALUES ($1, $2, $3, $4, $5)
            """,
            variable_id,
            data['license_id'],
            data['key'],
            data['value'],
            data['is_secret'],
        )
        return variable_id

    @staticmethod
    async def get_variable_by_id(conn: Connection, variable_id: str) -> Optional[Dict[str, Any]]:
        """Get a variable by ID."""
        return await conn.fetchrow(
            "SELECT id, key, value, is_secret, created_at, updated_at FROM license_variables WHERE id = $1",
            variable_id,
        )

    @staticmethod
    async def update_license_variable(conn: Connection, variable_id: str, value: Any, is_secret: Optional[bool]) -> None:
        """Update a variable's value and/or visibility."""
        if is_secret is not None:
            await conn.execute(
                "UPDATE license_variables SET value = $1, is_secret = $2, updated_at = NOW() WHERE id = $3",
                value, is_secret, variable_id
            )
        else:
            await conn.execute(
                "UPDATE license_variables SET value = $1, updated_at = NOW() WHERE id = $2",
                value, variable_id
            )

    @staticmethod
    async def delete_license_variable(conn: Connection, variable_id: str) -> None:
        """Delete a variable."""
        await conn.execute("DELETE FROM license_variables WHERE id = $1", variable_id)

    @staticmethod
    async def get_latest_completed_build(conn: Connection, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest successful build for a project."""
        return await conn.fetchrow(
            """SELECT id, created_at, build_type FROM cloud_builds 
               WHERE project_id = $1 AND status = 'completed' 
               ORDER BY created_at DESC LIMIT 1""",
            project_id,
        )

    @staticmethod
    async def get_active_kill_switch(conn: Connection, project_id: str) -> Optional[Dict[str, Any]]:
        """Get active kill switch policy."""
        return await conn.fetchrow(
            """SELECT enabled, reason, killed_versions, redirect_url 
               FROM kill_switches 
               WHERE project_id = $1 AND enabled = TRUE""",
            project_id,
        )

    @staticmethod
    async def upsert_kill_switch(conn: Connection, project_id: str, data: Dict[str, Any]) -> None:
        """Create or update a kill switch."""
        await conn.execute(
            """INSERT INTO kill_switches (id, project_id, enabled, reason, killed_versions, redirect_url, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, NOW())
               ON CONFLICT (project_id) DO UPDATE SET
               enabled = $3, reason = $4, killed_versions = $5, redirect_url = $6
            """,
            secrets.token_hex(16),
            project_id,
            data['enabled'],
            data['reason'],
            json.dumps(data['killed_versions']),
            data['redirect_url'],
        )

