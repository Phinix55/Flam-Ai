"""``python -m audit`` -- one entrypoint, one subcommand per stage.

Thin by contract: this module parses arguments and dispatches. It contains
no analysis logic, no arithmetic and no file formats. Everything it can do
is reachable from ``make``, and everything ``make`` does is reachable from
here, so there is exactly one way to produce any artefact.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from audit import stages
from audit.config import AuditConfig

Handler = Callable[[AuditConfig, argparse.Namespace], object]

_STAGE_HELP: dict[str, str] = {
    "corpus": "NETWORK STAGE: fetch FLORES-200 + tokenizers into .cache/, checksummed",
    "prepare": "offline: validate alignment -> results/corpus_stats.json",
    "ablate": "offline: sweep the ablation flag grid -> results/ablation.json",
    "analyze": "offline: corrected multi-tokenizer analysis -> results/analysis.json",
    "bench": "offline: spec parse + KV math + log analysis -> results/bench.json",
    "render": "offline: results/*.json + templates -> deliverable/",
    "adversarial": "offline: run adversarial fixtures -> results/adversarial.json",
    "reproduce": "offline: prepare -> ablate -> analyze -> bench -> render",
}


def _handle_corpus(config: AuditConfig, _args: argparse.Namespace) -> object:
    return stages.run_corpus(config)


def _handle_prepare(config: AuditConfig, _args: argparse.Namespace) -> object:
    return stages.run_prepare(config)


def _handle_ablate(config: AuditConfig, _args: argparse.Namespace) -> object:
    return stages.run_ablate(config)


def _handle_analyze(config: AuditConfig, _args: argparse.Namespace) -> object:
    return stages.run_analyze(config)


def _handle_bench(config: AuditConfig, _args: argparse.Namespace) -> object:
    return stages.run_bench(config)


def _handle_render(config: AuditConfig, _args: argparse.Namespace) -> object:
    return stages.run_render(config)


def _handle_adversarial(config: AuditConfig, _args: argparse.Namespace) -> object:
    return stages.run_adversarial(config)


def _handle_reproduce(config: AuditConfig, args: argparse.Namespace) -> object:
    """Offline end-to-end rebuild. Excludes ``corpus`` (the network stage)
    but includes ``prepare``, so every artefact is regenerated from the
    cache alone."""
    return [
        _handle_prepare(config, args),
        _handle_ablate(config, args),
        _handle_analyze(config, args),
        _handle_bench(config, args),
        _handle_render(config, args),
    ]


HANDLERS: dict[str, Handler] = {
    "corpus": _handle_corpus,
    "prepare": _handle_prepare,
    "ablate": _handle_ablate,
    "analyze": _handle_analyze,
    "bench": _handle_bench,
    "render": _handle_render,
    "adversarial": _handle_adversarial,
    "reproduce": _handle_reproduce,
}


def build_parser() -> argparse.ArgumentParser:
    """Argparse tree. One subcommand per Makefile target."""
    parser = argparse.ArgumentParser(
        prog="python -m audit",
        description="Audit of the v0 tokenizer-fertility and serving-capacity report.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repo root override; defaults to the directory holding pyproject.toml",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in _STAGE_HELP.items():
        sub = subparsers.add_parser(name, help=help_text, description=help_text)
        if name == "ablate":
            sub.add_argument(
                "--flag",
                action="append",
                default=None,
                metavar="NAME",
                help="run only this flag against baseline (repeatable); "
                "default is the full sweep",
            )
    return parser


def _config_for(args: argparse.Namespace) -> AuditConfig:
    return AuditConfig() if args.root is None else AuditConfig(root=args.root.resolve())


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint. Returns a process exit code; never raises to the shell."""
    args = build_parser().parse_args(argv)
    try:
        HANDLERS[args.command](_config_for(args), args)
    except NotImplementedError as exc:
        print(f"audit {args.command}: not implemented yet ({exc}).", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"audit {args.command}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0
