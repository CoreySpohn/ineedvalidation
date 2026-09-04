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
