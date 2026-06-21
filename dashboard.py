from pathlib import Path
import base64
import unicodedata

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from shapely.geometry import Point
from streamlit_folium import st_folium


BASE_DIR = Path(__file__).parent
RESULTADOS_DIR = BASE_DIR / "resultados"
ASSETS_DIR = BASE_DIR / "assets"

ARQUIVOS = {
    "areas_risco": RESULTADOS_DIR / "areas_risco.geojson",
    "vias_risco": RESULTADOS_DIR / "vias_afetadas.geojson",
    "vias_risco_nomes": RESULTADOS_DIR / "vias_afetadas_nomes.csv",
    "resumo_risco": RESULTADOS_DIR / "resumo_vias_afetadas.csv",
    "dados_setores": RESULTADOS_DIR / "dados_setores_planilha.csv",
    "setores_sem_correspondencia": RESULTADOS_DIR / "setores_sem_correspondencia_na_planilha.csv",
    "correcoes_nomes_vias": RESULTADOS_DIR / "correcoes_nomes_vias.csv",
    "manchas_tr": RESULTADOS_DIR / "manchas_inundacao_por_tempo_recorrencia.geojson",
    "vias_tr": RESULTADOS_DIR / "vias_afetadas_por_tempo_recorrencia_com_mdt_raster.geojson",
    "indicadores_tr": RESULTADOS_DIR / "indicadores_por_tempo_recorrencia_com_mdt_raster.csv",
}

COR_AZUL_ESCURO = "#12395b"
COR_AZUL = "#1f78b4"
COR_AZUL_CLARO = "#74add1"
COR_VERMELHO = "#d73027"
COR_LARANJA = "#f57c00"
COR_CINZA_TEXTO = "#27313a"
COR_CINZA_FUNDO = "#f4f7fb"

CORES_MANCHAS = {
    "TR 10 anos": "#74add1",
    "TR 50 anos": "#2b83ba",
    "TR 100 anos": "#08306b",
}

CORES_VIAS_TR = {
    "TR 10 anos": "#fdae61",
    "TR 50 anos": "#f46d43",
    "TR 100 anos": "#d7191c",
}

PAGINAS = [
    "Visão Geral",
    "Mapa",
    "Consulta",
    "Dados",
    "Orientações",
]


st.set_page_config(
    page_title="Painel de Apoio a identificação de Riscos",
    layout="wide",
)


def aplicar_css():
    st.markdown(
        f"""
<style>
    .stApp {{
        background: {COR_CINZA_FUNDO};
        color: {COR_CINZA_TEXTO};
    }}

    section[data-testid="stSidebar"] {{
        background: #ffffff;
        border-right: 1px solid #d9e2ec;
        color: #111111;
    }}

    section[data-testid="stSidebar"] > div:first-child {{
        min-height: 100vh;
    }}

    section[data-testid="stSidebar"] * {{
        color: #111111 !important;
    }}

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {{
        text-align: justify;
    }}

    h1, h2, h3 {{
        color: {COR_AZUL_ESCURO};
    }}

    div[data-testid="stMetric"] {{
        background: #ffffff;
        border: 1px solid #dfe7ef;
        border-left: 5px solid {COR_LARANJA};
        border-radius: 8px;
        padding: 16px;
        min-height: 118px;
        box-shadow: 0 1px 2px rgba(18, 57, 91, 0.06);
    }}

    div[data-testid="stMetric"] * {{
        color: #111111 !important;
    }}

    .hero {{
        background: {COR_AZUL_ESCURO};
        color: white;
        border-radius: 8px;
        padding: 26px 30px;
        margin-bottom: 20px;
    }}

    .hero h1 {{
        color: white;
        margin: 0 0 8px 0;
    }}

    .hero p {{
        color: #e7eef6;
        margin: 0;
        font-size: 1.02rem;
    }}

    .info-card {{
        background: #ffffff;
        color: #111111;
        border: 1px solid #dfe7ef;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 1px 2px rgba(18, 57, 91, 0.05);
    }}

    .info-card * {{
        color: #111111 !important;
    }}

    .result-card {{
        background: #ffffff;
        color: #111111;
        border: 1px solid #dfe7ef;
        border-left: 5px solid {COR_AZUL};
        border-radius: 8px;
        padding: 14px 16px;
        margin: 10px 0;
    }}

    .result-card * {{
        color: #111111 !important;
    }}

    .warning-card {{
        border-left-color: {COR_LARANJA};
    }}

    .danger-card {{
        border-left-color: {COR_VERMELHO};
    }}

    .small-muted {{
        color: #61707d;
        font-size: 0.92rem;
    }}

    .sidebar-brand {{
        border-bottom: 1px solid #d9e2ec;
        margin-bottom: 18px;
        padding-bottom: 14px;
        text-align: center;
    }}

    .sidebar-brand img {{
        display: block;
        margin: 0 auto;
        max-width: 100%;
        object-fit: contain;
    }}

    .sidebar-brand-title {{
        color: #111111;
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: 0;
        margin-bottom: 2px;
        text-align: center;
    }}

    .sidebar-brand-subtitle {{
        color: #111111;
        font-size: 0.78rem;
        line-height: 1.25;
        margin-bottom: 12px;
        text-align: justify;
    }}

    .logo-placeholder {{
        align-items: center;
        background: #f4f7fb;
        border: 1px solid #d9e2ec;
        border-radius: 6px;
        color: #111111;
        display: flex;
        font-size: 0.7rem;
        font-weight: 700;
        height: 44px;
        justify-content: center;
        text-align: center;
        width: 100%;
    }}

    .sidebar-partners {{
        background: #ffffff;
        color: #111111;
        font-size: 0.76rem;
        line-height: 1.25;
        margin-top: 34vh;
        padding: 10px 0 0 0;
        position: sticky;
        top: calc(100vh - 260px);
        width: 100%;
        z-index: 999;
    }}

    .sidebar-partners-title {{
        color: #111111;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 8px;
        text-align: justify;
    }}

    .sidebar-logo-row {{
        align-items: center;
        display: grid;
        gap: 6px;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        width: 100%;
    }}

    .sidebar-logo-box {{
        align-items: center;
        display: flex;
        height: 48px;
        justify-content: center;
        overflow: hidden;
        width: 100%;
    }}

    .sidebar-partners img {{
        height: auto;
        max-height: 44px;
        max-width: 100%;
        object-fit: contain;
        width: auto;
    }}

    .sidebar-footer-text {{
        color: #111111;
        font-size: 0.76rem;
        line-height: 1.25;
        margin-top: 12px;
        text-align: justify;
    }}

    div[data-testid="stDownloadButton"] button {{
        background: {COR_AZUL_ESCURO};
        border: 1px solid {COR_AZUL_ESCURO};
        border-radius: 6px;
        color: #ffffff;
        font-weight: 700;
    }}

    div[data-testid="stDownloadButton"] button:hover,
    div[data-testid="stDownloadButton"] button:focus {{
        background: {COR_AZUL};
        border-color: {COR_AZUL};
        color: #ffffff;
    }}

    div[data-testid="stDownloadButton"] button *,
    div[data-testid="stDownloadButton"] button:hover *,
    div[data-testid="stDownloadButton"] button:focus * {{
        color: inherit !important;
    }}
</style>
""",
        unsafe_allow_html=True,
    )


