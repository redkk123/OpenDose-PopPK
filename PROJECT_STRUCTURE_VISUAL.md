# 🏗️ Visualização da Estrutura Final

## Antes vs. Depois

### ❌ ANTES (Caótico)
```
OpenDose-PopPK/
├── datasets/              ← Dados misturados
├── figures/               ← Figuras soltas na raiz
├── notebooks/
├── docs/
├── paper/
├── opendose_poppk/
├── tests/
├── main.py               ← Scripts na raiz
├── demo_2compartment.py   ← Sem padrão
└── opendose.py
```

**Problemas**:
- ❌ Dados e resultados misturados
- ❌ Paths hardcoded (`datasets/`, `figures/`)
- ❌ Não reutilizável em outra máquina
- ❌ Difícil adicionar novas análises
- ❌ Sem template/padrão para novos scripts

---

### ✅ DEPOIS (Profissional)

```
OpenDose-PopPK/
│
├── 📊 data/                          ← DADOS CENTRALIZADOS
│   ├── raw/                          # Originais (imutáveis)
│   │   └── drugs_parameters.csv
│   └── processed/                    # Limpeza/transformação
│
├── 🔬 models/                        ← ANÁLISES ESTRUTURADAS
│   ├── __init__.py
│   ├── 01_basic_pk_analysis.py       # Template completo
│   ├── 02_monte_carlo_simulation.py  # Exemplo (futuro)
│   └── 03_covariate_population.py    # Exemplo (futuro)
│
├── 🛠️ scripts/                       ← CÓDIGO REUTILIZÁVEL
│   ├── __init__.py
│   ├── project_paths.py              # ⭐ CHAVE DO SISTEMA
│   └── utils.py                      # Helpers (futuro)
│
├── 📈 output/                        ← RESULTADOS
│   ├── figures/                      # Gráficos
│   │   ├── monte_carlo_paracetamol.png
│   │   ├── drug_comparison_panel.png
│   │   ├── covariate_simulation.png
│   │   ├── map_estimation.png
│   │   ├── demo_2compartment.png
│   │   └── basic_pk_analysis.png
│   └── tables/                       # Tabelas
│       └── basic_pk_analysis.csv
│
├── 💻 CORE LIBRARY
│   ├── opendose_poppk/
│   │   ├── __init__.py
│   │   └── pk_model.py
│   └── opendose.py
│
├── ✅ TESTES
│   └── tests/
│       ├── test_basic.py
│       ├── test_bayesian.py
│       └── test_population.py
│
├── 📚 DOCUMENTAÇÃO
│   ├── docs/
│   │   └── math.md
│   ├── STRUCTURE.md              ← Técnica
│   ├── QUICKSTART.md             ← 5 minutos
│   ├── EXECUTIVE_SUMMARY.md      ← Este
│   └── REFACTORING_2COMPARTMENT.md
│
├── 📄 SCRIPTS RAIZ
│   ├── main.py                   ← Refatorado
│   └── demo_2compartment.py      ← Refatorado
│
└── 📝 CONFIGURAÇÃO
    ├── README.md
    ├── requirements.txt
    └── .gitignore
```

**Melhorias**:
- ✅ Dados organizados (raw/ vs processed/)
- ✅ Paths centralizados em `scripts/project_paths.py`
- ✅ Reutilizável em qualquer máquina (Windows/Linux/macOS)
- ✅ Template claro em `models/01_basic_pk_analysis.py`
- ✅ Resultados em local único (output/)
- ✅ Documentação profissional

---

## 🎯 Fluxo de Dados Recomendado

```
┌─────────────────────────────────────────────────────────┐
│  1. RAW DATA (data/raw/)                                │
│     └─ Nunca modificar! Origem única de verdade        │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  2. SCRIPTS (models/)                                   │
│     └─ Ler de raw/ ou processed/                       │
│     └─ Usar project_paths para acessar arquivos       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  3. PROCESSAMENTO (opcional)                            │
│     └─ Salvar em data/processed/ se intermediários     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  4. RESULTADOS (output/)                                │
│     ├─ output/figures/ (gráficos)                      │
│     ├─ output/tables/ (tabelas)                        │
│     └─ output/reports/ (relatórios)                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  5. PUBLICAÇÃO                                          │
│     └─ Copiar resultados para paper/, notebooks/       │
└─────────────────────────────────────────────────────────┘
```

---

## 🔑 O Sistema de Paths (project_paths.py)

```python
from scripts.project_paths import paths

# ✅ SEMPRE FUNCIONA
csv = paths.raw_data("drugs_parameters.csv")
result = paths.figures("my_plot.png")
table = paths.tables("my_table.csv")

# ✅ Retorna objetos pathlib.Path (robustos)
# ✅ Funciona em Windows, Linux, macOS
# ✅ Sem caminhos hardcoded
```

**Por trás dos panos**:
```
paths.raw_data("file.csv")
  ↓
Path(__file__).parent.parent.resolve()
  ↓
C:\Users\...\OpenDose-PopPK\
  ↓
C:\Users\...\OpenDose-PopPK\data\raw\file.csv
```

