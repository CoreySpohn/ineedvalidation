"""pytest plugin: registers the evidence markers and writes the evidence file.

Loaded automatically through the ``pytest11`` entry point once the package is
installed, so a repository declares nothing in its own configuration. Passing
``--inv-evidence PATH`` turns on the collector, which records every marked or
defaulted test and writes them all to one JSON file at the end of the session.
"""

import json
import subprocess
import tomllib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from ineedvalidation.marks import MARK_CASE, MARK_REGRESSION, MARK_SEAM
from ineedvalidation.schema import EvidenceFile, TestRecord

MARKER_HELP = {
    MARK_CASE: (
        "inv_case(slug, tier, srq=None, ref=None): the physical case, evidence "
        "tier and system response quantity a test exercises (use ineedvalidation.case)"
    ),
    MARK_SEAM: (
        "inv_seam(producer, consumer, case=None): an absolute-scale anchor test "
        "across a producer/consumer interface (use ineedvalidation.seam)"
    ),
    MARK_REGRESSION: (
        "inv_regression: a frozen or golden reference, excluded from every "
        "evidence tier (use ineedvalidation.regression)"
    ),
}


def pytest_addoption(parser):
    """Register the evidence output options."""
    group = parser.getgroup("ineedvalidation")
    group.addoption(
        "--inv-evidence",
        action="store",
        default=None,
        metavar="PATH",
        help="write the collected validation evidence to this JSON file",
    )
    group.addoption(
        "--inv-library",
        action="store",
        default=None,
        metavar="NAME",
        help="library name recorded in the evidence file",
    )


def pytest_configure(config):
    """Register the markers and, when asked, the evidence collector."""
    for name, text in MARKER_HELP.items():
        config.addinivalue_line("markers", f"{name}: {text}")
    if config.getoption("--inv-evidence"):
        config.pluginmanager.register(EvidenceCollector(config), "inv-evidence")


def load_settings(rootdir):
    """Return the library name and the path defaults from ``pyproject.toml``."""
    path = Path(rootdir) / "pyproject.toml"
    if not path.is_file():
        return None, {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    table = data.get("tool", {}).get("ineedvalidation", {})
    return table.get("library"), dict(table.get("defaults", {}))


def match_default(relpath, defaults):
    """The default table for the longest matching path prefix, or None."""
    best, best_length = None, -1
    for prefix, values in defaults.items():
        if relpath.startswith(prefix) and len(prefix) > best_length:
            best, best_length = values, len(prefix)
    return best


def _outcome(report, current):
    """The outcome a phase report implies, or None when it says nothing new."""
    if report.when == "setup" and report.skipped:
        return "skipped"
    if report.when == "call":
        if hasattr(report, "wasxfail"):
            return "xpassed" if report.passed else "xfailed"
        if report.failed:
            return "failed"
        if report.skipped:
            return "skipped"
        return "passed"
    if report.when == "teardown" and report.failed and current in (None, "passed"):
        return "error"
    return None


def _git_commit(rootdir):
    """The short commit of the repository under test, or None."""
    try:
        result = subprocess.run(
            ["git", "-C", str(rootdir), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() or None


class EvidenceCollector:
    """Turn marked test items into records and write them at the end of a run."""

    def __init__(self, config):
        """Read the settings for the repository under test."""
        self.config = config
        self.records = {}
        library, self.defaults = load_settings(config.rootpath)
        self.library = (
            config.getoption("--inv-library") or library or config.rootpath.name
        )

    def pytest_collection_modifyitems(self, items):
        """Build one record per marked or defaulted item."""
        for item in items:
            record = self._record(item)
            if record is not None:
                self.records[item.nodeid] = record

    def _record(self, item):
        """The record an item implies, or None when it declares nothing."""
        case_mark = item.get_closest_marker(MARK_CASE)
        seam_mark = item.get_closest_marker(MARK_SEAM)
        regression = item.get_closest_marker(MARK_REGRESSION) is not None
        case = tier = srq = ref = seam = None
        if case_mark is not None:
            case, tier = case_mark.args[0], case_mark.args[1]
            srq, ref = case_mark.kwargs.get("srq"), case_mark.kwargs.get("ref")
        elif seam_mark is None and not regression:
            values = match_default(Path(item.location[0]).as_posix(), self.defaults)
            if values is None:
                return None
            case, tier = values.get("case"), values.get("tier")
            srq, ref = values.get("srq"), values.get("ref")
        if seam_mark is not None:
            seam = (seam_mark.args[0], seam_mark.args[1])
            case = seam_mark.kwargs.get("case") or case
        if regression:
            tier = None
        return TestRecord(
            nodeid=item.nodeid, case=case, tier=tier, srq=srq, ref=ref, seam=seam
        )

    def pytest_runtest_logreport(self, report):
        """Fold each phase report into the record's outcome."""
        record = self.records.get(report.nodeid)
        if record is None:
            return
        outcome = _outcome(report, record.outcome)
        if outcome is not None:
            self.records[report.nodeid] = replace(record, outcome=outcome)

    def pytest_sessionfinish(self, session, exitstatus):
        """Write the evidence file."""
        target = Path(self.config.getoption("--inv-evidence"))
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = EvidenceFile(
            library=self.library,
            commit=_git_commit(self.config.rootpath),
            recorded=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            tests=tuple(self.records[key] for key in sorted(self.records)),
        )
        target.write_text(json.dumps(payload.to_dict(), indent=1) + "\n")
