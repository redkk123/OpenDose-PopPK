from pathlib import Path

from opendose_poppk.release_tools import (
    build_release_readiness_report,
    is_strict_semver,
    render_release_readiness_markdown,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_release_readiness_success(tmp_path):
    _write(tmp_path / "README.md", "# Demo\n")
    _write(tmp_path / "LICENSE", "MIT\n")
    _write(tmp_path / "pyproject.toml", '[project]\nname="x"\nversion = "1.2.3"\n')
    _write(tmp_path / "opendose_poppk" / "__init__.py", '__version__ = "1.2.3"\n')
    _write(tmp_path / ".github" / "workflows" / "release.yml", "name: release\n")
    _write(tmp_path / "examples" / "drugs" / "a.py", "print('a')\n")
    _write(tmp_path / "examples" / "drugs" / "b.py", "print('b')\n")

    report = build_release_readiness_report(tmp_path)
    assert report["ready"] is True
    assert report["pyproject_version"] == "1.2.3"
    assert report["__init___version"] == "1.2.3"
    assert report["strict_semver_pyproject"] is True
    assert report["strict_semver___init__"] is True
    assert report["examples_count"] == 2
    assert report["failures"] == []

    md = render_release_readiness_markdown(report)
    assert "# OpenDose Release Readiness" in md
    assert "examples/drugs/a.py" in md


def test_release_readiness_failures(tmp_path):
    _write(tmp_path / "README.md", "# Demo\n")
    _write(tmp_path / "pyproject.toml", '[project]\nname="x"\nversion = "1.2"\n')
    _write(tmp_path / "opendose_poppk" / "__init__.py", '__version__ = "2.0.0"\n')
    _write(tmp_path / "examples" / "drugs" / "only_one.py", "print('one')\n")

    report = build_release_readiness_report(tmp_path)
    assert report["ready"] is False
    assert any("missing_file:" in f for f in report["failures"])
    assert any("semver:" in f for f in report["failures"])
    assert any("version_mismatch:" in f for f in report["failures"])
    assert any("examples:" in f for f in report["failures"])


def test_strict_semver():
    assert is_strict_semver("1.0.0") is True
    assert is_strict_semver("0.1.9") is True
    assert is_strict_semver("1.0") is False
    assert is_strict_semver("v1.0.0") is False


def test_release_readiness_parse_and_invalid_init_semver(tmp_path):
    _write(tmp_path / "README.md", "# Demo\n")
    _write(tmp_path / "LICENSE", "MIT\n")
    _write(tmp_path / "pyproject.toml", '[project]\nname="x"\n')
    _write(tmp_path / "opendose_poppk" / "__init__.py", '__version__ = "v2.0.0"\n')
    _write(tmp_path / ".github" / "workflows" / "release.yml", "name: release\n")
    _write(tmp_path / "examples" / "drugs" / "a.py", "print('a')\n")
    _write(tmp_path / "examples" / "drugs" / "b.py", "print('b')\n")

    report = build_release_readiness_report(tmp_path)
    assert report["ready"] is False
    assert "version_parse: pyproject.toml version not found" in report["failures"]
    assert "semver: invalid __init__ version 'v2.0.0'" in report["failures"]


def test_release_readiness_missing_init_version_and_render_failures(tmp_path):
    _write(tmp_path / "README.md", "# Demo\n")
    _write(tmp_path / "LICENSE", "MIT\n")
    _write(tmp_path / "pyproject.toml", '[project]\nname="x"\nversion = "1.0.0"\n')
    _write(tmp_path / "opendose_poppk" / "__init__.py", "# no version\n")
    _write(tmp_path / ".github" / "workflows" / "release.yml", "name: release\n")

    report = build_release_readiness_report(tmp_path)
    assert report["ready"] is False
    assert "version_parse: __init__.py __version__ not found" in report["failures"]

    md = render_release_readiness_markdown(report)
    assert "## Example Files" in md
    assert "- none" in md
    assert "version_parse: __init__.py __version__ not found" in md
