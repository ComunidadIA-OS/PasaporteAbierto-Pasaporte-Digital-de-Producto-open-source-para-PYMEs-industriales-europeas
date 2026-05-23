from fastapi import APIRouter

from app import __version__
from app.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    backend = settings.model_backend
    model = backend.split(":", 1)[1] if ":" in backend else backend
    return {
        "version": __version__,
        "model": model,
        "backend": backend,
    }
