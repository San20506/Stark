.PHONY: help lint format test typecheck security check clean maintenance

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

lint:  ## Run ruff linter
	ruff check .

format:  ## Run ruff formatter
	ruff format .

format-check:  ## Check formatting without changes
	ruff format --check .

test:  ## Run tests with coverage
	pytest tests/ -v --tb=short --cov=core --cov=memory

typecheck:  ## Run mypy type checker
	mypy core/ memory/ agents/ --ignore-missing-imports

security:  ## Run bandit security scan
	bandit -c pyproject.toml -r core/ memory/ agents/

check: lint format-check security  ## Run all checks (lint + format + security)

clean:  ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .ruff_cache mypy_cache .pytest_cache .coverage coverage.xml

maintenance:  ## Run DB maintenance
	python scripts/db_maintenance.py

install-dev:  ## Install dev dependencies
	pip install -e ".[dev]"
	pre-commit install

setup: install-dev  ## Full project setup
	@echo "Run 'make check' to verify everything works"
