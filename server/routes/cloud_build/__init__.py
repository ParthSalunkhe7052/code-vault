from fastapi import APIRouter
from routes.cloud_build.trigger import router as trigger_router
from routes.cloud_build.status import router as status_router
from routes.cloud_build.webhook import router as webhook_router

router = APIRouter(prefix="/api/v1/cloud-build", tags=["cloud-build"])

router.include_router(trigger_router)
router.include_router(status_router)
router.include_router(webhook_router)
