# ============================================================
# config.py — Configurações do Football Analyzer
# ============================================================
# Aqui ficam todas as configurações do projeto.
# Você só precisa alterar este arquivo para personalizar
# o funcionamento da ferramenta.
# ============================================================

import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# ------------------------------------------------------------
# CONFIGURAÇÃO DA API
# ------------------------------------------------------------
# Usamos a API gratuita do football-data.org
# Cadastre-se em: https://www.football-data.org/client/register
# Após o cadastro, você receberá uma chave (API Key) por e-mail

API_KEY = os.getenv("API_KEY", "SUA_CHAVE_AQUI")
BASE_URL = "https://api.football-data.org/v4"

# Cabeçalho necessário para autenticar nas requisições
HEADERS = {
    "X-Auth-Token": API_KEY
}

# ------------------------------------------------------------
# COMPETIÇÕES DISPONÍVEIS (plano gratuito)
# ------------------------------------------------------------
# Cada competição tem um código. Use esses códigos no main.py
COMPETITIONS = {
    "Premier League":     "PL",    # Inglaterra
    "La Liga":            "PD",    # Espanha
    "Bundesliga":         "BL1",   # Alemanha
    "Serie A":            "SA",    # Itália
    "Ligue 1":            "FL1",   # França
    "Champions League":   "CL",    # Europa
    "Brasileirão Série A":"BSA",   # Brasil
}

# ------------------------------------------------------------
# CONFIGURAÇÕES DE ANÁLISE
# ------------------------------------------------------------
# Número mínimo de jogos para considerar uma análise confiável
MIN_JOGOS = 5

# Peso dos resultados recentes (últimos jogos têm mais peso)
PESO_FORMA_RECENTE = 0.6   # 60% para últimos 5 jogos
PESO_TEMPORADA = 0.4        # 40% para toda a temporada

# Limiar de confiança para recomendar entrada (de 0 a 1)
LIMIAR_CONFIANCA = 0.65     # Recomenda apenas se confiança > 65%

# ------------------------------------------------------------
# CONFIGURAÇÕES DE SAÍDA
# ------------------------------------------------------------
# Pasta onde os gráficos e relatórios serão salvos
PASTA_SAIDA = "resultados"

# Pasta onde ficam os arquivos Excel/CSV de entrada
PASTA_DADOS = "dados"

# Formato dos gráficos gerados
FORMATO_GRAFICO = "png"     # Pode ser "png", "pdf" ou "svg"

# Resolução dos gráficos (DPI)
DPI_GRAFICO = 150
