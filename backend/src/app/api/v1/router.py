from fastapi import APIRouter

from app.api.v1 import chat, health, wizard

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(wizard.router)
api_router.include_router(chat.router)
