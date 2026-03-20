# ============================================================
# visualizer.py — Geração de Gráficos e Visualizações
# ============================================================
# Este arquivo transforma os dados em imagens e gráficos
# para facilitar a interpretação visual das estatísticas.
# ============================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from config import PASTA_SAIDA, FORMATO_GRAFICO, DPI_GRAFICO

# Garante que a pasta de saída existe
os.makedirs(PASTA_SAIDA, exist_ok=True)

# Configuração visual padrão
plt.rcParams.update({
    "figure.facecolor": "#1a1a2e",  # Fundo escuro
    "axes.facecolor":   "#16213e",
    "axes.edgecolor":   "#444",
    "axes.labelcolor":  "#ddd",
    "xtick.color":      "#aaa",
    "ytick.color":      "#aaa",
    "text.color":       "#eee",
    "grid.color":       "#333",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "DejaVu Sans",
})

CORES_TIMES = ["#4fc3f7", "#ef5350"]  # Azul para casa, Vermelho para fora


def _salvar(fig, nome_arquivo: str):
    """Salva a figura e fecha para liberar memória."""
    caminho = os.path.join(PASTA_SAIDA, f"{nome_arquivo}.{FORMATO_GRAFICO}")
    fig.savefig(caminho, dpi=DPI_GRAFICO, bbox_inches="tight")
    plt.close(fig)
    print(f"💾 Gráfico salvo: {caminho}")
    return caminho


