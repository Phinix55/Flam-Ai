"""Config is frozen, discoverable and hashed path-independently."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from audit.config import AuditConfig, Language, TokenizerSpec


def test_config_is_frozen(config):
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.seed = 1  # type: ignore[misc]


def test_seed_matches_legacy_script(config):
    """The legacy script seeds 1337. Reusing it removes seed choice as an
    explanation for any parity difference."""
    assert config.seed == 1337


def test_required_languages_present(config):
    """A1 needs >=4 languages incl. English, Hindi and two Dravidian."""
    codes = {lang.code for lang in config.languages}
    assert {"eng", "hin", "kan", "tam", "tel"} <= codes
    dravidian = {"kan", "tam", "tel"} & codes
    assert len(dravidian) >= 2


def test_tokenizer_registry_covers_a3_requirement(config):
    """A3 needs >=2 tokenizers, one multilingual/Indic-aware, and must keep
    the gpt2 encoding the v0 report actually used."""
    families = {spec.family for spec in config.tokenizers}
    assert len(config.tokenizers) >= 2
    assert {"multilingual", "indic-aware"} & families
    assert config.tokenizer("gpt2").ref == "gpt2"


def test_starter_kit_is_discovered_without_being_moved(config):
    """Works for both the flat and the nested zip extraction layout."""
    assert config.legacy_script.is_file()
    assert config.model_spec_path.is_file()
    assert config.bench_log_path.is_file()
    assert (config.legacy_corpus_dir / "eng_sample.txt").is_file()


def test_config_hash_is_path_independent():
    """Same experiment on two machines must hash identically."""
    a = AuditConfig(root=Path("/somewhere/else"))
    b = AuditConfig(root=Path("/another/place"))
    assert a.config_hash() == b.config_hash()


def test_config_hash_moves_when_the_experiment_moves(config):
    changed = dataclasses.replace(config, bootstrap_iterations=999)
    assert changed.config_hash() != config.config_hash()


def test_unknown_lookups_raise_with_the_known_set(config):
    with pytest.raises(KeyError, match="Configured languages"):
        config.language("xxx")
    with pytest.raises(KeyError, match="Registered tokenizers"):
        config.tokenizer("xxx")


def test_registry_entries_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Language("a", "b", "c", "d").code = "z"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        TokenizerSpec("a", "b", "c", "d").key = "z"  # type: ignore[misc]
