from test_nodes import HIER

from ineedvalidation import evidence, nodes


def summary():
    return evidence.summarize(
        nodes.load(HIER / "nodes"), evidence.load_dir(HIER / "evidence")
    )


def test_load_dir_reads_every_evidence_file():
    files = evidence.load_dir(HIER / "evidence")
    assert [f.library for f in files] == ["widgetlib"]
    assert len(files[0].tests) == 4


def test_summarize_separates_demonstrated_from_claimed():
    bench = summary()["B-bench"]
    assert bench.demonstrated == ("D",)
    assert bench.claimed == ("B",)
    assert bench.libraries == ("widgetlib",)
    assert bench.srqs_covered == ("loop residual",)
    assert bench.refs == ("bench-2026", "othercode")
    assert bench.tests == 2
    assert bench.skipped == 1
    assert bench.computed is True


def test_a_node_with_no_tests_falls_back_to_the_declared_fields():
    front = summary()["S-front"]
    assert front.computed is False
    assert front.demonstrated == ("A",)
    assert front.libraries == ("widgetlib",)


def test_unfiled_cases_are_listed_with_their_libraries():
    unfiled = evidence.unfiled_cases(
        nodes.load(HIER / "nodes"), evidence.load_dir(HIER / "evidence")
    )
    assert unfiled == {"not-filed": ("widgetlib",)}


def test_records_round_trip_through_json():
    files = evidence.load_dir(HIER / "evidence")
    assert type(files[0]).from_dict(files[0].to_dict()) == files[0]
