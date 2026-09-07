"""Jinja2 rendering: templates + ``results/*.json`` -> ``deliverable/``.

CLAUDE.md rule 3: no number is ever typed into prose. The rule is enforced
by two checks that together close the loop:

1. **Templates contain no digits.** Verified before rendering. A template
   that cannot express a digit cannot emit an untraceable one.
2. **Every numeral in the output traces to a results key.** Verified after
   rendering, against the ``Tracer`` that formatted them. The build fails
   listing any that do not.

Check 1 is what makes check 2 airtight: with no digits in the template,
every numeral in the output must have arrived through ``Tracer.fmt``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from audit.config import AuditConfig
from audit.reporting.tables import Tracer

NUMERAL = re.compile(r"\d+(?:\.\d+)?")
IDENTIFIER_WITH_DIGIT = re.compile(r"[A-Za-z_][A-Za-z_-]*\d[\w-]*")


def _is_identifier_digit(line: str, start: int) -> bool:
    """True when a numeral is part of a name rather than a figure.

    ``B1``, ``gpt2``, ``L4``, ``FLORES-200``, ``cl100k`` and ``A100-80GB``
    are proper nouns; the digits in them carry no measurement and cannot
    trace to a results key because they are not data.

    Decided by walking back over the whole ``[alnum-]`` token and asking
    whether it *starts* with a letter. Checking only the preceding
    character is not enough: in ``A100-80GB`` the character before ``80``
    is a hyphen and the one before that is a digit, so a two-character
    rule reads it as data. Walking the token also keeps ``-0.503`` in
    scope, because there the run stops at a space and the token begins
    with the sign.
    """
    index = start
    while index > 0 and (line[index - 1].isalnum() or line[index - 1] in "-_"):
        index -= 1
    return index < start and line[index].isalpha()


def data_numerals(line: str) -> list[re.Match[str]]:
    """Every numeral in ``line`` that is a figure rather than a name."""
    return [
        m for m in NUMERAL.finditer(line) if not _is_identifier_digit(line, m.start())
    ]


OUTPUTS: dict[str, str] = {
    "partA_corpus.md.j2": "partA/CORPUS.md",
    "partA_findings.md.j2": "partA/FINDINGS.md",
    "partA_analysis.md.j2": "partA/ANALYSIS.md",
    "partA_memo.md.j2": "partA/MEMO.md",
    "partB_answers.md.j2": "partB/ANSWERS.md",
    "partC_memo.md.j2": "partC/memo.md",
}


class UntracedNumeralError(ValueError):
    """Raised when a rendered deliverable holds a number no results key
    accounts for. Failing the build is the point: an untraceable number in
    a deliverable is indistinguishable from a fabricated one."""


class TemplateDigitError(ValueError):
    """Raised when a template contains a numeric literal."""


def load_results(config: AuditConfig) -> dict[str, Any]:
    """Load every ``results/*.json`` into one namespace keyed by stem."""
    paths = sorted(config.results_dir.glob("*.json"))
    if not paths:
        msg = (
            f"No results artefacts in {config.results_dir}. Rendering a "
            "deliverable with no measurements behind it is exactly what rule 3 "
            "forbids. Run `make ablate analyze bench` first."
        )
        raise FileNotFoundError(msg)
    return {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in paths}


def validate_template_has_no_digits(template_text: str, name: str) -> None:
    """Assert a template contains no numeric literal outside placeholders.

    Jinja comment blocks are stripped first, so a comment may cite a
    figure while the emitted template body still cannot.
    """
    body = re.sub(r"\{#.*?#\}", "", template_text, flags=re.DOTALL)
    offenders = [
        f"line {index}: {match.group()!r} in {line.strip()[:70]!r}"
        for index, line in enumerate(body.splitlines(), 1)
        for match in data_numerals(line)
    ]
    if offenders:
        msg = (
            f"Template {name} contains numeric literals, which rule 3 forbids: "
            + "; ".join(offenders)
            + ". Emit a placeholder and populate it from a results key."
        )
        raise TemplateDigitError(msg)


def template_identifiers(template_text: str) -> set[str]:
    """Digit-bearing names a template is allowed to contain, for reporting.

    Surfaced rather than silently permitted: if this set ever grows a
    member that is actually a figure, it should be visible in the build.
    """
    body = re.sub(r"\{#.*?#\}", "", template_text, flags=re.DOTALL)
    return set(IDENTIFIER_WITH_DIGIT.findall(body))


def validate_no_untraced_numerals(rendered: str, tracer: Tracer, name: str) -> None:
    """Assert every numeral in a rendered document traces to a results key.

    Raises ``UntracedNumeralError`` listing each offender with its line, so
    the failure is actionable rather than a bare assertion.
    """
    allowed = tracer.texts()
    offenders = [
        f"line {index}: {match.group()!r} in {line.strip()[:70]!r}"
        for index, line in enumerate(rendered.splitlines(), 1)
        for match in data_numerals(line)
        if match.group() not in allowed
    ]
    if offenders:
        msg = (
            f"{name} contains {len(offenders)} numeral(s) not traced to any "
            f"results key: " + "; ".join(offenders) + ". Every figure in a "
            "deliverable must come from results/*.json via Tracer.fmt."
        )
        raise UntracedNumeralError(msg)


def _environment(config: AuditConfig) -> Environment:
    """StrictUndefined so a missing key fails loudly instead of rendering
    an empty cell that reads like a measured zero."""
    return Environment(
        loader=FileSystemLoader(str(config.templates_dir)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def build_context(results: dict[str, Any], tracer: Tracer) -> dict[str, Any]:
    """Assemble the render namespace. Every numeral passes through ``tracer``."""
    from audit.reporting import context

    return context.build(results, tracer)


def render_all(config: AuditConfig) -> tuple[Path, ...]:
    """Render every template into ``deliverable/``. Returns written paths."""
    results = load_results(config)
    environment = _environment(config)
    tracer = Tracer()
    written: list[Path] = []
    for template_name, relative in OUTPUTS.items():
        source = (config.templates_dir / template_name).read_text(encoding="utf-8")
        validate_template_has_no_digits(source, template_name)
        rendered = environment.get_template(template_name).render(
            **build_context(results, tracer)
        )
        validate_no_untraced_numerals(rendered, tracer, relative)
        path = config.deliverable_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        written.append(path)
    return tuple(written)
