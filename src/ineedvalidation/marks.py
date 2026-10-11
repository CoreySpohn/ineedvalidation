"""The decorators a test uses to declare its evidence.

Each decorator is a thin wrapper over a pytest marker with its arguments
validated at decoration time, so a bad evidence kind or a misspelled keyword
fails when the module is imported rather than being silently ignored at
collection.

The evidence kinds are named, not lettered. A reader of a marked test should
not need a key to tell a cross-code benchmark from a validation against
measured data, and a grep for ``validation`` should not also return every
test that merely converges.
"""

import math
import re
from datetime import date

import pytest

CODE_VERIFICATION = "code-verification"
"""Exact solutions, identities, property invariants, sign and seam anchors."""

SOLUTION_VERIFICATION = "solution-verification"
"""Convergence of a response quantity in an ordered discretization parameter."""

CROSS_CODE_BENCHMARK = "cross-code-benchmark"
"""Agreement with an independently developed code. Never validation."""

VALIDATION = "validation"
"""Comparison against measured data: a testbed, an instrument, a published table."""

UNCERTAINTY_QUANTIFICATION = "uncertainty-quantification"
"""Segregated aleatory and epistemic propagation; sensitivity analysis."""

EVIDENCE_KINDS = (
    CODE_VERIFICATION,
    SOLUTION_VERIFICATION,
    CROSS_CODE_BENCHMARK,
    VALIDATION,
    UNCERTAINTY_QUANTIFICATION,
)
"""Every kind of evidence a test may claim, in reading order.

Verification comes first and splits in two, then the benchmark that is often
mistaken for validation, then validation itself, then uncertainty. This is the
order the hierarchy renders in; it is not alphabetical and does not need to be.
"""

MARK_CASE = "vv_case"
MARK_SEAM = "vv_seam"
MARK_REGRESSION = "vv_regression"

BASES = (
    "floating-point",
    "exact-algebra",
    "monte-carlo",
    "coverage",
    "simulation-based-calibration",
    "mutation",
    "spike",
    "literature",
    "equivalence",
)
"""Ways a test establishes its acceptance criterion."""

ACCEPTANCE_KEYS = (
    "metric",
    "tolerance",
    "margin",
    "rule",
    "domain",
    "draws",
    "sigma",
    "reference_error",
    "registered",
)
"""Allowed keys describing a test's acceptance criterion."""


def _check_slug(name, value):
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string, got {value!r}")


def validate_case(
    slug,
    evidence,
    *,
    srq=None,
    reference_code=None,
    refined_parameter=None,
    referent=None,
    reference_model=None,
    alternative=None,
    basis=None,
    acceptance=None,
):
    """Validate a case declaration from a decorator or a path default.

    Args:
        slug: non-empty name of the physical case.
        evidence: one of :data:`EVIDENCE_KINDS`.
        srq: the system response quantity the test checks, if one.
        reference_code: independent code used for a cross-code benchmark.
        refined_parameter: discretization parameter for solution verification.
        referent: measured dataset used for validation.
        reference_model: reference computation for solution verification.
        alternative: alternative model for uncertainty quantification.
        basis: one of :data:`BASES`, describing how the criterion is established.
        acceptance: criterion metadata keyed by :data:`ACCEPTANCE_KEYS`.

    Raises:
        TypeError: if the case slug or acceptance values have invalid types.
        ValueError: if the evidence kind, basis or acceptance metadata is invalid,
            or a keyword belongs to another evidence kind.
    """
    _check_slug("case", slug)
    if evidence not in EVIDENCE_KINDS:
        raise ValueError(f"evidence must be one of {EVIDENCE_KINDS}, got {evidence!r}")
    for keyword, value, belongs_to in (
        ("reference_code", reference_code, CROSS_CODE_BENCHMARK),
        ("refined_parameter", refined_parameter, SOLUTION_VERIFICATION),
        ("referent", referent, VALIDATION),
        ("reference_model", reference_model, SOLUTION_VERIFICATION),
        ("alternative", alternative, UNCERTAINTY_QUANTIFICATION),
    ):
        if value is not None and evidence != belongs_to:
            raise ValueError(
                f"{keyword}= belongs to {belongs_to!r} evidence, not {evidence!r}"
            )
    if basis is not None and basis not in BASES:
        raise ValueError(f"basis must be one of {BASES}, got {basis!r}")
    if acceptance is None:
        return
    if not isinstance(acceptance, dict):
        raise TypeError("acceptance must be a dict")
    for key, value in acceptance.items():
        if key not in ACCEPTANCE_KEYS:
            raise ValueError(f"unknown acceptance key {key!r}")
        if key == "registered":
            if isinstance(value, date):
                raise ValueError(
                    "acceptance.registered must be a YYYY-MM-DD string; "
                    "quote the date in TOML"
                )
            if not isinstance(value, str) or not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
            ):
                raise ValueError("acceptance.registered must be a YYYY-MM-DD date")
            try:
                date.fromisoformat(value)
            except ValueError as error:
                raise ValueError(
                    "acceptance.registered must be a valid YYYY-MM-DD date"
                ) from error
            continue
        for item in value if isinstance(value, list) else [value]:
            if not isinstance(item, (str, bool, int, float)):
                raise TypeError(
                    f"acceptance.{key} must contain strings, booleans or finite numbers"
                )
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError(f"acceptance.{key} must contain only finite numbers")


