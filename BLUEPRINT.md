# Execution blueprint — The Audit

Read `CLAUDE.md` first; it is the constitution. This file is the sequence.

---

## 0. Repo layout

```
audit/
├── CLAUDE.md
├── README.md                    # what this is, how to run, 10 lines
├── Makefile
├── pyproject.toml               # pinned deps, ruff/mypy/pytest config
├── NOTEBOOK.md                  # chronological, timestamped, includes failures
├── AI_USAGE.md
├── starter_kit/                 # vendored verbatim, READ-ONLY
│   ├── fertility.py
│   ├── REPORT_v0.md
│   ├── corpus_sample/
│   └── bench/
├── src/audit/
│   ├── __init__.py
│   ├── __main__.py              # python -m audit
│   ├── cli.py                   # subcommands: corpus, ablate, analyze, bench, render, reproduce
│   ├── config.py                # frozen dataclass: paths, SEED, languages, tokenizer ids
│   ├── provenance.py            # git sha, checksums, versions → every JSON
│   ├── corpus/
│   │   ├── schema.py            # ParallelRecord, CorpusStats
│   │   ├── acquire.py           # FLORES-200 fetch → .cache/, checksummed
│   │   └── prepare.py           # alignment validation, NFC/NFD variants
│   ├── tokenizers/
│   │   ├── base.py              # TokenizerAdapter Protocol
│   │   ├── hf.py
│   │   ├── tiktoken.py
│   │   └── registry.py
│   ├── metrics/
│   │   ├── counters.py          # words | graphemes | bytes | codepoints | sentences
│   │   ├── fertility.py         # ratio computation per denominator
│   │   └── aggregation.py       # micro, macro, bootstrap CI
│   ├── ablation/
│   │   ├── flags.py             # AblationFlags frozen dataclass
│   │   ├── legacy.py            # faithful reimplementation + toggles
│   │   └── runner.py            # sweep: baseline, each-alone, all-on
│   ├── bench/
│   │   ├── spec.py              # parse model_spec.md → ModelSpec
│   │   ├── kv_math.py           # GQA-aware KV bytes, concurrency ceiling
│   │   └── log_analysis.py      # goodput (2 derivations), knee detection
│   └── reporting/
│       ├── tables.py            # results JSON → markdown tables
│       ├── figures.py           # matplotlib, deterministic
│       └── render.py            # jinja2: templates + results → deliverable/
├── templates/                   # markdown with {{ placeholders }}, zero digits
│   ├── partA_findings.md.j2
│   ├── partA_memo.md.j2
│   └── partB_answers.md.j2
├── tests/
├── results/                     # generated JSON only, git-tracked
└── deliverable/
    ├── partA/{FINDINGS.md, ANALYSIS.md, MEMO.md, CORPUS.md}
    ├── partB/ANSWERS.md
    └── partC/memo.md
```

**Why this shape wins:** the grader can point at any number in any deliverable
and you can name the JSON key it came from and the command that produced it.

---

## 1. Makefile targets

```make
setup      # venv + pinned install + pre-commit
corpus     # ONLY network stage: fetch FLORES → .cache/, verify checksums
check      # ruff + mypy --strict + pytest
parity     # legacy-parity test alone — gate for all ablation work
ablate     # flag sweep → results/ablation.json
analyze    # corrected multi-tokenizer × multi-denominator → results/analysis.json
bench      # spec parse + KV math + log analysis → results/bench.json
render     # results/*.json + templates → deliverable/
reproduce  # check → ablate → analyze → bench → render   (offline, deterministic)
adversarial# run harness against tests/fixtures/adversarial/* — defense prep
```

---

## 2. The master prompt (paste this first, in a fresh session)

