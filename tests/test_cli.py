import shutil

import pytest
from conftest import HAVE_BINARIES
from test_nodes import HIER

from ineedvalidation import cli


def copy(tmp_path):
    target = tmp_path / "hierarchy"
    shutil.copytree(HIER, target)
    return target


def test_lint_reports_problems_and_returns_one(capsys, tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["lint", str(hierarchy)]) == 1
    out = capsys.readouterr().out
    assert "LINT: case not-filed is not owned by any node" in out
    assert "LINT: S-front: no evidence" in out
    assert "5 nodes, complete=1, system=1, subsystem=1, benchmark=1, unit=1" in out


def test_lint_without_a_ledger_skips_the_two_way_rules(capsys, tmp_path):
    hierarchy = copy(tmp_path)
    shutil.rmtree(hierarchy / "evidence")
    assert cli.main(["lint", str(hierarchy)]) == 0
    assert "LINT:" not in capsys.readouterr().out


def test_scaffold_writes_one_stub_per_unfiled_case(tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["scaffold", str(hierarchy)]) == 0
    stub = (hierarchy / "nodes" / "unfiled-not-filed.md").read_text()
    assert "cases:\n- not-filed" in stub
    assert "tier: ''" in stub


EXISTING_STUB = """---
id: unfiled-not-filed
tier: ''
title: something a curator started
couples_to: []
cases: []
srqs: []
referent: ''
referent_status: none
validation_level: 0
---
# something a curator started

Keep me.
"""


def test_scaffold_never_overwrites(capsys, tmp_path):
    hierarchy = copy(tmp_path)
    target = hierarchy / "nodes" / "unfiled-not-filed.md"
    target.write_text(EXISTING_STUB)
    assert cli.main(["scaffold", str(hierarchy)]) == 0
    assert target.read_text() == EXISTING_STUB
    assert "skipped, already present" in capsys.readouterr().out


def test_an_unknown_view_name_is_an_error(capsys, tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["render", str(hierarchy), "--view", "nope"]) == 2
    assert "no view named nope" in capsys.readouterr().err


@pytest.mark.skipif(not HAVE_BINARIES, reason="needs d2 and rsvg-convert")
def test_render_writes_the_two_builtin_views(tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["render", str(hierarchy)]) == 0
    for name in ("reference", "status"):
        assert (hierarchy / "output" / f"{name}.gen.d2").exists()
        assert (hierarchy / "output" / f"{name}.png").exists()


@pytest.mark.skipif(not HAVE_BINARIES, reason="needs d2 and rsvg-convert")
def test_render_of_a_branch_names_the_output_for_the_root(tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["render", str(hierarchy), "--root", "SS-mixer"]) == 0
    text = (hierarchy / "output" / "status_SS-mixer.gen.d2").read_text()
    assert "C-system" not in text
    assert "Mixer stage" in text


@pytest.mark.skipif(not HAVE_BINARIES, reason="needs d2 and rsvg-convert")
def test_all_views_includes_the_view_files(tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["render", str(hierarchy), "--all-views"]) == 0
    assert (hierarchy / "output" / "branch.gen.d2").exists()
