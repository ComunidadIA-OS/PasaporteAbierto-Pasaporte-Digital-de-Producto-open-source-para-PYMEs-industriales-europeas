import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.public_dpp import router as public_dpp_router
from app.api.v1.router import api_router
from app.db.session import init_db
from app.observability.langfuse_client import init_observability


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Inicializa BD (crea tablas si no existen) y observabilidad al arrancar."""
    init_db()
    init_observability()
    yield


app = FastAPI(title="PasaporteAbierto", version="0.1.0", lifespan=lifespan)

# CORS — el frontend (Next.js) corre en otro origen (puerto distinto en dev,
# host distinto en algunos despliegues). Sin esto, los client components
# fallan en el preflight OPTIONS antes de llegar al handler.
# CORS_ALLOW_ORIGINS admite lista separada por comas; default cubre dev local.
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_origins = [
    o.strip()
    for o in os.environ.get("CORS_ALLOW_ORIGINS", _default_origins).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
# Endpoint público del DPP — fuera de /api/v1 a propósito (URL navegable
# para escaneo del QR, content negotiation JSON-LD/HTML).
app.include_router(public_dpp_router)

# Observabilidad e init_db se ejecutan en el lifespan (arriba).
