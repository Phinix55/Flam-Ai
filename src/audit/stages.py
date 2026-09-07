"""Stage orchestration: the only place that wires I/O to pure functions.

``cli.py`` must stay a thin argparse shell, but ``metrics/`` and ``bench/``
must stay pure. Something has to read files, call the pure layer and write
``results/*.json``; this module is that seam. It contains no arithmetic of
its own -- every number it writes was computed by a tested pure function.

Every stage is independently runnable and idempotent: re-running one
overwrites its own artefact and touches nothing else.
"""

from __future__ import annotations

from pathlib import Path

from audit.config import AuditConfig
from audit.provenance import write_results


def run_corpus(config: AuditConfig) -> tuple[Path, ...]:
    """NETWORK STAGE. Fetch FLORES-200 + tokenizers into ``.cache/``.

    The only stage permitted to open a socket, and deliberately the only
    thing it does. Artefact generation is ``run_prepare``, which is
    offline -- otherwise ``results/corpus_stats.json`` could only be
    rebuilt with a network connection, and CLAUDE.md rule 4 requires
    ``make reproduce`` to regenerate *every* artefact offline from the
    cache alone.

    Idempotent: an existing cache is validated, never re-fetched.
    """
    from audit.corpus.acquire import fetch_corpus, fetch_hf_tokenizers, fetch_tiktoken

    fetch_tiktoken(config)
    fetch_hf_tokenizers(config)
    fetch_corpus(config)
    return run_prepare(config)


def run_prepare(config: AuditConfig) -> tuple[Path, ...]:
    """Offline. Validate alignment and emit the corpus artefacts.

    Writes ``results/corpus_stats.json`` and ``results/sample_manifest.json``
    from the cached corpus. Runs first in ``reproduce``.
    """
    from dataclasses import asdict

    from audit.corpus.acquire import language_file, require_corpus_cache
    from audit.corpus.prepare import corpus_stats, load_parallel, sample_manifest

    require_corpus_cache(config)
    inputs = [language_file(config, lang.flores_code) for lang in config.languages]
    stats = {
        form: asdict(corpus_stats(load_parallel(config, form), config))
        for form in config.normalisation_forms
    }
    records = load_parallel(config, config.normalisation_forms[0])
    return (
        write_results(
            config.results_dir / "corpus_stats.json",
            {"by_normalisation": stats},
            config,
            inputs,
        ),
        write_results(
            config.results_dir / "sample_manifest.json",
            sample_manifest(records, config),
            config,
            inputs,
        ),
    )


def run_ablate(config: AuditConfig) -> Path:
    """Offline. Sweep the flag grid -> ``results/ablation.json``.

    ``make ablate`` depends on ``make parity``: an ablation delta measured
    against an unverified baseline proves nothing, so the gate runs first.
    """
    from dataclasses import asdict

    from audit.ablation.flags import AblationFlags
    from audit.ablation.runner import (
        SWEEP_TOKENIZER,
        deltas,
        headline_ratios,
        legacy_sample_arms,
        run_sweep,
    )
    from audit.corpus.acquire import language_file, require_cache
    from audit.corpus.prepare import load_legacy_sample
    from audit.tokenizers import registry

    require_cache(config)
    sweep = run_sweep(config)
    tokenizer = registry.load(config, SWEEP_TOKENIZER)
    sample = legacy_sample_arms(load_legacy_sample(config), tokenizer)
    inputs = [language_file(config, lang.flores_code) for lang in config.languages]
    inputs += [
        config.legacy_corpus_dir / f"{lang}_sample.txt" for lang in ("eng", "hin")
    ]
    inputs.append(config.legacy_script)
    return write_results(
        config.results_dir / "ablation.json",
        {
            "tokenizer": SWEEP_TOKENIZER,
            "flags": list(AblationFlags.flag_names()),
            "sweep": sweep,
            "deltas": deltas(sweep),
            "headline_ratios": headline_ratios(sweep, config.pivot_language),
            "legacy_sample": {
                label: [asdict(r) for r in results] for label, results in sample.items()
            },
        },
        config,
        inputs,
    )


