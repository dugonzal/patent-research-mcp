# Contributing

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
make install
```

Pre-commit hooks (optional but recommended):

```bash
pip install pre-commit
pre-commit install
```

## Commands

| Command | Description |
|---------|-------------|
| `make test` | Run unit tests |
| `make test-all` | Run all tests (including e2e) |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Ruff lint check |
| `make format` | Auto-format with ruff |
| `make format-check` | Check formatting without writing |
| `make typecheck` | Mypy static type check |
| `make build` | Build the package |
| `make clean` | Remove build/cache artifacts |

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `style`, `ci`, `chore`, `perf`.

Examples:
- `feat: add cross-patent entity comparison`
- `fix: handle empty claims sections gracefully`
- `test: add resilience tests for DOM mutation fallback`
- `docs: update README with plugin system example`

## Branch Naming

```
<type>/<short-slug>
```

Examples: `feat/cross-pattern-comparison`, `fix/empty-claims`, `docs/plugin-example`.

## Pull Request Process

1. Ensure tests pass: `make test && make lint && make typecheck`
2. Write a clear PR description referencing any related issues
3. Keep changes focused — one logical change per PR
4. Update CHANGELOG.md if the change is user-facing
