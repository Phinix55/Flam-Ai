"""A3 grid contracts (Phase 5).

These pin the properties the denominator argument rests on, so that
argument cannot quietly stop being true.
"""

from __future__ import annotations

import numpy as np
import pytest

from audit.metrics.aggregation import bootstrap_ratio_ci
from audit.metrics.fertility import DENOMINATORS, LineMeasurement, measure_line
from audit.metrics.grid import build, cell, measure_all


class FakeTokenizer:
    """One token per character. Deterministic, no cache, no network."""

    name = "fake"
    vocab_size = 1
    counts_special_tokens = False

    def encode(self, text: str) -> list[int]:
        return [1] * len(text)


def test_a3_requires_these_four_denominators():
    assert {"words", "graphemes", "utf8_bytes", "sentences"} <= set(DENOMINATORS)


def test_sentence_denominator_is_one_per_line():
    measurement = measure_line(0, "a b c", [1, 2, 3])
    assert measurement.sentences == 1
    assert measurement.denominator("sentences") == 1


def test_unknown_denominator_raises_with_the_available_set():
    with pytest.raises(KeyError, match="Available"):
        measure_line(0, "x", [1]).denominator("furlongs")


def test_micro_equals_macro_under_the_sentence_denominator():
    """The structural claim: with every denominator equal to 1, the
    weighting choice cannot change the answer. If this ever fails, the
    sentence unit is not doing what A3 says it does."""
    measurements = [
        LineMeasurement(i, tokens=t, words=1, graphemes=1, codepoints=1, utf8_bytes=1)
        for i, t in enumerate([3, 40, 7, 900, 1])
    ]
    result = cell(measurements, "sentences", seed=1337, iterations=200, confidence=0.95)
    assert result["micro"] == pytest.approx(result["macro"])


def test_micro_and_macro_differ_under_the_word_denominator():
    """The contrast case: unequal denominators must separate them, or the
    previous test proves nothing."""
    measurements = [
        LineMeasurement(0, tokens=1, words=1, graphemes=1, codepoints=1, utf8_bytes=1),
        LineMeasurement(
            1, tokens=30, words=10, graphemes=1, codepoints=1, utf8_bytes=1
        ),
    ]
    result = cell(measurements, "words", seed=1337, iterations=200, confidence=0.95)
    assert result["micro"] != pytest.approx(result["macro"])


def test_pivot_language_ratio_is_exactly_one():
    corpus = {"eng": ["ab", "cde"], "hin": ["xyz", "w"]}
    grid = build(
        measure_all(corpus, FakeTokenizer()),
        pivot="eng",
        seed=1337,
        iterations=200,
        confidence=0.95,
    )
    for denominator in DENOMINATORS:
        assert grid["ratio_to_pivot"][denominator]["eng"]["macro"] == pytest.approx(1.0)
        assert grid["ratio_to_pivot"][denominator]["eng"]["micro"] == pytest.approx(1.0)


def test_missing_pivot_raises():
    with pytest.raises(KeyError, match="Pivot language"):
        build(
            measure_all({"hin": ["a"]}, FakeTokenizer()),
            pivot="eng",
            seed=1,
            iterations=10,
            confidence=0.95,
        )


def test_paired_bootstrap_rejects_unequal_lengths():
    """Unequal series are not a parallel corpus; pairing would be false."""
    with pytest.raises(ValueError, match="not parallel"):
        bootstrap_ratio_ci(
            [1.0, 2.0],
            [1.0],
            generator=np.random.default_rng(1),
            iterations=10,
            confidence=0.95,
        )


def test_paired_bootstrap_is_tighter_than_treating_series_as_independent():
    """Why pairing matters: on a parallel corpus the two series co-vary,
    and pairing keeps that covariance instead of discarding it."""
    rng = np.random.default_rng(1337)
    shared = rng.normal(10.0, 3.0, size=400)
    numerator = (shared * 2.0).tolist()
    pivot = shared.tolist()
    paired = bootstrap_ratio_ci(
        numerator,
        pivot,
        generator=np.random.default_rng(7),
        iterations=2000,
        confidence=0.95,
    )
    assert paired[0] == pytest.approx(2.0, abs=1e-9)
    assert paired[1] == pytest.approx(2.0, abs=1e-9)
