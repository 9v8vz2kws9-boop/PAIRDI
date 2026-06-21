import os
import shutil
import math
from pathlib import Path
import folium
from folium.plugins import MiniMap, Fullscreen, MeasureControl
import pandas as pd
import geopandas as gpd
import rasterio
import rasterio.features
from shapely.geometry import shape

print("Bibliotecas importadas com sucesso.")

BASE_DIR = Path(__file__).resolve().parent
RESULTADOS_DIR = BASE_DIR / "resultados"

pastas = [
    BASE_DIR / "dados_brutos",
    BASE_DIR / "dados_processados",
    RESULTADOS_DIR,
    BASE_DIR / "mapas",
]

for pasta in pastas:
    pasta.mkdir(exist_ok=True)

print("Pastas criadas/verificadas:")
for pasta in pastas:
    print(f"- {pasta}")

caminhos_manchas_tif = {
    "TR 10 anos": BASE_DIR / "TR10_classificado.tif",
    "TR 50 anos": BASE_DIR / "TR50_classificado.tif",
    "TR 100 anos": BASE_DIR / "TR100_classificado.tif",
}

caminho_rede = BASE_DIR / "Logradouros_Muriae.shp"

# Arquivo raster do MDT/MDE contendo as cotas altimétricas.
# Ajuste o nome do arquivo conforme o seu dado.
caminho_mdt_raster = BASE_DIR / "MDT_MURIAE.tif"

campo_tempo_recorrencia = "tempo_recorrencia"

# Distância, em metros, entre os pontos amostrados ao longo de cada trecho afetado.
# Valores menores aumentam a precisão, mas deixam o processamento mais lento.
intervalo_amostragem_mdt_m = 10

print("Manchas de inundação:")
for tempo, caminho in caminhos_manchas_tif.items():
    print(f"- {tempo}: {caminho}")

print(f"\nRede viária: {caminho_rede}")
print(f"MDT raster: {caminho_mdt_raster}")

for tempo, caminho_tif in caminhos_manchas_tif.items():
    if not caminho_tif.exists():
        raise FileNotFoundError(
            f"Arquivo TIF não encontrado para {tempo}: {caminho_tif}")

if not caminho_rede.exists():
    raise FileNotFoundError(
        f"Arquivo da rede viária não encontrado: {caminho_rede}")

if not caminho_mdt_raster.exists():
    raise FileNotFoundError(
        f"Arquivo MDT raster não encontrado: {caminho_mdt_raster}")

print("Todos os arquivos principais foram encontrados.")

print("""
Atenção:
Para o shapefile da rede viária, os arquivos .shp, .dbf, .shx e .prj devem estar na mesma pasta.
""")

rede_viaria = gpd.read_file(caminho_rede)

print("Dados lidos com sucesso.")
print(f"Camada da rede viária: {len(rede_viaria)} feições")
print(f"\nCRS da rede viária: {rede_viaria.crs}")

if rede_viaria.crs is None:
    raise ValueError("A rede viária está sem CRS.")

with rasterio.open(caminho_mdt_raster) as mdt_src:
    crs_mdt = mdt_src.crs
    nodata_mdt = mdt_src.nodata

if crs_mdt is None:
    raise ValueError("O MDT raster está sem CRS.")

print(f"CRS do MDT raster: {crs_mdt}")
print(f"Valor nodata do MDT raster: {nodata_mdt}")


def identificar_campo(gdf, candidatos):
    colunas_minusculas = {col.lower(): col for col in gdf.columns}

    for candidato in candidatos:
        if candidato.lower() in colunas_minusculas:
            return colunas_minusculas[candidato.lower()]

    return None


