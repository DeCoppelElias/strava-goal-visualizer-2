.PHONY: help install install-dev lint format format-check typecheck test pre-commit-install pre-commit-run ci clean

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
	$(UV) sync --group backend
	cd frontend && npm install

install-dev: ## Install all dependencies including dev tooling
	$(UV) sync --group backend --group dev
	cd frontend && npm install
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
	$(UV) run ruff check .

format: ## Run ruff formatter
	$(UV) run ruff format .

format-check: ## Check formatting without writing changes (used in CI)
	$(UV) run ruff format --check .

typecheck: ## Run mypy static type checking
	$(UV) run mypy backend frontend

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
test: ## Run full test suite with coverage
	$(UV) run pytest

# ---------------------------------------------------------------------------
# CI target — mirrors what GitHub Actions runs
# ---------------------------------------------------------------------------
ci: pre-commit-run lint format-check typecheck ## Run full CI suite locally

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove build artifacts, caches, coverage reports
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache  -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml
