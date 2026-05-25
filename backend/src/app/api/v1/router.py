from fastapi import APIRouter

from app.api.v1 import audit, chat, health, plugins, wizard

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(wizard.router)
api_router.include_router(chat.router)
# Histórico del chat por sesión bajo /sessions/{id}/chat (F3-04 criterio 3).
# Vive en chat.py por proximidad lógica al endpoint POST /chat aunque se
# monta bajo el prefijo /sessions.
api_router.include_router(chat.history_router)
api_router.include_router(plugins.router)
api_router.include_router(audit.router)