def converter_raster_inundacao_para_vetor(caminho_tif, tempo_recorrencia, limite_inundacao=0):
    """
    Converte um raster de inundação em uma camada vetorial.
    Considera como inundado todo pixel maior que limite_inundacao.
    """

    with rasterio.open(caminho_tif) as src:
        crs_raster = src.crs
        transformacao = src.transform
        nodata = src.nodata
        dados = src.read(1)

    if crs_raster is None:
        raise ValueError(f"O raster {caminho_tif} está sem CRS.")

    if nodata is not None:
        mascara_inundacao = (dados > limite_inundacao) & (dados != nodata)
    else:
        mascara_inundacao = dados > limite_inundacao

    pixels_inundados = mascara_inundacao.sum()

    print(f"{tempo_recorrencia}: {pixels_inundados} pixels inundados.")

    if pixels_inundados == 0:
        print(f"AVISO: Nenhum pixel inundado encontrado para {tempo_recorrencia}.")
        return gpd.GeoDataFrame(
            {campo_tempo_recorrencia: []},
            geometry=[],
            crs=crs_raster
        )

    geometrias = []

    for geometria, valor in rasterio.features.shapes(
        dados,
        mask=mascara_inundacao,
        transform=transformacao
    ):
        geometrias.append(shape(geometria))

    mancha = gpd.GeoDataFrame(
        {campo_tempo_recorrencia: [tempo_recorrencia] * len(geometrias)},
        geometry=geometrias,
        crs=crs_raster
    )

    mancha = mancha.dissolve(by=campo_tempo_recorrencia).reset_index()

    return mancha


def gerar_pontos_ao_longo_da_geometria(geometria, intervalo_m):
    """
    Gera pontos espaçados ao longo de linhas ou multilinhas.
    A geometria precisa estar em CRS métrico.
    """

    if geometria is None or geometria.is_empty:
        return []

    pontos = []

    if geometria.geom_type == "LineString":
        comprimento = geometria.length

        if comprimento == 0:
            return [geometria.representative_point()]

        quantidade_segmentos = max(1, math.ceil(comprimento / intervalo_m))
        distancias = [
            min(i * intervalo_m, comprimento)
            for i in range(quantidade_segmentos + 1)
        ]

        return [geometria.interpolate(distancia) for distancia in distancias]

    if geometria.geom_type == "MultiLineString":
        for linha in geometria.geoms:
            pontos.extend(gerar_pontos_ao_longo_da_geometria(linha, intervalo_m))
        return pontos

    if geometria.geom_type == "GeometryCollection":
        for parte in geometria.geoms:
            if parte.geom_type in ["LineString", "MultiLineString"]:
                pontos.extend(gerar_pontos_ao_longo_da_geometria(parte, intervalo_m))
        return pontos

    return []


def calcular_cotas_vias_por_mdt(vias_gdf, caminho_mdt, intervalo_m):
    """
    Amostra o MDT raster em pontos ao longo das vias afetadas.
    Retorna cota mínima, média, máxima e número de pontos amostrados por trecho.
    """

    registros_pontos = []

    for _, via in vias_gdf.iterrows():
        pontos = gerar_pontos_ao_longo_da_geometria(via.geometry, intervalo_m)

        for ponto in pontos:
            registros_pontos.append({
                "id_trecho": via["id_trecho"],
                "geometry": ponto
            })

    if len(registros_pontos) == 0:
        return pd.DataFrame(columns=[
            "id_trecho",
            "cota_min_m",
            "cota_media_m",
            "cota_max_m",
            "qtd_pontos_mdt"
        ])

    pontos_gdf = gpd.GeoDataFrame(
        registros_pontos,
        geometry="geometry",
        crs=vias_gdf.crs
    )

    with rasterio.open(caminho_mdt) as src:
        if src.crs is None:
            raise ValueError("O MDT raster está sem CRS.")

        pontos_raster = pontos_gdf.to_crs(src.crs)
        coordenadas = [(ponto.x, ponto.y) for ponto in pontos_raster.geometry]
        valores = []

        for valor in src.sample(coordenadas, masked=True):
            cota = valor[0]

            if hasattr(cota, "mask") and cota.mask:
                valores.append(pd.NA)
            elif src.nodata is not None and float(cota) == float(src.nodata):
                valores.append(pd.NA)
            else:
                valores.append(float(cota))

    pontos_gdf["cota_mdt_m"] = valores
    pontos_gdf = pontos_gdf.dropna(subset=["cota_mdt_m"])

    if pontos_gdf.empty:
        return pd.DataFrame(columns=[
            "id_trecho",
            "cota_min_m",
            "cota_media_m",
            "cota_max_m",
            "qtd_pontos_mdt"
        ])

    cotas_por_trecho = (
        pontos_gdf
        .groupby("id_trecho")["cota_mdt_m"]
        .agg(
            cota_min_m="min",
            cota_media_m="mean",
            cota_max_m="max",
            qtd_pontos_mdt="count"
        )
        .reset_index()
    )

    return cotas_por_trecho


