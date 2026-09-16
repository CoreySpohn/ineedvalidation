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
    "free-space-propagation", "solution-verification", refined_parameter="grid-spacing"
)
def test_second_order_in_the_step():
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

Three optional keywords each belong to exactly one kind, and using one with the
wrong kind raises: `reference_code` for a cross-code benchmark, `refined_parameter`
for solution verification, and `referent` for validation. Each names what it holds,
so a value filed under the wrong one fails at import rather than sitting unnoticed
in the ledger.

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
"tests/test_kernels.py" = { case = "kernel-sum", evidence = "code-verification" }
```

The longest matching prefix wins. An explicit marker, on the function or in a module
level `pytestmark`, overrides the default entirely. `library` names the repository in
the evidence file; without it the name of the root directory is used.

## Writing the evidence file

```console
$ pytest --vv-evidence evidence/mylib.json
```

The file lists every marked or defaulted test with the outcome it reached:

```json
{"library": "mylib", "commit": "abc1234", "recorded": "2026-09-04T15:00:00Z",
 "tests": [{"nodeid": "tests/test_kernels.py::test_sum", "case": "kernel-sum",
            "evidence": "code-verification", "srq": "summation error",
            "reference_code": null, "refined_parameter": null, "referent": null,
            "seam": null, "outcome": "passed"}]}
```

Under `--collect-only` every outcome is `null`, which is the cheap way to see what a
repository claims without running anything. In a real run the outcomes are filled in,
and the difference matters: evidence that passed is demonstrated, while evidence that
was marked and then skipped is only claimed. The package never decides whether a test
without its reference data should fail or skip; that policy stays with the repository.
Use `--vv-library` to override the recorded name for one run.
