"""WP-12 (D31, D35): gold oficial v2, ámbito v2 y referencias del F1. Datos inventados."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from mtx import gold_v2 as V
from mtx import ie_v2 as I


def _ent(*filas, metodo=None):
    cols = ["passage_id", "tipo", "texto", "inicio", "fin"]
    df = pd.DataFrame([{"passage_id": p, "tipo": t, "texto": "x", "inicio": i, "fin": f}
                       for p, t, i, f in filas], columns=cols)
    return df.assign(metodo=metodo) if metodo else df


def _cfg(tmp_path):
    partes = {pid: V.Parte(pid, pid, tmp_path / f"{pid}.csv", ("u", "v"), "w", (1, 2))
              for pid in ("seleccion", "a", "b")}
    return V.ConfigGold(partes, (), True)


# --------------------------------------------------------------------------- gold y ámbito


def test_gold_v2_une_v1_con_a_y_b_y_deja_fuera_la_seleccion(tmp_path, monkeypatch):
    ruta_v1 = tmp_path / "gold_v1.csv"
    _ent(("1_1", "PER", 0, 3)).to_csv(ruta_v1, index=False)
    g2 = pd.concat([_ent(("2_1", "ORG", 0, 4)).assign(parte="a", pasada=1),
                    _ent(("3_1", "FECHA", 5, 9)).assign(parte="b", pasada=2),
                    _ent(("9_9", "LOC", 0, 2)).assign(parte="seleccion", pasada=1)])
    monkeypatch.setattr(V, "gold_oficial", lambda cfg, d=None: g2)
    g = I.gold_v2(_cfg(tmp_path), ruta_v1)
    assert sorted(g["passage_id"]) == ["1_1", "2_1", "3_1"]
    assert list(g.columns) == I.COLUMNAS_GOLD_KIT


def test_gold_v2_repetido_es_error(tmp_path, monkeypatch):
    ruta_v1 = tmp_path / "gold_v1.csv"
    _ent(("1_1", "PER", 0, 3)).to_csv(ruta_v1, index=False)
    monkeypatch.setattr(V, "gold_oficial", lambda cfg, d=None: _ent(("1_1", "PER", 0, 3))
                        .assign(parte="a", pasada=1))
    with pytest.raises(ValueError, match="repite"):
        I.gold_v2(_cfg(tmp_path), ruta_v1)


def test_ambito_v2_top10_del_ganador_mas_gold_sin_duplicar(tmp_path):
    rk = pd.DataFrame({"query_id": ["Q1", "Q1", "Q11"], "modelo": ["bm25_con_filtro",
                                                                  "tfidf_con_filtro",
                                                                  "bm25_con_filtro"],
                       "rango": ["1", "1", "1"], "passage_id": ["5_1", "6_1", "7_1"],
                       "doc_id": ["5", "6", "7"]})
    ruta_rk, ruta_m = tmp_path / "ranking.csv", tmp_path / "mejor.json"
    rk.to_csv(ruta_rk, index=False)
    ruta_m.write_text(json.dumps({"modelo": "bm25_lema_con_filtro",
                                  "modelo_en_ranking_csv": "bm25_con_filtro"}))
    gold = pd.DataFrame({"query_id": ["Q1", "Q2"], "passage_id": ["5_1", "8_1"],
                         "doc_id": ["5", "8"], "origen": ["v1", "v2_a"]})
    amb = I.ambito_ie_v2(ruta_rk, ruta_m, gold)
    assert amb[["query_id", "passage_id"]].values.tolist() == [["Q1", "5_1"], ["Q2", "8_1"],
                                                               ["Q11", "7_1"]]
    assert amb.set_index("passage_id").loc["5_1", "origen"] == "top10"
    assert "6_1" not in set(amb["passage_id"])


def test_pasajes_gold_v2_de_v1_a_y_b(tmp_path, monkeypatch):
    ruta = tmp_path / "muestra_v1.csv"
    pd.DataFrame({"query_id": ["Q1"], "passage_id": ["1_1"], "doc_id": ["1"]}).to_csv(ruta,
                                                                                      index=False)
    man = {"a": pd.DataFrame({"query_id": ["Q2"], "passage_id": ["2_1"], "doc_id": ["2"]}),
           "b": pd.DataFrame({"query_id": ["Q11"], "passage_id": ["3_1"], "doc_id": ["3"]})}
    monkeypatch.setattr(V, "manifiesto", lambda p: man[p.id])
    out = I.pasajes_gold_v2(_cfg(tmp_path), ruta)
    assert out["origen"].tolist() == ["v1", "v2_a", "v2_b"]


# --------------------------------------------------------------------------- referencias


def test_f1_parcial_a_mano():
    gold = _ent(("p", "PER", 0, 10), ("p", "ORG", 20, 30))
    pred = _ent(("p", "PER", 5, 12), ("p", "LOC", 20, 30), ("p", "PER", 40, 45))
    # Predicciones que solapan un gold del mismo tipo: 1 de 3; gold recuperados: 1 de 2.
    p, r, f = I.f1_parcial(gold, pred)
    assert (p, r) == (pytest.approx(1 / 3), 0.5) and f == pytest.approx(0.4)


def test_bootstrap_f1_reproducible_y_perfecto():
    gold = _ent(*[(f"p{i}", "PER", 0, 3) for i in range(5)])
    assert I.bootstrap_f1(gold, gold, [f"p{i}" for i in range(5)], n=500) == (1.0, 1.0)
    pred = _ent(("p0", "PER", 0, 3), ("p1", "PER", 0, 3), ("p2", "ORG", 0, 3))
    a = I.bootstrap_f1(gold, pred, [f"p{i}" for i in range(5)], n=500)
    assert a == I.bootstrap_f1(gold, pred, [f"p{i}" for i in range(5)], n=500)
    assert a[0] <= I._f1(2, 3, 5) <= a[1]


def test_techo_humano_suma_a_y_b_sin_micro_ni_seleccion():
    ac = pd.DataFrame([
        {"parte": "a", "pasada": 1, "tipo": "PER", "pasajes": 10, "n_anotador_1": 4,
         "n_anotador_2": 6, "coincidencias": 4},
        {"parte": "a", "pasada": 1, "tipo": "micro", "pasajes": 10, "n_anotador_1": 4,
         "n_anotador_2": 6, "coincidencias": 4},
        {"parte": "b", "pasada": 1, "tipo": "PER", "pasajes": 5, "n_anotador_1": 2,
         "n_anotador_2": 2, "coincidencias": 1},
        {"parte": "seleccion", "pasada": 1, "tipo": "PER", "pasajes": 10, "n_anotador_1": 50,
         "n_anotador_2": 50, "coincidencias": 0}])
    t = I.techo_humano(ac).set_index("tipo")
    assert t.loc["PER", "f1"] == pytest.approx(2 * 5 / 14)
    assert t.loc["TODOS", "f1"] == pytest.approx(2 * 5 / 14) and t.loc["TODOS", "pasajes"] == 15


def test_referencias_tiene_todas_las_lineas():
    gold = _ent(("p1", "PER", 0, 3), ("p1", "LOC", 5, 9), ("p2", "FECHA", 0, 5))
    pred = pd.concat([_ent(("p1", "PER", 0, 3), metodo="modelo"),
                      _ent(("p1", "LOC", 5, 9), metodo="ambos"),
                      _ent(("p2", "FECHA", 0, 5), metodo="regla"),
                      _ent(("p9", "ORG", 0, 2), metodo="regla")])
    lb = _ent(("p1", "LOC", 5, 9))
    f_v1 = _ent(("p2", "FECHA", 0, 3))
    ac = pd.DataFrame([{"parte": "a", "pasada": 1, "tipo": "PER", "pasajes": 2,
                        "n_anotador_1": 1, "n_anotador_2": 1, "coincidencias": 1}])
    r = I.referencias(gold, pred, lb, f_v1, ac, n=200)
    assert set(r["referencia"]) == {"sistema_exacto", "sistema_parcial", "linea_base_gazetteer",
                                    "fecha_reglas_v1", "fecha_reglas_v2", "techo_humano"}
    comb = r[(r["referencia"] == "sistema_exacto") & (r["metodo"] == "combinado")].iloc[0]
    assert comb["f1"] == 1.0 and comb["pasajes"] == 2  # p9 no está en el gold: no cuenta
    fe = r.set_index("referencia")
    assert fe.loc["fecha_reglas_v2", "f1"] == 1.0 and fe.loc["fecha_reglas_v1", "f1"] == 0.0


def test_modulo_no_escribe_en_anotaciones():
    import inspect

    fuente = inspect.getsource(I)
    assert "to_csv" not in fuente and "write_text" not in fuente
