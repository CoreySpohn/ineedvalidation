import json

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


def test_evidence_records_outcomes(pytester, tmp_path):
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    result = pytester.runpytest("--vv-evidence", str(out))
    result.assert_outcomes(passed=3, skipped=1)
    data = json.loads(out.read_text())
    assert data["library"] == "widgetlib"
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
