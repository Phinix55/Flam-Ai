# NOTEBOOK

Chronological lab notebook. Append-only. Dead ends stay in — they are the
record of how the conclusions were reached, and deleting them would make this
a document written after the fact.

Entry format:

```
## YYYY-MM-DD — <session / phase>
**Hypothesis:**
**Ran:**            <exact command>
**Came back:**      <what the artefact said>
**Now believe:**
**Died:**           <what this ruled out>
```

---

## Unverified hypotheses

**Status of this section.** Nothing below is a claim, a finding, or a
conclusion. Every item is a *candidate for measurement*, and every item is
`UNVERIFIED` until an experiment in this repo reports a number. No item may be
cited in any file under `deliverable/` in its current state.

An item leaves this section only by being measured. It then moves to
`deliverable/partA/FINDINGS.md` — as a finding **or** as a rejected claim, at
the same level of rigour. Refuted items are worth the same as confirmed ones
and must not be quietly dropped.

**What the ranking means.** Items are ordered by one mechanical criterion:
*the predicted magnitude of the change to the report's headline `5.89×`
Hindi:English figure if this single thing were changed in isolation.* That is a
prediction, not a result, and the order is expected to change once measured —
which is the entire point of measuring. Two consequences worth stating:

- The criterion **cannot express the importance of class-M items** (below).
  Several of the lowest-ranked items are predicted to move the headline by
  exactly zero while bearing directly on whether the headline means anything.
