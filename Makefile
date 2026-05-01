.PHONY: help install install-dev lint format typecheck test test-unit test-integration \
        security pre-commit-install pre-commit-run clean

PYTHON := python
UV     := uv

# ---------------------------------------------------------------------------
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
install: ## Install all runtime dependencies (backend + frontend)
	$(UV) sync --group backend --group frontend

install-dev: ## Install all dependencies including dev tooling
	$(UV) sync --group backend --group frontend --group dev
	$(MAKE) pre-commit-install

# ---------------------------------------------------------------------------
# Pre-commit
# ---------------------------------------------------------------------------
pre-commit-install: ## Install git hooks via pre-commit
	$(UV) run pre-commit install --hook-type pre-commit --hook-type commit-msg

pre-commit-run: ## Run all pre-commit hooks against all files
	$(UV) run pre-commit run --all-files

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------
lint: ## Run ruff linter
	$(UV) run ruff check backend frontend tests

format: ## Run ruff formatter
	$(UV) run ruff format backend frontend tests

format-check: ## Check formatting without writing changes (used in CI)
	$(UV) run ruff format --check backend frontend tests

typecheck: ## Run mypy static type checking
	$(UV) run mypy backend frontend

security: ## Run bandit security scanner
	$(UV) run bandit -c pyproject.toml -r backend frontend

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
test: ## Run full test suite with coverage
	$(UV) run pytest

test-unit: ## Run only unit tests (no I/O)
	$(UV) run pytest tests/unit -v

test-integration: ## Run only integration tests
	$(UV) run pytest tests/integration -v

test-fast: ## Run tests, stop on first failure
	$(UV) run pytest -x

# ---------------------------------------------------------------------------
# CI target — mirrors what GitHub Actions runs
# ---------------------------------------------------------------------------
ci: lint format-check typecheck security test ## Run full CI suite locally

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove build artifacts, caches, coverage reports
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache  -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml
