# ============================================================
# analyzer.py — Análise Estatística dos Jogos
# ============================================================
# Aqui transformamos os dados brutos da API em estatísticas
# úteis. É o "cérebro" da ferramenta.
# ============================================================

import pandas as pd
import numpy as np
from config import MIN_JOGOS, PESO_FORMA_RECENTE, PESO_TEMPORADA


def jogos_para_dataframe(jogos: list) -> pd.DataFrame:
    """
    Converte a lista de jogos da API para uma tabela (DataFrame).
    
    Um DataFrame é como uma planilha do Excel, mas dentro do Python.
    Isso facilita muito a análise dos dados.
    
    Retorna:
        DataFrame com as colunas:
        data, time_casa, time_fora, gols_casa, gols_fora, resultado
    """
    registros = []

    for jogo in jogos:
        # Só consideramos jogos que já terminaram
        if jogo.get("status") != "FINISHED":
            continue

        placar = jogo.get("score", {}).get("fullTime", {})
        gols_casa = placar.get("home")
        gols_fora = placar.get("away")

        # Pulamos jogos sem placar registrado
        if gols_casa is None or gols_fora is None:
            continue

        # Determinamos o resultado
        if gols_casa > gols_fora:
            resultado = "vitoria_casa"
        elif gols_fora > gols_casa:
            resultado = "vitoria_fora"
        else:
            resultado = "empate"

        registros.append({
            "id_jogo":    jogo.get("id"),
            "data":       pd.to_datetime(jogo.get("utcDate")),
            "competicao": jogo.get("competition", {}).get("name", ""),
            "time_casa":  jogo.get("homeTeam", {}).get("name", ""),
            "id_casa":    jogo.get("homeTeam", {}).get("id"),
            "time_fora":  jogo.get("awayTeam", {}).get("name", ""),
            "id_fora":    jogo.get("awayTeam", {}).get("id"),
            "gols_casa":  gols_casa,
            "gols_fora":  gols_fora,
            "resultado":  resultado,
            "total_gols": gols_casa + gols_fora,
        })

    df = pd.DataFrame(registros)
    if not df.empty:
        df = df.sort_values("data").reset_index(drop=True)

    return df


def calcular_estatisticas_time(df: pd.DataFrame, nome_time: str) -> dict:
    """
    Calcula estatísticas completas de um time específico.
    
    Parâmetros:
        df:         DataFrame com todos os jogos
        nome_time:  Nome exato do time (como aparece na API)
    
    Retorna:
        Dicionário com as estatísticas calculadas
    """
    # Filtramos apenas os jogos que envolvem o time
    jogos_casa = df[df["time_casa"] == nome_time].copy()
    jogos_fora = df[df["time_fora"] == nome_time].copy()

    total_jogos = len(jogos_casa) + len(jogos_fora)

    if total_jogos < MIN_JOGOS:
        print(f"⚠️  Apenas {total_jogos} jogos encontrados. Mínimo recomendado: {MIN_JOGOS}")

    # --- Gols marcados e sofridos ---
    gols_marcados_casa  = jogos_casa["gols_casa"].sum()
    gols_sofridos_casa  = jogos_casa["gols_fora"].sum()
    gols_marcados_fora  = jogos_fora["gols_fora"].sum()
    gols_sofridos_fora  = jogos_fora["gols_casa"].sum()

    total_marcados = gols_marcados_casa + gols_marcados_fora
    total_sofridos = gols_sofridos_casa + gols_sofridos_fora

    # --- Vitórias, empates e derrotas ---
    vitorias_casa    = (jogos_casa["resultado"] == "vitoria_casa").sum()
    empates_casa     = (jogos_casa["resultado"] == "empate").sum()
    derrotas_casa    = (jogos_casa["resultado"] == "vitoria_fora").sum()

    vitorias_fora    = (jogos_fora["resultado"] == "vitoria_fora").sum()
    empates_fora     = (jogos_fora["resultado"] == "empate").sum()
    derrotas_fora    = (jogos_fora["resultado"] == "vitoria_casa").sum()

    total_vitorias   = vitorias_casa + vitorias_fora
    total_empates    = empates_casa + empates_fora
    total_derrotas   = derrotas_casa + derrotas_fora

    # --- Aproveitamento (%) ---
    pontos_possiveis = total_jogos * 3
    pontos_obtidos   = total_vitorias * 3 + total_empates
    aproveitamento   = (pontos_obtidos / pontos_possiveis * 100) if pontos_possiveis > 0 else 0

    # --- Over/Under 2.5 gols ---
    todos_jogos = pd.concat([
        jogos_casa[["total_gols", "data"]],
        jogos_fora[["total_gols", "data"]]
    ]).sort_values("data")

    over25 = (todos_jogos["total_gols"] > 2.5).mean() * 100

    # --- Forma recente (últimos 5 jogos) ---
    forma = calcular_forma_recente(jogos_casa, jogos_fora, nome_time)

    return {
        "time":               nome_time,
        "total_jogos":        total_jogos,
        "vitorias":           int(total_vitorias),
        "empates":            int(total_empates),
        "derrotas":           int(total_derrotas),
        "gols_marcados":      int(total_marcados),
        "gols_sofridos":      int(total_sofridos),
        "saldo_gols":         int(total_marcados - total_sofridos),
        "media_gols_marcados": round(total_marcados / total_jogos, 2) if total_jogos > 0 else 0,
        "media_gols_sofridos": round(total_sofridos / total_jogos, 2) if total_jogos > 0 else 0,
        "aproveitamento_pct": round(aproveitamento, 1),
        "over25_pct":         round(over25, 1),
        "forma_recente":      forma,
        # Casa
        "jogos_casa":         len(jogos_casa),
        "vitorias_casa":      int(vitorias_casa),
        "aproveitamento_casa": round(vitorias_casa / len(jogos_casa) * 100, 1) if len(jogos_casa) > 0 else 0,
        # Fora
        "jogos_fora":         len(jogos_fora),
        "vitorias_fora":      int(vitorias_fora),
        "aproveitamento_fora": round(vitorias_fora / len(jogos_fora) * 100, 1) if len(jogos_fora) > 0 else 0,
    }


