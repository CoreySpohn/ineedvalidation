"""The decorators a test uses to declare its evidence.

Each decorator is a thin wrapper over a pytest marker with its arguments
validated at decoration time, so a bad tier or a misspelled keyword fails when
the module is imported rather than being silently ignored at collection.
"""

import pytest

TIERS = ("A", "B", "C", "D")
"""Evidence tiers a test can claim.

A: code verification against analytic forms, identities and invariants.
B: cross-code benchmark against an independently developed code.
C: solution verification, convergence in an ordered discretization parameter.
D: validation against measured data.
"""

MARK_CASE = "inv_case"
MARK_SEAM = "inv_seam"
MARK_REGRESSION = "inv_regression"


def _check_slug(name, value):
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string, got {value!r}")


def case(slug, tier, *, srq=None, ref=None):
    """Declare the physical case, evidence tier and response quantity of a test.

    Args:
        slug: plain name of the physical case the test exercises; a hierarchy
            node lists the slugs it owns.
        tier: one of :data:`TIERS`.
        srq: the system response quantity the test checks, if one.
        ref: meaning depends on the tier: the reference code for tier B, the
            ordered discretization parameter for tier C, the referent dataset
            for tier D.

    Returns:
        A pytest mark decorator.
    """
    _check_slug("case", slug)
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}, got {tier!r}")
    return getattr(pytest.mark, MARK_CASE)(slug, tier, srq=srq, ref=ref)


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

Regression tests are excluded from every evidence tier: they catch unintended
change, they do not establish correctness.
"""