> You are working on a graded technical audit. Read `CLAUDE.md` in full and
> treat it as binding for every subsequent turn.
>
> Context: `starter_kit/` contains `fertility.py`, `REPORT_v0.md`, a tiny
> parallel corpus sample, and a serving benchmark (`bench/model_spec.md`,
> `bench/bench_log.csv`). The submission is an audit of that work. Grading
> punishes unverified claims (−5 each) and fails fabricated evidence. There is
> a live defense where the grader will paste new inputs, add flags, and ask for
> numbers to be re-derived on the spot.
>
> **This session is scaffolding only. Do not analyze, do not diagnose, do not
> claim anything is wrong.**
>
> Build:
> 1. The exact repo tree in `BLUEPRINT.md` §0 with all `__init__.py` files.
> 2. `pyproject.toml` — Python 3.11, exact pins, ruff + mypy strict + pytest
>    config, package under `src/`.
> 3. `Makefile` with the targets in §1. `reproduce` must run offline.
> 4. `src/audit/config.py` — frozen dataclass: `SEED`, paths, target languages
>    (eng, hin, kan, tam, tel, ben, mar), tokenizer registry ids, bootstrap
>    iterations. No mutable module state.
> 5. `src/audit/provenance.py` — a `provenance_block()` returning git SHA, UTC
>    timestamp, python + package versions, config hash, and SHA-256 of every
>    input file. Every results JSON embeds this.
> 6. `src/audit/cli.py` — argparse subcommands matching the Makefile. Each is a
>    thin wrapper; no logic in the CLI.
> 7. `src/audit/tokenizers/base.py` — `TokenizerAdapter` Protocol with
>    `name`, `vocab_size`, `counts_special_tokens`, `encode(text) -> list[int]`,
>    plus `hf.py` and `tiktoken.py` implementations and a `registry.py`.
> 8. Empty `NOTEBOOK.md` and `AI_USAGE.md` with heading skeletons.
>
> Stubs with `NotImplementedError` are fine for `metrics/`, `ablation/`,
> `bench/`, `reporting/`. Make `make check` pass on the skeleton.
>
> Then stop and give me a one-screen summary of what you built and any design
> decision where you had to choose between two reasonable options.

---

## 3. Phase prompts

### Phase 1 — recon (no code, no verdicts)

> Read `starter_kit/fertility.py`, `REPORT_v0.md`, and the corpus sample.
>
> Produce `NOTEBOOK.md` → `## Unverified hypotheses`: a ranked list of things
> that *might* be wrong. For each: (a) one-line description, (b) whether it is
> a code bug, a conceptual/metric problem, or ambiguous, (c) the **specific
> experiment** that would confirm or refute it, (d) your predicted direction of
> distortion, (e) confidence 1–5.
>
> Rules: every item is labelled UNVERIFIED. Do not use the word "bug" as an
> assertion. Include at least two candidates you suspect are *harmless* — the
> assignment states one suspicious-looking thing is actually fine. Do not
> recommend which to pursue; I choose.

**You then pick 4–6 to test.** That selection is your judgment, not the model's.

### Phase 2 — parity gate

> Implement `src/audit/ablation/legacy.py`: a faithful reimplementation of
> `starter_kit/fertility.py` whose behaviour is identical when all
> `AblationFlags` are False. Define the flags dataclass in `flags.py` with one
> boolean per hypothesis I selected: [paste your chosen list].
>
> Each flag must change exactly one thing and be independently togglable.
> Implement `tests/test_legacy_parity.py` proving all-flags-off reproduces the
> original script's output on `starter_kit/corpus_sample/` to full precision.
>
> `make parity` must pass before you write anything else.

### Phase 3 — corpus (A1)

> Implement `corpus/acquire.py` and `corpus/prepare.py`. Fetch FLORES-200
> devtest for eng, hin, kan, tam, tel (+ ben, mar for Part C reuse) into
> `.cache/` with checksum verification. Network only in this stage.
>
> `prepare.py` must: validate line-count alignment across all languages and
> raise on mismatch (never truncate); produce NFC and NFD variants; and emit
> `results/corpus_stats.json` with per-language sentence count, character
> count, byte count, grapheme count, and script distribution.
>
> Also emit a `sample_manifest.json` recording the exact devtest indices used,
> so the corpus is reconstructible without shipping the data.

Then **you** write `deliverable/partA/CORPUS.md` — especially the "what this
corpus cannot tell you" paragraph. Domain narrowness, translationese, no
chat/code/transliterated text, n≈1000 giving tight CIs on means but nothing on
tails.

### Phase 4 — metrics + ablation sweep (A2)

> Implement `metrics/counters.py` (whitespace words, extended grapheme clusters
> via `regex \X`, UTF-8 bytes, codepoints, sentences), `metrics/fertility.py`,
> and `metrics/aggregation.py` (micro, macro, bootstrap CI with seeded
> Generator).
>
> Implement `ablation/runner.py`: sweep baseline → each flag alone → all-on,
> across all corpus languages and both NFC/NFD, writing `results/ablation.json`
> with absolute and relative deltas per flag per language.
>
> Write the golden tests in `CLAUDE.md` §4. Do not write any prose findings.

### Phase 5 — corrected analysis (A3)

> Implement the analysis stage: 2+ tokenizers (one Indic-aware, one
> Western-centric) × 5 languages × 4 denominators (word, grapheme, byte,
> parallel sentence), micro and macro aggregation, bootstrap 95% CIs, all
> ratios normalized to English. Emit `results/analysis.json` + deterministic
> figures.
>
> Produce the tables. Leave every interpretive sentence as
> `TODO(pratik): interpretation`.

