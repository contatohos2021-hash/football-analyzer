# ============================================================
# predictor.py — Modelo Preditivo e Recomendação de Entrada
# ============================================================
# Este arquivo usa os dados analisados para gerar uma
# recomendação de entrada (qual aposta/mercado faz mais
# sentido com base nas estatísticas).
# ============================================================

import numpy as np
from scipy.stats import poisson
from config import LIMIAR_CONFIANCA


def calcular_probabilidades_poisson(media_casa: float, media_fora: float, max_gols: int = 8) -> dict:
    """
    Calcula probabilidades usando distribuição de Poisson.
    
    O modelo de Poisson é amplamente usado em análise de futebol
    para estimar a probabilidade de cada placar possível.
    
    Parâmetros:
        media_casa:  gols esperados pelo time da casa
        media_fora:  gols esperados pelo time visitante
        max_gols:    máximo de gols a considerar por time
    
    Retorna:
        Dicionário com probabilidades de vitória, empate, derrota e mercados
    """
    # Construímos uma matriz de probabilidades para cada placar possível
    # Eixo 0 = gols do time da casa (0 a max_gols)
    # Eixo 1 = gols do time visitante (0 a max_gols)
    matriz = np.zeros((max_gols + 1, max_gols + 1))

    for i in range(max_gols + 1):
        for j in range(max_gols + 1):
            # Probabilidade de o time da casa marcar exatamente i gols
            # E o visitante marcar exatamente j gols
            prob_i = poisson.pmf(i, media_casa)
            prob_j = poisson.pmf(j, media_fora)
            matriz[i][j] = prob_i * prob_j

    # Calculamos as probabilidades dos resultados principais
    prob_vitoria_casa  = np.sum(np.tril(matriz, -1))  # Triângulo inferior (casa > fora)
    prob_empate        = np.sum(np.diag(matriz))       # Diagonal (casa = fora)
    prob_vitoria_fora  = np.sum(np.triu(matriz, 1))   # Triângulo superior (fora > casa)

    # Over/Under 2.5 gols
    prob_over25  = 0.0
    prob_under25 = 0.0
    for i in range(max_gols + 1):
        for j in range(max_gols + 1):
            if i + j > 2:
                prob_over25  += matriz[i][j]
            else:
                prob_under25 += matriz[i][j]

    # Ambos marcam (BTTS)
    prob_btts = np.sum(matriz[1:, 1:])  # Casa >= 1 E fora >= 1

    # Os 5 placares mais prováveis
    melhores_placares = []
    for i in range(max_gols + 1):
        for j in range(max_gols + 1):
            melhores_placares.append((i, j, matriz[i][j]))
    melhores_placares.sort(key=lambda x: x[2], reverse=True)

    return {
        "vitoria_casa":  round(prob_vitoria_casa * 100, 1),
        "empate":        round(prob_empate * 100, 1),
        "vitoria_fora":  round(prob_vitoria_fora * 100, 1),
        "over25":        round(prob_over25 * 100, 1),
        "under25":       round(prob_under25 * 100, 1),
        "btts_sim":      round(prob_btts * 100, 1),
        "btts_nao":      round((1 - prob_btts) * 100, 1),
        "top5_placares": [(f"{i}x{j}", round(p * 100, 1)) for i, j, p in melhores_placares[:5]],
        "matriz":        matriz,
    }


def gerar_recomendacao(stats_casa: dict, stats_fora: dict, comparacao: dict, probs: dict) -> dict:
    """
    Analisa todos os dados e gera uma recomendação de entrada.
    
    A recomendação considera:
    - Probabilidades calculadas pelo modelo de Poisson
    - Forma recente dos times
    - Histórico em casa/fora
    - Mercados disponíveis (resultado, gols, BTTS)
    
    Retorna:
        Dicionário com a recomendação e justificativa
    """
    candidatos = []

    nome_casa = stats_casa["time"]
    nome_fora = stats_fora["time"]

    # --- MERCADO 1: Resultado (1x2) ---
    if probs["vitoria_casa"] > 55:
        candidatos.append({
            "mercado":     f"Vitória {nome_casa}",
            "confianca":   probs["vitoria_casa"] / 100,
            "probabilidade": probs["vitoria_casa"],
            "justificativa": (
                f"{nome_casa} tem {probs['vitoria_casa']}% de chance de vencer segundo o modelo. "
                f"Aproveitamento em casa: {stats_casa['aproveitamento_casa']}%."
            )
        })

    if probs["vitoria_fora"] > 50:
        candidatos.append({
            "mercado":     f"Vitória {nome_fora}",
            "confianca":   probs["vitoria_fora"] / 100,
            "probabilidade": probs["vitoria_fora"],
            "justificativa": (
                f"{nome_fora} tem {probs['vitoria_fora']}% de chance de vencer. "
                f"Aproveitamento fora: {stats_fora['aproveitamento_fora']}%."
            )
        })

    # --- MERCADO 2: Over/Under 2.5 gols ---
    if probs["over25"] > 60:
        candidatos.append({
            "mercado":     "Over 2.5 gols",
            "confianca":   probs["over25"] / 100,
            "probabilidade": probs["over25"],
            "justificativa": (
                f"Modelo indica {probs['over25']}% de chance de mais de 2.5 gols. "
                f"Média de gols esperados: {comparacao['total_gols_esperado']}."
            )
        })

    if probs["under25"] > 60:
        candidatos.append({
            "mercado":     "Under 2.5 gols",
            "confianca":   probs["under25"] / 100,
            "probabilidade": probs["under25"],
            "justificativa": (
                f"Modelo indica {probs['under25']}% de chance de menos de 2.5 gols. "
                f"Médias defensivas sólidas nos dois times."
            )
        })

    # --- MERCADO 3: Ambos Marcam (BTTS) ---
    if probs["btts_sim"] > 60:
        candidatos.append({
            "mercado":     "Ambos Marcam - SIM",
            "confianca":   probs["btts_sim"] / 100,
            "probabilidade": probs["btts_sim"],
            "justificativa": (
                f"Probabilidade de ambos marcarem: {probs['btts_sim']}%. "
                f"Ambos os times marcam em média {stats_casa['media_gols_marcados']} "
                f"e {stats_fora['media_gols_marcados']} gols por jogo."
            )
        })

    # --- ESCOLHA FINAL ---
    # Ordenamos pelos candidatos com maior confiança
    candidatos.sort(key=lambda x: x["confianca"], reverse=True)

    if candidatos and candidatos[0]["confianca"] >= LIMIAR_CONFIANCA:
        melhor = candidatos[0]
        status = "✅ ENTRADA RECOMENDADA"
    elif candidatos:
        melhor = candidatos[0]
        status = "⚠️  ENTRADA COM RESSALVAS (baixa confiança)"
    else:
        melhor = {
            "mercado":       "Nenhum mercado recomendado",
            "confianca":     0,
            "probabilidade": 0,
            "justificativa": "O modelo não encontrou mercado com confiança suficiente."
        }
        status = "❌ SEM ENTRADA RECOMENDADA"

    return {
        "status":             status,
        "mercado":            melhor["mercado"],
        "probabilidade":      melhor["probabilidade"],
        "confianca_pct":      round(melhor["confianca"] * 100, 1),
        "justificativa":      melhor["justificativa"],
        "todos_candidatos":   candidatos,
        "placar_mais_provavel": probs["top5_placares"][0][0] if probs["top5_placares"] else "N/A",
    }
