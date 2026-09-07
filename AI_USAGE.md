# AI_USAGE

An honest account of where AI did the work, where I did, and where it was
wrong. The last section is the point of the document.

---

## Where AI did the work

**Session 0 — scaffolding**

- `src/audit/**`, `pyproject.toml`, `Makefile`, `tests/**`: generated, reviewed
  line by line.
- `tests/` contract stubs are `xfail(strict=True)` rather than `skip`.
  Reviewed and kept: a skipped gate reports green while proving nothing,
  whereas strict xfail turns the eventual XPASS into a hard failure and forces
  the marker off. `make parity` is therefore honest about not yet being armed.
- `AblationFlags` ships with zero fields and machinery written over
  `dataclasses.fields`. Kept deliberately: naming a flag is asserting a claim,
  and claim selection is mine, not the model's.

**Session 1 — Phase 1 recon**

- `NOTEBOOK.md` → `## Unverified hypotheses`: the 15 candidates, their
  categories, experiments, predicted directions and confidences were drafted by
  the model from a read of `fertility.py`, `REPORT_v0.md` and the corpus
  sample. Reviewed item by item.
- Every quantitative observation in that section was re-derived from a
  byte-level read of the input files rather than accepted from prose — which
  caught one arithmetic error in the draft (see below).

**Session 2 — claim selection and Phase 2 parity gate**

- **Claim selection.** Which six of the 15 candidates became `AblationFlags`
  fields was decided by the model, not by me. See the correction below and the
  selection entry in `NOTEBOOK.md`, which records the criteria applied and why
  each unselected candidate was left out.
- `src/audit/ablation/legacy.py`, `flags.py`, `metrics/counters.py`,
  `tests/test_legacy_parity.py`: generated, reviewed line by line.
- Two review changes I kept: line ingestion reproduces text-mode file iteration
  rather than `str.splitlines()` (which breaks on VT/FF/NEL/LS/PS and would
  have been a silent unmeasured ablation), and the parity gate proves float
  equality with `==` rather than `approx`, since the original prints only 2–3
  decimals and any tolerance would hide a real arithmetic difference.
- The per-flag *wiring probes* were added beyond the phase brief, after
  noticing that a declared-but-unwired flag would produce a zero delta
  indistinguishable from a genuine null.

---

## Where I wrote it myself

**Nothing in this submission's reasoning.** This is the entry that matters, so
it is stated plainly rather than softened.

`CLAUDE.md` rule 6 — which I wrote — reserves for me every sentence that
asserts a conclusion, ranks a cause or recommends an action, and the model held
that line through nine sessions, leaving thirty-three
`TODO(pratik): interpretation` markers. I then instructed it to write them. It
did. The affected text is:

- the "what this corpus cannot tell you" paragraph in `partA/CORPUS.md`
- every claim, category and direction in `partA/FINDINGS.md`, including which
  two candidates went to the rejected-claims section
- the denominator argument in `partA/ANALYSIS.md`
- the routing recommendation, caveat and monitor metric in `partA/MEMO.md`
- B2's mechanism, B3's misread-column diagnosis and B4's counter in
  `partB/ANSWERS.md`
- the recommendation, success threshold, kill criterion and day-one experiment
  in `partC/memo.md`

Every one of those sentences cites a number this repo measured, and the
rendering pipeline will not emit a figure that is not traceable to a
`results/*.json` key — so the *evidence* is sound and reproducible regardless
of who wrote the prose around it. But the assignment asks whether I know which
parts of my submission I understand, and the honest answer is that the
arguments are reconstructions of the model's reasoning, not records of mine.

Also model-produced, and logged in the sessions above: the selection of which
six claims to test, the B1/B3 hand derivations, and Part C's arithmetic.

The interpretive sentences are isolated in
`src/audit/reporting/interpretation.py` and in the jinja templates, so exactly
what was authored is auditable in two places rather than scattered.

---

## Where AI misled me

**Session 1 — a mis-summed corpus statistic, caught before it reached a
deliverable.**

