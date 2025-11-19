# Dev targets

.PHONY: schema
schema:
	node_modules/.bin/json2ts ../backend/schema.json -o components/models.ts --unreachableDefinitions


# Linting targets

.PHONY: format
format:
	npm run format

.PHONY: lint
lint:
	npm run lint


# Test targets

.PHONY: lint-verify
lint-verify:
	npm run check

.PHONY: build
build:
	npm run build
