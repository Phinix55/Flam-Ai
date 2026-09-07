# The Audit

An audit of `starter_kit/` — a v0 tokenizer-fertility benchmark (`fertility.py`,
`REPORT_v0.md`) and a serving-capacity report (`bench/`). Every number in
`deliverable/` is rendered from a `results/*.json` key; nothing is typed by hand.

```bash
make setup    # Python 3.11 + pinned deps
make corpus   # ONLY network stage: FLORES-200 + tokenizers -> .cache/
make check    # ruff + mypy --strict + pytest
make reproduce  # offline, deterministic rebuild of results/ and deliverable/
```

`starter_kit/` is vendored verbatim and never modified; all changes to it live
behind flags in `src/audit/ablation/`. Read `CLAUDE.md` for the working rules,
`BLUEPRINT.md` for the sequence, and `NOTEBOOK.md` for the chronological log
including dead ends.
