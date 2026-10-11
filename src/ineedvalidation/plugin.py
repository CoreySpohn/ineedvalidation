"""pytest plugin: registers the evidence markers and writes the evidence file.

Loaded automatically through the ``pytest11`` entry point once the package is
installed, so a repository declares nothing in its own configuration. Passing
``--vv-evidence PATH`` turns on the collector, which records every marked or
defaulted test and writes them all to one JSON file at the end of the session.
"""

import hashlib
import json
import math
import subprocess
import tomllib
import warnings
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ineedvalidation.marks import MARK_CASE, MARK_REGRESSION, MARK_SEAM, validate_case
from ineedvalidation.schema import EvidenceFile, TestRecord

DECLARATION_PROPERTY = "ineedvalidation.declaration"
DECLARATIONS_KEY = "ineedvalidation.declarations"
RESULT_PROPERTY = "ineedvalidation.result"
OUTCOME_SEVERITY = {
    "skipped": 0,
    "passed": 1,
    "xfailed": 2,
    "xpassed": 3,
    "failed": 4,
    "error": 5,
}

MARKER_HELP = {
    MARK_CASE: (
        "vv_case(slug, evidence, srq=None, reference_code=None, "
        "refined_parameter=None, referent=None, reference_model=None, "
        "alternative=None, basis=None, acceptance=None): the physical case, kind of "
        "evidence and system response quantity a test exercises "
        "(use ineedvalidation.case)"
    ),
    MARK_SEAM: (
        "vv_seam(producer, consumer, case=None): an absolute-scale anchor test "
        "across a producer/consumer interface (use ineedvalidation.seam)"
    ),
    MARK_REGRESSION: (
        "vv_regression: a frozen or golden reference, claiming no kind of "
        "evidence (use ineedvalidation.regression)"
    ),
}


def pytest_addoption(parser):
    """Register the evidence output options."""
    group = parser.getgroup("ineedvalidation")
    group.addoption(
        "--vv-evidence",
        action="store",
        default=None,
        metavar="PATH",
        help="write the collected validation evidence to this JSON file",
    )
    group.addoption(
        "--vv-library",
        action="store",
        default=None,
        metavar="NAME",
        help="library name recorded in the evidence file",
    )


def pytest_configure(config):
    """Register the markers and, when asked, the evidence collector."""
    for name, text in MARKER_HELP.items():
        config.addinivalue_line("markers", f"{name}: {text}")
    settings = load_settings(config.rootpath)
    for prefix, values in settings[1].items():
        try:
            if not isinstance(values, dict):
                raise TypeError("default must be a table")
            validate_case(
                values.get("case"),
                values.get("evidence"),
                **{k: v for k, v in values.items() if k not in ("case", "evidence")},
            )
        except (TypeError, ValueError) as error:
            raise pytest.UsageError(
                f"ineedvalidation default {prefix!r}: {error}"
            ) from error
    if config.getoption("--vv-evidence"):
        config.pluginmanager.register(
            EvidenceCollector(config, settings), "vv-evidence"
        )


