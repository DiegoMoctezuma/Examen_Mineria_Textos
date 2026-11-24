"""WP-02 (D24): mayoría, omitidos, cobertura y kappas contra ejemplos calculados a mano. Juicios
inventados, nunca los del equipo."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from mtx import acuerdo as K
from mtx import anotadores as A
from mtx.app import componentes as C

JUECES = ("ana", "beto", "caro")


def _asignacion(pares: list[tuple[str, str]], lote: str = "1", jueces=JUECES) -> pd.DataFrame:
    filas = [{"lote": lote, "anotador": a, "origen": "app", "orden": str(i), "query_id": q,
              "doc_id": p.split("_")[0], "passage_id": p, "texto_sha256": f"h{p}"}
             for a in jueces for i, (q, p) in enumerate(pares)]
    return pd.DataFrame(filas, columns=A.COLUMNAS_ASIGNACION)


def _escribir(dir_anot, anotador: str, valores: dict[tuple[str, str], str]) -> None:
    ruta = A.ruta_juicios(dir_anot, anotador)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    filas = [{"query_id": q, "doc_id": p.split("_")[0], "passage_id": p, "relevante": v}
             for (q, p), v in valores.items()]
    pd.DataFrame(filas, columns=["query_id", "doc_id", "passage_id", "relevante"]).to_csv(
        ruta, index=False, lineterminator="\n")


PARES = [("Q1", "10_1"), ("Q1", "11_2"), ("Q2", "12_3"), ("Q2", "13_4")]


def _caso(tmp_path, valores_por_juez):
    asig = _asignacion(PARES)
    for a, vals in zip(JUECES, valores_por_juez):
        _escribir(tmp_path, a, dict(zip(PARES, vals)))
    lar = K.largo(asig, tmp_path)
    return asig, lar, K.agregar(asig, lar)


# --------------------------------------------------------------------------- kappas a mano


def test_fleiss_contra_ejemplo_a_mano():
    # Votos «relevante» por par con 3 jueces: 3, 0, 2, 1.
    # P_i = 1, 1, 1/3, 1/3 → P̄ = 2/3; p1 = 6/12 = 1/2 → Pe = 1/2; κ = (2/3 − 1/2)/(1/2) = 1/3.
    d = K.fleiss(pd.Series([3, 0, 2, 1]))
    assert d["pares"] == 4
    assert d["acuerdo_observado"] == pytest.approx(2 / 3, abs=1e-4)
    assert d["acuerdo_esperado"] == pytest.approx(0.5)
    assert d["kappa"] == pytest.approx(1 / 3, abs=1e-4)


def test_cohen_contra_ejemplo_a_mano():
    # Coinciden 4 de 6 → po = 2/3; los dos marcan 1 en la mitad → pe = 1/2; κ = 1/3.
    d = K.cohen(pd.Series(["1", "1", "0", "0", "1", "0"]), pd.Series(["1", "0", "0", "0", "1", "1"]))
    assert d["acuerdo_observado"] == pytest.approx(2 / 3, abs=1e-4)
    assert d["kappa"] == pytest.approx(1 / 3, abs=1e-4)


def test_kappa_indefinido_si_todos_votan_igual():
    assert K.fleiss(pd.Series([3, 3]))["kappa"] != K.fleiss(pd.Series([3, 3]))["kappa"]  # NaN
    assert K.fleiss(pd.Series([], dtype=int))["pares"] == 0


# --------------------------------------------------------------------------- mayoría


def test_mayoria_dos_de_tres(tmp_path):
    _, _, agr = _caso(tmp_path, [("1", "1", "0", "1"), ("1", "0", "0", "1"),
                                 ("0", "0", "0", "1")])
    assert agr["relevante"].tolist() == ["1", "0", "0", "1"]
    assert agr["votos_relevante"].tolist() == [2, 1, 0, 3]
    assert agr["unanime"].tolist() == [False, False, True, True]
    assert agr["cerrado"].all() and (agr["jueces"] == "ana,beto,caro").all()


def test_omitido_no_cuenta_como_cero_y_el_par_no_se_cierra(tmp_path):
    _, _, agr = _caso(tmp_path, [("1", "", "0", "1"), ("1", "0", "0", "1"),
                                 ("1", "0", "0", "1")])
    fila = agr.set_index("passage_id").loc["11_2"]
    assert fila["validos"] == 2 and not fila["cerrado"] and fila["relevante"] == ""
    kit = K.exportar_kit(agr)
    assert "11_2" not in set(kit["passage_id"]) and len(kit) == 3
    assert list(kit.columns) == ["query_id", "doc_id", "passage_id", "relevante"]


def test_archivo_ausente_deja_los_pares_sin_cerrar(tmp_path):
    asig = _asignacion(PARES)
    for a in JUECES[:2]:
        _escribir(tmp_path, a, dict(zip(PARES, ("1", "1", "0", "0"))))
    agr = K.agregar(asig, K.largo(asig, tmp_path))
    assert not agr["cerrado"].any() and K.exportar_kit(agr).empty


def test_juicio_fuera_de_la_asignacion_se_ignora(tmp_path):
    asig = _asignacion(PARES)
    for a in JUECES:
        _escribir(tmp_path, a, {**dict(zip(PARES, ("1", "1", "0", "0"))), ("Q9", "99_9"): "1"})
    lar = K.largo(asig, tmp_path)
    assert "99_9" not in set(lar["passage_id"]) and len(lar) == 12


def test_orden_de_la_asignacion_por_lote(tmp_path):
    asig = pd.concat([_asignacion(PARES[2:], lote="2", jueces=("ana", "dani", "eva")),
                      _asignacion(PARES[:2], lote="1")])
    agr = K.agregar(asig, K.largo(asig, tmp_path))
    assert agr["passage_id"].tolist() == ["10_1", "11_2", "12_3", "13_4"]


# --------------------------------------------------------------------------- acuerdo


def test_acuerdo_global_lote_consulta_y_parejas(tmp_path):
    _, lar, agr = _caso(tmp_path, [("1", "1", "0", "1"), ("1", "0", "0", "1"),
                                   ("0", "0", "0", "1")])
    t = K.acuerdo(agr, lar)
    assert set(t["ambito"]) == {"global", "lote", "consulta", "pareja"}
    glob = t[t["ambito"] == "global"].iloc[0]
    assert glob["pares"] == 4 and glob["kappa"] == K.fleiss(pd.Series([2, 1, 0, 3]))["kappa"]
    parejas = t[t["ambito"] == "pareja"]
    assert parejas["clave"].tolist() == ["ana-beto", "ana-caro", "beto-caro"]
    assert parejas.set_index("clave").loc["ana-beto", "pares"] == 4


# --------------------------------------------------------------------------- cierre


def test_sin_cierre_no_se_agrega(tmp_path):
    assert "cierre-juicios-v2" in K.verificar_cierre(None, tmp_path / "a.csv", tmp_path)[0]


def test_archivo_cambiado_despues_del_cierre(tmp_path):
    asig = _asignacion(PARES)
    ruta_asig = tmp_path / "asignacion.csv"
    asig.to_csv(ruta_asig, index=False)
    for a in JUECES:
        _escribir(tmp_path, a, dict(zip(PARES, ("1", "1", "0", "0"))))
    cierre = {"sha256_asignacion": C.sha256_ruta(ruta_asig),
              "jueces": {a: {"sha256": C.sha256_ruta(A.ruta_juicios(tmp_path, a))}
                         for a in JUECES}}
    json.dumps(cierre)
    assert K.verificar_cierre(cierre, ruta_asig, tmp_path) == []
    _escribir(tmp_path, "beto", dict(zip(PARES, ("1", "1", "1", "0"))))
    err = K.verificar_cierre(cierre, ruta_asig, tmp_path)
    assert len(err) == 1 and "beto" in err[0]


def test_exportacion_pasa_validar_juicios(tmp_path):
    from mtx import pool

    asig, _, agr = _caso(tmp_path, [("1", "", "0", "1"), ("1", "0", "0", "1"),
                                    ("1", "0", "0", "1")])
    ruta = tmp_path / "juicios_relevancia.csv"
    K.exportar_kit(agr).to_csv(ruta, index=False, lineterminator="\n")
    v = pool.validar_juicios(ruta, K.pool_de(asig, agr))
    assert v.errores == []


def test_modulo_no_escribe_en_anotaciones():
    import inspect

    fuente = inspect.getsource(K)
    assert "to_csv" not in fuente and "write_text" not in fuente
