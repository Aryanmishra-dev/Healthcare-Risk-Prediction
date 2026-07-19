.PHONY: help install dev docker-dev docker-up docker-down test lint format security db-migrate db-rollback clean coverage

help:
	@echo 'Usage: make <target>'
	@echo ''
	@echo 'Available targets:'
	@echo '  install      Install Python dependencies (dev)'
	@echo '  dev          Run development server with hot-reload'
	@echo '  docker-dev   Start PostgreSQL + Redis via Docker Compose'
	@echo '  docker-up    Start full stack (app + db + redis + nginx + mlflow)'
	@echo '  docker-down  Stop all containers'
	@echo '  test         Run test suite (SQLite, no external deps)'
	@echo '  lint         Run linters (black, isort, flake8)'
	@echo '  format       Auto-format code (black + isort)'
	@echo '  security     Run security scans (bandit, pip-audit)'
	@echo '  db-migrate   Apply database migrations'
	@echo '  db-rollback  Rollback last migration'
	@echo '  clean        Remove generated artifacts'
	@echo '  coverage     Run tests with coverage report'

install:
	pip install --upgrade pip
	pip install -r backend/requirements-dev.txt

dev:
	uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

docker-dev:
	docker compose -f deployment/docker/docker-compose.dev.yml up -d

docker-up:
	docker compose -f deployment/docker/docker-compose.yml up -d --build

docker-down:
	docker compose -f deployment/docker/docker-compose.dev.yml down 2>/dev/null; \
	docker compose -f deployment/docker/docker-compose.yml down

test:
	pytest -v --tb=short

lint:
	black --check backend/ ml/ shared/ config/ tests/
	isort --check-only backend/ ml/ shared/ config/ tests/
	flake8 backend/ ml/ shared/ config/ tests/

format:
	black backend/ ml/ shared/ config/ tests/
	isort backend/ ml/ shared/ config/ tests/

security:
	bandit -r backend/app ml shared -x tests,ml/experiments
	pip-audit -r backend/requirements.txt

db-migrate:
	cd backend && alembic upgrade head

db-rollback:
	cd backend && alembic downgrade -1

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null
	find . -name "*.pyc" -not -path "./.venv/*" -not -path "./.git/*" -delete
	rm -rf htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/ .coverage coverage.xml
	rm -rf *.db *.sqlite3
	rm -rf mlruns/

coverage:
	pytest --cov=backend/app --cov-report=html --cov-report=term-missing tests/
