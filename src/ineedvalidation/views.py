"""Named views over the hierarchy, and the hand-edited D2 overrides."""

from __future__ import annotations

from pathlib import Path

import yaml

from .schema import View


def builtin() -> dict[str, View]:
    """The two views that reproduce the default reference and status figures."""
    return {
        "reference": View(name="reference", mode="reference", show=()),
        "status": View(name="status", mode="status", show=("libraries", "tiers")),
    }


def load(path: Path) -> View:
    """Read one view file."""
    path = Path(path)
    data = yaml.safe_load(path.read_text()) or {}
    return View(
        name=data.get("name", path.stem),
        root=data.get("root"),
        depth=data.get("depth", "all"),
        mode=data.get("mode", "status"),
        layout=data.get("layout", "elk"),
        show=tuple(data.get("show", ("libraries", "tiers"))),
        highlight=tuple(data.get("highlight", ())),
        title=data.get("title"),
    )


def load_dir(directory: Path) -> dict[str, View]:
    """Every view file in a directory, keyed by name."""
    directory = Path(directory)
    if not directory.is_dir():
        return {}
    found = {}
    for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        view = load(path)
        found[view.name] = view
    return found


def resolve(name: str, directory: Path | None = None) -> View:
    """A named view: a file in the directory first, then a built-in."""
    if directory is not None:
        found = load_dir(directory)
        if name in found:
            return found[name]
    built = builtin()
    if name in built:
        return built[name]
    raise KeyError(f"no view named {name}")


def override_path(directory: Path | None, name: str) -> Path | None:
    """The hand-edited D2 override for a view, when one exists."""
    if directory is None:
        return None
    candidate = Path(directory) / f"{name}.d2"
    return candidate if candidate.is_file() else None
