"""Fold per-repository evidence files into one summary per hierarchy node."""

from __future__ import annotations

import json
from pathlib import Path

from .marks import EVIDENCE_KINDS
from .schema import EvidenceFile, Node, NodeSummary


def load_dir(directory: Path) -> list[EvidenceFile]:
    """Read every ``*.json`` evidence file in a directory."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return [
        EvidenceFile.from_dict(json.loads(path.read_text()))
        for path in sorted(directory.glob("*.json"))
    ]


def _reading_order(kinds) -> tuple[str, ...]:
    """Sort evidence kinds into EVIDENCE_KINDS order, not alphabetical order."""
    return tuple(kind for kind in EVIDENCE_KINDS if kind in kinds)


def summarize(
    nodes: dict[str, Node], files: list[EvidenceFile]
) -> dict[str, NodeSummary]:
    """One summary per node, computed where tests exist, declared where they do not."""
    owner = {case: nid for nid, node in nodes.items() for case in node.cases}
    collected: dict[str, list[tuple[str, object]]] = {nid: [] for nid in nodes}
    for evidence_file in files:
        for record in evidence_file.tests:
            nid = owner.get(record.case)
            if nid is not None:
                collected[nid].append((evidence_file.library, record))
    summaries = {}
    for nid, node in nodes.items():
        rows = collected[nid]
        if not rows:
            summaries[nid] = NodeSummary(
                node_id=nid,
                libraries=node.libraries_planned,
                demonstrated=_reading_order(node.evidence_declared),
                computed=False,
            )
            continue
        demonstrated: set[str] = set()
        claimed: set[str] = set()
        libraries: list[str] = []
        srqs: list[str] = []
        seams: list[tuple[str, str]] = []
        skipped = 0
        for library, record in rows:
            if library not in libraries:
                libraries.append(library)
            if record.evidence:
                target = demonstrated if record.outcome == "passed" else claimed
                target.add(record.evidence)
            if record.srq and record.srq not in srqs:
                srqs.append(record.srq)
            if record.seam and record.seam not in seams:
                seams.append(record.seam)
            if record.outcome in ("skipped", "xfailed"):
                skipped += 1
        summaries[nid] = NodeSummary(
            node_id=nid,
            libraries=tuple(libraries),
            demonstrated=_reading_order(demonstrated),
            claimed=_reading_order(claimed - demonstrated),
            srqs_covered=tuple(srqs),
            seams=tuple(seams),
            tests=len(rows),
            skipped=skipped,
            computed=True,
        )
    return summaries


def unfiled_cases(
    nodes: dict[str, Node], files: list[EvidenceFile]
) -> dict[str, tuple[str, ...]]:
    """Cases named by a test that no node owns, mapped to the libraries naming them."""
    known = {case for node in nodes.values() for case in node.cases}
    found: dict[str, list[str]] = {}
    for evidence_file in files:
        for record in evidence_file.tests:
            if record.case and record.case not in known:
                libraries = found.setdefault(record.case, [])
                if evidence_file.library not in libraries:
                    libraries.append(evidence_file.library)
    return {case: tuple(libraries) for case, libraries in sorted(found.items())}
