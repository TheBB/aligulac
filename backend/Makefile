# Linting targets

.PHONY: format
format:
	uv run ruff format

.PHONY: lint
lint:
	uv run ruff check --fix

.PHONY: ruff
ruff: format lint


# Test targets

.PHONY: pytest
pytest:
	uv run pytest

.PHONY: mypy
mypy:
	uv run mypy

.PHONY: ruff-verify
ruff-verify:
	uv run ruff check
	uv run ruff format --check

.PHONY: test
test: pytest mypy ruff-verify
