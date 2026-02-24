import os
import sys

# Allow Sphinx to import the package
sys.path.insert(0, os.path.abspath('..'))

project = 'OpenDose-PopPK'
author = 'Angelo Gabriel C. Silva Gomes'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'nbsphinx',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
