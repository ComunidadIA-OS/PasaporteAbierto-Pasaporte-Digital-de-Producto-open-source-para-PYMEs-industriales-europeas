.PHONY: up up-remote up-ollama down logs test seed reset health ingest

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
