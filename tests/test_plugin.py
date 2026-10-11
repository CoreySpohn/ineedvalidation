import hashlib
import importlib.util
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest
from test_marks import EXPECTED_BASES
from test_nodes import HIER

from ineedvalidation.plugin import RESULT_PROPERTY, _outcome
from ineedvalidation.schema import EvidenceFile

pytest_plugins = ["pytester"]

MARKED = """
import pytest

import ineedvalidation as vv


@vv.case("kernel-sum", "code-verification", srq="summation error")
def test_passes():
    assert True


@vv.case("kernel-sum", "cross-code-benchmark", reference_code="othercode")
def test_skips():
    pytest.skip("no reference data")


@vv.regression
def test_golden():
    assert True


def test_unmarked():
    assert True
"""

TOML = '[tool.pytest.ini_options]\n[tool.ineedvalidation]\nlibrary = "widgetlib"\n'

STANDALONE_TOML = """
library = "widgetlib"

[defaults."tests/"]
case = "kernel-sum"
evidence = "code-verification"
srq = "summation error"
basis = "floating-point"
acceptance = { tolerance = 1e-12 }
"""


@pytest.fixture
def settings_suite(pytester):
    pytester.makepyfile(**{"tests/test_defaulted": "def test_default():\n    pass\n"})
    return pytester


