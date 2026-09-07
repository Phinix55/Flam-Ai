"""Ablation flag machinery, tested independently of any specific flag.

These tests are written against ``dataclasses.fields``, so they keep
holding as Phase 2 adds flags. That is the point: they prove "adding a
flag is a one-file change", which the defense session may ask for live.
"""

from __future__ import annotations

import dataclasses

import pytest

from audit.ablation.flags import AblationFlags


def test_baseline_has_every_flag_off():
    baseline = AblationFlags.all_off()
    assert baseline.enabled() == ()
    assert baseline.label() == "baseline"


def test_flags_are_frozen():
    """Declared frozen + slots, so a flag cannot be mutated mid-sweep and
    silently change what an arm of the grid measured."""
    params = AblationFlags.__dataclass_params__  # type: ignore[attr-defined]
    assert params.frozen is True
    assert not hasattr(AblationFlags.all_off(), "__dict__")


def test_defaults_are_all_false():
    """All-off must be the legacy behaviour, so no field may default True."""
    for field in dataclasses.fields(AblationFlags):
        assert field.default is False, f"{field.name} must default to False"


def test_only_sets_exactly_one_flag():
    for name in AblationFlags.flag_names():
        assert AblationFlags.only(name).enabled() == (name,)


def test_only_rejects_an_unknown_flag():
    with pytest.raises(KeyError, match="Declared flags"):
        AblationFlags.only("no_such_flag")


def test_all_on_enables_every_declared_flag():
    assert set(AblationFlags.all_on().enabled()) == set(AblationFlags.flag_names())


def test_labels_are_unique_across_the_sweep():
    """Labels become results-JSON keys; a collision would silently overwrite
    one arm of the evidence grid."""
    if not AblationFlags.flag_names():
        pytest.skip("no flags declared yet; Phase 2 adds them after claim selection")
    configurations = [AblationFlags.all_off(), AblationFlags.all_on()]
    configurations += [AblationFlags.only(n) for n in AblationFlags.flag_names()]
    labels = [c.label() for c in configurations]
    assert len(labels) == len(set(labels))
