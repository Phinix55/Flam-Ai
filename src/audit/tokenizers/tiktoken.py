"""tiktoken-backed adapter (gpt2, cl100k_base, ...).

Module name mirrors BLUEPRINT.md 0. Python 3 uses absolute imports, so
``import tiktoken`` below resolves to the third-party package, not to this
module.
"""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path

from audit.tokenizers.base import TokenizerLoadError

CACHE_ENV_VAR = "TIKTOKEN_CACHE_DIR"
"""tiktoken resolves its BPE cache from this variable.

Set from ``AuditConfig`` rather than left to tiktoken's default temp
directory, so the cache lives inside the repo, survives reboots, and is
the same directory ``make corpus`` populated. Without it an "offline" run
could silently succeed off a machine-local temp cache that a clean
checkout would not have.
"""


def set_cache_dir(cache_dir: Path) -> None:
    """Point tiktoken at ``cache_dir``. Idempotent."""
    os.environ[CACHE_ENV_VAR] = str(cache_dir)


class TiktokenAdapter:
    """Adapter over a tiktoken ``Encoding``.

    tiktoken's ``encode`` emits content tokens only -- no BOS/EOS -- so
    ``counts_special_tokens`` is False. This is the backend the v0 report
    used, which is why it stays in the grid unmodified.
    """

    def __init__(self, name: str, encoding_name: str, cache_dir: Path) -> None:
        self._name = name
        self._encoding_name = encoding_name
        self._cache_dir = cache_dir

    @cached_property
    def _encoding(self) -> object:
        try:
            import tiktoken
        except ImportError as exc:  # pragma: no cover - dependency is pinned
            msg = "tiktoken is not installed. Run `make setup`."
            raise TokenizerLoadError(msg) from exc
        set_cache_dir(self._cache_dir)
        try:
            return tiktoken.get_encoding(self._encoding_name)
        except Exception as exc:
            msg = (
                f"Could not load tiktoken encoding {self._encoding_name!r} for "
                f"tokenizer {self._name!r}. Analysis stages run offline: the BPE "
                "file must already be in TIKTOKEN_CACHE_DIR. Run `make corpus`."
            )
            raise TokenizerLoadError(msg) from exc

    @property
    def name(self) -> str:
        return self._name

    @property
    def vocab_size(self) -> int:
        return int(self._encoding.n_vocab)  # type: ignore[attr-defined]

    @property
    def counts_special_tokens(self) -> bool:
        return False

    def encode(self, text: str) -> list[int]:
        return list(self._encoding.encode(text))  # type: ignore[attr-defined]
