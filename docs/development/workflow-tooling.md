# Tooling Workflow

## Scope

This document defines the required tooling workflow for local development commands in this repository.

## When To Read This Doc

Read this document when:

- running tests
- running one-off scripts
- installing dependencies
- choosing how to invoke Python tooling in this repository

## Rules

- Use Poetry as the command entry point for this repository.
- Run project commands with `poetry run ...` instead of invoking the project virtualenv directly.
- Do not use `./.venv/bin/...` command paths in this repository unless the user explicitly asks for that form.
- Use `poetry install` to prepare the environment when dependencies are missing.
- When documenting commands for this repository, prefer Poetry-based examples.

## Examples

- `poetry run pytest`
- `poetry run pytest tests/unit/application/test_property_management.py`
- `poetry run python main.py`

## Related Files

- `pyproject.toml`
- `AGENTS.md`
- `docs/README.md`
