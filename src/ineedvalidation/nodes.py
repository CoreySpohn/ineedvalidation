"""Load and lint a directory of validation hierarchy notes."""

from __future__ import annotations

from pathlib import Path

import yaml

from .schema import Node


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
    """The root plus every node that couples, transitively, up to it."""
    keep = {root}
    changed = True
    while changed:
        changed = False
        for nid, node in nodes.items():
            if nid not in keep and any(p in keep for p in node.couples_to):
                keep.add(nid)
                changed = True
    return {k: nodes[k] for k in keep}
