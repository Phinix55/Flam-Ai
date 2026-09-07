"""Running a stage twice yields byte-identical JSON but for the timestamp."""

from __future__ import annotations

import dataclasses
import json

from audit.provenance import TIMESTAMP_FIELD, strip_timestamp, write_results


def test_strip_timestamp_removes_only_the_volatile_field(config, tmp_path):
    path = write_results(tmp_path / "r.json", {"x": 1}, config)
    document = json.loads(path.read_text(encoding="utf-8"))
    stripped = strip_timestamp(document)
    assert TIMESTAMP_FIELD not in stripped["provenance"]
    assert stripped["x"] == 1
    assert (
        stripped["provenance"]["config_hash"] == document["provenance"]["config_hash"]
    )


def test_ablation_sweep_is_deterministic(config):
    """The sweep twice over, compared exactly.

    Run at reduced bootstrap iterations: determinism comes from the seeded
    ``Generator`` and from sorted iteration order, neither of which depends
    on the iteration count, and the full-scale run costs ~15 s. Tested on
    ``run_sweep`` rather than ``run_ablate`` so the real ``results/``
    artefact is never clobbered by the test suite.
    """
    from audit.ablation.runner import run_sweep

    fast = dataclasses.replace(config, bootstrap_iterations=64)
    assert run_sweep(fast) == run_sweep(fast)


def test_bootstrap_bounds_move_with_the_seed(config):
    """Determinism must come from seeding, not from the CI being constant."""
    from audit.ablation.runner import run_sweep

    a = run_sweep(dataclasses.replace(config, bootstrap_iterations=64, seed=1337))
    b = run_sweep(dataclasses.replace(config, bootstrap_iterations=64, seed=4242))
    key = ("NFC", "baseline", "eng")
    cell_a = a[key[0]][key[1]][key[2]]
    cell_b = b[key[0]][key[1]][key[2]]
    assert cell_a["fertility"] == cell_b["fertility"]
    assert cell_a["fertility_ci_low"] != cell_b["fertility_ci_low"]


def test_bench_payload_is_deterministic(config):
    """Bench has no RNG at all, so this is the strictest determinism case:
    identical inputs must give an identical dict, every run."""
    from audit.stages import _bench_payload

    assert _bench_payload(config) == _bench_payload(config)
