# CLAUDE.md — working constitution for this repo

This repo is an **audit submission**. It is graded on defensibility, not volume.
Unverified claims score negative. Fabricated evidence is an automatic fail.
Every rule below exists to make that impossible by construction.

---

## 1. Hard rules (never violate)

1. **The evidence rule.** Never write the words "bug", "flaw", "wrong",
   "misleading" or "slower/faster" about anything in `starter_kit/` unless a
   runnable experiment in this repo measures its effect. No measurement = do
   not mention it in any deliverable. Park it in `NOTEBOOK.md` under
   `## Unverified hypotheses` instead.
2. **`starter_kit/` is read-only.** Never edit, move, reformat or "fix" it.
   Copy into `src/audit/ablation/legacy.py` to modify.
3. **No number is ever typed into prose.** All figures in `deliverable/**.md`
   are rendered from `results/*.json` via `src/audit/reporting/render.py`.
   If you find yourself writing a digit inside a markdown template, stop —
   emit a `{{ placeholder }}` and populate it from a results artifact.
4. **`make reproduce` must regenerate every artifact from scratch**, offline,
   deterministically, on a clean checkout with only the corpus cache present.
5. **Log to `NOTEBOOK.md` at the end of every session**: hypothesis, what was
   run, what came back, what I now believe, what died. Dead ends are graded
   content — never delete them, never tidy them into a clean narrative.
6. **Interpretation is human-authored.** You may generate code, tables,
   figures and schemas. You may not author any sentence that asserts a
   conclusion, ranks a cause, or recommends an action. Draft those as
   `TODO(pratik): interpretation` and stop.

---

## 2. Determinism & environment

- Python 3.11. Dependencies pinned in `pyproject.toml` with exact versions.
- `PYTHONHASHSEED=0`; every RNG seeded from `config.SEED`; bootstrap uses an
  explicit `numpy.random.Generator`, never global state.
- **Network only in `make corpus`.** Analysis code must never hit the network.
  Corpus and tokenizer files are fetched once into `.cache/`, checksummed, and
  read from disk thereafter. A missing cache is a hard error with a clear
  message, never a silent re-download.
- Every results JSON carries a `provenance` block: git SHA, UTC timestamp,
  python version, package versions, config hash, input file checksums.

---

## 3. Code standards

- Full type annotations. `mypy --strict` clean. `ruff` clean.
- **Pure functions in `metrics/` and `bench/`** — inputs in, values out, no I/O,
  no globals, no printing. I/O lives only in `cli.py`, `corpus/`, `reporting/`.
- Configuration is a frozen dataclass, never module-level mutable state.
- One CLI entrypoint (`python -m audit`), subcommands per stage. Every stage is
  independently runnable and idempotent.
- Errors are explicit exceptions with actionable messages. Never `except:
  pass`. Never silently truncate, coerce, or drop rows — if parallel corpora
  misalign, raise.
- Docstrings state *what is held constant* for any metric function. That single
  habit is the core intellectual content of Part A.
- No file over ~250 lines. No function over ~40. If a function needs a comment
  explaining a block, that block is a function.

---

## 4. Testing contract

`tests/` is not optional — it is the defense rehearsal.

- `test_legacy_parity.py` — **the keystone.** With all ablation flags OFF, the
  reimplementation must reproduce the original `fertility.py` output exactly on
  `starter_kit/corpus_sample/`. Until this passes, no ablation result is
  admissible. This is what proves the deltas measure the flaw and not a
  rewrite artifact.
- `test_counters.py` — golden cases for word / grapheme / byte / codepoint
  counts on hand-checked Devanagari, Kannada, Tamil, Telugu, Bengali strings
  including combining marks, ZWJ, ZWNJ and a virama sequence.
- `test_aggregation.py` — micro vs macro averaging differ on a constructed
  example with known values; bootstrap CI covers the true mean on a synthetic
  distribution.
- `test_kv_math.py` — KV arithmetic against a hand-worked example; an explicit
  MHA-vs-GQA case proving the group ratio is applied.
- `test_reproducibility.py` — running a stage twice yields byte-identical JSON
  apart from the timestamp field.
- Edge-case fixtures: empty line, whitespace-only line, mixed-script line,
  emoji, a line of pure punctuation. These are what the grader will paste.

---

## 5. Architecture contract

Data flows one direction; never skip a layer.

```
config → corpus (load, validate, normalize)
       → tokenizers (adapter protocol, one class per backend)
       → metrics (pure counting + pure aggregation)
       → ablation (flag-toggled legacy reimplementation)
       → results/*.json
       → reporting (tables, figures, markdown rendering)
       → deliverable/
```

- `TokenizerAdapter` is a `Protocol` with `encode(text) -> list[int]`,
  `name`, `vocab_size`, and `counts_special_tokens: bool`. Adding a tokenizer
  must never require touching `metrics/`.
- Ablation flags are a frozen dataclass of booleans, one per *independently
  measurable* claim. The runner sweeps: all-off baseline, each flag alone, and
  all-on. That grid is the evidence table.
- `bench/spec.py` parses `model_spec.md` into a dataclass. **Never hardcode a
  spec value** — B1 must be derived from the file so it survives a grader
  editing the spec live.

---

## 6. Deliverable conventions

Every claim in `deliverable/partA/FINDINGS.md` uses this exact block:

```markdown
### F-03 — <one-line claim>

**Category:** code bug | conceptual | rejected
**Command:** `python -m audit ablate --flag fix_special_tokens`
**Before → after:** 1.842 → 1.671 tokens/word (Hindi, micro-avg)
**Direction & magnitude:** overstates Hindi fertility by +10.2% relative;
effect scales inversely with sentence length.
**Why the delta proves it:** the only change between runs is <X>; all other
inputs, seeds and code paths are identical.
```

Same shape every time, numbered `F-01…F-NN`, including a **`## Claims
investigated and rejected`** section with null results shown at the same level
of rigour. Rejected claims are worth points — they are the proof of method.

---

## 7. Session hygiene

- One phase per session, fresh context. Long sessions compound hallucination.
- Start each session by reading `NOTEBOOK.md` tail and `results/` index.
- End each session by appending to `NOTEBOOK.md` and to `AI_USAGE.md` if
  anything you produced turned out to be wrong — that entry is graded content.
- If uncertain whether something is a real flaw: build the experiment, don't
  assert. If the experiment is impractical, say so in the notebook and move on.
