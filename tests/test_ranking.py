"""T04 a T06 · TF-IDF y BM25 contra sus fórmulas, `rank_bm25`, filtro de fecha y top-k (PRD §6.4)."""
from __future__ import annotations

import math
import subprocess
import sys
from collections import Counter

import numpy as np
import pandas as pd
import pytest

from mtx import indice, ranking
from mtx.preproceso import tokenizar, tokenizar_pasaje

# --------------------------------------------------------------------------- utilidades


def _modelos(toks):
    ind = indice.construir([str(i) for i in range(len(toks))], toks)
    vec, X = ranking.ajustar_tfidf(toks)
    return ind, ranking.BM25(ind), ranking.Tfidf(vec, X)


def _bm25_a_mano(toks, q, k1=1.5, b=0.75):
    """Implementación independiente, término por término, de la fórmula del PRD §6.4."""
    N = len(toks)
    avgdl = sum(map(len, toks)) / N
    df = Counter(t for d in toks for t in set(d))
    out = []
    for d in toks:
        tf, s = Counter(d), 0.0
        for t in dict.fromkeys(q):
            if df[t] == 0 or tf[t] == 0:
                continue
            idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avgdl))
        out.append(s)
    return np.array(out)


def _tfidf_a_mano(toks, q):
    """Coseno con `w = (1 + ln tf) * (ln((1+N)/(1+df)) + 1)` y normalización L2."""
    N = len(toks)
    df = Counter(t for d in toks for t in set(d))

    def vector(d):
        v = {t: (1 + math.log(c)) * (math.log((1 + N) / (1 + df[t])) + 1)
             for t, c in Counter(d).items() if df[t]}
        n = math.sqrt(sum(x * x for x in v.values()))
        return {t: x / n for t, x in v.items()} if n else {}

    vq = vector(q)
    return np.array([sum(w * vq.get(t, 0.0) for t, w in vector(d).items()) for d in toks])


TOKS = [
    ["tren", "maya", "tren", "obra"],
    ["vacuna", "covid", "vacuna", "vacuna", "dosis"],
    ["tren", "vacuna"],
    ["refineria", "pemex", "obra", "obra", "obra", "tabasco"],
    [],
]


def _corpus_aleatorio(n=200, vocab=60, semilla=7):
    """Corpus con distribución tipo Zipf: hay términos con df > N/2 y términos raros."""
    rng = np.random.default_rng(semilla)
    pesos = 1 / np.arange(1, vocab + 1)
    pesos /= pesos.sum()
    palabras = [f"t{i}" for i in range(vocab)]
    return [list(rng.choice(palabras, size=rng.integers(0, 40), p=pesos)) for _ in range(n)]


# --------------------------------------------------------------------------- T04: fórmulas


def test_bm25_valor_calculado_a_mano():
    """Caso mínimo a mano: N=2, avgdl=2, q=["a"]. Pasaje 0 = ["a","b"], pasaje 1 = ["b","b"].
    idf(a) = ln(1 + 1.5/1.5) = ln 2; score_0 = ln2 * 1*2.5 / (1 + 1.5*(0.25 + 0.75*1)) = ln2."""
    ind, bm, _ = _modelos([["a", "b"], ["b", "b"]])
    s = bm.puntajes(["a"])
    assert s[0] == pytest.approx(math.log(2), abs=1e-12)
    assert s[1] == 0.0


@pytest.mark.parametrize("q", [["tren"], ["vacuna", "dosis"], ["obra", "obra", "tabasco"],
                               ["tren", "vacuna", "pemex", "maya"]])
def test_bm25_y_tfidf_coinciden_con_la_formula(q):
    _, bm, tf = _modelos(TOKS)
    np.testing.assert_allclose(bm.puntajes(q), _bm25_a_mano(TOKS, q), atol=1e-12)
    np.testing.assert_allclose(tf.puntajes(q), _tfidf_a_mano(TOKS, q), atol=1e-12)


