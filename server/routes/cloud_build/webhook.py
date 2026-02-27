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
    platform: Optional[str] = None
    download_key: Optional[str] = None
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
        # 3. Update build status
        await BuildRepository.update_build_status(
            conn, 
            payload.build_id, 
            payload.status, 
            payload.error
        )
        
        # 4. Update artifact if platform provided
        if payload.platform:
            await BuildRepository.update_artifact(
                conn,
                payload.build_id,
                payload.platform,
                {
                    'status': payload.status,
                    'download_key': payload.download_key,
                    'error': payload.error
                }
            )
            
        return {"status": "ok"}
    finally:
        await release_db(conn)
