"""H4 · Evaluación IR (PRD §6.6, D08) y condiciones de entrega (PRD §13.2).

Todo ocurre en `tmp_path` con juicios SINTÉTICOS (alternan 0 y 1): prueban la tubería, nunca son
juicios humanos y no tocan `anotaciones/`, `salida/`, `data/` ni la raíz.
"""
from __future__ import annotations

import json
import pickle
import shutil

import pandas as pd
import pytest

from mtx import config, entrega, evaluacion, pool
from mtx import indice as mod_indice
from mtx.app import componentes
from mtx.preproceso import tokenizar_pasaje

# --------------------------------------------------------------------------- mundo sintético

FILAS = [(9, 1, "2020-01-01", "Tren Maya en Tabasco"), (10, 2, "2020-06-01", "huachicol y robo"),
         (10, 0, "2019-12-31", "Tren de carga"), (3, 4, None, "robo de combustible"),
         (5, 0, "2021-01-01", "Maya y Tabasco"), (6, 7, "2020-03-03", "combustible en ductos"),
         (7, 0, "2020-04-04", "otro tema distinto")]

TOPS = {
    ("Q1", "tfidf_con_filtro"): ["9_1", "10_2", "6_7"],
    ("Q1", "bm25_con_filtro"): ["10_2", "7_0", "9_1"],
    ("Q1", "tfidf_sin_filtro"): ["10_0", "9_1", "3_4"],
    ("Q1", "bm25_sin_filtro"): ["5_0", "10_0", "10_2"],
    ("Q2", "tfidf_con_filtro"): ["9_1", "6_7"],
    ("Q2", "bm25_con_filtro"): ["6_7", "9_1"],
    ("Q2", "tfidf_sin_filtro"): ["9_1", "3_4"],
    ("Q2", "bm25_sin_filtro"): ["3_4", "6_7"],
}

CONSULTAS = pd.DataFrame([
    {"query_id": "Q1", "consulta": "avances del Tren Maya en Tabasco", "desde": "2020-01-01",
     "hasta": "2020-12-31", "pregunta_extraccion": "a"},
    {"query_id": "Q2", "consulta": "combate al huachicol y robo de combustible",
     "desde": "2020-01-01", "hasta": "2020-12-31", "pregunta_extraccion": "b"},
])


def _pasajes():
    return pd.DataFrame([{
        "passage_id": f"{d}_{p}", "doc_id": d, "posicion": p,
        "fecha": pd.Timestamp(f) if f else pd.NaT, "texto": f"X: {t}", "inicio_cuerpo": 3,
        "texto_sha256": pool.sha256_texto(f"X: {t}"),
    } for d, p, f, t in FILAS])


def _ranking():
    fechas = {f"{d}_{p}": (f or "") for d, p, f, _ in FILAS}
    filas = []
    for (q, m), ids in TOPS.items():
        for r, pid in enumerate(ids, 1):
            d, p = pid.split("_")
            filas.append({"query_id": q, "modelo": m, "variante": m.split("_", 1)[1],
                          "rango": r, "passage_id": pid, "doc_id": d, "fecha": fechas[pid],
                          "posicion": p, "puntaje": f"{1 / r:.6f}"})
    return pd.DataFrame(filas)