def test_terminos_repetidos_cuentan_una_vez_en_bm25():
    _, bm, _ = _modelos(TOKS)
    np.testing.assert_array_equal(bm.puntajes(["obra", "obra"]), bm.puntajes(["obra"]))


def test_terminos_desconocidos_y_consulta_vacia_dan_ceros_sin_nan():
    _, bm, tf = _modelos(TOKS)
    for q in (["inexistente"], [], ["inexistente", "otro"]):
        for s in (bm.puntajes(q), tf.puntajes(q)):
            assert s.shape == (len(TOKS),)
            assert not np.isnan(s).any()
            assert (s == 0).all()
    # El pasaje vacío nunca puntúa ni produce NaN.
    assert bm.puntajes(["tren"])[4] == 0.0 and tf.puntajes(["tren"])[4] == 0.0


class BM25Propio:
    """Envoltura para crear, sin importar `rank_bm25` a nivel de módulo, una subclase de
    `BM25Okapi` con el idf positivo del proyecto (PRD §6.4)."""

    @staticmethod
    def clase():
        rank_bm25 = pytest.importorskip("rank_bm25")

        class _BM25(rank_bm25.BM25Okapi):
            def _calc_idf(self, nd):
                for termino, df in nd.items():
                    self.idf[termino] = math.log(1 + (self.corpus_size - df + 0.5) / (df + 0.5))
        return _BM25, rank_bm25.BM25Okapi


def test_bm25_coincide_con_subclase_de_rank_bm25():
    sub, _ = BM25Propio.clase()
    toks = _corpus_aleatorio()
    _, bm, _ = _modelos(toks)
    ref = sub(toks)
    consultas = [["t0"], ["t1", "t5"], ["t3", "t3", "t20"], ["t59", "t0", "t12"],
                 ["t7", "t8", "t9", "inexistente"]]
    for q in consultas:
        unicos = list(dict.fromkeys(q))  # rank_bm25 suma los repetidos; el PRD los cuenta una vez
        np.testing.assert_allclose(bm.puntajes(q), ref.get_scores(unicos), atol=1e-6)


def test_sin_subclase_bm25okapi_aplana_el_idf_de_los_terminos_frecuentes():
    """Documenta por qué se compara contra una subclase y no contra `BM25Okapi` directo.

    `BM25Okapi` usa idf = ln((N-df+0.5)/(df+0.5)); cuando sale negativo (df > N/2) lo reemplaza
    por un piso `epsilon * idf_promedio`. Efectos medidos en este corpus sintético:
    1. Todos los términos con df > N/2 reciben el mismo idf: se pierde el orden por df, que el idf
       propio, ln(1 + (N-df+0.5)/(df+0.5)), conserva (estrictamente decreciente en df).
    2. La diferencia ln(1 + (df+0.5)/(N-df+0.5)) crece con df: en términos raros es pequeña en
       términos relativos y se acerca a ln 2 cerca de df = N/2. Por el piso, en df > N/2 la
       diferencia absoluta no es necesariamente la mayor (matiz frente al PRD §6.4).
    """
    _, okapi = BM25Propio.clase()
    toks = _corpus_aleatorio()
    ind, _, _ = _modelos(toks)
    ref = okapi(toks)
    frecuentes = [t for t in ind.postings if ind.df[t] > ind.N / 2]
    assert len(frecuentes) >= 2
    assert len({ref.idf[t] for t in frecuentes}) == 1  # piso común
    assert ref.idf[frecuentes[0]] == pytest.approx(ref.epsilon * ref.average_idf)
    propios = {ind.idf_bm25(t) for t in frecuentes}
    assert len(propios) == len({ind.df[t] for t in frecuentes})  # el propio distingue por df
    por_df = sorted(ind.postings, key=lambda t: ind.df[t])
    idf = [ind.idf_bm25(t) for t in por_df]
    assert all(a >= b for a, b in zip(idf, idf[1:]))
    raros = [t for t in ind.postings if ind.df[t] <= ind.N / 10]
    assert raros
    assert max(abs(ind.idf_bm25(t) - ref.idf[t]) / ind.idf_bm25(t) for t in raros) < 0.05


