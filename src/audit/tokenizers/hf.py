"""HuggingFace-backed adapter (xlm-roberta-base, MuRIL, ...)."""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path

from audit.tokenizers.base import TokenizerLoadError


class HFAdapter:
    """Adapter over a ``transformers`` fast tokenizer.

    ``add_special_tokens=False`` is fixed, not configurable. Fertility is a
    ratio of tokens to a linguistic denominator; BOS/EOS are a constant
    per-line offset that inflates short lines more than long ones, so
    including them would make the metric depend on sentence length. Holding
    it False keeps the comparison across languages honest and matches the
    tiktoken adapter's behaviour, so the two backends differ only in
    vocabulary.
    """

    def __init__(self, name: str, repo_id: str, cache_dir: Path) -> None:
        self._name = name
        self._repo_id = repo_id
        self._cache_dir = cache_dir

    @cached_property
    def _tokenizer(self) -> object:
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:  # pragma: no cover - dependency is pinned
            msg = "transformers is not installed. Run `make setup`."
            raise TokenizerLoadError(msg) from exc
        previous = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            return AutoTokenizer.from_pretrained(
                self._repo_id, cache_dir=str(self._cache_dir), local_files_only=True
            )
        except Exception as exc:
            raise TokenizerLoadError(self._missing_cache_message()) from exc
        finally:
            self._restore(previous)

    @staticmethod
    def _restore(previous: str | None) -> None:
        if previous is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous

    def _missing_cache_message(self) -> str:
        return (
            f"Tokenizer {self._repo_id!r} is not in the local cache at "
            f"{self._cache_dir}. Analysis stages are offline by contract; they "
            "never download. Run `make corpus` (the only network stage) first."
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def vocab_size(self) -> int:
        """Full id space including added/special tokens.

        ``len(tokenizer)`` rather than ``tokenizer.vocab_size``: the latter
        excludes added tokens and would under-report the id space that
        fertility is being read against.
        """
        return len(self._tokenizer)  # type: ignore[arg-type]

    @property
    def counts_special_tokens(self) -> bool:
        return False

    def encode(self, text: str) -> list[int]:
        return list(
            self._tokenizer.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]
        )