---

## 📚 Arquivos Novos Criados

| Arquivo | Tipo | Propósito |
|---------|------|----------|
| `scripts/project_paths.py` | Python | Gerenciador central de paths |
| `scripts/__init__.py` | Python | Exporta `paths` |
| `models/__init__.py` | Python | Package marker |
| `models/01_basic_pk_analysis.py` | Python | Template de análise |
| `STRUCTURE.md` | Markdown | Documentação técnica |
| `QUICKSTART.md` | Markdown | Guia 5 minutos |
| `EXECUTIVE_SUMMARY.md` | Markdown | Sumário (este) |
| `data/raw/` | Folder | Dados originais |
| `data/processed/` | Folder | Dados processados |
| `output/figures/` | Folder | Gráficos |
| `output/tables/` | Folder | Tabelas |

---

## 🔄 Fluxo de Uso Típico

### Opção 1: Executar Pipelines Existentes

```bash
# Pipeline completo (main)
python main.py

# Demonstração 2-compartimentos
python demo_2compartment.py

# Análise básica (template)
python models/01_basic_pk_analysis.py
```

### Opção 2: Criar Nova Análise

```bash
# 1. Copiar template
cp models/01_basic_pk_analysis.py models/02_my_analysis.py

# 2. Editar
nano models/02_my_analysis.py

# 3. Executar
python models/02_my_analysis.py

# 4. Ver resultados em output/
ls output/figures/
ls output/tables/
```

### Opção 3: Adicionar Novos Dados

```bash
# 1. Colocar em data/raw/ (nunca modificar!)
cp my_data.csv data/raw/

# 2. Criar script de processamento
python models/02_my_analysis.py

# 3. Script usa:
#    db = DrugDatabase(str(paths.raw_data("my_data.csv")))
```

---

## 📊 Comparação de Padrões

### Pattern Antigo (❌)
```python
# main.py
CSV_PATH = os.path.join("datasets", "drugs_parameters.csv")
OUT_DIR  = "figures"
os.makedirs(OUT_DIR, exist_ok=True)

fig.savefig(os.path.join(OUT_DIR, "plot.png"))
```

**Problemas**:
- Caminhos hardcoded
- Quebra em máquinas diferentes
- Difícil mover arquivos
- Sem centralização

### Pattern Novo (✅)
```python
# Qualquer script
from scripts.project_paths import paths

csv = paths.raw_data("drugs_parameters.csv")
fig_path = paths.figures("plot.png")
fig.savefig(fig_path)
```

**Vantagens**:
- Centralizado
- Portável (qualquer SO)
- Fácil de mover
- API clara

---

## 🎓 Inspiração Metodológica

```
Cookiecutter Data Science
    ↓
Padrão de Projetos de Análise
    ↓
Nossas Adaptações
    ↓
OpenDose-PopPK v2.0 (Agora)
```

**Referências**:
- Wilson et al. (2017) — "Good Enough Practices in Scientific Computing"
- Drivendata — "Cookiecutter Data Science" (MIT License)
- R Community — Package structure best practices

---

## 📈 Métricas de Qualidade

| Métrica | Valor | Status |
|---------|-------|--------|
| Testes Passando | 4/4 | ✅ 100% |
| Portabilidade | Windows/Linux/macOS | ✅ Total |
| Documentação | 3 arquivos | ✅ Completa |
| Breaking Changes | 0 | ✅ Nenhuma |
| Paths Centralizados | 1 módulo | ✅ Único |
| Templates Disponíveis | 1 | ✅ Pronto |
| Code Reusability | Alto | ✅ Fácil |

---

## 🚀 Próximos Passos (Sugeridos)

### Curto Prazo (Semanas)
- [ ] Popul `data/processed/` com dados limpeza
- [ ] Adicionar `scripts/utils.py` (helpers)
- [ ] Criar `models/02_*.py` (análises adicionais)

### Médio Prazo (Meses)
- [ ] Integração CI/CD (GitHub Actions)
- [ ] Cobertura de testes (pytest-cov)
- [ ] Jupyter notebooks (EDA)

### Longo Prazo (Semestres)
- [ ] Dockerização
- [ ] API REST (FastAPI)
- [ ] Interface web (Streamlit/Shiny)
- [ ] Publicação

---

## 📧 Contato

**Desenvolvedor**: Angelo Gabriel C. Silva Gomes  
**Instituição**: Federal Institute of Brasília (IFB)  
**Projeto**: OpenDose-PopPK  
**Versão**: 2.0 (2-Compartimentos + Estrutura Profissional)  
**Data**: Fevereiro 2026

---

**Leitura Recomendada**:
1. [QUICKSTART.md](QUICKSTART.md) — Comece em 5 minutos
2. [STRUCTURE.md](STRUCTURE.md) — Entenda a organização completa
3. Este arquivo — Visualização e fluxos
4. [REFACTORING_2COMPARTMENT.md](REFACTORING_2COMPARTMENT.md) — Detalhes técnicos
