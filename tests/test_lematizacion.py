"""WP-03 · Lematización y ocho variantes (PRD v2 D26)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mtx import config, consultas, indice, preproceso, ranking
from mtx.preproceso import tokenizar


def test_lema_de_vacunas_es_vacuna():
    assert tokenizar("vacunas", "lema") == ["vacuna"]


def test_maya_y_mayo_no_comparten_lema():
    (maya,) = tokenizar("el Tren Maya", "lema")[1:]
    (mayo,) = tokenizar("en mayo", "lema")
    assert maya != mayo
    assert tokenizar("maya") == tokenizar("mayo")  # con Snowball sí chocan: por eso se compara


def test_mismo_pipeline_salvo_la_raiz():
    """Mismos tokens de superficie (stoplist, longitud, covid-19) que v1: solo cambia la raíz."""
    texto = "Las vacunas contra el COVID-19 llegaron el 19 de mayo a las refinerías de la a"
    lemas, stems = tokenizar(texto, "lema"), tokenizar(texto)
    assert len(lemas) == len(stems) == len(preproceso.tokenizar_sin_stem(texto))
    assert "covid-19" in lemas and "19" in lemas
    assert tokenizar("de la a", "lema") == []


def test_nfc_y_minusculas_en_lema():
    assert tokenizar("pensión", "lema") == tokenizar("PENSIÓN", "lema")
    assert all(t == t.lower() for t in tokenizar("Programas SOCIALES del Gobierno", "lema"))


def test_lematizar_por_lotes_coincide_con_uno_por_uno():
    textos = ["Las vacunas llegaron.", "", "Refinerías y trenes", "el 19 de mayo"]
    assert preproceso.lematizar(textos) == [tokenizar(t, "lema") for t in textos]


def test_tokenizar_pasaje_lema_ignora_la_marca():
    texto = "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: Las vacunas"
    ini = texto.index("Las")
    assert indice.tokenizar_pasajes(pd.DataFrame({"texto": [texto], "inicio_cuerpo": [ini]}),
                                    raiz="lema") == [["vacuna"]]


def test_raiz_desconocida():
    with pytest.raises(ValueError):
        tokenizar("hola", "raiz")


def test_stem_sin_cambios():
    """El camino de v1 no depende de spaCy y conserva sus resultados."""
    assert tokenizar("Las vacunas contra el COVID-19") == ["vacun", "covid-19"]


def _buscador(raiz):
    pas = pd.DataFrame({
        "passage_id": ["1_0", "1_1", "2_0"], "doc_id": [1, 1, 2], "posicion": [0, 1, 0],
        "fecha": pd.to_datetime(["2020-05-01", "2020-05-01", "2021-01-10"]),
        "texto": ["Las vacunas llegaron", "El Tren Maya avanza", "En mayo hubo vacunación"],
        "inicio_cuerpo": [0, 0, 0]})
    toks = indice.tokenizar_pasajes(pas, raiz=raiz)
    ind = indice.construir(list(pas["passage_id"]), toks)
    vec, X = ranking.ajustar_tfidf(toks)
    return ranking.Buscador(ind, ranking.Tfidf(vec, X), pas, raiz=raiz)


def test_ocho_variantes_con_nombres_de_d26():
    cons = pd.DataFrame({"query_id": ["Q1"], "consulta": ["vacunas"],
                         "desde": ["2020-01-01"], "hasta": ["2020-12-31"]})
    v = ranking.variantes_v2(_buscador("stem"), _buscador("lema"), cons)
    assert set(v["modelo"]) == set(ranking.MODELOS_V2)
    assert set(v["variante"]) == {"con_filtro", "sin_filtro"}
    r = ranking.formatear_ranking(v).astype(str)
    assert ranking.validar_ranking(r, cons, ranking.MODELOS_V2) == []
    assert ranking.validar_ranking(r, cons) != []  # el validador v1 no acepta las de lema
    with pytest.raises(ValueError):
        ranking.variantes_v2(_buscador("lema"), _buscador("stem"), cons)


def test_bm25_lema_usa_las_mismas_formulas():
    b = _buscador("lema")
    tokens = tokenizar("vacunas", "lema")
    ind = b.bm25.indice
    esperado = np.zeros(ind.N)
    for t in tokens:
        for i, tf in ind.postings.get(t, {}).items():
            norma = 1.5 * (1 - 0.75 + 0.75 * ind.longitud[i] / ind.avgdl)
            esperado[i] += ind.idf_bm25(t) * tf * 2.5 / (tf + norma)
    assert np.allclose(b.bm25.puntajes(tokens), esperado)


@pytest.mark.skipif(not (config.DIR_SALIDA_V2 / "ranking_8_variantes.csv").exists()
                    or not (config.DIR_SALIDA / "ranking.csv").exists(),
                    reason="falta `make ranking-v2`")
def test_variantes_stem_identicas_a_v1():
    v2 = pd.read_csv(config.DIR_SALIDA_V2 / "ranking_8_variantes.csv", dtype=str,
                     keep_default_na=False)
    v1 = pd.read_csv(config.DIR_SALIDA / "ranking.csv", dtype=str, keep_default_na=False)
    mio = v2[v2["modelo"].isin(ranking.MODELOS_OFICIALES) & v2["query_id"].isin(set(v1["query_id"]))]
    assert mio.reset_index(drop=True).equals(v1.reset_index(drop=True))
    assert ranking.validar_ranking(v2, consultas.cargar(), ranking.MODELOS_V2) == []
