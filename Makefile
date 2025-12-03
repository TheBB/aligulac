# Dev targets

.PHONY: dev
dev:
	foreman start -f dev.procfile

.PHONY: schema
schema:
	make -C backend schema
	make -C frontend schema


# Linting targets

.PHONY: format
format:
	make -C backend format
	make -C frontend format

.PHONY: lint
lint:
	make -C backend lint
	make -C frontend lint


# Test targets

.PHONY: lint-verify
lint-verify:
	make -C backend ruff-verify
	make -C frontend lint-verify

.PHONY:	types
types:
	make -C backend mypy
	make -C frontend build

.PHONY: tests
tests:
	make -C backend pytest

.PHONY: test
test: tests types lint-verify
