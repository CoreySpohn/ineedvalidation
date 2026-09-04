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

## Status

Pre-alpha. The markers and plugin registration exist; evidence collection, the hierarchy lint and the renderer are in progress.
