import json

import pytest

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
def test_explicit_marker_replaces_all_default_fields(pytester, tmp_path, defaults):
    pytester.makepyfile(
        test_model=(
            "import ineedvalidation as vv\n\n"
            '@vv.case("explicit-case", "code-verification")\n'
            "def test_model():\n    assert True\n"
        )
    )
    pytester.makefile(
        ".toml",
        pyproject=(
            TOML
            + '[tool.ineedvalidation.defaults."test_model.py"]\n'
            + 'case = "default-case"\nsrq = "default response"\n'
            + defaults
        ),
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
