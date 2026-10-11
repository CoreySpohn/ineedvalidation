# Marking a test

A test declares what it demonstrates with one of three decorators. Each is a thin
wrapper over a pytest marker whose arguments are validated at decoration time, so a
bad evidence kind or a misspelled keyword fails when the module is imported rather than being
ignored at collection.

```python
import ineedvalidation as vv


@vv.case("free-space-propagation", "code-verification", srq="on-axis intensity")
def test_matches_closed_form():
    ...


@vv.case(
    "free-space-propagation", "solution-verification",
    refined_parameter="grid-spacing", reference_model="full-resolution propagation",
)
def test_second_order_in_the_step():
    ...


@vv.case(
    "free-space-propagation", "uncertainty-quantification",
    alternative="alternative propagation model",
)
def test_sensitivity_to_model_choice():
    ...


@vv.seam("optics", "detector", case="detector-frame")
def test_photon_scale_anchor():
    ...


@vv.regression
def test_frozen_output():
    ...
```

## The arguments

`case` names a physical case as a plain slug. It carries no level prefix and no
hierarchy identifier: a node note lists the slugs it owns, so the same slug can be
exercised by tests in several repositories.

`evidence` is the kind of evidence the test produces. The kinds are spelled out
rather than lettered, so a marked test reads without a key and a grep for
`validation` does not also return every test that merely converges.

| Kind | Meaning |
|---|---|
| `code-verification` | Exact solutions, identities, property invariants, sign and seam anchors. |
| `solution-verification` | Convergence in an ordered discretization parameter. |
| `cross-code-benchmark` | Agreement with an independently developed code. Never validation. |
| `validation` | Comparison against measured data, and nothing else. |
| `uncertainty-quantification` | Segregated aleatory and epistemic propagation; sensitivity analysis. |

Note that `cross-code-benchmark` is a kind of evidence, while `benchmark` is also a
level of the validation hierarchy (hardware with two or three coupled effects). The
two are unrelated, which is why neither is abbreviated.

`srq` is optional and names the system response quantity the test measures. When the
declarations are linted against a hierarchy, the value must be one the node lists.

Five optional keywords each belong to exactly one kind, and using one with the
wrong kind raises: `reference_code` for a cross-code benchmark, `refined_parameter`
and `reference_model` for solution verification, `referent` for validation, and
`alternative` for uncertainty quantification. Each names what it holds,
so a value filed under the wrong one fails at import rather than sitting unnoticed
in the ledger.

`reference_model` names a reference computation of the same governing probabilistic
model and assumptions as the reduced model under test, with its own numerical error
quantified (`acceptance.reference_error`); a model with different physics is not
a reference model, and that comparison is uncertainty quantification with
`alternative`.

`alternative` names the alternative model compared with the baseline; such a
comparison is a sensitivity analysis, not an estimate of model-form uncertainty.

`basis` describes how the test establishes its criterion. Its allowed values are
`floating-point`, `exact-algebra`, `monte-carlo`, `coverage`,
`simulation-based-calibration`, `mutation`, `spike`, `literature` and `equivalence`.
It is independent of the evidence kind.

`acceptance` is an optional dictionary describing the criterion. Its allowed keys
are `metric`, `tolerance`, `margin`, `rule`, `domain`, `draws`, `sigma`,
`reference_error` and `registered`. Values may be strings, booleans, finite integers
or floats, or lists of those values. Nested dictionaries, nested lists, null values,
NaN and infinity are rejected. `registered` must instead be a string containing a
valid calendar date in exactly `YYYY-MM-DD` form.

```python
@vv.case(
    "kernel-sum", "code-verification", basis="floating-point",
    acceptance={"metric": "absolute error", "tolerance": 1e-12},
)
def test_sum_matches_exact_value():
    ...


@vv.case(
    "free-space-propagation", "solution-verification",
    reference_model="full-resolution propagation", basis="equivalence",
    acceptance={"reference_error": 1e-8, "registered": "2026-09-01"},
)
def test_matches_reference_computation():
    ...
```

Neither keyword is required at decoration time. `lint --require-metadata` checks
for missing basis, a reference model without `acceptance.reference_error`, and a
registered criterion that postdates the run. Regression records are exempt.

`seam(producer, consumer, case=...)` marks an absolute-scale anchor test across an
interface between two libraries. Shape, ratio and fitted-scale tests are scale blind,
so an interface that is only covered by those can carry a constant factor for a long
time without any test noticing. The lint checks that the two libraries own nodes that
are actually coupled.

`regression` marks a frozen or golden reference. Such a test is recorded but is
excluded from every kind, so it cannot inflate the evidence for a case.

## Tagging by path

Tagging every test by hand is not worth the effort when a whole directory exercises
one case. A table in the repository's `pyproject.toml` assigns a case and an evidence kind by
path prefix:

