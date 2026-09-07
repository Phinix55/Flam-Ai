"""The ablation sweep: baseline -> each flag alone -> all-on.

That grid is the evidence table for Part A. Each cell differs from the
baseline in exactly one respect, which is the entire basis for attributing
a delta to a specific behaviour.

The sweep drives ``ablation/legacy.py``, not the corrected ``metrics/``
path, because what is under measurement is the legacy pipeline's
behaviour. Routing it through corrected code would change two things at
once and make every delta uninterpretable.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from audit.ablation.flags import AblationFlags
from audit.ablation.legacy import LegacyResult, aggregate, measure_lines, read_lines
from audit.config import AuditConfig
from audit.corpus.prepare import load_parallel
from audit.metrics.aggregation import bootstrap_ci
from audit.tokenizers import registry
from audit.tokenizers.base import TokenizerAdapter

SWEEP_TOKENIZER = "gpt2"
"""The encoding the v0 run used. Held fixed across the whole sweep: the
ablation isolates code behaviour, so varying the tokenizer here would
confound it. Tokenizer variation is Phase 5's grid."""


def sweep_configurations() -> tuple[AblationFlags, ...]:
    """baseline, then one configuration per flag alone, then all-on.

    all-on is included so flag interaction is observable: if it differs
    from the composition of the singles, the flags are not orthogonal and
    that is a reportable result rather than a bug in the sweep.
    """
    singles = tuple(AblationFlags.only(name) for name in AblationFlags.flag_names())
    return (AblationFlags.all_off(), *singles, AblationFlags.all_on())


def _cell(
    text: str, tokenizer: TokenizerAdapter, flags: AblationFlags, config: AuditConfig
) -> dict[str, Any]:
    """One (language x normalisation x arm) cell of the grid."""
    lines = read_lines(text, flags)
    counts = measure_lines(lines, tokenizer, flags)
    fertility, tokens_per_char = aggregate(counts, flags)
    low, high = bootstrap_ci(
        [c.tokens / c.words for c in counts],
        generator=np.random.default_rng(config.seed),
        iterations=config.bootstrap_iterations,
        confidence=config.bootstrap_confidence,
    )
    return {
        "fertility": fertility,
        "tokens_per_char": tokens_per_char,
        "fertility_ci_low": low,
        "fertility_ci_high": high,
        "n_lines": len(lines),
        "total_tokens": sum(c.tokens for c in counts),
        "total_words": sum(c.words for c in counts),
        "total_chars": sum(c.chars for c in counts),
    }


def _corpora(config: AuditConfig, normalisation: str) -> dict[str, str]:
    """``{lang: corpus text}`` in the legacy pipeline's input shape."""
    records = load_parallel(config, normalisation)
    return {
        lang.code: "\n".join(r.texts[lang.code] for r in records)
        for lang in config.languages
    }


def run_sweep(config: AuditConfig) -> dict[str, Any]:
    """Execute the grid across languages x normalisation forms.

    Held constant within the grid: corpus, tokenizer, seed, code path.
    Only the flag vector varies.
    """
    tokenizer = registry.load(config, SWEEP_TOKENIZER)
    sweep: dict[str, Any] = {}
    for form in config.normalisation_forms:
        corpora = _corpora(config, form)
        sweep[form] = {
            flags.label(): {
                lang: _cell(text, tokenizer, flags, config)
                for lang, text in corpora.items()
            }
            for flags in sweep_configurations()
        }
    return sweep


def _relative(after: float, before: float) -> float | None:
    """Percent change, or None where the baseline is zero."""
    return None if before == 0 else (after - before) / before * 100.0


def deltas(sweep: dict[str, Any]) -> dict[str, Any]:
    """Absolute and relative deltas of each configuration vs baseline."""
    out: dict[str, Any] = {}
    for form, arms in sweep.items():
        baseline = arms["baseline"]
        out[form] = {
            label: {
                lang: {
                    f"{metric}_{suffix}": value
                    for metric in ("fertility", "tokens_per_char")
                    for suffix, value in (
                        ("abs", cell[metric] - baseline[lang][metric]),
                        (
                            "rel_pct",
                            _relative(cell[metric], baseline[lang][metric]),
                        ),
                    )
                }
                for lang, cell in langs.items()
            }
            for label, langs in arms.items()
            if label != "baseline"
        }
    return out


def headline_ratios(sweep: dict[str, Any], pivot: str) -> dict[str, Any]:
    """Each language's fertility relative to the pivot, per arm.

    This is the shape of the number ``REPORT_v0.md`` §1 reports, so it is
    the one the ablation has to move to be relevant to that claim.
    """
    return {
        form: {
            label: {
                lang: cell["fertility"] / langs[pivot]["fertility"]
                for lang, cell in langs.items()
            }
            for label, langs in arms.items()
        }
        for form, arms in sweep.items()
    }


def legacy_sample_arms(
    corpora: dict[str, str], tokenizer: TokenizerAdapter
) -> dict[str, list[LegacyResult]]:
    """The same grid on ``starter_kit/corpus_sample/``.

    Kept because the v0 report's published numbers come from these ten
    lines; a delta on FLORES answers "what is true", a delta here answers
    "what would the report have printed".
    """
    from audit.ablation.legacy import run

    return {
        flags.label(): run(corpora, tokenizer, flags)
        for flags in sweep_configurations()
    }
