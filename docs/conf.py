import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(".."))

project = "OpenDose-PopPK"
author = "Angelo Gabriel C. Silva Gomes"
copyright = f"{datetime.now().year}"
release = "1.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

html_theme = "sphinx_rtd_theme"
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_static_path = ["_static"]
source_suffix = ".rst"
master_doc = "index"