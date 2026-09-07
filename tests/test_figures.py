"""Figures must be byte-identical across runs (Phase 5).

A figure that changes without its inputs changing is not evidence. These
tests render each figure twice and compare the bytes, which is what
catches non-deterministic ordering and embedded version/timestamp
metadata.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from audit.reporting.figures import (
    SAVE_KWARGS,
    ablation_deltas,
    fertility_by_denominator,
    throughput_curve,
    tokenizer_comparison,
)

FIGURES = [
    ("analysis.json", fertility_by_denominator),
    ("analysis.json", tokenizer_comparison),
    ("ablation.json", ablation_deltas),
    ("bench.json", throughput_curve),
]


def _digest(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(("artefact", "render"), FIGURES)
def test_figure_is_byte_identical_across_two_renders(
    artefact, render, config, tmp_path
):
    source = config.results_dir / artefact
    if not source.is_file():
        pytest.skip(f"{artefact} not generated yet; run `make {artefact[:-5]}`")
    data = json.loads(source.read_text(encoding="utf-8"))
    first = render(data, tmp_path / "a.png")
    second = render(data, tmp_path / "b.png")
    assert _digest(first) == _digest(second)


def test_software_metadata_is_suppressed():
    """Without this the matplotlib version is embedded in every PNG, so a
    dependency bump would change the bytes while the data stayed fixed."""
    assert SAVE_KWARGS["metadata"]["Software"] is None


def test_backend_is_non_interactive():
    import matplotlib

    assert matplotlib.get_backend().lower() == "agg"
