# ============================================================
# app.py — Interface Web com Streamlit
# ============================================================
# Para rodar:  streamlit run app.py
# ============================================================

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import os

# ---- Configuração da página (deve ser o primeiro comando Streamlit) ----
st.set_page_config(
    page_title="Football Analyzer",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Importações do projeto ----
from api_client  import buscar_jogos_competicao, buscar_classificacao
from analyzer    import (jogos_para_dataframe, calcular_estatisticas_time,
                          comparar_times, analisar_tabela)
from predictor   import calcular_probabilidades_poisson, gerar_recomendacao
from importer    import (importar_arquivo, validar_colunas_jogos,
                          preparar_dataframe_importado)

# ============================================================
# ESTILOS CUSTOMIZADOS
# ============================================================
st.markdown("""
<style>
    /* Cartão de recomendação */
    .recomendacao-box {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 2px solid #4fc3f7;
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
    }
    .stat-card {
        background: #16213e;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .mercado-tag {
        background: #0f3460;
        color: #4fc3f7;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

@st.cache_data(ttl=3600)  # Cache por 1 hora — evita chamadas repetidas à API
def carregar_jogos_api(competicao: str):
    """Busca e converte jogos da API (com cache)."""
    jogos_brutos = buscar_jogos_competicao(competicao)
    return jogos_para_dataframe(jogos_brutos)


@st.cache_data(ttl=3600)
def carregar_classificacao_api(competicao: str):
    """Busca tabela de classificação (com cache)."""
    tabela = buscar_classificacao(competicao)
    return analisar_tabela(tabela)


def figura_para_streamlit(fig) -> None:
    """Converte figura Matplotlib para exibição no Streamlit."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    st.image(buf, use_column_width=True)
    plt.close(fig)


def exibir_forma(forma_str: str):
    """Exibe a forma recente com emojis coloridos."""
    mapa = {"V": "🟢", "E": "🟡", "D": "🔴"}
    if not forma_str or forma_str == "N/A":
        return "Sem dados"
    return " ".join(mapa.get(r, "⬜") for r in forma_str.split())


def badge_resultado(status: str) -> str:
    """Retorna o estilo do badge conforme o status da recomendação."""
    if "RECOMENDADA" in status:
        return "✅"
    elif "RESSALVAS" in status:
        return "⚠️"
    else:
        return "❌"


# ============================================================
# SIDEBAR — CONFIGURAÇÕES
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/soccer-ball-emoji.png", width=60)
    st.title("Football Analyzer")
    st.caption("Análise estatística com modelo preditivo")

    st.divider()

    # --- API Key ---
    st.subheader("🔑 API Key")
    api_key = st.text_input(
        "Chave da football-data.org",
        type="password",
        placeholder="Cole sua API Key aqui",
        help="Cadastre-se grátis em football-data.org/client/register"
    )

    if api_key:
        os.environ["API_KEY"] = api_key
        # Atualiza o header de configuração
        import config
        config.API_KEY = api_key
        import api_client
        api_client.HEADERS["X-Auth-Token"] = api_key
        st.success("API Key configurada!")

    st.divider()

    # --- Fonte de Dados ---
    st.subheader("📂 Fonte de Dados")
    modo = st.radio(
        "Escolha a fonte:",
        ["🌐 API Online", "📄 Arquivo (CSV/Excel)"],
        help="API busca dados em tempo real. Arquivo usa seus próprios dados."
    )

    st.divider()

    # --- Competição ---
    COMPETICOES = {
        "Brasileirão Série A": "BSA",
        "Premier League":      "PL",
        "La Liga":             "PD",
        "Bundesliga":          "BL1",
        "Serie A (Itália)":    "SA",
        "Ligue 1":             "FL1",
        "Champions League":    "CL",
    }

    competicao_nome = st.selectbox(
        "🏆 Competição",
        list(COMPETICOES.keys()),
    )
    competicao_codigo = COMPETICOES[competicao_nome]

    st.divider()
    st.caption("⚠️ Use com responsabilidade. Esta ferramenta é para fins analíticos.")


# ============================================================
# ABAS PRINCIPAIS
# ============================================================
aba_analise, aba_tabela, aba_sobre = st.tabs([
    "⚔️  Analisar Confronto",
    "🏆 Classificação",
    "ℹ️  Sobre"
])


# ============================================================
# ABA 1: ANÁLISE DE CONFRONTO
# ============================================================
with aba_analise:
    st.header("⚔️ Analisar Confronto")

    # ---- Carregamento dos dados ----
    df_jogos = pd.DataFrame()

    if modo == "🌐 API Online":
        if not api_key:
            st.warning("👆 Insira sua API Key na barra lateral para continuar.")
            st.info("Cadastre-se grátis em [football-data.org](https://www.football-data.org/client/register)")
            st.stop()

        with st.spinner(f"Buscando jogos de {competicao_nome}..."):
            df_jogos = carregar_jogos_api(competicao_codigo)

        if df_jogos.empty:
            st.error("Nenhum dado retornado. Verifique sua API Key e a competição selecionada.")
            st.stop()

        st.success(f"✅ {len(df_jogos)} jogos carregados de {competicao_nome}")

    else:  # Modo arquivo
        arquivo = st.file_uploader(
            "Envie seu arquivo de jogos",
            type=["csv", "xlsx", "xls"],
            help="O arquivo deve ter as colunas: time_casa, time_fora, gols_casa, gols_fora, data"
        )

        if arquivo is None:
            st.info("📄 Envie um arquivo CSV ou Excel com os dados dos jogos.")
            with st.expander("Ver formato esperado do arquivo"):
                st.dataframe(pd.DataFrame({
                    "data":       ["2024-01-10", "2024-01-17"],
                    "time_casa":  ["Flamengo",   "Palmeiras"],
                    "time_fora":  ["Palmeiras",  "Corinthians"],
                    "gols_casa":  [2, 1],
                    "gols_fora":  [1, 1],
                }))
            st.stop()

        # Salva temporariamente e importa
        caminho_temp = f"/tmp/{arquivo.name}"
        with open(caminho_temp, "wb") as f:
            f.write(arquivo.read())

        df_bruto = importar_arquivo(caminho_temp)

        if df_bruto.empty or not validar_colunas_jogos(df_bruto):
            st.error("Arquivo inválido. Verifique as colunas necessárias.")
            st.stop()

        df_jogos = preparar_dataframe_importado(df_bruto)
        st.success(f"✅ {len(df_jogos)} jogos importados do arquivo.")

    # ---- Seleção dos times ----
    times_disponiveis = sorted(
        set(df_jogos["time_casa"].unique()) | set(df_jogos["time_fora"].unique())
    )

    col1, col2 = st.columns(2)
    with col1:
        time_casa = st.selectbox("🏠 Time da Casa (Mandante)", times_disponiveis, index=0)
    with col2:
        times_fora = [t for t in times_disponiveis if t != time_casa]
        time_fora = st.selectbox("✈️ Time Visitante", times_fora, index=0)

    # ---- Botão de análise ----
    analisar = st.button("🔍 Analisar Confronto", type="primary", use_container_width=True)

    if not analisar:
        st.info("Configure os times acima e clique em **Analisar Confronto**.")
        st.stop()

    # ============================================================
    # PROCESSAMENTO E EXIBIÇÃO DOS RESULTADOS
    # ============================================================
    with st.spinner("Calculando estatísticas e probabilidades..."):
        stats_casa   = calcular_estatisticas_time(df_jogos, time_casa)
        stats_fora   = calcular_estatisticas_time(df_jogos, time_fora)
        comparacao   = comparar_times(stats_casa, stats_fora)
        probs        = calcular_probabilidades_poisson(
                           comparacao["gols_esperados_casa"],
                           comparacao["gols_esperados_fora"]
                       )
        recomendacao = gerar_recomendacao(stats_casa, stats_fora, comparacao, probs)

    # ---- RECOMENDAÇÃO (destaque) ----
    st.divider()
    emoji = badge_resultado(recomendacao["status"])

    cor_borda = (
        "#4CAF50" if "RECOMENDADA" in recomendacao["status"] else
        "#FFC107" if "RESSALVAS"   in recomendacao["status"] else
        "#f44336"
    )

    st.markdown(f"""
    <div style="background:#0d1117;border:2px solid {cor_borda};border-radius:12px;padding:20px;margin-bottom:16px">
        <h3 style="color:{cor_borda};margin:0">{emoji} {recomendacao['status']}</h3>
        <p style="font-size:1.3em;margin:10px 0 4px"><b>Mercado:</b>
            <span style="color:#4fc3f7">{recomendacao['mercado']}</span>
        </p>
        <p style="margin:4px 0"><b>Probabilidade do modelo:</b> {recomendacao['probabilidade']}% &nbsp;|&nbsp;
           <b>Confiança:</b> {recomendacao['confianca_pct']}% &nbsp;|&nbsp;
           <b>Placar mais provável:</b> {recomendacao['placar_mais_provavel']}
        </p>
        <p style="color:#aaa;margin-top:10px">💡 {recomendacao['justificativa']}</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- PROBABILIDADES (métricas) ----
    st.subheader("📐 Probabilidades por Mercado")

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric(f"🏠 {time_casa[:10]}", f"{probs['vitoria_casa']}%")
    c2.metric("🤝 Empate",            f"{probs['empate']}%")
    c3.metric(f"✈️ {time_fora[:10]}", f"{probs['vitoria_fora']}%")
    c4.metric("⬆️ Over 2.5",          f"{probs['over25']}%")
    c5.metric("⬇️ Under 2.5",         f"{probs['under25']}%")
    c6.metric("⚽ BTTS Sim",          f"{probs['btts_sim']}%")
    c7.metric("🚫 BTTS Não",          f"{probs['btts_nao']}%")

    st.divider()

    # ---- ESTATÍSTICAS DOS TIMES ----
    st.subheader("📊 Estatísticas dos Times")

    col_casa, col_fora = st.columns(2)

    def exibir_stats(col, stats, label_local):
        with col:
            st.markdown(f"### 🏟️ {stats['time']} ({label_local})")
            st.markdown(f"**Forma recente:** {exibir_forma(stats['forma_recente'])}")

            dados = {
                "Métrica": [
                    "Jogos", "Vitórias", "Empates", "Derrotas",
                    "Aproveitamento Geral", "Aprov. em Casa/Fora",
                    "Gols Marcados", "Gols Sofridos",
                    "Média Gols Marcados", "Média Gols Sofridos",
                    "Over 2.5 (%)",
                ],
                "Valor": [
                    stats["total_jogos"], stats["vitorias"],
                    stats["empates"], stats["derrotas"],
                    f"{stats['aproveitamento_pct']}%",
                    f"{stats['aproveitamento_casa'] if label_local == 'Casa' else stats['aproveitamento_fora']}%",
                    stats["gols_marcados"], stats["gols_sofridos"],
                    stats["media_gols_marcados"], stats["media_gols_sofridos"],
                    f"{stats['over25_pct']}%",
                ]
            }
            st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)

    exibir_stats(col_casa, stats_casa, "Casa")
    exibir_stats(col_fora, stats_fora, "Fora")

    st.divider()

    # ---- GRÁFICOS ----
    st.subheader("📈 Visualizações")

    from visualizer import (grafico_comparacao_times, grafico_probabilidades_mercados,
                             grafico_matriz_placares, grafico_forma_recente)

    tab_graf1, tab_graf2, tab_graf3, tab_graf4, tab_graf5 = st.tabs([
        "Comparação", "Mercados", "Matriz de Placares",
        f"Forma {time_casa[:12]}", f"Forma {time_fora[:12]}"
    ])

    with tab_graf1:
        fig = grafico_comparacao_times(stats_casa, stats_fora)
        # Como visualizer.py salva em arquivo, recriamos inline
        fig2, axes = plt.subplots(1, 3, figsize=(14, 4))
        fig2.patch.set_facecolor("#1a1a2e")
        metricas = [
            ("Aproveitamento (%)", "aproveitamento_pct"),
            ("Média Gols Marcados", "media_gols_marcados"),
            ("Over 2.5 (%)", "over25_pct"),
        ]
        for ax, (titulo, chave) in zip(axes, metricas):
            ax.set_facecolor("#16213e")
            vals = [stats_casa[chave], stats_fora[chave]]
            nomes = [time_casa[:12], time_fora[:12]]
            barras = ax.bar(nomes, vals, color=["#4fc3f7", "#ef5350"], width=0.5)
            for b, v in zip(barras, vals):
                ax.text(b.get_x() + b.get_width()/2, b.get_height()/2,
                        f"{v}", ha="center", va="center",
                        fontsize=11, fontweight="bold", color="white")
            ax.set_title(titulo, fontsize=10, color="#ccc")
            ax.tick_params(colors="#aaa")
            for sp in ax.spines.values():
                sp.set_color("#333")
            ax.set_ylim(0, max(vals)*1.3 + 1)
            ax.grid(axis="y", alpha=0.2, color="#555")
        plt.tight_layout()
        figura_para_streamlit(fig2)

    with tab_graf2:
        fig3, axes3 = plt.subplots(1, 3, figsize=(14, 4))
        fig3.patch.set_facecolor("#1a1a2e")
        fig3.suptitle("Probabilidades por Mercado", color="#eee", fontsize=13)

        dados_pizza = [
            (axes3[0], [probs["vitoria_casa"], probs["empate"], probs["vitoria_fora"]],
             [f"Casa\n{time_casa[:8]}", "Empate", f"Fora\n{time_fora[:8]}"],
             ["#4fc3f7","#ffd54f","#ef5350"], "Resultado 1x2"),
            (axes3[1], [probs["over25"], probs["under25"]],
             [f"Over 2.5\n{probs['over25']}%", f"Under 2.5\n{probs['under25']}%"],
             ["#81c784","#e57373"], "Over/Under 2.5"),
            (axes3[2], [probs["btts_sim"], probs["btts_nao"]],
             [f"Sim\n{probs['btts_sim']}%", f"Não\n{probs['btts_nao']}%"],
             ["#ce93d8","#90a4ae"], "BTTS"),
        ]
        for ax, vals, labels, cores, titulo in dados_pizza:
            ax.set_facecolor("#1a1a2e")
            wedges, texts, autotexts = ax.pie(
                vals, labels=labels, autopct="%1.1f%%",
                colors=cores, startangle=90,
                textprops={"color": "#ccc", "fontsize": 8}
            )
            for at in autotexts:
                at.set_color("white")
                at.set_fontweight("bold")
            ax.set_title(titulo, color="#ccc", fontsize=10)
        plt.tight_layout()
        figura_para_streamlit(fig3)

    with tab_graf3:
        import seaborn as sns
        import numpy as np
        matriz = probs["matriz"][:6, :6] * 100
        fig4, ax4 = plt.subplots(figsize=(8, 6))
        fig4.patch.set_facecolor("#1a1a2e")
        ax4.set_facecolor("#16213e")
        sns.heatmap(matriz, annot=True, fmt=".1f", linewidths=0.5,
                    cmap="YlOrRd", ax=ax4,
                    cbar_kws={"label": "Probabilidade (%)"},
                    annot_kws={"size": 10})
        ax4.set_xlabel(f"Gols {time_fora}", color="#ccc")
        ax4.set_ylabel(f"Gols {time_casa}", color="#ccc")
        ax4.set_title(f"Probabilidade de Placares (%)", color="#eee")
        ax4.tick_params(colors="#aaa")
        plt.tight_layout()
        figura_para_streamlit(fig4)

    with tab_graf4:
        fig5 = _fazer_grafico_forma(df_jogos, time_casa)
        if fig5:
            figura_para_streamlit(fig5)

    with tab_graf5:
        fig6 = _fazer_grafico_forma(df_jogos, time_fora)
        if fig6:
            figura_para_streamlit(fig6)

    # ---- TOP PLACARES ----
    st.divider()
    st.subheader("🎯 Top 5 Placares Mais Prováveis")
    cols = st.columns(5)
    for i, (placar, prob) in enumerate(probs["top5_placares"]):
        with cols[i]:
            st.metric(f"#{i+1}", placar, f"{prob}%")

    # ---- DOWNLOAD DO RELATÓRIO ----
    st.divider()
    st.subheader("📄 Exportar Relatório")

    from importer import exportar_relatorio
    caminho_relatorio = f"/tmp/relatorio_{time_casa[:8]}_{time_fora[:8]}.xlsx"
    exportar_relatorio(recomendacao, stats_casa, stats_fora, probs, caminho_relatorio)

    with open(caminho_relatorio, "rb") as f:
        st.download_button(
            label="⬇️ Baixar Relatório Excel",
            data=f.read(),
            file_name=f"analise_{time_casa[:12]}_vs_{time_fora[:12]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ============================================================
# ABA 2: CLASSIFICAÇÃO
# ============================================================
with aba_tabela:
    st.header(f"🏆 Classificação — {competicao_nome}")

    if not api_key:
        st.warning("Insira sua API Key na barra lateral para ver a classificação.")
    else:
        if st.button("🔄 Carregar Classificação", type="primary"):
            with st.spinner("Buscando classificação..."):
                df_tabela = carregar_classificacao_api(competicao_codigo)

            if df_tabela.empty:
                st.error("Não foi possível carregar a classificação.")
            else:
                # Adiciona colunas de aproveitamento e médias
                df_tabela["aprov%"] = (
                    (df_tabela["vitorias"] * 3 + df_tabela["empates"]) /
                    (df_tabela["jogos"] * 3) * 100
                ).round(1)
                df_tabela["media_gols"] = (df_tabela["gols_pro"] / df_tabela["jogos"]).round(2)

                # Estilização da tabela
                def colorir_posicao(val):
                    if val <= 4:
                        return "background-color:#1a472a;color:#81c784"
                    elif val <= 6:
                        return "background-color:#1a3a5c;color:#4fc3f7"
                    return ""

                df_exibir = df_tabela[[
                    "posicao","time","jogos","vitorias","empates","derrotas",
                    "gols_pro","gols_contra","saldo","pontos","aprov%","media_gols"
                ]].rename(columns={
                    "posicao":"Pos","time":"Time","jogos":"J","vitorias":"V",
                    "empates":"E","derrotas":"D","gols_pro":"GP","gols_contra":"GC",
                    "saldo":"SG","pontos":"Pts","aprov%":"Aprov%","media_gols":"Méd.Gols"
                })

                st.dataframe(
                    df_exibir.style.map(colorir_posicao, subset=["Pos"]),
                    use_container_width=True,
                    hide_index=True,
                    height=600,
                )

                st.caption("🟢 Zona de classificação europeia/continental  |  🔵 Copa")


# ============================================================
# ABA 3: SOBRE
# ============================================================
with aba_sobre:
    st.header("ℹ️ Sobre o Football Analyzer")

    st.markdown("""
    ### Como funciona?

    O Football Analyzer usa o **Modelo de Distribuição de Poisson** para calcular as probabilidades
    de cada resultado com base nas médias de gols dos times.

    ### Fluxo da análise

    1. **Coleta de dados** via API football-data.org ou arquivo próprio
    2. **Cálculo de estatísticas** individuais por time (aproveitamento, médias, forma recente)
    3. **Comparação dos times** (força relativa, gols esperados)
    4. **Modelo de Poisson** → matriz de probabilidades para todos os placares
    5. **Geração da recomendação** com base na confiança mínima configurável

    ### Mercados analisados
    - **1x2** — Vitória casa / Empate / Vitória fora
    - **Over/Under 2.5 gols**
    - **BTTS** — Ambos os times marcam

    ### Dados
    Utilizamos a API gratuita da [football-data.org](https://www.football-data.org).
    Cadastre-se para obter sua chave de acesso.

    ---
    > ⚠️ Esta ferramenta é para fins educacionais e de análise estatística.
    > Aposte sempre com responsabilidade.
    """)


# ============================================================
# FUNÇÕES DE GRÁFICO INLINE (sem salvar arquivo)
# ============================================================
def _fazer_grafico_forma(df, nome_time):
    """Gera gráfico de forma recente inline (sem salvar em disco)."""
    import numpy as np

    pontos = []
    for _, jogo in df.iterrows():
        if jogo["time_casa"] == nome_time:
            pontos.append(3 if jogo["resultado"]=="vitoria_casa" else
                          1 if jogo["resultado"]=="empate" else 0)
        elif jogo["time_fora"] == nome_time:
            pontos.append(3 if jogo["resultado"]=="vitoria_fora" else
                          1 if jogo["resultado"]=="empate" else 0)

    if not pontos:
        st.warning(f"Nenhum jogo encontrado para {nome_time}")
        return None

    media_movel = pd.Series(pontos).rolling(5, min_periods=1).mean()
    pts_acum    = np.cumsum(pontos)

    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    fig.suptitle(f"Evolução de Desempenho — {nome_time}", color="#eee", fontsize=13)

    cores = ["#81c784" if p==3 else "#ffd54f" if p==1 else "#ef5350" for p in pontos]
    ax.bar(range(len(pontos)), pontos, color=cores, alpha=0.7)
    ax.plot(range(len(media_movel)), media_movel, color="#4fc3f7",
            linewidth=2, label="Média Móvel (5j)")

    ax2 = ax.twinx()
    ax2.plot(range(len(pts_acum)), pts_acum, color="#ffd54f",
             alpha=0.3, linewidth=1.5, label="Pts Acum.")
    ax2.tick_params(colors="#ffd54f")
    ax2.set_ylabel("Pts Acumulados", color="#ffd54f", fontsize=9)

    ax.set_ylim(0, 3.5)
    ax.set_ylabel("Pontos / Jogo", color="#aaa", fontsize=9)
    ax.set_xlabel("Jogo", color="#aaa", fontsize=9)
    ax.tick_params(colors="#aaa")
    ax.legend(loc="upper left", fontsize=8, facecolor="#1a1a2e",
              edgecolor="#444", labelcolor="#eee")
    ax.grid(axis="y", alpha=0.2, color="#555")
    for sp in ax.spines.values():
        sp.set_color("#333")
    plt.tight_layout()
    return fig
