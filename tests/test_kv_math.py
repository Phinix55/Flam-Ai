"""KV arithmetic, incl. an explicit MHA-vs-GQA case (CLAUDE.md §4).

The GQA case is the one that matters: KV bytes scale with kv_heads, not
with query heads. If the group ratio ever silently drops out of the
formula, this test is what catches it.
"""

from __future__ import annotations

import pytest

from audit.bench.kv_math import kv_bytes_per_token
from audit.bench.spec import ModelSpec, dtype_bytes


def _spec(**overrides):
    base = {
        "name": "toy",
        "parameters_b": 1.0,
        "layers": 2,
        "d_model": 16,
        "attention_heads": 8,
        "kv_heads": 8,
        "head_dim": 4,
        "vocab_size": 100,
        "weights_dtype": "fp16",
        "kv_dtype": "fp16",
    }
    return ModelSpec(**{**base, **overrides})


def test_hand_worked_mha_example():
    """2 * 2 layers * 8 kv_heads * 4 head_dim * 2 bytes = 256 bytes/token."""
    assert kv_bytes_per_token(_spec()).bytes_per_token == 256


def test_gqa_divides_by_the_group_ratio():
    """Same model with 2 KV heads instead of 8 is 4x cheaper, not equal."""
    mha = kv_bytes_per_token(_spec(attention_heads=8, kv_heads=8))
    gqa = kv_bytes_per_token(_spec(attention_heads=8, kv_heads=2))
    assert gqa.group_ratio == 4.0
    assert mha.bytes_per_token == 4 * gqa.bytes_per_token


def test_query_head_count_does_not_enter_the_kv_formula():
    a = kv_bytes_per_token(_spec(attention_heads=8, kv_heads=2))
    b = kv_bytes_per_token(_spec(attention_heads=64, kv_heads=2))
    assert a.bytes_per_token == b.bytes_per_token


def test_unknown_dtype_raises_instead_of_guessing():
    with pytest.raises(ValueError, match="dtype"):
        dtype_bytes("float-something")


def test_dtype_halving_halves_the_cache():
    """fp8 KV is exactly half of fp16 KV, everything else fixed."""
    fp16 = kv_bytes_per_token(_spec(kv_dtype="fp16"))
    fp8 = kv_bytes_per_token(_spec(kv_dtype="fp8"))
    assert fp16.bytes_per_token == 2 * fp8.bytes_per_token


def test_every_intermediate_term_is_reported():
    """The defense asks for re-derivation; a bare total cannot be checked."""
    breakdown = kv_bytes_per_token(_spec())
    assert breakdown.k_and_v_factor == 2
    assert breakdown.kv_dim_per_layer == breakdown.kv_heads * breakdown.head_dim
    assert breakdown.bytes_per_token == (
        breakdown.k_and_v_factor
        * breakdown.layers
        * breakdown.kv_dim_per_layer
        * breakdown.dtype_bytes
    )


def test_dtype_bytes_known_values():
    assert dtype_bytes("fp16") == dtype_bytes("bf16") == 2
    assert dtype_bytes("fp32") == 4
    assert dtype_bytes("fp8") == 1
    assert dtype_bytes("`fp16`") == 2
