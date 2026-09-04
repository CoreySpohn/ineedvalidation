"""Data types shared by the evidence collector and the hierarchy renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

HIERARCHY_TIERS = ("complete", "system", "subsystem", "benchmark", "unit")
REFERENT_STATUS = ("none", "identified", "requested", "in-hand")
VALIDATION_LEVELS = (0, 1, 2, 3, 4)
EVIDENCE_ORDER = ("A", "C", "B", "D", "E")


def _tuple(value: Any) -> tuple:
    """Return a tuple for a scalar, a sequence or None."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


@dataclass(frozen=True)
class Node:
    """One case in the validation hierarchy, loaded from a note."""

    id: str
    tier: str
    title: str
    couples_to: tuple[str, ...] = ()
    cases: tuple[str, ...] = ()
    srqs: tuple[str, ...] = ()
    referent: str = ""
    referent_status: str = "none"
    validation_level: int = 0
    libraries_planned: tuple[str, ...] = ()
    evidence_declared: tuple[str, ...] = ()
    path: Path | None = None

    @classmethod
    def from_frontmatter(cls, data: dict, path: Path | None = None) -> Node:
        """Build a node from a parsed frontmatter mapping."""
        return cls(
            id=data.get("id", ""),
            tier=data.get("tier", ""),
            title=data.get("title", ""),
            couples_to=_tuple(data.get("couples_to")),
            cases=_tuple(data.get("cases")),
            srqs=_tuple(data.get("srqs")),
            referent=data.get("referent", ""),
            referent_status=data.get("referent_status", "none"),
            validation_level=data.get("validation_level", 0),
            libraries_planned=(
                _tuple(data.get("libraries")) or _tuple(data.get("libraries_planned"))
            ),
            evidence_declared=_tuple(data.get("evidence")),
            path=path,
        )


@dataclass(frozen=True)
class TestRecord:
    """One marked test as it was collected or run."""

    nodeid: str
    case: str | None = None
    tier: str | None = None
    srq: str | None = None
    ref: str | None = None
    seam: tuple[str, str] | None = None
    outcome: str | None = None
    points: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        """Return the JSON form of the record."""
        return {
            "nodeid": self.nodeid,
            "case": self.case,
            "tier": self.tier,
            "srq": self.srq,
            "ref": self.ref,
            "seam": list(self.seam) if self.seam else None,
            "outcome": self.outcome,
            "points": [dict(p) for p in self.points],
        }

    @classmethod
    def from_dict(cls, data: dict) -> TestRecord:
        """Build a record from its JSON form."""
        seam = data.get("seam")
        return cls(
            nodeid=data["nodeid"],
            case=data.get("case"),
            tier=data.get("tier"),
            srq=data.get("srq"),
            ref=data.get("ref"),
            seam=tuple(seam) if seam else None,
            outcome=data.get("outcome"),
            points=tuple(data.get("points") or ()),
        )


@dataclass(frozen=True)
class EvidenceFile:
    """Every marked test in one repository, with the commit it describes."""

    library: str
    commit: str | None
    recorded: str
    tests: tuple[TestRecord, ...] = ()

    def to_dict(self) -> dict:
        """Return the JSON form of the file."""
        return {
            "library": self.library,
            "commit": self.commit,
            "recorded": self.recorded,
            "tests": [t.to_dict() for t in self.tests],
        }

    @classmethod
    def from_dict(cls, data: dict) -> EvidenceFile:
        """Build an evidence file from its JSON form."""
        return cls(
            library=data["library"],
            commit=data.get("commit"),
            recorded=data.get("recorded", ""),
            tests=tuple(TestRecord.from_dict(t) for t in data.get("tests", [])),
        )


@dataclass(frozen=True)
class NodeSummary:
    """What the collected tests say about one node."""

    node_id: str
    libraries: tuple[str, ...] = ()
    demonstrated: tuple[str, ...] = ()
    claimed: tuple[str, ...] = ()
    srqs_covered: tuple[str, ...] = ()
    refs: tuple[str, ...] = ()
    seams: tuple[tuple[str, str], ...] = ()
    tests: int = 0
    skipped: int = 0
    computed: bool = False
