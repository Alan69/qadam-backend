.PHONY: help up down build logs shell dj migrate migrations test test-cov lint format superuser seed clean

DC = docker compose
EXEC = $(DC) exec web

help:
	@echo "Qadam backend — Makefile commands"
	@echo ""
	@echo "  make up           Start all services in foreground"
	@echo "  make up-d         Start all services in background"
	@echo "  make down         Stop all services"
	@echo "  make build        Rebuild images"
	@echo "  make logs         Tail logs from all services"
	@echo "  make shell        Open bash inside web container"
	@echo "  make dj           Open Django shell_plus"
	@echo "  make migrate      Apply migrations"
	@echo "  make migrations   Create new migrations"
	@echo "  make test         Run tests"
	@echo "  make test-cov     Run tests with coverage report"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Run ruff formatter"
	@echo "  make superuser    Create Django superuser"
	@echo "  make seed         Load fixtures (test data)"
	@echo "  make clean        Remove containers, volumes, cache"

up:
	$(DC) up

up-d:
	$(DC) up -d

down:
	$(DC) down

build:
	$(DC) build

logs:
	$(DC) logs -f

shell:
	$(EXEC) bash

dj:
	$(EXEC) python manage.py shell_plus

migrate:
	$(EXEC) python manage.py migrate

migrations:
	$(EXEC) python manage.py makemigrations

test:
	$(EXEC) pytest

test-cov:
	$(EXEC) pytest --cov --cov-report=term-missing --cov-report=html

lint:
	$(EXEC) ruff check src/

format:
	$(EXEC) ruff format src/
	$(EXEC) ruff check --fix src/

superuser:
	$(EXEC) python manage.py createsuperuser

seed:
	$(EXEC) python manage.py loaddata initial_data

clean:
	$(DC) down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
