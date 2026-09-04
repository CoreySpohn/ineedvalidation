"""Decorators validate at decoration time; the plugin registers the markers."""

import pytest

import ineedvalidation as inv

pytest_plugins = ["pytester"]


def test_case_rejects_bad_tier():
    with pytest.raises(ValueError):
        inv.case("some-case", "E")


def test_case_rejects_empty_slug():
    with pytest.raises(TypeError):
        inv.case("", "A")


def test_seam_needs_two_names():
    with pytest.raises(TypeError):
        inv.seam("producer", "")


def test_case_mark_carries_arguments():
    mark = inv.case("some-case", "B", srq="contrast", ref="other-code").mark
    assert mark.name == "inv_case"
    assert mark.args == ("some-case", "B")
    assert mark.kwargs == {"srq": "contrast", "ref": "other-code"}


def test_markers_registered_under_strict_markers(pytester):
    pytester.makepyfile(
        """
        import ineedvalidation as inv

        @inv.case("some-case", "A", srq="flux")
        def test_one():
            pass

        @inv.seam("producer", "consumer")
        def test_two():
            pass

        @inv.regression
        def test_three():
            pass
        """
    )
    result = pytester.runpytest("--strict-markers", "-q")
    result.assert_outcomes(passed=3)
