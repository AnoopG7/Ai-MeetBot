.PHONY: install test lint typecheck fmt dev-api dev-agent dev-frontend docker-up docker-down clean

# ── Backend ──────────────────────────────────────────────

install:
	cd backend && uv sync --frozen

test:
	cd backend && uv run pytest -v --cov=advisor --cov-report=term

lint:
	cd backend && uv run ruff check src/ tests/

typecheck:
	cd backend && uv run mypy src/ --ignore-missing-imports

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

# ── Pre-commit ──────────────────────────────────────────

pre-commit-install:
	cd backend && uv run pre-commit install

pre-commit-run:
	cd backend && uv run pre-commit run --all-files

# ── Database ────────────────────────────────────────────

db-migrate:
	cd backend && uv run alembic upgrade head

db-revision:
	cd backend && uv run alembic revision --autogenerate -m "$(message)"

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
