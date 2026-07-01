"""API endpoints routes directory initialization module."""

from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router

router = APIRouter()

# Include subrouters
router.include_router(chat_router)
router.include_router(health_router)
