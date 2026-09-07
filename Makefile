# Every artefact in this repo is produced by one of these targets.
# If a number in deliverable/ cannot be traced to a target here, it does not
# belong in the submission.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# Determinism (CLAUDE.md 2). PYTHONHASHSEED=0 is set for every target, not
# just the analysis ones, so a test can never pass under a hash seed that the
# pipeline would not use.
export PYTHONHASHSEED := 0
export PYTHONDONTWRITEBYTECODE := 1

# Offline enforcement for every stage except `corpus`. Set as environment
# rather than as a code default so that a stage which tries to reach the
# network fails loudly instead of quietly succeeding on a warm cache.
OFFLINE_ENV := HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1

UV      := uv
PY      := $(UV) run --frozen python
RUN     := $(UV) run --frozen
AUDIT   := $(OFFLINE_ENV) $(PY) -m audit

.PHONY: help setup corpus prepare check lint types test parity ablate analyze \
	bench partc render reproduce adversarial clean tree

help:  ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- environment

setup:  ## Create the venv and install pinned deps (Python 3.11)
	$(UV) python install 3.11
	$(UV) sync --frozen --all-groups
	@echo "ok: run 'make check'"

# ------------------------------------------------------------- network stage

corpus:  ## NETWORK. Fetch FLORES-200 + tokenizers -> .cache/, checksummed
	@echo ">> the only target permitted to use the network"
	$(PY) -m audit corpus

prepare:  ## Offline. Validate alignment -> results/corpus_stats.json
	$(AUDIT) prepare

# ------------------------------------------------------------------- quality

check: lint types test  ## ruff + mypy --strict + pytest

lint:  ## ruff check + format check
	$(RUN) ruff check src tests
	$(RUN) ruff format --check src tests

types:  ## mypy --strict
	$(RUN) mypy

test:  ## pytest
	$(OFFLINE_ENV) $(RUN) pytest

parity:  ## THE GATE. Legacy-parity test alone; must pass before any ablation
	$(OFFLINE_ENV) $(RUN) pytest -m parity -v

# ---------------------------------------------------------------- pipeline

ablate: parity  ## Flag sweep -> results/ablation.json  (gated on parity)
	$(AUDIT) ablate

analyze:  ## Corrected multi-tokenizer analysis -> results/analysis.json
	$(AUDIT) analyze

bench:  ## Spec parse + KV math + log analysis -> results/bench.json
	$(AUDIT) bench

partc:  ## Part C envelope arithmetic -> results/partc.json
	$(AUDIT) partc

render:  ## results/*.json + templates -> deliverable/
	$(AUDIT) render

adversarial:  ## Run tests/fixtures/adversarial/* through the pipeline
	$(AUDIT) adversarial

reproduce: check prepare ablate analyze bench partc adversarial render  ## Offline end-to-end rebuild
	@echo ""
	@echo "reproduce: complete. Every file under results/ and deliverable/ was"
	@echo "regenerated offline from starter_kit/ plus the .cache/ corpus."

# ------------------------------------------------------------------ utility

tree:  ## Print the source tree (starter_kit excluded; it is read-only)
	@find src tests templates -type f -name '*.py' -o -type f -name '*.j2' \
	  | sort

clean:  ## Remove generated artefacts. Never touches .cache/ or starter_kit/
	rm -rf results/*.json deliverable/partA/*.md deliverable/partB/*.md \
	       deliverable/figures .mypy_cache .ruff_cache .pytest_cache
	find src tests -name '__pycache__' -type d -exec rm -rf {} +
