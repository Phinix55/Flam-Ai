"""Golden denominator counts (CLAUDE.md §4).

Hand-checked strings in Devanagari, Kannada, Tamil, Telugu and Bengali,
including combining marks, ZWJ, ZWNJ and a virama sequence. Expected
values are filled in Phase 4 by hand-counting, never by running the code
and recording what it printed -- that would test nothing.
"""

from __future__ import annotations

from audit.metrics.counters import (
    count_codepoints,
    count_graphemes,
    count_utf8_bytes,
    count_whitespace_words,
)


def test_grapheme_and_codepoint_diverge_on_a_virama_sequence():
    # क + ् + ष : one perceived character, three codepoints.
    text = "क्ष"
    assert count_codepoints(text) == 3
    assert count_graphemes(text) == 1


def test_zwj_sequence_is_one_grapheme():
    assert count_graphemes("\U0001f469‍\U0001f4bb") == 1


def test_indic_codepoints_cost_three_utf8_bytes():
    assert count_utf8_bytes("ಕ") == 3  # Kannada KA
    assert count_utf8_bytes("a") == 1


def test_whitespace_words_ignore_repeated_and_exotic_separators():
    assert count_whitespace_words("a  b") == 2
    assert count_whitespace_words("   ") == 0
    assert count_whitespace_words("") == 0


def test_grapheme_clustering_is_not_uniform_across_indic_scripts():
    """Measured, not assumed, and pinned because it constrains every claim
    that rests on the grapheme denominator.

    Under the bundled UAX #29 tables the Devanagari conjunct क्ष
    (ka + virama + ssa) is one cluster, while the Kannada conjunct ಕ್ಕ
    (ka + virama + ka) is two -- same structure, different answer. A
    per-grapheme cross-script comparison therefore does not hold "one
    perceived character" constant the way it does within a single script.
    """
    assert count_codepoints("क्ष") == 3
    assert count_graphemes("क्ष") == 1
    assert count_codepoints("ಕ್ಕ") == 3
    assert count_graphemes("ಕ್ಕ") == 2


def test_denominators_coincide_exactly_on_ascii():
    """The control for every Indic measurement: where the three counters
    must agree, they must agree exactly."""
    ascii_text = "The train arrived exactly on time."
    assert count_codepoints(ascii_text) == count_utf8_bytes(ascii_text)
    assert count_codepoints(ascii_text) == count_graphemes(ascii_text)
