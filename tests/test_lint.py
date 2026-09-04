from dataclasses import replace

from test_nodes import HIER

from ineedvalidation import nodes


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
