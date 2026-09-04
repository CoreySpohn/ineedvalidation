"""Emit the tiered hierarchy diagram as D2, and drive the rendering binaries.

The layout is deterministic: one row per tier, uniform boxes, and an invisible
anchor chain that pins each node to its tier rank from above and below, only
where its real edges would let it drift.
"""

from __future__ import annotations

import textwrap

from .schema import HIERARCHY_TIERS, NodeSummary, View

NODE_W, NODE_H = 250, 110  # px; uniform for every node

TIER_LABEL = {
    "complete": "Complete\nsystem",
    "system": "System\ntier",
    "subsystem": "Subsystem\ntier",
    "benchmark": "Benchmark\ntier",
    "unit": "Unit\nproblems",
}
D2_SHAPE = {
    "complete": "oval",
    "system": "oval",
    "subsystem": "hexagon",
    "benchmark": "rectangle",
    "unit": "rectangle",
}
STATUS_EDGE = {
    "none": "#9a9a9a",
    "identified": "#F5D300",
    "requested": "#FE53BB",
    "in-hand": "#08F7FE",
}
LEVEL_FILL = {0: "#000000", 1: "#3a3a3a", 2: "#0b3d16", 3: "#0f6b25", 4: "#22a544"}
EVIDENCE_TEXT = {
    "A": "A  code verification",
    "C": "C  solution verification",
    "B": "B  cross-code benchmark",
    "D": "D  validation against measurement",
    "E": "E  uncertainty quantification",
}
LEVEL_TEXT = {
    0: "0  insufficient evidence",
    1: "1  conceptually validated",
    2: "2  representative system, in domain",
    3: "3  real system, representative environment",
    4: "4  real system, operating environment",
}


def _wrap(text: str, chars: int) -> str:
    """Wrap a label to a width, joined by the D2 line break."""
    return "\\n".join(textwrap.wrap(text, chars))


def _evidence_text(summary: NodeSummary) -> str:
    """The evidence line for a label: demonstrated plain, claimed in parentheses."""
    parts = list(summary.demonstrated)
    if summary.computed:
        parts += [f"({tier})" for tier in summary.claimed]
    return " ".join(parts) or "none"


