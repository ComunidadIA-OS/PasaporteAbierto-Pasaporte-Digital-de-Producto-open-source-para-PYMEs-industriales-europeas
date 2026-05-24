from fastapi import FastAPI

from app.api.v1.router import api_router
from app.observability.langfuse_client import init_observability

app = FastAPI(title="PasaporteAbierto", version="0.1.0")
app.include_router(api_router)

# Inicializa observabilidad explícitamente (no como side effect al import).
# Si LANGFUSE_PUBLIC_KEY/SECRET_KEY están configurados, habilita el callback
# automático de LiteLLM hacia Langfuse para que cada llamada a complete()
# emita un span generation. Sin credenciales, es no-op.
init_observability()
