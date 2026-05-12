.PHONY: install test lint typecheck fmt dev-api dev-agent dev-frontend docker-up docker-down docker-logs docker-build ingest clean help

# ── Backend ──────────────────────────────────────────────

install:
	cd backend && uv sync

test:
	cd backend && PYTHONPATH=src uv run pytest -v --cov=advisor --cov-report=term

lint:
	cd backend && uv run ruff check src/ tests/

typecheck:
	cd backend && PYTHONPATH=src uv run mypy src/

fmt:
	cd backend && uv run ruff format src/ tests/ && uv run ruff check --fix src/ tests/

# ── Dev Servers ─────────────────────────────────────────

dev-api:
	cd backend && PYTHONPATH=src uv run uvicorn advisor.api.app:app --reload --host 0.0.0.0 --port 8000

dev-agent:
	cd backend && PYTHONPATH=src uv run python -m advisor.agent.main

dev-frontend:
	cd frontend && npm run dev

# ── Docker ──────────────────────────────────────────────

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-build:
	docker compose build

# ── Database ────────────────────────────────────────────

db-migrate:
	cd backend && PYTHONPATH=src uv run alembic upgrade head

db-revision:
	cd backend && PYTHONPATH=src uv run alembic revision --autogenerate -m "$(message)"

# ── RAG Ingestion ───────────────────────────────────────

ingest:
	cd backend && PYTHONPATH=src uv run python -m advisor.rag.ingest

ingest-recreate:
	cd backend && PYTHONPATH=src uv run python -m advisor.rag.ingest --recreate

# ── Cleanup ─────────────────────────────────────────────

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv
	rm -rf frontend/dist

# ── Help ────────────────────────────────────────────────

help:
	@echo "Usage:"
	@echo "  make install         Install backend dependencies"
	@echo "  make test            Run backend tests"
	@echo "  make lint            Lint backend code"
	@echo "  make typecheck       Run mypy type checking"
	@echo "  make fmt             Format backend code"
	@echo "  make dev-api         Start API dev server (hot reload)"
	@echo "  make dev-agent       Start agent dev server"
	@echo "  make dev-frontend    Start frontend dev server"
	@echo "  make docker-up       Start all services"
	@echo "  make docker-down     Stop all services"
	@echo "  make docker-logs     Tail docker logs"
	@echo "  make docker-build    Rebuild Docker images"
	@echo "  make ingest          Ingest knowledge base into Qdrant"
	@echo "  make ingest-recreate Recreate collection and re-ingest"
	@echo "  make db-migrate      Run database migrations"
	@echo "  make db-revision     Create new migration revision"
	@echo "  make clean           Remove caches and build artifacts"
