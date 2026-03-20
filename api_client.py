# ============================================================
# api_client.py — Comunicação com a API de Futebol
# ============================================================
# Este arquivo é responsável por "conversar" com a API.
# Pense nele como um garçom: você faz o pedido, ele vai
# buscar os dados e traz de volta para você.
# ============================================================

import requests
import time
from config import BASE_URL, HEADERS


def _fazer_requisicao(endpoint: str) -> dict:
    """
    Função interna que faz a chamada à API.
    
    Parâmetros:
        endpoint: parte final da URL (ex: "/competitions/PL/matches")
    
    Retorna:
        Dicionário com os dados ou None se houver erro
    """
    url = BASE_URL + endpoint

    try:
        resposta = requests.get(url, headers=HEADERS, timeout=10)

        # Código 200 significa "sucesso"
        if resposta.status_code == 200:
            return resposta.json()

        # Código 429 significa "muitas requisições" — esperamos 1 minuto
        elif resposta.status_code == 429:
            print("⚠️  Limite de requisições atingido. Aguardando 60 segundos...")
            time.sleep(60)
            return _fazer_requisicao(endpoint)

        # Código 403 significa "acesso negado" — verifique sua API Key
        elif resposta.status_code == 403:
            print("❌ Acesso negado. Verifique sua API Key no arquivo config.py")
            return None

        else:
            print(f"❌ Erro {resposta.status_code}: {resposta.text[:100]}")
            return None

    except requests.exceptions.Timeout:
        print("❌ Tempo de espera esgotado. Verifique sua conexão com a internet.")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ Sem conexão com a internet.")
        return None


# ------------------------------------------------------------
# FUNÇÕES PÚBLICAS — use estas no main.py
# ------------------------------------------------------------

def buscar_jogos_competicao(codigo_competicao: str, temporada: int = None) -> list:
    """
    Busca todos os jogos de uma competição.
    
    Exemplo de uso:
        jogos = buscar_jogos_competicao("PL")          # Premier League atual
        jogos = buscar_jogos_competicao("BSA", 2023)   # Brasileirão 2023
    
    Retorna:
        Lista de dicionários com informações de cada jogo
    """
    endpoint = f"/competitions/{codigo_competicao}/matches"
    if temporada:
        endpoint += f"?season={temporada}"

    dados = _fazer_requisicao(endpoint)
    if dados and "matches" in dados:
        print(f"✅ {len(dados['matches'])} jogos encontrados.")
        return dados["matches"]
    return []


def buscar_jogos_time(id_time: int, limite: int = 10) -> list:
    """
    Busca os últimos jogos de um time específico.
    
    Exemplo de uso:
        jogos = buscar_jogos_time(64, limite=10)  # Últimos 10 jogos do Liverpool
    
    Retorna:
        Lista com os últimos jogos do time
    """
    endpoint = f"/teams/{id_time}/matches?status=FINISHED&limit={limite}"
    dados = _fazer_requisicao(endpoint)
    if dados and "matches" in dados:
        return dados["matches"]
    return []


def buscar_classificacao(codigo_competicao: str) -> list:
    """
    Busca a tabela de classificação de uma competição.
    
    Exemplo de uso:
        tabela = buscar_classificacao("PL")
    
    Retorna:
        Lista com as informações de cada time na tabela
    """
    endpoint = f"/competitions/{codigo_competicao}/standings"
    dados = _fazer_requisicao(endpoint)

    if dados and "standings" in dados:
        # A API retorna diferentes tipos de tabela (geral, casa, fora)
        # Pegamos a tabela geral (índice 0)
        tabela = dados["standings"][0]["table"]
        print(f"✅ Classificação com {len(tabela)} times carregada.")
        return tabela
    return []


def buscar_times_competicao(codigo_competicao: str) -> list:
    """
    Busca todos os times de uma competição.
    
    Exemplo de uso:
        times = buscar_times_competicao("BSA")
    
    Retorna:
        Lista com informações de cada time (incluindo o ID)
    """
    endpoint = f"/competitions/{codigo_competicao}/teams"
    dados = _fazer_requisicao(endpoint)
    if dados and "teams" in dados:
        return dados["teams"]
    return []


def buscar_proximo_jogo(id_time: int) -> dict:
    """
    Busca o próximo jogo agendado de um time.
    
    Retorna:
        Dicionário com informações do próximo jogo, ou None
    """
    endpoint = f"/teams/{id_time}/matches?status=SCHEDULED&limit=1"
    dados = _fazer_requisicao(endpoint)
    if dados and "matches" in dados and dados["matches"]:
        return dados["matches"][0]
    return None
