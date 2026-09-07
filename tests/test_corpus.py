"""Corpus alignment and normalisation contracts (Phase 3).

The load path must raise on misalignment rather than truncate. Every
"per parallel sentence" number downstream is only meaningful because this
holds, so it is tested directly rather than assumed.
"""

from __future__ import annotations

import pytest

from audit.corpus.prepare import AlignmentError, _validate_alignment, corpus_stats
from audit.corpus.schema import ParallelRecord


def test_misaligned_line_counts_raise_and_name_the_counts():
    with pytest.raises(AlignmentError, match="eng=3, hin=2"):
        _validate_alignment({"eng": ["a", "b", "c"], "hin": ["x", "y"]})


def test_aligned_counts_return_the_shared_length():
    assert _validate_alignment({"eng": ["a", "b"], "hin": ["x", "y"]}) == 2


def test_alignment_error_mentions_refusing_to_truncate():
    """The message has to say what it did *not* do, or a reader assumes
    the shorter file was silently used."""
    with pytest.raises(AlignmentError, match="Refusing to truncate"):
        _validate_alignment({"eng": ["a"], "hin": []})


def _records(texts_by_lang: dict[str, list[str]]) -> tuple[ParallelRecord, ...]:
    n = len(next(iter(texts_by_lang.values())))
    return tuple(
        ParallelRecord(
            index=i,
            texts={lang: lines[i] for lang, lines in texts_by_lang.items()},
            normalisation="NFC",
        )
        for i in range(n)
    )


def test_corpus_stats_holds_the_sentence_set_constant(config):
    """Every language must report the same sentence count, because they
    are indexed views of one record set."""
    records = _records({lang.code: ["hello world"] * 3 for lang in config.languages})
    stats = corpus_stats(records, config)
    assert {ls.sentences for ls in stats.per_language} == {3}
    assert stats.n_records == 3


def test_corpus_stats_rejects_an_empty_record_set(config):
    with pytest.raises(ValueError, match="empty record set"):
        corpus_stats((), config)


def test_ascii_makes_the_three_denominators_agree(config):
    """The control: where bytes, codepoints and graphemes must coincide,
    they must coincide exactly, in the real aggregation path."""
    records = _records(
        {lang.code: ["the train arrived"] * 2 for lang in config.languages}
    )
    for language_stats in corpus_stats(records, config).per_language:
        assert language_stats.codepoints == language_stats.utf8_bytes
        assert language_stats.codepoints == language_stats.graphemes
