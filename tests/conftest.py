"""Shared facts about the machine the tests are running on."""

import importlib.util
import os
import shutil

from hypothesis import settings

HAVE_BINARIES = bool(shutil.which("d2") and shutil.which("rsvg-convert"))

# hwoutils is optional, and released versions may not include the budget plugin.
pytest_plugins = []
if (
    importlib.util.find_spec("hwoutils") is not None
    and importlib.util.find_spec("hwoutils.testbudget") is not None
):
    pytest_plugins.append("hwoutils.testbudget.plugin")

settings.register_profile("quick", max_examples=25, deadline=None)
settings.register_profile("nightly", max_examples=200, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "quick"))
