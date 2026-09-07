"""Spec parsing and log analysis (Phase 6).

The defense expects the spec to be edited live, so the parser is tested
against *modified* spec text, not only the shipped file. If any value were
hardcoded, these are the tests that would catch it.
"""

from __future__ import annotations

import pytest

from audit.bench.kv_math import concurrency_ceiling, kv_bytes_per_token
from audit.bench.log_analysis import (
    correlate_ceiling,
    find_knee,
    goodput_derivations,
    parse_log,
    reconstruct_reported,
    sweep,
)
from audit.bench.spec import SpecParseError, parse_model_spec


@pytest.fixture(scope="module")
def spec_text(config) -> str:
    return config.model_spec_path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def log_rows(config):
    return parse_log(config.bench_log_path.read_text(encoding="utf-8"))


# ------------------------------------------------------------ spec parsing


def test_parses_the_shipped_spec(spec_text):
    model, serving = parse_model_spec(spec_text)
    assert (model.layers, model.kv_heads, model.attention_heads) == (28, 8, 24)
    assert model.head_dim == 128
    assert model.vocab_size == 128_000
    assert model.kv_dtype == "fp16"
    assert serving.max_model_len == 4096
    assert serving.gpu_memory_gb == 24.0
    assert serving.gpu_memory_utilization == 0.92


def test_gpu_capacity_is_not_the_device_count(spec_text):
    """`1x NVIDIA L4 (24 GB)` starts with a 1; a naive first-number parse
    would return the device count as the memory size."""
    _, serving = parse_model_spec(spec_text)
    assert serving.gpu_memory_gb == 24.0


@pytest.mark.parametrize(
    ("old", "new", "attribute", "expected"),
    [
        ("| layers | 28 |", "| layers | 56 |", "layers", 56),
        ("| KV heads (GQA) | 8 |", "| KV heads (GQA) | 24 |", "kv_heads", 24),
        ("| head_dim | 128 |", "| head_dim | 64 |", "head_dim", 64),
        (
            "| KV cache precision | fp16 |",
            "| KV cache precision | fp8 |",
            "kv_dtype",
            "fp8",
        ),
    ],
)
def test_editing_the_spec_changes_the_parsed_value(
    spec_text, old, new, attribute, expected
):
    """The live-edit case. Nothing may be memorised from the shipped file."""
    assert old in spec_text
    model, _ = parse_model_spec(spec_text.replace(old, new))
    assert getattr(model, attribute) == expected


def test_kv_math_follows_a_live_spec_edit(spec_text):
    """Doubling layers must double KV bytes/token, end to end."""
    base, _ = parse_model_spec(spec_text)
    doubled, _ = parse_model_spec(
        spec_text.replace("| layers | 28 |", "| layers | 56 |")
    )
    assert (
        kv_bytes_per_token(doubled).bytes_per_token
        == 2 * kv_bytes_per_token(base).bytes_per_token
    )


def test_removing_a_required_field_raises_and_names_it(spec_text):
    stripped = spec_text.replace("| KV heads (GQA) | 8 |", "")
    with pytest.raises(SpecParseError, match="kv heads"):
        parse_model_spec(stripped)


def test_unparseable_value_raises_rather_than_defaulting(spec_text):
    broken = spec_text.replace("| layers | 28 |", "| layers | many |")
    with pytest.raises(SpecParseError, match="no number"):
        parse_model_spec(broken)


def test_ceiling_scales_inversely_with_context_length(spec_text):
    model, serving = parse_model_spec(spec_text)
    at_4096 = concurrency_ceiling(model, serving, 4096)
    at_2048 = concurrency_ceiling(model, serving, 2048)
    assert at_2048.exact_sequences == pytest.approx(2 * at_4096.exact_sequences)


def test_model_that_does_not_fit_raises(spec_text):
    huge = spec_text.replace("| parameters | 4.2 B |", "| parameters | 420 B |")
    model, serving = parse_model_spec(huge)
    with pytest.raises(ValueError, match="does not fit"):
        concurrency_ceiling(model, serving, 4096)


# ------------------------------------------------------------ log analysis


def test_header_mismatch_raises_rather_than_guessing(config):
    text = config.bench_log_path.read_text(encoding="utf-8").replace(
        "reported_tok_s", "throughput"
    )
    with pytest.raises(ValueError, match="Refusing to guess"):
        parse_log(text)


def test_missing_prompt_length_lists_what_is_available(log_rows):
    with pytest.raises(ValueError, match="Available"):
        sweep(log_rows, 999)


def test_two_goodput_derivations_use_disjoint_columns(log_rows):
    """Independence is the point: shared columns would make agreement
    circular rather than confirmatory."""
    row = next(r for r in log_rows if (r.batch_size, r.prompt_len) == (24, 3584))
    first, second = goodput_derivations(row)
    assert set(first.columns_used) & set(second.columns_used) == set()


def test_reported_counter_counts_prompt_plus_generated_on_every_row(log_rows):
    """Stated as a checkable identity, not an assumption about the harness."""
    for row in log_rows:
        recon = reconstruct_reported(row)
        assert recon["relative_error_vs_prompt_plus_generated_pct"] < 0.05


def test_knee_is_located_at_the_throughput_peak(log_rows):
    knee = find_knee(sweep(log_rows, 3584))
    assert knee["knee_batch_size"] == 24
    assert knee["next_reported_tok_s"] < knee["peak_reported_tok_s"]
    assert knee["at_knee"]["preempted_seqs"] == 0
    assert knee["after_knee"]["preempted_seqs"] > 0


def test_saturated_rows_are_excluded_from_capacity_inversion(log_rows):
    """A clipped utilisation cannot be inverted; treating it as if it
    could would manufacture agreement."""
    result = correlate_ceiling(sweep(log_rows, 3584), 25.7)
    for row in result["rows"]:
        if row["saturated"]:
            assert row["implied_capacity_tokens"] is None


def test_a_wrong_ceiling_fails_the_preemption_check(log_rows):
    """The check must be capable of rejecting, or its passing means
    nothing."""
    rows = sweep(log_rows, 3584)
    assert correlate_ceiling(rows, 25.7)["preemption_matches_all_rows"]
    assert not correlate_ceiling(rows, 28.9)["preemption_matches_all_rows"]
