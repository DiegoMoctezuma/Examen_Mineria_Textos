"""WP-14: condiciones v2 de `make validar` con artefactos inventados en carpetas temporales."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd

from mtx import adaptadores_kit
from mtx import entrega_v2 as W
from mtx.entrega import FALLA, OK, PENDIENTE, Contexto


def _cx(tmp_path) -> Contexto:
    return Contexto(SimpleNamespace(dir_raiz=tmp_path), correr_pruebas=False)


def _agregacion(tmp_path, sin_cerrar=(), aceptar=False):
    (tmp_path / "anotaciones").mkdir(exist_ok=True)
    (tmp_path / "anotaciones" / "cierre_juicios_v2.json").write_text(
        json.dumps({"aceptar_incompletos": aceptar}))
    s2 = tmp_path / "salida" / "v2"
    s2.mkdir(parents=True, exist_ok=True)
    for n in ("juicios_relevancia.csv", "05a_juicios_agregados.csv", "05a_acuerdo.csv"):
        (s2 / n).write_text("x\n")
    sha = {n: adaptadores_kit.sha256_archivo(s2 / n)
           for n in ("juicios_relevancia.csv", "05a_juicios_agregados.csv")}
    (s2 / "05a_acuerdo.json").write_text(json.dumps({
        "sha256": sha, "pares": 3, "pares_cerrados": 3 - len(sin_cerrar),
        "pares_sin_cerrar": list(sin_cerrar), "fleiss_global": {"kappa": 0.5}}))
    return s2


def test_c16_pendiente_sin_cierre(tmp_path):
    assert W.c16_juicios_v2(_cx(tmp_path)).estado == PENDIENTE


def test_c16_ok_y_falla_por_archivo_cambiado(tmp_path):
    s2 = _agregacion(tmp_path)
    assert W.c16_juicios_v2(_cx(tmp_path)).estado == OK
    (s2 / "juicios_relevancia.csv").write_text("editado a mano\n")
    r = W.c16_juicios_v2(_cx(tmp_path))
    assert r.estado == FALLA and "juicios_relevancia.csv" in r.detalle[0]


def test_c16_pares_sin_cerrar_requieren_excepcion(tmp_path):
    _agregacion(tmp_path, sin_cerrar=[["Q1", "1_1"]])
    assert W.c16_juicios_v2(_cx(tmp_path)).estado == FALLA
    _agregacion(tmp_path, sin_cerrar=[["Q1", "1_1"]], aceptar=True)
    r = W.c16_juicios_v2(_cx(tmp_path))
    assert r.estado == OK and "excepción" in r.detalle[0]


def test_c21_tablas_y_valoraciones(tmp_path):
    from mtx import respuestas as RS

    assert W.c21_tablas_v2(_cx(tmp_path)).estado == PENDIENTE
    s2 = tmp_path / "salida" / "v2"
    s2.mkdir(parents=True)
    hashes = {f"Q{i}": f"{i:064d}" for i in range(1, 16)}
    (s2 / "10_hashes_tablas.json").write_text(json.dumps(hashes))
    r = W.c21_tablas_v2(_cx(tmp_path))
    assert r.estado == PENDIENTE and "Q1" in r.detalle[0]
    d = tmp_path / "anotaciones" / "valoraciones_v2"
    d.mkdir(parents=True)
    tok = ""
    for q, h in hashes.items():
        tok = RS.guardar_valoracion(d / "luis.yaml", tok, q, "Creíble.", h)
    assert W.c21_tablas_v2(_cx(tmp_path)).estado == OK


def test_c19_y_c20_pendientes_sin_salidas(tmp_path):
    assert W.c19_ir_v2(_cx(tmp_path)).estado == PENDIENTE
    assert W.c20_ie_v2(_cx(tmp_path)).estado == PENDIENTE


def test_c18_detecta_muestras_que_se_tocan(tmp_path, monkeypatch):
    from mtx import ambito
    from mtx import gold_v2 as V

    partes = {p: V.Parte(p, n, tmp_path / f"{p}.csv", ("u", "v"), "w", (1, 2))
              for p, n in (("seleccion", "Selección"), ("a", "Parte A"), ("b", "Parte B"))}
    monkeypatch.setattr(V, "cargar_config", lambda **kw: V.ConfigGold(partes, (), True))
    ids = {"seleccion": ["1_1"], "a": ["2_1"], "b": ["2_1"]}
    monkeypatch.setattr(V, "manifiesto", lambda p: pd.DataFrame({"passage_id": ids[p.id]}))
    (tmp_path / "anotaciones").mkdir()
    pd.DataFrame({"passage_id": ["9_9"]}).to_csv(tmp_path / "anotaciones" / "muestra_gold.csv",
                                                 index=False)
    monkeypatch.setattr(ambito, "ambito_ie", lambda *a: pd.DataFrame({"passage_id": ["1_1"]}))
    r = W.c18_muestras(_cx(tmp_path))
    assert r.estado == FALLA
    assert any("Parte A y Parte B" in d for d in r.detalle)
    assert any("ámbito IE de v1" in d for d in r.detalle)
