from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging
import json
import hmac
import hashlib
from database import get_db, release_db
from repositories.build_repo import BuildRepository
from config import BUILD_CALLBACK_SECRET

logger = logging.getLogger(__name__)
router = APIRouter()

class WebhookPayload(BaseModel):
    build_id: str
    status: str
    cloud_build_id: Optional[str] = None
    platform: Optional[str] = None
    download_key: Optional[str] = None
    linux_download_key: Optional[str] = None
    windows_download_key: Optional[str] = None
    linux_status: Optional[str] = None
    windows_status: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


@router.post("/webhook")
async def build_webhook(request: Request):
    """Callback from cloud build system."""
    # 1. Verify signature
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    body = await request.body()
    expected = hmac.new(
        BUILD_CALLBACK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Process payload
    try:
        data = json.loads(body)
        payload = WebhookPayload(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    conn = await get_db()
    try:
        # 3. Handle artifacts for specific platforms based on the overall payload
        if not payload.platform:
            if payload.windows_download_key or payload.windows_status:
                await BuildRepository.update_artifact(
                    conn, payload.build_id, 'windows',
                    {
                        'status': payload.windows_status or 'completed',
                        'download_key': payload.windows_download_key,
                        'filename': payload.windows_download_key.split('/')[-1] if payload.windows_download_key else None,
                        'error': payload.error if payload.windows_status == 'failed' else None
                    }
                )
            if payload.linux_download_key or payload.linux_status:
                await BuildRepository.update_artifact(
                    conn, payload.build_id, 'linux',
                    {
                        'status': payload.linux_status or 'completed',
                        'download_key': payload.linux_download_key,
                        'filename': payload.linux_download_key.split('/')[-1] if payload.linux_download_key else None,
                        'error': payload.error if payload.linux_status == 'failed' else None
                    }
                )
        elif payload.platform:
            # 4. Update artifact if specific platform provided
            await BuildRepository.update_artifact(
                conn,
                payload.build_id,
                payload.platform,
                {
                    'status': payload.status,
                    'download_key': payload.download_key,
                    'filename': payload.filename,
                    'error': payload.error
                }
            )

        # 5. Check if overall build should be marked completed
        artifacts = await conn.fetch("SELECT status FROM cloud_build_artifacts WHERE build_id = $1", payload.build_id)
        all_statuses = [a["status"] for a in artifacts]
        
        final_status = payload.status
        final_error = payload.error
        
        if all(s in ["completed", "failed", "cancelled", "skipped"] for s in all_statuses):
            if "completed" in all_statuses:
                final_status = "completed"
            elif all(s in ["cancelled", "skipped"] for s in all_statuses):
                final_status = "cancelled"
            else:
                final_status = "failed"
                
        # 6. Update build status
        # Priority: linux_download_key > windows_download_key > download_key
        final_download_key = payload.linux_download_key or payload.windows_download_key or payload.download_key
        
        await conn.execute(
            """
            UPDATE cloud_builds 
            SET status = $1, error_message = $2, updated_at = NOW(),
                download_key = COALESCE(download_key, $3),
                download_filename = COALESCE(download_filename, $4),
                progress = 100, completed_at = CASE WHEN $1 IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END
            WHERE id = $5
            """,
            final_status,
            final_error,
            final_download_key,
            payload.filename,
            payload.build_id
        )
            
        return {"status": "ok"}
    finally:
        await release_db(conn)
