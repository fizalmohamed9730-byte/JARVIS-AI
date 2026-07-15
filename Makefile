.PHONY: install dev build test lint format clean docker-up docker-down migrate seed help

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
PIP := pip
NODE := node
NPM := npm
DOCKER := docker-compose
DOCKER_DEV := docker-compose -f docker-compose.yml -f docker-compose.dev.yml

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m

# ============================================
# Development Commands
# ============================================

## Install all dependencies
install: install-backend install-frontend

install-backend:
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	$(PIP) install -r backend/requirements.txt
	$(PIP) install -e ".[dev]"

install-frontend:
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && $(NPM) install

## Start development servers
dev:
	@echo "$(GREEN)Starting development servers...$(NC)"
	$(PYTHON) -m uvicorn backend.main:app --reload --port 8000 &
	cd frontend && $(NPM) start

## Build production assets
build:
	@echo "$(BLUE)Building for production...$(NC)"
	cd frontend && $(NPM) run build

## Run all tests
test: test-backend test-frontend

test-backend:
	@echo "$(BLUE)Running backend tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov

test-frontend:
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && $(NPM) test -- --watchAll=false

## Run linting
lint: lint-backend lint-frontend

lint-backend:
	@echo "$(BLUE)Linting backend code...$(NC)"
	ruff check .
	black --check .

lint-frontend:
	@echo "$(BLUE)Linting frontend code...$(NC)"
	cd frontend && $(NPM) run lint

## Format code
format:
	@echo "$(GREEN)Formatting code...$(NC)"
	ruff format .
	black .
	cd frontend && $(NPM) run format

## Clean build artifacts
clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	rm -rf frontend/build frontend/dist node_modules
	rm -rf dist build *.egg-info

# ============================================
# Database Commands
# ============================================

## Run database migrations
migrate:
	@echo "$(BLUE)Running database migrations...$(NC)"
	alembic upgrade head

## Create new migration
migration:
	@echo "$(BLUE)Creating new migration...$(NC)"
	alembic revision --autogenerate -m "$(msg)"

## Seed database with sample data
seed:
	@echo "$(GREEN)Seeding database...$(NC)"
	$(PYTHON) -m backend.seed

## Reset database (WARNING: destroys data)
db-reset:
	@echo "$(YELLOW)Resetting database...$(NC)"
	$(PYTHON) -m backend.seed --reset

# ============================================
# Docker Commands
# ============================================

## Start Docker containers
docker-up:
	@echo "$(GREEN)Starting Docker containers...$(NC)"
	$(DOCKER) up -d

## Stop Docker containers
docker-down:
	@echo "$(YELLOW)Stopping Docker containers...$(NC)"
	$(DOCKER) down

## Start development containers
docker-dev:
	@echo "$(GREEN)Starting development containers...$(NC)"
	$(DOCKER_DEV) up -d

## View Docker logs
docker-logs:
	$(DOCKER) logs -f

## Rebuild Docker images
docker-rebuild:
	@echo "$(BLUE)Rebuilding Docker images...$(NC)"
	$(DOCKER) build --no-cache

## Clean Docker resources
docker-clean:
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	$(DOCKER) down -v --rmi all
	docker system prune -f

# ============================================
# Electron Commands
# ============================================

## Install Electron dependencies
electron-install:
	cd electron && $(NPM) install

## Run Electron in development
electron-dev:
	cd electron && $(NPM) run dev

## Build Electron for current platform
electron-build:
	cd electron && $(NPM) run build

## Build Electron for all platforms
electron-build-all:
	cd electron && $(NPM) run build:all

# ============================================
# Utilities
# ============================================

## Show project status
status:
	@echo "$(GREEN)Project Status$(NC)"
	@echo "-------------"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Node: $$($(NODE) --version)"
	@echo "npm: $$($(NPM) --version)"
	@echo "Docker: $$($(DOCKER) --version 2>/dev/null || echo 'not installed')"

## Generate API documentation
docs:
	@echo "$(BLUE)Generating API documentation...$(NC)"
	cd docs && mkdocs build

## Run security checks
security:
	@echo "$(BLUE)Running security checks...$(NC)"
	$(PYTHON) -m safety check
	cd frontend && $(NPM) audit

## Show this help message
help:
	@echo "$(BLUE)JARVIS Development Commands$(NC)"
	@echo ""
	@grep -E '^## .*$$' $(MAKEFILE_LIST) | sed 's/^## /$(GREEN)/' | sed 's/$$/$(NC)/'
	@echo ""
	@echo "$(YELLOW)Usage:$(NC) make <command>"
