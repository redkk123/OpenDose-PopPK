"""
project_paths.py
================
Gerenciador centralizado de caminhos do projeto OpenDose-PopPK.

Este módulo fornece caminhos absolutos para todas as pastas principais,
garantindo que o projeto funcione em qualquer máquina usando caminhos
relativos à raiz do repositório.

Uso
---
    from scripts.project_paths import paths
    
    # Acessar qualquer caminho
    drug_data = paths.data("raw/drugs_parameters.csv")
    fig_path  = paths.output("figures/my_plot.png")
    model_script = paths.models("01_basic_pk_analysis.py")

Estrutura de pastas
--------------------
    data/
        raw/              # Dados originais (não modificar)
        processed/        # Dados processados / intermdíários
    models/               # Scripts de modelagem
    scripts/              # Funções auxiliares + utilitários
    output/
        figures/          # Figuras (.png, .pdf)
        tables/           # Tabelas (.csv, .xlsx)
    notebooks/            # Jupyter notebooks (análise exploratória)
    opendose_poppk/       # Pacote principal
    tests/                # Testes unitários
"""

from pathlib import Path
from typing import Union


class ProjectPaths:
    """
    Gerenciador de caminhos do projeto.
    
    Todos os métodos retornam objetos `pathlib.Path` que funcionam
    em Windows, Linux e macOS.
    """

    def __init__(self):
        """Detecta a raiz do projeto (onde está o setup.py ou .git)"""
        # Começa do diretório deste arquivo
        current = Path(__file__).resolve().parent
        
        # Sobe para encontrar a raiz (procura por setup.py, pyproject.toml, ou .git)
        while current != current.parent:
            if (current / ".git").exists() or \
               (current / "setup.py").exists() or \
               (current / "pyproject.toml").exists() or \
               (current / "README.md").exists():
                self._root = current
                break
            current = current.parent
        else:
            # Fallback: assume que a raiz é 2 níveis acima (scripts/)
            self._root = Path(__file__).resolve().parent.parent

    @property
    def root(self) -> Path:
        """Retorna a raiz do projeto."""
        return self._root

    def _resolve_path(self, *parts: str) -> Path:
        """Resolve um caminho relativo à raiz."""
        p = self.root.joinpath(*parts)
        return p

    # ── Pastas Principais ────────────────────────────────────────────────────

    def data(self, subpath: str = "") -> Path:
        """Retorna o caminho para data/. Se subpath for dado, retorna data/subpath."""
        return self._resolve_path("data", subpath) if subpath else self._resolve_path("data")

    def models(self, subpath: str = "") -> Path:
        """Retorna o caminho para models/."""
        return self._resolve_path("models", subpath) if subpath else self._resolve_path("models")

    def scripts(self, subpath: str = "") -> Path:
        """Retorna o caminho para scripts/."""
        return self._resolve_path("scripts", subpath) if subpath else self._resolve_path("scripts")

    def output(self, subpath: str = "") -> Path:
        """Retorna o caminho para output/."""
        return self._resolve_path("output", subpath) if subpath else self._resolve_path("output")

    def notebooks(self, subpath: str = "") -> Path:
        """Retorna o caminho para notebooks/."""
        return self._resolve_path("notebooks", subpath) if subpath else self._resolve_path("notebooks")

    def docs(self, subpath: str = "") -> Path:
        """Retorna o caminho para docs/."""
        return self._resolve_path("docs", subpath) if subpath else self._resolve_path("docs")

    def tests(self, subpath: str = "") -> Path:
        """Retorna o caminho para tests/."""
        return self._resolve_path("tests", subpath) if subpath else self._resolve_path("tests")

    def package(self, subpath: str = "") -> Path:
        """Retorna o caminho para opendose_poppk/ (pacote principal)."""
        return self._resolve_path("opendose_poppk", subpath) if subpath else self._resolve_path("opendose_poppk")

    # ── Subpastas de output ──────────────────────────────────────────────────

    def figures(self, filename: str = "") -> Path:
        """Retorna o caminho para output/figures/."""
        p = self._resolve_path("output", "figures", filename) if filename else \
            self._resolve_path("output", "figures")
        return p

    def tables(self, filename: str = "") -> Path:
        """Retorna o caminho para output/tables/."""
        p = self._resolve_path("output", "tables", filename) if filename else \
            self._resolve_path("output", "tables")
        return p

    # ── Subpastas de data ────────────────────────────────────────────────────

    def raw_data(self, filename: str = "") -> Path:
        """Retorna o caminho para data/raw/."""
        p = self._resolve_path("data", "raw", filename) if filename else \
            self._resolve_path("data", "raw")
        return p

    def processed_data(self, filename: str = "") -> Path:
        """Retorna o caminho para data/processed/."""
        p = self._resolve_path("data", "processed", filename) if filename else \
            self._resolve_path("data", "processed")
        return p

    # ── Métodos Auxiliares ───────────────────────────────────────────────────

    def ensure_exists(self, path: Union[str, Path]) -> Path:
        """Cria uma pasta se não existir. Retorna o Path."""
        p = Path(path) if isinstance(path, str) else path
        p.mkdir(parents=True, exist_ok=True)
        return p

    def __repr__(self) -> str:
        return f"ProjectPaths(root='{self._root}')"


# Instância global — usar como: from scripts.project_paths import paths
paths = ProjectPaths()


if __name__ == "__main__":
    # Teste: exibir estrutura
    print("OpenDose-PopPK Project Paths")
    print("=" * 60)
    print(f"Root: {paths.root}")
    print()
    print("Pastas principais:")
    print(f"  data/       → {paths.data()}")
    print(f"  models/     → {paths.models()}")
    print(f"  scripts/    → {paths.scripts()}")
    print(f"  output/     → {paths.output()}")
    print(f"  notebooks/  → {paths.notebooks()}")
    print(f"  tests/      → {paths.tests()}")
    print()
    print("Subpastas importantes:")
    print(f"  data/raw/        → {paths.raw_data()}")
    print(f"  data/processed/  → {paths.processed_data()}")
    print(f"  output/figures/  → {paths.figures()}")
    print(f"  output/tables/   → {paths.tables()}")
    print()
    print("Existem?")
    for name in ["raw_data", "processed_data", "figures", "tables"]:
        p = getattr(paths, name)()
        exists = "✓" if p.exists() else "✗"
        print(f"  {exists} {p}")
