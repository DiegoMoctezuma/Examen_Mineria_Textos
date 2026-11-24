"""WP-06 (D28, D29): ganador v2, ranking con nombres v1, métricas y robustez. Datos inventados; el
kit corre localmente (sin red)."""
from __future__ import annotations

import importlib.util
import json
import random

import pandas as pd
import pytest

from mtx import adaptadores_kit
from mtx import evaluacion_v2 as E
from mtx.evaluacion import FILA_PROMEDIO
from mtx.ranking import MODELOS_V2


def _res(maps: dict[str, float]) -> pd.DataFrame:
    filas = [{"query_id": FILA_PROMEDIO, "modelo": m, "P@5": 0.0, "P@10": 0.0, "AP": v,
              "relevantes_recuperados": None, "relevantes_en_pool": None, "no_juzgados": None}
             for m, v in maps.items()]
    return pd.DataFrame(filas)


def _maps(**kw) -> dict[str, float]:
    base = dict.fromkeys(MODELOS_V2, 0.1)
    base.update(kw)
    return base


# --------------------------------------------------------------------------- ganador


def test_gana_el_mayor_map_con_filtro_aunque_sin_filtro_sea_mayor():
    m = E.elegir_ganador_v2(_res(_maps(bm25_lema_con_filtro=0.41, bm25_con_filtro=0.40,
                                       bm25_lema_sin_filtro=0.9)))
    assert m["modelo"] == "bm25_lema_con_filtro" and m["preprocesamiento"] == "lema"
    assert m["modelo_en_ranking_csv"] == "bm25_con_filtro"
    assert m["alternativa"] == "bm25_con_filtro" and not m["empate"]


def test_empate_a_cuatro_decimales_gana_bm25_stem():
    m = E.elegir_ganador_v2(_res(_maps(tfidf_lema_con_filtro=0.40001, bm25_con_filtro=0.40004)))
    assert m["modelo"] == "bm25_con_filtro" and m["empate"]


def test_empate_sin_bm25_stem_gana_el_primero_de_la_lista():
    m = E.elegir_ganador_v2(_res(_maps(tfidf_con_filtro=0.5, bm25_lema_con_filtro=0.5)))
    assert m["modelo"] == "tfidf_con_filtro"


def test_ranking_raiz_v2_toma_el_preprocesamiento_ganador_con_nombres_v1():
    filas = [{"query_id": q, "modelo": mo, "rango": "1", "passage_id": f"{mo}_{q}"}
             for q in ("Q2", "Q10") for mo in MODELOS_V2]
    r8 = pd.DataFrame(filas)
    lema = E.ranking_raiz_v2(r8, "lema")
    assert set(lema["modelo"]) == {"tfidf_con_filtro", "bm25_con_filtro", "tfidf_sin_filtro",
                                   "bm25_sin_filtro"}
    assert lema["passage_id"].str.contains("_lema_").all()
    assert lema["query_id"].tolist()[:4] == ["Q2"] * 4
    stem = E.ranking_raiz_v2(r8, "stem")
    assert not stem["passage_id"].str.contains("_lema_").any()


# --------------------------------------------------------------------------- métricas


