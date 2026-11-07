"""T07 y T08 · Pool de relevancia y `validar_juicios()` (PRD §6.5, D06).

Los juicios de estas pruebas son sintéticos y viven en `tmp_path`: nunca en `anotaciones/`.
"""
from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd
import pytest

from mtx import config, pool
from mtx.ranking import MODELOS_OFICIALES

# --------------------------------------------------------------------------- fixtures


def _pasajes():
    filas = [(9, 1, "2020-01-01"), (10, 2, "2020-06-01"), (10, 0, "2019-12-31"), (3, 4, None),
             (5, 0, "2021-01-01"), (6, 7, "2020-03-03"), (7, 0, "2020-04-04")]
    return pd.DataFrame([{
        "passage_id": f"{d}_{p}", "doc_id": d, "posicion": p,
        "fecha": pd.Timestamp(f) if f else pd.NaT, "texto": f"X: texto {d}_{p}",
        "texto_sha256": pool.sha256_texto(f"X: texto {d}_{p}"),
    } for d, p, f in filas])


CONSULTAS = pd.DataFrame([
    {"query_id": "Q1", "consulta": "a", "desde": "2020-01-01", "hasta": "2020-12-31"},
    {"query_id": "Q2", "consulta": "b", "desde": "2020-01-01", "hasta": "2020-12-31"},
])

# Cuatro rankings parcialmente solapados para Q1 y uno compartido con Q2 (T07, T08).
TOPS = {
    ("Q1", "tfidf_con_filtro"): ["9_1", "10_2", "6_7"],
    ("Q1", "bm25_con_filtro"): ["10_2", "7_0", "9_1"],
    ("Q1", "tfidf_sin_filtro"): ["10_0", "9_1", "3_4"],
    ("Q1", "bm25_sin_filtro"): ["5_0", "10_0", "10_2"],
    ("Q2", "tfidf_con_filtro"): ["9_1"],
    ("Q2", "bm25_con_filtro"): ["9_1"],
    ("Q2", "tfidf_sin_filtro"): ["9_1", "3_4"],
    ("Q2", "bm25_sin_filtro"): ["3_4"],
}


def _ranking(tops=TOPS):
    filas = []
    for (q, m), ids in tops.items():
        for r, pid in enumerate(ids, 1):
            d, p = pid.split("_")
            filas.append({"query_id": q, "modelo": m, "variante": m.split("_", 1)[1],
                          "rango": str(r), "passage_id": pid, "doc_id": d, "fecha": "",
                          "posicion": p, "puntaje": "1.000000"})
    return pd.DataFrame(filas)


def _pool():
    return pool.como_texto(pool.formatear_pool(
        pool.construir_pool(_ranking(), _pasajes(), CONSULTAS)))


def _juicios(tmp_path, filas, cabecera="query_id,doc_id,passage_id,relevante", bom=False):
    ruta = tmp_path / "juicios.csv"
    texto = cabecera + "\n" + "".join(",".join(map(str, f)) + "\n" for f in filas)
    ruta.write_bytes((b"\xef\xbb\xbf" if bom else b"") + texto.encode("utf-8"))
    return ruta


def _completos(p, valor=lambda i: i % 2):
    return [(r.query_id, r.doc_id, r.passage_id, valor(i))
            for i, r in enumerate(p.itertuples(index=False))]


# --------------------------------------------------------------------------- T07 y T08


def test_pool_es_la_union_exacta_de_las_cuatro_variantes():
    p = _pool()
    assert list(p.columns) == pool.COLUMNAS_POOL
    for q in ("Q1", "Q2"):
        union = set().union(*[set(ids) for (qq, _), ids in TOPS.items() if qq == q])
        g = p[p["query_id"] == q]
        assert set(g["passage_id"]) == union
        assert g["passage_id"].is_unique


def test_pasaje_compartido_aparece_una_vez_por_consulta():
    p = _pool()
    assert len(p[p["passage_id"] == "9_1"]) == 2
    assert set(p.loc[p["passage_id"] == "9_1", "query_id"]) == {"Q1", "Q2"}


def test_procedencia_y_mejor_rango():
    p = _pool().set_index(["query_id", "passage_id"])
    assert p.at[("Q1", "9_1"), "variantes"] == "tfidf_con_filtro|bm25_con_filtro|tfidf_sin_filtro"
    assert p.at[("Q1", "9_1"), "mejor_rango_tfidf"] == "1"
    assert p.at[("Q1", "9_1"), "mejor_rango_bm25"] == "3"
    assert p.at[("Q1", "5_0"), "mejor_rango_tfidf"] == ""  # solo lo trajo BM25
    assert p.at[("Q1", "5_0"), "variantes"] == "bm25_sin_filtro"


