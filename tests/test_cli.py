import shutil

import pytest
from conftest import HAVE_BINARIES
from test_lint import METADATA_HIER, METADATA_PROBLEMS
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
    assert "LINT: system-front: no evidence" in out
    assert "5 nodes, complete=1, system=1, subsystem=1, benchmark=1, unit=1" in out


def test_lint_without_a_ledger_skips_the_two_way_rules(capsys, tmp_path):
    hierarchy = copy(tmp_path)
    shutil.rmtree(hierarchy / "evidence")
    assert cli.main(["lint", str(hierarchy)]) == 0
    assert "LINT:" not in capsys.readouterr().out


def test_lint_reports_two_notes_owning_one_case_and_returns_one(capsys, tmp_path):
    hierarchy = copy(tmp_path)
    shutil.rmtree(hierarchy / "evidence")
    note = hierarchy / "nodes" / "complete-system.md"
    note.write_text(note.read_text().replace("cases: []", "cases:\n- kernel-sum"))
    assert cli.main(["lint", str(hierarchy)]) == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        "LINT: case kernel-sum is owned by nodes complete-system and unit-kernel\n"
        "5 nodes, complete=1, system=1, subsystem=1, benchmark=1, unit=1\n"
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_repeated_library_maps_accept_either_file_and_report_neither(
    capsys, tmp_path, reverse
):
    hierarchy = copy(tmp_path)
    shutil.rmtree(hierarchy / "evidence")
    note = hierarchy / "nodes" / "complete-system.md"
    note.write_text(
        note.read_text().replace("- widgetlib", "- firstlib\n- secondlib\n- unknownlib")
    )
    first = tmp_path / "libraries.md"
    first.write_text("widgetlib\nfirstlib\n")
    second = tmp_path / "extra-libraries.md"
    second.write_text("secondlib\n")
    maps = [second, first] if reverse else [first, second]
    argv = ["lint", str(hierarchy)]
    for path in maps:
        argv.extend(["--library-map", str(path)])
    assert cli.main(argv) == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        "LINT: complete-system: library unknownlib not in the library list\n"
        "5 nodes, complete=1, system=1, subsystem=1, benchmark=1, unit=1\n"
    )
    note.write_text(note.read_text().replace("- unknownlib\n", ""))
    assert cli.main(argv) == 0
    assert capsys.readouterr().out == (
        "5 nodes, complete=1, system=1, subsystem=1, benchmark=1, unit=1\n"
    )


@pytest.mark.parametrize("listed", [True, False])
def test_one_library_map_preserves_1_0_output(capsys, tmp_path, listed):
    library_map = tmp_path / "libraries.md"
    library_map.write_text("widgetlib\n" if listed else "otherlib\n")
    assert cli.main(["lint", str(HIER), "--library-map", str(library_map)]) == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    expected = (HIER.parent / "golden/hierarchy-lint.txt").read_text()
    if not listed:
        expected = (
            "LINT: benchmark-bench: library widgetlib not in the library list\n"
            "LINT: complete-system: library widgetlib not in the library list\n"
            "LINT: subsystem-mixer: library widgetlib not in the library list\n"
            "LINT: subsystem-mixer: no evidence, 1 case(s) declared\n"
            "LINT: system-front: library widgetlib not in the library list\n"
            "LINT: system-front: no evidence, 1 case(s) declared\n"
            "LINT: unit-kernel: library widgetlib not in the library list\n"
            "LINT: case not-filed is not owned by any node (from widgetlib)\n"
            "5 nodes, complete=1, system=1, subsystem=1, benchmark=1, unit=1\n"
        )
    assert captured.out.encode("utf-8") == expected.encode("utf-8")


def test_scaffold_writes_one_stub_per_unfiled_case(tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["scaffold", str(hierarchy)]) == 0
    stub = (hierarchy / "nodes" / "unfiled-not-filed.md").read_text()
    assert "cases:\n- not-filed" in stub
    assert "level: ''" in stub


EXISTING_STUB = """---
id: unfiled-not-filed
level: ''
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
    assert cli.main(["render", str(hierarchy), "--root", "subsystem-mixer"]) == 0
    text = (hierarchy / "output" / "status_subsystem-mixer.gen.d2").read_text()
    assert "complete-system" not in text
    assert "Mixer stage" in text


@pytest.mark.skipif(not HAVE_BINARIES, reason="needs d2 and rsvg-convert")
def test_all_views_includes_the_view_files(tmp_path):
    hierarchy = copy(tmp_path)
    assert cli.main(["render", str(hierarchy), "--all-views"]) == 0
    assert (hierarchy / "output" / "branch.gen.d2").exists()


def test_lint_require_metadata_prints_exactly_three_lines_and_returns_one(capsys):
    assert cli.main(["lint", str(METADATA_HIER), "--require-metadata"]) == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == "".join(
        f"LINT: {problem}\n" for problem in METADATA_PROBLEMS
    )
    assert len(captured.out.splitlines()) == 3


def test_plain_lint_ignores_metadata_defects_and_returns_zero(capsys):
    assert cli.main(["lint", str(METADATA_HIER)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        "1 nodes, complete=1, system=0, subsystem=0, benchmark=0, unit=0\n"
    )
