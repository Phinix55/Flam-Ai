"""Construction of ``TokenizerAdapter`` instances from config entries.

This is the only place that maps a ``TokenizerSpec.kind`` onto a concrete
class. Adding a backend touches this file and ``config.TOKENIZERS`` --
never ``metrics/``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from audit.config import AuditConfig, TokenizerSpec
from audit.tokenizers.base import TokenizerAdapter
from audit.tokenizers.hf import HFAdapter
from audit.tokenizers.tiktoken import TiktokenAdapter

Builder = Callable[[TokenizerSpec, Path], TokenizerAdapter]


def _build_tiktoken(spec: TokenizerSpec, cache_dir: Path) -> TokenizerAdapter:
    return TiktokenAdapter(
        name=spec.key, encoding_name=spec.ref, cache_dir=cache_dir / "tiktoken"
    )


def _build_hf(spec: TokenizerSpec, cache_dir: Path) -> TokenizerAdapter:
    return HFAdapter(name=spec.key, repo_id=spec.ref, cache_dir=cache_dir)


BUILDERS: dict[str, Builder] = {
    "tiktoken": _build_tiktoken,
    "hf": _build_hf,
}


def build(spec: TokenizerSpec, cache_dir: Path) -> TokenizerAdapter:
    """Instantiate the adapter for ``spec``.

    Construction is lazy inside each adapter: nothing is loaded from disk
    until ``encode`` or ``vocab_size`` is first touched, so building the
    full registry costs nothing.
    """
    try:
        builder = BUILDERS[spec.kind]
    except KeyError as exc:
        known = ", ".join(sorted(BUILDERS))
        msg = (
            f"No adapter registered for tokenizer kind {spec.kind!r} "
            f"(tokenizer {spec.key!r}). Known kinds: {known}."
        )
        raise KeyError(msg) from exc
    return builder(spec, cache_dir)


def load_all(config: AuditConfig) -> dict[str, TokenizerAdapter]:
    """Every configured tokenizer, keyed by registry key."""
    return {
        spec.key: build(spec, config.tokenizer_cache_dir) for spec in config.tokenizers
    }


def load(config: AuditConfig, key: str) -> TokenizerAdapter:
    """One tokenizer by registry key."""
    return build(config.tokenizer(key), config.tokenizer_cache_dir)