def test_en_ventana_con_fecha_desconocida_es_falso():
    p = _pool().set_index(["query_id", "passage_id"])
    assert p.at[("Q1", "9_1"), "en_ventana"] == "1"
    assert p.at[("Q1", "10_0"), "en_ventana"] == "0"  # 2019-12-31, un día antes
    assert p.at[("Q1", "3_4"), "en_ventana"] == "0"  # NaT
    assert p.at[("Q1", "3_4"), "fecha"] == ""


def test_orden_barajado_con_semilla_42_por_consulta_sobre_ids_ordenados():
    p = _pool()
    g = p[p["query_id"] == "Q1"]["passage_id"].tolist()
    ordenados = sorted(g, key=lambda s: tuple(map(int, s.split("_"))))
    esperado = [ordenados[i] for i in np.random.default_rng(42).permutation(len(ordenados))]
    assert g == esperado
    assert pool.hash_pool(p) == pool.hash_pool(_pool())  # determinista


def test_texto_sha256_coincide_con_el_texto():
    p = _pool()
    assert all(pool.sha256_texto(t) == h for t, h in zip(p["texto"], p["texto_sha256"]))


def test_passage_id_ausente_de_los_pasajes_falla():
    r = _ranking({**TOPS, ("Q1", "bm25_sin_filtro"): ["999_0"]})
    with pytest.raises(KeyError, match="999_0"):
        pool.construir_pool(r, _pasajes(), CONSULTAS)


def test_resumen_aportes_exclusivos():
    p = _pool()
    res = pool.resumen_pool(p.assign(en_ventana=p["en_ventana"] == "1")).set_index("query_id")
    assert res.at["Q1", "pasajes"] == 7
    assert res.at["Q1", "solo_bm25_sin_filtro"] == 1  # 5_0
    assert res.at["Q1", "solo_bm25_con_filtro"] == 1  # 7_0
    assert res.at["Q1", "fuera_de_rango_esperado"] == 1


def test_diferencias_detectan_entradas_salidas_y_textos():
    viejo = _pool()
    assert pool.diferencias_pool(viejo, _pool()) == []
    nuevo = pool.como_texto(pool.formatear_pool(pool.construir_pool(
        _ranking({**TOPS, ("Q1", "bm25_sin_filtro"): ["5_0"]}), _pasajes(), CONSULTAS)))
    dif = pool.diferencias_pool(viejo, nuevo)
    assert "Sale del pool: Q1 10_0" not in dif  # 10_0 sigue por tfidf_sin_filtro
    assert any("Cambia variantes en Q1 10_2" in d for d in dif)
    pas = _pasajes()
    pas.loc[pas.passage_id == "6_7", "texto_sha256"] = "otro"
    cambiado = pool.como_texto(pool.formatear_pool(pool.construir_pool(_ranking(), pas, CONSULTAS)))
    assert any("texto_sha256 en Q1 6_7" in d for d in pool.diferencias_pool(viejo, cambiado))


# --------------------------------------------------------------------------- validar_juicios


def test_juicios_completos_validan_y_se_exportan(tmp_path):
    p = _pool()
    ruta = _juicios(tmp_path, _completos(p))
    v = pool.validar_juicios(ruta, p, _pasajes())
    assert v.ok and v.juzgados == v.esperados == len(p)
    destino = tmp_path / "raiz.csv"
    pool.exportar_juicios(ruta, destino, v)
    assert destino.read_bytes() == ruta.read_bytes()


def test_cobertura_incompleta_es_error_y_no_se_exporta(tmp_path):
    p = _pool()
    ruta = _juicios(tmp_path, _completos(p)[:-2])  # dos omitidos: no son ceros
    v = pool.validar_juicios(ruta, p)
    assert not v.ok and any("faltan 2" in e for e in v.errores)
    with pytest.raises(ValueError):
        pool.exportar_juicios(ruta, tmp_path / "raiz.csv", v)
    assert not (tmp_path / "raiz.csv").exists()


@pytest.mark.parametrize("cambio,mensaje", [
    (lambda f: f + [("Q1", "4", "4_0", 1)], "fuera del pool"),
    (lambda f: f + [f[0]], "más de un juicio"),
    (lambda f: [(f[0][0], f[0][1], f[0][2], 2)] + f[1:], "fuera de {0, 1}"),
    (lambda f: [(f[0][0], f[0][1], f[0][2], "x")] + f[1:], "fuera de {0, 1}"),
    (lambda f: [(f[0][0], "77", f[0][2], 1)] + f[1:], "doc_id"),
])
def test_errores_de_contenido(tmp_path, cambio, mensaje):
    p = _pool()
    v = pool.validar_juicios(_juicios(tmp_path, cambio(_completos(p))), p)
    assert any(mensaje in e for e in v.errores), v.errores