def _mundo(tmp_path, valor=lambda i: i % 2):
    """Crea el repo en miniatura y devuelve sus `RutasIR`. Los juicios son sintéticos."""
    raiz, salida, anot = tmp_path / "raiz", tmp_path / "salida", tmp_path / "anotaciones"
    for d in (raiz, salida, anot):
        d.mkdir()
    pas = _pasajes()
    pas.to_parquet(tmp_path / "pasajes.parquet")
    CONSULTAS.to_csv(tmp_path / "consultas.csv", index=False)
    rk = _ranking()
    rk.to_csv(salida / "ranking.csv", index=False)
    shutil.copyfile(salida / "ranking.csv", raiz / "ranking.csv")
    p = pool.formatear_pool(pool.construir_pool(
        pd.read_csv(salida / "ranking.csv", dtype=str, keep_default_na=False), pas, CONSULTAS))
    p.to_csv(salida / "04_pool.csv", index=False)
    (salida / "04_pool_meta.json").write_text(json.dumps(
        {"sha256_ranking_csv": evaluacion._sha(raiz / "ranking.csv")}))
    (tmp_path / "criterios.md").write_text("criterio sintético de prueba\n")
    pc = pool.leer_pool(salida / "04_pool.csv")
    filas = [(r.query_id, r.doc_id, r.passage_id, valor(i))
             for i, r in enumerate(pc.itertuples(index=False))]
    pd.DataFrame(filas, columns=pool.COLUMNAS_JUICIOS).to_csv(
        anot / "juicios_relevancia.csv", index=False)
    ind = mod_indice.construir(list(pas["passage_id"]),
                               [tokenizar_pasaje(t, 3) for t in pas["texto"]])
    with open(tmp_path / "indice.pkl", "wb") as f:
        pickle.dump(ind, f)
    shutil.copyfile(config.DIR_CONFIG / "sinonimos_consultas.yaml", tmp_path / "sinonimos.yaml")
    app = componentes.Rutas(anotaciones=anot, criterios=tmp_path / "criterios.md",
                            pool=salida / "04_pool.csv", pasajes=tmp_path / "pasajes.parquet",
                            consultas=tmp_path / "consultas.csv")
    return evaluacion.RutasIR(
        app=app, ranking=raiz / "ranking.csv", ranking_salida=salida / "ranking.csv",
        pool_meta=salida / "04_pool_meta.json", indice_pkl=tmp_path / "indice.pkl",
        sinonimos=tmp_path / "sinonimos.yaml", dir_salida=salida, dir_raiz=raiz,
        mejor_modelo=tmp_path / "data" / "mejor_modelo.json", dir_figuras=tmp_path / "figuras")


def _correr(rp):
    return evaluacion.ejecutar_ir(rp, pd.read_parquet(rp.app.pasajes), figuras=False)


def _res(ap_t, ap_b):
    """Salida del kit fabricada para probar D08 sin juicios."""
    filas = [{"query_id": evaluacion.FILA_PROMEDIO, "modelo": m, "P@5": 0, "P@10": 0,
              "AP": {"tfidf_con_filtro": ap_t, "bm25_con_filtro": ap_b}.get(m, 0.9),
              "relevantes_recuperados": None, "relevantes_en_pool": None, "no_juzgados": None}
             for m in ("bm25_con_filtro", "bm25_sin_filtro", "tfidf_con_filtro",
                       "tfidf_sin_filtro")]
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- ejecución completa


def test_ejecucion_completa_escribe_salidas_oficiales_y_complementarias(tmp_path):
    rp = _mundo(tmp_path)
    inf = _correr(rp)
    assert inf.ok, inf.errores
    oficial = (rp.dir_salida / "resultados_ir.csv").read_bytes()
    assert rp.resultados_raiz.read_bytes() == oficial
    assert rp.juicios_raiz.read_bytes() == rp.app.juicios.read_bytes()
    res = evaluacion.leer_resultados(rp.resultados_raiz)
    assert list(res.columns) == evaluacion.COLUMNAS_RESULTADOS_IR
    assert len(res) == 2 * 4 + 4
    assert (res.loc[res["query_id"] != evaluacion.FILA_PROMEDIO, "no_juzgados"] == 0).all()
    for n in ("05_juicios_con_ventana.csv", "05_resultados_ir_ventana.csv",
              "05_relevantes_por_ventana.csv", "05_ir_por_consulta.csv",
              "05_ir_ganador_por_consulta.csv", "05_registro_evaluacion.json"):
        assert (rp.dir_salida / n).exists(), n
    m = json.loads(rp.mejor_modelo.read_text())
    assert m["modelo"] in evaluacion.CON_FILTRO
    assert m["sha256_juicios_relevancia_csv"] == evaluacion._sha(rp.juicios_raiz)
    ancho = pd.read_csv(rp.dir_salida / "05_ir_por_consulta.csv")
    assert list(ancho["query_id"]) == ["Q1", "Q2"]
    assert (ancho["bm25_con_filtro_juzgados"] == [3, 2]).all()


