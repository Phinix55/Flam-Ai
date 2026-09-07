"""Rule 3 enforcement (Phase 7).

The two validators are only worth having if they can fail. Each is tested
against a document that must be rejected as well as one that must pass.
"""

from __future__ import annotations

import pytest

from audit.reporting.render import (
    OUTPUTS,
    TemplateDigitError,
    UntracedNumeralError,
    data_numerals,
    template_identifiers,
    validate_no_untraced_numerals,
    validate_template_has_no_digits,
)
from audit.reporting.tables import Tracer, markdown_table


def _texts(line: str) -> list[str]:
    return [m.group() for m in data_numerals(line)]


# ------------------------------------------------------- numeral extraction


def test_identifier_digits_are_not_treated_as_figures():
    assert _texts("B1 and gpt2 and L4 and FLORES-200 and cl100k") == []


def test_signed_and_decimal_figures_are_in_scope():
    assert _texts("delta was -0.503 % and +1.991 %") == ["0.503", "1.991"]


def test_bracketed_ci_values_are_in_scope():
    assert _texts("6.32 [6.26, 6.39]") == ["6.32", "6.26", "6.39"]


# ------------------------------------------------------- template validator


def test_every_shipped_template_is_digit_free(config):
    for name in OUTPUTS:
        source = (config.templates_dir / name).read_text(encoding="utf-8")
        validate_template_has_no_digits(source, name)


def test_a_digit_in_a_template_is_rejected():
    with pytest.raises(TemplateDigitError, match="numeric literals"):
        validate_template_has_no_digits("Hindi is 5.89x English.\n", "t.j2")


def test_a_digit_inside_a_jinja_comment_is_allowed():
    validate_template_has_no_digits("{# was 5.89 before #}\n{{ x }}\n", "t.j2")


def test_template_identifiers_are_reported(config):
    source = (config.templates_dir / "partB_answers.md.j2").read_text(encoding="utf-8")
    assert {"B1", "B2", "B3", "B4"} <= template_identifiers(source)


# ------------------------------------------------------- numeral validator


def test_untraced_numeral_fails_the_build():
    tracer = Tracer()
    with pytest.raises(UntracedNumeralError, match="not traced to any results key"):
        validate_no_untraced_numerals("Hindi is 5.89x English.", tracer, "d.md")


def test_error_names_every_offender_with_its_line():
    tracer = Tracer()
    with pytest.raises(UntracedNumeralError) as excinfo:
        validate_no_untraced_numerals("a 1.5\nb 2.5\n", tracer, "d.md")
    message = str(excinfo.value)
    assert "line 1" in message and "line 2" in message
    assert "'1.5'" in message and "'2.5'" in message


def test_a_traced_numeral_passes_and_keeps_its_key():
    tracer = Tracer()
    text = tracer.fmt(5.8901, "ablation.headline_ratios.NFC.baseline.hin")
    validate_no_untraced_numerals(f"Hindi is {text}x English.", tracer, "d.md")
    assert tracer.key_for("5.8901") == "ablation.headline_ratios.NFC.baseline.hin"


def test_signed_format_registers_the_bare_numeral():
    """`+.3f` emits '+0.023'; the validator sees '0.023'. Both sides must
    agree on what a numeral is or every signed delta fails."""
    tracer = Tracer()
    assert tracer.fmt(0.0234, "k", "+.3f") == "+0.023"
    validate_no_untraced_numerals("delta +0.023 %", tracer, "d.md")


def test_structural_exemptions_are_declared_with_a_reason():
    tracer = Tracer()
    tracer.structural("01", "finding ordinal")
    exemptions = tracer.structural_exemptions()
    assert [e.text for e in exemptions] == ["01"]
    assert exemptions[0].key == "finding ordinal"


# ------------------------------------------------------------------ tables


def test_ragged_table_rows_raise_rather_than_padding():
    with pytest.raises(ValueError, match="Refusing to pad"):
        markdown_table(["a", "b"], [["1"]])


# --------------------------------------------------------- rendered output


def test_rendered_deliverables_exist_and_carry_reserved_interpretation(config):
    for relative in OUTPUTS.values():
        path = config.deliverable_dir / relative
        if not path.is_file():
            pytest.skip("deliverables not rendered yet; run `make render`")
        assert path.read_text(encoding="utf-8").strip()


def test_authored_interpretation_is_disclosed_in_ai_usage(config):
    """CLAUDE.md rule 6 reserves interpretive sentences for the human author.

    That reservation was overridden on the author's instruction, so the
    invariant this suite can still enforce is the honest one: if the
    deliverables contain authored argument rather than markers, AI_USAGE.md
    must say so. A submission that quietly claimed the reasoning would be
    the one thing this assignment fails outright for.
    """
    memo = config.deliverable_dir / "partA/MEMO.md"
    if not memo.is_file():
        pytest.skip("deliverables not rendered yet; run `make render`")
    rendered = memo.read_text(encoding="utf-8")
    disclosure = (config.root / "AI_USAGE.md").read_text(encoding="utf-8")
    if "TODO(pratik): interpretation" not in rendered:
        assert "interpretation" in disclosure.lower()
        assert "model" in disclosure.lower()


def test_every_finding_carries_a_category_and_a_direction(config):
    """An evidence block without a stated direction is an unverified claim
    in the shape of a verified one."""
    findings = config.deliverable_dir / "partA/FINDINGS.md"
    if not findings.is_file():
        pytest.skip("deliverables not rendered yet; run `make render`")
    text = findings.read_text(encoding="utf-8")
    assert text.count("**Category:**") == text.count("**Command:**")
    assert "TODO(pratik)" not in text
    assert "Claims investigated and rejected" in text
    for category in ("code bug", "conceptual", "rejected"):
        assert category in text


def test_hyphenated_product_names_are_not_treated_as_figures():
    """`A100-80GB` broke a two-character rule: the char before `80` is a
    hyphen and the one before that is a digit."""
    assert _texts("A100-80GB and FLORES-200 and cl100k_base") == []


def test_a_leading_digit_is_treated_as_data_not_a_name():
    """The rule looks backwards only, so `1x` reads as a figure. That is
    the safe direction: an unrecognised numeral has to be declared rather
    than silently exempted, and `1x NVIDIA L4 (24 GB)` is in fact declared
    structural as verbatim spec text."""
    assert _texts("1x A100") == ["1"]


def test_a_negative_value_is_still_a_figure():
    assert _texts("delta -0.503 percent") == ["0.503"]


def test_dict_method_shadowing_would_be_caught():
    """`{{ partc.items }}` resolves to dict.items in Jinja and renders a
    method repr containing an address. The validator is what catches it."""
    tracer = Tracer()
    with pytest.raises(UntracedNumeralError):
        validate_no_untraced_numerals(
            "| items | <built-in method items of dict object at 0x7f00> |",
            tracer,
            "d.md",
        )
