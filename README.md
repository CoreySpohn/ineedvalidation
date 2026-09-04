# ineedvalidation

Declare which physical case, evidence tier and response quantity a test exercises; collect the declarations across repositories into an evidence ledger; lint and render a validation hierarchy from node notes plus that ledger.

The vocabulary follows Oberkampf and Roy, *Verification and Validation in Scientific Computing* (2010): a validation hierarchy of unit, benchmark, subsystem and system cases, and a strict separation between verification (the code solves the equations correctly) and validation (the equations describe the measured world).

## Marking a test

```python
import ineedvalidation as inv

@inv.case("free-space-propagation", "A", srq="on-axis intensity")
def test_matches_closed_form():
    ...

@inv.case("free-space-propagation", "B", ref="other-code")
def test_matches_independent_code():
    ...

@inv.seam("optics", "detector")
def test_photon_scale_anchor():
    ...

@inv.regression
def test_frozen_output():
    ...
```

Tiers: `A` code verification, `B` cross-code benchmark, `C` solution verification, `D` validation against measured data. Regression tests are excluded from every tier.

The markers register through a pytest plugin entry point, so installing the package is the only setup a repository needs.

## Collecting the evidence

```console
$ pytest --inv-evidence evidence/mylib.json
```

One JSON file per repository lists every marked test, its case, its tier and the outcome it reached. A table in `pyproject.toml` can assign a case and tier by test path, so the tagging cost is per directory rather than per test.

## Linting and rendering a hierarchy

```console
$ ineedvalidation lint hierarchy/
$ ineedvalidation render hierarchy/
```

The hierarchy is a directory of Markdown notes with YAML frontmatter, one per case. The lint checks the notes for internal consistency and checks them against the collected tests in both directions: a case no node owns, a node with no tests, a response quantity a node does not list, or a validation level claimed without a passing test that supports it. The renderer draws the tiered figure through `d2`, with named views and optional hand-edited overrides for figures that have to look right in a talk.

## Status

Pre-alpha. The markers, the evidence collector, the hierarchy lint and the renderer work; the API is not yet stable.
