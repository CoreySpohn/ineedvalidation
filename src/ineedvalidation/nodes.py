"""Load and lint a directory of validation hierarchy notes."""

from __future__ import annotations

from pathlib import Path

import yaml

from .schema import (
    EVIDENCE_ORDER,
    HIERARCHY_TIERS,
    REFERENT_STATUS,
    VALIDATION_LEVELS,
    Node,
)


def load(directory: Path) -> dict[str, Node]:
    """Read every ``*.md`` note in a directory, keyed by node id."""
    found: dict[str, Node] = {}
    for path in sorted(Path(directory).glob("*.md")):
        parts = path.read_text().split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"{path}: no YAML frontmatter")
        node = Node.from_frontmatter(yaml.safe_load(parts[1]) or {}, path)
        found[node.id] = node
    return found


def subtree(nodes: dict[str, Node], root: str) -> dict[str, Node]:
    """The root plus every node that couples, transitively, up to it.

    The result keeps the order the notes were loaded in, so a branch renders
    the same way on every run.
    """
    keep = {root}
    changed = True
    while changed:
        changed = False
        for nid, node in nodes.items():
            if nid not in keep and any(p in keep for p in node.couples_to):
                keep.add(nid)
                changed = True
    return {nid: node for nid, node in nodes.items() if nid in keep}


def _evidence_for(node: Node, summary: dict | None) -> tuple[str, ...]:
    """Demonstrated tiers when a summary covers the node, else the declared list."""
    if summary is not None and node.id in summary and summary[node.id].computed:
        return summary[node.id].demonstrated
    return node.evidence_declared


def _seam_is_coupled(nodes: dict[str, Node], producer: str, consumer: str) -> bool:
    """True when a node of one library couples to a node of the other."""

    def owned(library):
        return {nid for nid, n in nodes.items() if library in n.libraries_planned}

    lower, upper = owned(producer), owned(consumer)
    if not lower or not upper:
        return False
    for nid in lower:
        if any(p in upper for p in nodes[nid].couples_to):
            return True
    for nid in upper:
        if any(p in lower for p in nodes[nid].couples_to):
            return True
    return False


def lint(
    nodes: dict[str, Node],
    summary: dict | None = None,
    library_text: str | None = None,
    unfiled: dict[str, tuple[str, ...]] | None = None,
) -> list[str]:
    """Report every rule violation in the hierarchy, as one line each."""
    problems: list[str] = []
    for nid, node in nodes.items():
        if node.path is not None and node.path.stem != nid:
            problems.append(f"{nid}: file name {node.path.name} does not match id")
        if node.tier not in HIERARCHY_TIERS:
            problems.append(f"{nid}: unknown tier {node.tier}")
            continue
        for parent in node.couples_to:
            if parent not in nodes:
                problems.append(f"{nid}: couples_to {parent} does not exist")
            elif HIERARCHY_TIERS.index(nodes[parent].tier) >= HIERARCHY_TIERS.index(
                node.tier
            ):
                problems.append(f"{nid}: couples_to {parent} is not in a higher tier")
        if node.tier != "complete" and not node.couples_to:
            problems.append(f"{nid}: no couples_to edge")
        if library_text is not None:
            for lib in node.libraries_planned:
                if lib not in library_text:
                    problems.append(f"{nid}: library {lib} not in the library list")
        if node.referent_status not in REFERENT_STATUS:
            problems.append(
                f"{nid}: referent_status {node.referent_status} "
                f"not in {list(REFERENT_STATUS)}"
            )
        level = node.validation_level
        if level not in VALIDATION_LEVELS:
            problems.append(
                f"{nid}: validation_level {level} not in {list(VALIDATION_LEVELS)}"
            )
            continue
        for tier in node.evidence_declared:
            if tier not in EVIDENCE_ORDER:
                problems.append(f"{nid}: evidence {tier} not in {list(EVIDENCE_ORDER)}")
        if level >= 2 and node.referent_status != "in-hand":
            problems.append(
                f"{nid}: validation_level {level} claimed without a referent in hand"
            )
        if level >= 2 and "D" not in _evidence_for(node, summary):
            problems.append(
                f"{nid}: validation_level {level} claimed without Tier D evidence"
            )
        if level >= 3 and node.tier != "complete":
            problems.append(
                f"{nid}: validation_level {level} needs measurements on the "
                "real system (Table 9)"
            )
        if summary is not None and nid in summary:
            if node.cases and not summary[nid].computed:
                problems.append(
                    f"{nid}: no evidence, {len(node.cases)} case(s) declared"
                )
            for srq in summary[nid].srqs_covered:
                if srq not in node.srqs:
                    problems.append(f"{nid}: srq {srq} is not one of the node srqs")
            for producer, consumer in summary[nid].seams:
                if not _seam_is_coupled(nodes, producer, consumer):
                    problems.append(
                        f"{nid}: seam {producer} -> {consumer} has no couples_to edge"
                    )
    for case, libraries in (unfiled or {}).items():
        problems.append(
            f"case {case} is not owned by any node (from {', '.join(libraries)})"
        )
    return problems
