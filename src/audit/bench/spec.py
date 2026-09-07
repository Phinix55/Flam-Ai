"""Parse ``bench/model_spec.md`` into a ``ModelSpec``. Pure given text.

**No spec value is ever hardcoded** (CLAUDE.md §5). B1's arithmetic is
derived from the file, so if a grader edits ``model_spec.md`` live -- flips
GQA heads, changes dtype, doubles the layer count -- ``make bench``
re-derives the answer instead of reprinting a memorised one.

Every field is looked up by name and raises if absent. Nothing is
defaulted: a missing field silently replaced by a plausible number is
fabricated evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ROW = re.compile(r"^\s*\|(?P<key>[^|]+)\|(?P<value>[^|]+)\|\s*$")
NUMBER = re.compile(r"(-?\d+(?:\.\d+)?)")
MEMORY_IN_PARENS = re.compile(r"\((\d+(?:\.\d+)?)\s*GB\)", re.IGNORECASE)
MAGNITUDES = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}

DTYPE_BYTES = {
    "fp16": 2,
    "float16": 2,
    "bf16": 2,
    "bfloat16": 2,
    "fp32": 4,
    "float32": 4,
    "fp8": 1,
    "int8": 1,
    "fp4": 1,
    "int4": 1,
}


class SpecParseError(ValueError):
    """Raised when a required field is absent or unparseable."""


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Everything B1 needs, all of it read from the spec file."""

    name: str
    parameters_b: float
    layers: int
    d_model: int
    attention_heads: int
    kv_heads: int
    head_dim: int
    vocab_size: int
    weights_dtype: str
    kv_dtype: str


@dataclass(frozen=True, slots=True)
class ServingSpec:
    """Hardware and serving configuration, also read from the file."""

    gpu: str
    gpu_memory_gb: float
    memory_bandwidth_gb_s: float
    peak_fp16_tflops: float
    max_model_len: int
    gpu_memory_utilization: float
    runtime_overhead_gb: float


def _normalise(key: str) -> str:
    return key.strip().strip("`").strip().lower()


def parse_tables(markdown: str) -> dict[str, str]:
    """Every ``| key | value |`` row in the document, keys normalised.

    Header and separator rows are dropped by shape, not by position, so
    reordering or adding a table does not break the parse.
    """
    fields: dict[str, str] = {}
    for line in markdown.splitlines():
        match = ROW.match(line)
        if match is None:
            continue
        key = _normalise(match["key"])
        value = match["value"].strip()
        if not key or key == "property" or set(key) <= {"-", ":"}:
            continue
        fields[key] = value
    return fields


def _lookup(fields: dict[str, str], key: str) -> str:
    """Exact match, else a unique prefix match. Ambiguity is an error."""
    if key in fields:
        return fields[key]
    candidates = [name for name in fields if name.startswith(key)]
    if len(candidates) == 1:
        return fields[candidates[0]]
    if not candidates:
        known = ", ".join(sorted(fields))
        msg = f"Required field {key!r} not found in model_spec.md. Present: {known}."
        raise SpecParseError(msg)
    msg = f"Field {key!r} is ambiguous; matches {sorted(candidates)}."
    raise SpecParseError(msg)


def _number(fields: dict[str, str], key: str) -> float:
    raw = _lookup(fields, key)
    match = NUMBER.search(raw)
    if match is None:
        msg = f"Field {key!r} has value {raw!r}, which contains no number."
        raise SpecParseError(msg)
    return float(match.group(1))


def _scaled_number(fields: dict[str, str], key: str) -> int:
    """Read a value like ``128k`` or ``4.2 B`` into a plain integer."""
    raw = _lookup(fields, key)
    match = NUMBER.search(raw)
    if match is None:
        msg = f"Field {key!r} has value {raw!r}, which contains no number."
        raise SpecParseError(msg)
    suffix = raw[match.end() :].strip().lower()
    multiplier = MAGNITUDES.get(suffix[:1], 1) if suffix else 1
    return int(float(match.group(1)) * multiplier)


def _word(fields: dict[str, str], key: str) -> str:
    return _lookup(fields, key).strip().strip("`").lower()


def dtype_bytes(dtype: str) -> int:
    """Bytes per element for a dtype name.

    Raises on an unrecognised dtype: guessing here would silently halve or
    double every KV number downstream.
    """
    key = dtype.strip().strip("`").lower()
    if key not in DTYPE_BYTES:
        known = ", ".join(sorted(DTYPE_BYTES))
        msg = f"Unrecognised dtype {dtype!r}. Known dtype names: {known}."
        raise ValueError(msg)
    return DTYPE_BYTES[key]


def _gpu_memory_gb(raw: str) -> float:
    """Pull the capacity out of e.g. ``1x NVIDIA L4 (24 GB)``.

    Targeted at the parenthesised capacity rather than "first number in
    the string", which would return the device count.
    """
    match = MEMORY_IN_PARENS.search(raw)
    if match is None:
        msg = f"Could not read a GPU memory capacity from {raw!r}; expected '(N GB)'."
        raise SpecParseError(msg)
    return float(match.group(1))


def _model_name(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("## Model:"):
            return line.removeprefix("## Model:").strip()
    msg = "No '## Model:' heading found in model_spec.md."
    raise SpecParseError(msg)


def parse_model_spec(markdown: str) -> tuple[ModelSpec, ServingSpec]:
    """Parse both tables out of ``model_spec.md``."""
    fields = parse_tables(markdown)
    gpu = _lookup(fields, "gpu")
    model = ModelSpec(
        name=_model_name(markdown),
        parameters_b=_number(fields, "parameters"),
        layers=int(_number(fields, "layers")),
        d_model=int(_number(fields, "d_model")),
        attention_heads=int(_number(fields, "attention heads")),
        kv_heads=int(_number(fields, "kv heads")),
        head_dim=int(_number(fields, "head_dim")),
        vocab_size=_scaled_number(fields, "vocab"),
        weights_dtype=_word(fields, "weights precision"),
        kv_dtype=_word(fields, "kv cache precision"),
    )
    serving = ServingSpec(
        gpu=gpu,
        gpu_memory_gb=_gpu_memory_gb(gpu),
        memory_bandwidth_gb_s=_number(fields, "memory bandwidth"),
        peak_fp16_tflops=_number(fields, "fp16 dense compute"),
        max_model_len=int(_number(fields, "max_model_len")),
        gpu_memory_utilization=_number(fields, "gpu_memory_utilization"),
        runtime_overhead_gb=_number(fields, "non-kv runtime overhead"),
    )
    return model, serving