def _check_number(name, value):
    """Require a finite numeric result or interval endpoint."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")


def _record_file(rootdir, name, value):
    """Hash a file addressed relative to the pytest rootdir."""
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be a path relative to rootdir")
    root = rootdir.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"{name} must be a path within rootdir")
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }


@pytest.fixture
def vv_record(request):
    """Return a callable that validates and records measured test results."""

    def record(
        value=None, interval=None, reference=None, artifact=None, manifest=None, **point
    ):
        if value is not None:
            _check_number("value", value)
        if interval is not None:
            if not isinstance(interval, (list, tuple)) or len(interval) != 2:
                raise ValueError("interval must contain exactly two endpoints")
            for endpoint in interval:
                _check_number("interval endpoint", endpoint)
            if interval[0] > interval[1]:
                raise ValueError("interval must have lo <= hi")
        entry = {
            "value": value,
            "interval": list(interval) if interval is not None else None,
            "reference": reference,
            "artifact": _record_file(request.config.rootpath, "artifact", artifact),
            "manifest": _record_file(request.config.rootpath, "manifest", manifest),
            "point": point,
        }
        # Snapshot JSON data now so later mutation cannot change an earlier call.
        entry = json.loads(json.dumps(entry, allow_nan=False))
        if request.config.getoption("--vv-evidence"):
            request.node.user_properties.append((RESULT_PROPERTY, entry))

    return record


def load_settings(rootdir):
    """Return settings from the rootdir's pyproject or standalone TOML file."""
    rootdir = Path(rootdir)
    pyproject = rootdir / "pyproject.toml"
    standalone = rootdir / "ineedvalidation.toml"
    table = None
    if pyproject.is_file():
        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
        table = data.get("tool", {}).get("ineedvalidation")
    if standalone.is_file():
        if table is not None:
            raise pytest.UsageError(
                f"ineedvalidation settings defined in both {pyproject} and {standalone}"
            )
        with standalone.open("rb") as handle:
            table = tomllib.load(handle)
    if table is None:
        return None, {}
    return table.get("library"), dict(table.get("defaults", {}))


def match_default(relpath, defaults):
    """The default table for the longest matching path prefix, or None."""
    best, best_length = None, -1
    for prefix, values in defaults.items():
        if relpath.startswith(prefix) and len(prefix) > best_length:
            best, best_length = values, len(prefix)
    return best


def _outcome(report, current):
    """Fold a phase report by severity, or return None for an irrelevant phase."""
    if report.when in ("setup", "teardown", "???") and report.failed:
        outcome = "error"
    elif report.when == "setup" and report.skipped:
        outcome = "skipped"
    elif report.when == "call":
        if hasattr(report, "wasxfail"):
            outcome = "xpassed" if report.passed else "xfailed"
        elif report.failed:
            outcome = "failed"
        elif report.skipped:
            outcome = "skipped"
        else:
            outcome = "passed"
    else:
        return None
    if current is None or OUTCOME_SEVERITY[outcome] > OUTCOME_SEVERITY[current]:
        return outcome
    return current


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