**Your job:** the denominator argument. The routing decision needs cost per unit
of *meaning*, and only the parallel sentence holds meaning constant across
languages — "word" varies with morphology, so tokens/word conflates tokenizer
efficiency with agglutination. Bytes and graphemes are diagnostics (byte-fallback,
combining-mark shattering), not decision metrics. Say it with your numbers.

### Phase 6 — Part B

**Do B1 on paper first.** `2 × layers × kv_heads × head_dim × dtype_bytes`,
watching for GQA. Then:

> Implement `bench/spec.py` (parse `model_spec.md` → `ModelSpec`; never
> hardcode), `bench/kv_math.py` (GQA-aware bytes/token, memory budget,
> concurrency ceiling at 4096 ctx, with every intermediate term in the output
> so the arithmetic is auditable), and `bench/log_analysis.py` (parse the CSV,
> compute goodput two independent ways, locate the throughput knee in the
> prompt-3584 sweep, correlate it against the predicted KV ceiling).
>
> Emit `results/bench.json` with each arithmetic step named. Add
> `tests/test_kv_math.py` including an explicit MHA-vs-GQA case.
>
> If my hand calculation and your script disagree, report the disagreement —
> do not reconcile silently.

**Your job:** B3's misread column, and the sentence explaining why one
misreading collapses both of the report's conclusions at once.

### Phase 7 — render + adversarial

> Implement `reporting/render.py` (jinja2) and the templates. Add a validator
> that scans every rendered `deliverable/**.md` for numeric literals not traced
> to a `results/*.json` key, and fails the build listing them.
>
> Build `tests/fixtures/adversarial/`: empty file, whitespace-only line,
> mixed-script line, emoji, pure punctuation, unusual combining marks, a
> ZWJ/ZWNJ sequence, and a length-mismatched parallel pair. Add `make
> adversarial`. Report what breaks — do not fix anything yet.

---

## 4. Part C — no code, all judgment

Write it yourself. The two constraints that decide the score:

- **No external API budget** → synthetic "casualized" pairs cannot come from a
  frontier API. They must come off your own model on the same A100.
- **Reviewer covers Hindi + Kannada only** → 4 of 6 languages are structurally
  unvalidatable. Name it and design around it.

Envelope to show: 20 reviewer-hours ≈ 1600 items at ~80/hr, so the reviewer is
an *evaluator*, not a labeller. LoRA SFT on ~15k pairs × ~400 tok × 3 epochs
≈ 18M tokens — hours on an A100. **GPU is not the bottleneck; data and human
eval are.** Saying that explicitly is the signal.

Labelled sections, exactly as specified: assumptions, arithmetic, success
metric with a number, kill criterion with a date, day-1 experiment.

---

## 5. Schedule (~10h)

| Block | Work | h |
|---|---|---|
| 1 | Master prompt + scaffold + `make check` green | 1.0 |
| 2 | Phase 1 recon; **you** select claims | 0.5 |
| 3 | B1 + B3 by hand (anchors everything) | 1.0 |
| 4 | Phase 2 parity gate | 0.75 |
| 5 | Phase 3 corpus | 1.0 |
| 6 | Phase 4 ablation sweep + tests | 1.75 |
| 7 | Phase 5 corrected analysis | 1.25 |
| 8 | Phase 6 Part B implementation | 1.0 |
| 9 | Phase 7 render + adversarial | 0.75 |
| 10 | A4 + Part C memos, AI_USAGE, notebook pass | 1.0 |

---

## 6. Defense readiness checklist

- [ ] `make reproduce` green on a clean clone, offline
- [ ] `make parity` green — ablation deltas are admissible
- [ ] Every deliverable number traceable to a `results/*.json` key by name
- [ ] Rejected-claims section present with null results shown
- [ ] Bootstrap CIs on every headline ratio
- [ ] Adversarial fixtures run; you know what breaks and why
- [ ] You can re-derive KV-bytes/token and your top fertility ratio cold, no notes
- [ ] Adding a tokenizer or a flag is a one-file change (they may ask)
- [ ] `AI_USAGE.md` contains at least one entry where the model misled you and
      the measurement that caught it, cross-referenced to a rejected claim

---

## 7. AI_USAGE.md skeleton

```markdown
## Where AI did the work
- <file>: generated, reviewed line by line, I changed <what> because <why>

## Where I wrote it myself
- claim selection, denominator argument, B3 diagnosis, Part C reasoning

## Where AI misled me
- **Claimed:** <the confident wrong assertion, verbatim>
- **Caught by:** <command> — delta was <0.1%, see F-NN (rejected)
- **Lesson:** <one line>

## What I would not be able to defend
- <honest boundary — this scores better than pretending there isn't one>
```

That last section is counterintuitive and it works. They said they'd rather see
three claims you can defend to the death than ten you can't.
