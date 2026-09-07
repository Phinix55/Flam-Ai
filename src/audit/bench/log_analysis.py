"""Analysis of ``bench/bench_log.csv``. Pure functions over parsed rows.

Goodput is computed **two independent ways** so they can be cross-checked
against each other and against the harness's own reported counter. Two
derivations that agree are evidence; one derivation is an assertion.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

COLUMNS = (
    "batch_size",
    "prompt_len",
    "gen_len",
    "num_requests",
    "wall_clock_s",
    "reported_tok_s",
    "ttft_ms_p50",
    "itl_ms_p50",
    "e2e_ms_p95",
    "preempted_seqs",
    "kv_cache_util",
)


@dataclass(frozen=True, slots=True)
class BenchRow:
    """One load-test run, verbatim from the CSV. No derived fields."""

    batch_size: int
    prompt_len: int
    gen_len: int
    num_requests: int
    wall_clock_s: float
    reported_tok_s: float
    ttft_ms_p50: float
    itl_ms_p50: float
    e2e_ms_p95: float
    preempted_seqs: int
    kv_cache_util: float

    @property
    def context_tokens(self) -> int:
        """Tokens resident per sequence at peak: prompt plus everything
        generated, since no request stops early."""
        return self.prompt_len + self.gen_len

    @property
    def output_tokens(self) -> int:
        return self.num_requests * self.gen_len

    @property
    def total_tokens(self) -> int:
        """Prompt plus generated, over all requests."""
        return self.num_requests * self.context_tokens


@dataclass(frozen=True, slots=True)
class GoodputDerivation:
    """One way of computing throughput, with its inputs named.

    ``method`` states which columns were used, so a disagreement between
    two derivations localises to specific columns rather than to "the
    numbers differ".
    """

    method: str
    columns_used: tuple[str, ...]
    tokens_counted: str
    value_tok_s: float


def _row(raw: dict[str, str]) -> BenchRow:
    """Build one row with every field converted explicitly.

    Written out rather than derived from the dataclass fields: an
    int-vs-float mistake here would silently truncate ``kv_cache_util`` to
    0, and a generic converter would hide which column it happened to.
    """
    return BenchRow(
        batch_size=int(raw["batch_size"]),
        prompt_len=int(raw["prompt_len"]),
        gen_len=int(raw["gen_len"]),
        num_requests=int(raw["num_requests"]),
        wall_clock_s=float(raw["wall_clock_s"]),
        reported_tok_s=float(raw["reported_tok_s"]),
        ttft_ms_p50=float(raw["ttft_ms_p50"]),
        itl_ms_p50=float(raw["itl_ms_p50"]),
        e2e_ms_p95=float(raw["e2e_ms_p95"]),
        preempted_seqs=int(raw["preempted_seqs"]),
        kv_cache_util=float(raw["kv_cache_util"]),
    )


def parse_log(csv_text: str) -> tuple[BenchRow, ...]:
    """Parse the CSV. Raises on a missing or extra column; never coerces."""
    reader = csv.DictReader(io.StringIO(csv_text))
    header = tuple(reader.fieldnames or ())
    if header != COLUMNS:
        missing = sorted(set(COLUMNS) - set(header))
        extra = sorted(set(header) - set(COLUMNS))
        msg = (
            f"bench_log.csv header mismatch. Missing: {missing or 'none'}; "
            f"unexpected: {extra or 'none'}. Refusing to guess column meaning."
        )
        raise ValueError(msg)
    rows = [_row(raw) for raw in reader]
    if not rows:
        msg = "bench_log.csv contains a header but no data rows."
        raise ValueError(msg)
    return tuple(rows)


def goodput_derivations(row: BenchRow) -> tuple[GoodputDerivation, ...]:
    """Compute output throughput for one row by two independent routes.

    Held constant: the row. The derivations differ only in which columns
    they trust, which is what makes their agreement -- or the size of their
    gap -- informative about the columns themselves.

    They are not expected to be equal. Route 1 spreads output tokens over
    the whole run including prefill; route 2 measures the decode loop only.
    The gap between them is therefore the prefill share, which is a
    quantity rather than an error.
    """
    return (
        GoodputDerivation(
            method="output tokens / wall clock",
            columns_used=("num_requests", "gen_len", "wall_clock_s"),
            tokens_counted="generated only",
            value_tok_s=row.output_tokens / row.wall_clock_s,
        ),
        GoodputDerivation(
            method="batch size / median inter-token latency",
            columns_used=("batch_size", "itl_ms_p50"),
            tokens_counted="generated only, decode phase",
            value_tok_s=row.batch_size / (row.itl_ms_p50 / 1000.0),
        ),
    )


def reconstruct_reported(row: BenchRow) -> dict[str, float]:
    """Reproduce ``reported_tok_s`` from the other columns.

    States what the harness counter contains as a checkable identity,
    rather than as an assumption about the harness.
    """
    prompt_and_generated = row.total_tokens / row.wall_clock_s
    generated_only = row.output_tokens / row.wall_clock_s
    return {
        "reported_tok_s": row.reported_tok_s,
        "prompt_plus_generated_over_wall": prompt_and_generated,
        "generated_only_over_wall": generated_only,
        "relative_error_vs_prompt_plus_generated_pct": abs(
            prompt_and_generated - row.reported_tok_s
        )
        / row.reported_tok_s
        * 100.0,
        "ratio_reported_to_generated_only": row.reported_tok_s / generated_only,
    }


def prefill_share(row: BenchRow) -> dict[str, float]:
    """Split the run into decode and everything else, from ITL alone."""
    decode_seconds = row.gen_len * (row.itl_ms_p50 / 1000.0)
    other = row.wall_clock_s - decode_seconds
    return {
        "decode_seconds_from_itl": decode_seconds,
        "non_decode_seconds": other,
        "non_decode_share": other / row.wall_clock_s,
        "prompt_tokens": float(row.num_requests * row.prompt_len),
        "implied_prefill_tok_s": (row.num_requests * row.prompt_len) / other
        if other > 0
        else float("nan"),
    }


def sweep(rows: Sequence[BenchRow], prompt_len: int) -> tuple[BenchRow, ...]:
    """Rows at one prompt length, ordered by batch size."""
    selected = tuple(
        sorted(
            (r for r in rows if r.prompt_len == prompt_len), key=lambda r: r.batch_size
        )
    )
    if not selected:
        available = sorted({r.prompt_len for r in rows})
        msg = f"No rows with prompt_len={prompt_len}. Available: {available}."
        raise ValueError(msg)
    return selected


def correlate_ceiling(rows: Sequence[BenchRow], ceiling: float) -> dict[str, Any]:
    """Test a predicted concurrency ceiling against what the log did.

    Two independent signals, neither of which the prediction was fitted
    to:

    * **Preemption.** Above the ceiling, the excess sequences cannot be
      resident, so ``preempted_seqs`` should track ``batch_size - floor(ceiling)``.
    * **Capacity inversion.** On rows where ``kv_cache_util`` is not
      clipped at its maximum, ``resident_tokens / kv_cache_util`` inverts
      to the total KV capacity, which should match the predicted one.

    Saturated rows are excluded from the inversion and flagged: a clipped
    utilisation cannot be inverted, and treating it as if it could would
    manufacture agreement.
    """
    floor_ceiling = int(ceiling)
    utilisations = [r.kv_cache_util for r in rows]
    clipped = max(utilisations) if utilisations else 0.0
    per_row = []
    for row in sorted(rows, key=lambda r: r.batch_size):
        saturated = row.kv_cache_util >= clipped
        per_row.append(
            {
                "batch_size": row.batch_size,
                "resident_tokens": row.batch_size * row.context_tokens,
                "kv_cache_util": row.kv_cache_util,
                "saturated": saturated,
                "implied_capacity_tokens": None
                if saturated or row.kv_cache_util == 0
                else (row.batch_size * row.context_tokens) / row.kv_cache_util,
                "preempted_seqs": row.preempted_seqs,
                "predicted_preempted": max(0, row.batch_size - floor_ceiling),
                "preemption_matches": row.preempted_seqs
                == max(0, row.batch_size - floor_ceiling),
            }
        )
    return {
        "predicted_ceiling_exact": ceiling,
        "predicted_ceiling_floor": floor_ceiling,
        "saturation_threshold": clipped,
        "rows": per_row,
        "preemption_matches_all_rows": all(r["preemption_matches"] for r in per_row),
    }


def find_knee(rows: Sequence[BenchRow]) -> dict[str, Any]:
    """Locate the batch size past which reported throughput stops rising.

    Returns the batch size, the values either side, and the co-moving
    columns at that point, so the knee is characterised rather than merely
    located.
    """
    ordered = sorted(rows, key=lambda r: r.batch_size)
    if len(ordered) < 2:
        msg = "Need at least two rows to locate a knee."
        raise ValueError(msg)
    peak = max(ordered, key=lambda r: r.reported_tok_s)
    index = ordered.index(peak)
    following = ordered[index + 1] if index + 1 < len(ordered) else None
    return {
        "knee_batch_size": peak.batch_size,
        "peak_reported_tok_s": peak.reported_tok_s,
        "is_last_row_tested": following is None,
        "next_batch_size": following.batch_size if following else None,
        "next_reported_tok_s": following.reported_tok_s if following else None,
        "at_knee": {
            "kv_cache_util": peak.kv_cache_util,
            "preempted_seqs": peak.preempted_seqs,
            "ttft_ms_p50": peak.ttft_ms_p50,
            "itl_ms_p50": peak.itl_ms_p50,
        },
        "after_knee": None
        if following is None
        else {
            "kv_cache_util": following.kv_cache_util,
            "preempted_seqs": following.preempted_seqs,
            "ttft_ms_p50": following.ttft_ms_p50,
            "itl_ms_p50": following.itl_ms_p50,
        },
    }
