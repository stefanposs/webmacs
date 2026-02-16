# Contributing

Contributions to WebMACS are welcome. Here is how to get involved.

---

## Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/stefanposs/webmacs.git
cd webmacs
```

### 2. Install dependencies

```bash
# Backend
cd backend && uv sync --all-extras && cd ..

# Controller
cd controller && uv sync --all-extras && cd ..

# Frontend
cd frontend && npm install && cd ..
```

### 3. Verify installation

```bash
just test       # Run all tests
just lint       # Check code style
```

---

## Development Workflow

### Available Commands

All commands use [just](https://github.com/casey/just) (a modern `make` alternative).

```bash
# Setup
just setup              # Install all dependencies (backend + controller + plugins + frontend)
just setup-backend      # Install backend dependencies only
just setup-controller   # Install controller dependencies only
just setup-frontend     # Install frontend dependencies only

# Code quality
just lint               # Run all linters (backend + controller + plugins + frontend)
just lint-backend       # Lint backend + controller + plugins with ruff
just lint-frontend      # Lint frontend with ESLint
just lint-fix           # Auto-fix Python lint issues
just format             # Auto-format Python code
just fix                # Format + lint-fix

# Type checking
just typecheck          # Type check Python (backend + controller) with mypy
just typecheck-frontend # Type check frontend with vue-tsc

# Testing
just test               # Run all tests (backend + controller + plugins + frontend)
just test-backend       # Backend tests only
just test-backend-cov   # Backend tests with coverage report
just test-controller    # Controller tests only
just test-frontend      # Frontend tests only
just test-frontend-cov  # Frontend tests with coverage report
just test-plugins       # Run all plugin tests
just test-plugin <name> # Run tests for a specific plugin
just test-example-plugin # Run example plugin tests (validates SDK contract)

# CI / QA
just qa                 # Full QA pipeline: lint + typecheck + all tests
just check              # Quick check before commit
just ci                 # Simulate full CI pipeline locally (mirrors GitHub Actions)
just ci-cov             # Full CI with coverage reports
just ci-quick           # Quick CI (lint + test, skip typecheck)

# Docker
just dev                # Start full Docker stack (detached)
just down               # Stop all containers
just down-clean         # Stop and remove all data (volumes)
just rebuild            # Rebuild and restart all containers
just restart <service>  # Restart a single service
just status             # Check service health
just logs <service>     # View logs (follow mode)

# Database
just db-shell           # Open psql shell
just db-backup          # Create database backup

# Documentation
just docs               # Serve docs locally (http://localhost:8001)
just docs-build         # Build static docs

# Release
just bundle <version>   # Build OTA update bundle for customer deployment

# Utilities
just info               # Show project info
just loc                # Count lines of code
just clean              # Clean build artifacts
```

---

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Production-ready code |
| `develop` | Integration branch |
| `feature/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation updates |

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Purpose |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `test:` | Tests |
| `refactor:` | Code refactoring |
| `perf:` | Performance improvements |
| `ci:` | CI/CD changes |
| `chore:` | Maintenance |

---

## Pull Request Process

### 1. Create feature branch

```bash
git checkout -b feature/my-awesome-feature
```

### 2. Make changes

- Write tests for new functionality
- Ensure `just qa` passes
- Update documentation if needed

### 3. Push and open PR

```bash
git push origin feature/my-awesome-feature
```

Open a PR against `develop` (or `main` for hotfixes).

### 4. Code review

- At least one approval required
- CI must pass
- No merge conflicts

---

## CI/CD Pipeline

GitHub Actions runs on every push:

- **Python**: Ruff linting, mypy type checking, pytest with coverage
- **Frontend**: ESLint, vue-tsc type checking, Vite build, vitest
- **Matrix**: Backend + Controller tested separately
- **Services**: PostgreSQL 17 for integration tests

---

## Release Process

1. Merge to `main`
2. Tag version: `git tag v2.x.x`
3. Push tags: `git push --tags`
4. Docker images rebuilt automatically

---

## Questions?

Open a [GitHub Issue](https://github.com/stefanposs/webmacs/issues).
