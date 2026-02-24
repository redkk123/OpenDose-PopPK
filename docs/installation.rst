Installation
============

Requirements
------------

- Python 3.9 or newer
- pip ≥ 21

Dependencies installed automatically:

.. code-block:: text

    numpy  ≥ 1.24
    pandas ≥ 2.0
    scipy  ≥ 1.10
    matplotlib ≥ 3.7

Installing from PyPI (stable)
------------------------------

.. code-block:: bash

    pip install opendose-poppk

Installing from source (development)
--------------------------------------

.. code-block:: bash

    git clone https://github.com/redkk123/OpenDose-PopPK.git
    cd OpenDose-PopPK
    pip install -e ".[dev,docs,jupyter]"

Optional dependency groups
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Group
     - Contents
   * - ``dev``
     - pytest, pytest-cov, black, flake8, mypy
   * - ``docs``
     - sphinx, sphinx-rtd-theme, nbsphinx, myst-parser, sphinx-autodoc-typehints
   * - ``jupyter``
     - jupyter, ipython, notebook

Verifying the installation
---------------------------

.. code-block:: python

    import opendose_poppk
    print(opendose_poppk.__version__)
    # 1.0.0

Building the documentation locally
------------------------------------

.. code-block:: bash

    pip install -e ".[docs]"
    cd docs
    make html
    # open docs/_build/html/index.html
