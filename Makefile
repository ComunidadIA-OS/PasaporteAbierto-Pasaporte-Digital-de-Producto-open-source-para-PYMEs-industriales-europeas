.PHONY: up up-remote up-ollama down logs test seed reset health ingest demo demo-full demo-ui

# Lee MODEL_LOCAL desde .env (si existe). Si vale "true" añade el profile
# `ollama` a todos los comandos de compose, de forma que un único `make up`
# arranca el stack correcto sin tener que recordar `--profile ollama`.
ifneq (,$(wildcard .env))
include .env
export
endif

COMPOSE_PROFILE_FLAG :=
ifeq ($(MODEL_LOCAL),true)
COMPOSE_PROFILE_FLAG := --profile ollama
endif

up:
	docker compose $(COMPOSE_PROFILE_FLAG) up -d --build

# Atajos explícitos por si alguien quiere ignorar el toggle de .env.
up-ollama:
	docker compose --profile ollama up -d --build

up-remote:
	docker compose up -d --build

down:
	docker compose $(COMPOSE_PROFILE_FLAG) down

logs:
	docker compose $(COMPOSE_PROFILE_FLAG) logs -f

test:
	cd backend && uv run pytest -v
	cd frontend && pnpm test

health:
	@curl -s http://localhost:8000/api/v1/health | python -m json.tool

seed:
	cd backend && uv run python -m scripts.seed

reset:
	cd backend && uv run python -m scripts.reset_db

INGEST_ARGS ?=
ingest:
	cd backend && PYTHONPATH=src uv run python -m app.rag.ingest $(INGEST_ARGS)

# Demo precargada: crea sesión + clasificación + BOM (47 campos) + 4 PDFs
# sintéticos vía API y abre el wizard en el navegador para continuar
# manualmente desde el paso 5 (extracción IA). El stack debe estar arriba
# (`make up`). Útil para enseñar el flujo sin teclear los campos a mano.
#
# STOP_AT permite ajustar dónde para el script (1..6). 4 deja BOM+docs
# cargados; 3 deja solo BOM; 5 deja la extracción ya ejecutada.
STOP_AT ?= 4
demo:
	uv run scripts/e2e_demo/run.py --stop-at $(STOP_AT) --open-browser

# Recorrido E2E completo (los 7 pasos vía API, sin UI). Útil como smoke
# test antes de demos o tras cambios en el pipeline.
demo-full:
	uv run scripts/e2e_demo/run.py

# Wizard manual con botones "Cargar ejemplo" en pasos 1, 3 y 4.
# Requiere DEMO_MODE=true en .env (re-arranca el stack para aplicar).
# Abre el navegador en /wizard para empezar una sesión nueva.
demo-ui:
	@grep -q '^DEMO_MODE=true' .env || { \
	  echo "→ Activando DEMO_MODE=true en .env"; \
	  sed -i.bak '/^DEMO_MODE=/d' .env && echo "DEMO_MODE=true" >> .env; \
	}
	docker compose $(COMPOSE_PROFILE_FLAG) up -d --build
	@echo ""
	@echo "→ Stack listo con modo demo activado."
	@echo "→ Abre http://localhost:3000/wizard y pulsa 'Cargar ejemplo' en cada paso."
	@command -v open >/dev/null && open http://localhost:3000/wizard || \
	  command -v xdg-open >/dev/null && xdg-open http://localhost:3000/wizard || true
