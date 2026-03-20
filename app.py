# ============================================================
# app.py — Interface Web com Streamlit + Claude AI
# ============================================================
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import os

st.set_page_config(
    page_title="Football Analyzer + Claude AI",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

from api_client     import buscar_jogos_competicao, buscar_classificacao
from analyzer       import (jogos_para_dataframe, calcular_estatisticas_time,
                             comparar_times, analisar_tabela)
from predictor      import calcular_probabilidades_poisson, gerar_recomendacao
from importer       import (importar_arquivo, validar_colunas_jogos,
                             preparar_dataframe_importado)
from claude_analyst import (gerar_analise_confronto, responder_pergunta,
                             gerar_resumo_executivo)

# ============================================================
# ESTILOS
# ============================================================
st.markdown("""
<style>
    .recomendacao-box { background:linear-gradient(135deg,#1a1a2e,#16213e);border:2px solid #4fc3f7;border-radius:12px;padding:24px;margin:16px 0; }
    .stat-card { background:#16213e;border-radius:8px;padding:14px;text-align:center; }
    .claude-box { background:linear-gradient(135deg,#0d1117,#1a1a2e);border:2px solid #7c4dff;border-radius:12px;padding:20px;margin:16px 0; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
@st.cache_data(ttl=3600)
def carregar_jogos_api(competicao: str):
    jogos_brutos = buscar_jogos_competicao(competicao)
    return jogos_para_dataframe(jogos_brutos)

@st.cache_data(ttl=3600)
def carregar_classificacao_api(competicao: str):
    tabela = buscar_classificacao(competicao)
    return analisar_tabela(tabela)

def figura_para_streamlit(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    st.image(buf, use_column_width=True)
    plt.close(fig)

def exibir_forma(forma_str: str):
    mapa = {"V": "🟢", "E": "🟡", "D": "🔴"}
    if not forma_str or forma_str == "N/A":
        return "Sem dados"
    return " ".join(mapa.get(r, "⬜") for r in forma_str.split())

def badge_resultado(status: str) -> str:
    if "RECOMENDADA" in status: return "✅"
    elif "RESSALVAS" in status:  return "⚠️"
    else:                        return "❌"

def _fazer_grafico_forma(df, nome_time):
    import numpy as np
    pontos = []
    for _, jogo in df.iterrows():
        if jogo["time_casa"] == nome_time:
            pontos.append(3 if jogo["resultado"]=="vitoria_casa" else 1 if jogo["resultado"]=="empate" else 0)
        elif jogo["time_fora"] == nome_time:
            pontos.append(3 if jogo["resultado"]=="vitoria_fora" else 1 if jogo["resultado"]=="empate" else 0)
    if not pontos:
        st.warning(f"Nenhum jogo encontrado para {nome_time}")
        return None
    media_movel = pd.Series(pontos).rolling(5, min_periods=1).mean()
    pts_acum = np.cumsum(pontos)
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    fig.suptitle(f"Evolução — {nome_time}", color="#eee", fontsize=13)
    cores = ["#81c784" if p==3 else "#ffd54f" if p==1 else "#ef5350" for p in pontos]
    ax.bar(range(len(pontos)), pontos, color=cores, alpha=0.7)
    ax.plot(range(len(media_movel)), media_movel, color="#4fc3f7", linewidth=2)
    ax2 = ax.twinx()
    ax2.plot(range(len(pts_acum)), pts_acum, color="#ffd54f", alpha=0.3, linewidth=1.5)
    ax2.tick_params(colors="#ffd54f")
    ax2.set_ylabel("Pts Acumulados", color="#ffd54f", fontsize=9)
    ax.set_ylim(0, 3.5)
    ax.set_ylabel("Pontos/Jogo", color="#aaa", fontsize=9)
    ax.tick_params(colors="#aaa")
    ax.grid(axis="y", alpha=0.2, color="#555")
    for sp in ax.spines.values(): sp.set_color("#333")
    plt.tight_layout()
    return fig


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/soccer-ball-emoji.png", width=60)
    st.title("Football Analyzer")
    st.caption("Estatísticas + Claude AI")

    st.divider()

    # API Key Football Data
    st.subheader("🔑 Dados de Futebol")
    api_key = st.text_input(
        "Chave football-data.org",
        type="password",
        placeholder="Cole sua API Key aqui",
        help="Cadastre-se grátis em football-data.org/client/register"
    )
    if api_key:
        os.environ["API_KEY"] = api_key
        import config
        config.API_KEY = api_key
        import api_client
        api_client.HEADERS["X-Auth-Token"] = api_key
        st.success("✅ Dados configurados!")

    st.divider()

    # API Key Claude
    st.subheader("🤖 Claude AI")
    claude_api_key = st.text_input(
        "Chave Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Obtenha em console.anthropic.com"
    )
    if claude_api_key:
        st.success("✅ Claude AI pronto!")
    else:
        st.caption("Opcional — habilita análise com IA")

    st.divider()

    # Fonte de Dados
    st.subheader("📂 Fonte de Dados")
    modo = st.radio(
        "Escolha a fonte:",
        ["🌐 API Online", "📄 Arquivo (CSV/Excel)"],
    )

    st.divider()

    # Competição
    COMPETICOES = {
        "Brasileirão Série A": "BSA",
        "Premier League":      "PL",
        "La Liga":             "PD",
        "Bundesliga":          "BL1",
        "Serie A (Itália)":    "SA",
        "Ligue 1":             "FL1",
        "Champions League":    "CL",
    }
    competicao_nome = st.selectbox("🏆 Competição", list(COMPETICOES.keys()))
    competicao_codigo = COMPETICOES[competicao_nome]

    st.divider()
    st.caption("⚠️ Use com responsabilidade. Fins analíticos.")


# ============================================================
# ABAS
# ============================================================
aba_analise, aba_claude, aba_tabela, aba_sobre = st.tabs([
    "⚔️  Analisar Confronto",
    "🤖 Análise Claude AI",
    "🏆 Classificação",
    "ℹ️  Sobre"
])


# ============================================================
# ABA 1: ANÁLISE DE CONFRONTO
# ============================================================
with aba_analise:
    st.header("⚔️ Analisar Confronto")

    df_jogos = pd.DataFrame()

    if modo == "🌐 API Online":
        if not api_key:
            st.warning("👆 Insira sua API Key de dados na barra lateral.")
            st.info("Cadastre-se grátis em [football-data.org](https://www.football-data.org/client/register)")
            st.stop()
        with st.spinner(f"Buscando jogos de {competicao_nome}..."):
            df_jogos = carregar_jogos_api(competicao_codigo)
        if df_jogos.empty:
            st.error("Nenhum dado retornado. Verifique sua API Key e a competição selecionada.")
            st.stop()
        st.success(f"✅ {len(df_jogos)} jogos carregados de {competicao_nome}")
    else:
        arquivo = st.file_uploader("Envie seu arquivo de jogos", type=["csv","xlsx","xls"])
        if arquivo is None:
            st.info("📄 Envie um arquivo CSV ou Excel com os dados dos jogos.")
            with st.expander("Ver formato esperado"):
                st.dataframe(pd.DataFrame({
                    "data":["2024-01-10","2024-01-17"],
                    "time_casa":["Flamengo","Palmeiras"],
                    "time_fora":["Palmeiras","Corinthians"],
                    "gols_casa":[2,1],"gols_fora":[1,1],
                }))
            st.stop()
        caminho_temp = f"/tmp/{arquivo.name}"
        with open(caminho_temp,"wb") as f:
            f.write(arquivo.read())
        df_bruto = importar_arquivo(caminho_temp)
        if df_bruto.empty or not validar_colunas_jogos(df_bruto):
            st.error("Arquivo inválido. Verifique as colunas.")
            st.stop()
        df_jogos = preparar_dataframe_importado(df_bruto)
        st.success(f"✅ {len(df_jogos)} jogos importados.")

    # Seleção dos times
    times_disponiveis = sorted(set(df_jogos["time_casa"].unique()) | set(df_jogos["time_fora"].unique()))
    col1, col2 = st.columns(2)
    with col1:
        time_casa = st.selectbox("🏠 Time da Casa", times_disponiveis, index=0)
    with col2:
        times_fora_lista = [t for t in times_disponiveis if t != time_casa]
        time_fora = st.selectbox("✈️ Time Visitante", times_fora_lista, index=0)

    analisar = st.button("🔍 Analisar Confronto", type="primary", use_container_width=True)
    if not analisar:
        st.info("Configure os times acima e clique em **Analisar Confronto**.")
        st.stop()

    # Processamento
    with st.spinner("Calculando estatísticas e probabilidades..."):
        stats_casa   = calcular_estatisticas_time(df_jogos, time_casa)
        stats_fora   = calcular_estatisticas_time(df_jogos, time_fora)
        comparacao   = comparar_times(stats_casa, stats_fora)
        probs        = calcular_probabilidades_poisson(
                           comparacao["gols_esperados_casa"],
                           comparacao["gols_esperados_fora"])
        recomendacao = gerar_recomendacao(stats_casa, stats_fora, comparacao, probs)

    # Salva na sessão para a aba do Claude usar
    st.session_state["stats_casa"]   = stats_casa
    st.session_state["stats_fora"]   = stats_fora
    st.session_state["comparacao"]   = comparacao
    st.session_state["probs"]        = probs
    st.session_state["recomendacao"] = recomendacao
    st.session_state["df_jogos"]     = df_jogos

    # Recomendação em destaque
    st.divider()
    emoji = badge_resultado(recomendacao["status"])
    cor = "#4CAF50" if "RECOMENDADA" in recomendacao["status"] else "#FFC107" if "RESSALVAS" in recomendacao["status"] else "#f44336"
    st.markdown(f"""
    <div style="background:#0d1117;border:2px solid {cor};border-radius:12px;padding:20px;margin-bottom:16px">
        <h3 style="color:{cor};margin:0">{emoji} {recomendacao['status']}</h3>
        <p style="font-size:1.3em;margin:10px 0 4px"><b>Mercado:</b> <span style="color:#4fc3f7">{recomendacao['mercado']}</span></p>
        <p><b>Probabilidade:</b> {recomendacao['probabilidade']}% &nbsp;|&nbsp; <b>Confiança:</b> {recomendacao['confianca_pct']}% &nbsp;|&nbsp; <b>Placar provável:</b> {recomendacao['placar_mais_provavel']}</p>
        <p style="color:#aaa">💡 {recomendacao['justificativa']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Sugestão de ir para aba Claude
    if claude_api_key:
        st.info("🤖 Clique na aba **Análise Claude AI** para obter a interpretação completa com inteligência artificial!")

    # Probabilidades
    st.subheader("📐 Probabilidades por Mercado")
    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.metric(f"🏠 {time_casa[:10]}", f"{probs['vitoria_casa']}%")
    c2.metric("🤝 Empate",            f"{probs['empate']}%")
    c3.metric(f"✈️ {time_fora[:10]}", f"{probs['vitoria_fora']}%")
    c4.metric("⬆️ Over 2.5",          f"{probs['over25']}%")
    c5.metric("⬇️ Under 2.5",         f"{probs['under25']}%")
    c6.metric("⚽ BTTS Sim",          f"{probs['btts_sim']}%")
    c7.metric("🚫 BTTS Não",          f"{probs['btts_nao']}%")

    st.divider()

    # Estatísticas
    st.subheader("📊 Estatísticas dos Times")
    col_casa, col_fora = st.columns(2)

    def exibir_stats(col, stats, label_local):
        with col:
            st.markdown(f"### 🏟️ {stats['time']} ({label_local})")
            st.markdown(f"**Forma recente:** {exibir_forma(stats['forma_recente'])}")
            dados = {
                "Métrica": ["Jogos","Vitórias","Empates","Derrotas","Aproveitamento Geral","Aprov. Casa/Fora","Gols Marcados","Gols Sofridos","Média Gols Marc.","Média Gols Sofr.","Over 2.5 (%)"],
                "Valor": [stats["total_jogos"],stats["vitorias"],stats["empates"],stats["derrotas"],
                          f"{stats['aproveitamento_pct']}%",
                          f"{stats['aproveitamento_casa'] if label_local=='Casa' else stats['aproveitamento_fora']}%",
                          stats["gols_marcados"],stats["gols_sofridos"],stats["media_gols_marcados"],stats["media_gols_sofridos"],f"{stats['over25_pct']}%"]
            }
            st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)

    exibir_stats(col_casa, stats_casa, "Casa")
    exibir_stats(col_fora, stats_fora, "Fora")

    st.divider()

    # Gráficos
    st.subheader("📈 Visualizações")
    from visualizer import grafico_comparacao_times, grafico_probabilidades_mercados, grafico_matriz_placares
    import seaborn as sns, numpy as np

    tab1,tab2,tab3,tab4,tab5 = st.tabs(["Comparação","Mercados","Matriz Placares",f"Forma {time_casa[:12]}",f"Forma {time_fora[:12]}"])

    with tab1:
        fig2, axes = plt.subplots(1,3,figsize=(14,4))
        fig2.patch.set_facecolor("#1a1a2e")
        for ax, (titulo, chave) in zip(axes, [("Aproveitamento (%)","aproveitamento_pct"),("Média Gols Marc.","media_gols_marcados"),("Over 2.5 (%)","over25_pct")]):
            ax.set_facecolor("#16213e")
            vals=[stats_casa[chave],stats_fora[chave]]
            nomes=[time_casa[:12],time_fora[:12]]
            barras=ax.bar(nomes,vals,color=["#4fc3f7","#ef5350"],width=0.5)
            for b,v in zip(barras,vals):
                ax.text(b.get_x()+b.get_width()/2,b.get_height()/2,f"{v}",ha="center",va="center",fontsize=11,fontweight="bold",color="white")
            ax.set_title(titulo,fontsize=10,color="#ccc")
            ax.tick_params(colors="#aaa")
            for sp in ax.spines.values(): sp.set_color("#333")
            ax.set_ylim(0,max(vals)*1.3+1)
            ax.grid(axis="y",alpha=0.2,color="#555")
        plt.tight_layout()
        figura_para_streamlit(fig2)

    with tab2:
        fig3,axes3=plt.subplots(1,3,figsize=(14,4))
        fig3.patch.set_facecolor("#1a1a2e")
        for ax,(vals,labels,cores,titulo) in zip(axes3,[
            ([probs["vitoria_casa"],probs["empate"],probs["vitoria_fora"]],[f"Casa",f"Empate",f"Fora"],["#4fc3f7","#ffd54f","#ef5350"],"Resultado 1x2"),
            ([probs["over25"],probs["under25"]],[f"Over 2.5",f"Under 2.5"],["#81c784","#e57373"],"Over/Under"),
            ([probs["btts_sim"],probs["btts_nao"]],[f"Sim",f"Não"],["#ce93d8","#90a4ae"],"BTTS"),
        ]):
            ax.set_facecolor("#1a1a2e")
            _,_,autotexts=ax.pie(vals,labels=labels,autopct="%1.1f%%",colors=cores,startangle=90,textprops={"color":"#ccc","fontsize":9})
            for at in autotexts: at.set_color("white"); at.set_fontweight("bold")
            ax.set_title(titulo,color="#ccc",fontsize=10)
        plt.tight_layout()
        figura_para_streamlit(fig3)

    with tab3:
        matriz=probs["matriz"][:6,:6]*100
        fig4,ax4=plt.subplots(figsize=(8,6))
        fig4.patch.set_facecolor("#1a1a2e"); ax4.set_facecolor("#16213e")
        sns.heatmap(matriz,annot=True,fmt=".1f",linewidths=0.5,cmap="YlOrRd",ax=ax4,cbar_kws={"label":"Probabilidade (%)"},annot_kws={"size":10})
        ax4.set_xlabel(f"Gols {time_fora}",color="#ccc"); ax4.set_ylabel(f"Gols {time_casa}",color="#ccc")
        ax4.set_title("Probabilidade de Placares (%)",color="#eee"); ax4.tick_params(colors="#aaa")
        plt.tight_layout()
        figura_para_streamlit(fig4)

    with tab4:
        fig5=_fazer_grafico_forma(df_jogos,time_casa)
        if fig5: figura_para_streamlit(fig5)

    with tab5:
        fig6=_fazer_grafico_forma(df_jogos,time_fora)
        if fig6: figura_para_streamlit(fig6)

    # Top Placares
    st.divider()
    st.subheader("🎯 Top 5 Placares Mais Prováveis")
    cols=st.columns(5)
    for i,(placar,prob) in enumerate(probs["top5_placares"]):
        with cols[i]: st.metric(f"#{i+1}",placar,f"{prob}%")

    # Download
    st.divider()
    from importer import exportar_relatorio
    caminho_rel=f"/tmp/relatorio_{time_casa[:8]}_{time_fora[:8]}.xlsx"
    exportar_relatorio(recomendacao,stats_casa,stats_fora,probs,caminho_rel)
    with open(caminho_rel,"rb") as f:
        st.download_button("⬇️ Baixar Relatório Excel",data=f.read(),
            file_name=f"analise_{time_casa[:12]}_vs_{time_fora[:12]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)


# ============================================================
# ABA 2: CLAUDE AI
# ============================================================
with aba_claude:
    st.header("🤖 Análise com Claude AI")

    if not claude_api_key:
        st.warning("👆 Insira sua chave da Anthropic na barra lateral para usar esta funcionalidade.")
        st.markdown("""
        **Como obter sua chave:**
        1. Acesse [console.anthropic.com](https://console.anthropic.com)
        2. Crie uma conta ou faça login
        3. Vá em **API Keys** → **Create Key**
        4. Cole a chave no campo da barra lateral
        """)
        st.stop()

    if "stats_casa" not in st.session_state:
        st.info("⚔️ Primeiro faça uma análise na aba **Analisar Confronto**, depois volte aqui.")
        st.stop()

    # Recupera dados da sessão
    sc   = st.session_state["stats_casa"]
    sf   = st.session_state["stats_fora"]
    comp = st.session_state["comparacao"]
    pb   = st.session_state["probs"]
    rec  = st.session_state["recomendacao"]

    st.markdown(f"### Confronto: **{sc['time']}** vs **{sf['time']}**")
    st.caption("O Claude irá analisar todos os dados estatísticos calculados e gerar insights em linguagem natural.")

    st.divider()

    # --- SEÇÃO 1: Análise Completa ---
    st.subheader("📋 Análise Completa")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        gerar_analise = st.button("🧠 Gerar Análise Completa", type="primary", use_container_width=True)
    with col_btn2:
        gerar_resumo = st.button("📱 Resumo para WhatsApp", use_container_width=True)

    if gerar_analise:
        with st.spinner("🤖 Claude está analisando o confronto..."):
            analise = gerar_analise_confronto(claude_api_key, sc, sf, comp, pb, rec)
        st.session_state["ultima_analise"] = analise
        st.markdown(f"""
        <div style="background:#0d1117;border:2px solid #7c4dff;border-radius:12px;padding:20px;margin:12px 0">
        {analise.replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)
        # Botão para copiar
        st.download_button("📋 Baixar análise (.txt)", data=analise,
            file_name=f"analise_claude_{sc['time']}_vs_{sf['time']}.txt",
            mime="text/plain")

    if gerar_resumo:
        with st.spinner("🤖 Gerando resumo..."):
            resumo = gerar_resumo_executivo(claude_api_key, sc, sf, rec, pb)
        st.markdown("**📱 Resumo para compartilhar:**")
        st.info(resumo)
        st.download_button("📋 Copiar resumo (.txt)", data=resumo,
            file_name=f"resumo_{sc['time']}_vs_{sf['time']}.txt",
            mime="text/plain")

    st.divider()

    # --- SEÇÃO 2: Chat com o Analista ---
    st.subheader("💬 Pergunte ao Analista")
    st.caption("Faça perguntas específicas sobre o confronto — o Claude responde com base nos dados.")

    # Inicializa histórico do chat
    if "chat_historico" not in st.session_state:
        st.session_state["chat_historico"] = []
    if "chat_jogo" not in st.session_state:
        st.session_state["chat_jogo"] = ""

    jogo_atual = f"{sc['time']}vs{sf['time']}"
    if st.session_state["chat_jogo"] != jogo_atual:
        st.session_state["chat_historico"] = []
        st.session_state["chat_jogo"] = jogo_atual

    # Exibe histórico
    for msg in st.session_state["chat_historico"]:
        role_label = "Você" if msg["role"] == "user" else "🤖 Claude"
        cor_bg = "#1a1a2e" if msg["role"] == "user" else "#0d1117"
        cor_borda = "#4fc3f7" if msg["role"] == "user" else "#7c4dff"
        st.markdown(f"""
        <div style="background:{cor_bg};border-left:3px solid {cor_borda};padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0">
            <small style="color:#888">{role_label}</small><br>{msg['content'].replace(chr(10),'<br>')}
        </div>
        """, unsafe_allow_html=True)

    # Sugestões de perguntas
    st.markdown("**💡 Sugestões:**")
    sugestoes = [
        f"Por que recomendar {rec['mercado']}?",
        "Qual time tem melhor defesa?",
        "O Over 2.5 é seguro nesse jogo?",
        "Quais são os maiores riscos desta entrada?",
    ]
    cols_sug = st.columns(4)
    for i, sug in enumerate(sugestoes):
        with cols_sug[i]:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state["pergunta_input"] = sug

    # Input da pergunta
    pergunta = st.chat_input("Digite sua pergunta sobre o confronto...")

    if "pergunta_input" in st.session_state and st.session_state["pergunta_input"]:
        pergunta = st.session_state.pop("pergunta_input")

    if pergunta:
        st.session_state["chat_historico"].append({"role": "user", "content": pergunta})
        with st.spinner("🤖 Claude está respondendo..."):
            resposta = responder_pergunta(
                claude_api_key, pergunta,
                st.session_state["chat_historico"][:-1],
                sc, sf, pb, rec
            )
        st.session_state["chat_historico"].append({"role": "assistant", "content": resposta})
        st.rerun()

    if st.session_state["chat_historico"]:
        if st.button("🗑️ Limpar conversa", use_container_width=False):
            st.session_state["chat_historico"] = []
            st.rerun()


# ============================================================
# ABA 3: CLASSIFICAÇÃO
# ============================================================
with aba_tabela:
    st.header(f"🏆 Classificação — {competicao_nome}")
    if not api_key:
        st.warning("Insira sua API Key de dados na barra lateral.")
    else:
        if st.button("🔄 Carregar Classificação", type="primary"):
            with st.spinner("Buscando classificação..."):
                df_tabela = carregar_classificacao_api(competicao_codigo)
            if df_tabela.empty:
                st.error("Não foi possível carregar a classificação.")
            else:
                df_tabela["aprov%"] = ((df_tabela["vitorias"]*3+df_tabela["empates"])/(df_tabela["jogos"]*3)*100).round(1)
                df_tabela["media_gols"] = (df_tabela["gols_pro"]/df_tabela["jogos"]).round(2)
                def colorir_posicao(val):
                    if val<=4: return "background-color:#1a472a;color:#81c784"
                    elif val<=6: return "background-color:#1a3a5c;color:#4fc3f7"
                    return ""
                df_exibir = df_tabela[["posicao","time","jogos","vitorias","empates","derrotas","gols_pro","gols_contra","saldo","pontos","aprov%","media_gols"]].rename(columns={
                    "posicao":"Pos","time":"Time","jogos":"J","vitorias":"V","empates":"E","derrotas":"D",
                    "gols_pro":"GP","gols_contra":"GC","saldo":"SG","pontos":"Pts","aprov%":"Aprov%","media_gols":"Méd.Gols"
                })
                st.dataframe(df_exibir.style.map(colorir_posicao,subset=["Pos"]),use_container_width=True,hide_index=True,height=600)
                st.caption("🟢 Zona de classificação europeia/continental  |  🔵 Copa")


# ============================================================
# ABA 4: SOBRE
# ============================================================
with aba_sobre:
    st.header("ℹ️ Sobre o Football Analyzer")
    st.markdown("""
    ### Como funciona?
    O Football Analyzer combina **análise estatística** com **inteligência artificial** para gerar recomendações de entradas em mercados esportivos.

    ### Pipeline
    1. **Coleta** de dados via API football-data.org ou arquivo próprio
    2. **Estatísticas** individuais por time (aproveitamento, médias, forma)
    3. **Modelo de Poisson** → probabilidades para todos os placares
    4. **Recomendação** baseada em confiança mínima configurável
    5. **Claude AI** → análise em linguagem natural + chat interativo

    ### Mercados analisados
    - **1x2** — Vitória casa / Empate / Vitória fora
    - **Over/Under 2.5 gols**
    - **BTTS** — Ambos os times marcam

    ### Tecnologias
    - Python + Streamlit (interface web)
    - Pandas + NumPy (análise de dados)
    - Scipy (modelo de Poisson)
    - Claude Sonnet (Anthropic) — análise com IA

    ---
    > ⚠️ Esta ferramenta é para fins educacionais e analíticos. Aposte com responsabilidade.
    """)
