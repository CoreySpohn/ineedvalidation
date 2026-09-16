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


def _check_slug(name, value):
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string, got {value!r}")


def case(
    slug,
    evidence,
    *,
    srq=None,
    reference_code=None,
    refined_parameter=None,
    referent=None,
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

    Returns:
        A pytest mark decorator.

    Raises:
        ValueError: if the evidence kind is unknown, or if a keyword is used
            with an evidence kind it does not belong to.
    """
    _check_slug("case", slug)
    if evidence not in EVIDENCE_KINDS:
        raise ValueError(f"evidence must be one of {EVIDENCE_KINDS}, got {evidence!r}")
    for keyword, value, belongs_to in (
        ("reference_code", reference_code, CROSS_CODE_BENCHMARK),
        ("refined_parameter", refined_parameter, SOLUTION_VERIFICATION),
        ("referent", referent, VALIDATION),
    ):
        if value is not None and evidence != belongs_to:
            raise ValueError(
                f"{keyword}= belongs to {belongs_to!r} evidence, not {evidence!r}"
            )
    return getattr(pytest.mark, MARK_CASE)(
        slug,
        evidence,
        srq=srq,
        reference_code=reference_code,
        refined_parameter=refined_parameter,
        referent=referent,
    )


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
