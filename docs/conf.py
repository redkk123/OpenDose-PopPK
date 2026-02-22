# Sphinx configuration file

# Import the necessary Sphinx extensions and settings
author = 'Your Name'
project = 'OpenDose-PopPK'
version = '0.1'
release = '0.1.0'
documentation_theme = 'sphinx_rtd_theme'

# Sphinx settings
autodoc_mock_imports = ['numpy', 'pandas']
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    documentation_theme,
]

# Paths for templates
templates_path = ['_templates']

# Source suffix
source_suffix = '.rst'

# Master document
master_doc = 'index'

# General information about the project
html_title = project + ' Documentation'
html_logo = 'logo.png'
html_static_path = ['_static']
