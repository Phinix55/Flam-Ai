"""THE KEYSTONE (CLAUDE.md §4).

With every ablation flag OFF, ``ablation/legacy.py`` must reproduce
``starter_kit/fertility.py`` on ``starter_kit/corpus_sample/``. Until this
passes, no ablation delta is admissible: a delta measured against an
unverified baseline could be a rewrite artefact rather than a property of
the original.

Parity is proved two independent ways, because either alone is weak:

1. **stdout parity** -- the original run as a subprocess, its bytes
   compared to ``format_report``. Catches formatting and rounding, but the
   original prints only 2-3 decimals, so a difference in the fourth would
   survive.
2. **float parity** -- the original module loaded read-only via
   ``importlib`` and its own ``read_lines``/``analyze`` called directly,
   compared with ``==`` at full double precision. Catches what rounding
   hides.

Loading the original module is a read, not a modification: nothing is
written, moved or reformatted, so CLAUDE.md rule 2 holds.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from types import ModuleType

import pytest

from audit.ablation.flags import AblationFlags
from audit.ablation.legacy import analyze, format_report, read_lines, run
from audit.corpus.acquire import require_tiktoken_cache
from audit.tokenizers import registry

pytestmark = pytest.mark.parity

LANGS = ("eng", "hin")


@pytest.fixture(scope="module")
def corpora(config) -> dict[str, str]:
    """``{lang: file_text}`` in the same order the reported run used."""
    return {
        lang: (config.legacy_corpus_dir / f"{lang}_sample.txt").read_text(
            encoding="utf-8"
        )
        for lang in LANGS
    }


@pytest.fixture(scope="module")
def tokenizer(config):
    require_tiktoken_cache(config)
    return registry.load(config, "gpt2")


@pytest.fixture(scope="module")
def original(config) -> ModuleType:
    """The untouched original, imported read-only for direct comparison."""
    spec = importlib.util.spec_from_file_location(
        "starter_kit_fertility", config.legacy_script
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_original_cli(config, tokenizer_name: str = "gpt2") -> str:
    """Execute the untouched script as a subprocess and capture stdout.

    A subprocess, not an import, so no state from our process can leak
    into the reference output. The tiktoken cache path is passed through
    explicitly: without it the child would resolve a machine-local temp
    cache and the run would not be offline.
    """
    corpus = config.legacy_corpus_dir
    env = {**os.environ, "TIKTOKEN_CACHE_DIR": str(config.tiktoken_cache_dir)}
    proc = subprocess.run(
        [sys.executable, str(config.legacy_script)]
        + [f"--corpus={lang}={corpus / f'{lang}_sample.txt'}" for lang in LANGS]
        + ["--tokenizer", tokenizer_name],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return proc.stdout


# ---------------------------------------------------------------- proof 1


def test_all_flags_off_reproduces_the_original_stdout(config, corpora, tokenizer):
    results = run(corpora, tokenizer, AblationFlags.all_off())
    assert format_report(results, "gpt2") == _run_original_cli(config)


# ---------------------------------------------------------------- proof 2


def test_all_flags_off_reproduces_the_original_floats_exactly(
    config, corpora, tokenizer, original
):
    """Bit-exact, not ``approx``. Any tolerance here would let a genuine
    arithmetic difference hide inside it."""
    ours = run(corpora, tokenizer, AblationFlags.all_off())
    assert [r.lang for r in ours] == list(LANGS)
    for result in ours:
        path = config.legacy_corpus_dir / f"{result.lang}_sample.txt"
        their_lines = original.read_lines(str(path))
        their_fert, their_tpc = original.analyze(their_lines, tokenizer.encode)
        assert result.fertility == their_fert
        assert result.tokens_per_char == their_tpc
        assert result.n_lines == len(their_lines)


def test_line_ingestion_matches_the_original_line_for_line(config, corpora):
    """``read_lines`` is where strip/filter/normalise order could diverge
    invisibly, so it is compared on its own before aggregation hides it."""
    spec = importlib.util.spec_from_file_location(
        "starter_kit_fertility_lines", config.legacy_script
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for lang, text in corpora.items():
        path = config.legacy_corpus_dir / f"{lang}_sample.txt"
        assert read_lines(text, AblationFlags.all_off()) == module.read_lines(str(path))


def test_analyze_matches_the_original_on_adversarial_shaped_input(original, tokenizer):
    """Parity must hold on inputs the sample does not contain -- otherwise
    it is parity with ten sentences, not with the original."""
    lines = ["a  b", "ONE Two THREE", "क्ष हैं", "...", "x"]
    ours = analyze(lines, tokenizer, AblationFlags.all_off())
    theirs = original.analyze(lines, tokenizer.encode)
    assert ours == theirs


# ---------------------------------------------------------------- guards


def test_every_flag_off_is_the_declared_baseline():
    assert AblationFlags.all_off().enabled() == ()
    assert AblationFlags.all_off().label() == "baseline"


@pytest.mark.parametrize("flag", AblationFlags.flag_names())
def test_each_flag_is_independently_togglable(flag):
    """A flag that cannot be set alone cannot have an attributable delta."""
    assert AblationFlags.only(flag).enabled() == (flag,)


# Input crafted to exercise each flag's branch. A flag that is declared but
# never reaches its code path would report a zero delta in the Phase 4 sweep
# and be indistinguishable from a genuine null result -- which is how an
# unmeasured claim turns into a fabricated one. These inputs prove the wiring.
WIRING_PROBES: dict[str, list[str]] = {
    "split_on_unicode_whitespace": ["a  b"],  # split(" ")=3 vs split()=2
    # Not every caseful string moves: "ABC DEF" and "Bengaluru International
    # Airport" tokenize to the same count either way, while "NASA and ISRO"
    # gains a token when folded and "Quarterly Review" loses one. The sign is
    # not uniform, which is why H-03's predicted direction carries low
    # confidence even though its presence carries high confidence.
    "preserve_case": ["NASA and ISRO"],
    "micro_aggregate": ["a", "b c d e"],  # unequal line lengths
    "grapheme_denominator": ["क्ष"],  # 3 codepoints, 1 cluster
    "skip_nfc_normalisation": ["é"],  # NFD; NFC composes it to 1 cp
}

NO_PROBE_EXISTS = {"perturb_global_rng"}
"""Flags for which no input can produce a delta -- which is the hypothesis.

Listed explicitly so the null is a stated claim rather than an accident of
nobody having crafted a probe. If a probe is ever found, this set is wrong
and the flag's result changes meaning.
"""


def test_every_flag_has_a_wiring_probe_or_a_declared_reason():
    assert set(WIRING_PROBES) | NO_PROBE_EXISTS == set(AblationFlags.flag_names())


@pytest.mark.parametrize("flag", sorted(WIRING_PROBES))
def test_flag_actually_reaches_its_code_path(flag, tokenizer):
    lines = read_lines("\n".join(WIRING_PROBES[flag]), AblationFlags.all_off())
    baseline = analyze(lines, tokenizer, AblationFlags.all_off())
    flagged_lines = read_lines("\n".join(WIRING_PROBES[flag]), AblationFlags.only(flag))
    flagged = analyze(flagged_lines, tokenizer, AblationFlags.only(flag))
    assert baseline != flagged, f"{flag} is declared but never changes the result"
