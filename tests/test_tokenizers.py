"""The adapter boundary holds, and load failures are loud."""

from __future__ import annotations

from pathlib import Path

import pytest

from audit.config import TokenizerSpec
from audit.tokenizers import registry
from audit.tokenizers.base import TokenizerAdapter, TokenizerLoadError
from audit.tokenizers.hf import HFAdapter
from audit.tokenizers.tiktoken import TiktokenAdapter


def test_every_registered_tokenizer_builds(config):
    adapters = registry.load_all(config)
    assert set(adapters) == {spec.key for spec in config.tokenizers}


PROTOCOL_MEMBERS = ("name", "vocab_size", "counts_special_tokens", "encode")


def test_adapters_satisfy_the_protocol(config):
    """Checked on the class, not the instance: ``isinstance`` against a
    runtime-checkable Protocol evaluates every property, which would force
    a tokenizer load and defeat the laziness the registry depends on."""
    for adapter in registry.load_all(config).values():
        for member in PROTOCOL_MEMBERS:
            assert hasattr(type(adapter), member), f"{adapter} lacks {member}"


def test_protocol_rejects_an_incomplete_implementation():
    class Missing:
        name = "x"
        vocab_size = 1

    assert not isinstance(Missing(), TokenizerAdapter)


def test_building_is_lazy(config):
    """Constructing the registry must not touch disk or the network, so the
    grid can be assembled before deciding which cells to run."""
    adapter = registry.load(config, "muril")
    assert adapter.name == "muril"


def test_unknown_kind_raises_with_known_kinds():
    with pytest.raises(KeyError, match="Known kinds"):
        registry.build(TokenizerSpec("x", "wat", "y", "z"), Path("/tmp"))


def test_special_tokens_are_excluded_by_both_backends(config):
    """Fertility must not depend on a per-line BOS/EOS offset, which would
    inflate short lines more than long ones."""
    for adapter in registry.load_all(config).values():
        assert adapter.counts_special_tokens is False


def test_hf_missing_cache_is_an_actionable_error(tmp_path):
    adapter = HFAdapter("x", "definitely/not-a-real-repo-id", tmp_path)
    with pytest.raises(TokenizerLoadError, match="make corpus"):
        adapter.encode("hello")


def test_tiktoken_unknown_encoding_is_an_actionable_error(config):
    adapter = TiktokenAdapter("x", "not_a_real_encoding", config.tiktoken_cache_dir)
    with pytest.raises(TokenizerLoadError, match="offline"):
        adapter.encode("hello")


def test_missing_tiktoken_cache_names_the_repair(config, tmp_path):
    """An empty directory must not read as a populated cache."""
    import dataclasses

    from audit.corpus.acquire import CacheMissError, require_tiktoken_cache

    with pytest.raises(CacheMissError, match="make corpus"):
        require_tiktoken_cache(dataclasses.replace(config, root=tmp_path))
