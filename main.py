# ============================================================
# main.py — Arquivo Principal do Football Analyzer
# ============================================================
# Este é o único arquivo que você precisa executar!
# Para rodar:  python main.py
#
# ANTES DE COMEÇAR:
# 1. Instale as dependências:
#    pip install -r requirements.txt
# 2. Cadastre-se em: https://www.football-data.org/client/register
# 3. Cole sua API Key no arquivo config.py
# ============================================================

from tabulate import tabulate
from config import COMPETITIONS

from api_client  import (buscar_jogos_competicao, buscar_classificacao,
                          buscar_jogos_time, buscar_times_competicao)
from analyzer    import (jogos_para_dataframe, calcular_estatisticas_time,
                          comparar_times, analisar_tabela)
from predictor   import calcular_probabilidades_poisson, gerar_recomendacao
from visualizer  import (grafico_comparacao_times, grafico_matriz_placares,
                          grafico_probabilidades_mercados, grafico_forma_recente)
from importer    import (importar_arquivo, validar_colunas_jogos,
                          preparar_dataframe_importado, exportar_relatorio,
                          criar_template_csv)


# ============================================================
# CONFIGURAÇÃO: ALTERE AQUI O QUE VOCÊ QUER ANALISAR
# ============================================================

# Competição a analisar (veja as opções em config.py)
COMPETICAO = "BSA"          # Brasileirão Série A

# Times que vão se enfrentar
NOME_TIME_CASA = "Flamengo"
NOME_TIME_FORA = "Palmeiras"

# Modo de dados: "api" (busca online) ou "arquivo" (usa seu CSV/Excel)
MODO = "api"

# Se MODO = "arquivo", informe o caminho do seu arquivo aqui
CAMINHO_ARQUIVO = "dados/meus_jogos.csv"


# ============================================================
def imprimir_cabecalho(texto: str):
    """Imprime um título formatado no terminal."""
    print("\n" + "=" * 60)
    print(f"  {texto}")
    print("=" * 60)


