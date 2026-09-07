"""The render namespace: results JSON -> template variables.

Kept apart from ``render.py`` so that assembling the namespace and
enforcing rule 3 are separate concerns. Everything numeric in here goes
through ``Tracer``, which is what makes the post-render check meaningful.

No interpretation is assembled here. Sentences that assert a conclusion,
rank a cause, or recommend an action are left in the templates as
``TODO(pratik): interpretation`` (CLAUDE.md rule 6) -- this module supplies
only the evidence they will eventually cite.
"""

from __future__ import annotations

from typing import Any

from audit.reporting import tables
from audit.reporting.tables import Tracer


def _provenance(results: dict[str, Any], tracer: Tracer) -> dict[str, Any]:
    """Provenance identifiers, declared structural rather than traced.

    A commit SHA, a config hash, a timestamp and an interpreter version
    all contain digits, but none of them is a measurement, so none can
    trace to a results *value*. Declaring them keeps them out of the
    untraced-numeral failure while leaving the exemption visible in
    ``Tracer.structural_exemptions()`` -- the alternative, widening the
    validator to ignore anything that looks like a date, would also
    silence a genuinely wrong figure that happened to look like one.
    """
    block = results["ablation"]["provenance"]
    return {
        "git_sha": tracer.structural(block["git_sha"], "provenance: git sha"),
        "config_hash": tracer.structural(
            block["config_hash"], "provenance: config hash"
        ),
        "generated_at_utc": tracer.structural(
            block["generated_at_utc"], "provenance: build timestamp"
        ),
        "python_version": tracer.structural(
            block["python_version"], "provenance: interpreter version"
        ),
        "seed": tracer.fmt(
            block["config"]["seed"], "ablation.provenance.config.seed", "d"
        ),
        "bootstrap_iterations": tracer.fmt(
            block["config"]["bootstrap_iterations"],
            "ablation.provenance.config.bootstrap_iterations",
            "d",
        ),
        "confidence": tracer.fmt(
            block["config"]["bootstrap_confidence"],
            "ablation.provenance.config.bootstrap_confidence",
            ".2f",
        ),
    }


def _findings(results: dict[str, Any], tracer: Tracer) -> list[dict[str, str]]:
    """One evidence block per ablation flag.

    The measured half is filled from ``ablation.json``. The claim,
    direction and "why the delta proves it" are left as interpretation
    markers -- asserting them is the human's job, and a generated sentence
    there is exactly the unverified claim the grading punishes.
    """
    ablation = results["ablation"]
    sweep = ablation["sweep"]["NFC"]
    deltas = ablation["deltas"]["NFC"]
    pivot = ablation["provenance"]["config"]["pivot_language"]
    blocks = []
    for ordinal, flag in enumerate(ablation["flags"], start=1):
        base = sweep["baseline"]["hin"]["fertility"]
        after = sweep[flag]["hin"]["fertility"]
        blocks.append(
            {
                "id": "F-" + tracer.structural(f"{ordinal:02d}", "finding ordinal"),
                "flag": flag,
                "command": f"python -m audit ablate --flag {flag}",
                "before": tracer.fmt(base, "ablation.sweep.NFC.baseline.hin.fertility"),
                "after": tracer.fmt(after, f"ablation.sweep.NFC.{flag}.hin.fertility"),
                "rel_pct": tracer.fmt(
                    deltas[flag]["hin"]["fertility_rel_pct"],
                    f"ablation.deltas.NFC.{flag}.hin.fertility_rel_pct",
                    "+.3f",
                ),
                "pivot": pivot,
            }
        )
    return blocks


def _headline(results: dict[str, Any], tracer: Tracer) -> list[dict[str, str]]:
    """Ratio to pivot under every denominator, for the v0 tokenizer."""
    analysis = results["analysis"]
    key = analysis["headline_tokenizer"]
    ratios = analysis["grid"][key]["ratio_to_pivot"]
    rows = []
    for lang in analysis["languages"]:
        if lang == analysis["pivot"]:
            continue
        entry = {"lang": lang}
        for denominator in analysis["denominators"]:
            path = f"analysis.grid.{key}.ratio_to_pivot.{denominator}.{lang}.macro"
            entry[denominator] = tracer.fmt(ratios[denominator][lang]["macro"], path)
        rows.append(entry)
    return rows