def _kit_mod():
    spec = importlib.util.spec_from_file_location("evaluar_kit",
                                                  adaptadores_kit.DIR_KIT / "evaluar.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ap_y_ndcg_a_mano():
    # rel = 1,0,1 con 2 relevantes en el pool: AP = (1/1 + 2/3)/2; DCG = 1 + 1/log2(4) = 1.5,
    # ideal = 1 + 1/log2(3).
    assert E.ap([1, 0, 1], 2) == pytest.approx((1 + 2 / 3) / 2)
    assert E.ndcg([1, 0, 1], 2) == pytest.approx(1.5 / (1 + 1 / 1.5849625))
    assert E.ndcg([0, 0], 0) == 0.0 and E.ap([0], 0) == 0.0


def test_ap_coincide_con_el_kit():
    kit = _kit_mod()
    rnd = random.Random(42)
    for _ in range(50):
        rel = [rnd.randint(0, 1) for _ in range(10)]
        total = sum(rel) + rnd.randint(0, 5)
        assert E.ap(rel, total) == pytest.approx(kit.average_precision(rel, total))


def test_bootstrap_reproducible_y_contiene_la_media():
    a = pd.Series([0.1, 0.5, 0.3, 0.9, 0.2, 0.4])
    lo, hi = E.bootstrap_map(a, n=2000)
    assert (lo, hi) == E.bootstrap_map(a, n=2000)
    assert lo <= a.mean() <= hi


def test_permutacion_pareada():
    a = pd.Series([0.5, 0.6, 0.7, 0.8, 0.9, 0.55, 0.65, 0.75, 0.85, 0.95])
    assert E.permutacion_pareada(a, a, n=2000) == 1.0
    assert E.permutacion_pareada(a, a - 0.3, n=2000) < 0.01
    assert E.permutacion_pareada(a, a - 0.3, n=2000) == E.permutacion_pareada(a, a - 0.3, n=2000)


def test_sensibilidad_con_unanimidad_y_al_menos_uno():
    agr = pd.DataFrame({"query_id": ["Q1"] * 4, "doc_id": ["1", "2", "3", "4"],
                        "passage_id": ["1_1", "2_1", "3_1", "4_1"],
                        "votos_relevante": ["3", "2", "1", "0"],
                        "cerrado": ["True", "True", "True", "False"]})
    assert E.juicios_con_regla(agr, 3)["relevante"].tolist() == ["1", "0", "0"]
    assert E.juicios_con_regla(agr, 1)["relevante"].tolist() == ["1", "1", "1"]


def test_inflacion_por_pool_con_el_kit():
    # El pool v2 agrega un relevante que el ranking no recupera: el kit divide entre 2 y el AP
    # baja de 1.0 a 0.5.
    rk = pd.DataFrame({"query_id": ["Q1"], "modelo": ["bm25_con_filtro"], "rango": [1],
                       "passage_id": ["1_1"]})
    v1 = pd.DataFrame({"query_id": ["Q1"], "doc_id": ["1"], "passage_id": ["1_1"],
                       "relevante": ["1"]})
    v2 = pd.concat([v1, pd.DataFrame({"query_id": ["Q1"], "doc_id": ["9"],
                                      "passage_id": ["9_1"], "relevante": ["1"]})])
    assert E.map_por_modelo(E._kit_df(v1, rk))["bm25_con_filtro"] == 1.0
    assert E.map_por_modelo(E._kit_df(v2, rk))["bm25_con_filtro"] == 0.5


# --------------------------------------------------------------------------- insumos


def _rutas(tmp_path) -> E.RutasV2:
    return E.RutasV2(juicios=tmp_path / "juicios_relevancia.csv",
                     agregados=tmp_path / "05a_juicios_agregados.csv",
                     acuerdo_json=tmp_path / "05a_acuerdo.json",
                     cierre_juicios=tmp_path / "cierre_juicios_v2.json",
                     ranking8=tmp_path / "ranking_8_variantes.csv",
                     consultas=tmp_path / "consultas.csv", dir_salida=tmp_path / "v2",
                     mejor_modelo=tmp_path / "mejor_modelo.json")


def test_sin_cierre_no_se_evalua(tmp_path):
    inf = E.ejecutar_ir_v2(_rutas(tmp_path))
    assert not inf.ok and "cierre-juicios-v2" in inf.errores[0] and inf.escritos == []


def test_juicios_distintos_a_los_de_la_agregacion(tmp_path):
    rp = _rutas(tmp_path)
    for p in (rp.cierre_juicios, rp.juicios, rp.agregados, rp.ranking8):
        p.write_text("x\n")
    sha = {p.name: E._sha(p) for p in (rp.juicios, rp.agregados)}
    rp.acuerdo_json.write_text(json.dumps({"sha256": sha,
                                           "cierre": {"sha256": E._sha(rp.cierre_juicios)}}))
    assert E.validar_insumos(rp) == []
    rp.juicios.write_text("y\n")
    assert any("agregar-juicios" in e for e in E.validar_insumos(rp))


def test_pasaje_sin_juicio_es_aviso_no_error():
    cons = pd.DataFrame({"query_id": ["Q1"]})
    filas = [{"query_id": "Q1", "modelo": m, "P@5": 0, "P@10": 0, "AP": 0,
              "relevantes_recuperados": 0, "relevantes_en_pool": 1,
              "no_juzgados": 1 if m == "bm25_con_filtro" else 0} for m in MODELOS_V2]
    res = pd.concat([pd.DataFrame(filas), _res(dict.fromkeys(MODELOS_V2, 0.0))])
    err, av = E.validar_resultados_v2(res, cons)
    assert err == [] and len(av) == 1 and "bm25_con_filtro" in av[0]