ANALYSIS_NORMALISATION = "NFC"
"""The analysis grid runs under one normalisation form.

NFC because it is what the legacy script produces, so corrected numbers
are comparable to reported ones. The NFC-vs-NFD question is answered by
the ablation sweep, which measures both; repeating it here would double
the grid without adding a measurement.
"""

HEADLINE_TOKENIZER = "gpt2"
"""The encoding the v0 report used, so its row is the comparable one."""


def _analysis_payload(config: AuditConfig) -> dict[str, object]:
    """Build the full grid. No I/O beyond reading the cached corpus."""
    from audit.corpus.prepare import load_parallel
    from audit.metrics.fertility import DENOMINATORS
    from audit.metrics.grid import build, measure_all
    from audit.tokenizers import registry

    records = load_parallel(config, ANALYSIS_NORMALISATION)
    corpus = {
        lang.code: [r.texts[lang.code] for r in records] for lang in config.languages
    }
    adapters = registry.load_all(config)
    grid = {
        key: build(
            measure_all(corpus, adapter),
            pivot=config.pivot_language,
            seed=config.seed,
            iterations=config.bootstrap_iterations,
            confidence=config.bootstrap_confidence,
        )
        for key, adapter in sorted(adapters.items())
    }
    return {
        "corpus": {
            "split": config.flores_split,
            "normalisation": ANALYSIS_NORMALISATION,
            "n_records": len(records),
        },
        "pivot": config.pivot_language,
        "headline_tokenizer": HEADLINE_TOKENIZER,
        "languages": [lang.code for lang in config.languages],
        "denominators": list(DENOMINATORS),
        "tokenizers": {
            spec.key: {
                "ref": spec.ref,
                "family": spec.family,
                "vocab_size": adapters[spec.key].vocab_size,
                "counts_special_tokens": adapters[spec.key].counts_special_tokens,
            }
            for spec in config.tokenizers
        },
        "grid": grid,
    }


def run_analyze(config: AuditConfig) -> Path:
    """Offline. Tokenizers x languages x denominators -> ``results/analysis.json``."""
    from audit.corpus.acquire import language_file, require_cache
    from audit.reporting.figures import (
        ablation_deltas,
        fertility_by_denominator,
        tokenizer_comparison,
    )

    require_cache(config)
    payload = _analysis_payload(config)
    path = write_results(
        config.results_dir / "analysis.json",
        payload,
        config,
        [language_file(config, lang.flores_code) for lang in config.languages],
    )
    figures = config.figures_dir
    fertility_by_denominator(payload, figures / "fertility_by_denominator.png")
    tokenizer_comparison(payload, figures / "tokenizer_comparison.png")
    ablation_path = config.results_dir / "ablation.json"
    if ablation_path.is_file():
        import json

        ablation_deltas(
            json.loads(ablation_path.read_text(encoding="utf-8")),
            figures / "ablation_deltas.png",
        )
    return path


LONG_PROMPT_LEN = 3584
"""The sweep B2 asks about. Read from the log, not assumed to exist:
``log_analysis.sweep`` raises and lists the available prompt lengths."""

B3_ROW = (24, 3584)
"""(batch_size, prompt_len) of the row B3 asks for goodput on."""


