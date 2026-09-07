"""The tokenizer boundary.

``metrics/`` consumes token *counts*. It must never learn which backend
produced them, so every backend is reduced to this Protocol. Adding a
tokenizer is a new adapter plus one ``config.TOKENIZERS`` entry -- nothing
under ``metrics/`` changes.

``counts_special_tokens`` is on the Protocol rather than hidden inside
each backend because whether BOS/EOS land in the token count is a
property that must be *held constant* across languages when comparing
fertility. A backend that silently adds two tokens per line inflates
short lines more than long ones, so the flag has to be visible to the
layer doing the comparison.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenizerAdapter(Protocol):
    """Uniform view of one tokenizer backend.

    Implementations must be pure with respect to ``encode``: the same
    string yields the same ids for the lifetime of the process, with no
    hidden state carried between calls.
    """

    @property
    def name(self) -> str:
        """Stable registry key. Becomes a results-JSON key, so it must not
        change between runs or the artefacts stop being comparable."""
        ...

    @property
    def vocab_size(self) -> int:
        """Size of the token id space, for reporting alongside fertility.

        Fertility is only interpretable next to vocab size: a larger
        vocabulary buys lower fertility, so the two must be reported
        together or the comparison is not held constant.
        """
        ...

    @property
    def counts_special_tokens(self) -> bool:
        """Whether ``encode`` includes special tokens in its output.

        False means the returned ids are content tokens only.
        """
        ...

    def encode(self, text: str) -> list[int]:
        """Token ids for ``text``. No normalisation, no case folding.

        Any transformation of the input is the caller's responsibility and
        must be visible in the pipeline, never buried in an adapter --
        otherwise two tokenizers could differ because of preprocessing
        rather than vocabulary.
        """
        ...


class TokenizerLoadError(RuntimeError):
    """Raised when a backend cannot be constructed from the local cache.

    Analysis stages run offline. A load failure means the cache is missing
    or incomplete and must be repaired by ``make corpus`` -- it must never
    trigger a silent download mid-analysis.
    """
