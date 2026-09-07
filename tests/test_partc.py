"""Part C envelope arithmetic (Block 10).

Part C is a judgment exercise, so these tests pin the *arithmetic* and the
structural facts it rests on -- not any conclusion drawn from them.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from audit.partc import (
    INDIC_TARGETS,
    REVIEWER_LANGUAGES,
    PartCAssumptions,
    build,
    reviewer_envelope,
    rewriter_envelope,
    schedule,
    training_envelope,
)

MEASURED = {c: 30.0 for c in INDIC_TARGETS}


def test_reviewer_capacity_matches_the_stated_constraints():
    """1 reviewer x 10 h/week x 2 weeks x 80 items/h = 1600 items."""
    envelope = reviewer_envelope(PartCAssumptions())
    assert envelope["reviewer_hours"] == 20
    assert envelope["items_at_stated_rate"] == 1600


def test_four_of_six_target_languages_have_no_native_reviewer():
    """The structural constraint the memo has to design around."""
    envelope = reviewer_envelope(PartCAssumptions())
    assert envelope["target_languages"] == 6
    assert envelope["covered_languages"] == 2
    assert set(envelope["uncovered_languages"]) == set(INDIC_TARGETS) - set(
        REVIEWER_LANGUAGES
    )
    assert len(envelope["uncovered_languages"]) == 4


def test_reviewer_capacity_does_not_scale_with_language_count():
    """Capacity is one person's hours: adding a language divides the same
    budget rather than adding to it."""
    envelope = reviewer_envelope(PartCAssumptions())
    assert (
        envelope["items_per_language_if_split_evenly"]
        < envelope["items_per_covered_language"]
    )


def test_training_tokens_scale_linearly_in_pairs_and_epochs():
    base = PartCAssumptions()
    doubled_pairs = training_envelope(replace(base, sft_pairs=30_000), MEASURED)
    single = training_envelope(base, MEASURED)
    assert doubled_pairs["training_tokens"] == pytest.approx(
        2 * single["training_tokens"]
    )


def test_gpu_budget_is_not_the_binding_constraint_at_any_plausible_size():
    """Robust by orders of magnitude: even at 10x the pairs and 10x the
    response length, the job still fits the two-week allocation."""
    stretched = replace(
        PartCAssumptions(), sft_pairs=150_000, sentences_per_response=40
    )
    envelope = training_envelope(stretched, MEASURED)
    assert envelope["gpu_hours_at_low_throughput"] < envelope["gpu_hours_available"]


def test_rewriter_second_pass_halves_measured_goodput():
    envelope = rewriter_envelope(200.92)
    assert envelope["effective_output_tok_s_if_equal_cost"] == pytest.approx(100.46)
    assert envelope["passes_per_request"] == 2


def test_schedule_gives_the_kill_criterion_a_date():
    dates = schedule(PartCAssumptions(start_date=date(2026, 9, 7)))
    assert dates["day_one"] == "2026-09-08"
    assert dates["review_launch"] == "2026-09-28"
    assert dates["decision_deadline"] < dates["review_launch"]


def test_envelope_ranks_nothing():
    """Rule 6: this module supplies arithmetic, never a recommendation."""
    envelope = build(PartCAssumptions(), MEASURED, 200.92)
    flat = repr(envelope).lower()
    for word in ("recommend", "should", "best", "prefer", "choose"):
        assert word not in flat


def test_assumptions_are_frozen():
    """Frozen so an assumption cannot be mutated between the arithmetic and
    the memo that cites it."""
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        PartCAssumptions().sft_pairs = 1  # type: ignore[misc]