```toml
[tool.ineedvalidation]
library = "mylib"

[tool.ineedvalidation.defaults]
"tests/validation/" = { case = "free-space-propagation", evidence = "cross-code-benchmark" }
"tests/test_kernels.py" = { case = "kernel-sum", evidence = "code-verification", basis = "floating-point", acceptance = { metric = "absolute error", tolerance = 1e-12 } }
"tests/convergence/" = { case = "free-space-propagation", evidence = "solution-verification", reference_model = "full-resolution propagation" }
"tests/sensitivity/" = { case = "free-space-propagation", evidence = "uncertainty-quantification", alternative = "alternative propagation model" }
```

The longest matching prefix wins. An explicit marker, on the function or in a module
level `pytestmark`, overrides the default entirely, including optional keyword
fields such as `basis` and `acceptance`; no fields are merged. A marker that omits
them records null even when the path default supplies them. Every defaults entry
is validated at pytest configuration time with the same rules as the decorator,
even for an unused prefix or a run without `--vv-evidence`. An invalid entry raises
`pytest.UsageError` naming its prefix. `library` names the repository in
the evidence file; without it the name of the root directory is used.

## Writing the evidence file

```console
$ pytest --vv-evidence evidence/mylib.json
```

The file lists every marked or defaulted test with the outcome it reached:

```json
{"library": "mylib", "commit": "abc1234", "recorded": "2026-09-04T15:00:00Z",
 "mode": "run", "root": ".",
 "tests": [{"nodeid": "tests/test_kernels.py::test_sum", "case": "kernel-sum",
            "evidence": "code-verification", "srq": "summation error",
            "reference_code": null, "refined_parameter": null, "referent": null,
            "reference_model": null, "alternative": null,
            "basis": "floating-point",
            "acceptance": {"metric": "absolute error", "tolerance": 1e-12},
            "seam": null, "outcome": "passed", "results": []}]}
```

## Recording results in the test body

The plugin provides the `vv_record` fixture. Its callable has the signature
`vv_record(value=None, interval=None, reference=None, artifact=None, manifest=None, **point)`.
Each call appends one result, in call order, to the marked or defaulted test's
`results` list. Results remain in the ledger when a later assertion fails.

```python
@vv.case("kernel-sum", "code-verification")
def test_sum(vv_record):
    vv_record(value=0.25, interval=(0.2, 0.3), reference=0.25, spacing=0.1)
    vv_record(value=0.125, spacing=0.05, artifact="results/sum.txt")
```

Each entry contains `value`, `interval`, `reference`, `artifact`, `manifest` and
`point`. Omitted arguments are null, and extra keywords form the `point` dictionary:

```json
{"value": 0.25, "interval": [0.2, 0.3], "reference": 0.25,
 "artifact": null, "manifest": null, "point": {"spacing": 0.1}}
```

`value` must be a finite integer or float. An interval is a list or tuple of exactly
two finite numbers, with the lower endpoint at most the upper endpoint. `reference`
and point coordinates must be JSON serializable, with no NaN or infinity. Each call
snapshots its input so subsequent changes to a mutable argument do not alter it.

`artifact` and `manifest` accept strings or path objects identifying existing files
relative to the pytest rootdir, even when the test changes its working directory.
The paths must remain within that root. Each is recorded as
`{"path": "results/sum.txt", "sha256": "..."}`, hashing the file's bytes at the time
of the call. Neither file is copied or interpreted.

Invalid arguments raise at the call in the test body, producing a `failed` outcome
and adding no invalid entry. Without `--vv-evidence` the fixture still validates
arguments and file paths, but records nothing and writes no ledger. Tests that make
no calls have an empty `results` list. Worker reports carry results to the controller
under pytest-xdist.

## Collection modes and parallel runs

Under `--collect-only` the file has `mode: "collect-only"` and every outcome is
`null`, which is the cheap way to see what a repository claims without running
anything. In a real run `mode` is `"run"` and the outcomes are filled in,
and the difference matters: evidence that passed is demonstrated, while evidence that
was marked and then skipped is only claimed. The package never decides whether a test
without its reference data should fail or skip; that policy stays with the repository.
Use `--vv-library` to override the recorded name for one run.

Collection also supports pytest-xdist:

```console
$ pytest -n 2 --vv-evidence evidence/mylib.json
```

Each worker collects complete declarations, carries them on test reports, and
sends the full collection to the controller when it shuts down. Only the controller
writes the ledger, with one record per declared node id, including deselected and
unrun tests with a `null` outcome. Outcomes include setup, call and teardown: an
assertion in the test body is `failed`, and a fixture error in setup or after a
passing body is `error`. A worker crash reported by xdist is also `error`, including
a crash before setup reports. A surviving worker supplies the declarations when
another worker crashes. Serial reports and serial JUnit XML carry no declaration
property, while under xdist JUnit XML may include the `ineedvalidation.declaration`
property carried by worker reports.

`root` records the pytest rootdir relative to the Git repository's top level, using
forward slashes: `"."` for the repository root or, for example, `"sub/dir"` for a
nested suite. Outside a Git repository it is `null`.

A 1.0 ledger still loads. Missing keyword fields, including `basis` and
`acceptance`, read as null; missing `mode` reads as `"run"` and missing `root` as
null. Missing `results` reads as an empty list. The new metadata does not change the
evidence summary or plain lint output for existing ledgers.