def grafico_comparacao_times(stats_casa: dict, stats_fora: dict) -> str:
    """
    Gera gráfico de barras comparando as estatísticas dos dois times.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(
        f"{stats_casa['time']}  vs  {stats_fora['time']}",
        fontsize=14, fontweight="bold", color="#fff", y=1.02
    )

    metricas = [
        ("Aproveitamento (%)", "aproveitamento_pct"),
        ("Média de Gols Marcados",  "media_gols_marcados"),
        ("Over 2.5 (%)",       "over25_pct"),
    ]

    for ax, (titulo, chave) in zip(axes, metricas):
        valores = [stats_casa[chave], stats_fora[chave]]
        times   = [stats_casa["time"][:12], stats_fora["time"][:12]]
        barras  = ax.bar(times, valores, color=CORES_TIMES, width=0.5, edgecolor="#555")

        # Valor dentro de cada barra
        for barra, val in zip(barras, valores):
            ax.text(
                barra.get_x() + barra.get_width() / 2,
                barra.get_height() * 0.5,
                f"{val}", ha="center", va="center",
                fontsize=12, fontweight="bold", color="white"
            )

        ax.set_title(titulo, fontsize=10, color="#ccc")
        ax.set_ylim(0, max(valores) * 1.3 + 1)
        ax.grid(axis="y", alpha=0.3)
        ax.tick_params(axis="x", labelsize=9)

    plt.tight_layout()
    return _salvar(fig, f"comparacao_{stats_casa['time'][:8]}_{stats_fora['time'][:8]}")


def grafico_matriz_placares(probs: dict, nome_casa: str, nome_fora: str) -> str:
    """
    Gera heatmap com a probabilidade de cada placar (0x0 a 5x5).
    """
    matriz = probs["matriz"][:6, :6] * 100  # Pegamos apenas 0 a 5 gols

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.suptitle(
        f"Probabilidade de Placares (%)\n{nome_casa} (linhas) vs {nome_fora} (colunas)",
        fontsize=12, color="#fff"
    )

    sns.heatmap(
        matriz,
        annot=True, fmt=".1f", linewidths=0.5,
        cmap="YlOrRd", ax=ax,
        cbar_kws={"label": "Probabilidade (%)"}
    )

    ax.set_xlabel(f"Gols {nome_fora}", fontsize=10)
    ax.set_ylabel(f"Gols {nome_casa}", fontsize=10)

    plt.tight_layout()
    return _salvar(fig, f"placares_{nome_casa[:8]}_{nome_fora[:8]}")


def grafico_probabilidades_mercados(probs: dict, nome_casa: str, nome_fora: str) -> str:
    """
    Gera gráfico de pizza com as probabilidades dos principais mercados.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Probabilidades por Mercado", fontsize=14, color="#fff")

    # --- 1x2 ---
    ax1 = axes[0]
    vals_1x2   = [probs["vitoria_casa"], probs["empate"], probs["vitoria_fora"]]
    labels_1x2 = [f"Casa\n{nome_casa[:10]}", "Empate", f"Fora\n{nome_fora[:10]}"]
    cores_1x2  = ["#4fc3f7", "#ffd54f", "#ef5350"]
    wedges, texts, autotexts = ax1.pie(
        vals_1x2, labels=labels_1x2, autopct="%1.1f%%",
        colors=cores_1x2, startangle=90,
        textprops={"color": "#ddd", "fontsize": 9}
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontweight("bold")
    ax1.set_title("Resultado (1x2)", color="#ccc")

    # --- Over/Under ---
    ax2 = axes[1]
    vals_ou   = [probs["over25"], probs["under25"]]
    labels_ou = [f"Over 2.5\n{probs['over25']}%", f"Under 2.5\n{probs['under25']}%"]
    cores_ou  = ["#81c784", "#e57373"]
    ax2.pie(vals_ou, labels=labels_ou, colors=cores_ou, startangle=90,
            textprops={"color": "#ddd", "fontsize": 10})
    ax2.set_title("Over/Under 2.5 Gols", color="#ccc")

    # --- BTTS ---
    ax3 = axes[2]
    vals_btts   = [probs["btts_sim"], probs["btts_nao"]]
    labels_btts = [f"Sim\n{probs['btts_sim']}%", f"Não\n{probs['btts_nao']}%"]
    cores_btts  = ["#ce93d8", "#90a4ae"]
    ax3.pie(vals_btts, labels=labels_btts, colors=cores_btts, startangle=90,
            textprops={"color": "#ddd", "fontsize": 10})
    ax3.set_title("Ambos Marcam (BTTS)", color="#ccc")

    plt.tight_layout()
    return _salvar(fig, f"mercados_{nome_casa[:8]}_{nome_fora[:8]}")


def grafico_classificacao(df_tabela: pd.DataFrame, competicao: str, top_n: int = 10) -> str:
    """
    Gera gráfico de barras horizontais com a tabela de classificação.
    """
    df = df_tabela.head(top_n).copy()

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(f"Classificação — {competicao} (Top {top_n})", fontsize=13, color="#fff")

    cores = ["#ffd700" if i < 4 else "#4fc3f7" if i < 6 else "#90a4ae"
             for i in range(len(df))]

    barras = ax.barh(df["time"].str[:20][::-1], df["pontos"][::-1],
                     color=cores[::-1], edgecolor="#444")

    for barra, pontos in zip(barras, df["pontos"][::-1]):
        ax.text(barra.get_width() + 0.3, barra.get_y() + barra.get_height() / 2,
                f"{int(pontos)} pts", va="center", fontsize=9, color="#ddd")

    ax.set_xlabel("Pontos", color="#aaa")
    ax.grid(axis="x", alpha=0.3)

    legenda = [
        mpatches.Patch(color="#ffd700", label="Zona de Champions/Libertadores"),
        mpatches.Patch(color="#4fc3f7", label="Zona de Copa"),
        mpatches.Patch(color="#90a4ae", label="Demais"),
    ]
    ax.legend(handles=legenda, loc="lower right", fontsize=8,
              facecolor="#1a1a2e", edgecolor="#444", labelcolor="#ddd")

    plt.tight_layout()
    return _salvar(fig, f"classificacao_{competicao}")


def grafico_forma_recente(df_jogos: pd.DataFrame, nome_time: str) -> str:
    """
    Gera gráfico de linha com o desempenho do time ao longo do tempo.
    """
    # Filtramos os jogos do time e calculamos pontos por jogo
    pontos = []
    datas  = []

    for _, jogo in df_jogos.iterrows():
        if jogo["time_casa"] == nome_time:
            if jogo["resultado"] == "vitoria_casa":
                pontos.append(3)
            elif jogo["resultado"] == "empate":
                pontos.append(1)
            else:
                pontos.append(0)
            datas.append(jogo["data"])
        elif jogo["time_fora"] == nome_time:
            if jogo["resultado"] == "vitoria_fora":
                pontos.append(3)
            elif jogo["resultado"] == "empate":
                pontos.append(1)
            else:
                pontos.append(0)
            datas.append(jogo["data"])

    if not pontos:
        print(f"⚠️  Nenhum jogo encontrado para {nome_time}")
        return ""

    # Média móvel dos últimos 5 jogos
    pts_acumulados = np.cumsum(pontos)
    media_movel    = pd.Series(pontos).rolling(5, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.suptitle(f"Evolução de Desempenho — {nome_time}", fontsize=13, color="#fff")

    # Pontos acumulados
    ax2 = ax.twinx()
    ax2.plot(range(len(pts_acumulados)), pts_acumulados,
             color="#ffd54f", alpha=0.3, linewidth=1.5, label="Pontos Acumulados")
    ax2.set_ylabel("Pontos Acumulados", color="#ffd54f", fontsize=9)
    ax2.tick_params(axis="y", colors="#ffd54f")

    # Média móvel
    cores_pts = ["#81c784" if p == 3 else "#ffd54f" if p == 1 else "#ef5350" for p in pontos]
    ax.bar(range(len(pontos)), pontos, color=cores_pts, alpha=0.7, label="Pontos por Jogo")
    ax.plot(range(len(media_movel)), media_movel,
            color="#4fc3f7", linewidth=2, label="Média Móvel (5 jogos)")
    ax.set_ylim(0, 3.5)
    ax.set_ylabel("Pontos por Jogo", color="#aaa", fontsize=9)
    ax.set_xlabel("Número do Jogo", color="#aaa", fontsize=9)

    legenda = [
        mpatches.Patch(color="#81c784", label="Vitória (3 pts)"),
        mpatches.Patch(color="#ffd54f", label="Empate (1 pt)"),
        mpatches.Patch(color="#ef5350", label="Derrota (0 pts)"),
    ]
    ax.legend(handles=legenda, loc="upper left", fontsize=8,
              facecolor="#1a1a2e", edgecolor="#444", labelcolor="#ddd")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    return _salvar(fig, f"forma_{nome_time[:15]}")
