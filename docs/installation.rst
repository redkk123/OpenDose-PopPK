# Installation Instructions

To install the OpenDose-PopPK package, you can use the following command:

```
pip install opendose-poppk
```

## Documentation Dependencies

To build the documentation, make sure you have the following dependencies installed:

```
pip install sphinx sphinx-autodoc-typehints
```

After installing the dependencies, navigate to the `docs` folder and run:

```
sphinx-build -b html . _build/html
```

This will generate the static HTML documentation in the `_build/html` directory.