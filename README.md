# ⚽ Football Analyzer

Ferramenta de análise estatística de futebol com modelo preditivo de entradas.

---

## 🚀 Como começar (passo a passo)

### 1. Instale o Python
Acesse https://www.python.org/downloads/ e instale a versão 3.10 ou superior.

### 2. Instale as dependências
Abra o terminal na pasta do projeto e execute:
```
pip install -r requirements.txt
```

### 3. Obtenha sua API Key gratuita
- Acesse: https://www.football-data.org/client/register
- Cadastre-se gratuitamente
- Você receberá uma API Key por e-mail
- Cole a chave no arquivo `config.py` na variável `API_KEY`

### 4. Configure a análise
Abra o arquivo `main.py` e ajuste:
```python
COMPETICAO      = "BSA"        # Código da competição (veja config.py)
NOME_TIME_CASA  = "Flamengo"   # Time mandante
NOME_TIME_FORA  = "Palmeiras"  # Time visitante
MODO            = "api"        # "api" ou "arquivo"
```

### 5. Execute
```
python main.py
```

---

## 📁 Estrutura do Projeto

```
football_analyzer/
├── main.py          → Execute este arquivo
├── config.py        → Configurações e API Key
├── api_client.py    → Comunicação com a API
├── analyzer.py      → Análise estatística
├── predictor.py     → Modelo preditivo (Poisson)
├── visualizer.py    → Gráficos e visualizações
├── importer.py      → Importação de Excel/CSV
├── requirements.txt → Dependências
├── dados/           → Coloque seus arquivos CSV/Excel aqui
└── resultados/      → Gráficos e relatórios gerados
```

---

## 📊 O que a ferramenta analisa

### Estatísticas por time
- Vitórias, empates e derrotas
- Aproveitamento geral, em casa e fora
- Médias de gols marcados e sofridos
- Percentual de Over 2.5 gols
- Forma recente (últimos 5 jogos)

### Modelo Preditivo (Distribuição de Poisson)
O modelo calcula probabilidades para:
- **1x2**: Vitória casa / Empate / Vitória fora
- **Over/Under 2.5 gols**
- **BTTS**: Ambos os times marcam
- **Top 5 placares mais prováveis**

### Recomendação de Entrada
A ferramenta analisa todos os mercados e recomenda o mais favorável com base na confiança do modelo (padrão: ≥ 65%).

---

## 🗂️ Usando seus próprios dados (sem API)

1. Execute para criar um template:
```python
from importer import criar_template_csv
criar_template_csv()
```

2. Preencha o arquivo `dados/template_jogos.csv`

3. No `main.py`, altere:
```python
MODO            = "arquivo"
CAMINHO_ARQUIVO = "dados/template_jogos.csv"
```

---

## ⚽ Competições disponíveis (plano gratuito)

| Código | Competição        |
|--------|-------------------|
| `PL`   | Premier League    |
| `PD`   | La Liga           |
| `BL1`  | Bundesliga        |
| `SA`   | Serie A           |
| `FL1`  | Ligue 1           |
| `CL`   | Champions League  |
| `BSA`  | Brasileirão Série A |

---

## ⚠️ Aviso importante
Esta ferramenta é para fins educacionais e de análise estatística.
Aposte com responsabilidade.