def test_segunda_corrida_es_identica(tmp_path):
    rp = _mundo(tmp_path)
    _correr(rp)
    antes = {p.name: p.read_bytes() for p in rp.dir_salida.glob("05_*.csv")}
    mm = rp.mejor_modelo.read_bytes()
    assert _correr(rp).ok
    assert antes == {p.name: p.read_bytes() for p in rp.dir_salida.glob("05_*.csv")}
    assert rp.mejor_modelo.read_bytes() == mm


@pytest.mark.parametrize("valor", [
    lambda i: 1 if i else "",          # un omitido (vacío) no es 0
    lambda i: i % 2 if i else "",
])
def test_juicios_incompletos_no_escriben_nada(tmp_path, valor):
    rp = _mundo(tmp_path, valor)
    inf = _correr(rp)
    assert not inf.ok
    assert any("Cobertura incompleta" in e and "omitidos por ahora" in e for e in inf.errores)
    assert not rp.juicios_raiz.exists() and not rp.resultados_raiz.exists()
    assert not rp.mejor_modelo.exists()
    assert sorted(p.name for p in rp.dir_salida.iterdir()) == [
        "04_pool.csv", "04_pool_meta.json", "ranking.csv"]


def test_pool_de_otro_ranking_bloquea(tmp_path):
    rp = _mundo(tmp_path)
    rp.pool_meta.write_text(json.dumps({"sha256_ranking_csv": "0" * 64}))
    inf = _correr(rp)
    assert any("otro ranking.csv" in e for e in inf.errores)
    assert not rp.resultados_raiz.exists()


def test_ranking_raiz_distinto_de_salida_bloquea(tmp_path):
    rp = _mundo(tmp_path)
    rp.ranking.write_text(rp.ranking.read_text().replace("1.000000", "2.000000", 1))
    assert any("no es copia" in e for e in _correr(rp).errores)


def test_insumos_congelados_cambiados_bloquean(tmp_path):
    rp = _mundo(tmp_path)
    meta = {"sha256_pool": "x", "sha256_criterios": componentes.sha256_ruta(rp.app.criterios)}
    (rp.app.anotaciones / "juicios_relevancia.csv.meta.json").write_text(json.dumps(meta))
    assert any("Cambió el pool" in e for e in _correr(rp).errores)


# --------------------------------------------------------------------------- D08


@pytest.mark.parametrize("t, b, esperado, empate", [
    (0.30, 0.40, "bm25_con_filtro", False),
    (0.45, 0.40, "tfidf_con_filtro", False),
    (0.40, 0.40, "bm25_con_filtro", True),
])
def test_d08_argmax_con_empate_a_bm25(t, b, esperado, empate):
    m = evaluacion.elegir_mejor_modelo(_res(t, b))
    assert m["modelo"] == esperado and m["empate"] is empate
    assert {m["modelo"], m["alternativa"]} == set(evaluacion.CON_FILTRO)


def test_d08_ignora_variantes_sin_filtro_y_marca_diferencia_pequena():
    m = evaluacion.elegir_mejor_modelo(_res(0.400, 0.405))
    assert m["modelo"] == "bm25_con_filtro"            # las sin filtro valen 0.9 y no cuentan
    assert m["diferencia_menor_0.01"] is True
    assert evaluacion.elegir_mejor_modelo(_res(0.30, 0.40))["diferencia_menor_0.01"] is False


def test_mejor_modelo_no_cambia_si_la_ie_ya_empezo(tmp_path):
    rp = _mundo(tmp_path)
    assert _correr(rp).ok
    antes = rp.mejor_modelo.read_bytes()
    j = pd.read_csv(rp.app.juicios, dtype=str)
    j["relevante"] = (1 - j["relevante"].astype(int)).astype(str)
    j.to_csv(rp.app.juicios, index=False)
    (rp.app.anotaciones / "muestra_gold.csv").write_text("passage_id\n")
    inf = _correr(rp)
    assert any("la IE ya empezó" in e for e in inf.errores)
    assert rp.mejor_modelo.read_bytes() == antes


def test_mejor_modelo_se_regenera_con_aviso_antes_de_la_ie(tmp_path):
    rp = _mundo(tmp_path)
    _correr(rp)
    j = pd.read_csv(rp.app.juicios, dtype=str)
    j["relevante"] = (1 - j["relevante"].astype(int)).astype(str)
    j.to_csv(rp.app.juicios, index=False)
    inf = _correr(rp)
    assert inf.ok and any("mejor_modelo.json cambió" in a for a in inf.avisos)


