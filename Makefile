.PHONY: help up down logs test lint format clean setup install dev

help:
	@echo "ELIOT Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initialize development environment"
	@echo "  make install        - Install Python dependencies locally"
	@echo "  make dev            - Run core service locally (no Docker)"
	@echo ""
	@echo "Running:"
	@echo "  make up             - Start all services (docker-compose up -d)"
	@echo "  make down           - Stop all services (docker-compose down)"
	@echo "  make logs           - View all service logs"
	@echo ""
	@echo "Development:"
	@echo "  make test           - Run test suite"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make lint           - Run linting checks"
	@echo "  make format         - Format code with black"
	@echo "  make type-check     - Run mypy type checking"
	@echo ""
	@echo "Cleaning:"
	@echo "  make clean          - Remove pycache, .pytest_cache, etc."
	@echo "  make clean-docker   - Remove containers and volumes"
	@echo ""
	@echo "Utilities:"
	@echo "  make health         - Check service health"
	@echo "  make shell          - Open core container shell"
	@echo "  make redis-cli      - Connect to Redis CLI"
	@echo "  make agents-test    - Test agent chat via API"
	@echo "  make tools-list     - List available tools via API"
	@echo "  make kb-ingest      - Ingest docs/ into knowledge base"

setup:
	@echo "Setting up ELIOT development environment..."
	cp .env.example .env
	mkdir -p security data data/vectordb logs models
	docker-compose build
	@echo "Setup complete. Run 'make up' to start services."

install:
	pip install -r requirements.txt
	@echo "Dependencies installed."

dev:
	uvicorn core.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker-compose up -d
	@echo "Services started. Check health with: make health"

down:
	docker-compose down
	@echo "Services stopped."

logs:
	docker-compose logs -f

test:
	python -m pytest tests/ -v

test-coverage:
	python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term

lint:
	flake8 core/ agents/ knowledge/ tools/ security/ hardware/ voice/ vision/ avatar/ ui/ tests/ --max-line-length=127 --exclude=__pycache__

format:
	black core/ agents/ knowledge/ tools/ security/ hardware/ voice/ vision/ avatar/ ui/ tests/ --line-length=127

type-check:
	mypy core/ agents/ knowledge/ tools/ voice/ vision/ avatar/ --ignore-missing-imports || true

health:
	@echo "Health check..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Service not responding"

agents-test:
	@echo "Testing agent chat..."
	@curl -s -X POST http://localhost:8000/agents/chat \
		-H "Content-Type: application/json" \
		-d '{"message": "create a plan for network reconnaissance"}' | python -m json.tool

tools-list:
	@curl -s http://localhost:8000/tools/ | python -m json.tool

kb-ingest:
	@curl -s -X POST "http://localhost:8000/knowledge/ingest/directory?path=docs" | python -m json.tool

shell:
	docker-compose exec core /bin/bash

redis-cli:
	docker-compose exec redis redis-cli

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type d -name .pytest_cache -exec rm -rf {} + || true
	find . -type f -name .coverage -delete
	rm -rf htmlcov/
	@echo "Cleaned up Python cache files."

clean-docker:
	docker-compose down -v
	@echo "Removed containers and volumes."

clean-all: clean clean-docker
	@echo "Complete cleanup done."
