from pathlib import Path

from ineedvalidation import nodes, schema

HIER = Path(__file__).parent / "data" / "hierarchy"


def test_load_reads_every_note():
    loaded = nodes.load(HIER / "nodes")
    assert set(loaded) == {"C-system", "S-front", "SS-mixer", "B-bench", "U-kernel"}
    unit = loaded["U-kernel"]
    assert unit.tier == "unit"
    assert unit.cases == ("kernel-sum",)
    assert unit.couples_to == ("B-bench",)
    assert unit.libraries_planned == ("widgetlib",)
    assert unit.evidence_declared == ("A",)
    assert unit.validation_level == 1
    assert unit.path.name == "U-kernel.md"


def test_tiers_are_ordered_from_complete_to_unit():
    assert schema.HIERARCHY_TIERS[0] == "complete"
    assert schema.HIERARCHY_TIERS[-1] == "unit"


def test_subtree_keeps_the_root_and_everything_under_it():
    loaded = nodes.load(HIER / "nodes")
    branch = nodes.subtree(loaded, "SS-mixer")
    assert set(branch) == {"SS-mixer", "B-bench", "U-kernel"}


def test_subtree_keeps_the_loading_order():
    loaded = nodes.load(HIER / "nodes")
    branch = nodes.subtree(loaded, "S-front")
    assert list(branch) == [nid for nid in loaded if nid in set(branch)]
