# Contributing

Contributions to WebMACS are welcome. Here is how to get involved.

---

## Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/stefanposs/webmacs.git
cd webmacs/v2
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

```bash
# Setup
just setup              # Install all dependencies

# Code quality
just lint               # Run ruff linter on backend + controller
just format             # Auto-format code
just fix                # Format + lint-fix

# Testing
just test               # Run all tests (backend + controller + frontend)
just test-backend       # Backend tests only
just test-controller    # Controller tests only
just test-frontend      # Frontend tests only

# Docker
just dev                # Start full Docker stack
just down               # Stop all containers
just rebuild            # Rebuild and restart

# Documentation
just docs               # Serve docs locally (http://localhost:8001)
just docs-build         # Build static docs

# Quality
just qa                 # Full QA: lint + format-check + test
just check              # Quick check before commit
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