def _git_root(rootdir):
    """The pytest rootdir relative to its git repository, or None."""
    try:
        result = subprocess.run(
            ["git", "-C", str(rootdir), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return (
            Path(rootdir)
            .resolve()
            .relative_to(Path(result.stdout.strip()).resolve())
            .as_posix()
        )
    except (OSError, ValueError):
        return None


class EvidenceCollector:
    """Turn marked test items into records and write them at the end of a run."""

    def __init__(self, config, settings):
        """Read the settings for the repository under test."""
        self.config = config
        self.records = {}
        self.outcomes = {}
        self.had_workers = False
        self.received_declarations = False
        library, self.defaults = settings
        self.library = (
            config.getoption("--vv-library") or library or config.rootpath.name
        )

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, items):
        """Capture declarations before deselection, including tests never run."""
        worker = hasattr(self.config, "workerinput")
        for item in items:
            record = self._record(item)
            if record is not None:
                self.records[item.nodeid] = record
                if worker:
                    item.user_properties.append(
                        (DECLARATION_PROPERTY, record.to_dict())
                    )
        if worker:
            self.config.workeroutput[DECLARATIONS_KEY] = [
                record.to_dict() for record in self.records.values()
            ]

    @pytest.hookimpl(optionalhook=True)
    def pytest_testnodedown(self, node, error):
        """Merge worker declarations without overwriting reported outcomes."""
        self.had_workers = True
        workeroutput = getattr(node, "workeroutput", {})
        if DECLARATIONS_KEY in workeroutput:
            self.received_declarations = True
        for declaration in workeroutput.get(DECLARATIONS_KEY, []):
            record = TestRecord.from_dict(declaration)
            # The declaration from the report that ran the test is kept.
            self.records.setdefault(
                record.nodeid,
                replace(record, outcome=self.outcomes.get(record.nodeid)),
            )

    def _record(self, item):
        """The record an item implies, or None when it declares nothing."""
        case_mark = item.get_closest_marker(MARK_CASE)
        seam_mark = item.get_closest_marker(MARK_SEAM)
        regression = item.get_closest_marker(MARK_REGRESSION) is not None
        case = evidence = srq = seam = None
        reference_code = refined_parameter = referent = None
        reference_model = alternative = None
        basis = acceptance = None
        if case_mark is not None:
            case, evidence = case_mark.args[0], case_mark.args[1]
            srq = case_mark.kwargs.get("srq")
            reference_code = case_mark.kwargs.get("reference_code")
            refined_parameter = case_mark.kwargs.get("refined_parameter")
            referent = case_mark.kwargs.get("referent")
            reference_model = case_mark.kwargs.get("reference_model")
            alternative = case_mark.kwargs.get("alternative")
            basis = case_mark.kwargs.get("basis")
            acceptance = case_mark.kwargs.get("acceptance")
        elif seam_mark is None and not regression:
            values = match_default(Path(item.location[0]).as_posix(), self.defaults)
            if values is None:
                return None
            case, evidence = values.get("case"), values.get("evidence")
            srq = values.get("srq")
            reference_code = values.get("reference_code")
            refined_parameter = values.get("refined_parameter")
            referent = values.get("referent")
            reference_model = values.get("reference_model")
            alternative = values.get("alternative")
            basis = values.get("basis")
            acceptance = values.get("acceptance")
        if seam_mark is not None:
            seam = (seam_mark.args[0], seam_mark.args[1])
            case = seam_mark.kwargs.get("case") or case
        if regression:
            evidence = None
        return TestRecord(
            nodeid=item.nodeid,
            case=case,
            evidence=evidence,
            srq=srq,
            reference_code=reference_code,
            refined_parameter=refined_parameter,
            referent=referent,
            reference_model=reference_model,
            alternative=alternative,
            basis=basis,
            acceptance=acceptance,
            seam=seam,
        )

    def pytest_runtest_logreport(self, report):
        """Fold each phase report into the record's outcome and results."""
        # Crash reports have no declaration and can precede a surviving worker's
        # collection payload. Keep their outcomes until declarations arrive.
        outcome = _outcome(report, self.outcomes.get(report.nodeid))
        if outcome is not None:
            self.outcomes[report.nodeid] = outcome
        record = self.records.get(report.nodeid)
        if record is None:
            for name, declaration in report.user_properties:
                if name == DECLARATION_PROPERTY:
                    record = TestRecord.from_dict(declaration)
                    self.records[report.nodeid] = record
                    break
            if record is None:
                return
        results = [
            entry for name, entry in report.user_properties if name == RESULT_PROPERTY
        ]
        self.records[report.nodeid] = replace(
            record,
            outcome=self.outcomes.get(report.nodeid),
            results=results if results else record.results,
        )

    def pytest_sessionfinish(self, session, exitstatus):
        """Write the merged evidence file from the controller only."""
        if hasattr(self.config, "workerinput"):
            return
        target = Path(self.config.getoption("--vv-evidence"))
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = EvidenceFile(
            library=self.library,
            commit=_git_commit(self.config.rootpath),
            recorded=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            tests=tuple(self.records[key] for key in sorted(self.records)),
            mode="collect-only" if self.config.option.collectonly else "run",
            root=_git_root(self.config.rootpath),
        )
        target.write_text(
            json.dumps(payload.to_dict(), indent=1, allow_nan=False) + "\n"
        )
        if self.had_workers and not self.received_declarations:
            warnings.warn(
                f"Evidence ledger {target} may be incomplete: "
                "no worker delivered its declarations payload.",
                pytest.PytestWarning,
                stacklevel=2,
            )
