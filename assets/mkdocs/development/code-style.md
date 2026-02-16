# Code Style

WebMACS enforces consistent code style across all components.

---

## Python (Backend & Controller)

### Formatter & Linter: Ruff

[Ruff](https://docs.astral.sh/ruff/) handles both formatting and linting:

```toml
# pyproject.toml
[tool.ruff]
target-version = "py313"
line-length = 120

[tool.ruff.lint]
select = [
    "E", "F", "W",     # pycodestyle, pyflakes
    "I",                # isort
    "N",                # pep8-naming
    "UP",               # pyupgrade
    "S",                # bandit (security)
    "B",                # bugbear
    "A",                # builtins
    "C4",               # comprehensions
    "DTZ",              # datetime timezone
    "T20",              # print statements
    "PT",               # pytest style
    "SIM",              # simplify
    "TID",              # tidy imports
    "TCH",              # type checking
    "ARG",              # unused arguments
    "PL",               # pylint
    "TRY",              # tryceratops
    "PERF",             # performance
    "RUF",              # ruff-specific
]
ignore = ["S101", "TRY003", "PLR0913"]
```

### Type Checking: mypy

```toml
[tool.mypy]
python_version = "3.13"
strict = true
disallow_untyped_defs = true
```

### Commands

```bash
just lint       # ruff check + format check
just format     # ruff format (auto-fix)
just fix        # format + lint-fix
```

---

## TypeScript (Frontend)

### Linter: ESLint

The frontend uses ESLint with Vue and TypeScript rules:

```bash
npm run lint        # Check
npm run lint:fix    # Auto-fix
```

### Type Checking: vue-tsc

```bash
npm run type-check
```

---

## Conventions

### Python

- **Imports**: Sorted by `isort` (via Ruff). First-party packages: `webmacs_backend`, `webmacs_controller`
- **Docstrings**: Google style
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Type hints**: Required on all public functions (mypy strict mode)
- **Async**: Use `async def` for all I/O-bound operations

### TypeScript

- **Naming**: `camelCase` for variables/functions, `PascalCase` for components/types
- **Composition API**: `<script setup lang="ts">` for all components
- **Types**: Explicit interfaces in `types/` directory
- **Imports**: Absolute paths from `@/` alias

### Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/) — see [Contributing](contributing.md#commit-messages).

---

## Pre-Commit Checks

Run before every commit:

```bash
just check      # lint + type-check + test
```

Or integrate with git hooks:

```bash
# .pre-commit-config.yaml support planned
```

---

## Next Steps

- [Contributing](contributing.md) — full development workflow
- [Testing](testing.md) — test structure and patterns
