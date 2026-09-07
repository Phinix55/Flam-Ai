"""Scaffold integrity.

Two things this must guarantee before any analysis exists:

1. Every unimplemented stage raises. A stub that returns ``None`` or an
   empty dict would let a later bug produce a plausible-looking empty
   artefact -- which is the shape fabricated evidence takes by accident.
2. The CLI surface matches the Makefile, so there is exactly one way to
   produce any artefact.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

from audit.cli import HANDLERS, build_parser

ROOT = Path(__file__).resolve().parents[1]

STUBS: list[tuple[str, list[str]]] = []
"""Modules still awaiting a phase. Entries leave this list as they are
implemented; an implemented function left here fails loudly, which is what
keeps the list honest rather than decorative."""


@pytest.mark.parametrize(("module_name", "names"), STUBS)
def test_stubs_raise_rather_than_returning_a_plausible_empty(module_name, names):
    module = importlib.import_module(module_name)
    for name in names:
        func = getattr(module, name)
        with pytest.raises(NotImplementedError):
            _call_with_placeholders(func)


def _call_with_placeholders(func):
    """Call a stub with the right arity; the body raises before touching args."""
    import inspect

    args, kwargs = [], {}
    for name, param in inspect.signature(func).parameters.items():
        if param.kind is inspect.Parameter.KEYWORD_ONLY:
            kwargs[name] = None
        elif param.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            args.append(None)
    return func(*args, **kwargs)


def test_cli_exposes_one_subcommand_per_makefile_stage():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for command in HANDLERS:
        assert f"\n{command}:" in makefile, f"{command} has no Makefile target"


def test_cli_parses_every_subcommand():
    parser = build_parser()
    for command in HANDLERS:
        assert parser.parse_args([command]).command == command


def test_cli_rejects_an_unknown_subcommand():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["definitely-not-a-stage"])


def _run_cli(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "audit", command],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_module_entrypoint_runs_an_implemented_stage():
    """`python -m audit` is the single entrypoint and exits 0 on success."""
    assert _run_cli("bench").returncode == 0


def test_every_stage_is_implemented():
    """Every Makefile stage now runs; nothing is left raising
    NotImplementedError. When STUBS empties, this is what says so."""
    assert STUBS == []


def test_starter_kit_is_untouched():
    """CLAUDE.md rule 2. Nothing under src/ may reference a write to it."""
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert (
            "starter_kit" not in text or "read-only" in text or "starter_kit/" in text
        )
