"""Run the adversarial fixtures through both pipelines and record outcomes.

BLUEPRINT §3 Phase 7: *"Report what breaks -- do not fix anything yet."*
This module therefore **catches and records** exceptions rather than
letting them propagate or repairing the code that raised them. An
exception is a documented outcome here, not a failure of the stage.

Two pipelines are run on every fixture so the comparison is meaningful:

* **legacy** -- ``ablation/legacy.py`` at ``AblationFlags.all_off()``, i.e.
  exactly what ``starter_kit/fertility.py`` does.
* **corrected** -- ``metrics/`` counters over the same bytes.

Where they differ, the difference is a property of the v0 pipeline. Where
both raise, the input is hostile to any implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from audit.ablation.flags import AblationFlags
from audit.ablation.legacy import analyze, read_lines
from audit.metrics.counters import (
    count_codepoints,
    count_graphemes,
    count_utf8_bytes,
    count_whitespace_words,
)
from audit.tokenizers.base import TokenizerAdapter

PARALLEL_PAIR = ("parallel_eng.txt", "parallel_hin.txt")


def _outcome(fn: Any) -> dict[str, Any]:
    """Call ``fn``, recording either its value or the exception it raised."""
    try:
        return {"outcome": "ok", "value": fn()}
    except Exception as exc:  # noqa: BLE001 - recording is the whole point
        return {
            "outcome": "raised",
            "exception": type(exc).__name__,
            "message": str(exc)[:300],
        }


def _legacy_probe(text: str, tokenizer: TokenizerAdapter) -> dict[str, Any]:
    flags = AblationFlags.all_off()

    def run() -> dict[str, float]:
        lines = read_lines(text, flags)
        fertility, tokens_per_char = analyze(lines, tokenizer, flags)
        return {
            "n_lines": len(lines),
            "fertility": fertility,
            "tokens_per_char": tokens_per_char,
        }

    return _outcome(run)


def _corrected_probe(text: str, tokenizer: TokenizerAdapter) -> dict[str, Any]:
    def run() -> dict[str, int]:
        lines = [line for line in text.split("\n") if line]
        joined = "".join(lines)
        return {
            "n_lines": len(lines),
            "tokens": sum(len(tokenizer.encode(line)) for line in lines),
            "words": count_whitespace_words(joined),
            "graphemes": count_graphemes(joined),
            "codepoints": count_codepoints(joined),
            "utf8_bytes": count_utf8_bytes(joined),
        }

    return _outcome(run)


def _alignment_probe(directory: Path) -> dict[str, Any]:
    from audit.corpus.prepare import _validate_alignment

    def run() -> int:
        per_language = {
            name.split("_")[1].removesuffix(".txt"): (directory / name)
            .read_text(encoding="utf-8")
            .split("\n")
            for name in PARALLEL_PAIR
        }
        return _validate_alignment(per_language)

    return _outcome(run)


def run_fixtures(directory: Path, tokenizer: TokenizerAdapter) -> dict[str, Any]:
    """Every fixture through both pipelines. Never raises on fixture content."""
    fixtures: dict[str, Any] = {}
    for path in sorted(directory.glob("*.txt")):
        if path.name in PARALLEL_PAIR:
            continue
        text = path.read_text(encoding="utf-8")
        fixtures[path.name] = {
            "bytes": path.stat().st_size,
            "codepoints": len(text),
            "legacy": _legacy_probe(text, tokenizer),
            "corrected": _corrected_probe(text, tokenizer),
        }
    fixtures["parallel_length_mismatch"] = {
        "files": list(PARALLEL_PAIR),
        "alignment": _alignment_probe(directory),
    }
    return {"fixtures": fixtures, "summary": summarise(fixtures)}


def summarise(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Which pipeline broke on which fixture, and where they disagree."""
    legacy_raised = sorted(
        name
        for name, entry in fixtures.items()
        if entry.get("legacy", {}).get("outcome") == "raised"
    )
    corrected_raised = sorted(
        name
        for name, entry in fixtures.items()
        if entry.get("corrected", {}).get("outcome") == "raised"
    )
    return {
        "legacy_raised": legacy_raised,
        "corrected_raised": corrected_raised,
        "legacy_only": sorted(set(legacy_raised) - set(corrected_raised)),
        "both_raised": sorted(set(legacy_raised) & set(corrected_raised)),
        "note": (
            "Recorded, not fixed. BLUEPRINT Phase 7: report what breaks; "
            "remediation is a later, separately-measured decision."
        ),
    }
