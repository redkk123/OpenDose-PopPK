# Contributing to OpenDose-PopPK

Thank you for your interest in contributing! 🎉

---

## Development setup

```bash
git clone https://github.com/redkk123/OpenDose-PopPK.git
cd OpenDose-PopPK
pip install -e ".[dev,docs,jupyter]"
```

## Running the test suite

```bash
pytest                          # all tests with coverage
pytest -m "not slow"            # fast tests only
pytest tests/test_pk_model.py   # single module
```

Coverage report is printed to the terminal. Aim for ≥ 90 % on any new code.

## Code style

We use **black** (line length 100) and **isort**:

```bash
black .
isort .
flake8 opendose_poppk tests
```

Type hints are encouraged. Run mypy with:

```bash
mypy opendose_poppk
```

## Building the documentation

```bash
cd docs
make html
# open _build/html/index.html
```

## Submitting a pull request

1. Fork the repository and create a feature branch from `main`.
2. Write tests for new functionality.
3. Ensure `pytest` and `black` pass.
4. Update `CHANGELOG.md` under `[Unreleased]`.
5. Open a PR describing what changed and why.

## Reporting bugs

Open an issue on [GitHub Issues](https://github.com/redkk123/OpenDose-PopPK/issues)
with a minimal reproducible example.

## Code of conduct

Be kind, inclusive, and constructive. We follow the
[Contributor Covenant](https://www.contributor-covenant.org/).
