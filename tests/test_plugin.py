import json

pytest_plugins = ["pytester"]

MARKED = """
import pytest

import ineedvalidation as inv


@inv.case("kernel-sum", "A", srq="summation error")
def test_passes():
    assert True


@inv.case("kernel-sum", "B", ref="othercode")
def test_skips():
    pytest.skip("no reference data")


@inv.regression
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
    result = pytester.runpytest("--inv-evidence", str(out))
    result.assert_outcomes(passed=3, skipped=1)
    data = json.loads(out.read_text())
    assert data["library"] == "widgetlib"
    by_name = {r["nodeid"].split("::")[-1]: r for r in data["tests"]}
    assert set(by_name) == {"test_passes", "test_skips", "test_golden"}
    assert by_name["test_passes"]["case"] == "kernel-sum"
    assert by_name["test_passes"]["tier"] == "A"
    assert by_name["test_passes"]["srq"] == "summation error"
    assert by_name["test_passes"]["outcome"] == "passed"
    assert by_name["test_skips"]["outcome"] == "skipped"
    assert by_name["test_skips"]["ref"] == "othercode"
    assert by_name["test_golden"]["tier"] is None


def test_collect_only_leaves_outcomes_null(pytester, tmp_path):
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    pytester.runpytest("--collect-only", "--inv-evidence", str(out))
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
            + '"slow_tests/" = { case = "bench-loop", tier = "D" }\n'
        ),
    )
    out = tmp_path / "evidence.json"
    pytester.runpytest("--inv-evidence", str(out))
    data = json.loads(out.read_text())
    assert data["tests"][0]["case"] == "bench-loop"
    assert data["tests"][0]["tier"] == "D"
    assert data["tests"][0]["outcome"] == "passed"


def test_the_longest_prefix_wins():
    from ineedvalidation.plugin import match_default

    defaults = {
        "tests/": {"case": "broad", "tier": "A"},
        "tests/deep/": {"case": "narrow", "tier": "B"},
    }
    assert match_default("tests/test_a.py", defaults)["case"] == "broad"
    assert match_default("tests/deep/test_b.py", defaults)["case"] == "narrow"
    assert match_default("other/test_c.py", defaults) is None


def test_a_marker_overrides_a_path_default(pytester, tmp_path):
    pytester.makepyfile(
        **{
            "slow_tests/test_marked": (
                "import ineedvalidation as inv\n\n\n"
                '@inv.case("mixer", "C")\n'
                "def test_marked():\n    assert True\n"
            )
        }
    )
    pytester.makefile(
        ".toml",
        pyproject=(
            TOML
            + "[tool.ineedvalidation.defaults]\n"
            + '"slow_tests/" = { case = "bench-loop", tier = "D" }\n'
        ),
    )
    out = tmp_path / "evidence.json"
    pytester.runpytest("--inv-evidence", str(out))
    data = json.loads(out.read_text())
    assert data["tests"][0]["case"] == "mixer"
    assert data["tests"][0]["tier"] == "C"


def test_module_level_pytestmark_is_honoured(pytester, tmp_path):
    pytester.makepyfile(
        test_mod=(
            "import ineedvalidation as inv\n\n"
            'pytestmark = inv.case("mixer", "C", ref="grid")\n\n\n'
            "def test_one():\n    assert True\n"
        )
    )
    pytester.makefile(".toml", pyproject=TOML)
    out = tmp_path / "evidence.json"
    pytester.runpytest("--inv-evidence", str(out))
    data = json.loads(out.read_text())
    assert data["tests"][0]["case"] == "mixer"
    assert data["tests"][0]["tier"] == "C"
    assert data["tests"][0]["ref"] == "grid"


def test_no_evidence_file_is_written_without_the_option(pytester, tmp_path):
    pytester.makepyfile(test_marked=MARKED)
    pytester.makefile(".toml", pyproject=TOML)
    pytester.runpytest()
    assert not (tmp_path / "evidence.json").exists()
