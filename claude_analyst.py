# ============================================================
# claude_analyst.py — Integração com a API do Claude (Anthropic)
# ============================================================
# Este módulo usa o Claude para transformar os dados estatísticos
# em análises em linguagem natural, como um analista profissional.
# ============================================================

import requests
import json


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


def _chamar_claude(api_key: str, mensagens: list, system: str = "", max_tokens: int = 1500) -> str:
    """
    Função base que chama a API do Claude.
    Retorna o texto da resposta ou uma mensagem de erro.
    """
    headers = {
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }

    payload = {
        "model":      MODEL,
        "max_tokens": max_tokens,
        "messages":   mensagens,
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
        elif resp.status_code == 401:
            return "❌ API Key do Claude inválida. Verifique nas configurações."
        elif resp.status_code == 429:
            return "⚠️ Limite de requisições atingido. Tente novamente em instantes."
        else:
            return f"❌ Erro {resp.status_code}: {resp.text[:200]}"
    except requests.exceptions.Timeout:
        return "❌ Tempo de resposta esgotado. Verifique sua conexão."
    except Exception as e:
        return f"❌ Erro inesperado: {str(e)}"


def gerar_analise_confronto(
    api_key: str,
    stats_casa: dict,
    stats_fora: dict,
    comparacao: dict,
    probs: dict,
    recomendacao: dict,
) -> str:
    """
    Gera uma análise completa do confronto em linguagem natural.
    O Claude age como um analista esportivo profissional.
    """

    system = """Você é um analista esportivo profissional especializado em futebol e mercados de apostas.
Sua função é interpretar dados estatísticos e transformá-los em análises claras, objetivas e úteis.
Escreva sempre em português brasileiro. Seja direto, profissional e fundamentado nos dados fornecidos.
Não invente informações além do que os dados mostram. Estruture bem a resposta com seções."""

    dados = f"""
CONFRONTO: {stats_casa['time']} (CASA) vs {stats_fora['time']} (FORA)

=== ESTATÍSTICAS — {stats_casa['time']} ===
- Jogos: {stats_casa['total_jogos']} | Vitórias: {stats_casa['vitorias']} | Empates: {stats_casa['empates']} | Derrotas: {stats_casa['derrotas']}
- Aproveitamento geral: {stats_casa['aproveitamento_pct']}% | Em casa: {stats_casa['aproveitamento_casa']}%
- Gols marcados: {stats_casa['gols_marcados']} | Gols sofridos: {stats_casa['gols_sofridos']}
- Média gols marcados: {stats_casa['media_gols_marcados']} | Média gols sofridos: {stats_casa['media_gols_sofridos']}
- Over 2.5 nos jogos: {stats_casa['over25_pct']}%
- Forma recente (últimos 5): {stats_casa['forma_recente']}

=== ESTATÍSTICAS — {stats_fora['time']} ===
- Jogos: {stats_fora['total_jogos']} | Vitórias: {stats_fora['vitorias']} | Empates: {stats_fora['empates']} | Derrotas: {stats_fora['derrotas']}
- Aproveitamento geral: {stats_fora['aproveitamento_pct']}% | Fora de casa: {stats_fora['aproveitamento_fora']}%
- Gols marcados: {stats_fora['gols_marcados']} | Gols sofridos: {stats_fora['gols_sofridos']}
- Média gols marcados: {stats_fora['media_gols_marcados']} | Média gols sofridos: {stats_fora['media_gols_sofridos']}
- Over 2.5 nos jogos: {stats_fora['over25_pct']}%
- Forma recente (últimos 5): {stats_fora['forma_recente']}

=== MODELO PREDITIVO (Distribuição de Poisson) ===
- Gols esperados casa: {comparacao['gols_esperados_casa']} | Gols esperados fora: {comparacao['gols_esperados_fora']}
- Total gols esperados: {comparacao['total_gols_esperado']}
- Probabilidade vitória {stats_casa['time']}: {probs['vitoria_casa']}%
- Probabilidade empate: {probs['empate']}%
- Probabilidade vitória {stats_fora['time']}: {probs['vitoria_fora']}%
- Over 2.5: {probs['over25']}% | Under 2.5: {probs['under25']}%
- Ambos marcam (Sim): {probs['btts_sim']}% | (Não): {probs['btts_nao']}%
- Top placares: {', '.join([f"{p[0]} ({p[1]}%)" for p in probs['top5_placares']])}

=== RECOMENDAÇÃO DO MODELO ===
- Status: {recomendacao['status']}
- Mercado sugerido: {recomendacao['mercado']}
- Probabilidade: {recomendacao['probabilidade']}%
- Confiança do modelo: {recomendacao['confianca_pct']}%
- Placar mais provável: {recomendacao['placar_mais_provavel']}
"""

    prompt = f"""{dados}

Com base nesses dados, faça uma análise completa e profissional deste confronto.
Estruture sua resposta nas seguintes seções:

## 🔍 Panorama do Confronto
(Comparação geral dos dois times, quem está em melhor momento)

## ⚽ Análise Ofensiva e Defensiva
(Potencial de gols de cada time, vulnerabilidades defensivas)

## 📊 Mercados Mais Favoráveis
(Analise os mercados 1x2, Over/Under e BTTS com base nas probabilidades)

## ✅ Recomendação Final
(Qual entrada você recomendaria e por quê, com nível de confiança)

## ⚠️ Pontos de Atenção
(Riscos, incertezas ou fatores que podem invalidar a análise)"""

    return _chamar_claude(api_key, [{"role": "user", "content": prompt}], system)


def responder_pergunta(
    api_key: str,
    pergunta: str,
    historico: list,
    stats_casa: dict,
    stats_fora: dict,
    probs: dict,
    recomendacao: dict,
) -> str:
    """
    Responde perguntas do usuário sobre o confronto em modo chat.
    Mantém o histórico da conversa para respostas contextualizadas.
    """

    system = f"""Você é um analista esportivo especializado em futebol. 
Você acabou de analisar o confronto entre {stats_casa['time']} (casa) e {stats_fora['time']} (fora).

Dados resumidos que você conhece:
- Probabilidade vitória {stats_casa['time']}: {probs['vitoria_casa']}%
- Probabilidade empate: {probs['empate']}%  
- Probabilidade vitória {stats_fora['time']}: {probs['vitoria_fora']}%
- Over 2.5: {probs['over25']}% | Under 2.5: {probs['under25']}%
- BTTS Sim: {probs['btts_sim']}%
- Placar mais provável: {recomendacao['placar_mais_provavel']}
- Mercado recomendado: {recomendacao['mercado']} ({recomendacao['probabilidade']}%)
- Forma {stats_casa['time']}: {stats_casa['forma_recente']}
- Forma {stats_fora['time']}: {stats_fora['forma_recente']}

Responda de forma direta e objetiva em português. Seja conciso (máximo 3 parágrafos)."""

    # Monta histórico + nova pergunta
    mensagens = historico + [{"role": "user", "content": pergunta}]

    return _chamar_claude(api_key, mensagens, system, max_tokens=800)


def gerar_resumo_executivo(
    api_key: str,
    stats_casa: dict,
    stats_fora: dict,
    recomendacao: dict,
    probs: dict,
) -> str:
    """
    Gera um resumo executivo curto — ideal para compartilhar rapidamente.
    """

    system = "Você é um analista de futebol. Escreva em português brasileiro de forma concisa."

    prompt = f"""Crie um resumo executivo CURTO (máximo 5 linhas) para compartilhar sobre este jogo:

{stats_casa['time']} vs {stats_fora['time']}
- Probabilidades: {stats_casa['time']} {probs['vitoria_casa']}% | Empate {probs['empate']}% | {stats_fora['time']} {probs['vitoria_fora']}%
- Over 2.5: {probs['over25']}% | BTTS: {probs['btts_sim']}%
- Recomendação: {recomendacao['mercado']} ({recomendacao['probabilidade']}%)
- Placar provável: {recomendacao['placar_mais_provavel']}

Formato: texto direto, sem títulos, como se fosse uma mensagem para um grupo de WhatsApp de apostadores."""

    return _chamar_claude(api_key, [{"role": "user", "content": prompt}], system, max_tokens=300)