# --------------------------------------------------------------------------- vistas y tablas


def test_vista_con_ventana_y_conteos():
    p = pool.como_texto(pool.formatear_pool(pool.construir_pool(
        _ranking().astype(str), _pasajes(), CONSULTAS)))
    j = p[["query_id", "doc_id", "passage_id"]].assign(relevante="1")
    jv = evaluacion.juicios_con_ventana(j, p)
    q1 = jv[jv["query_id"] == "Q1"].set_index("passage_id")
    assert q1.at["9_1", "relevante"] == 1                   # en ventana
    assert q1.at["10_0", "relevante"] == 0                  # fuera de ventana (2019)
    assert q1.at["3_4", "relevante"] == 0                   # fecha desconocida no cumple
    assert (jv["relevante"] == jv["relevante_ventana"]).all()
    assert (jv["relevante_tematico"] == 1).all()
    c = evaluacion.relevantes_por_ventana(jv, ["Q1", "Q2"]).set_index("query_id")
    assert c.loc["Q1"].to_dict() == {"relevantes_tematicos": 7, "dentro_de_ventana": 4,
                                     "fuera_de_ventana": 2, "fecha_desconocida": 1}


def test_vista_con_ventana_rechaza_juicios_fuera_del_pool():
    p = pool.como_texto(pool.formatear_pool(pool.construir_pool(
        _ranking().astype(str), _pasajes(), CONSULTAS)))
    j = pd.DataFrame([["Q1", "7", "7_9", "1"]], columns=pool.COLUMNAS_JUICIOS)
    with pytest.raises(ValueError, match="fuera del pool"):
        evaluacion.juicios_con_ventana(j, p)


def test_validar_resultados_detecta_no_juzgados_y_filas_faltantes():
    filas = [{"query_id": q, "modelo": m, "P@5": 0.2, "P@10": 0.1, "AP": 0.5,
              "relevantes_recuperados": 1.0, "relevantes_en_pool": 2.0,
              "no_juzgados": 1.0 if (q, m) == ("Q2", "bm25_con_filtro") else 0.0}
             for q in ("Q1", "Q2") for m in evaluacion.MODELOS_OFICIALES]
    res = pd.concat([pd.DataFrame(filas), _res(0.1, 0.2)], ignore_index=True)
    problemas = evaluacion.validar_resultados_ir(res, CONSULTAS)
    assert len(problemas) == 1 and "Q2 bm25_con_filtro: 1" in problemas[0]
    assert evaluacion.validar_resultados_ir(res.iloc[1:], CONSULTAS)
    assert evaluacion.validar_resultados_ir(res.drop(columns="AP"), CONSULTAS)


def test_etiquetas_calculadas():
    cons = pd.DataFrame([
        {"query_id": "Q1", "consulta": "llegada de vacunas contra el COVID-19"},
        {"query_id": "Q2", "consulta": "aeropuerto Felipe Ángeles en Santa Lucía"},
        {"query_id": "Q3", "consulta": "combate al huachicol"},
    ])
    sin = config.cargar_yaml("sinonimos_consultas.yaml")["grupos"]
    df = {"lleg": 50, "vacun": 1}
    e = evaluacion.etiquetas_consultas(cons, df, 100, sin).set_index("query_id")
    assert e.at["Q1", "tiene_sigla"] == 1 and e.at["Q1", "tiene_nombre_propio"] == 0
    assert e.at["Q1", "terminos_df_alto"] == "lleg"
    assert e.at["Q2", "tiene_nombre_propio"] == 1 and e.at["Q2", "tiene_sigla"] == 0
    assert e.at["Q2", "grupo_sinonimos"] == "aifa"
    assert e.at["Q2", "sinonimos_ausentes_en_consulta"] == "AIFA"
    assert e.at["Q3", "sinonimos_ausentes_en_consulta"] == "robo de combustible"
    assert e.at["Q3", "longitud"] == "corta" and e.at["Q2", "longitud"] == "larga"


