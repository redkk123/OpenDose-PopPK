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
     - sphinx, sphinx-rtd-theme, myst-parser
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

Maintainer release workflow (PyPI)
----------------------------------

PyPI publication is automated by GitHub Actions using Trusted Publishing (OIDC).

1. Configure a Trusted Publisher in PyPI for this repository/workflow:
   - Owner: ``redkk123``
   - Repository: ``OpenDose-PopPK``
   - Workflow: ``release.yml``
   - Environment: ``pypi``
2. Bump package version.
3. Push a tag matching ``v*`` (example: ``v1.0.1``).