- Ranking is **not** a recommendation. Selection of which items to pursue is
  reserved to the human (BLUEPRINT §3, Phase 1: *"Do not recommend which to
  pursue; I choose."*).

**Class** column:

- **N** — predicted to move the number.
- **M** — predicted to change what the number *means*, at zero or near-zero
  effect on the number itself.

**Category** is recorded as a *candidate* category. On confirmation these map
to `FINDINGS.md`'s `code bug` / `conceptual`; on refutation, to `rejected`.
The word "bug" is not used below as an assertion about anything in
`starter_kit/`.

### Index

| # | Candidate | Category (cand.) | Class | Predicted Δ on headline | Conf. |
|---|---|---|---|---|---|
| H-01 | Single-tokenizer evidence behind a claim about all tokenizers | conceptual | N | large | 4 |
| H-02 | `chars` is a codepoint count, reported as "per character" | conceptual | N | large | 4 |
| H-03 | `.lower()` before tokenization is one-sided across these scripts | code-level | N | moderate | 5 / 3 |
| H-04 | Reported mean is macro (per-line ratios), not the corpus ratio | conceptual | N | moderate | 4 |
| H-05 | `split(" ")` on a literal space rather than a whitespace split | code-level | N | small | 4 / 2 |
| H-06 | `tok/char` presented as independent confirmation of `tok/word` | conceptual | M | ~0 | 5 |
| H-07 | Line-by-line parallelism asserted but never checked | conceptual | M | 0 | 4 / 5 |
| H-08 | n = 10, three significant figures, no dispersion reported | conceptual | M | 0 | 5 |
| H-09 | "worse/better tokenization" label derived from the ratio alone | conceptual | M | 0 | 3 |
| H-10 | Comparison baseline is whichever `--corpus` came first | code-level | M | 0 | 5 / 1 |
| H-11 | Blank lines filtered per file, independently per language | code-level | M | 0 | 5 / 1 |
| **H-12** | **`random.seed(1337)` with no evident consumer** | *suspected harmless* | — | 0 | 4 |
| **H-13** | **Unconditional `NFC` normalisation "just in case"** | *suspected harmless* | — | 0 | 5 / 2 |
| **H-14** | **Two backends, two special-token code paths** | *suspected harmless* | — | 0 | 4 |
| **H-15** | **Printed ratio ≠ ratio of the printed columns** | *suspected harmless* | — | 0 | 4 |

Where two confidences are given they are `<mechanism exists> / <it is material
to the headline>`. The assignment states that at least one suspicious-looking
thing is genuinely fine; H-12 … H-15 are the candidates for that, carried at
the same rigour as the rest because a null result has to be *earned*.

---

### H-01 — Finding 3 attributes the result to the script, on evidence from one tokenizer `UNVERIFIED`

**Category (candidate):** conceptual · **Class:** N
**Locus:** `REPORT_v0.md:21–23`; single `--tokenizer` argument at
`fertility.py:79`.

**Observation (no verdict).** The reported run used `gpt2` only
(`REPORT_v0.md:8`). `gpt2` is a byte-level BPE. Finding 3 reads: *"any
tokenizer will struggle. This is a property of the script, not the
tokenizer."* — a claim quantified over all tokenizers.

**Experiment.** Hold corpus, casing, denominator and aggregation fixed; vary
**only** the tokenizer across the registry (`gpt2`, `cl100k_base`,
`xlm-roberta-base`, `google/muril-base-cased`). Report Hindi fertility and the
Hindi:English ratio for each with bootstrap 95% CIs.
`python -m audit analyze` → `results/analysis.json`.

**Predicted direction.** If the effect is a property of the script, the ratio
is approximately invariant across tokenizers. Predicted instead to fall
substantially for the multilingual and Indic-aware vocabularies — which would
locate the effect in the vocabulary rather than in the script.

**Null control.** English fertility across the same four tokenizers bounds how
much of any movement is a generic vocabulary-size effect rather than Indic
coverage specifically.

**Confidence.** 5 that the tokenizers differ from each other; 4 that the
difference is large enough to bear on the attribution.

---

### H-02 — `chars = len(line)` counts codepoints; the column is labelled "tok/char" `UNVERIFIED`

**Category (candidate):** conceptual · **Class:** N
**Locus:** `fertility.py:63`, `fertility.py:65`; `REPORT_v0.md:10–13`.

**Observation (no verdict).** `len()` on a `str` returns codepoints. Direct
read of the sample, counting text only (line terminators excluded):
`hin_sample.txt` is 764 bytes / 290 codepoints over 10 lines; `eng_sample.txt`
is 448 bytes / 448 codepoints over 10 lines — i.e. pure ASCII. Devanagari
codepoints in this file encode to 3 UTF-8 bytes each, and a single perceived
character is routinely several codepoints (consonant + vowel sign; consonant +
virama + consonant).

**Experiment.** Recompute the identical numerator against four denominators —
codepoints, extended grapheme clusters (`regex` `\X`), UTF-8 bytes, and
parallel sentence — on the same corpus with the same tokenizer, and report all
four side by side per language.

**Predicted direction.** For Devanagari the grapheme count is predicted below
the codepoint count and the byte count predicted roughly 3× above it, so one
numerator yields three different ratios ordered `per-byte < per-codepoint <
per-grapheme`. Predicted to change the magnitude of the cross-language
comparison and possibly its ordering.

**Null control.** For pure ASCII, bytes = codepoints = graphemes exactly. The
English rows are the control: if they diverge, the counters are wrong, not the
metric.

**Confidence.** 5 that the denominators diverge; 4 that the divergence is
large enough to move the headline.

---

### H-03 — `.lower()` runs before tokenization, and lowercasing is not symmetric across these two scripts `UNVERIFIED`

**Category (candidate):** code-level · **Class:** N
**Locus:** `fertility.py:59–60` (`# lowercase so casing doesn't add noise`).

**Observation (no verdict).** Direct read of the sample:
`text.lower() != text` for `eng_sample.txt`; `text.lower() == text` for
`hin_sample.txt` — Devanagari is caseless. Codepoint length is unchanged by
`.lower()` in both files (delta `+0`), so `chars` at `fertility.py:63` cannot
move; only the token count can. The English sample contains `Bengaluru`,
`NASA`, `ISRO`, `MG Road`, `GPU`, `Quarterly Review`, `Thursday`, `March`.

**Experiment.** `--flag preserve_case`: skip the `.lower()` call, change
nothing else. Measure token count, micro and macro fertility per language,
with and without, on the sample and on FLORES; repeat per tokenizer, since
case sensitivity is a vocabulary property.

**Predicted direction.** Changes English token counts (`gpt2` BPE carries
distinct merges for capitalised forms) and changes Hindi token counts by
exactly zero. A one-sided change to the baseline language moves the reported
ratio even though neither language's *text* was treated differently by intent.

**Null control — built in.** The Hindi delta must be exactly `0.000`. A
non-zero Hindi delta means the flag is not isolating what it claims and the
experiment is void. This is the strongest self-check in the list.

**Sub-item for the adversarial fixtures.** `.lower()` is not universally
length-preserving (e.g. `İ` U+0130 → 2 codepoints), which would make `chars`
depend on casing. Observed delta is `+0` on both sample files; worth a fixture
rather than an assumption.

**Confidence.** 5 that English is affected; 5 that Hindi is not; 3 on the sign
of the English change.

---

### H-04 — The reported figure is the mean of per-line ratios, not the corpus ratio `UNVERIFIED`

**Category (candidate):** conceptual · **Class:** N
**Locus:** `fertility.py:64–67`; docstring at `:55` reads *"averaged over
lines"*.

**Observation (no verdict).** `per_line_fertility.append(len(tokens) /
len(words))` followed by `sum(per_line_fertility) / n`. Every line contributes
equally regardless of its length. Observed line lengths in the sample: 6–12
words (eng), 4–8 words (hin).

**Experiment.** Compute both on identical inputs — micro `Σtokens / Σwords`
and macro `mean(tokensᵢ / wordsᵢ)` — and report the gap per language and per
denominator, with bootstrap CIs on the macro.
`python -m audit ablate --flag micro_aggregate`.

**Predicted direction.** Macro ≥ micro where per-line fertility is negatively
correlated with line length (fixed per-line costs — leading-space tokens,
sentence-final punctuation — amortise over longer lines). Predicted to be
larger for the higher-fertility language, and therefore predicted to inflate
the cross-language ratio rather than merely both levels.

**Null control.** Micro and macro must coincide exactly when every line has the
same denominator value — a constructible synthetic fixture, already required by
`tests/test_aggregation.py`.

**Confidence.** 4.

---

### H-05 — Word count comes from `split(" ")` on a literal space, not a whitespace split `UNVERIFIED`

**Category (candidate):** code-level · **Class:** N
**Locus:** `fertility.py:62`.

**Observation (no verdict).** `words = line.split(" ")`. Direct read of the
sample: `eng_sample.txt` L07 and `hin_sample.txt` L10 each contain exactly one
run of two consecutive spaces. On those lines `split(" ")` yields 8 vs 7 parts
(eng) and 6 vs 5 parts (hin); all other 18 lines are identical under both
splits. Leading and trailing whitespace is already removed upstream by
`raw.strip()` at `fertility.py:44`. No non-ASCII whitespace is present in
either file.

**Experiment.** `--flag split_on_unicode_whitespace`: replace `line.split(" ")`
with `line.split()`, change nothing else. Report per-language micro and macro
fertility before → after on both the 10-line sample and FLORES.

**Predicted direction.** Increases the denominator on affected lines, lowering
that line's tokens/word and therefore the language's macro fertility. Both
sample files contain exactly one affected line out of ten, so the effect on the
*ratio* is predicted smaller than on either level — partial cancellation.
Predicted small in absolute terms (order 1%).

**Null control.** A corpus with no multi-space runs must give exactly zero
delta. If FLORES satisfies that, the flag's FLORES delta measures corpus
hygiene rather than the metric — and saying so is part of the result.

**Confidence.** 4 that the delta is non-zero on the sample; 2 that it is
material to the headline.

---

### H-06 — The `tok/char` column is presented as independent confirmation of `tok/word` `UNVERIFIED`

**Category (candidate):** conceptual · **Class:** M
**Locus:** `REPORT_v0.md:19–21` — *"The tok/char column agrees … which confirms
the per-word number"*; and `:27–28` — *"the two metrics agree, so the result is
robust."*

**Observation (no verdict).** Both columns are produced from the same token
count in the same loop body (`fertility.py:61`, `:64–65`). Written out, the
ratio between the two "agreeing" cross-language figures is

```
(T_h/W_h)/(T_e/W_e)  ÷  (T_h/C_h)/(T_e/C_e)  =  (C_h/W_h)/(C_e/W_e)
```

— the token count cancels completely, leaving the cross-language ratio of
characters-per-word.

**Experiment.** Emit chars-per-word per language, then check numerically that
`fertility_ratio / tpc_ratio` equals the chars-per-word ratio to floating-point
tolerance. Repeat with a second tokenizer: if the identity holds unchanged, the
second column carries no tokenizer information the first did not.

**Predicted direction.** Predicted to hold exactly, being an algebraic identity
given the shared numerator — which would mean the second column contributes one
script property and zero independent evidence about the tokenizer. Predicted
zero effect on either printed number.

**Null control.** The identity must hold for every tokenizer and every corpus.
Any input where it fails falsifies the derivation, not the report.

**Confidence.** 5.

---

### H-07 — The samples are described as parallel line-by-line; nothing checks it `UNVERIFIED`

**Category (candidate):** conceptual (corpus validity) · **Class:** M
**Locus:** assignment PDF — *"English + Hindi, parallel line-by-line"*;
`fertility.py:88–92`, which processes each `--corpus` path independently.

**Observation (no verdict).** A language-independent index check on shared
proper nouns and transliterated content words — chosen because it requires no
translation judgement:

| token | eng line(s) | token | hin line(s) |
|---|---|---|---|
| Bengaluru | 1 | बेंगलुरु | 2 |
| Mysuru | 8 | मैसूर | 4 |
| cricket | 4 | क्रिकेट | 7 |
| train | 5 | ट्रेन | 6 |
| book | 3, 7 | किताब | 3, 10 |

Both files contain 10 non-blank lines. The script performs no index-wise
comparison of any kind.

**Experiment.** (i) Systematic index-wise alignment check over shared named
entities, numerals and digits on the sample. (ii) In the real corpus,
`prepare.py` raising `AlignmentError` on any line-count or index mismatch
rather than truncating — the behaviour required by CLAUDE.md §3.

**Predicted direction.** Predicted **exactly zero** effect on the reported
`tok/word` and `tok/char` numbers, because each file is measured independently
and neither metric reads across files. Predicted to be decisive for any
*per-parallel-sentence* denominator, which requires index-wise correspondence
to mean anything at all.

**Confidence.** 4 that the sample indices are not content-aligned; 5 that no
alignment check exists in the script.

---

### H-08 — n = 10, reported to three significant figures, with no dispersion `UNVERIFIED`

**Category (candidate):** conceptual (statistical) · **Class:** M
**Locus:** `REPORT_v0.md:10–13`; *"No further measurement needed"* at `:27`.

**Observation (no verdict).** Ten lines per language, one tokenizer, one
domain, one script per language. No interval, variance, or per-line
distribution accompanies the point estimates.

**Experiment.** Bootstrap 95% CI (seeded `numpy.random.Generator`,
`config.bootstrap_iterations`) on the macro mean per language on the 10-line
sample; the same on FLORES devtest; compare interval widths against the
precision printed.

**Predicted direction.** Predicted that the CI at n = 10 is wide relative to
the two decimals printed, and narrows substantially at n ≈ 1000. Predicted zero
effect on the point estimates themselves.

**Confidence.** 5.

---

### H-09 — A "worse/better tokenization" label is derived from the ratio alone `UNVERIFIED`

**Category (candidate):** conceptual · **Class:** M
**Locus:** `fertility.py:102` — `{'worse' if ratio > 1 else 'better'}`.

**Observation (no verdict).** The label is a function of the ratio and nothing
else. No vocabulary size, downstream quality measure, or cost figure enters it.

**Experiment.** Report fertility alongside `vocab_size` for every tokenizer in
the A3 grid and check whether the ordering induced by fertility survives
holding vocabulary size constant.

**Predicted direction.** Predicted that a larger vocabulary lowers fertility
mechanically, so the ordering tracks vocabulary size in addition to whatever
else it tracks. Predicted zero effect on the numbers.

**Confidence.** 3.

---

### H-10 — The comparison baseline is whichever language appeared first in `--corpus` `UNVERIFIED`

**Category (candidate):** code-level (robustness) · **Class:** M
**Locus:** `fertility.py:96–97` — `base = langs[0]`.

**Observation (no verdict).** `results` is an insertion-ordered dict built from
the repeatable `--corpus` argument. The baseline is not pinned to a language;
it is positional.

**Experiment.** Run the untouched script twice with the two `--corpus`
arguments swapped; compare the printed ratio and label.

**Predicted direction.** Predicted to invert the ratio (`x → 1/x`) and flip the
worse/better label, with the per-language columns unchanged. Deterministic for
a fixed command line, so predicted zero effect on the documented invocation.

**Confidence.** 5 on the mechanism; 1 that it affects the reported numbers.

---

### H-11 — Blank lines are filtered per file, independently for each language `UNVERIFIED`

**Category (candidate):** code-level · **Class:** M
**Locus:** `fertility.py:45–46` — `if not line: continue`.

**Observation (no verdict).** Neither sample file contains a blank line, so
`n = 10` for both here. The filter runs per file, before any cross-file
relationship is established. `str.strip()` also removes Unicode whitespace, so
a whitespace-only line is filtered identically.

**Experiment.** Adversarial fixture — a parallel pair where one file carries a
blank or whitespace-only line at an index the other does not. Observe whether
`n` diverges between languages and whether anything raises.

**Predicted direction.** Predicted zero on the current sample (no blank lines
exist). On a corpus with asymmetric blanks, predicted to silently desynchronise
line indices between languages with no error surfaced.

**Confidence.** 5 that no cross-file check exists; 1 that it affects the
reported numbers.

---

## Candidates suspected harmless

Carried at the same rigour. A null result is only worth points if it was
genuinely at risk of not being null, so each of these still names the
experiment that could refute the "harmless" prediction.

### H-12 — `random.seed(1337)` at module scope with no evident consumer `UNVERIFIED`

**Category (candidate):** ambiguous → *suspected harmless*
**Locus:** `fertility.py:21`, `:25` (`random.seed(1337)  # reproducibility`);
`:23` (`import sys`).

**Observation (no verdict).** `import random` and a module-scope `random.seed`
call annotated "reproducibility". No call to any `random` function appears
elsewhere in the file. `sys` is imported and likewise not referenced anywhere
in the file.

**Experiment.** (i) Run the untouched script; run the flag-gated
reimplementation with the seed call absent; diff stdout byte-for-byte. (ii)
Rule out a transitive consumer by running the untouched script twice under
different global seeds and diffing — this is what would catch a backend that
reads global `random` state during `encode`.

**Predicted direction.** Predicted **exactly zero**. Recorded so the null
result is on the record rather than assumed, and so the seed's presence is not
mistaken for a determinism guarantee it does not provide.

**Confidence.** 4 that the effect is exactly zero.

---

### H-13 — `unicodedata.normalize("NFC", line)` applied unconditionally `UNVERIFIED`

**Category (candidate):** ambiguous → *suspected harmless on this input*
**Locus:** `fertility.py:48–49` (`# normalize just in case -- some corpora are
messy`).

**Observation (no verdict).** Direct read of the sample: both files already
satisfy `text == NFC(text)`. For these two files NFD is *also* identical —
codepoint delta `+0` — because the Devanagari nukta forms U+0958–U+095F are
Unicode composition exclusions, so NFC does not compose them and NFD finds
nothing further to decompose. On this corpus the call is therefore predicted to
be a no-op.

**Experiment.** (i) Assert `NFC(text) == text` per input file and report the
codepoint delta. (ii) On FLORES, run the whole pipeline under both NFC and NFD
and report every metric under both — the codepoint and grapheme denominators
are the ones that could move.

**Predicted direction.** Predicted exactly zero on the two sample files. On a
corpus containing decomposable sequences, predicted to change codepoint counts
(and hence `tok/char`) while leaving grapheme counts unchanged — which is
precisely what would make the grapheme denominator the more stable of the two.

**Confidence.** 5 that it is a no-op on the sample; 2 that it is a no-op on
FLORES.

---

### H-14 — The two backends are loaded through paths with different special-token settings `UNVERIFIED`

**Category (candidate):** ambiguous → *suspected harmless*
**Locus:** `fertility.py:28–38` — the HF path passes `add_special_tokens=False`
explicitly; the tiktoken path returns `enc.encode` with defaults.

**Observation (no verdict).** The two settings differ syntactically. Whether
they differ *behaviourally* is the open question: if tiktoken's `encode` emits
no special tokens by default, the two paths count the same thing.

**Experiment.** Per backend, encode a fixed string with and without special
tokens and compare counts. Separately, feed a string containing a literal
special-token spelling (`<|endoftext|>`) through both paths and record what
each does — this is an adversarial fixture, not a corpus condition.

**Predicted direction.** Predicted zero difference in counted tokens for
ordinary text. Predicted divergence only on text containing special-token
spellings.

**Confidence.** 4 that the two paths are behaviourally equivalent on this
corpus.

---

### H-15 — The report's printed ratio is not the ratio of its own printed columns `UNVERIFIED`

**Category (candidate):** ambiguous → *suspected harmless (display rounding)*
**Locus:** `REPORT_v0.md:10–19`; `fertility.py:93` (columns) vs `:100` (ratio).

**Observation (no verdict).** `7.45 / 1.27 = 5.8661`, but the report states
`5.89×`. Treating the printed columns as correctly rounded to 2 dp, the true
ratio is constrained to `[5.8392, 5.8933)` — `5.89` lies inside that interval,
but at its very top. The `tok/char` claim is far looser:
`1.579 / 0.226 = 6.9867`, band `[6.9691, 7.0044)`, reported as `7.0`.

**Experiment.** Recover the unrounded per-language values from the
reimplementation at parity and check whether their exact ratio rounds to
`5.89`. The script computes the ratio from unrounded values and prints the
columns rounded independently, so this is directly checkable.

**Predicted direction.** Predicted to resolve as display rounding and nothing
else. The narrowness of the admissible interval is the only reason this is
worth a measurement rather than an assumption — it is the kind of item that
would be embarrassing to assert either way without one.

**Confidence.** 4 that it is rounding.

---

## Serving-side propositions (Part B) — parked, deliberately not analysed

`REPORT_v0.md` §2 contains testable propositions about the serving stack.
Per BLUEPRINT §3 (block 3: *"B1 + B3 by hand — anchors everything"*), their
diagnosis is reserved for human hand-derivation **before** any script is
written, so no mechanism, column or answer is proposed here. Recorded verbatim
only, all `UNVERIFIED`:

- **P-1** *"at batch 16, long prompts hit 1311 tok/s vs only 883 tok/s for
  short prompts. Longer prompts clearly give better GPU utilization."*
  (`REPORT_v0.md:32–34`)
- **P-2** *"encourage clients to pack more context per request; throughput
  improves with prompt length."* (`:36–37`)
- **P-3** *"assume ~1600 tok/s per L4 (best observed) and scale linearly with
  batch size, so batch 48 should give us ~3200 tok/s."* (`:37–39`)

The assignment states P-2 and P-3 *"come from the same misreading of one
column"* (PDF, B3) — identifying that column is the human's task, not this
notebook's.

---

## What Phase 1 did not examine

Stated so the boundary is on the record rather than discovered at the defense:

- **No code was run against the metric.** Every number in this section is
  either a direct byte-level read of an input file, or arithmetic on figures
  printed in `REPORT_v0.md`. No fertility, token count or ratio has been
  computed by this repo yet.
- **No tokenizer has been loaded.** Every prediction about `gpt2` behaviour on
  Devanagari (H-01, H-02, H-03) is a prediction from vocabulary provenance, not
  an observation. All three could be wrong.
- **FLORES has not been fetched.** Sample-based observations (H-05's
  double-space count, H-13's NFC no-op) are properties of 20 lines and may not
  survive at n ≈ 1000.
- **The Hindi text was not translated by me for H-07.** The alignment signal
  used is transliterated proper-noun position, chosen precisely because it
  needs no translation judgement. A proper alignment check is the experiment.
- **`bench/` was not opened for analysis** beyond quoting §2 of the report.

---

## Session log

### 2026-09-07 — Session 0: scaffolding

**Hypothesis:** none. Infrastructure only; no analysis performed, no
`starter_kit/` behaviour examined for correctness.

**Ran:**

```
uv python install 3.11
uv sync --frozen --all-groups
make check
```

**Came back:** `ruff` clean, `ruff format --check` clean on 43 files,
`mypy --strict` clean on 31 source files, `pytest` → 50 passed, 1 skipped,
16 xfailed. The 16 xfails are the CLAUDE.md §4 contract tests, written with
real assertions and marked `xfail(strict=True)` so that implementing them
converts XPASS into a hard failure and forces the marker off — the gate cannot
go quietly green. The 1 skip is `test_labels_are_unique_across_the_sweep`,
which is vacuous until flags exist.

**Now believe:** nothing about the starter kit. The repo skeleton exists, the
architecture contract in CLAUDE.md §5 is enforced by module layout, and
`make check` is green on stubs.

**Died:** nothing yet.

---

### 2026-09-07 — Session 1: Phase 1 recon

**Hypothesis:** none under test. The objective was to enumerate candidates for
measurement without measuring any of them, per BLUEPRINT §3 Phase 1 ("no code,
no verdicts").

**Ran:** read-only inspection only —

```
# byte-level descriptive read of the two sample files
python - <<'PY'   # codepoints, bytes, split(" ") vs split(), multi-space runs,
                  # non-ASCII whitespace, NFC/NFD identity, lower() identity
# arithmetic on figures printed in REPORT_v0.md (rounding bands)
# index positions of shared transliterated proper nouns across the two files
```

No repo code was executed against the metric; no tokenizer was loaded.

**Came back:**

- `eng_sample.txt`: 448 B / 448 cp of text (pure ASCII) / 10 non-blank lines;
  one 2-space run at L07 (`split(" ")`→8, `split()`→7); already NFC; `lower()`
  changes the text.
- `hin_sample.txt`: 764 B / 290 cp of text / 10 non-blank lines; one 2-space
  run at L10 (`split(" ")`→6, `split()`→5); already NFC; NFD identical to NFC
  (composition exclusions U+0958–U+095F); `lower()` leaves the text unchanged.
- No non-ASCII whitespace and no blank lines in either file.
- Shared proper nouns sit at differing line indices across the two files
  (table in H-07).
- `7.45/1.27 = 5.8661` against a reported `5.89×`; the 2-dp rounding band is
  `[5.8392, 5.8933)`.

**Now believe:** 15 candidates are worth stating, of which 4 are suspected
harmless. Five are predicted to move the headline number and six are predicted
to move only its interpretation — a split that was not obvious before writing
them out, and which the single ranking criterion cannot express. The strongest
methodological find of the session is not a candidate at all: **H-03 has a
built-in null control** (Hindi must show exactly zero delta under a casing
flag), which makes it the one item whose experiment validates itself.

**Died:** two candidates considered and dropped before reaching the list —
(i) *division-by-zero on empty input*: `str.strip()` removes Unicode whitespace
and `if not line: continue` filters the result, so neither `len(words)` nor
`chars` can reach zero via the file path; it survives only as an adversarial
fixture, folded into H-11. (ii) *`chars` computed after `.lower()` could change
length*: true in principle (`İ` U+0130), but the observed codepoint delta is
`+0` on both files, so it is a fixture concern and was folded into H-03 rather
than promoted.

**Next:** selection of 4–6 candidates is the human's (BLUEPRINT §3). Phase 2
cannot begin until that selection exists, because each selected candidate
becomes exactly one field on `AblationFlags`.

---

### 2026-09-07 — Selection of claims to test

**Who selected.** BLUEPRINT §3 reserves this to the human ("*That selection is
your judgment, not the model's*"). It was instead **delegated to the model and
performed by it**, after the constraint was raised and reaffirmed. Recorded
here and in `AI_USAGE.md` rather than presented as human judgement, because the
provenance of the selection is itself graded content. Ratification, and the
ability to defend each choice cold, remains outstanding.

**Selection criteria applied**, in order:

1. **Single-toggle isolability.** The candidate must be expressible as one
   boolean that changes exactly one behaviour in `legacy.py`. This alone
   excluded H-01 (tokenizer choice is the A3 grid, not an ablation), H-06 (an
   algebraic identity checked on outputs), H-07 and H-08 (corpus and
   aggregation properties, not legacy behaviours).
2. **Category spread.** A2 states that some candidates are code-level and *at
   least one* is conceptual. The set carries both.
3. **At least one predicted null.** A2 also states that one suspicious-looking
   thing is genuinely fine, and penalises flagging it without evidence. Two
   nulls were selected rather than one, so the null result rests on two
   independent measurements.
4. **Preference for candidates carrying their own control.**

**Selected — six flags:**

| Flag | Candidate | Category (cand.) | Why selected |
|---|---|---|---|
| `grapheme_denominator` | H-02 | conceptual | The denominator claim, isolable as one counter swap |
| `preserve_case` | H-03 | code-level | Carries a built-in null control (Hindi must be exactly 0) |
| `micro_aggregate` | H-04 | conceptual | Macro/micro is a clean, well-defined single change |
| `split_on_unicode_whitespace` | H-05 | code-level | Smallest predicted effect; tests the harness's resolution |
| `skip_nfc_normalisation` | H-13 | predicted null | Null is falsifiable — NFD input would move it |
| `perturb_global_rng` | H-12 | predicted null | Null with no falsifying input; see wiring note below |

**Not selected, and why** — recorded so the omissions are deliberate rather
than forgotten. H-01 and H-06 move to Phase 5 (A3), where they are the natural
form of the question. H-07 becomes `prepare.py`'s `AlignmentError` in Phase 3.
H-08 becomes the bootstrap CI in Phase 4. H-09, H-10, H-11 and H-14 are carried
to Phase 7 as adversarial fixtures; none is expressible as a single behavioural
toggle on the reported numbers.

---

### 2026-09-07 — Session 2: Phase 2 parity gate

**Hypothesis:** that a from-scratch reimplementation can reproduce
`starter_kit/fertility.py` exactly — a precondition, not a claim about the
original. Until it holds, no ablation delta is admissible.

**Ran:**

```
make parity     # pytest -m parity
make check
TIKTOKEN_CACHE_DIR=.cache/tokenizers/tiktoken \
  python starter_kit/starter_kit/fertility.py \
    --corpus eng=.../eng_sample.txt --corpus hin=.../hin_sample.txt --tokenizer gpt2
```

**Came back:** `make parity` → **17 passed**. `make check` → 74 passed, 10
xfailed (Phases 4–6). The untouched original prints:

```
eng                       1.27       0.226
hin                       7.45       1.579
hin is 5.89x the fertility of eng (worse tokenization)
```

— which reproduces `REPORT_v0.md` §1 exactly, so the parity gate is anchored to
the actual reported run rather than to some other invocation of the script.

**Now believe:**

- Parity holds on two independent proofs: byte-exact stdout against the script
  run as a subprocess, and **bit-exact float equality** (`==`, no tolerance)
  against the original's own `read_lines` and `analyze`, loaded read-only via
  `importlib`. The second matters because the original prints only 2–3
  decimals, so stdout parity alone would let a difference in the fourth decimal
  survive.
- **H-15 is resolved as display rounding**, incidentally and for free: the
  script itself prints `5.89`, so the printed ratio is not a report
  transcription artefact. It computes the ratio from unrounded values and
  rounds the columns independently, exactly as predicted. Formal null result
  belongs to Phase 4; this is the mechanism, observed.

**Died:**

- **My `preserve_case` wiring probe was wrong.** I chose `"ABC DEF"`, assuming
  case folding changes gpt2 token counts. It does not — 2 tokens either way.
  Measured: `"Bengaluru International Airport"` and `"MG Road"` are also
  unchanged; `"NASA and ISRO"` gains a token when folded, `"Thursday"` gains
  one, and **`"Quarterly Review"` loses one**. The sign is not uniform. This
  retroactively justifies H-03's split confidence (5 that the effect exists / 3
  on its direction) and warns that a per-corpus net effect could partially
  cancel. Probe replaced with `"NASA and ISRO"`.
- `str.splitlines()` was rejected for line ingestion: it breaks on VT, FF, NEL,
  LS and PS, whereas text-mode file iteration translates CRLF/CR to LF and
  breaks on LF alone. Invisible on this corpus, but it would have been a
  silent unmeasured ablation on any input containing those separators.

**Measured this session, incidental to the gate:** `\X` grapheme clustering is
**not uniform across Indic scripts** — the Devanagari conjunct `क्ष`
(ka+virama+ssa) is one cluster, the structurally identical Kannada conjunct
`ಕ್ಕ` (ka+virama+ka) is two. Pinned in `tests/test_counters.py`. This
constrains H-02: a per-grapheme cross-script comparison does not hold "one
perceived character" constant the way it does within one script, and any A3
claim on that denominator has to carry the caveat.

**Guard added beyond the phase brief.** Each flag now has a *wiring probe* —
a crafted input proving the flag reaches its code path. A flag declared but not
wired would report a zero delta in the Phase 4 sweep and be indistinguishable
from a genuine null result, which is precisely how an unmeasured claim becomes
a fabricated one. `perturb_global_rng` is listed explicitly as having no
falsifying probe, since that is its hypothesis rather than an oversight.

**Scope pulled forward, deliberately:** the tiktoken BPE fetch
(`corpus/acquire.fetch_tiktoken`) and four counters in `metrics/counters.py`.
The gate cannot run offline without the first and the `grapheme_denominator`
flag cannot exist without the second. `make corpus` now populates the tokenizer
cache and then raises at the unimplemented FLORES step; the fetch is idempotent,
so the partial run leaves a valid cache.

**Next:** Phase 3 (corpus). The sweep itself is Phase 4 — no flag has been run
across the corpus yet, and no delta has been measured.

---

### 2026-09-07 — Block 3: B1 + B3 derived by hand (PRE-REGISTRATION)

**Why this is timestamped before Phase 6.** BLUEPRINT §3 Phase 6: *"If my hand
calculation and your script disagree, report the disagreement — do not
reconcile silently."* That check is only possible if the hand numbers exist
**before** `bench/kv_math.py` and `bench/log_analysis.py` do. They do not exist
yet. Everything below is longhand arithmetic on values read out of
`model_spec.md` and `bench_log.csv`; Phase 6's script must reproduce it by
parsing those files, and any disagreement is a reportable result about the
parser, not something to quietly fix.

**Provenance caveat.** BLUEPRINT §3 assigns this to the human. It was performed
by the model, like the claim selection before it. Recorded in `AI_USAGE.md`.

#### B1(a) — KV-cache bytes per token

Values read from `model_spec.md`: layers 28, KV heads (GQA) 8, head_dim 128,
attention heads (Q) 24, KV cache precision fp16 → 2 B.

```
KV bytes/token = 2 (K and V) × layers × kv_heads × head_dim × dtype_bytes
               = 2 × 28 × 8 × 128 × 2
     2 × 28    = 56
     56 × 8    = 448
     448 × 128 = 57,344
   57,344 × 2  = 114,688 B/token   ( = 112 KiB/token )
```

**GQA is the term that decides it.** Group ratio = Q heads / KV heads = 24 / 8
= 3. Using the 24 query heads in place of the 8 KV heads gives 344,064 B/token
— exactly 3× too large. That is the arithmetic `tests/test_kv_math.py` pins
with an explicit MHA-vs-GQA pair.

#### B1(b) — Concurrency ceiling at 4096 context

`gpu_memory_utilization` 0.92, weights 4.2 B params × 2 B (fp16) = 8.4 GB,
non-KV overhead ≈ 1.6 GB, `max_model_len` 4096.

Per sequence: 114,688 × 4096 = **469,762,048 B ≈ 0.4698 GB**.

The spec says "24 GB", which is ambiguous. Both readings carried, neither
silently chosen:

| Reading | Usable (×0.92) | − weights − ovh = KV budget | Capacity | Ceiling |
|---|---|---|---|---|
| **decimal GB** (spec-literal) | 22.080 GB | 12.080 GB | 105,329 tok | **25.72 → 25** |
| binary GiB | 23.708 GB | 13.590 GB | 118,497 tok | 28.93 → 28 |

#### B1 — checked against the log, which discriminates between the two

Every long-prompt row holds prompt + gen = 3584 + 512 = 4096 tokens per
sequence, so resident tokens = `batch_size × 4096`.

| bs | resident tok | `kv_cache_util` | implied capacity | `preempted_seqs` | bs − 25 | bs − 28 |
|---|---|---|---|---|---|---|
| 8 | 32,768 | 0.31 | 105,703 | 0 | — | — |
| 16 | 65,536 | 0.62 | 105,703 | 0 | — | — |
| 24 | 98,304 | 0.93 | 105,703 | 0 | — | — |
| 32 | 131,072 | 0.97 *(saturated)* | — | **7** | **7** | 4 |
| 48 | 196,608 | 0.97 *(saturated)* | — | **23** | **23** | 20 |

Two independent confirmations of the decimal-GB reading:

1. **Unsaturated rows back out a capacity of 105,703 tokens**, against 105,329
   predicted — a 0.35 % gap. (Rows at 0.97 are clipped and cannot be inverted,
   so they are excluded; bs = 4 gives 102,400 from a 2-significant-figure
   `0.16` and is within rounding.)
2. **`preempted_seqs` equals `batch_size − 25` exactly** at both saturated
   rows: 32 − 25 = 7 ✓, 48 − 25 = 23 ✓. The binary-GiB ceiling of 28 predicts
   4 and 20, which the log does not show.

So B1(b) = **25 concurrent 4096-token sequences**, and the "24 GB" in the spec
behaves as decimal GB. This was not assumed; it was selected by the log.

#### B3 — goodput of the batch-24 long-prompt row, two independent ways

Row: `24,3584,512,24,61.16,1607.4,500.5,96.07,69221.3,0,0.93`.

```
way 1 — wall clock:   output_tokens / wall  = (24 × 512) / 61.16 s
                                            = 12,288 / 61.16 = 200.92 tok/s

way 2 — decode rate:  batch_size / itl_p50  = 24 / 0.09607 s
                                            = 249.82 tok/s   (decode phase only)
```

The two are independent — way 1 uses `wall_clock_s` and `gen_len`, way 2 uses
`batch_size` and `itl_ms_p50` — and they reconcile through prefill, which way 2
excludes by construction:

```
implied prefill share = 1 − 200.92/249.82 = 19.6 %
                      = 11.97 s of the 61.16 s run
cross-check: 24 × 3584 = 86,016 prompt tok / 11.97 s ≈ 7,185 prompt tok/s
```

**What `reported_tok_s` contains, as a measured identity.** For all 13 rows:

```
reported_tok_s ≟ num_requests × (prompt_len + gen_len) / wall_clock_s
max relative error across all 13 rows = 0.022 %
```

For this row: 24 × (3584 + 512) / 61.16 = 98,304 / 61.16 = 1,607.3 against
1,607.4 reported.

**The batch-16 pair, both columns side by side:**

| prompt_len | `reported_tok_s` | output-only goodput |
|---|---|---|
| 512 | 883.2 | 294.5 tok/s |
| 3584 | 1311.4 | 163.9 tok/s |

#### Interpretation — reserved

- `TODO(pratik): interpretation` — which column `REPORT_v0.md` §2 read, and
  why one reading carries both of its conclusions.
- `TODO(pratik): interpretation` — what §2 should have said instead.
- `TODO(pratik): interpretation` — B4's confirming counter and its expected
  value.

Per CLAUDE.md rule 6 these sentences are not model-authored. The arithmetic
above is complete and stands on its own; only the conclusions are withheld.

**Anomaly noted, not built on.** `e2e_ms_p95` exceeds `wall_clock_s` on every
row (batch 24: 69.22 s vs 61.16 s; batch 1: 12.86 s vs 10.94 s), which is not
possible for requests submitted simultaneously into a run of that length unless
the column includes time outside the measured window. Nothing above depends on
this column. Parked as an observation for Phase 6.

---

### 2026-09-07 — Block 5: Phase 3 corpus (A1)

**Hypothesis:** none under test. Corpus construction and validation.

**Ran:** `make corpus` (34 s, the only network stage).

**Came back:** FLORES-200 `devtest`, **1012 sentences × 7 languages**, aligned,
under both NFC and NFD → `results/corpus_stats.json`,
`results/sample_manifest.json`.

| lang | script | codepoints | graphemes | UTF-8 bytes | words |
|---|---|---|---|---|---|
| eng | Latin | 131,966 | 131,966 | 132,096 | 21,901 |
| hin | Devanagari | 131,201 | 85,978 | 337,460 | 25,643 |
| kan | Kannada | 138,127 | 90,471 | 375,441 | 16,100 |
| tam | Tamil | 154,131 | 99,724 | 421,635 | 16,775 |
| tel | Telugu | 132,500 | 76,602 | 353,696 | 16,938 |
| ben | Bengali | 130,391 | 81,693 | 348,729 | 19,506 |
| mar | Devanagari | 133,252 | 80,489 | 355,712 | 19,046 |

**Now believe:**

- English is the clean control: codepoints = graphemes exactly (131,966), and
  bytes ≈ codepoints. For every Indic language the three separate widely.
- **NFD adds codepoints but never graphemes.** Per-language codepoint delta
  NFC→NFD: kan +4,693, tam +1,701, ben +1,544, tel +710, mar +113, hin +3,
  eng +23. Grapheme delta: **+0 for every language.** This is the mechanism
  H-13 predicted, now measured on 1012 sentences rather than 20 lines.
- Word counts do **not** track text volume: Kannada has the most bytes per
  sentence of the Dravidian three but the fewest words (16,100 vs English's
  21,901 for identical content).

**Died:** nothing. `AlignmentError` never fired — FLORES devtest is genuinely
line-aligned at 1012 for all seven languages, so the guard is untriggered here
and is tested synthetically in `tests/test_corpus.py` instead.

**Reserved:** `deliverable/partA/CORPUS.md`, including the "what this corpus
cannot tell you" paragraph. BLUEPRINT §3 assigns it to the human; the numbers
it will cite are in `corpus_stats.json` and get rendered in Phase 7.

---

### 2026-09-07 — Block 6: Phase 4 ablation sweep (A2)

**Hypothesis:** the six selected flags each move the reported numbers by a
measurable, attributable amount — or provably do not.

**Ran:** `make ablate` (gated on `make parity`, which passed first). 15 s.
Grid = 2 normalisation forms × 8 arms × 7 languages = 112 cells, each with a
seeded 10,000-iteration bootstrap CI. → `results/ablation.json`.

**Came back — baseline, FLORES devtest NFC, gpt2, n = 1012:**

| lang | fertility | 95 % CI (macro) | tok/char | ratio to eng |
|---|---|---|---|---|
| eng | 1.2874 | [1.2759, 1.2991] | 0.2141 | 1.0000 |
| hin | 7.8651 | [7.8070, 7.9233] | 1.5293 | 6.1095 |
| ben | 13.3848 | [13.2787, 13.4888] | 1.9930 | 10.3970 |
| mar | 11.1860 | [11.0892, 11.2801] | 1.5963 | 8.6891 |
| tel | 20.5656 | [20.3883, 20.7451] | 2.6452 | 15.9750 |
| kan | 22.5698 | [22.3647, 22.7754] | 2.6599 | 17.5318 |
| tam | 25.1270 | [24.9180, 25.3401] | 2.7239 | 19.5182 |

**Relative delta per flag, % (NFC).** `fert` = tok/word, `tpc` = tok/char.

| arm | eng fert | hin fert | kan fert | eng tpc | hin tpc | kan tpc |
|---|---|---|---|---|---|---|
| `split_on_unicode_whitespace` | 0.00 | +0.02 | **+1.99** | 0.00 | 0.00 | 0.00 |
| `preserve_case` | **−3.34** | −0.00 | −0.01 | −3.29 | −0.00 | −0.01 |
| `micro_aggregate` | −0.71 | −0.51 | −1.21 | −0.90 | +0.04 | +0.07 |
| `grapheme_denominator` | 0.00 | 0.00 | 0.00 | 0.00 | **+53.05** | **+52.85** |
| `skip_nfc_normalisation` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `perturb_global_rng` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

**Now believe:**

- **`perturb_global_rng` is an exact null.** Every one of the 14 cells is
  *byte-identical* to baseline, not merely close. Nothing in the pipeline —
  including inside the tokenizer backend — reads global RNG state.
- **`skip_nfc_normalisation` is a conditional null, and the condition is
  measurable.** Zero on the NFC corpus; non-zero on the NFD corpus (kan +0.42 %
  tok/char, eng +0.09 %, hin −0.00 %). The flag is falsifiable, and it is only
  null because the input already satisfies the normalisation.
- **NFC and NFD baselines are byte-identical**, because `read_lines`
  re-normalises to NFC unless the flag is set. Predicted and confirmed; it is
  why the NFD corpus only diverges on that one arm.
- **`grapheme_denominator` and `split_on_unicode_whitespace` are cleanly
  orthogonal** in the way their construction requires: the first moves only
  tok/char (0.00 % on tok/word everywhere), the second only tok/word (0.00 % on
  tok/char everywhere). English is 0.00 % under `grapheme_denominator` — the
  ASCII control holding exactly, as `tests/test_counters.py` pins.
- `all_on` ≠ the sum of the singles (hin tok/char +52.67 % vs
  `grapheme_denominator` alone at +53.05 %), so the flags are **not** perfectly
  orthogonal. The interaction is recorded, not smoothed.

**Died — my "exactly zero" null control for `preserve_case` was too strong.**

I predicted in H-03 that the Hindi delta *must be exactly `0.000`* and that any
non-zero value voids the experiment. Measured on FLORES:

| lang | tokens baseline → `preserve_case` | fertility delta |
|---|---|---|
| eng | 27,994 → 27,044 | −4.294 × 10⁻² |
| hin | 200,696 → 200,688 | −3.574 × 10⁻⁴ |
| tel | 350,848 → 350,748 | −5.826 × 10⁻³ |

Hindi is **not** exactly zero — 8 tokens out of 200,696. FLORES Indic text
contains embedded Latin (proper nouns, acronyms, digits), so case folding has
something to act on. The control is real but the correct statement is *"zero up
to embedded Latin"*, and the discriminating quantity is the **ratio**: English
moves ~120× more in relative terms. On the 20-line starter sample the
prediction held exactly, which is precisely how a too-strong claim survives a
small corpus. Logged in `AI_USAGE.md`.

**Not done, deliberately:** no prose findings, no `FINDINGS.md`. BLUEPRINT §3
Phase 4 — *"Do not write any prose findings."* Every number above is in
`results/ablation.json` under a named key and gets rendered in Phase 7.

---

### 2026-09-07 — Block 7: Phase 5 corrected analysis (A3)

**Hypothesis:** none under test. This stage builds the grid that the
denominator argument will be made from; the argument itself is reserved.

**Ran:** `make analyze` (36 s, offline) → `results/analysis.json` +
`deliverable/figures/*.png`. Grid = 4 tokenizers × 7 languages × 5
denominators × {micro, macro} with paired bootstrap 95 % CIs, all ratios
normalised to English.

**Came back — ratio to eng, macro, gpt2 (the encoding the v0 run used):**

| lang | per word | per grapheme | per UTF-8 byte | per parallel sentence |
|---|---|---|---|---|
| hin | 6.32 [6.26, 6.39] | 11.30 [11.18, 11.43] | 2.88 [2.85, 2.90] | 7.42 [7.33, 7.51] |
| ben | 10.80 [10.68, 10.91] | 15.40 [15.23, 15.58] | 3.60 [3.57, 3.63] | 9.61 [9.50, 9.71] |
| mar | 9.03 [8.92, 9.13] | 12.77 [12.63, 12.92] | 2.89 [2.87, 2.92] | 7.86 [7.78, 7.95] |
| tel | 16.74 [16.53, 16.95] | 22.23 [21.95, 22.51] | 4.79 [4.75, 4.83] | 12.97 [12.81, 13.13] |
| kan | 18.50 [18.27, 18.74] | 19.62 [19.42, 19.83] | 4.73 [4.69, 4.77] | 13.59 [13.43, 13.75] |
| tam | 20.29 [20.04, 20.54] | 20.36 [20.15, 20.57] | 4.82 [4.77, 4.86] | 15.54 [15.36, 15.72] |

**Same corpus, same denominator (parallel sentence), varying only the
tokenizer:**

| lang | gpt2 | cl100k | xlmr | muril |
|---|---|---|---|---|
| hin | 7.42 | 4.77 | 1.25 | 1.16 |
| ben | 9.61 | 5.88 | 1.37 | 1.00 |
| mar | 7.86 | 5.06 | 1.22 | 1.06 |
| tel | 12.97 | 8.29 | 1.32 | 1.20 |
| kan | 13.59 | 8.86 | 1.35 | 1.07 |
| tam | 15.54 | 7.64 | 1.35 | 1.06 |

vocab: gpt2 50,257 · cl100k 100,277 · muril 197,285 · xlmr 250,002.

**Absolute tokens per parallel sentence (macro), for scale:** eng ranges
26.7–30.3 across the four tokenizers; hin ranges 31.5 (muril) to 198.3 (gpt2).

**Now believe:**

- **The structural claim holds and is now pinned by a test.** Under the
  parallel-sentence denominator, micro and macro are *identical for every
  language and every tokenizer* — every line's denominator is 1, so the
  weighting choice cannot move the number. It is the only one of the four
  with that property; `tests/test_grid.py` asserts both it and the contrast
  case.
- **The four denominators disagree by roughly 4× on the same corpus, same
  tokenizer, same numerator.** For Hindi under gpt2: 2.88 per byte, 6.32 per
  word, 7.42 per sentence, 11.30 per grapheme. None of the CIs overlap.
- The CIs are **paired** bootstraps over sentence indices, not independent
  resamples of two languages. The corpus is parallel, so index *i* is the same
  sentence in both series; resampling independently would discard that
  covariance and widen every interval. `tests/test_grid.py` includes a
  degenerate case where a perfectly co-varying pair yields a zero-width
  interval, which independent resampling could not produce.
- Every pivot ratio is exactly 1.000 for eng under all five denominators — the
  arithmetic control.

**Died:** two design attempts, both replaced.

- I first computed the absolute per-cell CI by calling the paired-ratio
  bootstrap against a constant series of 1.0. It gives the right answer (the
  pivot mean is always 1) but it is an obscure way to say "bootstrap the mean",
  so it was replaced with a direct `bootstrap_ci` call.
- Figures initially embedded a `Software: Matplotlib vX.Y` PNG tag, which
  would have changed every figure's bytes on a dependency bump while the data
  stayed identical. Suppressed via `metadata={"Software": None}`;
  `tests/test_figures.py` renders each figure twice and compares SHA-256.

**Module added:** `src/audit/metrics/grid.py`. BLUEPRINT §0 lists `metrics/` as
counters/fertility/aggregation; the grid assembly is pure and belongs under
`metrics/`, but did not fit any of the three. Flagged like `stages.py` was.

**Reserved — the denominator argument is not written.** BLUEPRINT §3 Phase 5
assigns it to the human ("*Your job: the denominator argument… Say it with your
numbers*"). The numbers exist above and in `results/analysis.json`; no sentence
ranking the denominators or recommending one for the routing decision has been
authored. Same for every interpretive line in the templates.

---

### 2026-09-07 — Block 8: Phase 6 Part B implementation

**Hypothesis under test:** that the script, deriving everything by parsing
`model_spec.md` and `bench_log.csv`, reproduces the Block 3 hand derivation.
BLUEPRINT §3: *"If my hand calculation and your script disagree, report the
disagreement — do not reconcile silently."*

**Ran:** `make bench` → `results/bench.json` + `throughput_curve.png`.

**Came back — script vs the pre-registered hand values. Zero disagreements:**

| term | hand (pre-registered) | script | |
|---|---|---|---|
| KV bytes/token | 114,688 | 114,688 | ✓ |
| group ratio | 3.0 | 3.0 | ✓ |
| MHA equivalent B/token | 344,064 | 344,064 | ✓ |
| decimal: KV budget | 12.080 GB | 12.080 GB | ✓ |
| decimal: capacity | 105,329 tok | 105,329 tok | ✓ |
| decimal: exact seqs | 25.72 | 25.7151 | ✓ |
| decimal / binary ceiling | 25 / 28 | 25 / 28 | ✓ |
| B3 way 1 (wall clock) | 200.92 tok/s | 200.9156 | ✓ |
| B3 way 2 (ITL decode) | 249.82 tok/s | 249.8178 | ✓ |
| max identity error | 0.022 % | 0.0219 % | ✓ |

Nothing to report under the disagreement clause. The hand derivation was
timestamped before `bench/` existed, so this is a genuine check of the parser
rather than a restatement of it.

**Now believe:**

- **The GB/GiB ambiguity is settled empirically, and the check can reject.**
  Under the decimal reading, `preempted_seqs == batch_size − 25` on *every*
  row of the long-prompt sweep. Under the binary reading (ceiling 28) it
  predicts 4 and 20 where the log shows 7 and 23. `correlate_ceiling` is
  tested for its ability to fail, not only to pass — a check that cannot
  reject proves nothing.
- **Capacity inversion agrees independently.** Unsaturated rows (bs 8, 16, 24)
  all invert to 105,703 tokens against 105,329 predicted — 0.35 %. Saturated
  rows are excluded and flagged, since a clipped `kv_cache_util` cannot be
  inverted and treating it as if it could would manufacture agreement.
- **The knee sits at batch 24**, the last tested batch below the predicted
  ceiling of 25.72. At the knee: `kv_cache_util` 0.93, `preempted_seqs` 0,
  ttft 500.5 ms. Immediately after (batch 32): util 0.97, preempted 7, ttft
  636.9 ms.
- **The two goodput derivations use disjoint column sets** — (`num_requests`,
  `gen_len`, `wall_clock_s`) and (`batch_size`, `itl_ms_p50`). A shared column
  would make their agreement circular; a test asserts the intersection is
  empty.
- `reported_tok_s` reconstructs as `requests × (prompt+gen) / wall` to within
  0.022 % on all 13 rows, and for the batch-24 row the ratio of that counter
  to output-tokens-per-second is exactly 8.00 — which is (3584+512)/512.

**Died:** two implementation attempts.

- `parse_log` first built rows via `**kwargs` with types inferred from
  `dataclasses.fields`. Under `from __future__ import annotations` the field
  types are *strings*, so the converter was comparing `f.type == "int"`. It
  worked, but an int/float slip would have silently truncated `kv_cache_util`
  to 0 with no error. Replaced with an explicit eleven-line constructor.
- `_gpu_memory_gb` first used "first number in the string". The GPU row reads
  `1× NVIDIA L4 (24 GB)`, so that returns **1** — the device count — as the
  memory capacity. Replaced with a parenthesised-capacity regex; a test pins
  the case.

**Live-edit robustness.** `tests/test_bench.py` parses *modified* spec text,
not only the shipped file: doubling `layers` doubles KV bytes/token, changing
`KV heads (GQA)` changes the group ratio, switching `KV cache precision` to
fp8 halves the cache, deleting a field raises naming it, and an unparseable
value raises rather than defaulting. If any spec value were hardcoded, these
are what would catch it.

**All strict-xfail contract tests are now live.** The suite is 123 passed, 0
xfailed — `test_kv_math.py` included, with its explicit MHA-vs-GQA pair.

#### Interpretation — still reserved

- `TODO(pratik): interpretation` — B2's mechanism and the config change with a
  predicted quantitative effect.
- `TODO(pratik): interpretation` — which column §2 read, and why one reading
  carries both of its conclusions.
- `TODO(pratik): interpretation` — what §2 should have said, and B4's
  confirming counter with its expected value.

Every quantity those sentences need is in `results/bench.json` under a named
key. No sentence naming the misread column has been authored.

---

## Environment deviations

Deviations from CLAUDE.md §2 forced by the machine, recorded so a grader can
tell a constraint from a choice.

- **Python 3.11 is not a system package here** (host ships 3.14 only, and
  installing 3.11 via `dnf` needs root). Resolved with `uv python install
  3.11`, which fetches a standalone CPython 3.11.16 into the user's data
  directory. `requires-python = "==3.11.*"` is pinned in `pyproject.toml`, so
  the constraint is enforced, not merely intended.
