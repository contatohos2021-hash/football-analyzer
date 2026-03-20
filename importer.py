# ============================================================
# importer.py — Importação de Dados de Arquivos Externos
# ============================================================
# Permite que você use seus próprios dados de arquivos
# Excel ou CSV, além dos dados da API.
# ============================================================

import os
import pandas as pd
from config import PASTA_DADOS

# Garante que a pasta de dados existe
os.makedirs(PASTA_DADOS, exist_ok=True)


def importar_arquivo(caminho: str) -> pd.DataFrame:
    """
    Importa dados de um arquivo Excel ou CSV automaticamente.
    
    Detecta o tipo de arquivo pela extensão e usa o leitor correto.
    
    Parâmetros:
        caminho: caminho completo do arquivo
    
    Retorna:
        DataFrame com os dados do arquivo
    
    Exemplo de uso:
        df = importar_arquivo("dados/jogos_brasileirao.csv")
        df = importar_arquivo("dados/meus_dados.xlsx")
    """
    if not os.path.exists(caminho):
        print(f"❌ Arquivo não encontrado: {caminho}")
        return pd.DataFrame()

    extensao = os.path.splitext(caminho)[1].lower()

    try:
        if extensao == ".csv":
            # Tenta detectar o separador automaticamente
            df = pd.read_csv(caminho, sep=None, engine="python", encoding="utf-8")
            print(f"✅ CSV importado: {len(df)} linhas, {len(df.columns)} colunas")
            return df

        elif extensao in [".xlsx", ".xls"]:
            df = pd.read_excel(caminho)
            print(f"✅ Excel importado: {len(df)} linhas, {len(df.columns)} colunas")
            return df

        else:
            print(f"❌ Formato não suportado: {extensao}")
            print("   Use arquivos .csv, .xlsx ou .xls")
            return pd.DataFrame()

    except Exception as e:
        print(f"❌ Erro ao importar arquivo: {e}")
        return pd.DataFrame()


def validar_colunas_jogos(df: pd.DataFrame) -> bool:
    """
    Verifica se o DataFrame tem as colunas mínimas necessárias.
    
    Colunas obrigatórias:
        - time_casa:  nome do time mandante
        - time_fora:  nome do time visitante
        - gols_casa:  gols marcados pelo mandante
        - gols_fora:  gols marcados pelo visitante
        - data:       data do jogo
    
    Retorna:
        True se válido, False caso contrário
    """
    colunas_necessarias = ["time_casa", "time_fora", "gols_casa", "gols_fora", "data"]
    colunas_faltando = [c for c in colunas_necessarias if c not in df.columns]

    if colunas_faltando:
        print(f"❌ Colunas faltando no arquivo: {colunas_faltando}")
        print(f"   Colunas encontradas: {list(df.columns)}")
        return False

    print("✅ Estrutura do arquivo validada com sucesso.")
    return True


def preparar_dataframe_importado(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara o DataFrame importado no formato padrão da ferramenta.
    
    Adiciona colunas calculadas como:
    - resultado (vitoria_casa / empate / vitoria_fora)
    - total_gols
    
    Retorna:
        DataFrame no formato padrão da ferramenta
    """
    df = df.copy()

    # Converte a coluna de data
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")

    # Garante que os gols são números inteiros
    df["gols_casa"] = pd.to_numeric(df["gols_casa"], errors="coerce").fillna(0).astype(int)
    df["gols_fora"] = pd.to_numeric(df["gols_fora"], errors="coerce").fillna(0).astype(int)

    # Calcula o resultado
    def determinar_resultado(row):
        if row["gols_casa"] > row["gols_fora"]:
            return "vitoria_casa"
        elif row["gols_fora"] > row["gols_casa"]:
            return "vitoria_fora"
        else:
            return "empate"

    df["resultado"]  = df.apply(determinar_resultado, axis=1)
    df["total_gols"] = df["gols_casa"] + df["gols_fora"]

    # Remove linhas inválidas
    df = df.dropna(subset=["time_casa", "time_fora", "gols_casa", "gols_fora"])
    df = df.sort_values("data").reset_index(drop=True)

    print(f"✅ {len(df)} jogos preparados para análise.")
    return df


def exportar_relatorio(resultado: dict, stats_casa: dict, stats_fora: dict,
                        probs: dict, caminho: str = None) -> str:
    """
    Exporta um relatório completo em Excel com todas as análises.
    
    Parâmetros:
        resultado:  recomendação gerada pelo predictor.py
        stats_casa: estatísticas do time da casa
        stats_fora: estatísticas do time visitante
        probs:      probabilidades calculadas
        caminho:    caminho de saída (opcional)
    
    Retorna:
        Caminho do arquivo gerado
    """
    if caminho is None:
        nome = f"relatorio_{stats_casa['time'][:8]}_{stats_fora['time'][:8]}.xlsx"
        caminho = os.path.join("resultados", nome)

    os.makedirs("resultados", exist_ok=True)

    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:

        # --- Aba 1: Recomendação ---
        df_rec = pd.DataFrame([{
            "Status":          resultado["status"],
            "Mercado":         resultado["mercado"],
            "Probabilidade":   f"{resultado['probabilidade']}%",
            "Confiança":       f"{resultado['confianca_pct']}%",
            "Placar Provável": resultado["placar_mais_provavel"],
            "Justificativa":   resultado["justificativa"],
        }])
        df_rec.to_excel(writer, sheet_name="Recomendação", index=False)

        # --- Aba 2: Estatísticas dos Times ---
        df_stats = pd.DataFrame([stats_casa, stats_fora])
        df_stats.to_excel(writer, sheet_name="Estatísticas", index=False)

        # --- Aba 3: Probabilidades ---
        df_probs = pd.DataFrame([{
            "Vitória Casa":  f"{probs['vitoria_casa']}%",
            "Empate":        f"{probs['empate']}%",
            "Vitória Fora":  f"{probs['vitoria_fora']}%",
            "Over 2.5":      f"{probs['over25']}%",
            "Under 2.5":     f"{probs['under25']}%",
            "BTTS Sim":      f"{probs['btts_sim']}%",
            "BTTS Não":      f"{probs['btts_nao']}%",
        }])
        df_probs.to_excel(writer, sheet_name="Probabilidades", index=False)

        # --- Aba 4: Top 5 Placares ---
        df_placares = pd.DataFrame(probs["top5_placares"], columns=["Placar", "Probabilidade (%)"])
        df_placares.to_excel(writer, sheet_name="Top Placares", index=False)

    print(f"📊 Relatório exportado: {caminho}")
    return caminho


def criar_template_csv() -> str:
    """
    Cria um arquivo CSV de exemplo com o formato correto para importar dados.
    
    Retorna:
        Caminho do arquivo criado
    """
    dados_exemplo = {
        "data":      ["2024-01-10", "2024-01-17", "2024-01-24"],
        "time_casa": ["Flamengo",   "Palmeiras",  "Grêmio"],
        "time_fora": ["Palmeiras",  "Corinthians","Flamengo"],
        "gols_casa": [2, 1, 0],
        "gols_fora": [1, 1, 2],
        "competicao":["Brasileirão","Brasileirão","Brasileirão"],
    }

    df = pd.DataFrame(dados_exemplo)
    caminho = os.path.join(PASTA_DADOS, "template_jogos.csv")
    df.to_csv(caminho, index=False, encoding="utf-8")
    print(f"📄 Template criado: {caminho}")
    print("   Preencha este arquivo com seus dados e importe com importar_arquivo()")
    return caminho
