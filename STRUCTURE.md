# 📁 Estrutura do Projeto OpenDose-PopPK

## Visão Geral

Este projeto segue uma **estrutura profissional** comum em pesquisa científica, similar a pacotes R (como `rstan`) e organizações Python estilo `cookiecutter-data-science`.

## 🏗️ Hierarquia de Pastas

```
OpenDose-PopPK/
│
├── 📊 data/                          ← DADOS (Raw & Processed)
│   ├── raw/                          # Dados originais (IMUTÁVEL)
│   │   └── drugs_parameters.csv      # ← Parâmetros farmacológicos
│   └── processed/                    # Dados limpos, transformados (intermediários)
│
├── 🔬 models/                        ← ANÁLISES & MODELAGEM
│   ├── __init__.py
│   ├── 01_basic_pk_analysis.py      # Análise PK básica
│   ├── 02_monte_carlo_simulation.py # Simulações Monte Carlo
│   └── 03_covariate_population.py   # Análise de covariáveis
│
├── 🛠️ scripts/                       ← CÓDIGO AUXILIAR & UTILITÁRIOS
│   ├── __init__.py
│   ├── project_paths.py             # ← GERENCIADOR DE PATHS (essencial!)
│   └── utils.py                     # Funções helpers (limpeza, etc.)
│
├── 📈 output/                        ← RESULTADOS & SAÍDAS
│   ├── figures/                      # Gráficos (PNG, PDF, SVG)
│   ├── tables/                       # Tabelas (CSV, Excel, JSON)
│   └── reports/                      # Relatórios compilados (HTML, Markdown)
│
├── 📔 notebooks/                     ← JUPYTER (análise exploratória)
│   ├── 01_exploratory_analysis.ipynb # EDA interativa
│   └── 02_model_validation.ipynb     # Validação + diagnósticos
│
├── 📚 opendose_poppk/               ← PACOTE PRINCIPAL (Core Library)
│   ├── __init__.py
│   └── pk_model.py                  # Classes: PKModel, PDModel, Simulator, etc.
│
├── ✅ tests/                         ← TESTES UNITÁRIOS
│   ├── __init__.py
│   ├── test_basic.py
│   ├── test_bayesian.py
│   └── test_population.py
│
├── 📖 docs/                          ← DOCUMENTAÇÃO
│   ├── math.md
│   └── api.md
│
├── 📄 paper/                         ← PUBLICAÇÃO/PAPER
│   └── paper.md
│
├── 🔧 Arquivos de Config
│   ├── setup.py / pyproject.toml     # Metadados do projeto
│   ├── requirements.txt              # Dependências
│   ├── .gitignore
│   ├── README.md
│   └── STRUCTURE.md                  # ← Este arquivo
│
└── 📝 Scripts Raiz (Pipelines Principais)
    ├── main.py                       # Pipeline principal (gera todas as figuras)
    ├── demo_2compartment.py          # Demonstração do modelo 2-comp
    └── opendose.py                   # Shim de compatibilidade (imports)
```

## 🎯 Propósitos de Cada Pasta

### 📊 `data/`

**Regra de Ouro**: Nunca modificar arquivos em `data/raw/` programaticamente.

```python
# ✓ BOM: Ler dados brutos, processar, guardar em processed/
df_raw = pd.read_csv("data/raw/drugs_parameters.csv")
df_clean = df_raw.dropna()
df_clean.to_csv("data/processed/drugs_clean.csv", index=False)

# ✗ RUIM: Modificar/sobrescrever raw/
df_raw.to_csv("data/raw/drugs_parameters.csv")  # NÃO!
```

- `raw/` : Dados originais, versão de controle, documentação dos dados
- `processed/` : Dados finais para análise, caches, intermediários

### 🔬 `models/`

Scripts de **modelagem completa** e **análises principais**.

Cada arquivo é um **pipeline independente**:

```python
# models/01_basic_pk_analysis.py
from scripts.project_paths import paths
from opendose_poppk import PKModel, DrugDatabase

db = DrugDatabase(paths.raw_data("drugs_parameters.csv"))
# ... análise ...
# Salvar resultados em output/
```

**Padrão de nomenclatura**:
- `01_*` : Análises básicas
- `02_*` : Análises intermediárias / especializadas
- `03_*` : Análises avançadas

### 🛠️ `scripts/`

**Código reutilizável** e **funções auxiliares**:

```python
# scripts/project_paths.py (CENTRAL!)
from scripts.project_paths import paths
csv = paths.raw_data("drugs_parameters.csv")
fig = paths.figures("my_plot.png")

# scripts/utils.py (helpers)
def clean_data(df): ...
def plot_formatted(data): ...
```

**NÃO** são análises completas, apenas **funções suportivas**.

### 📈 `output/`

**Tudo que é gerado** pelo pipeline:

- `figures/` : Gráficos (sempre salvos automaticamente)
- `tables/` : Tabelas (CSV, Excel, JSON)
- `reports/` : Documentos finais (HTML, PDF)

