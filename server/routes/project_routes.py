import json
import secrets
import shutil
import zipfile
import logging

from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile


from database import get_db, release_db
from utils import get_current_user, utc_now, safe_join, validate_project_id, SecurityError, get_user_tier_limits, get_user_tier, sanitize_filename
from storage_service import storage_service, upload_project_file, LOCAL_UPLOAD_DIR, validate_file_size, MAX_ZIP_SIZE
from models import ProjectCreateRequest, ProjectConfigRequest
from routes.project_helpers import scan_project_structure, scan_nodejs_project_structure
from middleware.rate_limiter import RateLimitDependency
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Local upload directory
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

@router.get("")
async def list_projects(user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        rows = await conn.fetch(
            """
            SELECT p.id, p.name, p.description, p.created_at, p.language,
                   (SELECT COUNT(*) FROM licenses l WHERE l.project_id = p.id) as license_count
            FROM projects p WHERE p.user_id = $1 ORDER BY p.created_at DESC
        """,
            user["id"],
        )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "language": r.get("language", "python"),
                "created_at": r["created_at"].isoformat(),
                "license_count": r["license_count"],
                "local_path": str(LOCAL_UPLOAD_DIR / r["id"]),
            }
            for r in rows
        ]
    finally:
        await release_db(conn)

@router.post("")
async def create_project(data: ProjectCreateRequest, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        limits = await get_user_tier_limits(user["id"], conn)
        max_projects = limits.get("max_projects", 1)

        if max_projects != -1:
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM projects WHERE user_id = $1", user["id"]
            )
            if current_count >= max_projects:
                raise HTTPException(
                    status_code=403,
                    detail=f"Project limit reached ({max_projects}). Upgrade your plan.",
                )

        project_id = secrets.token_hex(16)
        await conn.execute(
            """
            INSERT INTO projects (id, user_id, name, description, language, compiler_options) 
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            project_id,
            user["id"],
            data.name,
            data.description,
            data.language,
            json.dumps(data.compiler_options),
        )
        return {
            "id": project_id,
            "name": data.name,
            "description": data.description,
            "language": data.language,
            "compiler_options": data.compiler_options,
            "created_at": utc_now().isoformat(),
            "license_count": 0,
            "local_path": str(LOCAL_UPLOAD_DIR / project_id),
        }
    finally:
        await release_db(conn)

@router.delete("/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await storage_service.delete_project_files(project_id)
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)

@router.get("/{project_id}/config")
async def get_project_config(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, name, settings, compiler_options, language FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        settings = project["settings"] or {}
        if isinstance(settings, str):
            settings = json.loads(settings) if settings else {}

        compiler_opts = project.get("compiler_options") or {}
        if isinstance(compiler_opts, str):
            compiler_opts = json.loads(compiler_opts)

        language = project.get("language", "python")

        files = await conn.fetch(
            """
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
        """,
            project_id,
        )

        import os
        # Get server URL for license validation API
        server_url = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000")
        api_url = f"{server_url}/api/v1/license/validate"

        # Get selected license if stored in settings
        selected_license_id = settings.get("selected_license_id")

        # Get user tier info for white-label branding
        tier_info = await get_user_tier(user["id"], conn)

        return {
            "project_name": project["name"],
            "entry_file": settings.get("entry_file"),
            "output_name": settings.get("output_name"),
            "include_modules": settings.get("include_modules", []),
            "exclude_modules": settings.get("exclude_modules", []),
            "nuitka_options": settings.get("nuitka_options", {}),
            "pkg_options": settings.get("pkg_options", {}),
            "compiler_options": compiler_opts,
            "language": language,
            "api_url": api_url,
            "server_url": server_url,
            "selected_license_id": selected_license_id,
            # Build options
            "skip_obfuscation": settings.get("skip_obfuscation", True),
            "enable_lease": settings.get("enable_lease", False),
            # White-label branding tier info
            "tier": tier_info["tier"],
            "is_pro": tier_info["is_pro"],
            "can_remove_branding": tier_info["can_remove_branding"],
            "can_custom_branding": tier_info["can_custom_branding"],
            "files": [
                {
                    "id": f["id"],
                    "filename": f["filename"],
                    "original_filename": f["original_filename"],
                    "file_size": f["file_size"],
                    "file_hash": f["file_hash"],
                    "created_at": f["created_at"].isoformat(),
                }
                for f in files
            ],
        }
    finally:
        await release_db(conn)

@router.put("/{project_id}/config")
async def update_project_config(
    project_id: str, data: ProjectConfigRequest, user: dict = Depends(get_current_user)
):
    # Debug: Log what we're receiving
    logger.debug(
        "Saving config for project %s: skip_obfuscation=%s, enable_lease=%s, compiler_options=%s",
        project_id, data.skip_obfuscation, data.enable_lease, data.compiler_options
    )

    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id, settings FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        current_settings = (
            json.loads(project["settings"])
            if isinstance(project["settings"], str)
            else (project["settings"] or {})
        )

        current_settings.update(
            {
                "entry_file": data.entry_file,
                "output_name": data.output_name,
                "include_modules": data.include_modules,
                "exclude_modules": data.exclude_modules,
                "nuitka_options": data.nuitka_options,
                # Build options
                "skip_obfuscation": data.skip_obfuscation,
                "enable_lease": data.enable_lease,
            }
        )

        await conn.execute(
            """
            UPDATE projects 
            SET settings = $1, compiler_options = $2, updated_at = NOW() 
            WHERE id = $3
        """,
            json.dumps(current_settings),
            json.dumps(data.compiler_options),
            project_id,
        )

        return await get_project_config(project_id, user)
    finally:
        await release_db(conn)

@router.post("/{project_id}/upload")
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
    _rate_limit: None = Depends(RateLimitDependency(max_requests=10, window_seconds=60, prefix="project:upload")),
):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        uploaded = []
        for upload_file in files:
            filename = upload_file.filename or "unnamed_file"
            content = await upload_file.read()

            from storage_service import validate_file_size

            is_valid, error_msg = validate_file_size(len(content), is_zip=False)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{filename}': {error_msg}",
                )

            stored = await upload_project_file(
                project_id, filename, content
            )

            file_id = secrets.token_hex(16)
            await conn.execute(
                """
                INSERT INTO project_files (id, project_id, filename, original_filename, file_path, file_hash, file_size, is_cloud)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                file_id,
                project_id,
                Path(stored.key).name,
                filename,
                stored.key,
                stored.hash,
                stored.size,
                not stored.is_local,
            )

            uploaded.append(
                {
                    "id": file_id,
                    "filename": Path(stored.key).name,
                    "original_filename": filename,
                    "file_size": stored.size,
                    "file_hash": stored.hash,
                    "created_at": utc_now().isoformat(),
                }
            )
        return uploaded
    finally:
        await release_db(conn)

