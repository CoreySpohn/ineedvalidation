"""Decorators validate at decoration time; the plugin registers the markers."""

import pytest

import ineedvalidation as vv

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
    }


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
