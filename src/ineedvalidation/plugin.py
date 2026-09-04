"""pytest plugin entry point: registers the evidence markers.

Loaded automatically through the ``pytest11`` entry point once the package is
installed, so a repository declares nothing in its own configuration.
"""

from ineedvalidation.marks import MARK_CASE, MARK_REGRESSION, MARK_SEAM

MARKER_HELP = {
    MARK_CASE: (
        "inv_case(slug, tier, srq=None, ref=None): the physical case, evidence "
        "tier and system response quantity a test exercises (use ineedvalidation.case)"
    ),
    MARK_SEAM: (
        "inv_seam(producer, consumer, case=None): an absolute-scale anchor test "
        "across a producer/consumer interface (use ineedvalidation.seam)"
    ),
    MARK_REGRESSION: (
        "inv_regression: a frozen or golden reference, excluded from every "
        "evidence tier (use ineedvalidation.regression)"
    ),
}


def pytest_configure(config):
    """Register the markers so ``--strict-markers`` accepts them."""
    for name, text in MARKER_HELP.items():
        config.addinivalue_line("markers", f"{name}: {text}")