def reparar_texto(texto):
    if not isinstance(texto, str):
        return texto

    corrigido = texto
    for _ in range(3):
        try:
            novo = corrigido.encode("latin1").decode("utf-8")
        except UnicodeError:
            break
        if novo == corrigido:
            break
        corrigido = novo

    return " ".join(corrigido.split())


def limpar_textos_dataframe(df):
    if df.empty:
        return df

    resultado = df.copy()
    for coluna in resultado.columns:
        if coluna == "geometry":
            continue
        if resultado[coluna].dtype == "object":
            resultado[coluna] = resultado[coluna].map(reparar_texto)
    return resultado


@st.cache_data(show_spinner=False)
def carregar_geojson(caminho):
    if not caminho.exists():
        return gpd.GeoDataFrame()
    return limpar_textos_dataframe(gpd.read_file(caminho))


@st.cache_data(show_spinner=False)
def carregar_csv(caminho):
    if not caminho.exists():
        return pd.DataFrame()
    for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            return limpar_textos_dataframe(pd.read_csv(caminho, encoding=encoding))
        except UnicodeDecodeError:
            continue
    return limpar_textos_dataframe(
        pd.read_csv(caminho, encoding="latin1", encoding_errors="replace")
    )


def preparar_correcoes_nomes(correcoes):
    if correcoes.empty:
        return {}

    col_original = identificar_coluna(
        correcoes, ["nome_original", "original", "nome incorreto", "nome_errado"])
    col_corrigido = identificar_coluna(
        correcoes, ["nome_corrigido", "corrigido", "nome correto", "nome_correto"])

    if col_original is None or col_corrigido is None:
        return {}

    tabela = correcoes[[col_original, col_corrigido]].dropna().copy()
    tabela[col_original] = tabela[col_original].astype(str).map(reparar_texto)
    tabela[col_corrigido] = tabela[col_corrigido].astype(str).map(reparar_texto)
    tabela = tabela[(tabela[col_original] != "") &
                    (tabela[col_corrigido] != "")]

    return {
        normalizar_texto(original): corrigido
        for original, corrigido in zip(tabela[col_original], tabela[col_corrigido])
    }


def aplicar_correcoes_nomes(df, correcoes):
    if df.empty or not correcoes:
        return df

    resultado = df.copy()
    colunas_nome = [
        coluna
        for coluna in [
            "NOME",
            "nome_via",
            "nome",
            "Name",
            "name",
            "rua",
            "RUA",
            "logradouro",
            "LOGRADOURO",
            "nm_lograd",
            "NM_LOGRAD",
            "nm_logradouro",
            "NM_LOGRADOURO",
            "descricao",
            "DESCRICAO",
        ]
        if coluna in resultado.columns
    ]

    for coluna in colunas_nome:
        resultado[coluna] = resultado[coluna].apply(
            lambda valor: correcoes.get(normalizar_texto(valor), reparar_texto(valor))
        )

    return resultado


def nome_via_invalido(valor):
    if pd.isna(valor):
        return True

    texto = normalizar_texto(reparar_texto(valor))
    return texto in {
        "",
        "nan",
        "none",
        "null",
        "sem nome",
        "sem nome informado",
        "nao informado",
        "não informado",
    }


def remover_vias_sem_nome(df, coluna_nome=None):
    if df.empty:
        return df

    coluna = coluna_nome or identificar_coluna_nome_via(df)
    if coluna is None or coluna not in df.columns:
        return df

    return df[~df[coluna].map(nome_via_invalido)].copy()


