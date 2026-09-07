"""The render namespace: results JSON -> template variables.

Kept apart from ``render.py`` so that assembling the namespace and
enforcing rule 3 are separate concerns. Everything numeric in here goes
through ``Tracer``, which is what makes the post-render check meaningful.

Assertions are not written here. Sentences that assert a conclusion, rank
a cause or recommend an action live in ``interpretation.py`` (per-finding)
and in the templates (the A3/A4/B/C arguments); this module supplies the
figures they cite, every one through ``Tracer``.
"""

from __future__ import annotations

from typing import Any

from audit.reporting import interpretation, tables
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

    The measured half is filled from ``ablation.json``; the claim,
    category and direction come from ``interpretation.findings``, which is
    where every asserting sentence in this repo lives. Confirmed and
    rejected findings render into separate sections from the same data.
    """
    ablation = results["ablation"]
    sweep = ablation["sweep"]["NFC"]
    deltas = ablation["deltas"]["NFC"]
    pivot = ablation["provenance"]["config"]["pivot_language"]
    authored = interpretation.findings(results, tracer)
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
                "category": authored[flag]["category"],
                "claim": authored[flag]["claim"],
                "direction": authored[flag]["direction"],
                "rejected": flag in interpretation.REJECTED,
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


def _partc(results: dict[str, Any], tracer: Tracer) -> dict[str, Any]:
    """Part C envelope figures. Arithmetic only; no path is ranked."""
    d = results["partc"]
    a, r, t, w, s = (
        d["assumptions"],
        d["reviewer"],
        d["training"],
        d["rewriter"],
        d["schedule"],
    )

    def f(value: float | int, key: str, spec: str = "d") -> str:
        return tracer.fmt(value, f"partc.{key}", spec)

    return {
        "gpu_count": f(a["gpu_count"], "assumptions.gpu_count"),
        "project_weeks": f(a["project_weeks"], "assumptions.project_weeks"),
        "reviewer_count": f(a["reviewer_count"], "assumptions.reviewer_count"),
        "reviewer_hours_per_week": f(
            a["reviewer_hours_per_week"], "assumptions.reviewer_hours_per_week"
        ),
        "review_launch_weeks": f(
            a["review_launch_weeks"], "assumptions.review_launch_weeks"
        ),
        "items_per_hour": f(
            a["reviewer_items_per_hour"], "assumptions.reviewer_items_per_hour"
        ),
        "sft_pairs": f(a["sft_pairs"], "assumptions.sft_pairs"),
        "sentences_per_response": f(
            a["sentences_per_response"], "assumptions.sentences_per_response"
        ),
        "epochs": f(a["epochs"], "assumptions.epochs"),
        "tps_low": f(
            a["lora_tokens_per_second_low"], "assumptions.lora_tokens_per_second_low"
        ),
        "tps_high": f(
            a["lora_tokens_per_second_high"], "assumptions.lora_tokens_per_second_high"
        ),
        "reviewer_hours": f(r["reviewer_hours"], "reviewer.reviewer_hours"),
        "review_items": f(r["items_at_stated_rate"], "reviewer.items_at_stated_rate"),
        "items_per_covered": f(
            r["items_per_covered_language"], "reviewer.items_per_covered_language"
        ),
        "items_per_language_even": f(
            r["items_per_language_if_split_evenly"],
            "reviewer.items_per_language_if_split_evenly",
        ),
        "covered_languages": f(r["covered_languages"], "reviewer.covered_languages"),
        "target_languages": f(r["target_languages"], "reviewer.target_languages"),
        "uncovered_count": f(
            len(r["uncovered_languages"]), "reviewer.uncovered_languages|count"
        ),
        "uncovered": r["uncovered_languages"],
        "tokens_per_response": f(
            t["mean_tokens_per_response"], "training.mean_tokens_per_response", ".1f"
        ),
        "training_tokens": f(t["training_tokens"], "training.training_tokens", ".0f"),
        "gpu_hours_high": f(
            t["gpu_hours_at_high_throughput"],
            "training.gpu_hours_at_high_throughput",
            ".2f",
        ),
        "gpu_hours_low": f(
            t["gpu_hours_at_low_throughput"],
            "training.gpu_hours_at_low_throughput",
            ".2f",
        ),
        "gpu_hours_available": f(
            t["gpu_hours_available"], "training.gpu_hours_available"
        ),
        "utilisation": f(
            t["utilisation_at_low_throughput"],
            "training.utilisation_at_low_throughput",
            ".5f",
        ),
        "sensitivity": [
            (f(int(k), f"sensitivity.{k}|pairs"), f(v, f"sensitivity.{k}", ".2f"))
            for k, v in sorted(
                d["sensitivity_gpu_hours_by_pair_count"].items(),
                key=lambda kv: int(kv[0]),
            )
        ],
        "goodput": f(
            w["measured_output_tok_s"], "rewriter.measured_output_tok_s", ".2f"
        ),
        "goodput_halved": f(
            w["effective_output_tok_s_if_equal_cost"],
            "rewriter.effective_output_tok_s_if_equal_cost",
            ".2f",
        ),
        "holdout_per_language": f(
            a["holdout_per_language"], "assumptions.holdout_per_language"
        ),
        "holdout_total": f(
            a["holdout_per_language"] * r["covered_languages"], "reviewer.holdout_total"
        ),
        "target_win_pct": f(a["target_win_pct"], "assumptions.target_win_pct"),
        "target_rating": f(a["target_rating"], "assumptions.target_rating"),
        "rating_scale": f(a["rating_scale"], "assumptions.rating_scale"),
        "pilot_items": f(a["pilot_items"], "assumptions.pilot_items"),
        "kill_win_pct": f(a["kill_win_pct"], "assumptions.kill_win_pct"),
        "day_one_pairs": f(a["day_one_pairs"], "assumptions.day_one_pairs"),
        "day_one_reviewed": f(a["day_one_reviewed"], "assumptions.day_one_reviewed"),
        "utilisation_pct": f(
            t["utilisation_at_low_throughput"] * 100, "training.utilisation_pct", ".2f"
        ),
        "sensitivity_max_pairs": f(
            max(int(k) for k in d["sensitivity_gpu_hours_by_pair_count"]),
            "sensitivity|max_pairs",
        ),
        "sensitivity_max_hours": f(
            max(d["sensitivity_gpu_hours_by_pair_count"].values()),
            "sensitivity|max_hours",
            ".1f",
        ),
        "day_one": tracer.structural(s["day_one"], "partc schedule: day one"),
        "gpu_exhausted": tracer.structural(
            s["gpu_budget_exhausted"], "partc schedule: gpu budget end"
        ),
        "decision_deadline": tracer.structural(
            s["decision_deadline"], "partc schedule: decision deadline"
        ),
        "review_launch": tracer.structural(
            s["review_launch"], "partc schedule: review launch"
        ),
    }


def _argument_figures(results: dict[str, Any], tracer: Tracer) -> dict[str, str]:
    """The specific numbers the A3/A4/B2/B3/B4 arguments cite."""
    a, b, c = results["analysis"], results["bench"], results["corpus_stats"]
    words = {
        e["code"]: e["whitespace_words"]
        for e in c["by_normalisation"]["NFC"]["per_language"]
    }
    cmp16 = b["b3"]["counter_comparison_batch16"]["by_prompt_len"]
    ceil = b["b1"]["concurrency_ceiling_by_memory_unit"]["decimal_GB"]
    rows = {r["batch_size"]: r for r in b["b2"]["rows"]}

    def ratio(tok: str, den: str, lang: str) -> str:
        return tracer.fmt(
            a["grid"][tok]["ratio_to_pivot"][den][lang]["macro"],
            f"analysis.grid.{tok}.ratio_to_pivot.{den}.{lang}.macro",
        )

    def counter(prompt: str, field: str) -> str:
        return tracer.fmt(
            cmp16[prompt][field],
            f"bench.b3.counter_comparison_batch16.{prompt}.{field}",
            ".1f",
        )

    def row(batch: int, field: str, spec: str = "d") -> str:
        return tracer.fmt(rows[batch][field], f"bench.b2.rows.{batch}.{field}", spec)

    return {
        "kan_words": tracer.fmt(words["kan"], "corpus_stats.kan.whitespace_words", "d"),
        "eng_words": tracer.fmt(words["eng"], "corpus_stats.eng.whitespace_words", "d"),
        "kan_per_word": ratio("gpt2", "words", "kan"),
        "kan_per_sentence": ratio("gpt2", "sentences", "kan"),
        "hin_per_word": ratio("gpt2", "words", "hin"),
        "hin_per_grapheme": ratio("gpt2", "graphemes", "hin"),
        "hin_per_byte": ratio("gpt2", "utf8_bytes", "hin"),
        "hin_per_sentence": ratio("gpt2", "sentences", "hin"),
        "hin_muril": ratio("muril", "sentences", "hin"),
        "hin_xlmr": ratio("xlmr", "sentences", "hin"),
        "ben_muril": ratio("muril", "sentences", "ben"),
        "tam_gpt2": ratio("gpt2", "sentences", "tam"),
        "tam_muril": ratio("muril", "sentences", "tam"),
        "short_reported": counter("512", "reported_tok_s"),
        "short_output": counter("512", "output_tok_s"),
        "long_reported": counter("3584", "reported_tok_s"),
        "long_output": counter("3584", "output_tok_s"),
        "long_prompt_share": tracer.fmt(
            cmp16["3584"]["prompt_share_of_counted_tokens"] * 100,
            "bench.b3.counter_comparison_batch16.3584.prompt_share_of_counted_tokens",
            ".1f",
        ),
        "kv_capacity_tokens": tracer.fmt(
            ceil["kv_capacity_tokens"], "bench.b1...decimal_GB.kv_capacity_tokens", "d"
        ),
        "kv_bytes_per_token": tracer.fmt(
            ceil["kv_bytes_per_token"], "bench.b1...decimal_GB.kv_bytes_per_token", "d"
        ),
        "preempt32": row(32, "preempted_seqs"),
        "preempt48": row(48, "preempted_seqs"),
        "wall24": row(24, "wall_clock_s", ".2f"),
        "wall32": row(32, "wall_clock_s", ".2f"),
        "wall48": row(48, "wall_clock_s", ".2f"),
        "ttft24": row(24, "ttft_ms_p50", ".1f"),
        "ttft48": row(48, "ttft_ms_p50", ".1f"),
        "util24": row(24, "kv_cache_util", ".2f"),
        "util32": row(32, "kv_cache_util", ".2f"),
        "reported48": row(48, "reported_tok_s", ".1f"),
        "long_prompt_len": tracer.fmt(
            b["b2"]["long_prompt_len"], "bench.b2.long_prompt_len", "d"
        ),
        "context_length": tracer.fmt(
            ceil["context_length"], "bench.b1...decimal_GB.context_length", "d"
        ),
        "max_batch": tracer.fmt(max(rows), "bench.b2.rows|max_batch_size", "d"),
        "fp8_ceiling": tracer.fmt(
            b["b2"]["hypotheticals"]["kv_cache_fp8"]["ceiling_after"],
            "bench.b2.hypotheticals.kv_cache_fp8.ceiling_after",
            "d",
        ),
        "prefill_share": tracer.fmt(
            b["b3"]["prefill_share"]["non_decode_share"] * 100,
            "bench.b3.prefill_share.non_decode_share",
            ".1f",
        ),
        "goodput_wall": tracer.fmt(
            b["b3"]["goodput_derivations"][0]["value_tok_s"],
            "bench.b3.goodput_derivations.0.value_tok_s",
            ".2f",
        ),
        "goodput_itl": tracer.fmt(
            b["b3"]["goodput_derivations"][1]["value_tok_s"],
            "bench.b3.goodput_derivations.1.value_tok_s",
            ".2f",
        ),
    }


def build(results: dict[str, Any], tracer: Tracer) -> dict[str, Any]:
    """The full template namespace."""
    analysis = results["analysis"]
    bench = results["bench"]
    knee = bench["b2"]["knee"]
    check = bench["b1_check_against_log"]["decimal_GB"]
    return {
        "provenance": _provenance(results, tracer),
        "partc": _partc(results, tracer),
        "arg": _argument_figures(results, tracer),
        "f_zero": tracer.fmt(0, "derived.zero", "d"),
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
        "reported_numbers_table": tables.reported_numbers_table(
            results["ablation"], tracer
        ),
        "analysis_tables": {
            denominator: tables.analysis_table(analysis, tracer, denominator)
            for denominator in analysis["denominators"]
        },
        "headline": _headline(results, tracer),
        "findings": _findings(results, tracer),
        "kv_table": tables.kv_table(bench, tracer),
        "concurrency_table": tables.concurrency_table(bench, tracer),
        "goodput_table": tables.goodput_table(bench, tracer),
        "hypotheticals_table": tables.hypotheticals_table(bench, tracer),
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