limite_inundacao = 0

lista_manchas = []

for tempo, caminho_tif in caminhos_manchas_tif.items():
    mancha = converter_raster_inundacao_para_vetor(
        caminho_tif=caminho_tif,
        tempo_recorrencia=tempo,
        limite_inundacao=limite_inundacao
    )

    if not mancha.empty:
        lista_manchas.append(mancha)

if len(lista_manchas) == 0:
    raise ValueError("Nenhuma mancha de inundação válida foi gerada.")

manchas_inundacao = pd.concat(lista_manchas, ignore_index=True)
manchas_inundacao = gpd.GeoDataFrame(
    manchas_inundacao,
    geometry="geometry",
    crs=lista_manchas[0].crs
)

print("Manchas de inundação convertidas com sucesso.")
print(manchas_inundacao[[campo_tempo_recorrencia]])

if rede_viaria.crs != manchas_inundacao.crs:
    rede_viaria = rede_viaria.to_crs(manchas_inundacao.crs)

rede_wgs84 = rede_viaria.to_crs(epsg=4326)
crs_metrico = rede_wgs84.estimate_utm_crs()

rede_viaria_metrica = rede_viaria.to_crs(crs_metrico)
manchas_inundacao_metrica = manchas_inundacao.to_crs(crs_metrico)

rede_viaria_metrica["id_trecho"] = rede_viaria_metrica.index.astype(str)
rede_viaria_metrica["extensao_m"] = rede_viaria_metrica.geometry.length

extensao_total_rede_m = rede_viaria_metrica["extensao_m"].sum()
numero_total_trechos = len(rede_viaria_metrica)

print(f"CRS métrico utilizado: {crs_metrico}")
print(f"Extensão total da rede viária: {extensao_total_rede_m:,.2f} m")
print(f"Número total de trechos viários: {numero_total_trechos}")

lista_vias_afetadas = []
lista_indicadores = []

for tempo in manchas_inundacao_metrica[campo_tempo_recorrencia].unique():
    mancha_tr = manchas_inundacao_metrica[
        manchas_inundacao_metrica[campo_tempo_recorrencia] == tempo
    ]

    vias_afetadas_tr = gpd.overlay(
        rede_viaria_metrica,
        mancha_tr[[campo_tempo_recorrencia, "geometry"]],
        how="intersection",
        keep_geom_type=False
    )

    if vias_afetadas_tr.empty:
        extensao_afetada_m = 0
        percentual_afetado = 0
        numero_trechos_afetados = 0
        cota_minima_m = None
        cota_media_m = None
        cota_maxima_m = None
        qtd_pontos_mdt = 0

        print(f"{tempo}: nenhuma via afetada.")

    else:
        vias_afetadas_tr["extensao_afetada_m"] = vias_afetadas_tr.geometry.length
        vias_afetadas_tr[campo_tempo_recorrencia] = tempo

        cotas_por_trecho = calcular_cotas_vias_por_mdt(
            vias_gdf=vias_afetadas_tr,
            caminho_mdt=caminho_mdt_raster,
            intervalo_m=intervalo_amostragem_mdt_m
        )

        if cotas_por_trecho.empty:
            print(f"AVISO: Nenhum ponto das vias afetadas recebeu cota do MDT em {tempo}.")
            vias_afetadas_tr["cota_min_m"] = pd.NA
            vias_afetadas_tr["cota_media_m"] = pd.NA
            vias_afetadas_tr["cota_max_m"] = pd.NA
            vias_afetadas_tr["qtd_pontos_mdt"] = 0
            cota_minima_m = None
            cota_media_m = None
            cota_maxima_m = None
            qtd_pontos_mdt = 0
        else:
            vias_afetadas_tr = vias_afetadas_tr.merge(
                cotas_por_trecho,
                on="id_trecho",
                how="left"
            )

            cota_minima_m = vias_afetadas_tr["cota_min_m"].min()
            cota_media_m = vias_afetadas_tr["cota_media_m"].mean()
            cota_maxima_m = vias_afetadas_tr["cota_max_m"].max()
            qtd_pontos_mdt = int(vias_afetadas_tr["qtd_pontos_mdt"].fillna(0).sum())

        extensao_afetada_m = vias_afetadas_tr["extensao_afetada_m"].sum()
        percentual_afetado = (extensao_afetada_m / extensao_total_rede_m) * 100
        numero_trechos_afetados = vias_afetadas_tr["id_trecho"].nunique()

        lista_vias_afetadas.append(vias_afetadas_tr)

        print(
            f"{tempo}: {extensao_afetada_m:,.2f} m afetados "
            f"({percentual_afetado:.2f}%). "
            f"Cotas MDT nas vias afetadas: min={cota_minima_m}, "
            f"média={cota_media_m}, max={cota_maxima_m}. "
            f"Pontos amostrados={qtd_pontos_mdt}."
        )

    lista_indicadores.append({
        campo_tempo_recorrencia: tempo,
        "extensao_total_rede_m": extensao_total_rede_m,
        "extensao_afetada_m": extensao_afetada_m,
        "percentual_rede_afetada": percentual_afetado,
        "numero_total_trechos": numero_total_trechos,
        "numero_trechos_afetados": numero_trechos_afetados,
        "cota_minima_mdt_vias_afetadas_m": cota_minima_m,
        "cota_media_mdt_vias_afetadas_m": cota_media_m,
        "cota_maxima_mdt_vias_afetadas_m": cota_maxima_m,
        "qtd_pontos_mdt_amostrados": qtd_pontos_mdt
    })

