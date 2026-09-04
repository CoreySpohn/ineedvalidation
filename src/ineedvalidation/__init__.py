"""Evidence declarations for tests and a validation hierarchy built from them.

The test half is a pytest plugin: :func:`case`, :func:`seam` and
:func:`regression` mark what a test demonstrates, and the plugin collects those
marks into an evidence ledger. The render half reads hierarchy node notes plus
that ledger, lints them against each other, and renders the hierarchy.
"""

from ineedvalidation._version import __version__
from ineedvalidation.marks import TIERS, case, regression, seam

__all__ = ["TIERS", "__version__", "case", "regression", "seam"]
