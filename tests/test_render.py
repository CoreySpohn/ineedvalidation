import re
from pathlib import Path

import pytest
from conftest import HAVE_BINARIES
from test_nodes import HIER

from ineedvalidation import d2, evidence, nodes, views

SAMPLE = Path(__file__).parent / "data" / "sample.svg"


def loaded():
    got = nodes.load(HIER / "nodes")
    return got, evidence.summarize(got, evidence.load_dir(HIER / "evidence"))


def test_require_binary_names_what_is_missing():
    with pytest.raises(RuntimeError, match="definitely-not-a-binary"):
        d2.require_binary("definitely-not-a-binary")


@pytest.mark.skipif(not SAMPLE.exists(), reason="no stored sample svg")
def test_tier_labels_are_written_once_per_tier():
    out = d2.inject_tier_labels(SAMPLE.read_text(), list(d2.HIERARCHY_TIERS), "#ffffff")
    assert out.count('style="text-anchor:end;font-size:22px"') == 5
    assert "Unit" in out and "Complete" in out


@pytest.mark.skipif(not SAMPLE.exists(), reason="no stored sample svg")
def test_the_drawing_is_widened_and_the_fonts_are_remapped():
    original = SAMPLE.read_text()
    out = d2.inject_tier_labels(original, list(d2.HIERARCHY_TIERS), "#ffffff")
    assert "Source Sans 3" in out
    assert "@font-face" not in out
    assert 'font-family: "d2-' not in out
    assert "font-family: d2-" not in out
    before = int(re.search(r'<svg class="[^"]+" width="(\d+)"', original).group(1))
    after = int(re.search(r'<svg class="[^"]+" width="(\d+)"', out).group(1))
    assert after == before + 230


@pytest.mark.skipif(not HAVE_BINARIES, reason="needs d2 and rsvg-convert")
def test_render_produces_all_three_files(tmp_path):
    got, summary = loaded()
    png = d2.render(got, summary, views.builtin()["status"], tmp_path)
    assert png.exists() and png.stat().st_size > 0
    assert (tmp_path / "status.gen.d2").exists()
    assert "text-anchor:end" in (tmp_path / "status.svg").read_text()


@pytest.mark.skipif(not HAVE_BINARIES, reason="needs d2 and rsvg-convert")
def test_an_override_file_is_compiled_instead_of_the_generated_one(tmp_path):
    got, summary = loaded()
    view_dir = tmp_path / "views"
    outdir = tmp_path / "output"
    view_dir.mkdir()
    outdir.mkdir()
    (view_dir / "status.d2").write_text(
        '...@"../output/status.gen.d2"\nU-kernel: { label: "Renamed kernel" }\n'
    )
    d2.render(got, summary, views.builtin()["status"], outdir, view_dir)
    assert "Renamed kernel" in (outdir / "status.svg").read_text()
    assert "Kernel summation" in (outdir / "status.gen.d2").read_text()