tabela_indicadores_tr = pd.DataFrame(lista_indicadores)

if len(lista_vias_afetadas) > 0:
    vias_afetadas = pd.concat(lista_vias_afetadas, ignore_index=True)
    vias_afetadas = gpd.GeoDataFrame(
        vias_afetadas,
        geometry="geometry",
        crs=crs_metrico
    )
    analise_com_intersecao = True
else:
    vias_afetadas = gpd.GeoDataFrame(geometry=[], crs=crs_metrico)
    analise_com_intersecao = False

print(tabela_indicadores_tr)

campos_nome_via = ["name", "nome", "rua", "logradouro"]
campos_classificacao = ["highway", "classe", "tipo", "classificacao", "classificação"]

campo_nome_via = identificar_campo(rede_viaria_metrica, campos_nome_via)
campo_classificacao = identificar_campo(rede_viaria_metrica, campos_classificacao)

if campo_nome_via:
    print(f"Campo de nome da via identificado: {campo_nome_via}")
else:
    print("AVISO: Nenhum campo de nome da via foi identificado.")

if campo_classificacao:
    print(f"Campo de classificação viária identificado: {campo_classificacao}")
else:
    print("AVISO: Nenhum campo de classificação viária foi identificado.")

if analise_com_intersecao:
    extensao_afetada_m = vias_afetadas["extensao_afetada_m"].sum()
    percentual_afetado = (extensao_afetada_m / extensao_total_rede_m) * 100
    numero_trechos_afetados = vias_afetadas["id_trecho"].nunique()
    cota_minima_geral_m = vias_afetadas["cota_min_m"].min()
    cota_media_geral_m = vias_afetadas["cota_media_m"].mean()
    cota_maxima_geral_m = vias_afetadas["cota_max_m"].max()
    qtd_pontos_mdt_geral = int(vias_afetadas["qtd_pontos_mdt"].fillna(0).sum())
else:
    extensao_afetada_m = 0
    percentual_afetado = 0
    numero_trechos_afetados = 0
    cota_minima_geral_m = None
    cota_media_geral_m = None
    cota_maxima_geral_m = None
    qtd_pontos_mdt_geral = 0

tabela_resumo = pd.DataFrame({
    "indicador": [
        "Extensão total da rede viária (m)",
        "Extensão total afetada (m)",
        "Percentual da rede afetada (%)",
        "Número total de trechos viários",
        "Número de trechos afetados",
        "Cota mínima MDT das vias afetadas (m)",
        "Cota média MDT das vias afetadas (m)",
        "Cota máxima MDT das vias afetadas (m)",
        "Quantidade de pontos MDT amostrados"
    ],
    "valor": [
        extensao_total_rede_m,
        extensao_afetada_m,
        percentual_afetado,
        numero_total_trechos,
        numero_trechos_afetados,
        cota_minima_geral_m,
        cota_media_geral_m,
        cota_maxima_geral_m,
        qtd_pontos_mdt_geral
    ]
})

