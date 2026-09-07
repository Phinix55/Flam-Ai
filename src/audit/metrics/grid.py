"""The A3 grid: tokenizers x languages x denominators. Pure.

One numerator, four denominators. Each line is tokenized **once** per
tokenizer and every denominator is stored alongside the token count, so
any ratio -- including one a grader asks for during the defense -- is
re-derivable without re-running a tokenizer.

What each denominator holds constant, which is the whole content of A3:

===============  ===========================================================
``words``        the whitespace-splitting rule. Morphology is *not* held
                 constant: an agglutinative language packs more meaning
                 into one word, so this ratio mixes tokenizer behaviour
                 with word formation.
``graphemes``    UAX #29 user-perceived characters. Not uniform across
                 scripts (see ``counters.count_graphemes``).
``utf8_bytes``   wire and storage cost. Holds the encoding constant, not
                 the content: Indic codepoints cost 3 bytes to Latin's 1.
``sentences``    propositional content, via the parallel index. The only
                 denominator whose unit is the same object in every
                 language.
===============  ===========================================================

A structural consequence worth stating: under ``sentences`` every line's
denominator is 1, so micro and macro are algebraically identical. It is
the one denominator whose value cannot depend on the weighting choice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from audit.metrics.aggregation import (
    bootstrap_ci,
    bootstrap_ratio_ci,
    macro_average,
    micro_average,
    per_line_ratios,
)
from audit.metrics.fertility import DENOMINATORS, LineMeasurement, measure_corpus
from audit.tokenizers.base import TokenizerAdapter

Measurements = dict[str, tuple[LineMeasurement, ...]]


def measure_all(
    corpus: Mapping[str, Sequence[str]], tokenizer: TokenizerAdapter
) -> Measurements:
    """Tokenize every language once. ``{lang: per-line measurements}``."""
    return {lang: measure_corpus(texts, tokenizer) for lang, texts in corpus.items()}


def _series(
    measurements: Sequence[LineMeasurement], denominator: str
) -> tuple[list[int], list[int]]:
    numerators = [m.tokens for m in measurements]
    denominators = [m.denominator(denominator) for m in measurements]
    return numerators, denominators


def cell(
    measurements: Sequence[LineMeasurement],
    denominator: str,
    *,
    seed: int,
    iterations: int,
    confidence: float,
) -> dict[str, Any]:
    """One (tokenizer, language, denominator) cell, micro and macro."""
    numerators, denominators = _series(measurements, denominator)
    ratios = per_line_ratios(numerators, denominators)
    low, high = bootstrap_ci(
        ratios,
        generator=np.random.default_rng(seed),
        iterations=iterations,
        confidence=confidence,
    )
    return {
        "micro": micro_average(numerators, denominators),
        "macro": macro_average(numerators, denominators),
        "macro_ci_low": low,
        "macro_ci_high": high,
        "total_tokens": sum(numerators),
        "total_denominator": sum(denominators),
        "n": len(ratios),
    }


def ratio_cell(
    measurements: Sequence[LineMeasurement],
    pivot_measurements: Sequence[LineMeasurement],
    denominator: str,
    *,
    seed: int,
    iterations: int,
    confidence: float,
) -> dict[str, Any]:
    """One language's ratio to the pivot, with a paired bootstrap CI.

    Paired because the two series are the same sentences; see
    ``aggregation.bootstrap_ratio_ci``.
    """
    numerators, denominators = _series(measurements, denominator)
    pivot_n, pivot_d = _series(pivot_measurements, denominator)
    ratios = per_line_ratios(numerators, denominators)
    pivot_ratios = per_line_ratios(pivot_n, pivot_d)
    low, high = bootstrap_ratio_ci(
        ratios,
        pivot_ratios,
        generator=np.random.default_rng(seed),
        iterations=iterations,
        confidence=confidence,
    )
    return {
        "micro": micro_average(numerators, denominators)
        / micro_average(pivot_n, pivot_d),
        "macro": macro_average(numerators, denominators)
        / macro_average(pivot_n, pivot_d),
        "macro_ci_low": low,
        "macro_ci_high": high,
    }


def build(
    measurements: Measurements,
    *,
    pivot: str,
    seed: int,
    iterations: int,
    confidence: float,
) -> dict[str, Any]:
    """Absolute cells and pivot-normalised ratios for every denominator."""
    if pivot not in measurements:
        msg = f"Pivot language {pivot!r} absent from the measured set."
        raise KeyError(msg)
    kwargs = {"seed": seed, "iterations": iterations, "confidence": confidence}
    absolute = {
        denominator: {
            lang: cell(series, denominator, **kwargs)  # type: ignore[arg-type]
            for lang, series in measurements.items()
        }
        for denominator in DENOMINATORS
    }
    ratios = {
        denominator: {
            lang: ratio_cell(
                series,
                measurements[pivot],
                denominator,
                **kwargs,  # type: ignore[arg-type]
            )
            for lang, series in measurements.items()
        }
        for denominator in DENOMINATORS
    }
    return {"absolute": absolute, "ratio_to_pivot": ratios}
