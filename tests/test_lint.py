from dataclasses import replace

from test_nodes import HIER

from ineedvalidation import evidence, nodes
from ineedvalidation.schema import TestRecord as Record


def loaded():
    return nodes.load(HIER / "nodes")


def test_clean_hierarchy_lints_clean():
    assert nodes.lint(loaded()) == []


def test_file_name_must_match_the_id():
    got = loaded()
    got["U-other"] = replace(got.pop("unit-kernel"), id="U-other")
    assert any("does not match id" in p for p in nodes.lint(got))


def test_unknown_hierarchy_level_is_reported():
    got = loaded()
    got["unit-kernel"] = replace(got["unit-kernel"], level="widget")
    assert any("unknown hierarchy level widget" in p for p in nodes.lint(got))


def test_couples_to_must_exist():
    got = loaded()
    got["unit-kernel"] = replace(got["unit-kernel"], couples_to=("nope",))
    assert any("couples_to nope does not exist" in p for p in nodes.lint(got))


def test_couples_to_must_point_at_a_higher_level():
    got = loaded()
    got["benchmark-bench"] = replace(
        got["benchmark-bench"], couples_to=("unit-kernel",)
    )
    assert any("is not at a higher level" in p for p in nodes.lint(got))


def test_non_complete_node_needs_an_edge():
    got = loaded()
    got["unit-kernel"] = replace(got["unit-kernel"], couples_to=())
    assert any("no couples_to edge" in p for p in nodes.lint(got))


def test_referent_status_enum():
    got = loaded()
    got["unit-kernel"] = replace(got["unit-kernel"], referent_status="maybe")
    assert any("referent_status maybe" in p for p in nodes.lint(got))


def test_validation_level_enum():
    got = loaded()
    got["unit-kernel"] = replace(got["unit-kernel"], validation_level=9)
    assert any("validation_level 9" in p for p in nodes.lint(got))


def test_level_two_needs_a_referent_in_hand():
    got = loaded()
    got["benchmark-bench"] = replace(
        got["benchmark-bench"], referent_status="identified"
    )
    assert any("without a referent in hand" in p for p in nodes.lint(got))


def test_level_two_needs_validation_evidence():
    got = loaded()
    got["benchmark-bench"] = replace(
        got["benchmark-bench"], evidence_declared=("code-verification",)
    )
    assert any("without validation evidence" in p for p in nodes.lint(got))


def test_level_three_only_at_the_complete_level():
    got = loaded()
    got["benchmark-bench"] = replace(got["benchmark-bench"], validation_level=3)
    assert any("real system" in p for p in nodes.lint(got))


def test_library_check_runs_only_with_a_library_list():
    got = loaded()
    assert nodes.lint(got, library_text="widgetlib\n") == []
    assert any(
        "not in the library list" in p for p in nodes.lint(got, library_text="other\n")
    )


def summary_for(got):
    return evidence.summarize(got, evidence.load_dir(HIER / "evidence"))


def test_a_node_with_cases_but_no_tests_is_flagged():
    got = loaded()
    problems = nodes.lint(got, summary=summary_for(got))
    assert any("system-front: no evidence" in p for p in problems)


def test_an_srq_a_node_does_not_list_is_flagged():
    got = loaded()
    got["benchmark-bench"] = replace(got["benchmark-bench"], srqs=("something else",))
    problems = nodes.lint(got, summary=summary_for(got))
    assert any("srq loop residual" in p for p in problems)


def test_unfiled_cases_are_reported():
    got = loaded()
    files = evidence.load_dir(HIER / "evidence")
    problems = nodes.lint(
        got,
        summary=evidence.summarize(got, files),
        unfiled=evidence.unfiled_cases(got, files),
    )
    assert any("case not-filed is not owned by any node" in p for p in problems)


def test_level_two_needs_a_passing_validation_test_not_a_marked_one():
    got = loaded()
    downgraded = [
        replace(
            f,
            tests=tuple(
                replace(t, outcome="skipped") if t.evidence == "validation" else t
                for t in f.tests
            ),
        )
        for f in evidence.load_dir(HIER / "evidence")
    ]
    problems = nodes.lint(got, summary=evidence.summarize(got, downgraded))
    assert any(
        "benchmark-bench: validation_level 2 claimed without validation" in p
        for p in problems
    )


def test_a_seam_needs_a_couples_to_edge_between_the_two_nodes():
    got = loaded()
    files = evidence.load_dir(HIER / "evidence")
    anchor = Record(
        nodeid="tests/test_seam.py::test_anchor",
        case="kernel-sum",
        seam=("widgetlib", "otherlib"),
        outcome="passed",
    )
    with_seam = [replace(files[0], tests=(*files[0].tests, anchor))]
    problems = nodes.lint(got, summary=evidence.summarize(got, with_seam))
    assert any("seam widgetlib -> otherlib" in p for p in problems)


def test_level_two_needs_the_axes_the_referent_covers():
    got = loaded()
    got["benchmark-bench"] = replace(got["benchmark-bench"], domain_covers=())
    assert any("without domain_overlap" in p for p in nodes.lint(got))


def test_an_axis_cannot_be_both_covered_and_missed():
    got = loaded()
    got["benchmark-bench"] = replace(
        got["benchmark-bench"], domain_misses=("loop-bandwidth",)
    )
    assert any("both covered and missed" in p for p in nodes.lint(got))


def test_a_node_id_must_start_with_its_level():
    got = loaded()
    got["benchmark-bench"] = replace(got["benchmark-bench"], level="unit")
    assert any("does not start with its level" in p for p in nodes.lint(got))
