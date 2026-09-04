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
    got["U-other"] = replace(got.pop("U-kernel"), id="U-other")
    assert any("does not match id" in p for p in nodes.lint(got))


def test_unknown_tier_is_reported():
    got = loaded()
    got["U-kernel"] = replace(got["U-kernel"], tier="widget")
    assert any("unknown tier widget" in p for p in nodes.lint(got))


def test_couples_to_must_exist():
    got = loaded()
    got["U-kernel"] = replace(got["U-kernel"], couples_to=("nope",))
    assert any("couples_to nope does not exist" in p for p in nodes.lint(got))


def test_couples_to_must_point_at_a_higher_tier():
    got = loaded()
    got["B-bench"] = replace(got["B-bench"], couples_to=("U-kernel",))
    assert any("is not in a higher tier" in p for p in nodes.lint(got))


def test_non_complete_node_needs_an_edge():
    got = loaded()
    got["U-kernel"] = replace(got["U-kernel"], couples_to=())
    assert any("no couples_to edge" in p for p in nodes.lint(got))


def test_referent_status_enum():
    got = loaded()
    got["U-kernel"] = replace(got["U-kernel"], referent_status="maybe")
    assert any("referent_status maybe" in p for p in nodes.lint(got))


def test_validation_level_enum():
    got = loaded()
    got["U-kernel"] = replace(got["U-kernel"], validation_level=9)
    assert any("validation_level 9" in p for p in nodes.lint(got))


def test_level_two_needs_a_referent_in_hand():
    got = loaded()
    got["B-bench"] = replace(got["B-bench"], referent_status="identified")
    assert any("without a referent in hand" in p for p in nodes.lint(got))


def test_level_two_needs_tier_d_evidence():
    got = loaded()
    got["B-bench"] = replace(got["B-bench"], evidence_declared=("A",))
    assert any("without Tier D evidence" in p for p in nodes.lint(got))


def test_level_three_only_at_the_complete_tier():
    got = loaded()
    got["B-bench"] = replace(got["B-bench"], validation_level=3)
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
    assert any("S-front: no evidence" in p for p in problems)


def test_an_srq_a_node_does_not_list_is_flagged():
    got = loaded()
    got["B-bench"] = replace(got["B-bench"], srqs=("something else",))
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


def test_level_two_needs_a_passing_tier_d_test_not_a_marked_one():
    got = loaded()
    downgraded = [
        replace(
            f,
            tests=tuple(
                replace(t, outcome="skipped") if t.tier == "D" else t for t in f.tests
            ),
        )
        for f in evidence.load_dir(HIER / "evidence")
    ]
    problems = nodes.lint(got, summary=evidence.summarize(got, downgraded))
    assert any(
        "B-bench: validation_level 2 claimed without Tier D" in p for p in problems
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
