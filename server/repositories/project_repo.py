"""
Project Repository - Data access layer for project-related operations.
"""

import json
import secrets
from typing import Optional, List, Dict, Any
from asyncpg import Connection

class ProjectRepository:
    """Handles all database operations for projects and project files."""

    @staticmethod
    async def list_user_projects(conn: Connection, user_id: str) -> List[Dict[str, Any]]:
        """List all projects belonging to a user."""
        return await conn.fetch(
            """
            SELECT p.id, p.name, p.description, p.created_at, p.language,
                   (SELECT COUNT(*) FROM licenses l WHERE l.project_id = p.id) as license_count
            FROM projects p WHERE p.user_id = $1 ORDER BY p.created_at DESC
            """,
            user_id,
        )

    @staticmethod
    async def get_project_by_id(conn: Connection, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID and user ID."""
        return await conn.fetchrow(
            "SELECT id, name, settings, compiler_options, language, signing_secret, signing_public_key, brand_name, brand_url, brand_primary_color, brand_secondary_color, brand_logo_url FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user_id,
        )

    @staticmethod
    async def create_project(conn: Connection, user_id: str, data: Dict[str, Any]) -> str:
        """Create a new project and return its ID."""
        project_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO projects (id, user_id, name, description, language, compiler_options, signing_secret, signing_private_key, signing_public_key) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            project_id,
            user_id,
            data['name'],
            data['description'],
            data['language'],
            json.dumps(data['compiler_options']),
            data['signing_secret'],
            data['signing_private_key'],
            data['signing_public_key'],
        )
        return project_id

    @staticmethod
    async def delete_project(conn: Connection, project_id: str) -> None:
        """Delete a project."""
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)

    @staticmethod
    async def update_project_config(conn: Connection, project_id: str, settings: Dict[str, Any], compiler_options: Dict[str, Any]) -> None:
        """Update project configuration."""
        await conn.execute(
            """
            UPDATE projects 
            SET settings = $1, compiler_options = $2, updated_at = NOW() 
            WHERE id = $3
            """,
            json.dumps(settings),
            json.dumps(compiler_options),
            project_id,
        )

    @staticmethod
    async def list_project_files(conn: Connection, project_id: str) -> List[Dict[str, Any]]:
        """List all files belonging to a project."""
        return await conn.fetch(
            """
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
            """,
            project_id,
        )

    @staticmethod
    async def create_project_file(conn: Connection, data: Dict[str, Any]) -> str:
        """Add a file to a project."""
        file_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO project_files (id, project_id, filename, original_filename, file_path, file_hash, file_size, is_cloud)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            file_id,
            data['project_id'],
            data['filename'],
            data['original_filename'],
            data['file_path'],
            data['file_hash'],
            data['file_size'],
            data['is_cloud'],
        )
        return file_id

    @staticmethod
    async def get_project_file(conn: Connection, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific project file with owner check."""
        return await conn.fetchrow(
            """
            SELECT pf.id, pf.file_path, pf.is_cloud FROM project_files pf
            JOIN projects p ON pf.project_id = p.id
            WHERE pf.id = $1 AND p.user_id = $2
            """,
            file_id,
            user_id,
        )

    @staticmethod
    async def get_project_files(conn: Connection, project_id: str) -> List[Dict[str, Any]]:
        """Get all files for a project."""
        return await conn.fetch(
            """
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
            """,
            project_id,
        )

    @staticmethod
    async def create_upload_token(conn: Connection, project_id: str, data: Dict[str, Any]) -> None:
        """Create or update an upload token."""
        await conn.execute(
            """
            INSERT INTO project_upload_tokens (project_id, token, r2_key, filename, file_size, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (project_id) DO UPDATE SET
                token = EXCLUDED.token,
                r2_key = EXCLUDED.r2_key,
                filename = EXCLUDED.filename,
                file_size = EXCLUDED.file_size,
                created_at = EXCLUDED.created_at
            """,
            project_id,
            data['token'],
            data['r2_key'],
            data['filename'],
            data['file_size'],
        )

    @staticmethod
    async def get_upload_token(conn: Connection, project_id: str, token: str) -> Optional[Dict[str, Any]]:
        """Get an upload token record."""
        return await conn.fetchrow(
            "SELECT r2_key, filename, file_size FROM project_upload_tokens WHERE project_id = $1 AND token = $2",
            project_id,
            token,
        )

    @staticmethod
    async def update_project_settings(conn: Connection, project_id: str, settings: Dict[str, Any]) -> None:
        """Update only the project settings (JSON)."""
        await conn.execute(
            "UPDATE projects SET settings = $1, updated_at = NOW() WHERE id = $2",
            json.dumps(settings),
            project_id,
        )

    @staticmethod
    async def register_binary_hash(conn: Connection, project_id: str, data: Dict[str, Any]) -> None:
        """Register a binary hash."""
        hash_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO binary_hashes (id, project_id, binary_hash, binary_size, platform, build_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            hash_id,
            project_id,
            data['binary_hash'],
            data.get('binary_size'),
            data.get('platform'),
            data.get('build_id'),
        )

    @staticmethod
    async def get_branding(conn: Connection, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get project branding settings."""
        return await conn.fetchrow(
            """SELECT id, brand_name, brand_url, brand_primary_color, brand_secondary_color, brand_logo_url
               FROM projects WHERE id = $1 AND user_id = $2""",
            project_id,
            user_id,
        )

    @staticmethod
    async def update_branding(conn: Connection, project_id: str, data: Dict[str, Any]) -> None:
        """Update project branding settings."""
        await conn.execute(
            """UPDATE projects SET 
               brand_name = $1,
               brand_url = $2,
               brand_primary_color = $3,
               brand_secondary_color = $4,
               brand_logo_url = $5
               WHERE id = $6""",
            data['brand_name'],
            data['brand_url'],
            data['brand_primary_color'],
            data['brand_secondary_color'],
            data['brand_logo_url'],
            project_id,
        )