**Regra**: Nunca fazer commit direto de `output/` (exceto estrutura). Está em `.gitignore`.

### 📔 `notebooks/`

**Análise exploratória** (EDA), **testes de hipóteses**, **validação**.

Diferente de `models/`:
- `models/` = pipelines determinísticos → output/
- `notebooks/` = exploração interativa

Usar para:
- Entender dados (`01_exploratory_analysis.ipynb`)
- Validar modelos (`02_model_validation.ipynb`)
- Gerar relatórios (com `jupyter nbconvert`)

## 🔑 Chave: `scripts/project_paths.py`

Este é o **coração** da organização relativa:

```python
from scripts.project_paths import paths

# Ler dados
csv = paths.raw_data("drugs_parameters.csv")

# Salvar figuras
fig_path = paths.figures("my_plot.png")

# Acessar qualquer pasta
model_script = paths.models("01_basic_pk_analysis.py")
output_table = paths.tables("results.csv")
```

**Vantagens**:
✓ Funciona em qualquer máquina (Windows, Linux, macOS)
✓ Sem `../../../` complicado
✓ Paths sempre absolutos internamente
✓ API clara e intuitiva

## 🚀 Usar o Projeto

### 1. Executar pipelines principais

```bash
# Pipeline completo (gera todas as figuras)
python main.py

# Demonstração do modelo 2-compartimentos
python demo_2compartment.py
```

### 2. Rodar testes

```bash
python -m pytest -v
python -m pytest tests/test_basic.py
```

### 3. Trabalhar em análises novas

```python
# models/04_my_analysis.py
from scripts.project_paths import paths
from opendose_poppk import PKModel, DrugDatabase

# Seu código aqui
db = DrugDatabase(paths.raw_data("drugs_parameters.csv"))
# ...

# Salvar resultados
fig.savefig(paths.figures("my_analysis.png"))
results.to_csv(paths.tables("my_results.csv"))
```

### 4. Editar notebooks

```bash
jupyter notebook notebooks/01_exploratory_analysis.ipynb
```

## 📋 Checklist: Refatoração Completa

- [x] Criar estrutura de pastas
- [x] Implementar `scripts/project_paths.py`
- [x] Mover `datasets/drugs_parameters.csv` → `data/raw/`
- [x] Refatorar `main.py` (usar paths relativo)
- [x] Refatorar `demo_2compartment.py` (usar paths relativo)
- [x] Atualizar `scripts/__init__.py` e `models/__init__.py`
- [x] Documentar estrutura (este arquivo)
- [ ] Criar `models/01_basic_pk_analysis.py`
- [ ] Criar `scripts/utils.py`
- [ ] Atualizar `.gitignore` (ignorar `output/`)

## 🔒 `.gitignore` Recomendado

```gitignore
# Output (gerado automaticamente)
output/figures/*
output/tables/*
output/reports/*
!output/**/.gitkeep

# Data processed (derivados)
data/processed/*
!data/processed/.gitkeep

# Python
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
.coverage
.env

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

## 🎓 Exemplo Prático: Adicionar uma Nova Análise

```python
# models/04_sensitivity_analysis.py
"""Análise de sensibilidade dos parâmetros."""

from scripts.project_paths import paths
from opendose_poppk import PKModel
import pandas as pd
import matplotlib.pyplot as plt

def main():
    # Ler dados
    db = DrugDatabase(paths.raw_data("drugs_parameters.csv"))
    
    # Sua análise
    results = []
    for drug_name in db.list_drugs():
        drug = db.get_drug(drug_name)
        pk = PKModel(**drug.pk_kwargs)
        # ... análise ...
        results.append({...})
    
    # Salvar resultados
    df = pd.DataFrame(results)
    df.to_csv(paths.tables("sensitivity_results.csv"), index=False)
    
    # Salvar figuras
    fig, ax = plt.subplots()
    # ... plot ...
    fig.savefig(paths.figures("sensitivity_plot.png"))
    plt.close()
    
    print(f"✓ Resultados salvos em {paths.output()}")

if __name__ == "__main__":
    main()
```

Então executar:

```bash
python models/04_sensitivity_analysis.py
```

## 🔗 Linhas de Importação Padrão

```python
# No início de todo arquivo models/ ou scripts/:
from scripts.project_paths import paths
from opendose_poppk import PKModel, DrugDatabase, PopulationSimulator
import pandas as pd
import matplotlib.pyplot as plt

# Usar paths:
csv = paths.raw_data("drugs_parameters.csv")
fig_out = paths.figures("my_plot.png")
table_out = paths.tables("my_table.csv")
```

## 📖 Referências

Este padrão é baseado em:

- **Cookiecutter Data Science**: https://drivendata.github.io/cookiecutter-data-science/
- **R Package Structure**: Padrão de pacotes R (rstan, tidyverse)
- **Scientific Computing Best Practices**: Wilson et al. (2017)

---

**Última atualização**: Fevereiro 2026
**Versão do Projeto**: OpenDose-PopPK v2.0 (2-compartimentos + Estrutura Profissional)
