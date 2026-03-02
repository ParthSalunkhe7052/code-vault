from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
import logging
from database import get_db, release_db
from repositories.build_repo import BuildRepository
from utils import get_current_user

from routes.cloud_build_routes import get_build_status as real_get_build_status

logger = logging.getLogger(__name__)
router = APIRouter()

# Use the full-featured get_build_status from the monolithic router
# which properly aggregates artifacts, generates signed URLs, handles sync=true etc.
router.get("/{build_id}/status")(real_get_build_status)

@router.get("/history")
async def list_build_history(
    user: dict = Depends(get_current_user),
    limit: int = 50,
):
    """List recent builds for the user."""
    conn = await get_db()
    try:
        return await BuildRepository.list_user_builds(conn, user["id"], limit)
    finally:
        await release_db(conn)