def test_omitido_es_pendiente_de_cobertura_no_cero(tmp_path):
    p = _pool()
    filas = _completos(p)
    filas[0] = (*filas[0][:3], "")
    v = pool.validar_juicios(_juicios(tmp_path, filas), p)
    assert v.juzgados == len(p) - 1
    assert not any("fuera de {0, 1}" in e for e in v.errores)
    assert any("faltan 1" in e and "1 de ellos omitidos" in e for e in v.errores)


def test_errores_de_formato(tmp_path):
    p = _pool()
    filas = _completos(p)
    assert any("BOM" in e for e in pool.validar_juicios(_juicios(tmp_path, filas, bom=True),
                                                        p).errores)
    v = pool.validar_juicios(_juicios(tmp_path, filas, "query_id,passage_id,doc_id,relevante"), p)
    assert any("Cabecera" in e for e in v.errores)
    v = pool.validar_juicios(_juicios(tmp_path, [], "query_id;doc_id;passage_id;relevante"), p)
    assert any("separador" in e for e in v.errores)
    assert any("No existe" in e for e in pool.validar_juicios(tmp_path / "nada.csv", p).errores)


def test_texto_cambiado_invalida_los_juicios(tmp_path):
    p = _pool()
    pas = _pasajes()
    pas.loc[pas.passage_id == "6_7", "texto"] = "X: otro texto"
    v = pool.validar_juicios(_juicios(tmp_path, _completos(p)), p, pas)
    assert any("cambiaron de texto" in e for e in v.errores)


def test_consulta_sin_relevantes_es_aviso_no_error(tmp_path):
    p = _pool()
    filas = [(q, d, pid, 0 if q == "Q2" else 1) for q, d, pid, _ in _completos(p)]
    ruta = _juicios(tmp_path, filas)
    antes = ruta.read_bytes()
    v = pool.validar_juicios(ruta, p)
    assert v.ok
    assert any("Q2" in a and "AP indefinido" in a for a in v.avisos)
    assert ruta.read_bytes() == antes  # el validador nunca toca los juicios


# --------------------------------------------------------------------------- script 04


def _script04():
    spec = importlib.util.spec_from_file_location("s04", config.RAIZ / "scripts" / "04_pool.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not (config.DIR_SALIDA / "ranking.csv").exists(), reason="requiere make ranking")
def test_script_se_detiene_si_el_pool_cambia_y_hay_juicios(tmp_path, monkeypatch, capsys):
    mod = _script04()
    ruta_pool = tmp_path / "04_pool.csv"
    real = pool.leer_pool(config.DIR_SALIDA / "04_pool.csv") if (
        config.DIR_SALIDA / "04_pool.csv").exists() else None
    if real is None:
        pytest.skip("requiere make pool")
    alterado = real.copy()
    alterado.loc[0, "texto_sha256"] = "alterado"
    alterado.to_csv(ruta_pool, index=False)
    juicios = tmp_path / "juicios.csv"
    juicios.write_text("query_id,doc_id,passage_id,relevante\nQ1,1,1_0,1\n", encoding="utf-8")
    monkeypatch.setattr(mod, "RUTA_POOL", ruta_pool)
    monkeypatch.setattr(mod, "RUTA_JUICIOS", juicios)
    antes = ruta_pool.read_bytes()
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert e.value.code == 1
    assert "ALTO" in capsys.readouterr().out
    assert ruta_pool.read_bytes() == antes


# --------------------------------------------------------------------------- pool real


RUTA_POOL = config.DIR_SALIDA / "04_pool.csv"


@pytest.mark.skipif(not RUTA_POOL.exists(), reason="requiere make pool")
def test_pool_real_cubre_el_ranking_y_sus_textos():
    p = pool.leer_pool(RUTA_POOL)
    r = pd.read_csv(config.DIR_SALIDA / "ranking.csv", dtype=str, keep_default_na=False)
    assert set(p["query_id"]) == set(r["query_id"]) and p["query_id"].nunique() == 10
    for q, g in r.groupby("query_id"):
        assert set(p.loc[p.query_id == q, "passage_id"]) == set(g["passage_id"])
    assert not p.duplicated(["query_id", "passage_id"]).any()
    assert set(p["variantes"].str.split("|").explode()) <= set(MODELOS_OFICIALES)
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto"])
    actual = pas.set_index("passage_id")["texto"]
    assert all(pool.sha256_texto(actual[pid]) == h
               for pid, h in zip(p["passage_id"], p["texto_sha256"]))