def test_tfidf_persistido_se_carga_en_otro_proceso(tmp_path):
    vec, X = ranking.ajustar_tfidf(TOKS)
    pkl, npz = tmp_path / "tfidf.pkl", tmp_path / "tfidf_X.npz"
    ranking.guardar_tfidf(vec, X, pkl, npz)
    codigo = ("import sys; from mtx import ranking; "
              "m = ranking.cargar_tfidf(sys.argv[1], sys.argv[2]); "
              "print(repr(float(m.puntajes(['tren', 'maya'])[0])))")
    r = subprocess.run([sys.executable, "-c", codigo, str(pkl), str(npz)], capture_output=True,
                       text=True, check=True)
    esperado = ranking.Tfidf(vec, X).puntajes(["tren", "maya"])[0]
    assert float(r.stdout.strip()) == pytest.approx(esperado, abs=1e-12)


# --------------------------------------------------------------------------- buscador sintético


def _buscador(filas):
    """`filas`: tuplas (doc_id, posicion, fecha o None, marca, cuerpo)."""
    pas = pd.DataFrame([{
        "passage_id": f"{d}_{p}", "doc_id": d, "posicion": p,
        "fecha": pd.Timestamp(f) if f else pd.NaT,
        "texto": m + c, "inicio_cuerpo": len(m),
    } for d, p, f, m, c in filas])
    toks = [tokenizar_pasaje(t, i) for t, i in zip(pas["texto"], pas["inicio_cuerpo"])]
    ind = indice.construir(list(pas["passage_id"]), toks)
    vec, X = ranking.ajustar_tfidf(toks)
    return ranking.Buscador(ind, ranking.Tfidf(vec, X), pas)


FILAS = [
    (9, 1, "2020-01-01", "PREGUNTA: ", "La refinería de Dos Bocas en Tabasco."),
    (10, 2, "2020-01-01", "PREGUNTA: ", "La refinería de Dos Bocas en Tabasco."),  # empate exacto
    (10, 0, "2020-06-30", "", "Refinería, refinería y Pemex en Paraíso, Tabasco."),
    (3, 4, "2021-12-31", "", "Tabasco y su refinería."),
    (5, 0, None, "", "Refinería de Dos Bocas sin fecha conocida."),
    (6, 0, "2019-12-31", "", "La refinería se anunció un día antes de la ventana."),
    (7, 0, "2022-01-01", "", "La refinería, un día después de la ventana."),
    (8, 0, "2020-09-09", "", "El Tren Maya avanza."),
] + [(100 + i, 0, "2020-08-08", "", f"Vacunas lote {i} en Tabasco.") for i in range(12)]
# Ventana 2020-01-01 a 2020-06-30: exactamente 9_1, 10_2 y 10_0.


# --------------------------------------------------------------------------- T05: fecha


def test_mascara_limites_exactos_inclusivos():
    f = np.array(["2019-12-31", "2020-01-01", "2021-12-31", "2022-01-01", "NaT"],
                 dtype="datetime64[ns]")
    np.testing.assert_array_equal(ranking.mascara_fecha(f, "2020-01-01", "2021-12-31"),
                                  [False, True, True, False, False])


def test_mascara_sin_limites_incluye_nat_y_ventanas_abiertas():
    f = np.array(["2019-12-31", "2022-01-01", "NaT"], dtype="datetime64[ns]")
    np.testing.assert_array_equal(ranking.mascara_fecha(f, None, None), [True, True, True])
    np.testing.assert_array_equal(ranking.mascara_fecha(f, "", "  "), [True, True, True])
    np.testing.assert_array_equal(ranking.mascara_fecha(f, float("nan"), None), [True, True, True])
    np.testing.assert_array_equal(ranking.mascara_fecha(f, "2020-01-01", None), [False, True, False])
    np.testing.assert_array_equal(ranking.mascara_fecha(f, None, "2020-01-01"), [True, False, False])


