"""Decorators validate at decoration time; the plugin registers the markers."""

import pytest

import ineedvalidation as vv
from ineedvalidation.marks import BASES

pytest_plugins = ["pytester"]


def test_case_rejects_an_unknown_evidence_kind():
    with pytest.raises(ValueError):
        vv.case("some-case", "not-a-kind")


def test_case_rejects_empty_slug():
    with pytest.raises(TypeError):
        vv.case("", "code-verification")


def test_seam_needs_two_names():
    with pytest.raises(TypeError):
        vv.seam("producer", "")


def test_case_mark_carries_arguments():
    mark = vv.case(
        "some-case", "cross-code-benchmark", srq="contrast", reference_code="other-code"
    ).mark
    assert mark.name == "vv_case"
    assert mark.args == ("some-case", "cross-code-benchmark")
    assert mark.kwargs == {
        "srq": "contrast",
        "reference_code": "other-code",
        "refined_parameter": None,
        "referent": None,
        "reference_model": None,
        "alternative": None,
        "basis": None,
        "acceptance": None,
    }


@pytest.mark.parametrize(
    ("keyword", "owner", "kind"),
    [
        (keyword, owner, kind)
        for keyword, owner in (
            ("reference_model", "solution-verification"),
            ("alternative", "uncertainty-quantification"),
        )
        for kind in vv.EVIDENCE_KINDS
        if kind != owner
    ],
)
def test_kind_keyword_rejects_each_other_kind(keyword, owner, kind):
    with pytest.raises(ValueError) as error:
        vv.case("some-case", kind, **{keyword: "comparison model"})
    assert keyword in str(error.value)
    assert owner in str(error.value)


def test_markers_registered_under_strict_markers(pytester):
    pytester.makepyfile(
        """
        import ineedvalidation as vv

        @vv.case("some-case", "code-verification", srq="flux")
        def test_one():
            pass

        @vv.seam("producer", "consumer")
        def test_two():
            pass

        @vv.regression
        def test_three():
            pass
        """
    )
    result = pytester.runpytest("--strict-markers", "-q")
    result.assert_outcomes(passed=3)


EXPECTED_BASES = (
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


def test_bases_vocabulary():
    assert BASES == EXPECTED_BASES


@pytest.mark.parametrize("basis", EXPECTED_BASES)
def test_case_accepts_each_basis(basis):
    mark = vv.case("some-case", "code-verification", basis=basis).mark
    assert mark.kwargs["basis"] == basis


def test_unknown_basis_lists_every_allowed_value():
    with pytest.raises(ValueError) as error:
        vv.case("some-case", "code-verification", basis="not-a-basis")
    assert "not-a-basis" in str(error.value)
    for basis in EXPECTED_BASES:
        assert basis in str(error.value)


@pytest.mark.parametrize(
    ("acceptance", "exception", "message"),
    [
        ({"typo": 1}, ValueError, "typo"),
        ({"tolerance": float("nan")}, ValueError, "finite"),
        ({"tolerance": float("inf")}, ValueError, "finite"),
        ({"tolerance": -float("inf")}, ValueError, "finite"),
        ({"margin": [1, float("nan")]}, ValueError, "finite"),
        ({"margin": [1, float("inf")]}, ValueError, "finite"),
        ({"domain": {"nested": 1}}, TypeError, "acceptance.domain"),
        ({"domain": ["first", {"nested": 1}]}, TypeError, "acceptance.domain"),
        ({"domain": [["nested"]]}, TypeError, "acceptance.domain"),
        ({"metric": None}, TypeError, "acceptance.metric"),
        ({"registered": "2026-13-01"}, ValueError, "YYYY-MM-DD"),
        ({"registered": "2026-10-01T00:00"}, ValueError, "YYYY-MM-DD"),
        ({"registered": "2026-02-29"}, ValueError, "YYYY-MM-DD"),
        ({"registered": "2026-1-01"}, ValueError, "YYYY-MM-DD"),
        ({"registered": ["2026-10-01"]}, ValueError, "YYYY-MM-DD"),
        ([], TypeError, "acceptance must be a dict"),
    ],
)
def test_case_rejects_invalid_acceptance(acceptance, exception, message):
    with pytest.raises(exception, match=message):
        vv.case("some-case", "code-verification", acceptance=acceptance)


@pytest.mark.parametrize("acceptance", [{}, {"domain": []}])
def test_case_preserves_empty_acceptance_values(acceptance):
    mark = vv.case("some-case", "code-verification", acceptance=acceptance).mark
    assert mark.kwargs["acceptance"] == acceptance


def test_public_metadata_vocabularies_support_star_import():
    namespace = {}
    exec("from ineedvalidation import *", namespace)
    assert namespace["BASES"] == EXPECTED_BASES
    assert namespace["ACCEPTANCE_KEYS"] == (
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
    mark = namespace["case"](
        "some-case",
        "code-verification",
        basis=namespace["BASES"][0],
        acceptance={namespace["ACCEPTANCE_KEYS"][0]: "absolute error"},
    ).mark
    assert mark.kwargs["basis"] == "floating-point"
    assert mark.kwargs["acceptance"] == {"metric": "absolute error"}
