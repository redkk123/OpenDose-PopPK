# 🚀 Guia de Início Rápido — OpenDose-PopPK

Bem-vindo à versão **refatorada e profissional** do OpenDose-PopPK!

## ⚡ Em 5 Minutos

### 1. **Instalar Dependências**

```bash
pip install -r requirements.txt
```

### 2. **Executar o Pipeline Principal**

Gera automaticamente **todas as 4 figuras** da análise:

```bash
python main.py
```

**Figuras salvas em**: `output/figures/`

### 3. **Rodar Demonstração do Modelo 2-Compartimentos**

```bash
python demo_2compartment.py
```

### 4. **Executar Testes**

```bash
python -m pytest -v
```

---

## 📁 Estrutura de Pastas

```
├── data/                      ← DADOS
│   ├── raw/                   # Dados originais (não modificar!)
│   └── processed/             # Processados (intermediários)
├── models/                    ← ANÁLISES  
│   └── 01_basic_pk_analysis.py
├── scripts/                   ← CÓDIGO AUXILIAR
│   └── project_paths.py       # ← Use isto para acessar arquivos!
├── output/                    ← RESULTADOS (figuras, tabelas)
│   ├── figures/
│   └── tables/
├── main.py                    ← Pipeline principal
└── demo_2compartment.py       ← Demonstração
```

**Ver estrutura completa**: [STRUCTURE.md](STRUCTURE.md)

---

## 🎯 Usar `project_paths` (A CHAVE!)

Todo arquivo que acessa dados ou salva resultados deve usar:

```python
from scripts.project_paths import paths

# LER DADOS
df = pd.read_csv(paths.raw_data("drugs_parameters.csv"))

# SALVAR FIGURAS
plt.savefig(paths.figures("my_plot.png"))

# SALVAR TABELAS
df.to_csv(paths.tables("my_results.csv"))
```

**Vantagens**:
✅ Funciona em qualquer máquina (Windows, Linux, macOS)
✅ Sem caminhos hardcoded
✅ Sem `../../../` confuso

---

## 🔬 Arquivos Principais

| Arquivo | Descrição |
|---------|-----------|
| **main.py** | Pipeline principal (4 análises) |
| **demo_2compartment.py** | Demonstração do modelo 2-compartimentos |
| **models/01_basic_pk_analysis.py** | Exemplo de análise reutilizável |
| **STRUCTURE.md** | Documentação completa da estrutura |
| **REFACTORING_2COMPARTMENT.md** | Detalhes técnicos do modelo 2-comp |

---

## 💡 Exemplos Comuns

### Carregar Dados de Drogas

```python
from scripts.project_paths import paths
from opendose_poppk import DrugDatabase

db = DrugDatabase(str(paths.raw_data("drugs_parameters.csv")))
drugs = db.list_drugs()
para = db.get_drug("Paracetamol")
```

### Criar Análise Nova

1. Criar arquivo em `models/02_my_analysis.py`
2. Usar `project_paths` para ler dados
3. Salvar resultados em `output/`
4. Executar: `python models/02_my_analysis.py`

Ver template: [models/01_basic_pk_analysis.py](models/01_basic_pk_analysis.py)

### Simular Perfil PK

```python
from opendose_poppk import PKModel

# Criar modelo
pk = PKModel(
    F=0.80, ka=1.80, ke=0.28, Vd=65.0,
    Q=10.0, V2=20.0  # Parâmetros 2-compartimentos
)

# Simular
t = np.linspace(0, 24, 300)
C = pk.concentration(t, D=1000.0)

# Análise cinética
cmax, tmax = pk.cmax(D=1000.0)
auc = pk.auc(D=1000.0)
```

---

## 🧪 Testes

Rodar todos:
```bash
python -m pytest -v
```

Rodar específico:
```bash
python -m pytest tests/test_basic.py -v
python -m pytest tests/test_bayesian.py::test_map_runs -v
```

Status atual: **4/4 testes passam** ✅

---

## 📊 Modelo 2-Compartimentos

Este projeto agora suporta **dois compartimentos** (central + periférico):

```
Absorção → Compartimento Central (V1) ↔ Compartimento Periférico (V2)
           |
           └─→ Eliminação (CL)
```

**Parametrização padrão NONMEM**:
- `V1` (ou `Vd`) : Volume central
- `V2` : Volume periférico
- `Q` : Clearance inter-compartimental
- `CL` : Clearance sistêmico (derivado)
- `ke` : Taxa de eliminação (derivado)

**Compatibilidade total** com API legada (1-compartimento).

[Detalhes técnicos →](REFACTORING_2COMPARTMENT.md)

---

## 🐛 Troubleshooting

### `ModuleNotFoundError: No module named 'scripts'`

Execute o script **da raiz do projeto**:

```bash
# ✓ CERTO
python models/01_basic_pk_analysis.py

# ✓ TAMBÉM CERTO
python -m pytest

# ✗ ERRADO (não rodar de dentro da pasta)
cd models && python 01_basic_pk_analysis.py
```

### Figuras salvas em lugar errado

Sempre use `project_paths`:

```python
# ✓ BOM
plt.savefig(paths.figures("plot.png"))

# ✗ RUIM
plt.savefig("output/figures/plot.png")  # Caminhos hardcoded
```

### CSV não encontrado

Verifique que está em `data/raw/`:

```bash
ls data/raw/
# Deve listar: drugs_parameters.csv
```

---

## 📚 Referências

- [Estrutura Completa](STRUCTURE.md)
- [Refatoração 2-Compartimentos](REFACTORING_2COMPARTMENT.md)
- [API do Projeto](opendose_poppk/)

---

## 📧 Contato & Contribuições

**Desenvolvido em**: Federal Institute of Brasília (IFB)  
**Última atualização**: Fevereiro 2026  
**Versão**: 2.0 (2-Compartimentos + Estrutura Profissional)

---

**Próximo passo**: [Leia STRUCTURE.md para entender a organização completa →](STRUCTURE.md)