def test_mascara_acepta_fechas_con_hora_dentro_del_ultimo_dia():
    f = np.array(["2021-12-31T18:30"], dtype="datetime64[ns]")
    assert ranking.mascara_fecha(f, "2021-12-31", "2021-12-31").all()


@pytest.mark.parametrize("desde,hasta,mensaje", [
    ("2022-01-01", "2021-01-01", "invertida"),
    ("2020-13-45", None, "inválido"),
    (None, "no es fecha", "inválido"),
])
def test_ventana_invertida_o_invalida_es_error_claro(desde, hasta, mensaje):
    f = np.array(["2020-01-01"], dtype="datetime64[ns]")
    with pytest.raises(ValueError, match=mensaje):
        ranking.mascara_fecha(f, desde, hasta)
    with pytest.raises(ValueError, match=mensaje):
        _buscador(FILAS).buscar("refinería", desde, hasta)


def test_filtro_no_recalcula_el_modelo():
    """El filtro cambia el conjunto elegible, no N, df, idf ni avgdl."""
    b = _buscador(FILAS)
    for modelo in ranking.MODELOS:
        sin, _ = b.buscar("refinería Tabasco", modelo=modelo, k=50)
        con, _ = b.buscar("refinería Tabasco", "2020-01-01", "2021-12-31", modelo=modelo, k=50)
        p_sin = dict(zip(sin["passage_id"], sin["puntaje"]))
        for pid, s in zip(con["passage_id"], con["puntaje"]):
            assert s == p_sin[pid]


def test_con_filtro_nunca_se_cuelan_excluidos_ni_nat():
    b = _buscador(FILAS)
    for modelo in ranking.MODELOS:
        res, est = b.buscar("refinería Dos Bocas", "2020-01-01", "2021-12-31", modelo=modelo, k=50)
        assert res["fecha"].between(pd.Timestamp("2020-01-01"), pd.Timestamp("2021-12-31")).all()
        assert not {"5_0", "6_0", "7_0"} & set(res["passage_id"])
        assert est["excluidos_fecha_desconocida"] == 1
        assert est["elegibles"] + est["excluidos_por_filtro"] == len(FILAS)
        sin, est_sin = b.buscar("refinería Dos Bocas", modelo=modelo, k=50)
        assert "5_0" in set(sin["passage_id"])  # NaT entra sin filtro
        assert est_sin["excluidos_por_filtro"] == 0 and est_sin["excluidos_fecha_desconocida"] == 0


# --------------------------------------------------------------------------- T06: top-k


def _consistente(res, k_esperado):
    assert len(res) == k_esperado
    assert list(res["rango"]) == list(range(1, k_esperado + 1))
    assert res["passage_id"].is_unique
    assert (np.diff(res["puntaje"].to_numpy()) <= 0).all()


@pytest.mark.parametrize("modelo", ranking.MODELOS)
def test_cero_candidatos(modelo):
    res, est = _buscador(FILAS).buscar("refinería", "2030-01-01", "2030-12-31", modelo=modelo)
    _consistente(res, 0)
    assert est["elegibles"] == 0
    assert any("no se rellena" in a for a in est["avisos"])


@pytest.mark.parametrize("modelo", ranking.MODELOS)
def test_tres_candidatos_no_se_rellena(modelo):
    res, est = _buscador(FILAS).buscar("refinería", "2020-01-01", "2020-06-30", modelo=modelo)
    _consistente(res, 3)
    assert set(res["passage_id"]) == {"9_1", "10_2", "10_0"}
    assert est["elegibles"] == 3
    assert any("Solo hay 3" in a for a in est["avisos"])


