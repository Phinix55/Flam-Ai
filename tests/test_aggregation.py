"""Micro vs macro, and bootstrap coverage (CLAUDE.md §4)."""

from __future__ import annotations

import numpy as np
import pytest

from audit.metrics.aggregation import (
    aggregate,
    bootstrap_ci,
    macro_average,
    micro_average,
    per_line_ratios,
)


def test_micro_and_macro_differ_on_a_constructed_example():
    """Two lines: 1 token / 1 word, and 30 tokens / 10 words.
    micro = 31/11 = 2.8181...; macro = (1.0 + 3.0)/2 = 2.0."""
    numerators, denominators = [1, 30], [1, 10]
    assert micro_average(numerators, denominators) == pytest.approx(31 / 11)
    assert macro_average(numerators, denominators) == pytest.approx(2.0)


def test_bootstrap_ci_covers_the_true_mean_of_a_synthetic_distribution():
    generator = np.random.default_rng(1337)
    values = generator.normal(loc=2.0, scale=0.5, size=500).tolist()
    low, high = bootstrap_ci(
        values, generator=generator, iterations=2000, confidence=0.95
    )
    assert low < 2.0 < high


def test_bootstrap_is_seed_deterministic():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    kwargs = {"iterations": 500, "confidence": 0.95}
    a = bootstrap_ci(values, generator=np.random.default_rng(1337), **kwargs)
    b = bootstrap_ci(values, generator=np.random.default_rng(1337), **kwargs)
    assert a == b


def test_micro_and_macro_coincide_when_denominators_are_equal():
    """The exact condition under which the two agree. If this ever fails,
    the gap reported everywhere else is not a weighting effect."""
    numerators, denominators = [3, 7, 5], [4, 4, 4]
    assert micro_average(numerators, denominators) == pytest.approx(
        macro_average(numerators, denominators)
    )


def test_zero_denominator_raises_instead_of_being_dropped():
    """Dropping the row would change the reported mean silently."""
    with pytest.raises(ZeroDivisionError, match="line index 1"):
        per_line_ratios([1, 1], [2, 0])


def test_length_mismatch_raises_instead_of_zipping_short():
    with pytest.raises(ValueError, match="length mismatch"):
        micro_average([1, 2, 3], [1, 2])


def test_aggregate_ci_brackets_its_own_macro():
    result = aggregate(
        [1, 30, 12, 7], [1, 10, 5, 4], seed=1337, iterations=2000, confidence=0.95
    )
    assert result.macro_ci_low <= result.macro <= result.macro_ci_high
    assert result.n == 4
    assert result.seed == 1337


def test_bootstrap_is_not_reading_global_numpy_state():
    """Seeding numpy globally between two calls must change nothing."""
    values = [1.0, 4.0, 2.0, 8.0, 3.0]
    kwargs = {"iterations": 500, "confidence": 0.95}
    first = bootstrap_ci(values, generator=np.random.default_rng(7), **kwargs)
    np.random.seed(999)
    second = bootstrap_ci(values, generator=np.random.default_rng(7), **kwargs)
    assert first == second
