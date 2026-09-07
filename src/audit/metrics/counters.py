"""Denominator counters. Pure functions: string in, integer out.

Each counter answers "how much text is this?" under a different theory of
what a unit of text is. A3 turns on the fact that these disagree, and that
the disagreement is systematic by script.

No I/O, no globals, no printing anywhere in this module.
"""

from __future__ import annotations

import regex

_GRAPHEME = regex.compile(r"\X")
"""UAX #29 extended grapheme clusters, per the bundled Unicode tables.

Compiled once at import: it is a constant, not mutable state.
"""


def count_whitespace_words(text: str) -> int:
    """Words by Unicode whitespace splitting, empty tokens discarded.

    Held constant: the splitting rule. What varies is morphology -- an
    agglutinative language packs more meaning into one whitespace word, so
    this denominator does NOT hold meaning constant across languages.

    Note this is ``str.split()`` semantics, which collapses runs of
    whitespace and yields zero words for whitespace-only input. It is
    deliberately not the same as ``str.split(" ")``.
    """
    return len(text.split())


def count_graphemes(text: str) -> int:
    """Extended grapheme clusters, via ``regex`` ``\\X``.

    Held constant: what UAX #29 calls one user-perceived character, under
    the Unicode version bundled with the pinned ``regex`` release.

    This is *not* uniform across Indic scripts, and the non-uniformity is
    measured rather than assumed: the Devanagari conjunct ``क्ष``
    (ka + virama + ssa) clusters as one, while the Kannada conjunct
    ``ಕ್ಕ`` (ka + virama + ka) clusters as two. Any cross-script claim
    resting on this denominator has to carry that caveat, which is why the
    golden cases in ``tests/test_counters.py`` pin both.
    """
    return len(_GRAPHEME.findall(text))


def count_codepoints(text: str) -> int:
    """Unicode scalar values, i.e. ``len(text)``.

    Held constant: the encoding-independent codepoint. Diverges from
    grapheme count exactly where combining marks appear, which makes the
    pair a diagnostic for combining-mark shattering.
    """
    return len(text)


def count_utf8_bytes(text: str) -> int:
    """UTF-8 encoded length.

    Held constant: wire/storage cost. Diagnostic, not a decision metric:
    Indic codepoints cost 3 bytes to Latin's 1, so a per-byte ratio
    measures UTF-8's design as much as the tokenizer's.
    """
    return len(text.encode("utf-8"))


def count_sentences(texts: tuple[str, ...]) -> int:
    """Number of parallel sentences.

    Held constant: propositional content. In a parallel corpus the same
    index carries the same meaning in every language, which makes this the
    only denominator under which a cross-language ratio is a statement
    about cost per unit of meaning.

    Unlike every other counter here, this one is a property of the
    *record set* rather than of a string: it takes the parallel tuple so
    that the unit it counts is visibly the aligned sentence, not "a line
    of this language's file". A per-language sentence count that differed
    would mean the corpus was not parallel, and ``prepare.py`` raises
    before this is ever reached.
    """
    return len(texts)
