from pathlib import Path

from ineedvalidation import nodes, schema

HIER = Path(__file__).parent / "data" / "hierarchy"


def test_load_reads_every_note():
    loaded = nodes.load(HIER / "nodes")
    assert set(loaded) == {
        "complete-system",
        "system-front",
        "subsystem-mixer",
        "benchmark-bench",
        "unit-kernel",
    }
    unit = loaded["unit-kernel"]
    assert unit.level == "unit"
    assert unit.cases == ("kernel-sum",)
    assert unit.couples_to == ("benchmark-bench",)
    assert unit.libraries_planned == ("widgetlib",)
    assert unit.evidence_declared == ("code-verification",)
    assert unit.validation_level == 1
    assert unit.path.name == "unit-kernel.md"


def test_levels_are_ordered_from_complete_to_unit():
    assert schema.HIERARCHY_LEVELS[0] == "complete"
    assert schema.HIERARCHY_LEVELS[-1] == "unit"


def test_subtree_keeps_the_root_and_everything_under_it():
    loaded = nodes.load(HIER / "nodes")
    branch = nodes.subtree(loaded, "subsystem-mixer")
    assert set(branch) == {"subsystem-mixer", "benchmark-bench", "unit-kernel"}


def test_subtree_keeps_the_loading_order():
    loaded = nodes.load(HIER / "nodes")
    branch = nodes.subtree(loaded, "system-front")
    assert list(branch) == [nid for nid in loaded if nid in set(branch)]
