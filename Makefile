# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# Thin convenience wrappers around the Nix flake. Everything runs inside
# `nix develop` so the toolchain is reproducible.

NIX ?= nix
DEV = $(NIX) develop --command

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: run
run: ## Launch the geocog TUI
	$(NIX) run .#geocog

.PHONY: test
test: ## Run the test suite
	$(DEV) pytest

.PHONY: lint
lint: ## Ruff lint + format check, REUSE licence lint, secret scan
	$(DEV) ruff check .
	$(DEV) ruff format --check .
	$(DEV) reuse lint
	$(DEV) gitleaks detect --no-banner --redact --source .

.PHONY: format
format: ## Auto-format with Ruff
	$(DEV) ruff format .
	$(DEV) ruff check --fix .

.PHONY: precommit
precommit: ## Run all pre-commit hooks
	$(DEV) pre-commit run --all-files

.PHONY: docs
docs: ## Serve the docs site locally
	$(NIX) run .#docs

.PHONY: docs-build
docs-build: ## Build the static docs site (strict)
	$(DEV) mkdocs build --strict

.PHONY: docs-pdf
docs-pdf: ## Build the docs, including the combined PDF (needs the `docs` pip extra)
	ENABLE_PDF_EXPORT=1 mkdocs build --strict

.PHONY: build
build: ## Build the geocog package (runs tests in the nix sandbox)
	$(NIX) build .#geocog -L

.PHONY: sbom
sbom: ## Generate a CycloneDX SBOM
	$(DEV) sh -c 'pip install cyclonedx-bom >/dev/null 2>&1; cyclonedx-py environment -o geocog-sbom.json --output-format JSON'

.PHONY: clean
clean: ## Remove build/test artifacts
	rm -rf result result-* dist build site *.egg-info \
	  .pytest_cache **/__pycache__ geocog-sbom.json