def carregar_dados():
    correcoes = preparar_correcoes_nomes(
        carregar_csv(ARQUIVOS["correcoes_nomes_vias"]))

    dados = {
        "areas_risco": carregar_geojson(ARQUIVOS["areas_risco"]),
        "vias_risco": carregar_geojson(ARQUIVOS["vias_risco"]),
        "vias_risco_nomes": carregar_csv(ARQUIVOS["vias_risco_nomes"]),
        "resumo_risco": carregar_csv(ARQUIVOS["resumo_risco"]),
        "dados_setores": carregar_csv(ARQUIVOS["dados_setores"]),
        "setores_sem_correspondencia": carregar_csv(ARQUIVOS["setores_sem_correspondencia"]),
        "manchas_tr": carregar_geojson(ARQUIVOS["manchas_tr"]),
        "vias_tr": carregar_geojson(ARQUIVOS["vias_tr"]),
        "indicadores_tr": carregar_csv(ARQUIVOS["indicadores_tr"]),
        "correcoes_nomes_vias": carregar_csv(ARQUIVOS["correcoes_nomes_vias"]),
    }

    if not dados["vias_risco_nomes"].empty and len(dados["vias_risco_nomes"].columns) >= 4:
        primeira_coluna = dados["vias_risco_nomes"].columns[0]
        if nome_via_invalido(primeira_coluna):
            dados["vias_risco_nomes"] = dados["vias_risco_nomes"].rename(
                columns={
                    dados["vias_risco_nomes"].columns[0]: "NOME",
                    dados["vias_risco_nomes"].columns[1]: "tipo_risco",
                    dados["vias_risco_nomes"].columns[2]: "extensao_afetada_m",
                    dados["vias_risco_nomes"].columns[3]: "trechos_afetados",
                }
            )

    for chave in ["vias_risco", "vias_risco_nomes", "vias_tr"]:
        dados[chave] = aplicar_correcoes_nomes(dados[chave], correcoes)

    dados["vias_risco"] = remover_vias_sem_nome(dados["vias_risco"])
    dados["vias_tr"] = remover_vias_sem_nome(dados["vias_tr"])
    if not dados["vias_risco_nomes"].empty:
        primeira_coluna = dados["vias_risco_nomes"].columns[0]
        dados["vias_risco_nomes"] = remover_vias_sem_nome(
            dados["vias_risco_nomes"],
            primeira_coluna,
        )

    return dados


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().lower()
    texto = texto.replace("\ufeff", "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return texto


def formatar_numero(valor, casas=1, sufixo=""):
    if pd.isna(valor):
        return "Não informado"
    try:
        numero = f"{float(valor):,.{casas}f}".replace(
            ",", "X").replace(".", ",").replace("X", ".")
        return f"{numero}{sufixo}"
    except (TypeError, ValueError):
        return str(valor)


def formatar_numero_br(valor):
    if pd.isna(valor):
        return ""
    try:
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return valor


def formatar_colunas_numericas(df):
    resultado = df.copy()
    for coluna in resultado.columns:
        serie = resultado[coluna]

        if pd.api.types.is_numeric_dtype(serie):
            resultado[coluna] = serie.apply(formatar_numero_br)
            continue

        if pd.api.types.is_object_dtype(serie) or pd.api.types.is_string_dtype(serie):
            serie_texto = serie.astype(str).str.strip()
            numerica = pd.to_numeric(serie_texto, errors="coerce")
            valores_validos = serie.notna() & (serie_texto != "")

            if valores_validos.any() and numerica[valores_validos].notna().all():
                resultado[coluna] = numerica.apply(formatar_numero_br)

    return resultado


def escolher_centro(*camadas):
    for camada in camadas:
        if isinstance(camada, gpd.GeoDataFrame) and not camada.empty:
            web = preparar_web(camada)
            geometria = web.geometry.union_all() if hasattr(
                web.geometry, "union_all") else web.unary_union
            centroide = geometria.centroid
            return [centroide.y, centroide.x]
    return [-21.1303, -42.3662]


def preparar_web(gdf):
    if gdf.empty:
        return gdf
    if gdf.crs is None:
        return gdf.set_crs(epsg=4326)
    return gdf.to_crs(epsg=4326)


def identificar_coluna(df, candidatos):
    if df.empty:
        return None
    colunas = {normalizar_texto(coluna): coluna for coluna in df.columns}
    for candidato in candidatos:
        achada = colunas.get(normalizar_texto(candidato))
        if achada:
            return achada
    return None


def identificar_coluna_nome_via(df):
    return identificar_coluna(
        df,
        [
            "nome_via",
            "name",
            "nome",
            "rua",
            "logradouro",
            "nm_lograd",
            "nm_logradouro",
            "nm_via",
            "descricao",
        ],
    )


def identificar_coluna_setor(df):
    return identificar_coluna(
        df,
        [
            "denominacao_setor",
            "denominacao_setor_mapa",
            "denominacao do setor",
            "setor",
            "name",
            "nome",
        ],
    )


def filtrar_texto(df, coluna, termo):
    if df.empty or coluna is None:
        return df.iloc[0:0].copy()
    termo_norm = normalizar_texto(termo)
    serie = df[coluna].apply(normalizar_texto)
    return df[serie.str.contains(termo_norm, na=False, regex=False)].copy()


def filtrar_por_coluna(df, coluna, valores):
    if df.empty or coluna not in df.columns or not valores:
        return df
    return df[df[coluna].astype(str).isin(valores)].copy()


def tabela_sem_geometria(df):
    if isinstance(df, gpd.GeoDataFrame):
        return pd.DataFrame(df.drop(columns="geometry", errors="ignore"))
    return df.copy()


def csv_download(df):
    return tabela_sem_geometria(df).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def cabecalhos_tabela(nome_tabela):
    nome = normalizar_texto(nome_tabela)

    if "vias afetadas por manchas" in nome:
        return {
            "NOME": "Nome da via",
            "extensao_m": "Extensão total da via (m)",
            "tempo_recorrencia": "Tempo de Recorrência (anos)",
            "extensao_afetada_m": "Extensão afetada da via (m)",
            "cota_min_m": "Cota Mínima de Inundação (m)",
            "cota_media_m": "Cota Média de Inundação (m)",
            "cota_max_m": "Cota Máxima de Inundação (m)",
        }

    if "indicadores por tempo" in nome:
        return {
            "tempo_recorrencia": "Tempo de Recorrência (anos)",
            "extensao_total_rede_m": "Extensão total da rede viária (m)",
            "extensao_afetada_m": "Extensão viária afetada (m)",
            "percentual_rede_afetada": "Porcentagem de via afetada (%)",
        }

    if "resumo das vias afetadas" in nome:
        return {
            "tipo_risco": "Tipo do Risco",
            "extensao_afetada_m": "Extensão afetada (m)",
            "extensao_afetada_km": "Extensão afetada (km)",
        }

    if "dados dos setores" in nome:
        return {
            "denominacao_setor": "Denominação do Setor",
            "grau_risco": "Grau de Risco",
            "processo": "Risco",
            "numero_edificacoes": "Número de Edificações atingidas",
            "numero_pessoas": "Número de Pessoas afetadas",
        }

    if "areas de risco" in nome or "areas de risco" in nome or "vias afetadas por areas de risco" in nome:
        return {
            "NOME": "Nome da via",
            "extensao_total_m": "Extensão total da via (m)",
            "tipo_risco": "Tipo de Risco",
            "extensao_afetada_m": "Extensão afetada da via (m)",
        }

    return {}


def aplicar_cabecalhos(nome_tabela, df):
    return tabela_sem_geometria(df).rename(columns=cabecalhos_tabela(nome_tabela))


def converter_colunas_numericas(df, colunas):
    resultado = df.copy()
    for coluna in colunas:
        if coluna in resultado.columns:
            resultado[coluna] = pd.to_numeric(
                resultado[coluna], errors="coerce")
    return resultado


def agrupar_vias_por_nome(df, chaves_extras=None):
    if df.empty:
        return df

    coluna_nome = identificar_coluna_nome_via(df)
    if coluna_nome is None:
        return df

    chaves = [coluna_nome]
    for chave in chaves_extras or []:
        if chave in df.columns and chave not in chaves:
            chaves.append(chave)

    agregacoes = {}
    for coluna in df.columns:
        if coluna in chaves:
            continue
        if coluna == "extensao_afetada_m":
            agregacoes[coluna] = "sum"
        elif coluna in ["extensao_total_m", "extensao_m"]:
            agregacoes[coluna] = "sum"
        elif coluna == "cota_min_m":
            agregacoes[coluna] = "min"
        elif coluna == "cota_media_m":
            agregacoes[coluna] = "mean"
        elif coluna == "cota_max_m":
            agregacoes[coluna] = "max"
        else:
            agregacoes[coluna] = "first"

    return df.groupby(chaves, dropna=False).agg(agregacoes).reset_index()


def formatar_tempo_recorrencia(valor):
    if pd.isna(valor):
        return valor

    texto = str(valor).strip()
    texto_norm = normalizar_texto(texto)

    if "100" in texto_norm:
        return "TR 100 anos"
    if "50" in texto_norm:
        return "TR 50 anos"
    if "10" in texto_norm:
        return "TR 10 anos"
    if texto_norm.startswith("tr"):
        return texto

    try:
        numero = int(float(texto.replace(",", ".")))
        return f"TR {numero} anos"
    except ValueError:
        return texto


def corrigir_tipo_risco(valor):
    if normalizar_texto(valor) == "inundacao":
        return "Inundação"
    return valor


def descricao_grau_risco(grau):
    grau_norm = normalizar_texto(grau).upper()
    if grau_norm == "R1":
        return (
            "R1 – Risco de baixa probabilidade: os condicionantes geológico-geotécnicos "
            "predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção "
            "no setor são de baixa potencialidade para o desenvolvimento de processos de "
            "escorregamentos e solapamentos. Não se observa (m) evidência (s) de instabilidade. "
            "Não há indícios de desenvolvimento de processos de instabilização de encostas e de "
            "margens de drenagens. É a condição menos crítica. Mantidas as condições existentes, "
            "não se espera a ocorrência de eventos destrutivos no período de 1 ano."
        )
    if grau_norm == "R2":
        return (
            "R2 – Risco de média probabilidade: os condicionantes geológico-geotécnicos "
            "predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção no "
            "setor são de média potencialidade para o desenvolvimento de processos de "
            "escorregamentos e solapamentos. Observa-se a presença de alguma (s) evidência (s) "
            "de instabilidade (encostas e margens de drenagens), porém incipiente (s). Processo "
            "de instabilização em estágio inicial de desenvolvimento. Mantidas as condições "
            "existentes, é reduzida a possibilidade de ocorrência de eventos destrutivos durante "
            "episódios de chuvas intensas e prolongadas, no período de 1 ano."
        )
    if grau_norm == "R3":
        return (
            "R3 – Risco de alta probabilidade: os condicionantes geológico-geotécnicos "
            "predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção no "
            "setor são de alta potencialidade para o desenvolvimento de processos de "
            "escorregamentos e solapamentos. Observa-se a presença de significativa (s) "
            "evidência (s) de instabilidade (trincas no solo, degraus de abatimento em taludes, "
            "etc.). Processo de instabilização em pleno desenvolvimento, ainda sendo possível "
            "monitorar a evolução do processo. Mantidas as condições existentes, é perfeitamente "
            "possível a ocorrência de eventos destrutivos durante episódios de chuvas intensas e "
            "prolongadas, no período de 1 ano."
        )
    if grau_norm == "R4":
        return (
            "R4 – Risco de probabilidade muito alta: os condicionantes geológico-geotécnicos "
            "predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção no "
            "setor são de muito alta potencialidade para o desenvolvimento de processos de "
            "escorregamentos e solapamentos. As evidências de instabilidade (trincas no solo, "
            "degraus de abatimento em taludes, trincas em moradias ou em muros de contenção, "
            "árvores ou postes inclinados, cicatrizes de escorregamento, feições erosivas, "
            "proximidade da moradia em relação à margem de córregos, etc.) são expressivas e "
            "estão presentes em grande número ou magnitude. Processo de instabilização em "
            "avançado estágio de desenvolvimento. É a condição mais crítica, sendo impossível "
            "monitorar a evolução do processo, dado seu elevado estágio de desenvolvimento. "
            "Mantidas as condições existentes, é muito provável a ocorrência de eventos "
            "destrutivos durante episódios de chuvas intensas e prolongadas, no período de 1 ano."
        )
    return "Grau de risco não informado para esta área."


def preparar_tabela_vias_risco(vias_risco):
    if vias_risco.empty:
        return pd.DataFrame()

    df = tabela_sem_geometria(vias_risco)
    df = converter_colunas_numericas(
        df, ["extensao_afetada_m", "extensao_total_m"])
    if "id_via" in df.columns:
        agregacoes = {}
        for coluna in df.columns:
            if coluna == "id_via":
                continue
            if coluna == "extensao_afetada_m":
                agregacoes[coluna] = "sum"
            elif coluna == "extensao_total_m":
                agregacoes[coluna] = "first"
            else:
                agregacoes[coluna] = "first"
        df = df.groupby("id_via", dropna=False).agg(agregacoes).reset_index()

    df = df.drop(columns=["id_via"], errors="ignore")

    coluna_nome = identificar_coluna_nome_via(df)
    if coluna_nome is not None:
        df = remover_vias_sem_nome(df, coluna_nome)

    if "tipo_risco" in df.columns:
        df["tipo_risco"] = df["tipo_risco"].apply(corrigir_tipo_risco)

    return agrupar_vias_por_nome(df, chaves_extras=["tipo_risco"])


def preparar_tabela_vias_tr(vias_tr):
    if vias_tr.empty:
        return pd.DataFrame()

    df = tabela_sem_geometria(vias_tr)
    df = converter_colunas_numericas(
        df,
        [
            "extensao_m",
            "extensao_afetada_m",
            "cota_min_m",
            "cota_media_m",
            "cota_max_m",
        ],
    )
    if "id_trecho" in df.columns:
        chaves = ["id_trecho"]
        if "tempo_recorrencia" in df.columns:
            chaves.append("tempo_recorrencia")

        agregacoes = {}
        for coluna in df.columns:
            if coluna in chaves:
                continue
            if coluna == "extensao_afetada_m":
                agregacoes[coluna] = "sum"
            elif coluna == "cota_min_m":
                agregacoes[coluna] = "min"
            elif coluna == "cota_media_m":
                agregacoes[coluna] = "mean"
            elif coluna == "cota_max_m":
                agregacoes[coluna] = "max"
            else:
                agregacoes[coluna] = "first"

        df = df.groupby(chaves, dropna=False).agg(agregacoes).reset_index()

    df = df.drop(columns=["id_trecho", "qtd_pontos_mdt"], errors="ignore")
    df = remover_vias_sem_nome(df)
    return agrupar_vias_por_nome(df, chaves_extras=["tempo_recorrencia"])


def preparar_tabela_indicadores(indicadores):
    if indicadores.empty:
        return pd.DataFrame()

    df = tabela_sem_geometria(indicadores)
    coluna_tempo = identificar_coluna(
        df,
        [
            "tempo_recorrencia",
            "tempo de recorrencia",
            "tempo de recorrencia anos",
            "Tempo de Recorrência (anos)",
            "TR",
            "cenario",
            "cenário",
        ],
    )
    coluna_ext_total = identificar_coluna(
        df,
        [
            "extensao_total_rede_m",
            "extensao total rede m",
            "extensao total da rede m",
            "Extensão Total da Rede (m)",
            "Extensão total da rede viária (m)",
        ],
    )
    coluna_ext_afetada = identificar_coluna(
        df,
        [
            "extensao_afetada_m",
            "extensao afetada m",
            "extensao viaria afetada m",
            "Extensão afetada (m)",
            "Extensão viária afetada (m)",
        ],
    )
    coluna_percentual = identificar_coluna(
        df,
        [
            "percentual_rede_afetada",
            "percentual da rede afetada",
            "rede afetada",
            "Rede afetada (%)",
        ],
    )

    colunas_encontradas = {
        "tempo_recorrencia": coluna_tempo,
        "extensao_total_rede_m": coluna_ext_total,
        "extensao_afetada_m": coluna_ext_afetada,
        "percentual_rede_afetada": coluna_percentual,
    }

    presentes = {novo: antigo for novo,
                 antigo in colunas_encontradas.items() if antigo is not None}
    if not presentes:
        return pd.DataFrame()

    resultado = df[list(presentes.values())].copy()
    resultado = resultado.rename(
        columns={antigo: novo for novo, antigo in presentes.items()})

    if "tempo_recorrencia" not in resultado.columns and len(resultado) == 3:
        resultado.insert(0, "tempo_recorrencia", [
                         "TR 10 anos", "TR 50 anos", "TR 100 anos"])

    if "tempo_recorrencia" in resultado.columns:
        resultado["tempo_recorrencia"] = resultado["tempo_recorrencia"].apply(
            formatar_tempo_recorrencia)
        ordem = ["TR 10 anos", "TR 50 anos", "TR 100 anos"]
        resultado["_ordem_tr"] = pd.Categorical(
            resultado["tempo_recorrencia"], categories=ordem, ordered=True)
        resultado = resultado.sort_values(
            "_ordem_tr").drop(columns="_ordem_tr")

    if "percentual_rede_afetada" not in resultado.columns:
        colunas_para_calculo = {"extensao_total_rede_m", "extensao_afetada_m"}
        if colunas_para_calculo.issubset(resultado.columns):
            total = pd.to_numeric(
                resultado["extensao_total_rede_m"], errors="coerce")
            afetada = pd.to_numeric(
                resultado["extensao_afetada_m"], errors="coerce")
            resultado["percentual_rede_afetada"] = (afetada / total) * 100

    return resultado


def preparar_tabela_resumo(resumo):
    if resumo.empty:
        return pd.DataFrame()
    return tabela_sem_geometria(resumo).drop(columns=["trechos_afetados"], errors="ignore")


def preparar_tabela_setores(setores):
    if setores.empty:
        return pd.DataFrame()
    return tabela_sem_geometria(setores).drop(columns=["chave_setor", "cor_grau_risco"], errors="ignore")


def tooltip_campos(gdf, campos, aliases=None):
    validos = [campo for campo in campos if campo in gdf.columns]
    if not validos:
        return None
    aliases_validos = None
    if aliases:
        aliases_validos = [alias for campo, alias in zip(
            campos, aliases) if campo in gdf.columns]
    return folium.GeoJsonTooltip(fields=validos, aliases=aliases_validos, localize=True, sticky=True)


def adicionar_geojson(mapa, gdf, nome, cor, peso=2, fill=True, fill_opacity=0.35, campos=None, aliases=None):
    if gdf.empty:
        return
    web = preparar_web(gdf)
    folium.GeoJson(
        web,
        name=nome,
        style_function=lambda feature, cor=cor: {
            "color": cor,
            "weight": peso,
            "opacity": 0.92,
            "fillColor": cor,
            "fillOpacity": fill_opacity if fill else 0,
        },
        tooltip=tooltip_campos(web, campos or [], aliases),
    ).add_to(mapa)


def criar_mapa_publico(areas_risco, manchas_tr, vias_risco, vias_tr, filtros):
    centro = escolher_centro(areas_risco, manchas_tr, vias_tr, vias_risco)
    mapa = folium.Map(location=centro, zoom_start=13,
                      tiles="CartoDB positron", control_scale=True)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(mapa)
    folium.TileLayer("Esri.WorldImagery",
                     name="Imagem de satélite").add_to(mapa)

    riscos_selecionados = filtros.get("riscos", [])
    tempos_selecionados = filtros.get("tempos", [])
    mostrar_vias_risco = filtros.get("mostrar_vias_risco", True)
    mostrar_vias_tr = filtros.get("mostrar_vias_tr", True)

    if not areas_risco.empty and "tipo_risco" in areas_risco.columns:
        for tipo in riscos_selecionados:
            camada = areas_risco[areas_risco["tipo_risco"].astype(str) == tipo]
            cor = COR_AZUL_CLARO if normalizar_texto(
                tipo).startswith("inund") else COR_VERMELHO
            adicionar_geojson(
                mapa,
                camada,
                f"Área de risco - {tipo}",
                cor,
                campos=[
                    "tipo_risco",
                    "grau_risco",
                    "denominacao_setor",
                    "denominacao_setor_mapa",
                    "numero_pessoas",
                    "numero_edificacoes",
                ],
                aliases=[
                    "Tipo de risco:",
                    "Grau de risco:",
                    "Setor:",
                    "Setor no mapa:",
                    "Pessoas:",
                    "Edificações:",
                ],
            )
    elif not areas_risco.empty:
        adicionar_geojson(mapa, areas_risco, "Áreas de risco", COR_VERMELHO)

    if not manchas_tr.empty and "tempo_recorrencia" in manchas_tr.columns:
        for tempo in tempos_selecionados:
            camada = manchas_tr[manchas_tr["tempo_recorrencia"].astype(
                str) == tempo]
            adicionar_geojson(
                mapa,
                camada,
                f"Mancha de inundação - {tempo}",
                CORES_MANCHAS.get(tempo, COR_AZUL),
                peso=1,
                fill_opacity=0.32,
                campos=["tempo_recorrencia"],
                aliases=["Cenário:"],
            )

    if mostrar_vias_risco:
        adicionar_geojson(
            mapa,
            vias_risco,
            "Vias afetadas por áreas de risco",
            COR_LARANJA,
            peso=4,
            fill=False,
            campos=["nome_via", "tipo_risco", "extensao_afetada_m"],
            aliases=["Via:", "Tipo de risco:", "Extensão afetada (m):"],
        )

    if mostrar_vias_tr and not vias_tr.empty and "tempo_recorrencia" in vias_tr.columns:
        for tempo in tempos_selecionados:
            camada = vias_tr[vias_tr["tempo_recorrencia"].astype(str) == tempo]
            adicionar_geojson(
                mapa,
                camada,
                f"Vias afetadas - {tempo}",
                CORES_VIAS_TR.get(tempo, COR_VERMELHO),
                peso=5,
                fill=False,
                campos=[
                    identificar_coluna_nome_via(camada) or "",
                    "tempo_recorrencia",
                    "extensao_afetada_m",
                    "cota_min_m",
                    "cota_media_m",
                    "cota_max_m",
                ],
                aliases=[
                    "Via:",
                    "Tempo de recorrência:",
                    "Extensão afetada (m):",
                    "Cota mínima (m):",
                    "Cota média (m):",
                    "Cota máxima (m):",
                ],
            )

    return mapa


def encontrar_area_clicada(areas_risco, evento_mapa):
    if areas_risco.empty or not evento_mapa:
        return None

    clique = evento_mapa.get("last_object_clicked") or evento_mapa.get("last_clicked")
    if not clique or "lat" not in clique or "lng" not in clique:
        return None

    areas = preparar_web(areas_risco)
    ponto = Point(clique["lng"], clique["lat"])
    candidatas = areas[areas.geometry.notna() & areas.geometry.intersects(ponto)]

    if candidatas.empty:
        return None

    return candidatas.iloc[0]


def render_resumo_area_clicada(area):
    if area is None:
        return

    coluna_setor = identificar_coluna_setor(pd.DataFrame([area.drop(labels="geometry", errors="ignore")]))
    tipo_risco = corrigir_tipo_risco(area.get("tipo_risco", "Não informado"))
    grau = area.get("grau_risco", "Não informado")
    setor = area.get(coluna_setor, "Não informado") if coluna_setor else "Não informado"
    pessoas = area.get("numero_pessoas", "Não informado")
    edificacoes = area.get("numero_edificacoes", "Não informado")

    st.markdown(
        f"""
<div class="info-card" style="text-align: justify;">
<h3>Resumo da área selecionada</h3>
<p><strong>Tipo de Risco:</strong> {tipo_risco}</p>
<p><strong>Grau:</strong> {descricao_grau_risco(grau)}</p>
<p><strong>Setor:</strong> {setor}. Trata-se apenas de um fator de identificação da região afetada.</p>
<p><strong>Pessoas:</strong> {pessoas}. Indica o número de pessoas atingidas pelo determinado evento conforme o levantamento feito pelas equipes de campo.</p>
<p><strong>Edificações:</strong> {edificacoes}. Indica o número de edificações localizadas nas áreas de risco conforme o levantamento feito pelas equipes de campo.</p>
</div>
""",
        unsafe_allow_html=True,
    )


def criar_mapa_consulta(vias_encontradas, areas_risco):
    if vias_encontradas.empty:
        return None

    vias = vias_encontradas.copy()
    if vias.crs is None:
        vias = vias.set_crs(epsg=4326)

    centro = escolher_centro(vias)
    mapa = folium.Map(location=centro, zoom_start=15,
                      tiles="CartoDB positron", control_scale=True)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(mapa)

    if not areas_risco.empty and "tipo_risco" in areas_risco.columns:
        areas_web = preparar_web(areas_risco)
        areas_web = areas_web.copy()
        areas_web["tipo_risco"] = areas_web["tipo_risco"].apply(corrigir_tipo_risco)
        tipos_normalizados = areas_web["tipo_risco"].apply(normalizar_texto)
        areas_inundacao = areas_web[tipos_normalizados.str.contains("inund", na=False)]
        areas_deslizamento = areas_web[tipos_normalizados.str.contains("desliz", na=False)]
        areas_outros = areas_web[
            ~tipos_normalizados.str.contains("inund", na=False)
            & ~tipos_normalizados.str.contains("desliz", na=False)
        ]

        adicionar_geojson(
            mapa,
            areas_inundacao,
            "Áreas de risco - Inundação",
            COR_AZUL,
            peso=2,
            fill=True,
            fill_opacity=0.22,
            campos=["tipo_risco", "grau_risco", "denominacao_setor",
                    "numero_pessoas", "numero_edificacoes"],
            aliases=["Tipo de risco:", "Grau:",
                     "Setor:", "Pessoas:", "Edificações:"],
        )
        adicionar_geojson(
            mapa,
            areas_deslizamento,
            "Áreas de risco - Deslizamento",
            COR_LARANJA,
            peso=2,
            fill=True,
            fill_opacity=0.24,
            campos=["tipo_risco", "grau_risco", "denominacao_setor",
                    "numero_pessoas", "numero_edificacoes"],
            aliases=["Tipo de risco:", "Grau:",
                     "Setor:", "Pessoas:", "Edificações:"],
        )
        adicionar_geojson(
            mapa,
            areas_outros,
            "Áreas de risco - Outros",
            COR_VERMELHO,
            peso=2,
            fill=True,
            fill_opacity=0.22,
            campos=["tipo_risco", "grau_risco", "denominacao_setor",
                    "numero_pessoas", "numero_edificacoes"],
            aliases=["Tipo de risco:", "Grau:",
                     "Setor:", "Pessoas:", "Edificações:"],
        )

    adicionar_geojson(
        mapa,
        vias.to_crs(epsg=4326),
        "Via pesquisada",
        "#ff00ff",
        peso=8,
        fill=False,
        campos=[identificar_coluna_nome_via(
            vias) or "", "tempo_recorrencia", "extensao_afetada_m", "cota_min_m", "cota_media_m", "cota_max_m"],
        aliases=["Via:", "Tempo de recorrência:",
                 "Extensão afetada (m):", "Cota mínima:", "Cota média:", "Cota máxima:"],
    )

    return mapa


def render_hero():
    st.markdown(
        """
<div class="hero">
  <h1>Painel de Apoio a Identificação de Riscos de Deslizamentos e Inundações</h1>
  <p>Consulta pública sobre áreas de risco, vias afetadas e cenários de inundação.</p>
</div>
""",
        unsafe_allow_html=True,
    )



def imagem_base64(caminho):
    if not caminho.exists():
        return None
    sufixo = caminho.suffix.lower().replace(".", "")
    mime = "svg+xml" if sufixo == "svg" else sufixo
    dados = base64.b64encode(caminho.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{dados}"


def logo_html(caminho, rotulo):
    src = imagem_base64(caminho)
    if src:
        return f'<div class="sidebar-logo-box"><img src="{src}" alt="{rotulo}"></div>'
    return f'<div class="sidebar-logo-box"><div class="logo-placeholder">{rotulo}</div></div>'


def render_sidebar_institucional():
    logo_pairdi = imagem_base64(ASSETS_DIR / "logo_pairdi.png")
    if logo_pairdi:
        conteudo = f'<img src="{logo_pairdi}" alt="PAIRDI">'
    else:
        conteudo = '<div class="sidebar-brand-title">PAIRDI</div>'

    st.markdown(
        f"""
<div class="sidebar-brand">
  {conteudo}
  <div class="sidebar-brand-subtitle">Painel de Apoio a Identificação de Riscos de Deslizamentos e Inundações</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_rodape():
    logos = "\n".join(
        [
            logo_html(ASSETS_DIR / "logo_prefeitura.png", "Prefeitura"),
            logo_html(ASSETS_DIR / "logo_ime.png", "IME"),
            logo_html(ASSETS_DIR / "logo_ufv.png", "UFV"),
        ]
    )
    st.markdown(
        f"""
<div class="sidebar-partners">
  <div class="sidebar-partners-title">Desenvolvido em parceria com:</div>
  <div class="sidebar-logo-row">
    {logos}
  </div>
  <div class="sidebar-footer-text">
    Este painel apresenta os resultados do PMRR desenvolvido para a cidade de Muriaé/MG.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_card(titulo, linhas, classe="result-card"):
    conteudo = "".join(
        f"<p><strong>{chave}:</strong> {valor}</p>" for chave, valor in linhas)
    st.markdown(
        f'<div class="{classe}"><h4>{titulo}</h4>{conteudo}</div>', unsafe_allow_html=True)


def pagina_visao_geral(dados):
    st.header("Panorama Geral dos Riscos de Deslizamentos e Inundações")
    st.markdown(
        """
<div class="info-card">
<h3>Entenda os Riscos em Muriaé</h3>
<p>O município de Muriaé apresenta áreas sujeitas a diferentes tipos de desastres naturais, especialmente inundações e deslizamentos de terra, que podem colocar em risco a segurança da população, causar danos a residências, interromper o trânsito e comprometer serviços essenciais.</p>
<p>As inundações ocorrem principalmente nas regiões próximas aos cursos d'água e áreas mais baixas da cidade, podendo afetar ruas, avenidas e bairros durante períodos de chuvas intensas. Já os deslizamentos tendem a ocorrer em encostas e terrenos com declividades acentuadas, especialmente quando associados à ocupação inadequada do solo ou à ausência de medidas de contenção.</p>
<p>Este painel reúne informações sobre as áreas suscetíveis a inundações e deslizamentos, além de identificar as vias potencialmente afetadas por diferentes cenários de chuva. O objetivo é facilitar a compreensão dos riscos existentes, apoiar ações de prevenção e auxiliar a população na adoção de medidas de segurança durante eventos climáticos extremos.</p>
<p>Navegue pelos mapas e consulte as informações para conhecer melhor os principais pontos de atenção do município.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    areas = dados["areas_risco"]
    resumo = dados["resumo_risco"]
    vias_risco = converter_colunas_numericas(
        dados["vias_risco"],
        ["extensao_afetada_m", "extensao_total_m"],
    )

    total_areas = len(areas) if not areas.empty else pd.NA
    inundacao = pd.NA
    deslizamento = pd.NA
    if not areas.empty and "tipo_risco" in areas.columns:
        tipos_norm = areas["tipo_risco"].apply(normalizar_texto)
        inundacao = tipos_norm.str.contains("inund", na=False).sum()
        deslizamento = tipos_norm.str.contains("desliz", na=False).sum()

    vias_afetadas = pd.NA
    extensao_total = pd.NA
    if not resumo.empty:
        if "trechos_afetados" in resumo.columns:
            vias_afetadas = resumo["trechos_afetados"].sum()
        if "extensao_afetada_m" in resumo.columns:
            extensao_total = resumo["extensao_afetada_m"].sum()

    if pd.isna(vias_afetadas) and not vias_risco.empty:
        if "id_via" in vias_risco.columns:
            vias_afetadas = vias_risco["id_via"].nunique()
        else:
            vias_afetadas = len(vias_risco)

    if pd.isna(extensao_total) and not vias_risco.empty and "extensao_afetada_m" in vias_risco.columns:
        extensao_total = vias_risco["extensao_afetada_m"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de áreas de risco", formatar_numero(total_areas, 0))
    col2.metric("Áreas de inundação", formatar_numero(inundacao, 0))
    col3.metric("Áreas de deslizamento", formatar_numero(deslizamento, 0))
    col4.metric("Extensão de vias afetadas",
                formatar_numero(extensao_total, 0, " m"))

    st.metric("Número de vias afetadas por áreas de risco",
              formatar_numero(vias_afetadas, 0))


def pagina_mapa(dados, filtros):
    st.header("Mapa Interativo de Riscos de Deslizamento e Inundações")
    st.markdown(
        """
<div class="info-card">
Use o mapa para visualizar as áreas suscetíveis a inundação e deslizamento, além das manchas de inundação simuladas para diferentes cenários de chuva.
</div>
""",
        unsafe_allow_html=True,
    )

    mapa = criar_mapa_publico(
        dados["areas_risco"],
        dados["manchas_tr"],
        dados["vias_risco"],
        dados["vias_tr"],
        filtros,
    )
    st_folium(mapa, width=None, height=720)


def pagina_consulta(dados):
    st.header("Consulte sua Rua ou Bairro")
    st.markdown(
        """
<div class="info-card">
Digite o nome de uma rua, avenida ou setor para verificar se há registros de risco ou vias afetadas nas análises disponíveis. Para entender melhor sobre os riscos que envolvem sua região, anote o nome do Setor e consulte na aba Dados, disponível no Menu lateral, a tabela Dados dos Setores.
</div>
""",
        unsafe_allow_html=True,
    )

    tipo_resultado = st.selectbox(
        "Tipo de resultado",
        [
            "Todos",
            "Áreas de risco",
            "Vias afetadas por áreas de risco",
        ],
    )

    termo = st.text_input(
        "Buscar", placeholder="Exemplo: Rua Coronel Domiciano ou nome do setor")
    if not termo:
        st.info(
            "Digite parte do nome da rua, avenida ou setor para iniciar a consulta.")
        return

    encontrou = False
    geometrias_para_mapa = []

    areas = dados["areas_risco"]
    if tipo_resultado in ["Todos", "Áreas de risco"]:
        coluna_setor = identificar_coluna_setor(areas)
        resultado_areas = filtrar_texto(areas, coluna_setor, termo)
        if not resultado_areas.empty:
            encontrou = True
            st.subheader("Setores de risco encontrados")
            for _, linha in resultado_areas.head(8).iterrows():
                render_card(
                    "Setor de risco",
                    [
                        ("Nome do setor", linha.get(coluna_setor, "Não informado")),
                        ("Tipo de risco", linha.get("tipo_risco", "Não informado")),
                        ("Grau de risco", linha.get("grau_risco", "Não informado")),
                        ("Número de pessoas", linha.get(
                            "numero_pessoas", "Não informado")),
                        ("Número de edificações", linha.get(
                            "numero_edificacoes", "Não informado")),
                    ],
                    "result-card danger-card",
                )

    vias_risco = dados["vias_risco"]
    if tipo_resultado in ["Todos", "Vias afetadas por áreas de risco"]:
        coluna_via_risco = identificar_coluna_nome_via(vias_risco)
        resultado_vias_risco = filtrar_texto(
            vias_risco, coluna_via_risco, termo)
        if not resultado_vias_risco.empty:
            encontrou = True
            geometrias_para_mapa.append(resultado_vias_risco)
            st.subheader("Vias afetadas por áreas de risco")

            resultado_cards = resultado_vias_risco.copy()
            resultado_cards = converter_colunas_numericas(resultado_cards, ["extensao_afetada_m"])
            if "tipo_risco" in resultado_cards.columns:
                resultado_cards["tipo_risco"] = resultado_cards["tipo_risco"].apply(corrigir_tipo_risco)

            if coluna_via_risco and "tipo_risco" in resultado_cards.columns:
                resultado_cards = (
                    resultado_cards
                    .groupby([coluna_via_risco, "tipo_risco"], dropna=False)
                    .agg(extensao_afetada_m=("extensao_afetada_m", "sum"))
                    .reset_index()
                )

            for _, linha in resultado_cards.head(12).iterrows():
                render_card(
                    "Via em área de risco",
                    [
                        ("Nome da via", linha.get(coluna_via_risco, "Não informado")),
                        ("Tipo de risco", linha.get("tipo_risco", "Não informado")),
                        ("Extensão afetada", formatar_numero(
                            linha.get("extensao_afetada_m", pd.NA), 1, " m")),
                    ],
                    "result-card warning-card",
                )

    if geometrias_para_mapa:
        vias_mapa = gpd.GeoDataFrame(pd.concat(
            geometrias_para_mapa, ignore_index=True), geometry="geometry", crs=geometrias_para_mapa[0].crs)
        st.subheader("Mapa da consulta")
        mapa = criar_mapa_consulta(vias_mapa, areas)
        if mapa is not None:
            evento_mapa = st_folium(mapa, width=None, height=560, key="mapa_consulta")
            area_clicada = encontrar_area_clicada(areas, evento_mapa)
            render_resumo_area_clicada(area_clicada)

    if not encontrou:
        st.warning(
            "Não encontramos esse nome nos arquivos carregados. Verifique se digitou corretamente "
            "ou tente buscar por parte do nome da rua ou setor."
        )


def render_tabela(nome, df, filtros=None):
    st.subheader(nome)
    exibicao = df.copy()

    if filtros:
        termo = normalizar_texto(filtros.get("termo", ""))
        if termo:
            sem_geom = tabela_sem_geometria(exibicao)
            mascara = pd.Series(False, index=sem_geom.index)
            for coluna in sem_geom.columns:
                if sem_geom[coluna].dtype == "object":
                    mascara = mascara | sem_geom[coluna].apply(
                        normalizar_texto).str.contains(termo, na=False, regex=False)
            exibicao = exibicao[mascara]

        tipo_risco = filtros.get("tipo_risco")
        if tipo_risco and tipo_risco != "Todos" and "tipo_risco" in exibicao.columns:
            exibicao = exibicao[exibicao["tipo_risco"].astype(
                str) == tipo_risco]

        tempo = filtros.get("tempo")
        if tempo and tempo != "Todos" and "tempo_recorrencia" in exibicao.columns:
            exibicao = exibicao[exibicao["tempo_recorrencia"].astype(
                str) == tempo]

    if exibicao.empty:
        st.info("Nenhum registro encontrado para esta tabela.")
        return

    exibicao_formatada = formatar_colunas_numericas(
        aplicar_cabecalhos(nome, exibicao))
    st.dataframe(exibicao_formatada, use_container_width=True, hide_index=True)
    st.download_button(
        f"Baixar {nome} em CSV",
        data=csv_download(exibicao_formatada),
        file_name=f"{normalizar_texto(nome).replace(' ', '_')}.csv",
        mime="text/csv",
    )


def render_descricao_riscos_setores():
    st.markdown(
        """
<div class="info-card" style="text-align: justify;">
<h3>Descrição dos riscos</h3>
<p><strong>R1 – Risco de baixa probabilidade:</strong> os condicionantes geológico-geotécnicos predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção no setor são de baixa potencialidade para o desenvolvimento de processos de escorregamentos e solapamentos. Não se observa (m) evidência (s) de instabilidade. Não há indícios de desenvolvimento de processos de instabilização de encostas e de margens de drenagens. É a condição menos crítica. Mantidas as condições existentes, não se espera a ocorrência de eventos destrutivos no período de 1 ano.</p>
<p><strong>R2 – Risco de média probabilidade:</strong> os condicionantes geológico-geotécnicos predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção no setor são de média potencialidade para o desenvolvimento de processos de escorregamentos e solapamentos. Observa-se a presença de alguma (s) evidência (s) de instabilidade (encostas e margens de drenagens), porém incipiente (s). Processo de instabilização em estágio inicial de desenvolvimento. Mantidas as condições existentes, é reduzida a possibilidade de ocorrência de eventos destrutivos durante episódios de chuvas intensas e prolongadas, no período de 1 ano.</p>
<p><strong>R3 – Risco de alta probabilidade:</strong> os condicionantes geológico-geotécnicos predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção no setor são de alta potencialidade para o desenvolvimento de processos de escorregamentos e solapamentos. Observa-se a presença de significativa (s) evidência (s) de instabilidade (trincas no solo, degraus de abatimento em taludes, etc.). Processo de instabilização em pleno desenvolvimento, ainda sendo possível monitorar a evolução do processo. Mantidas as condições existentes, é perfeitamente possível a ocorrência de eventos destrutivos durante episódios de chuvas intensas e prolongadas, no período de 1 ano.</p>
<p><strong>R4 – Risco de probabilidade muito alta:</strong> os condicionantes geológico-geotécnicos predisponentes (declividade, tipo de terreno, etc.) e o nível de intervenção no setor são de muito alta potencialidade para o desenvolvimento de processos de escorregamentos e solapamentos. As evidências de instabilidade (trincas no solo, degraus de abatimento em taludes, trincas em moradias ou em muros de contenção, árvores ou postes inclinados, cicatrizes de escorregamento, feições erosivas, proximidade da moradia em relação à margem de córregos, etc.) são expressivas e estão presentes em grande número ou magnitude. Processo de instabilização em avançado estágio de desenvolvimento. É a condição mais crítica, sendo impossível monitorar a evolução do processo, dado seu elevado estágio de desenvolvimento. Mantidas as condições existentes, é muito provável a ocorrência de eventos destrutivos durante episódios de chuvas intensas e prolongadas, no período de 1 ano.</p>
</div>
""",
        unsafe_allow_html=True,
    )


def pagina_tabelas(dados):
    st.header("Tabelas de Dados")
    st.markdown(
        """
<div class="info-card">
Consulte abaixo os dados utilizados no painel, incluindo áreas de risco, vias afetadas e indicadores por cenário de inundação.
</div>
""",
        unsafe_allow_html=True,
    )

    tabela_escolhida = st.selectbox(
        "Tabela",
        [
            "Vias afetadas por áreas de risco",
            "Vias afetadas por manchas de inundação",
            "Indicadores por tempo de recorrência",
            "Resumo das vias afetadas por tipo de risco",
            "Dados dos setores",
        ],
    )

    tabelas = {
        "Vias afetadas por áreas de risco": preparar_tabela_vias_risco(dados["vias_risco"]),
        "Vias afetadas por manchas de inundação": preparar_tabela_vias_tr(dados["vias_tr"]),
        "Indicadores por tempo de recorrência": preparar_tabela_indicadores(dados["indicadores_tr"]),
        "Resumo das vias afetadas por tipo de risco": preparar_tabela_resumo(dados["resumo_risco"]),
        "Dados dos setores": preparar_tabela_setores(dados["dados_setores"]),
    }
    render_tabela(tabela_escolhida, tabelas[tabela_escolhida])

    if tabela_escolhida == "Dados dos setores":
        render_descricao_riscos_setores()


def pagina_orientacoes():
    st.header("Orientações à População")
    st.markdown(
        """
<div class="info-card">
As informações deste painel ajudam a identificar áreas de atenção, mas não substituem os avisos oficiais da Defesa Civil. Em caso de emergência, siga sempre as orientações dos órgãos responsáveis.
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<div class="info-card">
<h3>Contatos úteis</h3>
<p><strong>Defesa Civil:</strong> 115</p>
<p><strong>Corpo de Bombeiros:</strong> 193</p>
<p><strong>Prefeitura:</strong> 3696-3362 ou 3696-3368</p>
<p><strong>SAMU:</strong> 192</p>
<p><strong>Polícia Militar:</strong> 190</p>
</div>
""",
        unsafe_allow_html=True,
    )

    secoes = [
        (
            "Antes da chuva",
            [
                "Acompanhe alertas meteorológicos.",
                "Mantenha documentos importantes protegidos.",
                "Evite descartar lixo em ruas, bueiros e cursos d'água.",
                "Conheça rotas alternativas e pontos seguros próximos.",
            ],
        ),
        (
            "Durante chuva forte",
            [
                "Evite atravessar ruas alagadas.",
                "Não tente passar por enxurradas.",
                "Evite áreas de encosta, barrancos e margens de rios.",
                "Desligue aparelhos elétricos se houver risco de água entrar na residência.",
            ],
        ),
        (
            "Em caso de inundação",
            [
                "Procure local mais alto e seguro.",
                "Não entre em contato com água de enchente.",
                "Evite dirigir em áreas alagadas.",
                "Siga as orientações da Defesa Civil.",
            ],
        ),
        (
            "Em caso de risco de deslizamento",
            [
                "Observe rachaduras em paredes, solo ou encostas.",
                "Fique atento a postes, árvores ou muros inclinados.",
                "Saia imediatamente do local se houver sinais de movimentação do terreno.",
                "Acione a Defesa Civil.",
            ],
        ),
        (
            "Depois do evento",
            [
                "Não retorne para áreas atingidas sem autorização.",
                "Verifique riscos elétricos e estruturais.",
                "Evite contato com água contaminada.",
                "Registre danos e comunique os órgãos responsáveis.",
            ],
        ),
    ]

    for titulo, itens in secoes:
        lista = "".join(f"<li>{item}</li>" for item in itens)
        st.markdown(
            f'<div class="info-card"><h3>{titulo}</h3><ul>{lista}</ul></div>', unsafe_allow_html=True)


def filtros_sidebar(pagina, dados):
    filtros = {
        "riscos": [],
        "tempos": [],
        "mostrar_vias_risco": True,
        "mostrar_vias_tr": True,
    }

    if pagina == "Mapa":
        st.sidebar.markdown("### Filtros do mapa")

        areas = dados["areas_risco"]
        riscos = sorted(areas["tipo_risco"].dropna().astype(str).unique(
        )) if not areas.empty and "tipo_risco" in areas.columns else []
        if riscos:
            filtros["riscos"] = st.sidebar.multiselect(
                "Tipo de risco", riscos, default=riscos)
        else:
            st.sidebar.info("Áreas de risco ainda não carregadas.")

        manchas = dados["manchas_tr"]
        tempos = sorted(manchas["tempo_recorrencia"].dropna().astype(str).unique(
        )) if not manchas.empty and "tempo_recorrencia" in manchas.columns else []
        if tempos:
            filtros["tempos"] = st.sidebar.multiselect(
                "Tempo de recorrência", tempos, default=tempos)
        else:
            st.sidebar.info("Manchas de inundação ainda não carregadas.")

        filtros["mostrar_vias_risco"] = st.sidebar.toggle(
            "Mostrar vias afetadas por áreas de risco", value=True)
        filtros["mostrar_vias_tr"] = st.sidebar.toggle(
            "Mostrar vias afetadas pelas manchas", value=True)

    return filtros


def main():
    aplicar_css()
    dados = carregar_dados()

    with st.sidebar:
        render_sidebar_institucional()
        st.markdown("## Menu")
        pagina = st.radio("Abas do painel", PAGINAS, label_visibility="collapsed")
        filtros = filtros_sidebar(pagina, dados)
        render_sidebar_rodape()

    render_hero()

    if pagina == "Visão Geral":
        pagina_visao_geral(dados)
    elif pagina == "Mapa":
        pagina_mapa(dados, filtros)
    elif pagina == "Consulta":
        pagina_consulta(dados)
    elif pagina == "Dados":
        pagina_tabelas(dados)
    elif pagina == "Orientações":
        pagina_orientacoes()


if __name__ == "__main__":
    main()
