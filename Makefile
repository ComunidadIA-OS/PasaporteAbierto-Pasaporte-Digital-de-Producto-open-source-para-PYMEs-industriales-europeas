.PHONY: up down logs test seed reset health

up:
	docker compose up -d --build

up-ollama:
	docker compose --profile ollama up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && uv run pytest -v
	cd frontend && pnpm test

health:
	@curl -s http://localhost:8000/api/v1/health | python -m json.tool

seed:
	cd backend && uv run python -m scripts.seed

reset:
	cd backend && uv run python -m scripts.reset_db

.PHONY: ingest
INGEST_ARGS ?=
ingest:
	cd backend && PYTHONPATH=src uv run python -m app.rag.ingest $(INGEST_ARGS)
