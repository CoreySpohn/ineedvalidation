from dataclasses import replace

from test_nodes import HIER

from ineedvalidation import d2, evidence, nodes, views


def emitted(mode="status", **kw):
    got = nodes.load(HIER / "nodes")
    summary = evidence.summarize(got, evidence.load_dir(HIER / "evidence"))
    view = views.builtin()[mode]
    return d2.emit(got, summary, replace(view, **kw) if kw else view)


def test_the_anchor_chain_covers_every_tier_plus_a_floor():
    text = emitted()
    for i in range(6):
        assert f'A{i}: {{ label: ""' in text
    assert "A6:" not in text
    assert "A0 -> A1: { style.opacity: 0 }" in text


def test_a_node_is_pinned_only_where_a_real_edge_would_let_it_drift():
    text = emitted()
    assert "A0 -> C-system" not in text
    assert "A4 -> U-kernel" not in text
    assert "A0 -> S-front" not in text
    assert "U-kernel -> A5: { style.opacity: 0 }" in text
    assert "C-system -> A1" not in text


def test_shapes_and_widths_follow_the_tier():
    text = emitted()
    assert "shape: oval; width: 290; height: 110" in text
    assert "shape: hexagon; width: 290" in text
    assert "shape: rectangle; width: 250" in text
    assert "style.border-radius: 8" in text


def test_the_status_label_carries_libraries_and_evidence():
    text = emitted()
    assert "widgetlib" in text
    assert "evidence D (B)" in text
    assert "evidence A" in text


def test_the_reference_view_has_no_labels_no_legend_and_a_white_ground():
    text = emitted("reference")
    assert 'style.fill: "#ffffff"' in text
    assert "legend:" not in text
    assert "evidence" not in text
    assert "widgetlib" not in text


def test_highlighting_dims_everything_else():
    assert "style.opacity: 0.25" in emitted(highlight=("otherlib",))
    assert "style.opacity: 0.25" not in emitted(highlight=("widgetlib",))


def test_the_subtitle_lists_the_levels_present():
    assert "validation levels present: 1, 2" in emitted()


def test_a_title_is_drawn_when_the_view_names_one():
    assert "Mixer branch" in emitted(title="Mixer branch")