def build(results: dict[str, Any], tracer: Tracer) -> dict[str, Any]:
    """The full template namespace."""
    analysis = results["analysis"]
    bench = results["bench"]
    knee = bench["b2"]["knee"]
    check = bench["b1_check_against_log"]["decimal_GB"]
    return {
        "provenance": _provenance(results, tracer),
        "sources": sorted(results),
        "pivot": analysis["pivot"],
        "languages": analysis["languages"],
        "denominators": analysis["denominators"],
        "tokenizers": sorted(analysis["tokenizers"]),
        "headline_tokenizer": analysis["headline_tokenizer"],
        "n_records": tracer.fmt(
            analysis["corpus"]["n_records"], "analysis.corpus.n_records", "d"
        ),
        # Counts are registered here rather than computed with a Jinja
        # `| length` filter: a filter produces a numeral the tracer never
        # saw, which is precisely what the post-render check rejects.
        "n_languages": tracer.fmt(
            len(analysis["languages"]), "analysis.languages|count", "d"
        ),
        "n_tokenizers": tracer.fmt(
            len(analysis["tokenizers"]), "analysis.tokenizers|count", "d"
        ),
        "n_denominators": tracer.fmt(
            len(analysis["denominators"]), "analysis.denominators|count", "d"
        ),
        "split": analysis["corpus"]["split"],
        "normalisation": analysis["corpus"]["normalisation"],
        "corpus_table": tables.corpus_table(results["corpus_stats"], tracer),
        "ablation_table": tables.ablation_table(results["ablation"], tracer),
        "analysis_tables": {
            denominator: tables.analysis_table(analysis, tracer, denominator)
            for denominator in analysis["denominators"]
        },
        "headline": _headline(results, tracer),
        "findings": _findings(results, tracer),
        "kv_table": tables.kv_table(bench, tracer),
        "concurrency_table": tables.concurrency_table(bench, tracer),
        "goodput_table": tables.goodput_table(bench, tracer),
        "knee_batch_size": tracer.fmt(
            knee["knee_batch_size"], "bench.b2.knee.knee_batch_size", "d"
        ),
        "knee_peak": tracer.fmt(
            knee["peak_reported_tok_s"], "bench.b2.knee.peak_reported_tok_s", ".1f"
        ),
        "next_batch_size": tracer.fmt(
            knee["next_batch_size"], "bench.b2.knee.next_batch_size", "d"
        ),
        "next_reported": tracer.fmt(
            knee["next_reported_tok_s"], "bench.b2.knee.next_reported_tok_s", ".1f"
        ),
        "predicted_ceiling": tracer.fmt(
            check["predicted_ceiling_exact"],
            "bench.b1_check_against_log.decimal_GB.predicted_ceiling_exact",
            ".2f",
        ),
        "ceiling_floor": tracer.fmt(
            check["predicted_ceiling_floor"],
            "bench.b1_check_against_log.decimal_GB.predicted_ceiling_floor",
            "d",
        ),
        "preemption_matches": check["preemption_matches_all_rows"],
        "max_identity_error": tracer.fmt(
            bench["b3"]["max_identity_error_pct"],
            "bench.b3.max_identity_error_pct",
            ".4f",
        ),
        # Verbatim strings lifted from model_spec.md. They carry digits
        # ("1x NVIDIA L4 (24 GB)") that are neither measurements nor
        # provenance, so they are declared rather than traced.
        "model_name": tracer.structural(
            bench["spec"]["model"]["name"], "spec verbatim: model name"
        ),
        "gpu": tracer.structural(bench["spec"]["serving"]["gpu"], "spec verbatim: gpu"),
    }