- **Claimed:** *"`hin_sample.txt` is 774 bytes / 296 codepoints over 10
  lines"*, in the H-02 observation block.
- **Caught by:** re-deriving the figure from the per-line output instead of
  accepting the summary line —
  `30+38+30+32+24+24+36+22+26+28 = 290`, not 296; and 774 B is the file
  including its 10 line terminators, so the text is 764 B. Confirmed with
  `Path(...).read_text().replace("\n","")` → `text_bytes=764
  text_codepoints=290`.
- **Lesson:** a total stated alongside correct per-item figures is the easiest
  kind of number to wave through, because the per-item data next to it looks
  like corroboration. It is not. This is exactly the failure mode CLAUDE.md
  rule 3 exists to prevent — and the reason no digit may be typed into
  `deliverable/` prose. Every figure there is rendered from a `results/*.json`
  key, so a mis-sum of this kind cannot survive into a graded artefact.

**Session 2 — a confidently wrong assumption about case folding, caught by the
test it was written for.**

- **Claimed:** that `"ABC DEF"` is a valid probe for the `preserve_case` flag —
  i.e. that case folding changes gpt2 token counts on caseful Latin text.
- **Caught by:** `pytest -m parity` failing on
  `test_flag_actually_reaches_its_code_path[preserve_case]`. Measured:
  `"ABC DEF"` is 2 tokens either way; so are `"Bengaluru International
  Airport"` and `"MG Road"`. `"NASA and ISRO"` gains a token when folded,
  `"Thursday"` gains one, `"Quarterly Review"` **loses** one.
- **Lesson:** the direction of the case-folding effect is not uniform, and
  neither is its presence. Had the wiring probe not existed, this flag would
  still have been "wired" — but I would have been carrying a mental model of a
  one-directional effect into Phase 4 and would have mis-read a partially
  cancelling net result. The probe was written to catch dead wiring and caught
  a wrong belief instead.

**Session 3 — a null control I wrote too strongly, corrected by the sweep.**

- **Claimed:** in H-03, verbatim — *"The Hindi delta must be exactly `0.000`. A
  non-zero Hindi delta means the flag is not isolating what it claims and the
  experiment is void."*
- **Caught by:** `make ablate` on FLORES devtest. Hindi tokens go 200,696 →
  200,688 under `preserve_case` — a delta of −3.574 × 10⁻⁴, not zero. FLORES
  Indic text carries embedded Latin (proper nouns, acronyms, digits), so case
  folding has something to act on. On the 20-line starter sample the prediction
  held exactly.
- **Lesson:** the claim was right about the mechanism and wrong about its
  bound, and a 20-line corpus was too small to expose the difference. The
  defensible form is *"zero up to embedded Latin"*, with the discriminating
  quantity being the ratio — English moves ~120× more in relative terms. I had
  written this control up as the strongest self-check in the list; it was the
  strongest *and* it was overstated, which is a combination worth remembering.

**Session 5 — two template bugs that would have shipped as prose.**

- **Claimed:** implicitly, by writing `{{ partc.items }}` in the Part C
  template, that Jinja would resolve `.items` to my dictionary key.
- **Caught by:** `make render` failing with `UntracedNumeralError` on
  `partC/memo.md`. Jinja had resolved it to Python's `dict.items` **method**
  and rendered `<built-in method items of dict object at 0x7f…>` into the memo.
  Only the hex address digits tripped the numeral check.
- **Lesson:** the rule-3 validator was built to stop fabricated *figures* and
  it caught a fabricated *sentence* instead. A deliverable can be wrong in ways
  the author never thought to test for, which is the argument for a check that
  runs on the rendered artefact rather than on the inputs.

A second, smaller one in the same session: my identifier rule read `A100-80GB`
as a figure, because it looked two characters back and found a hyphen preceded
by a digit rather than a letter. Fixed by walking the whole token. Recorded
because the near-miss direction matters — had the rule been *looser* instead of
stricter, it would have silently exempted real figures.

_(further entries per session; any entry arising from a measurement will be
cross-referenced to the rejected-claims section of
`deliverable/partA/FINDINGS.md`)_

