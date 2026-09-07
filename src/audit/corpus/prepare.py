"""Alignment validation and normalisation-variant construction.

Never truncates. If two languages disagree on line count the parallel
assumption is void, and every downstream "per parallel sentence" number
would be comparing different content -- so this raises.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from audit.config import AuditConfig
from audit.corpus.acquire import language_file, require_corpus_cache
from audit.corpus.schema import CorpusStats, LanguageStats, ParallelRecord
from audit.metrics.counters import (
    count_codepoints,
    count_graphemes,
    count_utf8_bytes,
    count_whitespace_words,
)


class AlignmentError(ValueError):
    """Raised when parallel files disagree on line count or line identity."""


def _read_split(path: Path) -> list[str]:
    """Lines of one FLORES file, terminators stripped, nothing filtered.

    Blank lines are *kept*: dropping one language's blank would shift that
    language's indices relative to the others, which is exactly the silent
    misalignment this module exists to prevent.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _validate_alignment(per_language: dict[str, list[str]]) -> int:
    """Assert every language has the same line count. Returns that count."""
    lengths = {code: len(lines) for code, lines in per_language.items()}
    if len(set(lengths.values())) != 1:
        detail = ", ".join(f"{code}={n}" for code, n in sorted(lengths.items()))
        msg = (
            f"Parallel corpus misaligned: line counts differ ({detail}). "
            "Refusing to truncate -- a per-sentence comparison across "
            "differently-indexed files would not hold meaning constant."
        )
        raise AlignmentError(msg)
    return next(iter(lengths.values()))


def load_parallel(
    config: AuditConfig, normalisation: str
) -> tuple[ParallelRecord, ...]:
    """Load the aligned devtest set under one Unicode normalisation form.

    Held constant across the returned records: the sentence indices and
    the normalisation form. Language is the only thing that varies.
    """
    if normalisation not in config.normalisation_forms:
        msg = (
            f"Unknown normalisation form {normalisation!r}. "
            f"Configured: {', '.join(config.normalisation_forms)}."
        )
        raise ValueError(msg)
    require_corpus_cache(config)
    per_language = {
        lang.code: [
            unicodedata.normalize(normalisation, line)  # type: ignore[arg-type]
            for line in _read_split(language_file(config, lang.flores_code))
        ]
        for lang in config.languages
    }
    n = _validate_alignment(per_language)
    return tuple(
        ParallelRecord(
            index=i,
            texts={code: lines[i] for code, lines in per_language.items()},
            normalisation=normalisation,
        )
        for i in range(n)
    )


def load_legacy_sample(config: AuditConfig) -> dict[str, str]:
    """Read ``starter_kit/corpus_sample/`` verbatim, one entry per language.

    Deliberately does no validation and no normalisation: this feeds the
    parity gate, which must see exactly the bytes the original script saw.
    Insertion order is eng then hin, matching the reported invocation.
    """
    return {
        lang: (config.legacy_corpus_dir / f"{lang}_sample.txt").read_text(
            encoding="utf-8"
        )
        for lang in ("eng", "hin")
    }


def _language_stats(
    code: str, script: str, texts: list[str], normalisation: str
) -> LanguageStats:
    return LanguageStats(
        code=code,
        script=script,
        normalisation=normalisation,
        sentences=len(texts),
        codepoints=sum(count_codepoints(t) for t in texts),
        graphemes=sum(count_graphemes(t) for t in texts),
        utf8_bytes=sum(count_utf8_bytes(t) for t in texts),
        whitespace_words=sum(count_whitespace_words(t) for t in texts),
    )


def corpus_stats(
    records: tuple[ParallelRecord, ...], config: AuditConfig
) -> CorpusStats:
    """Descriptive statistics over an aligned record set.

    Held constant: the sentence set (identical indices for every language)
    and the normalisation form. Only the language varies, so every
    difference here is a property of the language and its script.
    """
    if not records:
        msg = "Cannot compute corpus statistics over an empty record set."
        raise ValueError(msg)
    normalisation = records[0].normalisation
    return CorpusStats(
        split=config.flores_split,
        normalisation=normalisation,
        n_records=len(records),
        per_language=tuple(
            _language_stats(
                lang.code,
                lang.script,
                [r.texts[lang.code] for r in records],
                normalisation,
            )
            for lang in config.languages
        ),
    )


def sample_manifest(
    records: tuple[ParallelRecord, ...], config: AuditConfig
) -> dict[str, object]:
    """Record the exact devtest indices used, so the corpus is
    reconstructible without redistributing FLORES-200."""
    return {
        "source": "FLORES-200",
        "split": config.flores_split,
        "n_records": len(records),
        "indices": [r.index for r in records],
        "languages": {
            lang.code: {
                "flores_code": lang.flores_code,
                "script": lang.script,
                "file": language_file(config, lang.flores_code).name,
            }
            for lang in config.languages
        },
    }
