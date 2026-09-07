"""Results JSON -> markdown tables, with every numeral traced to its key.

Formatting only. This module never computes a value; it reads one from a
results artefact and formats it. Anything that needs arithmetic belongs in
``metrics/`` or ``bench/``, where it is tested.

Numbers are formatted **here, in Python**, never inside a template. That
is what makes CLAUDE.md rule 3 enforceable: a template containing no
digits cannot emit an untraceable one, so every numeral in a rendered
deliverable arrives through ``Tracer.fmt`` and carries the results key it
came from.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

NUMERAL_TOKEN = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True, slots=True)
class Traced:
    """One numeral that reached a deliverable, and where it came from."""

    text: str
    key: str
    kind: str


@dataclass
class Tracer:
    """Records the provenance of every numeral emitted into a deliverable.

    ``fmt`` is the only sanctioned way to turn a number into deliverable
    text. ``structural`` is the narrow escape hatch for numerals that are
    genuinely not data -- a finding's ordinal, for instance -- and it
    demands a reason, which is then reported in the build output so the
    exemptions stay visible rather than accumulating silently.
    """

    entries: dict[str, Traced] = field(default_factory=dict)

    def _record(self, text: str, key: str, kind: str) -> str:
        """Register every numeral *token* inside ``text``, not ``text`` itself.

        A formatted value carries decoration -- a sign from ``+.3f``, a
        bracket from a CI pair, a unit. The validator scans the rendered
        document for bare numerals, so registering the whole formatted
        string would never match. Registering its tokens makes the two
        sides agree on what a numeral is.
        """
        for match in NUMERAL_TOKEN.finditer(text):
            self.entries.setdefault(match.group(), Traced(match.group(), key, kind))
        return text

    def fmt(self, value: float | int, key: str, spec: str = ".4f") -> str:
        """Format ``value`` and record it against its results key."""
        return self._record(format(value, spec), key, "results")

    def text(self, value: str, key: str) -> str:
        """Register a results-derived *string* and the numerals inside it.

        Some results values are prose that embeds figures -- a
        hypothetical's description carries the context length it changes.
        The string came from a results key, so its numerals are traced to
        that key rather than declared structural.
        """
        return self._record(value, key, "results")

    def structural(self, text: str, reason: str) -> str:
        """Declare a non-data numeral. Reported, never silently allowed."""
        return self._record(text, reason, "structural")

    def texts(self) -> set[str]:
        return set(self.entries)

    def key_for(self, text: str) -> str | None:
        entry = self.entries.get(text)
        return None if entry is None else entry.key

    def structural_exemptions(self) -> list[Traced]:
        return sorted(
            (e for e in self.entries.values() if e.kind == "structural"),
            key=lambda e: e.text,
        )


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render a GitHub-flavoured markdown table. Raises on ragged rows."""
    width = len(headers)
    for index, row in enumerate(rows):
        if len(row) != width:
            msg = (
                f"Row {index} has {len(row)} cells but the header has {width}. "
                "Refusing to pad or truncate a results table."
            )
            raise ValueError(msg)
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def ablation_table(ablation: dict[str, Any], tracer: Tracer, form: str = "NFC") -> str:
    """The evidence grid: one row per flag, baseline -> flagged, with delta."""
    sweep = ablation["sweep"][form]
    deltas = ablation["deltas"][form]
    languages = ablation["provenance"]["config"]["languages"]
    codes = [lang["code"] for lang in languages]
    rows = []
    for arm in sorted(deltas):
        for code in codes:
            base = sweep["baseline"][code]["fertility"]
            after = sweep[arm][code]["fertility"]
            rel = deltas[arm][code]["fertility_rel_pct"]
            rows.append(
                [
                    f"`{arm}`",
                    code,
                    tracer.fmt(
                        base, f"ablation.sweep.{form}.baseline.{code}.fertility"
                    ),
                    tracer.fmt(after, f"ablation.sweep.{form}.{arm}.{code}.fertility"),
                    tracer.fmt(
                        rel,
                        f"ablation.deltas.{form}.{arm}.{code}.fertility_rel_pct",
                        "+.3f",
                    ),
                ]
            )
    return markdown_table(
        ["flag", "lang", "baseline tok/word", "flagged tok/word", "rel Δ %"], rows
    )


def analysis_table(analysis: dict[str, Any], tracer: Tracer, denominator: str) -> str:
    """Tokenizer x language for one denominator, with bootstrap CIs."""
    languages = analysis["languages"]
    tokenizers = sorted(analysis["tokenizers"])
    rows = []
    for lang in languages:
        row = [lang]
        for key in tokenizers:
            base = f"analysis.grid.{key}.ratio_to_pivot.{denominator}.{lang}"
            cell = analysis["grid"][key]["ratio_to_pivot"][denominator][lang]
            row.append(
                f"{tracer.fmt(cell['macro'], base + '.macro')} "
                f"[{tracer.fmt(cell['macro_ci_low'], base + '.macro_ci_low')}, "
                f"{tracer.fmt(cell['macro_ci_high'], base + '.macro_ci_high')}]"
            )
        rows.append(row)
    return markdown_table(["lang", *tokenizers], rows)


