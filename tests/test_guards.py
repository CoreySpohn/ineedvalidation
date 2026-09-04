"""The internal-reference guard and import purity."""

import pathlib
import subprocess
import sys

import ineedvalidation

SRC = pathlib.Path(ineedvalidation.__file__).parent
REPO = SRC.parent.parent
FORBIDDEN_LIBS = ("jax", "numpy", "matplotlib", "astropy", "xarray")


def test_no_internal_refs():
    suffixes = {".py", ".md", ".toml", ".yml", ".yaml"}
    skip_dirs = {".git", "_build", ".venv"}
    skip_names = {"CHANGELOG.md", "check_internal_refs.py"}
    files = [
        p
        for p in REPO.rglob("*")
        if p.is_file()
        and p.suffix in suffixes
        and not skip_dirs & set(p.parts)
        and p.name not in skip_names
    ]
    guard = REPO / "tools" / "check_internal_refs.py"
    result = subprocess.run(
        [sys.executable, str(guard), *map(str, files)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_heavy_imports():
    for path in SRC.rglob("*.py"):
        text = path.read_text()
        for lib in FORBIDDEN_LIBS:
            assert f"import {lib}" not in text, f"{path.name} imports {lib}"
            assert f"from {lib}" not in text, f"{path.name} imports {lib}"
