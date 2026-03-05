from __future__ import annotations

from pathlib import Path
import re


_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_PYPROJECT_VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$', flags=re.MULTILINE)
_INIT_VERSION_RE = re.compile(r'^\s*__version__\s*=\s*"([^"]+)"\s*$', flags=re.MULTILINE)


def is_strict_semver(version: str) -> bool:
    return bool(_SEMVER_RE.match(str(version).strip()))


def _extract_version_from_pyproject(pyproject_path: str | Path) -> str | None:
    text = Path(pyproject_path).read_text(encoding="utf-8")
    m = _PYPROJECT_VERSION_RE.search(text)
    return m.group(1) if m else None


def _extract_version_from_init(init_path: str | Path) -> str | None:
    text = Path(init_path).read_text(encoding="utf-8")
    m = _INIT_VERSION_RE.search(text)
    return m.group(1) if m else None


def build_release_readiness_report(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    required_files = [
        root / "README.md",
        root / "pyproject.toml",
        root / "opendose_poppk" / "__init__.py",
        root / "LICENSE",
        root / ".github" / "workflows" / "release.yml",
    ]

    failures: list[str] = []
    existing = {}
    for path in required_files:
        exists = path.exists()
        rel = path.relative_to(root).as_posix()
        existing[rel] = bool(exists)
        if not exists:
            failures.append(f"missing_file: {rel}")

    pyproject_version = None
    init_version = None
    pyproject_path = root / "pyproject.toml"
    init_path = root / "opendose_poppk" / "__init__.py"

    if pyproject_path.exists():
        pyproject_version = _extract_version_from_pyproject(pyproject_path)
        if pyproject_version is None:
            failures.append("version_parse: pyproject.toml version not found")
    if init_path.exists():
        init_version = _extract_version_from_init(init_path)
        if init_version is None:
            failures.append("version_parse: __init__.py __version__ not found")

    if pyproject_version is not None and not is_strict_semver(pyproject_version):
        failures.append(f"semver: invalid pyproject version '{pyproject_version}'")
    if init_version is not None and not is_strict_semver(init_version):
        failures.append(f"semver: invalid __init__ version '{init_version}'")
    if pyproject_version is not None and init_version is not None and pyproject_version != init_version:
        failures.append(f"version_mismatch: pyproject={pyproject_version} __init__={init_version}")

    examples_dir = root / "examples" / "drugs"
    example_files = (
        sorted(p.relative_to(root).as_posix() for p in examples_dir.glob("*.py")) if examples_dir.exists() else []
    )
    if len(example_files) < 2:
        failures.append("examples: expected at least 2 drug example scripts in examples/drugs/")

    return {
        "repo_root": str(root),
        "pyproject_version": pyproject_version,
        "__init___version": init_version,
        "strict_semver_pyproject": bool(pyproject_version and is_strict_semver(pyproject_version)),
        "strict_semver___init__": bool(init_version and is_strict_semver(init_version)),
        "required_files": existing,
        "examples_count": int(len(example_files)),
        "example_files": example_files,
        "ready": len(failures) == 0,
        "failures": failures,
    }


def render_release_readiness_markdown(report: dict) -> str:
    lines = [
        "# OpenDose Release Readiness",
        "",
        f"- Repo root: `{report['repo_root']}`",
        f"- Ready: `{report['ready']}`",
        f"- pyproject version: `{report['pyproject_version']}`",
        f"- __init__ version: `{report['__init___version']}`",
        f"- Strict semver (pyproject): `{report['strict_semver_pyproject']}`",
        f"- Strict semver (__init__): `{report['strict_semver___init__']}`",
        f"- Drug examples: `{report['examples_count']}`",
        "",
        "## Required Files",
    ]
    for rel, exists in report.get("required_files", {}).items():
        lines.append(f"- `{rel}`: {'OK' if exists else 'MISSING'}")

    lines.extend(["", "## Example Files"])
    if report.get("example_files"):
        for f in report["example_files"]:
            lines.append(f"- `{f}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Failures"])
    if report.get("failures"):
        for item in report["failures"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)