@router.get("/{project_id}/files")
async def list_files(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await conn.fetchrow(
            "SELECT id FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        files = await conn.fetch(
            """
            SELECT id, filename, original_filename, file_size, file_hash, created_at
            FROM project_files WHERE project_id = $1 ORDER BY created_at DESC
        """,
            project_id,
        )
        return [
            {
                "id": f["id"],
                "filename": f["filename"],
                "original_filename": f["original_filename"],
                "file_size": f["file_size"],
                "file_hash": f["file_hash"],
                "created_at": f["created_at"].isoformat(),
            }
            for f in files
        ]
    finally:
        await release_db(conn)

@router.delete("/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str, file_id: str, user: dict = Depends(get_current_user)
):
    conn = await get_db()
    try:
        file_row = await conn.fetchrow(
            """
            SELECT pf.id, pf.file_path, pf.is_cloud FROM project_files pf
            JOIN projects p ON pf.project_id = p.id
            WHERE pf.id = $1 AND p.user_id = $2
        """,
            file_id,
            user["id"],
        )
        if not file_row:
            raise HTTPException(status_code=404, detail="File not found")

        await storage_service.delete_file(
            file_row["file_path"], not file_row["is_cloud"]
        )
        await conn.execute("DELETE FROM project_files WHERE id = $1", file_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)

@router.post("/{project_id}/upload-zip")
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    _rate_limit: None = Depends(RateLimitDependency(max_requests=5, window_seconds=60, prefix="project:upload-zip")),
):
    """Upload an entire project as a ZIP file."""
    conn = await get_db()
    try:
        # Security: Validate project_id format before any path operations
        validate_project_id(project_id)

        project = await conn.fetchrow(
            "SELECT id, name, language FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not file.filename or not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="File must be a .zip file")

        # Use safe_join for all path operations
        project_dir = safe_join(UPLOAD_DIR, project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        zip_path = safe_join(project_dir, "project.zip")
        content = await file.read()

        from storage_service import validate_file_size

        is_valid, error_msg = validate_file_size(len(content), is_zip=True)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        with open(zip_path, "wb") as f:
            f.write(content)

        source_dir = safe_join(project_dir, "source")
        if source_dir.exists():
            shutil.rmtree(source_dir)
        source_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Validate all paths to prevent Zip Slip vulnerability
                for member in zip_ref.namelist():
                    member_path = (source_dir / member).resolve()
                    if not str(member_path).startswith(str(source_dir.resolve())):
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid ZIP: contains path traversal attempt"
                        )
                zip_ref.extractall(source_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")

        language = (
            project.get("language", "python")
            if hasattr(project, "get")
            else project["language"]
        )

        if language == "nodejs":
            file_tree = scan_nodejs_project_structure(source_dir)
        else:
            file_tree = scan_project_structure(source_dir)

        if file_tree["total_files"] == 0:
            lang_name = "JavaScript/TypeScript" if language == "nodejs" else "Python"
            raise HTTPException(
                status_code=400, detail=f"No {lang_name} files found in ZIP"
            )

        settings = await conn.fetchval(
            "SELECT settings FROM projects WHERE id = $1", project_id
        )
        settings = (
            json.loads(settings) if isinstance(settings, str) and settings else {}
        )

        settings["file_tree"] = file_tree
        settings["is_multi_folder"] = True
        settings["zip_uploaded_at"] = utc_now().isoformat()

        await conn.execute(
            "UPDATE projects SET settings = $1, updated_at = NOW() WHERE id = $2",
            json.dumps(settings),
            project_id,
        )

        zip_path.unlink()

        return {
            "success": True,
            "file_count": file_tree["total_files"],
            "structure": file_tree,
            "message": f"Successfully uploaded {file_tree['total_files']} files",
        }
    except HTTPException:
        raise
    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        import logging

        logging.error(f"Failed to process ZIP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process ZIP file")
    finally:
        await release_db(conn)


# =============================================================================
# Presigned Upload Endpoints (Direct R2 Upload - Bypasses Backend Bandwidth)
# =============================================================================

class PresignedUploadRequest(BaseModel):
    """Request model for presigned upload URL generation."""
    filename: str
    file_size: int
    content_type: str = "application/zip"


class PresignedUploadResponse(BaseModel):
    """Response model for presigned upload URL."""
    upload_url: str
    key: str
    expires_in: int
    max_size: int


class UploadCompleteRequest(BaseModel):
    """Request model for upload completion notification."""
    key: str
    filename: str
    file_size: int


@router.post("/{project_id}/presigned-upload", response_model=PresignedUploadResponse)
async def get_presigned_upload_url(
    project_id: str,
    data: PresignedUploadRequest,
    user: dict = Depends(get_current_user),
):
    """
    Generate a presigned URL for direct frontend → R2 upload.
    
    This bypasses the backend for large file transfers, reducing:
    - Backend bandwidth usage
    - Upload latency (direct to Cloudflare edge)
    - Timeout risks on serverless platforms
    
    Flow:
    1. Frontend requests presigned URL with file metadata
    2. Backend validates ownership and generates presigned PUT URL
    3. Frontend uploads directly to R2 using the presigned URL
    4. Frontend calls /upload-complete to notify backend
    """
    conn = await get_db()
    try:
        # Validate project_id format
        validate_project_id(project_id)
        
        # Verify project ownership
        project = await conn.fetchrow(
            "SELECT id, name FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Validate file size
        is_zip = data.filename.lower().endswith('.zip')
        is_valid, error_msg = validate_file_size(data.file_size, is_zip=is_zip)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Check if cloud storage is available
        if not storage_service.is_cloud_enabled():
            raise HTTPException(
                status_code=503, 
                detail="Cloud storage not configured. Use standard upload endpoint."
            )
        
        # Generate unique key for the upload
        safe_filename = sanitize_filename(data.filename)
        key = f"uploads/{project_id}/direct/{secrets.token_hex(8)}_{safe_filename}"
        
        # Generate presigned PUT URL
        try:
            upload_url = storage_service.client.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': storage_service.bucket,
                    'Key': key,
                    'ContentType': data.content_type,
                },
                ExpiresIn=3600,  # 1 hour
            )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")
        
        return PresignedUploadResponse(
            upload_url=upload_url,
            key=key,
            expires_in=3600,
            max_size=MAX_ZIP_SIZE if is_zip else 100 * 1024 * 1024,
        )
    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    finally:
        await release_db(conn)


@router.post("/{project_id}/upload-complete")
async def complete_presigned_upload(
    project_id: str,
    data: UploadCompleteRequest,
    user: dict = Depends(get_current_user),
):
    """
    Complete a presigned upload by processing the uploaded file.
    
    Called after frontend successfully uploads to R2 using presigned URL.
    This endpoint:
    1. Verifies the file exists in R2
    2. Downloads and extracts if ZIP
    3. Updates project settings with file structure
    """
    conn = await get_db()
    try:
        validate_project_id(project_id)
        
        project = await conn.fetchrow(
            "SELECT id, name, language, settings FROM projects WHERE id = $1 AND user_id = $2",
            project_id,
            user["id"],
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Verify the file exists in R2
        if not storage_service.is_cloud_enabled():
            raise HTTPException(status_code=503, detail="Cloud storage not configured")
        
        try:
            # Check file exists
            storage_service.client.head_object(
                Bucket=storage_service.bucket,
                Key=data.key
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Uploaded file not found in storage")
        
        # If it's a ZIP file, download and extract it
        if data.filename.lower().endswith('.zip'):
            # Download from R2
            response = storage_service.client.get_object(
                Bucket=storage_service.bucket,
                Key=data.key
            )
            content = response['Body'].read()
            
            # Process like standard ZIP upload
            project_dir = safe_join(UPLOAD_DIR, project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            zip_path = safe_join(project_dir, "project.zip")
            with open(zip_path, "wb") as f:
                f.write(content)
            
            source_dir = safe_join(project_dir, "source")
            if source_dir.exists():
                shutil.rmtree(source_dir)
            source_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    # Validate paths for Zip Slip protection
                    for member in zip_ref.namelist():
                        member_path = (source_dir / member).resolve()
                        if not str(member_path).startswith(str(source_dir.resolve())):
                            raise HTTPException(
                                status_code=400,
                                detail="Invalid ZIP: contains path traversal attempt"
                            )
                    zip_ref.extractall(source_dir)
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail="Invalid ZIP file")
            
            language = project["language"] or "python"
            
            if language == "nodejs":
                file_tree = scan_nodejs_project_structure(source_dir)
            else:
                file_tree = scan_project_structure(source_dir)
            
            if file_tree["total_files"] == 0:
                lang_name = "JavaScript/TypeScript" if language == "nodejs" else "Python"
                raise HTTPException(
                    status_code=400, detail=f"No {lang_name} files found in ZIP"
                )
            
            # Update project settings
            settings = project["settings"] or {}
            if isinstance(settings, str):
                settings = json.loads(settings) if settings else {}
            
            settings["file_tree"] = file_tree
            settings["is_multi_folder"] = True
            settings["zip_uploaded_at"] = utc_now().isoformat()
            settings["upload_method"] = "presigned_direct"
            
            await conn.execute(
                "UPDATE projects SET settings = $1, updated_at = NOW() WHERE id = $2",
                json.dumps(settings),
                project_id,
            )
            
            # Clean up
            zip_path.unlink()
            
            # Optionally delete the R2 temp file (keep for debugging initially)
            # storage_service.client.delete_object(Bucket=storage_service.bucket, Key=data.key)
            
            return {
                "success": True,
                "file_count": file_tree["total_files"],
                "structure": file_tree,
                "message": f"Successfully processed {file_tree['total_files']} files via direct upload",
                "upload_method": "presigned_direct",
            }
        else:
            # Non-ZIP file - just record it in project_files
            file_id = secrets.token_hex(16)
            await conn.execute(
                """
                INSERT INTO project_files (id, project_id, filename, original_filename, file_path, file_size, is_cloud)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                file_id,
                project_id,
                Path(data.key).name,
                data.filename,
                data.key,
                data.file_size,
                True,  # is_cloud = True for R2 files
            )
            
            return {
                "success": True,
                "file_id": file_id,
                "message": f"File '{data.filename}' uploaded successfully via direct upload",
                "upload_method": "presigned_direct",
            }
    except HTTPException:
        raise
    except SecurityError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        logger.error(f"Failed to complete presigned upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process uploaded file")
    finally:
        await release_db(conn)
