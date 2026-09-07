"""Aggregation across lines: micro, macro, and bootstrap CIs. Pure.

Micro and macro answer different questions and are not interchangeable:

- **micro** = sum(tokens) / sum(denominator). Holds constant: the corpus
  as one body of text. Each line contributes in proportion to its length.
- **macro** = mean of per-line ratios. Holds constant: the sentence as the
  unit of observation. Each line contributes equally regardless of length,
  so short lines carry the same weight as long ones.

They coincide only when every line has the same denominator value. The gap
between them is itself a measurement, which is why both are always
reported.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Aggregate:
    """One aggregated ratio with its uncertainty."""

    micro: float
    macro: float
    macro_ci_low: float
    macro_ci_high: float
    n: int
    bootstrap_iterations: int
    seed: int


def _check_lengths(numerators: Sequence[int], denominators: Sequence[int]) -> None:
    if len(numerators) != len(denominators):
        msg = (
            f"Numerator/denominator length mismatch: {len(numerators)} vs "
            f"{len(denominators)}. Refusing to zip and silently drop rows."
        )
        raise ValueError(msg)
    if not numerators:
        msg = "Cannot aggregate an empty sequence."
        raise ValueError(msg)


def micro_average(numerators: Sequence[int], denominators: Sequence[int]) -> float:
    """Ratio of sums. Length-weighted."""
    _check_lengths(numerators, denominators)
    total = sum(denominators)
    if total == 0:
        msg = "Micro average undefined: denominators sum to zero."
        raise ZeroDivisionError(msg)
    return sum(numerators) / total


def macro_average(numerators: Sequence[int], denominators: Sequence[int]) -> float:
    """Mean of per-line ratios. Sentence-weighted."""
    return float(np.mean(per_line_ratios(numerators, denominators)))


def per_line_ratios(
    numerators: Sequence[int], denominators: Sequence[int]
) -> list[float]:
    """One ratio per line, raising on any zero denominator.

    Zero is not coerced to a sentinel and the row is not dropped: how a
    zero-denominator line is handled changes the reported mean, so the
    decision is forced upward to an explicit policy rather than made here.
    """
    _check_lengths(numerators, denominators)
    for index, denominator in enumerate(denominators):
        if denominator == 0:
            msg = (
                f"Zero denominator at line index {index}. Dropping or coercing "
                "it would change the reported mean silently; handle it "
                "explicitly upstream."
            )
            raise ZeroDivisionError(msg)
    return [n / d for n, d in zip(numerators, denominators, strict=True)]


def bootstrap_ci(
    values: Sequence[float],
    *,
    generator: np.random.Generator,
    iterations: int,
    confidence: float,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean.

    Takes an explicit ``Generator``; never touches global numpy random
    state, so two runs with the same seed give byte-identical bounds.
    """
    if not 0.0 < confidence < 1.0:
        msg = f"confidence must be in (0, 1), got {confidence}."
        raise ValueError(msg)
    if iterations < 1:
        msg = f"iterations must be >= 1, got {iterations}."
        raise ValueError(msg)
    sample = np.asarray(values, dtype=np.float64)
    if sample.size == 0:
        msg = "Cannot bootstrap an empty sample."
        raise ValueError(msg)
    draws = generator.integers(0, sample.size, size=(iterations, sample.size))
    means = sample[draws].mean(axis=1)
    tail = (1.0 - confidence) / 2.0
    low, high = np.quantile(means, [tail, 1.0 - tail])
    return float(low), float(high)


def bootstrap_ratio_ci(
    numerator_ratios: Sequence[float],
    pivot_ratios: Sequence[float],
    *,
    generator: np.random.Generator,
    iterations: int,
    confidence: float,
) -> tuple[float, float]:
    """Paired percentile bootstrap for a cross-language ratio of means.

    **Paired, not independent.** The corpus is parallel: index *i* is the
    same sentence in both languages. Resampling the two languages
    independently would break that pairing and inflate the interval,
    because it would treat "this sentence is long" as two unrelated draws
    instead of one. The same index vector is therefore applied to both
    series, which is what holds content constant inside each resample.

    Requires equal lengths -- unequal series are not a parallel corpus and
    the pairing would be a fiction.
    """
    if len(numerator_ratios) != len(pivot_ratios):
        msg = (
            f"Paired bootstrap needs equal-length series, got "
            f"{len(numerator_ratios)} and {len(pivot_ratios)}. Unequal "
            "lengths mean the corpus is not parallel; pairing would be false."
        )
        raise ValueError(msg)
    numerator = np.asarray(numerator_ratios, dtype=np.float64)
    pivot = np.asarray(pivot_ratios, dtype=np.float64)
    draws = generator.integers(0, numerator.size, size=(iterations, numerator.size))
    ratios = numerator[draws].mean(axis=1) / pivot[draws].mean(axis=1)
    tail = (1.0 - confidence) / 2.0
    low, high = np.quantile(ratios, [tail, 1.0 - tail])
    return float(low), float(high)


def aggregate(
    numerators: Sequence[int],
    denominators: Sequence[int],
    *,
    seed: int,
    iterations: int,
    confidence: float,
) -> Aggregate:
    """Micro, macro and the macro CI in one pass."""
    ratios = per_line_ratios(numerators, denominators)
    low, high = bootstrap_ci(
        ratios,
        generator=np.random.default_rng(seed),
        iterations=iterations,
        confidence=confidence,
    )
    return Aggregate(
        micro=micro_average(numerators, denominators),
        macro=float(np.mean(ratios)),
        macro_ci_low=low,
        macro_ci_high=high,
        n=len(ratios),
        bootstrap_iterations=iterations,
        seed=seed,
    )
