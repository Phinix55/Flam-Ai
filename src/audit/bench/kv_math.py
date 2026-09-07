"""KV-cache arithmetic. Pure functions, every intermediate term returned.

The output is a named breakdown rather than a single number, because the
defense asks for re-derivation on the spot: each term has to be readable
and checkable against a hand calculation without re-running anything.

GQA is the term that decides the answer. KV bytes scale with *kv_heads*,
not with query heads; using ``attention_heads`` where ``kv_heads`` belongs
inflates the result by the group ratio. ``tests/test_kv_math.py`` pins an
explicit MHA-vs-GQA pair so that ratio can never silently drop out.
"""

from __future__ import annotations

from dataclasses import dataclass

from audit.bench.spec import ModelSpec, ServingSpec, dtype_bytes

DECIMAL_GB = 10**9
BINARY_GIB = 2**30

MEMORY_UNITS: dict[str, int] = {"decimal_GB": DECIMAL_GB, "binary_GiB": BINARY_GIB}
"""Both readings of "24 GB", carried rather than silently chosen.

The spec writes a bare "24 GB". Vendors quote decimal, allocators report
binary, and the two differ by 7.4 % -- enough to move the concurrency
ceiling by three sequences. Which one the machine actually behaved as is
an empirical question, answered by the log in ``log_analysis``, not by
picking a convention here.
"""


@dataclass(frozen=True, slots=True)
class KVBreakdown:
    """Every step of ``2 * layers * kv_heads * head_dim * dtype_bytes``."""

    k_and_v_factor: int
    layers: int
    kv_heads: int
    head_dim: int
    dtype_bytes: int
    kv_dim_per_layer: int
    bytes_per_token: int
    group_ratio: float
    mha_bytes_per_token: int


@dataclass(frozen=True, slots=True)
class ConcurrencyBreakdown:
    """Memory budget -> concurrent-sequence ceiling, term by term."""

    memory_unit: str
    bytes_per_unit: int
    gpu_memory_bytes: int
    gpu_memory_utilization: float
    usable_bytes: int
    weights_bytes: int
    runtime_overhead_bytes: int
    kv_budget_bytes: int
    kv_bytes_per_token: int
    context_length: int
    bytes_per_sequence: int
    exact_sequences: float
    max_concurrent_sequences: int
    kv_capacity_tokens: int


def kv_bytes_per_token(spec: ModelSpec) -> KVBreakdown:
    """KV bytes for one token, with every factor named.

    Held constant: the model. Nothing about the serving config or the load
    test enters here, so this number is a pure property of the spec file.

    ``mha_bytes_per_token`` is reported alongside deliberately -- it is
    what the same formula gives if query heads are substituted for KV
    heads, so the cost of that substitution is visible in the artefact
    rather than left as a caveat.
    """
    element = dtype_bytes(spec.kv_dtype)
    kv_dim_per_layer = spec.kv_heads * spec.head_dim
    return KVBreakdown(
        k_and_v_factor=2,
        layers=spec.layers,
        kv_heads=spec.kv_heads,
        head_dim=spec.head_dim,
        dtype_bytes=element,
        kv_dim_per_layer=kv_dim_per_layer,
        bytes_per_token=2 * spec.layers * kv_dim_per_layer * element,
        group_ratio=spec.attention_heads / spec.kv_heads,
        mha_bytes_per_token=2
        * spec.layers
        * spec.attention_heads
        * spec.head_dim
        * element,
    )


def weight_bytes(spec: ModelSpec) -> int:
    """Model weights in bytes, from parameter count and weight dtype.

    Parameter counts are quoted in decimal billions regardless of how GPU
    memory is quoted, so this never varies with ``memory_unit``.
    """
    return int(spec.parameters_b * DECIMAL_GB * dtype_bytes(spec.weights_dtype))


def concurrency_ceiling(
    spec: ModelSpec,
    serving: ServingSpec,
    context_length: int,
    memory_unit: str = "decimal_GB",
) -> ConcurrencyBreakdown:
    """Maximum concurrent sequences of ``context_length`` tokens.

    Held constant: context length across all sequences. Real traffic has
    mixed lengths, so this is a ceiling on a uniform workload -- stating
    that is part of the answer.
    """
    if memory_unit not in MEMORY_UNITS:
        known = ", ".join(sorted(MEMORY_UNITS))
        msg = f"Unknown memory unit {memory_unit!r}. Known: {known}."
        raise ValueError(msg)
    unit = MEMORY_UNITS[memory_unit]
    per_token = kv_bytes_per_token(spec).bytes_per_token
    total = int(serving.gpu_memory_gb * unit)
    usable = int(total * serving.gpu_memory_utilization)
    weights = weight_bytes(spec)
    overhead = int(serving.runtime_overhead_gb * unit)
    budget = usable - weights - overhead
    if budget <= 0:
        msg = (
            f"KV budget is non-positive ({budget} B): weights {weights} B plus "
            f"overhead {overhead} B exceed the usable {usable} B. The model "
            "does not fit on this GPU under this spec."
        )
        raise ValueError(msg)
    per_sequence = per_token * context_length
    exact = budget / per_sequence
    return ConcurrencyBreakdown(
        memory_unit=memory_unit,
        bytes_per_unit=unit,
        gpu_memory_bytes=total,
        gpu_memory_utilization=serving.gpu_memory_utilization,
        usable_bytes=usable,
        weights_bytes=weights,
        runtime_overhead_bytes=overhead,
        kv_budget_bytes=budget,
        kv_bytes_per_token=per_token,
        context_length=context_length,
        bytes_per_sequence=per_sequence,
        exact_sequences=exact,
        max_concurrent_sequences=int(exact),
        kv_capacity_tokens=budget // per_token,
    )