def case(
    slug,
    evidence,
    *,
    srq=None,
    reference_code=None,
    refined_parameter=None,
    referent=None,
    reference_model=None,
    alternative=None,
    basis=None,
    acceptance=None,
):
    """Declare the physical case, evidence kind and response quantity of a test.

    Args:
        slug: plain name of the physical case the test exercises; a hierarchy
            node lists the slugs it owns.
        evidence: one of :data:`EVIDENCE_KINDS`.
        srq: the system response quantity the test checks, if one.
        reference_code: for a cross-code benchmark, the independently developed
            code compared against.
        refined_parameter: for solution verification, the ordered discretization
            parameter that was refined.
        referent: for validation, the measured dataset compared against.
        reference_model: for solution verification, a reference computation of
            the same governing probabilistic model and assumptions, with its
            own numerical error quantified.
        alternative: for uncertainty quantification, the alternative model
            compared with the baseline in a sensitivity analysis.
        basis: one of :data:`BASES`, describing how the criterion is established.
        acceptance: criterion metadata keyed by :data:`ACCEPTANCE_KEYS`.

    Returns:
        A pytest mark decorator.

    Raises:
        TypeError: if the case slug or acceptance values have invalid types.
        ValueError: if the evidence kind, basis or acceptance metadata is invalid,
            or a keyword is used with an evidence kind it does not belong to.
    """
    keywords = dict(
        srq=srq,
        reference_code=reference_code,
        refined_parameter=refined_parameter,
        referent=referent,
        reference_model=reference_model,
        alternative=alternative,
        basis=basis,
        acceptance=acceptance,
    )
    validate_case(slug, evidence, **keywords)
    return getattr(pytest.mark, MARK_CASE)(slug, evidence, **keywords)


def seam(producer, consumer, *, case=None):
    """Declare an absolute-scale anchor test across a producer/consumer interface.

    Args:
        producer: name of the library that emits the quantity.
        consumer: name of the library that consumes it.
        case: the physical case the anchor belongs to, if one.

    Returns:
        A pytest mark decorator.
    """
    _check_slug("producer", producer)
    _check_slug("consumer", consumer)
    return getattr(pytest.mark, MARK_SEAM)(producer, consumer, case=case)


regression = getattr(pytest.mark, MARK_REGRESSION)
"""Mark a test as a frozen or golden regression reference.

Regression tests claim no evidence kind: they catch unintended change, they do
not establish correctness.
"""
