"""Ablation flags: one boolean per independently measurable claim.

Every field is False by default. All-False MUST reproduce
``starter_kit/fertility.py`` exactly -- that is the parity gate, and it is
what makes a delta attributable to the toggled behaviour rather than to
the rewrite.

Each flag name describes the **change**, never a verdict about the
original. ``True`` means "depart from legacy behaviour in exactly this one
way". The sweep machinery is written against ``dataclasses.fields``, so
adding a seventh flag is a one-line change here and nothing else moves.

Selected from the Phase 1 candidate list in ``NOTEBOOK.md``; the mapping
from flag to candidate is recorded there, including why the candidates
that were not selected were left out.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace


@dataclass(frozen=True, slots=True)
class AblationFlags:
    """Frozen switch panel. One field per independently togglable change.

    Invariants each field satisfies:

    1. It changes exactly one behaviour, so its delta is attributable.
    2. It is orthogonal to every other flag, so the all-on run equals the
       composition of the single-flag runs unless the flags genuinely
       interact -- and where they do, the gap is itself a result.
    3. Its name describes the change, not a verdict about the original.
    """

    split_on_unicode_whitespace: bool = False
    """H-05. Count words with ``str.split()`` instead of ``str.split(" ")``.

    Legacy splits on a literal single space, so a run of N consecutive
    spaces contributes N-1 empty strings to the word count. Isolates the
    denominator's sensitivity to whitespace runs and nothing else.
    """

    preserve_case: bool = False
    """H-03. Skip the ``line.lower()`` call before tokenization.

    Carries its own null control: Devanagari is caseless, so this flag
    must move Hindi by exactly zero. A non-zero Hindi delta means the flag
    is not isolating what it claims and its result is void.
    """

    micro_aggregate: bool = False
    """H-04. Aggregate as sum(tokens)/sum(denominator) instead of the mean
    of per-line ratios.

    Legacy weights every line equally regardless of length. This flag
    weights every line by its length. The two coincide exactly only when
    all lines share a denominator value.
    """

    grapheme_denominator: bool = False
    """H-02. Count the ``tok/char`` denominator in extended grapheme
    clusters instead of Unicode codepoints.

    Legacy uses ``len(line)``, i.e. codepoints. Isolates the denominator
    definition; the numerator and every other code path are untouched.
    """

    skip_nfc_normalisation: bool = False
    """H-13. Skip the unconditional ``unicodedata.normalize("NFC", ...)``.

    Predicted null on already-NFC input. Included so the null is measured
    rather than assumed.
    """

    perturb_global_rng: bool = False
    """H-12. Seed the global ``random`` module with a different value than
    the legacy script's 1337 before running.

    Legacy calls ``random.seed(1337)`` at import with no visible consumer.
    A zero delta under this flag is evidence that no code path -- including
    inside a tokenizer backend -- reads global RNG state. Predicted null.
    """

    @classmethod
    def flag_names(cls) -> tuple[str, ...]:
        """Declared flags, in declaration order."""
        return tuple(f.name for f in fields(cls))

    @classmethod
    def all_off(cls) -> AblationFlags:
        """The parity baseline: faithful legacy behaviour."""
        return cls()

    @classmethod
    def all_on(cls) -> AblationFlags:
        """Every change applied at once."""
        return cls(**dict.fromkeys(cls.flag_names(), True))

    @classmethod
    def only(cls, name: str) -> AblationFlags:
        """Exactly one change applied, everything else at legacy behaviour."""
        if name not in cls.flag_names():
            known = ", ".join(cls.flag_names()) or "<none declared yet>"
            msg = f"Unknown ablation flag {name!r}. Declared flags: {known}."
            raise KeyError(msg)
        return replace(cls(), **{name: True})

    def enabled(self) -> tuple[str, ...]:
        """Names of the flags currently set, for labelling results rows."""
        return tuple(name for name in self.flag_names() if getattr(self, name))

    def label(self) -> str:
        """Stable results-JSON key for this configuration."""
        enabled = self.enabled()
        if not enabled:
            return "baseline"
        if len(enabled) == len(self.flag_names()):
            return "all_on"
        return "+".join(enabled)