@pytest.mark.parametrize("modelo", ranking.MODELOS)
def test_diez_candidatos(modelo):
    res, est = _buscador(FILAS).buscar("vacunas Tabasco", "2020-08-08", "2020-08-08", modelo=modelo)
    _consistente(res, 10)
    assert est["elegibles"] == 12 and not any("Solo hay" in a for a in est["avisos"])
    assert res["sin_senal_lexica"].eq(0).all()


@pytest.mark.parametrize("modelo", ranking.MODELOS)
def test_terminos_desconocidos_marcan_sin_senal(modelo):
    res, est = _buscador(FILAS).buscar("xilófono zarzamora", modelo=modelo)
    _consistente(res, 10)
    assert (res["puntaje"] == 0).all() and res["sin_senal_lexica"].eq(1).all()
    assert any("puntaje 0" in a for a in est["avisos"])


def test_consulta_vacia_devuelve_estado_y_cero_filas():
    res, est = _buscador(FILAS).buscar("de la por para")
    assert len(res) == 0 and est["tokens"] == []
    assert any("no tiene términos" in a for a in est["avisos"])


def test_desempate_numerico_por_doc_id_y_posicion():
    """9_1 y 10_2 empatan: va primero doc_id 9 (como cadena, '10_2' < '9_1')."""
    res, _ = _buscador(FILAS).buscar("Dos Bocas", "2020-01-01", "2020-01-01", modelo="bm25")
    assert list(res["passage_id"]) == ["9_1", "10_2"]
    assert res["puntaje"].iloc[0] == res["puntaje"].iloc[1]
    p = np.array([1.0, 1.0, 1.0, 2.0])
    sel = ranking.top_k(p, np.ones(4, bool), np.array([10, 9, 9, 50]), np.array([0, 5, 2, 0]))
    np.testing.assert_array_equal(sel, [3, 2, 1, 0])


def test_cambiar_solo_la_marca_no_altera_puntajes_ni_orden():
    """D03: la marca de interlocutor queda fuera de los tokens del índice."""
    otras = [(d, p, f, "SECRETARIO DE ENERGÍA, ROCÍO NAHLE GARCÍA, REFINERÍA TABASCO: " if m
              else m, c) for d, p, f, m, c in FILAS]
    a, b = _buscador(FILAS), _buscador(otras)
    for modelo in ranking.MODELOS:
        ra, _ = a.buscar("refinería Tabasco Nahle", modelo=modelo, k=50)
        rb, _ = b.buscar("refinería Tabasco Nahle", modelo=modelo, k=50)
        pd.testing.assert_frame_equal(ra, rb)


def test_buscador_exige_el_orden_del_indice():
    b = _buscador(FILAS)
    with pytest.raises(ValueError, match="orden"):
        ranking.Buscador(b.bm25.indice, b.tfidf, b.pasajes.iloc[::-1])


def test_variantes_oficiales_formato():
    b = _buscador(FILAS)
    cons = pd.DataFrame([
        {"query_id": "Q1", "consulta": "refinería Dos Bocas", "desde": "2020-01-01",
         "hasta": "2020-06-30"},
        {"query_id": "Q2", "consulta": "vacunas", "desde": "2020-01-01", "hasta": "2021-12-31"},
    ])
    v = ranking.variantes_oficiales(b, cons)
    assert set(v["modelo"]) == {"tfidf_con_filtro", "tfidf_sin_filtro", "bm25_con_filtro",
                                "bm25_sin_filtro"}
    assert (v["variante"] == v["modelo"].str.split("_", n=1).str[1]).all()
    assert not v.duplicated(["query_id", "modelo", "rango"]).any()
    assert not v.duplicated(["query_id", "modelo", "passage_id"]).any()
    assert len(v[(v.query_id == "Q1") & (v.modelo == "bm25_con_filtro")]) == 3
    assert len(v[(v.query_id == "Q1") & (v.modelo == "bm25_sin_filtro")]) == 10


def test_tokenizar_consulta_y_pasaje_usan_la_misma_cadena():
    assert tokenizar("Refinería de Dos Bocas") == tokenizar_pasaje("X: Refinería de Dos Bocas", 3)
