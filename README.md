# ineedvalidation

Declare which physical case, kind of evidence and response quantity a test exercises; collect the declarations across repositories into an evidence ledger; lint and render a validation hierarchy from node notes plus that ledger.

The vocabulary follows Oberkampf and Roy, *Verification and Validation in Scientific Computing* (2010): a validation hierarchy of unit, benchmark, subsystem and system cases, and a strict separation between verification (the code solves the equations correctly) and validation (the equations describe the measured world).

## Marking a test

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

@vv.case("free-space-propagation", "cross-code-benchmark", reference_code="other-code")
def test_matches_independent_code():
    ...

@vv.case("detector-frame", "validation", referent="lab-flat-field-2026")
def test_matches_measured_frames():
    ...

@vv.seam("optics", "detector", case="detector-frame")
def test_photon_scale_anchor():
    ...

@vv.regression
def test_frozen_output():
    ...
```

Evidence kinds: `code-verification`, `solution-verification`, `cross-code-benchmark`, `validation` (measured data only) and `uncertainty-quantification`. They are spelled out rather than lettered so a marked test reads without a key. `reference_code=` belongs to a cross-code benchmark, `refined_parameter=` and `reference_model=` to solution verification, `referent=` to validation and `alternative=` to uncertainty quantification; each raises when used with another kind, so a mislabelled test fails at import. Regression tests claim no kind of evidence.

`reference_model` names a reference computation of the same governing probabilistic model and assumptions as the reduced model under test, with its own numerical error quantified (`acceptance.reference_error`); a model with different physics is not a reference model, and that comparison is uncertainty quantification with `alternative`.

`alternative` names the alternative model compared with the baseline; such a comparison is a sensitivity analysis, not an estimate of model-form uncertainty.

The markers register through a pytest plugin entry point, so installing the package is the only setup a repository needs.

## Tagging by path

A table in `pyproject.toml` assigns a case and evidence kind by test path, so the tagging cost is per file or directory rather than per test. The longest matching prefix wins, and an explicit marker replaces the default entirely, including optional keyword fields; no fields are merged.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ineedvalidation]
library = "mylib"

[tool.ineedvalidation.defaults]
"tests/test_kernel.py" = { case = "free-space-propagation", evidence = "code-verification" }
"tests/benchmark/" = { case = "free-space-propagation", evidence = "cross-code-benchmark" }
"tests/convergence/" = { case = "free-space-propagation", evidence = "solution-verification", reference_model = "full-resolution propagation" }
"tests/sensitivity/" = { case = "free-space-propagation", evidence = "uncertainty-quantification", alternative = "alternative propagation model" }
```

Paths are matched relative to the pytest rootdir. A `[tool.pytest.ini_options]` table in the same `pyproject.toml` pins the rootdir to the repository; without one, pytest can settle on a directory above it and no default matches.

For a test suite outside a package, use `pytest.ini` to set the rootdir and put settings in `ineedvalidation.toml` beside it:

```toml
library = "simulation-suite"

[defaults]
"tests/" = { case = "kernel-sum", evidence = "code-verification" }
```

The standalone file uses the same defaults schema and validation. A `pyproject.toml` without `[tool.ineedvalidation]` allows this fallback; defining settings in both files raises a pytest usage error naming both paths. See [test suites outside a package](docs/markers.md#test-suites-outside-a-package) for the complete setup.

## Collecting the evidence

```console
$ pytest --vv-evidence evidence/mylib.json
```

One JSON file per repository lists every marked or defaulted test with its case, kind of evidence, response quantity, seam and the outcome it reached, stamped with the commit. The library name comes from `--vv-library NAME`, else `library` in the settings file (`[tool.ineedvalidation]` in `pyproject.toml` or top-level in `ineedvalidation.toml`), else the rootdir name.

## Linting, scaffolding and rendering a hierarchy

```console
$ ineedvalidation lint hierarchy/ --library-map libraries.md
$ ineedvalidation scaffold hierarchy/
$ ineedvalidation render hierarchy/
```

The hierarchy is a directory holding `nodes/` (one Markdown note with YAML frontmatter per node, listing the cases it owns under `cases:`), `evidence/` (the ledgers) and optionally `views/`; `--nodes` and `--evidence` point elsewhere. The lint checks the notes for internal consistency and checks them against the collected tests in both directions: a case no node owns, a node with no tests, a response quantity a node does not list, or a validation level claimed without a passing test that supports it. `scaffold` writes a stub note for every case a test names that no node owns. The renderer draws the levelled figure through `d2`, with named views (`--view`, `--all-views`), a single branch (`--root`) and optional hand-edited overrides for figures that have to look right in a talk.