def corpus_table(stats: dict[str, Any], tracer: Tracer, form: str = "NFC") -> str:
    """Per-language descriptive counts for the evaluation corpus."""
    per_language = stats["by_normalisation"][form]["per_language"]
    fields = ("sentences", "whitespace_words", "graphemes", "codepoints", "utf8_bytes")
    rows = [
        [
            entry["code"],
            entry["script"],
            *[
                tracer.fmt(
                    entry[name],
                    f"corpus_stats.by_normalisation.{form}.per_language.{entry['code']}.{name}",
                    "d",
                )
                for name in fields
            ],
        ]
        for entry in per_language
    ]
    return markdown_table(["lang", "script", *fields], rows)


def kv_table(bench: dict[str, Any], tracer: Tracer) -> str:
    """B1's arithmetic, one row per named intermediate term."""
    breakdown = bench["b1"]["kv_bytes_per_token"]
    order = (
        "k_and_v_factor",
        "layers",
        "kv_heads",
        "head_dim",
        "dtype_bytes",
        "kv_dim_per_layer",
        "bytes_per_token",
        "group_ratio",
        "mha_bytes_per_token",
    )
    rows = [
        [
            f"`{name}`",
            tracer.fmt(
                breakdown[name],
                f"bench.b1.kv_bytes_per_token.{name}",
                ".1f" if isinstance(breakdown[name], float) else "d",
            ),
        ]
        for name in order
    ]
    return markdown_table(["term", "value"], rows)


def concurrency_table(bench: dict[str, Any], tracer: Tracer) -> str:
    """Memory budget -> concurrency ceiling, per memory-unit reading."""
    ceilings = bench["b1"]["concurrency_ceiling_by_memory_unit"]
    order = (
        "gpu_memory_bytes",
        "usable_bytes",
        "weights_bytes",
        "runtime_overhead_bytes",
        "kv_budget_bytes",
        "bytes_per_sequence",
        "kv_capacity_tokens",
        "exact_sequences",
        "max_concurrent_sequences",
    )
    units = sorted(ceilings)
    rows = [
        [
            f"`{name}`",
            *[
                tracer.fmt(
                    ceilings[unit][name],
                    f"bench.b1.concurrency_ceiling_by_memory_unit.{unit}.{name}",
                    ".4f" if isinstance(ceilings[unit][name], float) else "d",
                )
                for unit in units
            ],
        ]
        for name in order
    ]
    return markdown_table(["term", *units], rows)


def goodput_table(bench: dict[str, Any], tracer: Tracer) -> str:
    """B3's two independent derivations, with the columns each used."""
    rows = [
        [
            derivation["method"],
            ", ".join(f"`{c}`" for c in derivation["columns_used"]),
            derivation["tokens_counted"],
            tracer.fmt(
                derivation["value_tok_s"],
                f"bench.b3.goodput_derivations.{index}.value_tok_s",
                ".2f",
            ),
        ]
        for index, derivation in enumerate(bench["b3"]["goodput_derivations"])
    ]
    return markdown_table(["derivation", "columns used", "counts", "tok/s"], rows)


def reported_numbers_table(ablation: dict[str, Any], tracer: Tracer) -> str:
    """What ``REPORT_v0.md`` would have printed under each single change.

    A2 asks for the effect of each claimed flaw **on the reported
    numbers**. Those are the ten-line ``corpus_sample`` figures the deck
    carries, not the FLORES ones -- so this table runs the same flag grid
    over the same input the original run used. The baseline row must
    reproduce the published deck values exactly, which is what makes every
    other row in the table a statement about the report rather than about
    a different corpus.
    """
    arms = ablation["legacy_sample"]
    rows = []
    for arm in ["baseline", *sorted(a for a in arms if a != "baseline")]:
        results = arms[arm]
        by_lang = {r["lang"]: r for r in results}
        eng, hin = by_lang["eng"], by_lang["hin"]
        key = f"ablation.legacy_sample.{arm}"
        rows.append(
            [
                f"`{arm}`",
                tracer.fmt(eng["fertility"], f"{key}.eng.fertility", ".2f"),
                tracer.fmt(hin["fertility"], f"{key}.hin.fertility", ".2f"),
                tracer.fmt(eng["tokens_per_char"], f"{key}.eng.tokens_per_char", ".3f"),
                tracer.fmt(hin["tokens_per_char"], f"{key}.hin.tokens_per_char", ".3f"),
                tracer.fmt(
                    hin["fertility"] / eng["fertility"], f"{key}.hin_eng_ratio", ".2f"
                ),
            ]
        )
    return markdown_table(
        [
            "flag",
            "eng tok/word",
            "hin tok/word",
            "eng tok/char",
            "hin tok/char",
            "hin:eng",
        ],
        rows,
    )


def hypotheticals_table(bench: dict[str, Any], tracer: Tracer) -> str:
    """Predicted effect of each stated config change. Ranks nothing."""
    rows = []
    for name, entry in sorted(bench["b2"]["hypotheticals"].items()):
        key = f"bench.b2.hypotheticals.{name}"
        rows.append(
            [
                f"`{name}`",
                tracer.text(str(entry["changes"]), f"{key}.changes"),
                tracer.fmt(entry["ceiling_before"], f"{key}.ceiling_before", "d"),
                tracer.fmt(entry["ceiling_after"], f"{key}.ceiling_after", "d"),
                tracer.fmt(
                    entry["ceiling_multiplier"], f"{key}.ceiling_multiplier", ".2f"
                ),
            ]
        )
    return markdown_table(
        ["change", "what it alters", "ceiling before", "ceiling after", "x"], rows
    )
