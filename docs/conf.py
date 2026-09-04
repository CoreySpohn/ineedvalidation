"""Sphinx configuration file."""

from importlib.metadata import version as get_version

project = "ineedvalidation"
copyright = "2026, Corey Spohn"
author = "Corey Spohn"
release = get_version("ineedvalidation")
version = ".".join(release.split(".")[:2])

extensions = [
    "myst_nb",
    "autoapi.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "IPython.sphinxext.ipython_console_highlighting",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pytest": ("https://docs.pytest.org/en/stable/", None),
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
language = "en"

autoapi_dirs = ["../src"]
autoapi_ignore = ["**/*version.py"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
autodoc_typehints = "description"
napoleon_use_ivar = True
suppress_warnings = ["autoapi.python_import_resolution"]

myst_enable_extensions = ["amsmath", "dollarmath"]

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
master_doc = "index"
html_title = "ineedvalidation"
html_theme_options = {
    "repository_url": "https://github.com/CoreySpohn/ineedvalidation",
    "repository_branch": "main",
    "use_repository_button": True,
    "show_toc_level": 2,
}
html_context = {"default_mode": "dark"}
source_suffix = {".rst": "restructuredtext", ".md": "myst-nb"}
nb_execution_mode = "auto"
nb_execution_timeout = 300
nb_execution_raise_on_error = True
nb_execution_show_tb = True
nb_output_stderr = "remove"