def calcular_forma_recente(jogos_casa: pd.DataFrame, jogos_fora: pd.DataFrame, nome_time: str) -> str:
    """
    Calcula a forma recente do time (últimos 5 jogos).
    
    Retorna:
        String com resultados (ex: "V V E D V") e pontuação
    """
    # Unimos jogos em casa e fora e pegamos os últimos 5
    todos = []

    for _, jogo in jogos_casa.iterrows():
        if jogo["resultado"] == "vitoria_casa":
            todos.append(("V", jogo["data"]))
        elif jogo["resultado"] == "empate":
            todos.append(("E", jogo["data"]))
        else:
            todos.append(("D", jogo["data"]))

    for _, jogo in jogos_fora.iterrows():
        if jogo["resultado"] == "vitoria_fora":
            todos.append(("V", jogo["data"]))
        elif jogo["resultado"] == "empate":
            todos.append(("E", jogo["data"]))
        else:
            todos.append(("D", jogo["data"]))

    # Ordenamos por data e pegamos os últimos 5
    todos.sort(key=lambda x: x[1])
    ultimos_5 = [r for r, _ in todos[-5:]]

    return " ".join(ultimos_5) if ultimos_5 else "N/A"


def comparar_times(stats_casa: dict, stats_fora: dict) -> dict:
    """
    Compara dois times e gera métricas para o confronto.
    
    Parâmetros:
        stats_casa: estatísticas do time mandante
        stats_fora: estatísticas do time visitante
    
    Retorna:
        Dicionário com métricas do confronto
    """
    # Média de gols esperada no jogo (modelo de Poisson simples)
    # Usamos a média de ataque de um time vs a média de defesa do outro
    gols_esperados_casa = (
        stats_casa["media_gols_marcados"] * 0.6 +
        (stats_fora["media_gols_sofridos"] * 0.4)
    )
    gols_esperados_fora = (
        stats_fora["media_gols_marcados"] * 0.6 +
        (stats_casa["media_gols_sofridos"] * 0.4)
    )

    total_esperado = gols_esperados_casa + gols_esperados_fora

    # Probabilidade de Over 2.5
    prob_over25 = (stats_casa["over25_pct"] + stats_fora["over25_pct"]) / 2

    # Força relativa dos times (aproveitamento ponderado)
    forca_casa = (
        stats_casa["aproveitamento_pct"] * PESO_TEMPORADA +
        stats_casa["aproveitamento_casa"] * PESO_FORMA_RECENTE
    )
    forca_fora = (
        stats_fora["aproveitamento_pct"] * PESO_TEMPORADA +
        stats_fora["aproveitamento_fora"] * PESO_FORMA_RECENTE
    )

    return {
        "gols_esperados_casa": round(gols_esperados_casa, 2),
        "gols_esperados_fora": round(gols_esperados_fora, 2),
        "total_gols_esperado": round(total_esperado, 2),
        "prob_over25":         round(prob_over25, 1),
        "forca_casa":          round(forca_casa, 1),
        "forca_fora":          round(forca_fora, 1),
    }


def analisar_tabela(tabela: list) -> pd.DataFrame:
    """
    Converte a tabela de classificação da API para DataFrame.
    
    Retorna:
        DataFrame com posição, time, pontos, saldo de gols, etc.
    """
    registros = []
    for item in tabela:
        time = item.get("team", {})
        registros.append({
            "posicao":     item.get("position"),
            "time":        time.get("name"),
            "id_time":     time.get("id"),
            "jogos":       item.get("playedGames"),
            "vitorias":    item.get("won"),
            "empates":     item.get("draw"),
            "derrotas":    item.get("lost"),
            "gols_pro":    item.get("goalsFor"),
            "gols_contra": item.get("goalsAgainst"),
            "saldo":       item.get("goalDifference"),
            "pontos":      item.get("points"),
        })
    return pd.DataFrame(registros)
