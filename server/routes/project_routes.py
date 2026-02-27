import asyncio
import json
import secrets
import shutil
import zipfile
import logging

from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile


from database import get_db, release_db
from repositories.project_repo import ProjectRepository
from utils import (
    get_current_user,
    utc_now,
    safe_join,
    validate_project_id,
    SecurityError,
    get_user_tier_limits,
    get_user_tier,
)
from storage_service import (
    storage_service,
    upload_project_file,
    LOCAL_UPLOAD_DIR,
    validate_file_size,
)
from models import ProjectCreateRequest, ProjectConfigRequest, ProjectBrandingRequest
from pydantic import BaseModel, Field
from routes.project_helpers import scan_project_structure, scan_nodejs_project_structure
from routes.cloud_build_utils import invalidate_cached_source
from middleware.rate_limiter import RateLimitDependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Local upload directory
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("")
async def list_projects(user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        rows = await ProjectRepository.list_user_projects(conn, user["id"])
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
async def create_project(
    data: ProjectCreateRequest, user: dict = Depends(get_current_user)
):
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

        # Generate Ed25519 key pair for asymmetric signature verification
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PrivateFormat,
            PublicFormat,
            NoEncryption,
        )

        ed_private_key = Ed25519PrivateKey.generate()
        signing_private_key = ed_private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        ).decode("utf-8")
        signing_public_key = (
            ed_private_key.public_key()
            .public_bytes(
                encoding=Encoding.PEM,
                format=PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        project_data = {
            'name': data.name,
            'description': data.description,
            'language': data.language,
            'compiler_options': data.compiler_options,
            'signing_secret': secrets.token_hex(32),
            'signing_private_key': signing_private_key,
            'signing_public_key': signing_public_key,
        }

        project_id = await ProjectRepository.create_project(conn, user["id"], project_data)
        
        return {
            "id": project_id,
            "name": data.name,
            "description": data.description,
            "language": data.language,
            "compiler_options": data.compiler_options,
            "signing_secret": project_data['signing_secret'],
            "signing_public_key": signing_public_key,
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
        project = await ProjectRepository.get_project_by_id(conn, project_id, user["id"])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await storage_service.delete_project_files(project_id)
        await ProjectRepository.delete_project(conn, project_id)
        return {"status": "deleted"}
    finally:
        await release_db(conn)

@router.get(\"/{project_id}/config\")
async def get_project_config(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(status_code=404, detail=\"Project not found\")

        settings = project[\"settings\"] or {}
        if isinstance(settings, str):
            settings = json.loads(settings) if settings else {}

        compiler_opts = project.get(\"compiler_options\") or {}
        if isinstance(compiler_opts, str):
            compiler_opts = json.loads(compiler_opts)

        language = project.get(\"language\", \"python\")

        files = await ProjectRepository.get_project_files(conn, project_id)

        import os
        server_url = os.getenv(\"PUBLIC_API_URL\", \"http://127.0.0.1:8000\")
        api_url = f\"{server_url}/api/v1/license/validate\"

        selected_license_id = settings.get(\"selected_license_id\")
        tier_info = await get_user_tier(user[\"id\"], conn)

        return {
            \"project_name\": project[\"name\"],
            \"entry_file\": settings.get(\"entry_file\"),
            \"output_name\": settings.get(\"output_name\"),
            \"include_modules\": settings.get(\"include_modules\", []),
            \"exclude_modules\": settings.get(\"exclude_modules\", []),
            \"nuitka_options\": settings.get(\"nuitka_options\", {}),
            \"pkg_options\": settings.get(\"pkg_options\", {}),
            \"compiler_options\": compiler_opts,
            \"language\": language,
            \"signing_public_key\": project.get(\"signing_public_key\"),
            \"api_url\": api_url,
            \"server_url\": server_url,
            \"selected_license_id\": selected_license_id,
            \"skip_obfuscation\": settings.get(\"skip_obfuscation\", True),
            \"enable_lease\": settings.get(\"enable_lease\", False),
            \"use_onefile\": settings.get(\"use_onefile\", False),
            \"is_gui_app\": settings.get(\"is_gui_app\", False),
            \"enable_binary_hash\": settings.get(\"enable_binary_hash\", False),
            \"tier\": tier_info[\"tier\"],
            \"is_pro\": tier_info[\"is_pro\"],
            \"can_remove_branding\": tier_info[\"can_remove_branding\"],
            \"can_custom_branding\": tier_info[\"can_custom_branding\"],
            \"files\": [
                {
                    \"id\": f[\"id\"],
                    \"filename\": f[\"filename\"],
                    \"original_filename\": f[\"original_filename\"],
                    \"file_size\": f[\"file_size\"],
                    \"file_hash\": f[\"file_hash\"],
                    \"created_at\": f[\"created_at\"].isoformat(),
                }
                for f in files
            ],
        }
    finally:
        await release_db(conn)


@router.get(\"/{project_id}/build-config\")
async def get_build_config(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    import os
    conn = await get_db()
    try:
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(status_code=404, detail=\"Project not found\")

        settings = project[\"settings\"] or {}
        if isinstance(settings, str):
            settings = json.loads(settings) if settings else {}

        tier_info = await get_user_tier(user[\"id\"], conn)
        license_server_url = os.getenv(\"PUBLIC_API_URL\", \"https://api.codevault.dev\")
        heartbeat_interval = settings.get(\"heartbeat_interval\", 300)

        show_branding = not tier_info.get(\"can_remove_branding\", False)
        if settings.get(\"show_branding\") is not None:
            show_branding = settings.get(\"show_branding\", True)

        return {
            \"project_id\": project_id,
            \"project_name\": project[\"name\"],
            \"language\": project.get(\"language\", \"python\"),
            \"server_url\": license_server_url,
            \"signing_public_key\": project.get(\"signing_public_key\") or \"\",
            \"heartbeat_interval\": heartbeat_interval,
            \"entry_file\": settings.get(\"entry_file\"),
            \"output_name\": settings.get(\"output_name\"),
            \"enable_lease\": settings.get(\"enable_lease\", False),
            \"enable_binary_hash\": settings.get(\"enable_binary_hash\", False),
            \"show_branding\": show_branding,
            \"brand_name\": project.get(\"brand_name\") or \"CodeVault\",
            \"brand_url\": project.get(\"brand_url\") or \"https://codevault.dev\",
            \"brand_primary_color\": project.get(\"brand_primary_color\") or \"#6366f1\",
            \"nuitka_options\": settings.get(\"nuitka_options\", {}),
            \"compiler_options\": {},
            \"tier\": tier_info[\"tier\"],
        }
    finally:
        await release_db(conn)


@router.put(\"/{project_id}/config\")
async def update_project_config(
    project_id: str, data: ProjectConfigRequest, user: dict = Depends(get_current_user)
):
    conn = await get_db()
    try:
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(status_code=404, detail=\"Project not found\")

        current_settings = (
            json.loads(project[\"settings\"])
            if isinstance(project[\"settings\"], str)
            else (project[\"settings\"] or {})
        )

        current_settings.update(
            {
                \"entry_file\": data.entry_file,
                \"output_name\": data.output_name,
                \"include_modules\": data.include_modules,
                \"exclude_modules\": data.exclude_modules,
                \"nuitka_options\": data.nuitka_options,
                \"skip_obfuscation\": data.skip_obfuscation,
                \"enable_lease\": data.enable_lease,
                \"use_onefile\": data.use_onefile,
                \"is_gui_app\": data.is_gui_app,
                \"enable_binary_hash\": data.enable_binary_hash,
            }
        )

        await ProjectRepository.update_project_config(
            conn,
            project_id,
            current_settings,
            data.compiler_options
        )

        return {\"status\": \"ok\", \"message\": \"Configuration saved successfully\"}
    finally:
        await release_db(conn)

@router.post(\"/{project_id}/upload\")
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
    _rate_limit: None = Depends(
        RateLimitDependency(max_requests=10, window_seconds=60, prefix=\"project:upload\")
    ),
):
    conn = await get_db()
    try:
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(status_code=404, detail=\"Project not found\")

        uploaded = []
        for upload_file in files:
            filename = upload_file.filename or \"unnamed_file\"
            content = await upload_file.read()

            is_valid, error_msg = validate_file_size(len(content), is_zip=False)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f\"File '{filename}': {error_msg}\",
                )

            stored = await upload_project_file(project_id, filename, content)

            file_data = {
                'project_id': project_id,
                'filename': Path(stored.key).name,
                'original_filename': filename,
                'file_path': stored.key,
                'file_hash': stored.hash,
                'file_size': stored.size,
                'is_cloud': not stored.is_local,
            }
            file_id = await ProjectRepository.create_project_file(conn, file_data)

            uploaded.append(
                {
                    \"id\": file_id,
                    \"filename\": Path(stored.key).name,
                    \"original_filename\": filename,
                    \"file_size\": stored.size,
                    \"file_hash\": stored.hash,
                    \"created_at\": utc_now().isoformat(),
                }
            )

        await invalidate_cached_source(project_id)
        return uploaded
    finally:
        await release_db(conn)


@router.get(\"/{project_id}/files\")
async def list_files(project_id: str, user: dict = Depends(get_current_user)):
    conn = await get_db()
    try:
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(status_code=404, detail=\"Project not found\")

        files = await ProjectRepository.get_project_files(conn, project_id)
        return [
            {
                \"id\": f[\"id\"],
                \"filename\": f[\"filename\"],
                \"original_filename\": f[\"original_filename\"],
                \"file_size\": f[\"file_size\"],
                \"file_hash\": f[\"file_hash\"],
                \"created_at\": f[\"created_at\"].isoformat(),
            }
            for f in files
        ]
    finally:
        await release_db(conn)


@router.delete(\"/{project_id}/files/{file_id}\")
async def delete_file(
    project_id: str, file_id: str, user: dict = Depends(get_current_user)
):
    conn = await get_db()
    try:
        file_row = await ProjectRepository.get_project_file(conn, file_id, user[\"id\"])
        if not file_row:
            raise HTTPException(status_code=404, detail=\"File not found\")

        await storage_service.delete_file(
            file_row[\"file_path\"], not file_row[\"is_cloud\"]
        )
        await ProjectRepository.delete_project_file(conn, file_id)
        return {\"status\": \"deleted\"}
    finally:
        await release_db(conn)

@router.post(\"/{project_id}/upload-zip\")
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    _rate_limit: None = Depends(
        RateLimitDependency(
            max_requests=5, window_seconds=60, prefix=\"project:upload-zip\"
        )
    ),
):
    conn = await get_db()
    try:
        validate_project_id(project_id)
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(status_code=404, detail=\"Project not found\")

        if not file.filename or not file.filename.endswith(\".zip\"):
            raise HTTPException(status_code=400, detail=\"File must be a .zip file\")

        project_dir = safe_join(UPLOAD_DIR, project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        zip_path = safe_join(project_dir, \"project.zip\")

        CHUNK_SIZE = 1024 * 1024
        total_size = 0
        collected_chunks: list[bytes] = []

        while chunk := await file.read(CHUNK_SIZE):
            total_size += len(chunk)
            is_valid, error_msg = validate_file_size(total_size, is_zip=True)
            if not is_valid:
                zip_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=error_msg)
            collected_chunks.append(chunk)

        def _write_zip() -> None:
            with open(zip_path, \"wb\") as fh:
                for c in collected_chunks:
                    fh.write(c)

        await asyncio.to_thread(_write_zip)
        del collected_chunks

        source_dir = safe_join(project_dir, \"source\")
        async def _remove_old_source() -> None:
            if source_dir.exists():
                await asyncio.to_thread(shutil.rmtree, source_dir)

        await asyncio.gather(_remove_old_source(), invalidate_cached_source(project_id))
        source_dir.mkdir(parents=True, exist_ok=True)

        def _validate_and_extract() -> None:
            resolved_source = str(source_dir.resolve())
            try:
                with zipfile.ZipFile(zip_path, \"r\") as zip_ref:
                    for member in zip_ref.infolist():
                        member_path = (source_dir / member.filename).resolve()
                        if not str(member_path).startswith(resolved_source):
                            raise HTTPException(400, \"Invalid ZIP: path traversal\")
                        zip_ref.extract(member, source_dir)
            except zipfile.BadZipFile:
                raise HTTPException(400, \"Invalid ZIP file\")

        await asyncio.to_thread(_validate_and_extract)

        language = project.get(\"language\", \"python\")
        if language == \"nodejs\":
            file_tree = await asyncio.to_thread(scan_nodejs_project_structure, source_dir)
        else:
            file_tree = await asyncio.to_thread(scan_project_structure, source_dir)

        if file_tree[\"total_files\"] == 0:
            raise HTTPException(400, f\"No files found in ZIP\")

        settings = project[\"settings\"] or {}
        if isinstance(settings, str):
            settings = json.loads(settings) if settings else {}

        settings[\"file_tree\"] = file_tree
        settings[\"is_multi_folder\"] = True
        settings[\"zip_uploaded_at\"] = utc_now().isoformat()

        await ProjectRepository.update_project_settings(conn, project_id, settings)
        await asyncio.to_thread(zip_path.unlink, True)

        return {\"success\": True, \"file_count\": file_tree[\"total_files\"], \"message\": \"Uploaded successfully\"}
    finally:
        await release_db(conn)


@router.post(\"/{project_id}/upload-zip-url\")
async def get_upload_url(
    project_id: str,
    request: UploadUrlRequest,
    user: dict = Depends(get_current_user),
):
    conn = await get_db()
    try:
        validate_project_id(project_id)
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(404, \"Project not found\")

        upload_token = secrets.token_urlsafe(32)
        r2_key = f\"uploads/{project_id}/{upload_token}/{request.filename}\"
        presigned_url = storage_service.generate_presigned_url(r2_key, expires_in=3600, for_upload=True)

        if not presigned_url:
            raise HTTPException(503, \"Storage service unavailable\")

        await ProjectRepository.create_upload_token(conn, project_id, {
            'token': upload_token, 'r2_key': r2_key, 'filename': request.filename, 'file_size': request.file_size
        })

        return {\"upload_url\": presigned_url, \"token\": upload_token, \"expires_in\": 3600}
    finally:
        await release_db(conn)

@router.post(\"/{project_id}/process-upload\")
async def process_r2_upload(
    project_id: str,
    token: str,
    user: dict = Depends(get_current_user),
):
    conn = await get_db()
    try:
        validate_project_id(project_id)
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(404, \"Project not found\")

        token_record = await ProjectRepository.get_upload_token(conn, project_id, token)
        if not token_record:
            raise HTTPException(400, \"Invalid upload token\")

        r2_key = token_record[\"r2_key\"]
        temp_dir = safe_join(LOCAL_UPLOAD_DIR, project_id, \"temp_upload\")
        temp_dir.mkdir(parents=True, exist_ok=True)
        local_zip_path = safe_join(temp_dir, token_record[\"filename\"])

        try:
            file_content = await storage_service.download_file(r2_key)
            if not file_content:
                raise HTTPException(400, \"File not found\")
            local_zip_path.write_bytes(file_content)
        except Exception:
            raise HTTPException(500, \"Download failed\")

        project_dir = safe_join(LOCAL_UPLOAD_DIR, project_id)
        source_dir = safe_join(project_dir, \"source\")
        async def _remove_old_source() -> None:
            if source_dir.exists():
                await asyncio.to_thread(shutil.rmtree, source_dir)

        await asyncio.gather(_remove_old_source(), storage_service.delete_file(r2_key))
        source_dir.mkdir(parents=True, exist_ok=True)

        def _validate_and_extract() -> None:
            resolved_source = str(source_dir.resolve())
            with zipfile.ZipFile(local_zip_path, \"r\") as zip_ref:
                for member in zip_ref.infolist():
                    member_path = (source_dir / member.filename).resolve()
                    if not str(member_path).startswith(resolved_source):
                        raise HTTPException(400, \"Invalid ZIP\")
                    zip_ref.extract(member, source_dir)

        await asyncio.to_thread(_validate_and_extract)

        language = project.get(\"language\", \"python\")
        if language == \"nodejs\":
            file_tree = await asyncio.to_thread(scan_nodejs_project_structure, source_dir)
        else:
            file_tree = await asyncio.to_thread(scan_project_structure, source_dir)

        settings = project[\"settings\"] or {}
        if isinstance(settings, str):
            settings = json.loads(settings) if settings else {}

        settings[\"file_tree\"] = file_tree
        settings[\"is_multi_folder\"] = True
        settings[\"zip_uploaded_at\"] = utc_now().isoformat()

        await ProjectRepository.update_project_settings(conn, project_id, settings)
        await asyncio.to_thread(local_zip_path.unlink, True)
        await asyncio.to_thread(shutil.rmtree, temp_dir)

        return {\"success\": True, \"file_count\": file_tree[\"total_files\"]}
    finally:
        await release_db(conn)


@router.post(\"/{project_id}/binary-hash\")
async def register_binary_hash(
    project_id: str,
    data: BinaryHashRequest,
    user: dict = Depends(get_current_user),
):
    conn = await get_db()
    try:
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(404, \"Project not found\")

        await ProjectRepository.register_binary_hash(conn, project_id, data.dict())
        return {\"status\": \"registered\", \"binary_hash\": data.binary_hash}
    finally:
        await release_db(conn)


@router.get(\"/{project_id}/branding\")
async def get_project_branding(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    conn = await get_db()
    try:
        project = await ProjectRepository.get_branding(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(404, \"Project not found\")

        tier_info = await get_user_tier_limits(user[\"id\"], conn)
        return {
            \"brand_name\": project[\"brand_name\"],
            \"brand_url\": project[\"brand_url\"],
            \"brand_primary_color\": project[\"brand_primary_color\"] or \"#6366f1\",
            \"brand_secondary_color\": project[\"brand_secondary_color\"] or \"#4f46e5\",
            \"brand_logo_url\": project[\"brand_logo_url\"],
            \"can_custom_branding\": tier_info.get(\"white_label_branding\", False),
        }
    finally:
        await release_db(conn)


@router.put(\"/{project_id}/branding\")
async def update_project_branding(
    project_id: str,
    data: ProjectBrandingRequest,
    user: dict = Depends(get_current_user),
):
    conn = await get_db()
    try:
        project = await ProjectRepository.get_project_by_id(conn, project_id, user[\"id\"])
        if not project:
            raise HTTPException(404, \"Project not found\")

        tier_info = await get_user_tier_limits(user[\"id\"], conn)
        if not tier_info.get(\"white_label_branding\", False):
            raise HTTPException(403, \"Upgrade for white label branding\")

        await ProjectRepository.update_branding(conn, project_id, data.dict())
        return {\"status\": \"updated\"}
    finally:
        await release_db(conn)