def _bench_payload(config: AuditConfig) -> dict[str, object]:
    """Every arithmetic step, named. Pure given the two input files."""
    from dataclasses import asdict

    from audit.bench.kv_math import (
        MEMORY_UNITS,
        concurrency_ceiling,
        kv_bytes_per_token,
    )
    from audit.bench.log_analysis import (
        correlate_ceiling,
        find_knee,
        goodput_derivations,
        parse_log,
        prefill_share,
        reconstruct_reported,
    )
    from audit.bench.spec import parse_model_spec

    model, serving = parse_model_spec(
        config.model_spec_path.read_text(encoding="utf-8")
    )
    rows = parse_log(config.bench_log_path.read_text(encoding="utf-8"))
    long_sweep = [r for r in rows if r.prompt_len == LONG_PROMPT_LEN]
    ceilings = {
        unit: asdict(concurrency_ceiling(model, serving, serving.max_model_len, unit))
        for unit in sorted(MEMORY_UNITS)
    }
    b3 = next(r for r in rows if (r.batch_size, r.prompt_len) == B3_ROW)
    return {
        "spec": {"model": asdict(model), "serving": asdict(serving)},
        "b1": {
            "kv_bytes_per_token": asdict(kv_bytes_per_token(model)),
            "concurrency_ceiling_by_memory_unit": ceilings,
        },
        "b1_check_against_log": {
            unit: correlate_ceiling(long_sweep, c["exact_sequences"])
            for unit, c in ceilings.items()
        },
        "b2": {
            "long_prompt_len": LONG_PROMPT_LEN,
            "knee": find_knee(long_sweep),
            "rows": [asdict(r) for r in long_sweep],
        },
        "b3": {
            "row": asdict(b3),
            "goodput_derivations": [asdict(d) for d in goodput_derivations(b3)],
            "prefill_share": prefill_share(b3),
            "reported_counter_identity": {
                f"batch{r.batch_size}_prompt{r.prompt_len}": reconstruct_reported(r)
                for r in rows
            },
            "max_identity_error_pct": max(
                reconstruct_reported(r)["relative_error_vs_prompt_plus_generated_pct"]
                for r in rows
            ),
        },
    }


def run_bench(config: AuditConfig) -> Path:
    """Offline. Spec parse + KV math + log analysis -> ``results/bench.json``."""
    from audit.reporting.figures import throughput_curve

    payload = _bench_payload(config)
    path = write_results(
        config.results_dir / "bench.json",
        payload,
        config,
        [config.model_spec_path, config.bench_log_path],
    )
    throughput_curve(payload, config.figures_dir / "throughput_curve.png")
    return path


def run_partc(config: AuditConfig) -> Path:
    """Offline. Part C envelope -> ``results/partc.json``.

    Reads two measured inputs from earlier stages -- tokens per parallel
    sentence under the Indic-aware tokenizer, and the B3 output goodput --
    so the envelope inherits this repo's measurements rather than restating
    round numbers. Chooses no path and ranks nothing.
    """
    import json

    from audit.partc import PartCAssumptions, build, sensitivity

    analysis = json.loads(
        (config.results_dir / "analysis.json").read_text(encoding="utf-8")
    )
    bench = json.loads((config.results_dir / "bench.json").read_text(encoding="utf-8"))
    indic = analysis["grid"]["muril"]["absolute"]["sentences"]
    tokens_per_sentence = {code: cell["macro"] for code, cell in indic.items()}
    goodput = bench["b3"]["goodput_derivations"][0]["value_tok_s"]
    assumptions = PartCAssumptions()
    payload = build(assumptions, tokens_per_sentence, goodput)
    payload["sensitivity_gpu_hours_by_pair_count"] = sensitivity(
        assumptions, tokens_per_sentence
    )
    payload["measured_inputs"] = {
        "tokens_per_sentence_source": "analysis.grid.muril.absolute.sentences.*.macro",
        "goodput_source": "bench.b3.goodput_derivations.0.value_tok_s",
    }
    return write_results(config.results_dir / "partc.json", payload, config, [])


def run_render(config: AuditConfig) -> tuple[Path, ...]:
    """Offline. ``results/*.json`` + templates -> ``deliverable/``."""
    from audit.reporting.render import render_all

    return render_all(config)


ADVERSARIAL_DIR = Path("tests") / "fixtures" / "adversarial"


def run_adversarial(config: AuditConfig) -> Path:
    """Offline. Run every adversarial fixture through the pipeline.

    Records what each fixture does -- including what raises -- into
    ``results/adversarial.json``. A fixture that raises is a documented
    outcome, not a failure of this stage.
    """
    from audit.ablation.runner import SWEEP_TOKENIZER
    from audit.corpus.acquire import require_tiktoken_cache
    from audit.reporting.adversarial import run_fixtures
    from audit.tokenizers import registry

    require_tiktoken_cache(config)
    directory = config.root / ADVERSARIAL_DIR
    if not directory.is_dir():
        msg = f"Adversarial fixtures not found at {directory}."
        raise FileNotFoundError(msg)
    return write_results(
        config.results_dir / "adversarial.json",
        run_fixtures(directory, registry.load(config, SWEEP_TOKENIZER)),
        config,
        sorted(directory.glob("*.txt")),
    )
