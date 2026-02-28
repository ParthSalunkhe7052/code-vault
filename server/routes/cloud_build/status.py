from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
import logging
from database import get_db, release_db
from repositories.build_repo import BuildRepository
from utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{build_id}/status")
async def get_build_status(
    build_id: str,
    user: dict = Depends(get_current_user),
):
    """Check the status of a specific build."""
    conn = await get_db()
    try:
        build = await BuildRepository.get_build_by_id(conn, build_id)
        if not build:
            raise HTTPException(status_code=404, detail="Build not found")
        
        if build["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        return build
    finally:
        await release_db(conn)

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