def test_ganador_por_consulta():
    filas = [{"query_id": "Q1", "modelo": m, "AP": ap}
             for m, ap in zip(evaluacion.MODELOS_OFICIALES, (0.2, 0.5, 0.1, 0.1))]
    filas += [{"query_id": "Q2", "modelo": m, "AP": 0.3} for m in evaluacion.MODELOS_OFICIALES]
    g = evaluacion.ganador_por_consulta(pd.DataFrame(filas), pd.DataFrame({"query_id": ["Q1",
                                                                                         "Q2"]}))
    g = g.set_index("query_id")
    orden = dict(zip(evaluacion.MODELOS_OFICIALES, (0.2, 0.5, 0.1, 0.1)))
    esperado = ("bm25_con_filtro" if orden["bm25_con_filtro"] > orden["tfidf_con_filtro"]
                else "tfidf_con_filtro")
    assert g.at["Q1", "ganador_con_filtro"] == esperado
    assert g.at["Q2", "ganador_con_filtro"] == "empate"
    assert g.at["Q2", "diferencia_bm25_menos_tfidf"] == 0


# --------------------------------------------------------------------------- 99_validar


def test_entrega_juicios_pendientes_no_es_falla(tmp_path):
    rp = _mundo(tmp_path, lambda i: "" if i == 0 else 1)
    cx = entrega.Contexto(rp, correr_pruebas=False)
    r = entrega.c04_juicios(cx)
    assert r.estado == entrega.PENDIENTE and not rp.juicios_raiz.exists()


def test_entrega_juicios_invalidos_es_falla(tmp_path):
    rp = _mundo(tmp_path, lambda i: 2 if i == 0 else 1)
    assert entrega.c04_juicios(entrega.Contexto(rp)).estado == entrega.FALLA


def test_entrega_tras_evaluar_reproduce_y_detecta_manipulacion(tmp_path):
    rp = _mundo(tmp_path)
    assert _correr(rp).ok
    cx = entrega.Contexto(rp, correr_pruebas=False)
    assert entrega.c04_juicios(cx).estado == entrega.OK
    assert entrega.c05_resultados_ir(cx).estado == entrega.OK
    c2 = entrega.c02_seis_csv(cx)
    assert c2.estado == entrega.PENDIENTE                    # faltan los CSV de IE
    assert any("ranking.csv, juicios_relevancia.csv, resultados_ir.csv" in d for d in c2.detalle)
    rp.resultados_raiz.write_text(rp.resultados_raiz.read_text().replace("0.", "0.9", 1))
    assert entrega.c05_resultados_ir(cx).estado == entrega.FALLA
    assert entrega.c02_seis_csv(cx).estado == entrega.FALLA  # ya no es copia de salida/


def test_entrega_juicios_editados_tras_exportar_se_reexportan(tmp_path):
    rp = _mundo(tmp_path)
    cx = entrega.Contexto(rp, correr_pruebas=False)
    entrega.c04_juicios(cx)
    j = pd.read_csv(rp.app.juicios, dtype=str)
    j.loc[0, "relevante"] = "1" if j.loc[0, "relevante"] == "0" else "0"
    j.to_csv(rp.app.juicios, index=False)
    assert entrega.c04_juicios(cx).estado == entrega.OK
    assert rp.juicios_raiz.read_bytes() == rp.app.juicios.read_bytes()


def test_entrega_codigo_de_salida_y_excepciones(tmp_path):
    R = entrega.Resultado
    pend = [R(1, "a", entrega.OK, []), R(2, "b", entrega.PENDIENTE, [])]
    assert entrega.codigo_salida(pend, parcial=True) == 0
    assert entrega.codigo_salida(pend, parcial=False) == 1
    assert entrega.codigo_salida(pend + [R(3, "c", entrega.FALLA, [])], parcial=True) == 1
    assert entrega.codigo_salida([R(10, "d", entrega.AVISO, [])], parcial=False) == 0
    rp = _mundo(tmp_path)
    rp.app.consultas.unlink()                    # rompe la condición 3
    (r,) = entrega.validar(entrega.Contexto(rp), solo={3})
    assert r.estado == entrega.FALLA and "FileNotFoundError" in r.detalle[0]


def test_entrega_condicion_1_sobre_el_repo_real():
    rp = evaluacion.rutas_ir()
    assert entrega.c01_kit_y_consultas(entrega.Contexto(rp)).estado == entrega.OK