print(tabela_resumo)

tabelas_adicionais = {}

if analise_com_intersecao and campo_nome_via and campo_nome_via in vias_afetadas.columns:
    extensao_cota_por_nome = (
        vias_afetadas
        .groupby([campo_tempo_recorrencia, campo_nome_via], dropna=False)
        .agg({
            "extensao_afetada_m": "sum",
            "cota_min_m": "min",
            "cota_media_m": "mean",
            "cota_max_m": "max",
            "qtd_pontos_mdt": "sum"
        })
        .reset_index()
        .sort_values([campo_tempo_recorrencia, "extensao_afetada_m"], ascending=[True, False])
    )

    tabelas_adicionais["extensao_cota_por_nome_via"] = extensao_cota_por_nome
    print(extensao_cota_por_nome)
else:
    print("AVISO: Não foi possível calcular extensão e cota por nome da via.")

if analise_com_intersecao and campo_classificacao and campo_classificacao in vias_afetadas.columns:
    extensao_cota_por_classificacao = (
        vias_afetadas
        .groupby([campo_tempo_recorrencia, campo_classificacao], dropna=False)
        .agg({
            "extensao_afetada_m": "sum",
            "cota_min_m": "min",
            "cota_media_m": "mean",
            "cota_max_m": "max",
            "qtd_pontos_mdt": "sum"
        })
        .reset_index()
        .sort_values([campo_tempo_recorrencia, "extensao_afetada_m"], ascending=[True, False])
    )

    tabelas_adicionais["extensao_cota_por_classificacao"] = extensao_cota_por_classificacao
    print(extensao_cota_por_classificacao)
else:
    print("AVISO: Não foi possível calcular extensão e cota por classificação viária.")

rede_web = rede_viaria_metrica.to_crs(epsg=4326)
manchas_web = manchas_inundacao_metrica.to_crs(epsg=4326)

if analise_com_intersecao:
    vias_afetadas_web = vias_afetadas.to_crs(epsg=4326)

rede_web["geometry"] = rede_web.geometry.simplify(0.00001, preserve_topology=True)
manchas_web["geometry"] = manchas_web.geometry.simplify(0.00001, preserve_topology=True)

if analise_com_intersecao:
    vias_afetadas_web["geometry"] = vias_afetadas_web.geometry.simplify(
        0.00001,
        preserve_topology=True
    )

centroide = rede_web.geometry.union_all().centroid
centro_mapa = [centroide.y, centroide.x]

print(f"Centro do mapa: {centro_mapa}")

mapa_dinamico = folium.Map(
    location=centro_mapa,
    zoom_start=13,
    tiles="OpenStreetMap",
    control_scale=True
)

folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(mapa_dinamico)
folium.TileLayer("Esri.WorldImagery", name="Imagem de satélite").add_to(mapa_dinamico)

folium.GeoJson(
    rede_web,
    name="Rede viária",
    style_function=lambda feature: {
        "color": "#666666",
        "weight": 2,
        "opacity": 0.65
    }
).add_to(mapa_dinamico)

cores_manchas = {
    "TR 10 anos": "#74add1",
    "TR 50 anos": "#2b83ba",
    "TR 100 anos": "#08306b"
}

cores_vias = {
    "TR 10 anos": "#fdae61",
    "TR 50 anos": "#f46d43",
    "TR 100 anos": "#d7191c"
}