def test_pytest_ini_and_standalone_settings_apply(settings_suite, tmp_path):
    settings_suite.makefile(".ini", pytest="[pytest]\ntestpaths = tests\n")
    settings_suite.makefile(".toml", ineedvalidation=STANDALONE_TOML)
    out = tmp_path / "evidence.json"
    result = settings_suite.runpytest("tests", "--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    data = json.loads(out.read_text())
    assert data["library"] == "widgetlib"
    assert len(data["tests"]) == 1
    record = data["tests"][0]
    assert record["nodeid"] == "tests/test_defaulted.py::test_default"
    assert record["case"] == "kernel-sum"
    assert record["evidence"] == "code-verification"
    assert record["srq"] == "summation error"
    assert record["basis"] == "floating-point"
    assert record["acceptance"] == {"tolerance": 1e-12}
    assert record["outcome"] == "passed"


def test_pytest_only_pyproject_allows_standalone_settings(settings_suite, tmp_path):
    settings_suite.makefile(
        ".toml", pyproject='[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )
    settings_suite.makefile(".toml", ineedvalidation=STANDALONE_TOML)
    out = tmp_path / "evidence.json"
    result = settings_suite.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    data = json.loads(out.read_text())
    assert data["library"] == "widgetlib"
    assert len(data["tests"]) == 1
    record = data["tests"][0]
    assert record["nodeid"] == "tests/test_defaulted.py::test_default"
    assert record["case"] == "kernel-sum"
    assert record["evidence"] == "code-verification"
    assert record["basis"] == "floating-point"
    assert record["acceptance"] == {"tolerance": 1e-12}


@pytest.mark.parametrize("collect", [False, True])
@pytest.mark.parametrize("pyproject_settings", [TOML, "[tool.ineedvalidation]\n"])
def test_both_settings_files_raise_usage_error(
    settings_suite, tmp_path, collect, pyproject_settings
):
    settings_suite.makeini("[pytest]\n")
    pyproject = settings_suite.makefile(".toml", pyproject=pyproject_settings)
    standalone = settings_suite.makefile(".toml", ineedvalidation=STANDALONE_TOML)
    out = tmp_path / "evidence.json"
    result = settings_suite.runpytest(*(["--vv-evidence", str(out)] if collect else []))
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    message = result.stderr.str()
    assert str(pyproject) in message
    assert str(standalone) in message
    assert not out.exists()


def test_pyproject_settings_without_standalone_file_are_unchanged(
    settings_suite, tmp_path
):
    settings_suite.makefile(
        ".toml",
        pyproject=(
            TOML
            + "[tool.ineedvalidation.defaults]\n"
            + '"tests/" = { case = "kernel-sum", evidence = "code-verification" }\n'
        ),
    )
    out = tmp_path / "evidence.json"
    result = settings_suite.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    data = json.loads(out.read_text())
    assert data["library"] == "widgetlib"
    assert len(data["tests"]) == 1
    record = data["tests"][0]
    assert record["nodeid"] == "tests/test_defaulted.py::test_default"
    assert record["case"] == "kernel-sum"
    assert record["evidence"] == "code-verification"
    assert record["outcome"] == "passed"


def test_vv_library_overrides_standalone_name(settings_suite, tmp_path):
    settings_suite.makeini("[pytest]\n")
    settings_suite.makefile(".toml", ineedvalidation=STANDALONE_TOML)
    out = tmp_path / "evidence.json"
    result = settings_suite.runpytest(
        "--vv-evidence", str(out), "--vv-library", "override-lib"
    )
    result.assert_outcomes(passed=1)
    data = json.loads(out.read_text())
    assert data["library"] == "override-lib"
    assert len(data["tests"]) == 1
    assert data["tests"][0]["case"] == "kernel-sum"


@pytest.mark.parametrize("collect", [False, True])
def test_standalone_default_with_misspelled_kind_is_usage_error(
    settings_suite, tmp_path, collect
):
    settings_suite.makeini("[pytest]\n")
    settings_suite.makefile(
        ".toml",
        ineedvalidation=(
            'library = "widgetlib"\n[defaults]\n'
            '"unused_tests/" = { case = "kernel-sum", evidence = "code-verificaton" }\n'
        ),
    )
    out = tmp_path / "evidence.json"
    result = settings_suite.runpytest(*(["--vv-evidence", str(out)] if collect else []))
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    message = result.stderr.str()
    assert "unused_tests/" in message
    assert "code-verificaton" in message
    assert "code-verification" in message
    assert not out.exists()


def test_evidence_records_outcomes(pytester, tmp_path):
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=3, skipped=1)
    data = json.loads(out.read_text())
    assert data["library"] == "widgetlib"
    assert data["mode"] == "run"
    assert EvidenceFile.from_dict(data).mode == "run"
    by_name = {r["nodeid"].split("::")[-1]: r for r in data["tests"]}
    assert set(by_name) == {"test_passes", "test_skips", "test_golden"}
    assert by_name["test_passes"]["case"] == "kernel-sum"
    assert by_name["test_passes"]["evidence"] == "code-verification"
    assert by_name["test_passes"]["srq"] == "summation error"
    assert by_name["test_passes"]["outcome"] == "passed"
    assert by_name["test_skips"]["outcome"] == "skipped"
    assert by_name["test_skips"]["reference_code"] == "othercode"
    assert by_name["test_golden"]["evidence"] is None


def test_collect_only_leaves_outcomes_null(pytester, tmp_path):
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    pytester.runpytest("--collect-only", "--vv-evidence", str(out))
    data = json.loads(out.read_text())
    assert data["mode"] == "collect-only"
    assert EvidenceFile.from_dict(data).mode == "collect-only"
    assert len(data["tests"]) == 3
    assert {r["outcome"] for r in data["tests"]} == {None}


def test_a_path_default_tags_an_unmarked_test(pytester, tmp_path):
    pytester.makepyfile(
        **{"slow_tests/test_defaulted": "def test_default():\n    assert True\n"}
    )
    pytester.makefile(
        ".toml",
        pyproject=(
            TOML
            + "[tool.ineedvalidation.defaults]\n"
            + '"slow_tests/" = { case = "bench-loop", evidence = "validation" }\n'
        ),
    )
    out = tmp_path / "evidence.json"
    pytester.runpytest("--vv-evidence", str(out))
    data = json.loads(out.read_text())
    assert data["tests"][0]["case"] == "bench-loop"
    assert data["tests"][0]["evidence"] == "validation"
    assert data["tests"][0]["outcome"] == "passed"


def test_the_longest_prefix_wins():
    from ineedvalidation.plugin import match_default

    defaults = {
        "tests/": {"case": "broad", "evidence": "A"},
        "tests/deep/": {"case": "narrow", "evidence": "B"},
    }
    assert match_default("tests/test_a.py", defaults)["case"] == "broad"
    assert match_default("tests/deep/test_b.py", defaults)["case"] == "narrow"
    assert match_default("other/test_c.py", defaults) is None


def test_a_marker_overrides_a_path_default(pytester, tmp_path):
    pytester.makepyfile(
        **{
            "slow_tests/test_marked": (
                "import ineedvalidation as vv\n\n\n"
                '@vv.case("mixer", "solution-verification")\n'
                "def test_marked():\n    assert True\n"
            )
        }
    )
    pytester.makefile(
        ".toml",
        pyproject=(
            TOML
            + "[tool.ineedvalidation.defaults]\n"
            + '"slow_tests/" = { case = "bench-loop", evidence = "validation" }\n'
        ),
    )
    out = tmp_path / "evidence.json"
    pytester.runpytest("--vv-evidence", str(out))
    data = json.loads(out.read_text())
    assert data["tests"][0]["case"] == "mixer"
    assert data["tests"][0]["evidence"] == "solution-verification"


@pytest.mark.parametrize(
    ("keyword", "kind", "value"),
    [
        ("reference_model", "solution-verification", " Full model: grid = 0.01 "),
        ("alternative", "uncertainty-quantification", " Alternative: closure B "),
    ],
)
@pytest.mark.parametrize("source", ["decorator", "default"])
def test_kind_keyword_round_trips_into_ledger(
    pytester, tmp_path, keyword, kind, value, source
):
    declaration = (
        "import ineedvalidation as vv\n\n"
        f'@vv.case("mixer", {kind!r}, {keyword}={value!r})\n'
        if source == "decorator"
        else ""
    )
    pytester.makepyfile(test_model=declaration + "def test_model():\n    assert True\n")
    settings = TOML
    if source == "default":
        settings += (
            '[tool.ineedvalidation.defaults."test_model.py"]\n'
            'case = "mixer"\n'
            f'evidence = "{kind}"\n'
            f'{keyword} = "{value}"\n'
        )
    pytester.makefile(".toml", pyproject=settings)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    data = json.loads(out.read_text())
    record = data["tests"][0]
    assert record["case"] == "mixer"
    assert record["evidence"] == kind
    assert record[keyword] == value
    loaded = EvidenceFile.from_dict(data)
    assert getattr(loaded.tests[0], keyword) == value
    assert loaded.to_dict()["tests"][0][keyword] == value


@pytest.mark.parametrize(
    "defaults",
    [
        'evidence = "solution-verification"\n'
        'refined_parameter = "grid-spacing"\nreference_model = "full model"\n',
        'evidence = "uncertainty-quantification"\nalternative = "closure B"\n',
        'evidence = "cross-code-benchmark"\nreference_code = "other-code"\n',
        'evidence = "validation"\nreferent = "lab-data"\n',
    ],
)
@pytest.mark.parametrize("source", ["pyproject", "standalone"])
def test_explicit_marker_replaces_all_default_fields(
    pytester, tmp_path, defaults, source
):
    pytester.makepyfile(
        test_model=(
            "import ineedvalidation as vv\n\n"
            '@vv.case("explicit-case", "code-verification")\n'
            "def test_model():\n    assert True\n"
        )
    )
    header = (
        TOML + '[tool.ineedvalidation.defaults."test_model.py"]\n'
        if source == "pyproject"
        else '[defaults."test_model.py"]\n'
    )
    pytester.makeini("[pytest]\n")
    pytester.makefile(
        ".toml",
        **{
            "pyproject" if source == "pyproject" else "ineedvalidation": (
                header
                + 'case = "default-case"\nsrq = "default response"\n'
                + defaults
                + 'basis = "floating-point"\n'
                + 'acceptance = { metric = "error", tolerance = 0.001 }\n'
            )
        },
    )
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    record = json.loads(out.read_text())["tests"][0]
    assert record == {
        "nodeid": "test_model.py::test_model",
        "case": "explicit-case",
        "evidence": "code-verification",
        "srq": None,
        "reference_code": None,
        "refined_parameter": None,
        "referent": None,
        "reference_model": None,
        "alternative": None,
        "basis": None,
        "acceptance": None,
        "results": [],
        "seam": None,
        "outcome": "passed",
    }


def test_module_level_pytestmark_is_honoured(pytester, tmp_path):
    pytester.makepyfile(
        test_mod=(
            "import ineedvalidation as vv\n\n"
            "pytestmark = vv.case(\n"
            '    "mixer", "solution-verification", refined_parameter="grid"\n'
            ")\n\n\n"
            "def test_one():\n    assert True\n"
        )
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    pytester.runpytest("--vv-evidence", str(out))
    data = json.loads(out.read_text())
    assert data["tests"][0]["case"] == "mixer"
    assert data["tests"][0]["evidence"] == "solution-verification"
    assert data["tests"][0]["refined_parameter"] == "grid"


def test_no_evidence_file_is_written_without_the_option(pytester, tmp_path):
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    pytester.runpytest()
    assert not (tmp_path / "evidence.json").exists()


@pytest.mark.parametrize("collect", [False, True])
@pytest.mark.parametrize("source", ["pyproject", "standalone"])
@pytest.mark.parametrize(
    ("declaration", "messages"),
    [
        ('basis = "not-a-basis"', ("not-a-basis", *EXPECTED_BASES)),
        ("acceptance = { typo = 1 }", ("typo",)),
        ("acceptance = { tolerance = nan }", ("finite",)),
        ("acceptance = { tolerance = inf }", ("finite",)),
        ("acceptance = { tolerance = -inf }", ("finite",)),
        ("acceptance = { margin = [1, nan] }", ("finite",)),
        ("acceptance = { margin = [1, inf] }", ("finite",)),
        ("acceptance = { domain = { nested = 1 } }", ("acceptance.domain",)),
        ('acceptance = { domain = ["first", { nested = 1 }] }', ("acceptance.domain",)),
        ('acceptance = { registered = "2026-13-01" }', ("YYYY-MM-DD",)),
        ('acceptance = { registered = "2026-10-01T00:00" }', ("YYYY-MM-DD",)),
        ('evidence = "code-verificaton"', ("code-verificaton", "code-verification")),
        (
            'reference_model = "full model"',
            ("reference_model", "solution-verification"),
        ),
    ],
)
def test_every_default_is_validated_at_configure_time(
    pytester, tmp_path, collect, source, declaration, messages
):
    pytester.makepyfile(test_plain="def test_plain():\n    assert True\n")
    evidence_line = (
        ""
        if declaration.startswith("evidence =")
        else 'evidence = "code-verification"\n'
    )
    header = (
        TOML + '[tool.ineedvalidation.defaults."unused_tests/"]\n'
        if source == "pyproject"
        else '[defaults."unused_tests/"]\n'
    )
    pytester.makeini("[pytest]\n")
    pytester.makefile(
        ".toml",
        **{
            "pyproject" if source == "pyproject" else "ineedvalidation": (
                header + 'case = "some-case"\n' + evidence_line + declaration + "\n"
            )
        },
    )
    out = tmp_path / "evidence.json"
    result = pytester.runpytest(*(["--vv-evidence", str(out)] if collect else []))
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    message = result.stderr.str()
    assert "unused_tests/" in message
    for expected in messages:
        assert expected in message
    assert not out.exists()


def reject_constant(token):
    raise ValueError(f"non-finite JSON token: {token}")


ACCEPTANCE = {
    "metric": " Absolute error ",
    "tolerance": 0.001,
    "margin": -2,
    "rule": True,
    "domain": ["unit interval", False, 0, 0.5],
    "draws": 1000,
    "sigma": [1, 2.5],
    "reference_error": 0.0,
    "registered": "2026-10-01",
}


@pytest.mark.parametrize(
    ("basis", "acceptance"),
    [(basis, ACCEPTANCE) for basis in EXPECTED_BASES]
    + [("floating-point", {}), ("floating-point", {"domain": []})],
)
@pytest.mark.parametrize("source", ["decorator", "default"])
def test_basis_and_acceptance_round_trip_exactly(
    pytester, tmp_path, basis, acceptance, source
):
    declaration = (
        "import ineedvalidation as vv\n\n"
        f'@vv.case("some-case", "code-verification", basis={basis!r}, '
        f"acceptance={acceptance!r})\n"
        if source == "decorator"
        else ""
    )
    pytester.makepyfile(test_metadata=declaration + "def test_metadata():\n    pass\n")
    settings = TOML
    if source == "default":
        settings += (
            '[tool.ineedvalidation.defaults."test_metadata.py"]\n'
            'case = "some-case"\nevidence = "code-verification"\n'
            f'basis = "{basis}"\n'
            '[tool.ineedvalidation.defaults."test_metadata.py".acceptance]\n'
            + "\n".join(
                f"{key} = {json.dumps(value)}" for key, value in acceptance.items()
            )
            + "\n"
        )
    pytester.makefile(".toml", pyproject=settings)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    ledger_text = out.read_text()
    assert "NaN" not in ledger_text
    assert "Infinity" not in ledger_text
    data = json.loads(ledger_text, parse_constant=reject_constant)
    record = data["tests"][0]
    assert record["basis"] == basis
    assert record["acceptance"] == acceptance
    # JSON equality also distinguishes booleans from numbers and ints from floats.
    assert json.dumps(record["acceptance"], sort_keys=True) == json.dumps(
        acceptance, sort_keys=True
    )
    loaded = EvidenceFile.from_dict(data)
    assert loaded.tests[0].basis == basis
    assert loaded.tests[0].acceptance == acceptance
    assert loaded.to_dict() == data


@pytest.mark.parametrize("keyword", ["basis", "acceptance"])
def test_1_0_ledger_missing_metadata_reads_as_null(keyword):
    from test_nodes import HIER

    data = json.loads((HIER.parent / "ledger-1.0.json").read_text())
    assert keyword not in data["tests"][0]
    loaded = EvidenceFile.from_dict(data)
    assert getattr(loaded.tests[0], keyword) is None
    assert loaded.to_dict()["tests"][0][keyword] is None


SIX_TESTS = """
import pytest
import ineedvalidation as vv


@vv.case("kernel-sum", "code-verification", srq="summation error",
         basis="floating-point", acceptance={"tolerance": 1e-12})
def test_passes(vv_record):
    vv_record(value=0.25, interval=(0.2, 0.3), reference=0.25, spacing=0.1,
              artifact="pyproject.toml", manifest="pyproject.toml")
    vv_record(value=0.125, spacing=0.05)
    assert True


@vv.case("kernel-sum", "code-verification")
def test_fails(vv_record):
    vv_record(value=0.5)
    assert False


@vv.case("kernel-sum", "validation", referent="lab-data")
@pytest.mark.skip(reason="no reference data")
def test_skips():
    pass


@vv.case("kernel-sum", "code-verification")
@pytest.mark.xfail(reason="known limitation")
def test_xfails():
    assert False


@vv.regression
def test_regression():
    assert True


@vv.seam("producer", "consumer", case="kernel-sum")
def test_seam():
    assert True
"""


def missing_xdist_action(environ):
    return "fail" if environ.get("REQUIRE_XDIST") == "1" else "skip"


def require_xdist():
    if importlib.util.find_spec("xdist") is None:
        if missing_xdist_action(os.environ) == "fail":
            pytest.fail("pytest-xdist is required when REQUIRE_XDIST=1")
        pytest.skip("pytest-xdist is not installed")


@pytest.mark.parametrize(
    ("environ", "expected"),
    [({}, "skip"), ({"REQUIRE_XDIST": "0"}, "skip"), ({"REQUIRE_XDIST": "1"}, "fail")],
)
def test_missing_xdist_action(environ, expected):
    assert missing_xdist_action(environ) == expected


@pytest.mark.parametrize("required", [False, True])
def test_missing_xdist_skips_unless_required(monkeypatch, required):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setenv("REQUIRE_XDIST", "1" if required else "0")
    expected = pytest.fail.Exception if required else pytest.skip.Exception
    # Catch either outcome so an erroneous skip fails this test instead of
    # skipping the test itself when xdist is required.
    with pytest.raises((pytest.fail.Exception, pytest.skip.Exception)) as caught:
        require_xdist()
    assert isinstance(caught.value, expected)
    assert "pytest-xdist" in str(caught.value)


@pytest.mark.parametrize(
    ("worse", "better"),
    [
        ("error", "failed"),
        ("error", "xpassed"),
        ("error", "xfailed"),
        ("error", "passed"),
        ("error", "skipped"),
        ("failed", "xpassed"),
        ("failed", "xfailed"),
        ("failed", "passed"),
        ("failed", "skipped"),
        ("xpassed", "xfailed"),
        ("xpassed", "passed"),
        ("xpassed", "skipped"),
        ("xfailed", "passed"),
        ("xfailed", "skipped"),
        ("passed", "skipped"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_outcome_folding_keeps_the_worst_report(worse, better, reverse):
    outcomes = (better, worse) if reverse else (worse, better)
    current = None
    for outcome in outcomes:
        report = SimpleNamespace(
            when="teardown" if outcome == "error" else "call",
            failed=outcome in ("error", "failed"),
            passed=outcome in ("passed", "xpassed"),
            skipped=outcome in ("skipped", "xfailed"),
        )
        if outcome in ("xpassed", "xfailed"):
            report.wasxfail = "known limitation"
        folded = _outcome(report, current)
        if folded is not None:
            current = folded
    assert current == worse


def test_xdist_each_keeps_a_failure_from_one_worker(pytester, tmp_path):
    require_xdist()
    pytester.makepyfile(
        test_cases="""
import os
import time
import ineedvalidation as vv

@vv.case("kernel-sum", "code-verification")
def test_worker_outcome():
    if os.environ.get("PYTEST_XDIST_WORKER") == "gw1":
        time.sleep(0.5)
    assert os.environ.get("PYTEST_XDIST_WORKER") != "gw0"
"""
    )
    out = tmp_path / "evidence.json"
    result = pytester.runpytest_subprocess(
        "-n", "2", "--dist", "each", "--vv-evidence", str(out)
    )
    result.assert_outcomes(passed=1, failed=1)
    records = json.loads(out.read_text())["tests"]
    assert len(records) == 1
    assert records[0]["outcome"] == "failed"


@pytest.mark.parametrize("crash", [False, True])
def test_xdist_warns_only_when_no_worker_delivers_declarations(
    pytester, tmp_path, crash
):
    require_xdist()
    pytester.makepyfile(
        test_cases=f"""
import os
import ineedvalidation as vv

pytestmark = vv.case("kernel-sum", "code-verification")

def test_first():
    if {crash!r}:
        os._exit(1)

def test_remaining():
    pass
"""
    )
    out = tmp_path / "evidence.json"
    result = pytester.runpytest_subprocess(
        "-n",
        "1" if crash else "2",
        "--max-worker-restart",
        "0",
        "--vv-evidence",
        str(out),
    )
    ledger = json.loads(out.read_text())
    assert ledger["mode"] == "run"
    if crash:
        assert result.ret == pytest.ExitCode.TESTS_FAILED
        assert len(ledger["tests"]) < 2
        result.stdout.fnmatch_lines([f"*{out}*may be incomplete*"])
        assert "no worker delivered its declarations payload" in result.stdout.str()
    else:
        result.assert_outcomes(passed=2)
        assert len(ledger["tests"]) == 2
        assert "may be incomplete" not in result.stdout.str()
        assert "may be incomplete" not in result.stderr.str()


@pytest.fixture
def serial_and_parallel_ledgers(pytester, tmp_path):
    require_xdist()
    pytester.makepyfile(test_cases=SIX_TESTS)
    pytester.makefile(".toml", pyproject=TOML)
    ledgers = []
    for name, args in (("serial", []), ("parallel", ["-n", "2"])):
        out = tmp_path / f"{name}.json"
        result = pytester.runpytest_subprocess(*args, "--vv-evidence", str(out))
        result.assert_outcomes(passed=3, failed=1, skipped=1, xfailed=1)
        ledgers.append(json.loads(out.read_text()))
    return ledgers


def test_serial_and_xdist_records_are_equal(serial_and_parallel_ledgers):
    serial, parallel = serial_and_parallel_ledgers

    def records(ledger):
        return {
            (
                r["nodeid"],
                r["case"],
                r["evidence"],
                r["srq"],
                tuple(r["seam"]) if r["seam"] else None,
                r["outcome"],
            )
            for r in ledger["tests"]
        }

    serial_records, parallel_records = records(serial), records(parallel)
    assert len(serial_records) == 6
    assert len(parallel_records) == 6
    assert serial_records == parallel_records
    # Optional metadata must also survive report serialization.
    assert serial["tests"] == parallel["tests"]


def test_xdist_records_each_nodeid_once(serial_and_parallel_ledgers):
    _, parallel = serial_and_parallel_ledgers
    nodeids = [r["nodeid"] for r in parallel["tests"]]
    assert len(nodeids) == 6
    assert len(nodeids) == len(set(nodeids))


def test_serial_and_xdist_results_are_equal(serial_and_parallel_ledgers):
    serial, parallel = serial_and_parallel_ledgers
    serial_results = {
        r["nodeid"]: r["results"] for r in serial["tests"] if r["results"]
    }
    parallel_results = {
        r["nodeid"]: r["results"] for r in parallel["tests"] if r["results"]
    }
    assert serial_results
    assert parallel_results
    assert serial_results == parallel_results


@pytest.mark.parametrize("args", [["-x"], ["-k", "remaining"]])
def test_serial_and_xdist_include_unreported_declarations(pytester, tmp_path, args):
    require_xdist()
    pytester.makepyfile(
        test_cases="""
import time
import pytest
import ineedvalidation as vv

pytestmark = vv.case("kernel-sum", "code-verification", basis="floating-point")

def test_first():
    assert False

@pytest.mark.parametrize("index", range(20))
def test_remaining(index):
    time.sleep(0.01)
"""
    )
    declarations = []
    for name, workers in (("serial", []), ("parallel", ["-n", "2"])):
        out = tmp_path / f"{name}.json"
        result = pytester.runpytest_subprocess(
            *workers, *args, "--vv-evidence", str(out)
        )
        if "-x" in args:
            assert result.parseoutcomes()["failed"] == 1
            assert result.ret == (
                pytest.ExitCode.INTERRUPTED if workers else pytest.ExitCode.TESTS_FAILED
            )
        else:
            result.assert_outcomes(passed=20)
            assert result.ret == pytest.ExitCode.OK
        ledger = json.loads(out.read_text())
        assert ledger["mode"] == "run"
        records = ledger["tests"]
        assert len(records) == 21
        assert len({record["nodeid"] for record in records}) == 21
        assert any(record["outcome"] is None for record in records)
        first = next(r for r in records if r["nodeid"].endswith("::test_first"))
        assert first["outcome"] == ("failed" if "-x" in args else None)
        declarations.append([{**record, "outcome": None} for record in records])
    assert declarations[0] == declarations[1]


@pytest.mark.parametrize("phase", ["setup", "call"])
def test_worker_crash_is_an_error_and_keeps_unreported_tests(pytester, tmp_path, phase):
    require_xdist()
    pytester.makepyfile(
        test_cases=f"""
import os
import time
import pytest
import ineedvalidation as vv

pytestmark = vv.case("kernel-sum", "code-verification")

@pytest.fixture
def crash_setup():
    if {phase!r} == "setup":
        os._exit(1)

def test_crashes(crash_setup):
    os._exit(1)

@pytest.mark.parametrize("index", range(20))
def test_remaining(index):
    time.sleep(0.05)
"""
    )
    out = tmp_path / "evidence.json"
    result = pytester.runpytest_subprocess(
        "-n", "2", "-x", "--max-worker-restart=0", "--vv-evidence", str(out)
    )
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*worker*crashed*test_cases.py::test_crashes*"])
    records = json.loads(out.read_text())["tests"]
    assert len(records) == 21
    by_nodeid = {record["nodeid"]: record for record in records}
    assert len(by_nodeid) == 21
    assert by_nodeid["test_cases.py::test_crashes"]["outcome"] == "error"
    assert any(record["outcome"] is None for record in records)


@pytest.mark.parametrize("parallel", [False, True])
def test_body_failure_and_fixture_errors(pytester, tmp_path, parallel):
    if parallel:
        require_xdist()
    pytester.makepyfile(
        test_errors="""
import pytest
import ineedvalidation as vv

pytestmark = vv.case("kernel-sum", "code-verification")

@pytest.fixture
def broken_teardown():
    yield
    raise RuntimeError("teardown failed")

@pytest.fixture
def broken_setup():
    raise RuntimeError("setup failed")

def test_body_failure():
    assert False

def test_teardown_error(broken_teardown):
    pass

def test_setup_error(broken_setup):
    pass
"""
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest_subprocess(
        *(["-n", "2"] if parallel else []), "--vv-evidence", str(out)
    )
    result.assert_outcomes(passed=1, failed=1, errors=2)
    records = json.loads(out.read_text())["tests"]
    assert len(records) == 3
    assert {r["nodeid"].split("::")[-1]: r["outcome"] for r in records} == {
        "test_body_failure": "failed",
        "test_teardown_error": "error",
        "test_setup_error": "error",
    }


def test_worker_does_not_write_evidence(tmp_path):
    from ineedvalidation.plugin import EvidenceCollector

    out = tmp_path / "evidence.json"
    config = SimpleNamespace(
        workerinput={},
        rootpath=tmp_path,
        option=SimpleNamespace(collectonly=False),
        getoption=lambda name: str(out) if name == "--vv-evidence" else None,
    )
    collector = EvidenceCollector(config, (None, {}))
    collector.pytest_sessionfinish(None, 0)
    assert not out.exists()


@pytest.mark.parametrize("worker", [False, True])
def test_only_worker_phase_reports_carry_the_full_declaration(
    pytester, tmp_path, worker
):
    from ineedvalidation.plugin import DECLARATION_PROPERTY

    pytester.makepyfile(test_cases=SIX_TESTS)
    pytester.makefile(".toml", pyproject=TOML)
    pytester.makeconftest(f"""
def pytest_configure(config):
    if {worker!r}:
        config.workerinput = {{}}
        config.workeroutput = {{}}

def pytest_collection_modifyitems(items):
    for item in items:
        item.user_properties.append(("custom-property", "preserved"))

def pytest_sessionfinish(session):
    import json
    collector = session.config.pluginmanager.get_plugin("vv-evidence")
    records = [record.to_dict() for record in collector.records.values()]
    (session.config.rootpath / "reports.json").write_text(json.dumps(records))
""")
    out = tmp_path / "evidence.json"
    result = pytester.inline_run("--vv-evidence", str(out))
    reports = result.getreports("pytest_runtest_logreport")
    records = {
        r["nodeid"]: r for r in json.loads((pytester.path / "reports.json").read_text())
    }
    assert len(records) == 6
    assert len(reports) == 17  # A setup skip has no call phase.
    for report in reports:
        properties = dict(report.user_properties)
        assert properties["custom-property"] == "preserved"
        if worker:
            assert properties[DECLARATION_PROPERTY] == {
                **records[report.nodeid],
                "outcome": None,
                "results": [],
            }
        else:
            assert DECLARATION_PROPERTY not in properties


def test_serial_junit_has_no_declaration_property(pytester, tmp_path):
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    junit = tmp_path / "junit.xml"
    out = tmp_path / "evidence.json"
    result = pytester.runpytest_subprocess(
        "--junitxml", str(junit), "--vv-evidence", str(out)
    )
    result.assert_outcomes(passed=3, skipped=1)
    root = ET.parse(junit).getroot()
    assert len(root.findall(".//testcase")) == 4
    assert not any(
        prop.attrib["name"].startswith("ineedvalidation")
        for prop in root.findall(".//property")
    )
    assert len(json.loads(out.read_text())["tests"]) == 3


@pytest.mark.parametrize("relative_root", [".", "sub/dir"])
def test_root_is_relative_to_git_top_level(pytester, tmp_path, relative_root):
    subprocess.run(["git", "init", str(pytester.path)], check=True, capture_output=True)
    suite = pytester.path / relative_root
    suite.mkdir(parents=True, exist_ok=True)
    (suite / "pyproject.toml").write_text(TOML)
    (suite / "test_marked.py").write_text(MARKED)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest_subprocess(
        str(suite), "--rootdir", str(suite), "--vv-evidence", str(out)
    )
    result.assert_outcomes(passed=3, skipped=1)
    data = json.loads(out.read_text())
    assert data["root"] == relative_root
    assert EvidenceFile.from_dict(data).root == relative_root


def test_root_is_null_outside_git_repository(pytester, tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(pytester.path.parent))
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest_subprocess("--vv-evidence", str(out))
    result.assert_outcomes(passed=3, skipped=1)
    assert json.loads(out.read_text())["root"] is None


def test_1_0_ledger_missing_mode_reads_as_run():
    data = json.loads((HIER.parent / "ledger-1.0.json").read_text())
    assert "mode" not in data
    loaded = EvidenceFile.from_dict(data)
    assert loaded.mode == "run"
    assert loaded.to_dict()["mode"] == "run"


def test_1_0_ledger_missing_root_reads_as_null():
    data = json.loads((HIER.parent / "ledger-1.0.json").read_text())
    assert "root" not in data
    loaded = EvidenceFile.from_dict(data)
    assert loaded.root is None
    assert loaded.to_dict()["root"] is None


def result_entry(**values):
    return {
        "value": None,
        "interval": None,
        "reference": None,
        "artifact": None,
        "manifest": None,
        "point": {},
        **values,
    }


def test_vv_record_keeps_two_calls_in_order(pytester, tmp_path):
    pytester.makepyfile(
        test_results="""
import ineedvalidation as vv

@vv.case("kernel-sum", "code-verification")
def test_results(vv_record):
    vv_record(value=0.25, interval=(0.2, 0.3), reference=0.25, spacing=0.1)
    vv_record(value=0.125, interval=[0.1, 0.15], reference=0.125, spacing=0.05)
"""
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.inline_run("--vv-evidence", str(out))
    result.assertoutcome(passed=1)
    expected = [
        result_entry(
            value=0.25, interval=[0.2, 0.3], reference=0.25, point={"spacing": 0.1}
        ),
        result_entry(
            value=0.125, interval=[0.1, 0.15], reference=0.125, point={"spacing": 0.05}
        ),
    ]
    call = next(
        r for r in result.getreports("pytest_runtest_logreport") if r.when == "call"
    )
    properties = [
        entry for name, entry in call.user_properties if name == RESULT_PROPERTY
    ]
    assert properties == expected
    data = json.loads(out.read_text(), parse_constant=reject_constant)
    assert len(data["tests"]) == 1
    assert data["tests"][0]["results"] == expected
    assert EvidenceFile.from_dict(data).to_dict() == data


@pytest.mark.parametrize("collect", [False, True])
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ('value=float("nan")', "value must be a finite number"),
        ("interval=(2, 1)", "interval must have lo <= hi"),
        ("interval=(1, 2, 3)", "interval must contain exactly two endpoints"),
        ('artifact="missing.txt"', "FileNotFoundError"),
        ('manifest="missing.json"', "FileNotFoundError"),
    ],
)
def test_vv_record_invalid_input_fails_in_the_body(
    pytester, tmp_path, arguments, message, collect
):
    pytester.makepyfile(
        test_invalid=f"""
import ineedvalidation as vv

@vv.case("kernel-sum", "code-verification")
def test_invalid(vv_record):
    vv_record(value=1)
    vv_record({arguments})
"""
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest(*(["--vv-evidence", str(out)] if collect else []))
    result.assert_outcomes(failed=1)
    assert message in result.stdout.str()
    if collect:
        data = json.loads(out.read_text(), parse_constant=reject_constant)
        assert len(data["tests"]) == 1
        record = data["tests"][0]
        assert record["outcome"] == "failed"
        assert record["results"] == [result_entry(value=1)]
    else:
        assert not out.exists()


@pytest.mark.parametrize("keyword", ["artifact", "manifest"])
def test_vv_record_hashes_file_contents_at_each_call(pytester, tmp_path, keyword):
    contents = [b"first contents\n", b"edited contents\n"]
    pytester.makepyfile(
        test_hash=f"""
from pathlib import Path
import ineedvalidation as vv

@vv.case("kernel-sum", "code-verification")
def test_hash(vv_record, request, monkeypatch, tmp_path):
    path = request.config.rootpath / "data" / "result.txt"
    path.parent.mkdir()
    monkeypatch.chdir(tmp_path)
    path.write_bytes({contents[0]!r})
    vv_record({keyword}=Path("data/result.txt"))
    path.write_bytes({contents[1]!r})
    vv_record({keyword}="data/result.txt")
"""
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    entries = json.loads(out.read_text())["tests"][0]["results"]
    assert entries == [
        result_entry(
            **{
                keyword: {
                    "path": "data/result.txt",
                    "sha256": hashlib.sha256(b).hexdigest(),
                }
            }
        )
        for b in contents
    ]
    assert entries[0][keyword]["sha256"] != entries[1][keyword]["sha256"]


def test_vv_record_keeps_results_when_assertion_fails(pytester, tmp_path):
    pytester.makepyfile(
        test_failure="""
import ineedvalidation as vv

@vv.case("kernel-sum", "code-verification")
def test_failure(vv_record):
    vv_record(value=0.5, reference=1)
    assert False, "measured result differs"
"""
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(failed=1)
    record = json.loads(out.read_text())["tests"][0]
    assert record["outcome"] == "failed"
    assert record["results"] == [result_entry(value=0.5, reference=1)]


def test_vv_record_without_evidence_records_nothing(pytester):
    pytester.makepyfile(
        test_disabled="""
from ineedvalidation.plugin import RESULT_PROPERTY

def test_disabled(vv_record, request):
    vv_record(value=1, interval=(0, 2), reference=1, spacing=0.5)
    assert not any(name == RESULT_PROPERTY for name, _ in request.node.user_properties)
"""
    )
    pytester.makefile(".toml", pyproject=TOML)
    before = set(pytester.path.rglob("*.json"))
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert set(pytester.path.rglob("*.json")) == before


def test_vv_record_snapshots_mutable_inputs_and_allows_empty_calls(pytester, tmp_path):
    pytester.makepyfile(
        test_snapshot="""
import ineedvalidation as vv

@vv.case("kernel-sum", "code-verification")
def test_snapshot(vv_record):
    interval = [0, 1]
    reference = {"label": "exact solution", "value": 0.5}
    samples = [0.25, 0.5]
    vv_record(value=0.5, interval=interval, reference=reference, samples=samples)
    interval[1] = 2
    reference["value"] = 1
    samples.append(0.75)
    vv_record()
"""
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=1)
    assert json.loads(out.read_text())["tests"][0]["results"] == [
        result_entry(
            value=0.5,
            interval=[0, 1],
            reference={"label": "exact solution", "value": 0.5},
            point={"samples": [0.25, 0.5]},
        ),
        result_entry(),
    ]


def test_1_0_ledger_missing_results_reads_as_empty_list():
    data = json.loads((HIER.parent / "ledger-1.0.json").read_text())
    assert "results" not in data["tests"][0]
    loaded = EvidenceFile.from_dict(data)
    assert loaded.tests[0].results == []
    assert loaded.to_dict()["tests"][0]["results"] == []
