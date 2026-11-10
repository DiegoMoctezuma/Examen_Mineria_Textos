"""Evaluación de IE: detalle contra el kit, complementaria de 20 IDs (P04, T10), análisis de
errores y alertas U19. Fixtures sintéticos, nunca el gold real."""
from __future__ import annotations

import pandas as pd

from mtx import adaptadores_kit
from mtx import evaluacion_ie as E

TEXTO = ("SECRETARIO, JUAN PÉREZ LUNA: El IMSS y la Secretaría de Salud de Tabasco irán a "
         "Mérida y al Tren Maya con 2 mil millones de pesos.")
IC = TEXTO.index(":") + 2


def _e(pid, tipo, frag, metodo=None, fuentes="", desde=0, texto=TEXTO):
    i = texto.index(frag, desde)
    f = {"passage_id": pid, "tipo": tipo, "texto": frag, "inicio": i, "fin": i + len(frag)}
    if metodo:
        f.update(metodo=metodo, fuentes=fuentes)
    return f


GOLD = pd.DataFrame([
    _e("1_1", "PER", "JUAN PÉREZ LUNA"),
    _e("1_1", "ORG", "IMSS"),
    _e("1_1", "ORG", "Secretaría de Salud de Tabasco"),
    _e("1_1", "LOC", "Mérida"),
    _e("1_1", "LOC", "Tren Maya"),
    _e("1_1", "MONTO", "2 mil millones de pesos"),
])
PRED = pd.DataFrame([
    _e("1_1", "PER", "JUAN", "modelo", "modelo"),                      # partida en la marca
    _e("1_1", "PER", "PÉREZ LUNA", "modelo", "modelo"),
    _e("1_1", "ORG", "IMSS", "ambos", "gazetteer_org|modelo"),        # TP
    _e("1_1", "ORG", "Secretaría de Salud", "regla", "gazetteer_org"),  # frontera
    _e("1_1", "LOC", "Mérida", "regla", "gazetteer_loc"),             # TP
    _e("1_1", "ORG", "Tren Maya", "modelo", "modelo"),                # tipo (obra)
    _e("1_1", "MONTO", "2 mil millones", "regla", "regex_monto"),     # monto sin unidad
    _e("1_1", "LOC", "pesos", "modelo", "modelo"),                    # dentro de un MONTO gold
    _e("2_1", "LOC", "Mérida", "modelo", "modelo"),                   # pasaje sin gold
])


def test_detalle_semantica_del_kit_y_estados():
    d = E.detalle(GOLD, PRED, {"1_1"}).set_index(["metodo", "tipo"])
    assert d.loc[("combinado", "TODOS"), ["tp", "fp", "fn", "soporte"]].tolist() == [2, 6, 4, 6]
    assert d.loc[("regla", "ORG"), ["tp", "predichas"]].tolist() == [1, 2]  # regla + ambos
    assert d.loc[("modelo", "ORG"), ["tp", "predichas"]].tolist() == [1, 2]
    assert d.loc[("modelo", "MONTO"), "estado"] == "sin_cobertura"
    assert d.loc[("modelo", "FECHA"), "estado"] == "sin_cobertura"
    assert d.loc[("regla", "FECHA"), "estado"] == "no_aplicable"  # sin soporte gold
    assert d.loc[("regla", "LOC"), "estado"] == "ok"


def test_detalle_coincide_con_el_kit(tmp_path):
    ent = PRED.assign(query_id="Q1", doc_id=1)[["query_id", "doc_id", "passage_id", "tipo",
                                                 "texto", "inicio", "fin", "metodo"]]
    (tmp_path / "g.csv").write_text(GOLD.to_csv(index=False), encoding="utf-8")
    (tmp_path / "e.csv").write_text(ent.to_csv(index=False), encoding="utf-8")
    kit = pd.read_csv(adaptadores_kit.ejecutar_evaluador("ie", tmp_path / "g.csv",
                                                         tmp_path / "e.csv", tmp_path))
    det = E.detalle(GOLD, PRED, set(GOLD["passage_id"]))
    assert E.coincide_con_kit(det, kit) == []
    roto = det.copy()
    roto.loc[roto.index[-1], "tp"] += 1
    assert E.coincide_con_kit(roto, kit)


def test_complementaria_20_ids_cuenta_fp_en_pasaje_sin_gold():
    oficial = E.detalle(GOLD, PRED, set(GOLD["passage_id"])).set_index(["metodo", "tipo"])
    comp = E.detalle(GOLD, PRED, {"1_1", "2_1"}).set_index(["metodo", "tipo"])
    clave = ("combinado", "TODOS")
    assert comp.loc[clave, "fp"] == oficial.loc[clave, "fp"] + 1
    assert comp.loc[clave, "tp"] == oficial.loc[clave, "tp"]
    assert comp.loc[clave, "precision"] < oficial.loc[clave, "precision"]


def test_analisis_de_errores_por_categoria():
    pas = pd.DataFrame({"passage_id": ["1_1"], "texto": [TEXTO], "inicio_cuerpo": [IC]})
    err = E.analizar_errores(GOLD, PRED, pas, obras={"tren maya"})
    cat = {(f["error"], f["categoria"], f["texto_gold"] or f["texto_pred"])
           for f in err.to_dict("records")}
    assert ("FN", "frontera:entidad_partida", "JUAN PÉREZ LUNA") in cat
    assert ("FN", "en_marca", "JUAN PÉREZ LUNA") in cat
    assert ("FP", "en_marca", "JUAN PÉREZ LUNA") in cat
    assert ("FN", "frontera", "Secretaría de Salud de Tabasco") in cat
    assert ("FN", "tipo:obra_LOC_vs_ORG", "Tren Maya") in cat
    assert ("FN", "frontera:monto_sin_unidad", "2 mil millones de pesos") in cat
    assert ("FP", "frontera:monto_sin_unidad", "2 mil millones de pesos") in cat
    # "pesos" de tipo LOC dentro del MONTO gold: solapa con gold de otro tipo, no es espuria
    assert not any(c.startswith("espuria") for _, c, _ in cat)
    assert "2_1" not in set(err["passage_id"])  # solo pasajes del gold
    # TP no aparecen como error
    assert not ((err["texto_gold"] == "IMSS") | (err["texto_pred"] == "Mérida")).any()


def test_sigla_no_reconocida_omision_y_espuria():
    gold = pd.DataFrame([_e("1_1", "ORG", "IMSS"), _e("1_1", "LOC", "Mérida")])
    pred = pd.DataFrame([_e("1_1", "FECHA", "Tren", "regla", "regex_fecha")])
    pas = pd.DataFrame({"passage_id": ["1_1"], "texto": [TEXTO], "inicio_cuerpo": [IC]})
    err = E.analizar_errores(gold, pred, pas, obras=set())
    cat = set(zip(err["error"], err["categoria"]))
    assert {("FN", "sigla_no_reconocida"), ("FN", "omision"), ("FP", "espuria:regex")} <= cat
    assert E.resumen_errores(err)["n"].sum() == len(err)


def test_alertas_u19():
    det = pd.DataFrame([
        {"metodo": "combinado", "tipo": "TODOS", "f1": 0.25, "soporte": 50},
        {"metodo": "regla", "tipo": "MONTO", "f1": 1.0, "soporte": 6},
        {"metodo": "regla", "tipo": "FECHA", "f1": 1.0, "soporte": 5}])
    a = " ".join(E.alertas_u19(det))
    assert "< 0.30" in a and "MONTO" in a and "FECHA" not in a