for tempo in manchas_web[campo_tempo_recorrencia].unique():
    mancha_tr = manchas_web[manchas_web[campo_tempo_recorrencia] == tempo]

    grupo_mancha = folium.FeatureGroup(name=f"Mancha - {tempo}", show=True)
    cor_mancha = cores_manchas.get(tempo, "#2b83ba")

    folium.GeoJson(
        mancha_tr,
        style_function=lambda feature, cor=cor_mancha: {
            "fillColor": cor,
            "color": cor,
            "weight": 1,
            "fillOpacity": 0.35
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[campo_tempo_recorrencia],
            aliases=["Tempo de recorrência:"]
        )
    ).add_to(grupo_mancha)

    grupo_mancha.add_to(mapa_dinamico)

    if analise_com_intersecao:
        vias_tr = vias_afetadas_web[
            vias_afetadas_web[campo_tempo_recorrencia] == tempo
        ]

        if not vias_tr.empty:
            grupo_vias = folium.FeatureGroup(
                name=f"Vias afetadas - {tempo}",
                show=True
            )
            cor_via = cores_vias.get(tempo, "#d7191c")

            campos_tooltip = [
                campo_tempo_recorrencia,
                "extensao_afetada_m",
                "cota_min_m",
                "cota_media_m",
                "cota_max_m",
                "qtd_pontos_mdt"
            ]
            aliases_tooltip = [
                "Tempo de recorrência:",
                "Extensão afetada (m):",
                "Cota MDT mínima (m):",
                "Cota MDT média (m):",
                "Cota MDT máxima (m):",
                "Pontos MDT amostrados:"
            ]

            if campo_nome_via and campo_nome_via in vias_tr.columns:
                campos_tooltip.insert(0, campo_nome_via)
                aliases_tooltip.insert(0, "Via:")

            if campo_classificacao and campo_classificacao in vias_tr.columns:
                campos_tooltip.append(campo_classificacao)
                aliases_tooltip.append("Classificação:")

            folium.GeoJson(
                vias_tr,
                style_function=lambda feature, cor=cor_via: {
                    "color": cor,
                    "weight": 5,
                    "opacity": 0.95
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=campos_tooltip,
                    aliases=aliases_tooltip,
                    localize=True,
                    sticky=True
                )
            ).add_to(grupo_vias)

            grupo_vias.add_to(mapa_dinamico)

MiniMap(toggle_display=True).add_to(mapa_dinamico)
Fullscreen(position="topright").add_to(mapa_dinamico)

MeasureControl(
    position="topleft",
    primary_length_unit="meters",
    secondary_length_unit="kilometers"
).add_to(mapa_dinamico)

folium.LayerControl(collapsed=False).add_to(mapa_dinamico)

RESULTADOS_DIR.mkdir(exist_ok=True)

tabela_indicadores_tr.to_csv(
    RESULTADOS_DIR / "indicadores_por_tempo_recorrencia_com_mdt_raster.csv",
    index=False,
    encoding="utf-8-sig"
)

with pd.ExcelWriter(RESULTADOS_DIR / "indicadores_por_tempo_recorrencia_com_mdt_raster.xlsx", engine="openpyxl") as writer:
    tabela_indicadores_tr.to_excel(writer, sheet_name="indicadores", index=False)
    tabela_resumo.to_excel(writer, sheet_name="resumo", index=False)

    for nome_aba, tabela in tabelas_adicionais.items():
        tabela.to_excel(writer, sheet_name=nome_aba[:31], index=False)

manchas_inundacao_metrica.to_file(
    RESULTADOS_DIR / "manchas_inundacao_por_tempo_recorrencia.geojson",
    driver="GeoJSON"
)

if analise_com_intersecao:
    vias_afetadas.to_file(
        RESULTADOS_DIR / "vias_afetadas_por_tempo_recorrencia_com_mdt_raster.geojson",
        driver="GeoJSON"
    )

mapa_dinamico.save(RESULTADOS_DIR / "mapa_dinamico_tempos_recorrencia_com_mdt_raster.html")

print("Resultados salvos na pasta resultados.")
print("Mapa dinâmico salvo em: resultados/mapa_dinamico_tempos_recorrencia_com_mdt_raster.html")

arquivo_zip_resultados = BASE_DIR / "resultados_analise_inundacao_rede_viaria_com_mdt_raster.zip"

if arquivo_zip_resultados.exists():
    arquivo_zip_resultados.unlink()

shutil.make_archive(
    base_name=str(BASE_DIR / "resultados_analise_inundacao_rede_viaria_com_mdt_raster"),
    format="zip",
    root_dir=RESULTADOS_DIR
)

print(f"Arquivo ZIP criado: {arquivo_zip_resultados}")
