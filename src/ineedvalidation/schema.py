"""Data types shared by the evidence collector and the hierarchy renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

HIERARCHY_LEVELS = ("complete", "system", "subsystem", "benchmark", "unit")
"""Levels of the validation hierarchy (Oberkampf and Roy ch. 10.2).

Note that "benchmark" here is a hierarchy LEVEL, hardware with two or three
coupled effects. It is unrelated to ``CROSS_CODE_BENCHMARK``, which is a kind
of evidence. The two senses of the word are why neither is abbreviated.
"""

REFERENT_STATUS = ("none", "identified", "requested", "in-hand")
VALIDATION_LEVELS = (0, 1, 2, 3, 4)


def _tuple(value: Any) -> tuple:
    """Return a tuple for a scalar, a sequence or None."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


@dataclass(frozen=True)
class Node:
    """One case in the validation hierarchy, loaded from a note.

    ``domain_covers`` and ``domain_misses`` come from the note's
    ``domain_overlap`` mapping: which axes of the real system's domain of
    operation the referent overlaps, and which it does not. A level-2 claim
    rests on the covered axes and no others.
    """

    id: str
    level: str
    title: str
    couples_to: tuple[str, ...] = ()
    cases: tuple[str, ...] = ()
    srqs: tuple[str, ...] = ()
    referent: str = ""
    referent_status: str = "none"
    validation_level: int = 0
    libraries_planned: tuple[str, ...] = ()
    evidence_declared: tuple[str, ...] = ()
    domain_covers: tuple[str, ...] = ()
    domain_misses: tuple[str, ...] = ()
    path: Path | None = None

    @classmethod
    def from_frontmatter(cls, data: dict, path: Path | None = None) -> Node:
        """Build a node from a parsed frontmatter mapping."""
        return cls(
            id=data.get("id", ""),
            level=data.get("level", ""),
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
            domain_covers=_tuple((data.get("domain_overlap") or {}).get("covers")),
            domain_misses=_tuple((data.get("domain_overlap") or {}).get("misses")),
            path=path,
        )


@dataclass(frozen=True)
class TestRecord:
    """One marked test as it was collected or run."""

    nodeid: str
    case: str | None = None
    evidence: str | None = None
    srq: str | None = None
    reference_code: str | None = None
    refined_parameter: str | None = None
    referent: str | None = None
    seam: tuple[str, str] | None = None
    outcome: str | None = None

    def to_dict(self) -> dict:
        """Return the JSON form of the record."""
        return {
            "nodeid": self.nodeid,
            "case": self.case,
            "evidence": self.evidence,
            "srq": self.srq,
            "reference_code": self.reference_code,
            "refined_parameter": self.refined_parameter,
            "referent": self.referent,
            "seam": list(self.seam) if self.seam else None,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TestRecord:
        """Build a record from its JSON form."""
        seam = data.get("seam")
        return cls(
            nodeid=data["nodeid"],
            case=data.get("case"),
            evidence=data.get("evidence"),
            srq=data.get("srq"),
            reference_code=data.get("reference_code"),
            refined_parameter=data.get("refined_parameter"),
            referent=data.get("referent"),
            seam=tuple(seam) if seam else None,
            outcome=data.get("outcome"),
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
    seams: tuple[tuple[str, str], ...] = ()
    tests: int = 0
    skipped: int = 0
    computed: bool = False


@dataclass(frozen=True)
class View:
    """One named rendering of the hierarchy."""

    name: str
    root: str | None = None
    mode: str = "status"
    layout: str = "elk"
    show: tuple[str, ...] = ("libraries", "evidence")
    highlight: tuple[str, ...] = ()
    title: str | None = None
