"""Deterministic matplotlib figures.

Determinism requirements: the non-interactive Agg backend, no timestamp
or version metadata in the output, fixed figure size and DPI, and data
read in sorted key order. Two runs must produce byte-identical PNGs,
because a figure that changes without its inputs changing is not
evidence. ``tests/test_figures.py`` asserts the byte-identity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
from matplotlib.figure import Figure

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

FIGSIZE = (10.0, 5.5)
DPI = 140
SAVE_KWARGS: dict[str, Any] = {
    "dpi": DPI,
    "bbox_inches": "tight",
    # Suppress the "Software: Matplotlib vX.Y" PNG tag. It embeds the
    # library version, so without this a dependency bump would silently
    # change every figure's bytes while the data stayed identical.
    "metadata": {"Software": None},
}


def configure_matplotlib() -> None:
    """Force the Agg backend and pin every style knob that affects bytes."""
    matplotlib.use("Agg")
    plt.rcParams.update(
        {
            "figure.figsize": FIGSIZE,
            "figure.dpi": DPI,
            "savefig.dpi": DPI,
            "font.family": "DejaVu Sans",
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "audit",
        }
    )


def _save(fig: Figure, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, **SAVE_KWARGS)
    plt.close(fig)
    return out_path


def fertility_by_denominator(analysis: dict[str, Any], out_path: Path) -> Path:
    """Ratio to the pivot language, one panel per denominator.

    One panel each rather than one combined axis: the four denominators
    span very different magnitudes, so a shared y-axis would compress
    three of them into the baseline and hide exactly the disagreement the
    figure exists to show.
    """
    configure_matplotlib()
    denominators = analysis["denominators"]
    tokenizer = analysis["headline_tokenizer"]
    ratios = analysis["grid"][tokenizer]["ratio_to_pivot"]
    languages = [lang for lang in analysis["languages"] if lang != analysis["pivot"]]

    fig, axes = plt.subplots(
        1, len(denominators), figsize=(4.0 * len(denominators), 4.4)
    )
    for axis, denominator in zip(axes, denominators, strict=True):
        values = [ratios[denominator][lang]["macro"] for lang in languages]
        lows = [ratios[denominator][lang]["macro_ci_low"] for lang in languages]
        highs = [ratios[denominator][lang]["macro_ci_high"] for lang in languages]
        errors = [
            [v - low for v, low in zip(values, lows, strict=True)],
            [high - v for v, high in zip(values, highs, strict=True)],
        ]
        axis.bar(languages, values, yerr=errors, capsize=3, color="#4C72B0")
        axis.axhline(1.0, color="#C44E52", linewidth=1, linestyle="--")
        axis.set_title(f"per {denominator}")
        axis.set_ylabel(
            f"x {analysis['pivot']}" if denominator == denominators[0] else ""
        )
    fig.suptitle(
        f"Tokens per unit, relative to {analysis['pivot']} - {tokenizer} "
        f"(macro, 95% paired-bootstrap CI, n={analysis['corpus']['n_records']})"
    )
    fig.tight_layout()
    return _save(fig, out_path)


def tokenizer_comparison(analysis: dict[str, Any], out_path: Path) -> Path:
    """Ratio to pivot per tokenizer, under the parallel-sentence unit.

    Holds the denominator fixed and varies only the tokenizer, which is
    the comparison the single-tokenizer evidence in the v0 report cannot
    make.
    """
    configure_matplotlib()
    languages = [lang for lang in analysis["languages"] if lang != analysis["pivot"]]
    fig, axis = plt.subplots(figsize=FIGSIZE)
    width = 0.8 / len(analysis["tokenizers"])
    for offset, (key, meta) in enumerate(sorted(analysis["tokenizers"].items())):
        ratios = analysis["grid"][key]["ratio_to_pivot"]["sentences"]
        positions = [i + offset * width for i in range(len(languages))]
        axis.bar(
            positions,
            [ratios[lang]["macro"] for lang in languages],
            width=width,
            label=f"{key} ({meta['family']}, vocab {meta['vocab_size']:,})",
        )
    axis.set_xticks([i + 0.4 - width / 2 for i in range(len(languages))])
    axis.set_xticklabels(languages)
    axis.axhline(1.0, color="#C44E52", linewidth=1, linestyle="--")
    axis.set_ylabel(f"tokens per parallel sentence, x {analysis['pivot']}")
    axis.set_title("Same corpus, same denominator, varying only the tokenizer")
    axis.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out_path)


def ablation_deltas(ablation: dict[str, Any], out_path: Path) -> Path:
    """Per-flag relative delta against baseline, by language."""
    configure_matplotlib()
    deltas = ablation["deltas"]["NFC"]
    languages = sorted(deltas[next(iter(deltas))])
    arms = sorted(deltas)
    fig, axis = plt.subplots(figsize=FIGSIZE)
    width = 0.8 / len(arms)
    for offset, arm in enumerate(arms):
        positions = [i + offset * width for i in range(len(languages))]
        axis.bar(
            positions,
            [deltas[arm][lang]["fertility_rel_pct"] for lang in languages],
            width=width,
            label=arm,
        )
    axis.set_xticks([i + 0.4 - width / 2 for i in range(len(languages))])
    axis.set_xticklabels(languages)
    axis.axhline(0.0, color="#333333", linewidth=1)
    axis.set_ylabel("relative change in tokens/word vs baseline (%)")
    axis.set_title("Ablation: single-flag deltas, NFC corpus, gpt2")
    axis.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    return _save(fig, out_path)


def throughput_curve(bench: dict[str, Any], out_path: Path) -> Path:
    """Throughput vs batch size for the long-prompt sweep.

    Both counters are drawn on one axis -- the harness's ``reported_tok_s``
    and output-tokens-per-second -- because the point of the figure is
    that they are different quantities on the same rows. The predicted
    concurrency ceiling and the located knee are marked so their
    coincidence, or absence of it, is visible rather than asserted.
    """
    configure_matplotlib()
    rows = sorted(bench["b2"]["rows"], key=lambda r: r["batch_size"])
    batches = [r["batch_size"] for r in rows]
    reported = [r["reported_tok_s"] for r in rows]
    output_only = [r["num_requests"] * r["gen_len"] / r["wall_clock_s"] for r in rows]
    ceiling = bench["b1"]["concurrency_ceiling_by_memory_unit"]["decimal_GB"]

    fig, axis = plt.subplots(figsize=FIGSIZE)
    axis.plot(batches, reported, marker="o", label="reported_tok_s (harness counter)")
    axis.plot(batches, output_only, marker="s", label="output tokens / wall clock")
    axis.axvline(
        bench["b2"]["knee"]["knee_batch_size"],
        color="#C44E52",
        linestyle="--",
        linewidth=1,
        label=f"located knee (batch {bench['b2']['knee']['knee_batch_size']})",
    )
    axis.axvline(
        ceiling["exact_sequences"],
        color="#55A868",
        linestyle=":",
        linewidth=1.5,
        label=f"predicted KV ceiling ({ceiling['exact_sequences']:.2f} seqs)",
    )
    for row, value in zip(rows, reported, strict=True):
        if row["preempted_seqs"]:
            axis.annotate(
                f"{row['preempted_seqs']} preempted",
                (row["batch_size"], value),
                textcoords="offset points",
                xytext=(0, 10),
                fontsize=8,
                ha="center",
            )
    axis.set_xlabel("batch size")
    axis.set_ylabel("tokens / s")
    axis.set_title(
        f"Long-prompt sweep (prompt {bench['b2']['long_prompt_len']}): "
        "two counters on the same rows"
    )
    axis.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out_path)
