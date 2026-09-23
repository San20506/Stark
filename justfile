# STARK task runner (replaces Makefile).
# Install: sudo pacman -S just
# Single source of truth: all recipes run inside .venv (system python is 3.14
# and lacks yaml/pytest). Run `just install-dev` once to populate .venv.
venv_bin := ".venv/bin"

# Show available recipes
default:
    @just --list

# Run ruff linter
lint:
    {{venv_bin}}/ruff check .

# Run ruff formatter
format:
    {{venv_bin}}/ruff format .

# Check formatting without changes
format-check:
    {{venv_bin}}/ruff format --check .

# Run tests with coverage
test:
    {{venv_bin}}/python -m pytest tests/ -v --tb=short --cov=core --cov=memory

# Run mypy type checker
typecheck:
    {{venv_bin}}/mypy core/ memory/ agents/ --ignore-missing-imports

# Run bandit security scan
security:
    {{venv_bin}}/bandit -c pyproject.toml -r core/ memory/ agents/

# Run all checks (lint + format + security)
check: lint format-check security

# Clean build artifacts
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    rm -rf .ruff_cache mypy_cache .pytest_cache .coverage coverage.xml

# Run DB maintenance
maintenance:
    {{venv_bin}}/python scripts/db_maintenance.py

# Install dev dependencies
install-dev:
    {{venv_bin}}/pip install -e ".[dev]"
    {{venv_bin}}/pre-commit install

# Full project setup
setup: install-dev
    @echo "Run 'just check' to verify everything works"
