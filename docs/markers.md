# Marking a test

A test declares what it demonstrates with one of three decorators. Each is a thin
wrapper over a pytest marker whose arguments are validated at decoration time, so a
bad tier or a misspelled keyword fails when the module is imported rather than being
ignored at collection.

```python
import ineedvalidation as inv


@inv.case("free-space-propagation", "A", srq="on-axis intensity")
def test_matches_closed_form():
    ...


@inv.case("free-space-propagation", "C", ref="grid-spacing")
def test_second_order_in_the_step():
    ...


@inv.seam("optics", "detector", case="detector-frame")
def test_photon_scale_anchor():
    ...


@inv.regression
def test_frozen_output():
    ...
```

## The arguments

`case` names a physical case as a plain slug. It carries no tier prefix and no
hierarchy identifier: a node note lists the slugs it owns, so the same slug can be
exercised by tests in several repositories.

`tier` is the kind of evidence the test produces.

| Tier | Meaning |
|---|---|
| `A` | Code verification against analytic forms, identities and invariants. |
| `B` | Cross-code benchmark against an independently developed code. |
| `C` | Solution verification: convergence in an ordered discretization parameter. |
| `D` | Validation against measured data. |

Uncertainty quantification is a campaign record on the program, not a property of a
single test, so it has no marker.

`srq` is optional and names the system response quantity the test measures. When the
declarations are linted against a hierarchy, the value must be one the node lists.

`ref` is optional and reads differently by tier: the independent code for `B`, the
ordered parameter for `C`, the referent dataset for `D`.

`seam(producer, consumer, case=...)` marks an absolute-scale anchor test across an
interface between two libraries. Shape, ratio and fitted-scale tests are scale blind,
so an interface that is only covered by those can carry a constant factor for a long
time without any test noticing. The lint checks that the two libraries own nodes that
are actually coupled.

`regression` marks a frozen or golden reference. Such a test is recorded but is
excluded from every tier, so it cannot inflate the evidence for a case.

## Tagging by path

Tagging every test by hand is not worth the effort when a whole directory exercises
one case. A table in the repository's `pyproject.toml` assigns a case and a tier by
path prefix:

```toml
[tool.ineedvalidation]
library = "mylib"

[tool.ineedvalidation.defaults]
"tests/validation/" = { case = "free-space-propagation", tier = "B" }
"tests/test_kernels.py" = { case = "kernel-sum", tier = "A" }
```

The longest matching prefix wins. An explicit marker, on the function or in a module
level `pytestmark`, overrides the default entirely. `library` names the repository in
the evidence file; without it the name of the root directory is used.

## Writing the evidence file

```console
$ pytest --inv-evidence evidence/mylib.json
```

The file lists every marked or defaulted test with the outcome it reached:

```json
{"library": "mylib", "commit": "abc1234", "recorded": "2026-09-04T15:00:00Z",
 "tests": [{"nodeid": "tests/test_kernels.py::test_sum", "case": "kernel-sum",
            "tier": "A", "srq": "summation error", "ref": null, "seam": null,
            "outcome": "passed", "points": []}]}
```

Under `--collect-only` every outcome is `null`, which is the cheap way to see what a
repository claims without running anything. In a real run the outcomes are filled in,
and the difference matters: evidence that passed is demonstrated, while evidence that
was marked and then skipped is only claimed. The package never decides whether a test
without its reference data should fail or skip; that policy stays with the repository.
Use `--inv-library` to override the recorded name for one run.