---

**Sessions 3-5 — corpus, ablation, analysis, Part B, rendering**

- `corpus/`, `metrics/`, `ablation/runner.py`, `bench/`, `reporting/`,
  `partc.py` and their tests: generated, reviewed file by file.
- Design decisions I made during review and kept: the bootstrap over
  cross-language ratios is **paired** over sentence indices rather than
  independent (the corpus is parallel, so independent resampling would discard
  the covariance and inflate every interval); `correlate_ceiling` is tested for
  its ability to *reject* a wrong ceiling, not only to accept the right one;
  and the rule-3 validator formats numbers in Python rather than in templates,
  which is what makes "every numeral traces to a key" checkable at all.
- Part C's arithmetic takes two inputs from this repo's own measurements
  (response length from the A3 grid, second-pass cost from B3) instead of
  assuming round numbers.

---

## What I would not be able to defend

**As of submission:**

- **I did not write the reasoning.** See the section above. Each argument is
  defensible *from the numbers* — every figure re-derives with `make
  reproduce` — but "why this claim and not another", "why this denominator",
  "why path (a)" are arguments I would be reconstructing under questioning
  rather than recalling. On a 30-minute defense that is the difference the
  session is designed to find.
- **Four specific things I should be able to do cold before defending:**
  re-derive `2 x layers x kv_heads x head_dim x dtype_bytes` from
  `model_spec.md`; state what `reported_tok_s` counts and why that single
  misreading carries both of REPORT_v0 §2's conclusions; say why the parallel
  sentence is the only denominator that holds meaning constant; and explain why
  `perturb_global_rng` is in the rejected section rather than the findings.

**Earlier, and still true:**

- **I did not select the six claims under test.** The model did. The criteria
  are written down and the flags are individually defensible, but "why these
  six and not the other nine" is currently a reconstruction of someone else's
  reasoning, not mine. Until I have re-derived that choice myself, this is the
  question I would fail on.
- **B1 and B3 were not derived by my own hand.** BLUEPRINT §3 block 3 assigns
  them to me specifically so that a hand/script disagreement in Phase 6 is
  detectable. The model produced the arithmetic instead. It is pre-registered in
  `NOTEBOOK.md` before `bench/` exists, so it still functions as an independent
  anchor against the parser — but it is not the independent *human* check the
  blueprint intends. The three interpretive B3 sentences are left as
  `TODO(pratik)` and remain genuinely unwritten.
- **The rule-3 validator proves less than it appears to.** It confirms every
  numeral in a deliverable matches *a* registered value; it cannot confirm the
  numeral is in the *right* place. A figure that coincidentally equals an
  unrelated registered value passes. It rules out fabrication, not mis-keying.
- **Part C's `sentences_per_response` is a guess.** Four, applied to FLORES
  sentence lengths, gives 119 tokens per response — plausibly short for real
  chat replies. The GPU-hours conclusion survives a 100× stretch, but any
  claim I make about *dataset* size does not inherit that robustness.
- **Ten interpretive sentences are still unwritten**, across all three parts.
  They are marked, not hidden, but the submission is not finished until I have
  written them myself.

**As of Phase 1** — recorded now rather than discovered at the defense:

- **Every prediction in the hypothesis list is a prediction.** Nothing in
  `## Unverified hypotheses` has been measured. If asked to defend any item
  today, the honest answer is "that is why it is in that section."
- **The H-01/H-02/H-03 predictions about `gpt2` on Devanagari** come from
  vocabulary provenance, not observation. No tokenizer has been loaded. All
  three could be wrong in sign as well as magnitude.
- **H-07's alignment signal is proper-noun position**, chosen because it needs
  no translation judgement. I have not verified the sample's alignment by
  translation, and the table in H-07 is evidence of index displacement, not
  proof of non-parallelism.
- **Sample-derived observations rest on 20 lines.** The double-space count
  (H-05) and the NFC no-op (H-13) are properties of this sample and may not
  hold on FLORES.
