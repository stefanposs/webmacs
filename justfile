# WebMACS Development Commands
# Install just: https://github.com/casey/just

# Default recipe — show available commands
default:
    @just --list

# ============================================================================
# Setup & Installation
# ============================================================================

# Install all dependencies (backend + controller + frontend)
setup:
    cd backend && uv sync --all-extras
    cd controller && uv sync --all-extras
    cd frontend && npm install
    @echo "✅ All dependencies installed!"

# Install backend dependencies
setup-backend:
    cd backend && uv sync --all-extras

# Install controller dependencies
setup-controller:
    cd controller && uv sync --all-extras

# Install frontend dependencies
setup-frontend:
    cd frontend && npm install

# ============================================================================
# Testing
# ============================================================================

# Run all tests (backend + controller + frontend)
test: test-backend test-controller test-frontend
    @echo "✅ All tests passed!"

# Run backend tests
test-backend:
    cd backend && uv run pytest tests/ -v

# Run backend tests with coverage
test-backend-cov:
    cd backend && uv run pytest tests/ -v --cov --cov-report=term-missing
    @echo "📊 Coverage report generated"

# Run controller tests
test-controller:
    cd controller && uv run pytest tests/ -v

# Run frontend tests
test-frontend:
    cd frontend && npm run test -- --run

# ============================================================================
# Code Quality
# ============================================================================

# Run all linters
lint: lint-backend lint-frontend
    @echo "✅ All linting passed!"

# Lint backend + controller with ruff
lint-backend:
    uv run ruff check backend/src/ controller/src/
    uv run ruff format --check backend/src/ controller/src/

# Lint frontend with ESLint
lint-frontend:
    cd frontend && npm run lint

# Auto-format Python code
format:
    uv run ruff format backend/src/ controller/src/
    @echo "✅ Python code formatted!"

# Auto-fix Python lint issues
lint-fix:
    uv run ruff check --fix backend/src/ controller/src/

# Format + lint-fix
fix: format lint-fix
    @echo "✅ Code formatted and linted!"

# Type check Python
typecheck:
    cd backend && uv run mypy src/
    cd controller && uv run mypy src/

# Type check frontend
typecheck-frontend:
    cd frontend && npm run type-check

# Full QA pipeline (lint + typecheck + test)
qa: lint typecheck test
    @echo "✅ All QA checks passed!"

# Quick check before commit
check: lint typecheck
    @echo "✅ Ready to commit!"

# ============================================================================
# Docker
# ============================================================================

# Start all services (detached)
dev:
    docker compose up -d
    @echo "✅ Stack running — http://localhost"

# Start with rebuild
rebuild:
    docker compose up --build -d
    @echo "✅ Rebuilt and running — http://localhost"

# Stop all services
down:
    docker compose down

# Stop and remove data
down-clean:
    docker compose down -v
    @echo "⚠️  Volumes removed — database deleted"

# View logs (follow)
logs service="backend":
    docker compose logs -f {{service}}

# Check service health
status:
    docker compose ps

# Restart a single service
restart service:
    docker compose restart {{service}}

# Build OTA update bundle for customer deployment
bundle version:
    ./scripts/build-update-bundle.sh {{version}}

# ============================================================================
# Documentation
# ============================================================================

# Serve documentation locally (http://localhost:8001)
docs:
    mkdocs serve -a localhost:8001

# Build documentation
docs-build:
    mkdocs build

# ============================================================================
# Database
# ============================================================================

# Create database backup
db-backup:
    docker compose exec -T db pg_dump -U webmacs webmacs > backup_$(date +%Y%m%d_%H%M%S).sql
    @echo "✅ Backup created"

# Open psql shell
db-shell:
    docker compose exec db psql -U webmacs webmacs

# ============================================================================
# Utility
# ============================================================================

# Clean build artifacts
clean:
    rm -rf backend/dist/ controller/dist/ frontend/dist/
    rm -rf .pytest_cache .ruff_cache htmlcov
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @echo "✅ Cleaned build artifacts"

# Show project info
info:
    @echo "Project: WebMACS"
    @grep '^version' pyproject.toml | head -1 | cut -d'"' -f2 | xargs -I{} echo "Version: {}"
    @echo "Backend:    backend/src/webmacs_backend"
    @echo "Controller: controller/src/webmacs_controller"
    @echo "Frontend:   frontend/src"
    @echo ""
    @docker compose ps 2>/dev/null || echo "(Docker not running)"

# Count lines of code
loc:
    @echo "Python (backend):"
    @find backend/src -name '*.py' | xargs wc -l 2>/dev/null | tail -1
    @echo "Python (controller):"
    @find controller/src -name '*.py' | xargs wc -l 2>/dev/null | tail -1
    @echo "TypeScript (frontend):"
    @find frontend/src -name '*.ts' -o -name '*.vue' | xargs wc -l 2>/dev/null | tail -1
    @echo "Documentation:"
    @find assets/mkdocs -name '*.md' | xargs wc -l 2>/dev/null | tail -1

# ============================================================================
# CI Simulation
# ============================================================================

# Simulate full CI pipeline locally
ci: clean lint typecheck test
    @echo "✅ CI simulation complete!"

# Quick CI (lint + test, skip typecheck)
ci-quick: lint test
    @echo "✅ Quick CI done!"
