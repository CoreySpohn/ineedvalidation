"""Shared facts about the machine the tests are running on."""

import shutil

HAVE_BINARIES = bool(shutil.which("d2") and shutil.which("rsvg-convert"))