def executar_analise_completa(df_jogos, nome_casa: str, nome_fora: str):
    """
    Executa o pipeline completo de análise para dois times.
    
    Este é o fluxo completo da ferramenta:
    1. Calcula estatísticas de cada time
    2. Compara os dois times
    3. Calcula probabilidades via Poisson
    4. Gera recomendação de entrada
    5. Cria gráficos
    6. Exporta relatório Excel
    """

    # --- PASSO 1: Estatísticas individuais ---
    imprimir_cabecalho(f"📊 Estatísticas: {nome_casa}")
    stats_casa = calcular_estatisticas_time(df_jogos, nome_casa)

    tabela_stats_casa = [
        ["Jogos",              stats_casa["total_jogos"]],
        ["Vitórias",           stats_casa["vitorias"]],
        ["Empates",            stats_casa["empates"]],
        ["Derrotas",           stats_casa["derrotas"]],
        ["Aproveitamento",     f"{stats_casa['aproveitamento_pct']}%"],
        ["Gols Marcados",      stats_casa["gols_marcados"]],
        ["Gols Sofridos",      stats_casa["gols_sofridos"]],
        ["Méd. Gols Marcados", stats_casa["media_gols_marcados"]],
        ["Over 2.5 (%)",       f"{stats_casa['over25_pct']}%"],
        ["Forma Recente",      stats_casa["forma_recente"]],
    ]
    print(tabulate(tabela_stats_casa, headers=["Estatística", "Valor"], tablefmt="rounded_outline"))

    imprimir_cabecalho(f"📊 Estatísticas: {nome_fora}")
    stats_fora = calcular_estatisticas_time(df_jogos, nome_fora)

    tabela_stats_fora = [
        ["Jogos",              stats_fora["total_jogos"]],
        ["Vitórias",           stats_fora["vitorias"]],
        ["Empates",            stats_fora["empates"]],
        ["Derrotas",           stats_fora["derrotas"]],
        ["Aproveitamento",     f"{stats_fora['aproveitamento_pct']}%"],
        ["Gols Marcados",      stats_fora["gols_marcados"]],
        ["Gols Sofridos",      stats_fora["gols_sofridos"]],
        ["Méd. Gols Marcados", stats_fora["media_gols_marcados"]],
        ["Over 2.5 (%)",       f"{stats_fora['over25_pct']}%"],
        ["Forma Recente",      stats_fora["forma_recente"]],
    ]
    print(tabulate(tabela_stats_fora, headers=["Estatística", "Valor"], tablefmt="rounded_outline"))

    # --- PASSO 2: Comparação entre os times ---
    imprimir_cabecalho(f"⚔️  Confronto: {nome_casa} vs {nome_fora}")
    comparacao = comparar_times(stats_casa, stats_fora)

    tabela_comp = [
        ["Gols Esperados (Casa)",   comparacao["gols_esperados_casa"]],
        ["Gols Esperados (Fora)",   comparacao["gols_esperados_fora"]],
        ["Total de Gols Esperados", comparacao["total_gols_esperado"]],
        ["Prob. Over 2.5 (%)",      f"{comparacao['prob_over25']}%"],
        [f"Força {nome_casa}",      comparacao["forca_casa"]],
        [f"Força {nome_fora}",      comparacao["forca_fora"]],
    ]
    print(tabulate(tabela_comp, headers=["Métrica", "Valor"], tablefmt="rounded_outline"))

    # --- PASSO 3: Probabilidades via modelo de Poisson ---
    imprimir_cabecalho("📐 Probabilidades (Modelo de Poisson)")
    probs = calcular_probabilidades_poisson(
        comparacao["gols_esperados_casa"],
        comparacao["gols_esperados_fora"]
    )

    tabela_probs = [
        [f"Vitória {nome_casa}",  f"{probs['vitoria_casa']}%"],
        ["Empate",                f"{probs['empate']}%"],
        [f"Vitória {nome_fora}",  f"{probs['vitoria_fora']}%"],
        ["Over 2.5 gols",         f"{probs['over25']}%"],
        ["Under 2.5 gols",        f"{probs['under25']}%"],
        ["Ambos Marcam (Sim)",    f"{probs['btts_sim']}%"],
        ["Ambos Marcam (Não)",    f"{probs['btts_nao']}%"],
    ]
    print(tabulate(tabela_probs, headers=["Mercado", "Probabilidade"], tablefmt="rounded_outline"))

    print("\n🎯 Top 5 Placares Mais Prováveis:")
    for placar, prob in probs["top5_placares"]:
        print(f"   {placar}  →  {prob}%")

    # --- PASSO 4: Recomendação de entrada ---
    imprimir_cabecalho("✅ RECOMENDAÇÃO DE ENTRADA")
    recomendacao = gerar_recomendacao(stats_casa, stats_fora, comparacao, probs)

    print(f"  {recomendacao['status']}")
    print(f"  Mercado:        {recomendacao['mercado']}")
    print(f"  Probabilidade:  {recomendacao['probabilidade']}%")
    print(f"  Confiança:      {recomendacao['confianca_pct']}%")
    print(f"  Placar Provável:{recomendacao['placar_mais_provavel']}")
    print(f"\n  💡 {recomendacao['justificativa']}")

    if len(recomendacao["todos_candidatos"]) > 1:
        print("\n  📋 Outros mercados analisados:")
        for candidato in recomendacao["todos_candidatos"][1:]:
            print(f"     • {candidato['mercado']}: {candidato['probabilidade']}%")

    # --- PASSO 5: Gráficos ---
    imprimir_cabecalho("📈 Gerando Gráficos...")
    grafico_comparacao_times(stats_casa, stats_fora)
    grafico_matriz_placares(probs, nome_casa, nome_fora)
    grafico_probabilidades_mercados(probs, nome_casa, nome_fora)
    grafico_forma_recente(df_jogos, nome_casa)
    grafico_forma_recente(df_jogos, nome_fora)

    # --- PASSO 6: Exportar relatório ---
    imprimir_cabecalho("📄 Exportando Relatório Excel...")
    exportar_relatorio(recomendacao, stats_casa, stats_fora, probs)

    print("\n✅ Análise concluída! Verifique a pasta 'resultados/'")
    return recomendacao


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
if __name__ == "__main__":

    print("⚽ Football Analyzer — Iniciando...")
    print(f"   Competição: {COMPETICAO}")
    print(f"   Jogo: {NOME_TIME_CASA} vs {NOME_TIME_FORA}")
    print(f"   Modo: {MODO.upper()}")

    df_jogos = None

    # ---- Modo API: busca dados online ----
    if MODO == "api":
        print("\n🌐 Buscando dados da API...")
        jogos_brutos = buscar_jogos_competicao(COMPETICAO)
        df_jogos = jogos_para_dataframe(jogos_brutos)

        if df_jogos.empty:
            print("❌ Nenhum dado retornado pela API.")
            print("   Verifique sua API Key no arquivo config.py")
            exit(1)

    # ---- Modo Arquivo: usa dados locais ----
    elif MODO == "arquivo":
        print(f"\n📂 Importando arquivo: {CAMINHO_ARQUIVO}")
        df_bruto = importar_arquivo(CAMINHO_ARQUIVO)

        if df_bruto.empty:
            print("❌ Arquivo vazio ou inválido.")
            print("   Criando um template de exemplo...")
            criar_template_csv()
            exit(1)

        if not validar_colunas_jogos(df_bruto):
            print("   Ajuste as colunas do arquivo conforme o template.")
            exit(1)

        df_jogos = preparar_dataframe_importado(df_bruto)

    else:
        print(f"❌ Modo inválido: {MODO}. Use 'api' ou 'arquivo'.")
        exit(1)

    # ---- Verificação dos times ----
    times_disponiveis = set(df_jogos["time_casa"].unique()) | set(df_jogos["time_fora"].unique())

    if NOME_TIME_CASA not in times_disponiveis:
        print(f"❌ Time não encontrado: '{NOME_TIME_CASA}'")
        print(f"   Times disponíveis: {sorted(times_disponiveis)[:10]}...")
        exit(1)

    if NOME_TIME_FORA not in times_disponiveis:
        print(f"❌ Time não encontrado: '{NOME_TIME_FORA}'")
        print(f"   Times disponíveis: {sorted(times_disponiveis)[:10]}...")
        exit(1)

    # ---- Executa a análise completa ----
    executar_analise_completa(df_jogos, NOME_TIME_CASA, NOME_TIME_FORA)
