"""Corpus data types.

A ``ParallelRecord`` is the unit that makes cross-language comparison
legitimate: one index, the same propositional content, N language
renderings. Everything downstream that claims to hold *meaning* constant
holds it constant by sharing this index.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParallelRecord:
    """One aligned sentence across all evaluation languages.

    ``index`` is the FLORES-200 devtest line number (0-based), retained so
    the exact sample is reconstructible from ``sample_manifest.json``
    without shipping the corpus.

    ``texts`` maps language code -> sentence. Every record carries the same
    key set; a record missing a language is an alignment failure and must
    raise rather than be dropped.
    """

    index: int
    texts: dict[str, str]
    normalisation: str


@dataclass(frozen=True, slots=True)
class LanguageStats:
    """Descriptive counts for one language under one normalisation form.

    Held constant: the sentence set (same FLORES indices for every
    language) and the normalisation form. Only the language varies, so
    differences here are properties of the language and its script.
    """

    code: str
    script: str
    normalisation: str
    sentences: int
    codepoints: int
    graphemes: int
    utf8_bytes: int
    whitespace_words: int


@dataclass(frozen=True, slots=True)
class CorpusStats:
    """Whole-corpus descriptive statistics, one entry per language."""

    split: str
    normalisation: str
    n_records: int
    per_language: tuple[LanguageStats, ...]
