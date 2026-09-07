"""Faithful reimplementation of ``starter_kit/fertility.py``, flag-gated.

This is the sanctioned copy. ``starter_kit/`` is read-only (CLAUDE.md rule
2); all modification happens here, behind ``AblationFlags``.

Fidelity requirement: with ``AblationFlags.all_off()`` this module must
reproduce the original's printed output character-for-character AND its
floats bit-for-bit on ``starter_kit/corpus_sample/``. Quirks are preserved
deliberately, not tidied -- a "cleanup" would silently become an unmeasured
ablation and every downstream delta would be uninterpretable.

Two preserved behaviours worth naming, because both look like oversights:

* ``chars`` and ``words`` are both derived from the *case-folded* line,
  since the original reassigns ``line`` before measuring it.
* A zero denominator raises ``ZeroDivisionError`` rather than a friendly
  error. Fidelity outranks CLAUDE.md §3's error-message standard here:
  the baseline must fail the way the original fails, or the parity claim
  is limited to inputs that never fail. Phase 7 reports it; nothing fixes
  it without a flag.
"""

from __future__ import annotations

import random
import unicodedata
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from audit.ablation.flags import AblationFlags
from audit.metrics.counters import count_codepoints, count_graphemes
from audit.tokenizers.base import TokenizerAdapter

LEGACY_SEED = 1337
"""The seed literal in ``starter_kit/fertility.py:25``."""

PERTURBED_SEED = 90210
"""Deliberately different from ``LEGACY_SEED``, used only by
``perturb_global_rng``. Any value works; a fixed one keeps the flag's own
result reproducible."""

REPORT_WIDTH = 42
"""Width of the original's separator rule (``"-" * 42``)."""


@dataclass(frozen=True, slots=True)
class LegacyResult:
    """What the original script computes for one language.

    Field names mirror the original's reported columns so parity can be
    asserted field-by-field rather than on a formatted string alone.
    """

    lang: str
    fertility: float
    tokens_per_char: float
    n_lines: int


@dataclass(frozen=True, slots=True)
class LineCounts:
    """Per-line numerator and both denominators, before aggregation."""

    tokens: int
    words: int
    chars: int


def _iter_file_lines(text: str) -> Iterator[str]:
    """Reproduce Python text-mode file iteration over ``text``.

    Not ``str.splitlines()``: that also breaks on VT, FF, NEL, LS and PS,
    whereas a file opened in universal-newline text mode translates
    CRLF/CR to LF and then breaks on LF alone. The difference is invisible
    on this corpus and would be a silent, unmeasured ablation on input
    containing those separators.
    """
    return iter(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))


def read_lines(path_text: str, flags: AblationFlags) -> list[str]:
    """Line ingestion, reproducing the original's behaviour exactly.

    Takes file *text* rather than a path: keeps this module pure and lets
    the parity test and the adversarial fixtures feed it strings directly.
    """
    lines: list[str] = []
    for raw in _iter_file_lines(path_text):
        line = raw.strip()
        if not line:
            continue
        if not flags.skip_nfc_normalisation:
            line = unicodedata.normalize("NFC", line)
        lines.append(line)
    return lines


def _count_words(text: str, flags: AblationFlags) -> int:
    if flags.split_on_unicode_whitespace:
        return len(text.split())
    return len(text.split(" "))


def _count_chars(text: str, flags: AblationFlags) -> int:
    if flags.grapheme_denominator:
        return count_graphemes(text)
    return count_codepoints(text)


def measure_lines(
    lines: Sequence[str], tokenizer: TokenizerAdapter, flags: AblationFlags
) -> list[LineCounts]:
    """Numerator and both denominators per line.

    Held constant: the tokenizer and the line set. Case folding happens
    here, before every measurement, exactly as the original does it -- so
    ``words`` and ``chars`` describe the folded string, not the input.
    """
    counts: list[LineCounts] = []
    for line in lines:
        text = line if flags.preserve_case else line.lower()
        counts.append(
            LineCounts(
                tokens=len(tokenizer.encode(text)),
                words=_count_words(text, flags),
                chars=_count_chars(text, flags),
            )
        )
    return counts


def aggregate(
    counts: Sequence[LineCounts], flags: AblationFlags
) -> tuple[float, float]:
    """Collapse per-line counts to (fertility, tokens_per_char).

    Legacy is the macro branch: the mean of per-line ratios, every line
    weighted equally. The micro branch weights each line by its own
    denominator.
    """
    if flags.micro_aggregate:
        tokens = sum(c.tokens for c in counts)
        return tokens / sum(c.words for c in counts), tokens / sum(
            c.chars for c in counts
        )
    n = len(counts)
    return (
        sum(c.tokens / c.words for c in counts) / n,
        sum(c.tokens / c.chars for c in counts) / n,
    )


def analyze(
    lines: Sequence[str], tokenizer: TokenizerAdapter, flags: AblationFlags
) -> tuple[float, float]:
    """Reproduce the original ``analyze``: (fertility, tokens_per_char).

    Held constant relative to the original: the tokenizer, the line set,
    the aggregation order, and the arithmetic. Only behaviour explicitly
    gated by a flag may differ.
    """
    return aggregate(measure_lines(lines, tokenizer, flags), flags)


def _apply_rng_policy(flags: AblationFlags) -> None:
    """Set global RNG state the way the original's import-time call does.

    The original seeds at import; this runs per invocation, which is
    equivalent for any consumer that reads the state afterwards and is the
    only way to make the seed independently togglable.
    """
    random.seed(PERTURBED_SEED if flags.perturb_global_rng else LEGACY_SEED)


def run(
    corpora: dict[str, str], tokenizer: TokenizerAdapter, flags: AblationFlags
) -> list[LegacyResult]:
    """Full legacy pipeline over ``{lang: file_text}``, insertion-ordered.

    Order matters: the original normalises ratios against whichever
    language was passed first, so the mapping's order is part of the
    behaviour under test.
    """
    _apply_rng_policy(flags)
    results: list[LegacyResult] = []
    for lang, text in corpora.items():
        lines = read_lines(text, flags)
        fertility, tokens_per_char = analyze(lines, tokenizer, flags)
        results.append(LegacyResult(lang, fertility, tokens_per_char, len(lines)))
    return results


def _ratio_lines(results: Sequence[LegacyResult]) -> list[str]:
    """The original's trailing comparison block, including its blank line."""
    if len(results) < 2:
        return []
    base = results[0]
    out = [""]
    for result in results[1:]:
        ratio = result.fertility / base.fertility
        verdict = "worse" if ratio > 1 else "better"
        out.append(
            f"{result.lang} is {ratio:.2f}x the fertility of {base.lang} "
            f"({verdict} tokenization)"
        )
    return out


def format_report(results: Sequence[LegacyResult], tokenizer_name: str) -> str:
    """Reproduce the original's stdout verbatim, including its formatting.

    The parity test compares this string to the real script's captured
    stdout, so rounding, column widths and the trailing newline are all
    part of the contract.
    """
    header = f"{'lang':<8}{'fertility (tok/word)':>22}{'tok/char':>12}"
    lines = [f"tokenizer: {tokenizer_name}", header, "-" * REPORT_WIDTH]
    lines += [
        f"{r.lang:<8}{r.fertility:>22.2f}{r.tokens_per_char:>12.3f}" for r in results
    ]
    lines += _ratio_lines(results)
    return "\n".join(lines) + "\n"
