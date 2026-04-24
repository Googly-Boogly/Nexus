.PHONY: dev build test lint migrate seed seed-knowledge clean shell logs qdrant-ui compare-rag

dev:
	docker compose up --build

build:
	docker compose build

test:
	docker compose run --rm api pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	docker compose run --rm api bandit -r app/ -ll
	docker compose run --rm api python -m detect_secrets scan > .secrets.baseline

migrate:
	docker compose run --rm api alembic upgrade head

seed:
	docker compose run --rm api python scripts/seed_db.py

seed-knowledge:
	docker compose run --rm api python scripts/seed_knowledge.py

clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

shell:
	docker compose run --rm api bash

logs:
	docker compose logs -f api worker

qdrant-ui:
	@echo "Opening Qdrant dashboard: http://localhost:6333/dashboard"
	@open http://localhost:6333/dashboard 2>/dev/null || xdg-open http://localhost:6333/dashboard 2>/dev/null || true

compare-rag:
	@echo "Comparing retrieval paths for test query..."
	docker compose run --rm api python -c \
	  "import asyncio; from app.rag.pipeline import RAGPipeline; \
	   asyncio.run(RAGPipeline().compare_paths('What are P1 escalation steps?'))"
