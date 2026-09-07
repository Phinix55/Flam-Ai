"""Adversarial fixtures (Phase 7).

BLUEPRINT §3: *"Report what breaks -- do not fix anything yet."* These
tests therefore assert that outcomes are **recorded**, not that everything
succeeds. A test demanding success here would be a request to change the
legacy pipeline, which is the opposite of what this phase is for.
"""

from __future__ import annotations

import pytest

from audit.corpus.acquire import require_tiktoken_cache
from audit.reporting.adversarial import run_fixtures
from audit.tokenizers import registry

REQUIRED_FIXTURES = {
    "empty_file.txt",
    "whitespace_only.txt",
    "mixed_script.txt",
    "emoji.txt",
    "pure_punctuation.txt",
    "combining_marks.txt",
    "zwj_zwnj.txt",
}


@pytest.fixture(scope="module")
def outcomes(config):
    require_tiktoken_cache(config)
    directory = config.root / "tests" / "fixtures" / "adversarial"
    return run_fixtures(directory, registry.load(config, "gpt2"))


def test_every_required_fixture_shape_is_present(config):
    directory = config.root / "tests" / "fixtures" / "adversarial"
    present = {p.name for p in directory.glob("*.txt")}
    assert REQUIRED_FIXTURES <= present
    assert {"parallel_eng.txt", "parallel_hin.txt"} <= present


def test_the_harness_records_rather_than_propagates(outcomes):
    """It must survive every fixture, including the ones that raise."""
    for name, entry in outcomes["fixtures"].items():
        if name == "parallel_length_mismatch":
            continue
        assert entry["legacy"]["outcome"] in {"ok", "raised"}
        assert entry["corrected"]["outcome"] in {"ok", "raised"}


def test_a_raised_fixture_records_its_exception_type(outcomes):
    empty = outcomes["fixtures"]["empty_file.txt"]["legacy"]
    assert empty["outcome"] == "raised"
    assert empty["exception"] == "ZeroDivisionError"
    assert empty["message"]


def test_length_mismatched_parallel_pair_raises_alignment_error(outcomes):
    alignment = outcomes["fixtures"]["parallel_length_mismatch"]["alignment"]
    assert alignment["outcome"] == "raised"
    assert alignment["exception"] == "AlignmentError"


def test_summary_separates_legacy_only_failures(outcomes):
    summary = outcomes["summary"]
    assert set(summary["legacy_raised"]) >= {"empty_file.txt", "whitespace_only.txt"}
    assert summary["corrected_raised"] == []
    assert set(summary["legacy_only"]) == set(summary["legacy_raised"])


def test_script_fixtures_are_processed_without_raising(outcomes):
    """Emoji, ZWJ/ZWNJ, combining marks and mixed script are handled by
    both pipelines; only the degenerate-denominator cases break."""
    for name in (
        "emoji.txt",
        "zwj_zwnj.txt",
        "combining_marks.txt",
        "mixed_script.txt",
    ):
        assert outcomes["fixtures"][name]["legacy"]["outcome"] == "ok"