def emit(nodes: dict, summary: dict, view: View) -> str:
    """Render the hierarchy as D2 source for one view."""
    dark = view.mode == "status"
    fg, bg = ("#ffffff", "#000000") if dark else ("#000000", "#ffffff")
    lines = [
        "direction: down",
        f"vars: {{ d2-config: {{ layout-engine: {view.layout} }} }}",
        f'style.fill: "{bg}"',
    ]
    tiers = [t for t in HIERARCHY_TIERS if any(n.tier == t for n in nodes.values())]
    # Rank pinning. Anchor chain A0 -> ... -> A(k): A(i) carries the label of tier i
    # and shares its rank with row i; A(k) is a hidden floor. A node is pinned from
    # above (A(i-1) -> node) when no real parent sits in the tier directly above it,
    # and from below (node -> A(i+1)) when no real child sits in the tier directly
    # below it. Together with the real edges this fixes every node to its tier rank
    # under both layout engines with the fewest invisible edges.
    depth = len(tiers)
    for i in range(depth + 1):
        lines.append(
            f'A{i}: {{ label: ""; shape: rectangle; width: 1; height: 1; '
            "style.opacity: 0 }"
        )
        if i:
            lines.append(f"A{i - 1} -> A{i}: {{ style.opacity: 0 }}")
    children = {nid: [c for c in nodes if nid in nodes[c].couples_to] for nid in nodes}
    highlight = set(view.highlight)
    for nid, node in nodes.items():
        dim = bool(highlight) and not highlight & set(summary[nid].libraries)
        i = tiers.index(node.tier)
        parents = [p for p in node.couples_to if p in nodes]
        has_parent_above = any(tiers.index(nodes[p].tier) == i - 1 for p in parents)
        has_child_below = any(
            tiers.index(nodes[c].tier) == i + 1 for c in children[nid]
        )
        wrap = 26 if node.tier in ("benchmark", "unit") else 22
        label = _wrap(node.title, wrap)
        if dark and "libraries" in view.show:
            label += "\\n" + _wrap(", ".join(summary[nid].libraries), 34)
        if dark and "tiers" in view.show:
            label += "\\nevidence " + _evidence_text(summary[nid])
        fill = LEVEL_FILL[node.validation_level] if dark else bg
        stroke = STATUS_EDGE[node.referent_status] if dark else fg
        width = 3 if dark and node.referent_status != "none" else 2
        box = (
            NODE_W + 40 if node.tier in ("complete", "system", "subsystem") else NODE_W
        )
        lines.append(
            f'{nid}: {{ label: "{label}"; shape: {D2_SHAPE[node.tier]}; '
            f"width: {box}; height: {NODE_H}; "
            f'style.fill: "{fill}"; style.stroke: "{stroke}"; '
            f"style.stroke-width: {width}; "
            f'style.font-color: "{fg}"; style.font-size: 15; style.bold: true'
            + ("; style.border-radius: 8" if node.tier == "benchmark" else "")
            + ("; style.opacity: 0.25" if dim else "")
            + " }"
        )
        if i > 0 and not has_parent_above:
            lines.append(f"A{i - 1} -> {nid}: {{ style.opacity: 0 }}")
        if not has_child_below:
            lines.append(f"{nid} -> A{i + 1}: {{ style.opacity: 0 }}")
    for nid, node in nodes.items():
        for parent in node.couples_to:
            if parent not in nodes:
                continue
            dim = bool(highlight) and not (
                highlight & set(summary[nid].libraries)
                and highlight & set(summary[parent].libraries)
            )
            lines.append(
                f'{parent} -> {nid}: {{ style.stroke: "{fg}"; style.stroke-width: 1'
                + ("; style.opacity: 0.2" if dim else "")
                + " }"
            )
    if dark:
        present = sorted({n.validation_level for n in nodes.values()})
        subtitle = (
            "validation levels present: "
            + ", ".join(str(v) for v in present)
            + " (NASA-STD-7009B Table 9; level 2 is the ceiling before launch)"
        )
        head = (view.title + "\\n" if view.title else "") + subtitle
        lines.insert(
            3,
            f'title: {{ label: "{head}"; shape: text; near: top-center; '
            f"style.font-size: {30 if view.title else 18}; "
            f"style.bold: {'true' if view.title else 'false'}; "
            f'style.font-color: "{fg}" }}',
        )
    elif view.title:
        lines.insert(
            3,
            f'title: {{ label: "{view.title}"; shape: text; near: top-center; '
            f'style.font-size: 30; style.bold: true; style.font-color: "{fg}" }}',
        )
    if dark:
        lines.append("legend: {")
        lines.append('  label: ""')
        lines.append("  near: bottom-center")
        lines.append("  grid-rows: 3")
        lines.append("  grid-gap: 6")
        lines.append(f'  style.fill: "{bg}"')
        lines.append(f'  style.stroke: "{bg}"')
        cell = (
            f"shape: rectangle; width: 300; height: 38; style.font-size: 13; "
            f'style.font-color: "{fg}"'
        )
        # D2 fills a grid-rows grid column by column: three cells per column,
        # read top to bottom
        entries = []
        for level, color in LEVEL_FILL.items():
            entries.append(
                f'l{level}: {{ label: "level {LEVEL_TEXT[level]}"; {cell}; '
                f'style.fill: "{color}"; style.stroke: "{fg}"; style.stroke-width: 1 }}'
            )
        entries.append(f'gap1: {{ label: ""; {cell}; style.opacity: 0 }}')
        for status, color in STATUS_EDGE.items():
            entries.append(
                f'r{status}: {{ label: "referent {status}"; {cell}; '
                f'style.fill: "{bg}"; style.stroke: "{color}"; style.stroke-width: 3 }}'
            )
        entries.append(f'gap2: {{ label: ""; {cell}; style.opacity: 0 }}')
        entries.append(f'gap3: {{ label: ""; {cell}; style.opacity: 0 }}')
        for tier, text in EVIDENCE_TEXT.items():
            entries.append(
                f'e{tier}: {{ label: "evidence {text}"; {cell}; '
                f'style.fill: "{bg}"; style.stroke: "#555555"; '
                "style.stroke-width: 1; style.stroke-dash: 3 }"
            )
        for entry in entries:
            lines.append("  " + entry)
        lines.append("}")
    return "\n".join(lines) + "\n"
