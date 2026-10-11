import json
import subprocess
import sys
from dataclasses import asdict, replace

import pytest
from test_nodes import HIER

from ineedvalidation import evidence, nodes
from ineedvalidation.schema import EvidenceFile


def summary():
    return evidence.summarize(
        nodes.load(HIER / "nodes"), evidence.load_dir(HIER / "evidence")
    )


def test_load_dir_reads_every_evidence_file():
    files = evidence.load_dir(HIER / "evidence")
    assert [f.library for f in files] == ["widgetlib"]
    assert len(files[0].tests) == 4


def test_summarize_separates_demonstrated_from_claimed():
    bench = summary()["benchmark-bench"]
    assert bench.demonstrated == ("validation",)
    assert bench.claimed == ("cross-code-benchmark",)
    assert bench.libraries == ("widgetlib",)
    assert bench.srqs_covered == ("loop residual",)
    assert bench.tests == 2
    assert bench.skipped == 1
    assert bench.computed is True


def test_a_node_with_no_tests_falls_back_to_the_declared_fields():
    front = summary()["system-front"]
    assert front.computed is False
    assert front.demonstrated == ("code-verification",)
    assert front.libraries == ("widgetlib",)


def test_unfiled_cases_are_listed_with_their_libraries():
    unfiled = evidence.unfiled_cases(
        nodes.load(HIER / "nodes"), evidence.load_dir(HIER / "evidence")
    )
    assert unfiled == {"not-filed": ("widgetlib",)}


def test_records_round_trip_through_json():
    files = evidence.load_dir(HIER / "evidence")
    assert type(files[0]).from_dict(files[0].to_dict()) == files[0]


def test_a_1_0_ledger_loads():
    data = json.loads((HIER.parent / "ledger-1.0.json").read_text())
    loaded = EvidenceFile.from_dict(data)
    assert loaded.library == "widgetlib"
    assert loaded.commit == "0123456"
    assert loaded.recorded == "2026-09-04T15:00:00Z"
    assert len(loaded.tests) == 1
    record = loaded.tests[0]
    assert record.nodeid == "tests/test_kernel.py::test_sum"
    assert record.case == "kernel-sum"
    assert record.evidence == "code-verification"
    assert record.outcome == "passed"


@pytest.mark.parametrize(
    "keyword",
    [
        "srq",
        "reference_code",
        "refined_parameter",
        "referent",
        "reference_model",
        "alternative",
    ],
)
def test_missing_keyword_field_reads_as_null(keyword):
    data = json.loads((HIER.parent / "ledger-1.0.json").read_text())
    assert keyword not in data["tests"][0]
    loaded = EvidenceFile.from_dict(data)
    assert getattr(loaded.tests[0], keyword) is None
    assert loaded.to_dict()["tests"][0][keyword] is None


def test_summarize_matches_1_0_golden():
    serialized = (
        json.dumps(
            {key: asdict(value) for key, value in summary().items()},
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    assert serialized == (HIER.parent / "golden/hierarchy-summary.json").read_bytes()


def test_plain_lint_matches_1_0_golden():
    result = subprocess.run(
        [sys.executable, "-m", "ineedvalidation.cli", "lint", str(HIER)],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stderr == b""
    assert result.stdout == (HIER.parent / "golden/hierarchy-lint.txt").read_bytes()


@pytest.mark.parametrize("include_run", [False, True])
def test_collect_only_records_do_not_count_as_evidence(include_run):
    loaded = nodes.load(HIER / "nodes")
    ledger = evidence.load_dir(HIER / "evidence")[0]
    collected = replace(ledger, library="collection", mode="collect-only")
    files = [collected, ledger] if include_run else [collected]
    summaries = evidence.summarize(loaded, files)
    bench = summaries["benchmark-bench"]
    assert bench.tests == (2 if include_run else 0)
    assert bench.computed is include_run
    assert bench.libraries == ("widgetlib",)
