"""Extracción y evaluación IE v2 (PRD v2 D31, D33, D34, D35; WP-12).

- **Gold oficial v2:** los 20 pasajes del gold v1 (sin reanotar, recorte 3) más el gold
  adjudicado de las partes A y B (las dos pasadas). La selección no entra: solo elige el NER.
- **Ámbito:** top-10 del ganador IR v2 (`data/v2/mejor_modelo.json` sobre `salida/v2/ranking.csv`)
  para las 15 consultas, unido a los pasajes del gold v2 con su consulta. Antes de
  `cierre_gold_v2.json` nada de esto corre (D32).
- **Referencias del F1 (D35):** techo humano (acuerdo entre anotadores antes de adjudicar), línea
  base de solo gazetteer, intervalo bootstrap sobre pasajes y F1 con coincidencia parcial
  (solape de al menos un carácter y mismo tipo), además de FECHA con las reglas v1 como
  comparación de las reglas v2.

Este módulo lee el gold para medir; nunca lo escribe ni lo modifica.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from mtx import config
from mtx import evaluacion_ie as E
from mtx import gold_v2 as V

PARTES_EVALUADAS = ("a", "b")
COLUMNAS_GOLD_KIT = ["passage_id", "tipo", "texto", "inicio", "fin"]
COLUMNAS_REFERENCIAS = ["referencia", "metodo", "tipo", "precision", "recall", "f1", "ic95_inf",
                        "ic95_sup", "pasajes", "nota"]


# --------------------------------------------------------------------------- gold y ámbito


def gold_v2(cfg_gold: V.ConfigGold, gold_v1: Path, dir_anot: Path | None = None) -> pd.DataFrame:
    """Gold oficial v2 en el formato del kit: gold v1 + gold adjudicado de A y B."""
    g1 = pd.read_csv(gold_v1, dtype={"passage_id": str}, keep_default_na=False)
    g2 = V.gold_oficial(cfg_gold, dir_anot)
    g2 = g2[g2["parte"].isin(PARTES_EVALUADAS)]
    g = pd.concat([g1[COLUMNAS_GOLD_KIT], g2[COLUMNAS_GOLD_KIT]], ignore_index=True)
    g["inicio"], g["fin"] = g["inicio"].astype(int), g["fin"].astype(int)
    if g.duplicated(["passage_id", "tipo", "inicio", "fin"]).any():
        raise ValueError("El gold v2 repite entidades: v1 y v2 no deberían compartir pasajes")
    return g.sort_values(["passage_id", "inicio", "fin", "tipo"]).reset_index(drop=True)


def pasajes_gold_v2(cfg_gold: V.ConfigGold, muestra_v1: Path) -> pd.DataFrame:
    """`query_id, passage_id, doc_id, origen` de los pasajes del gold v2 (20 v1 + A + B)."""
    partes = [pd.read_csv(muestra_v1, dtype=str).assign(origen="v1")]
    for pid in PARTES_EVALUADAS:
        m = V.manifiesto(cfg_gold.partes[pid])
        partes.append(m.assign(origen=f"v2_{pid}"))
    out = pd.concat([p[["query_id", "passage_id", "doc_id", "origen"]] for p in partes],
                    ignore_index=True)
    if out["passage_id"].duplicated().any():
        raise ValueError("Un pasaje aparece en dos partes del gold")
    return out


def ambito_ie_v2(ranking_v2: Path, mejor_v2: Path, gold_pas: pd.DataFrame) -> pd.DataFrame:
    """`query_id, passage_id, doc_id, rango, origen`: top-10 del ganador v2 ∪ pasajes del gold."""
    nombre = json.loads(Path(mejor_v2).read_text("utf-8"))["modelo_en_ranking_csv"]
    rk = pd.read_csv(ranking_v2, dtype=str, keep_default_na=False)
    top = rk[rk["modelo"] == nombre][["query_id", "passage_id", "doc_id", "rango"]]
    if top.empty:
        raise ValueError(f"salida/v2/ranking.csv no tiene filas de {nombre}")
    top = top.assign(origen="top10")
    gold = gold_pas.assign(rango="")[["query_id", "passage_id", "doc_id", "rango", "origen"]]
    nuevos = gold.merge(top[["query_id", "passage_id"]], on=["query_id", "passage_id"],
                        how="left", indicator=True)
    gold = nuevos[nuevos["_merge"] == "left_only"].drop(columns="_merge")
    out = pd.concat([top, gold], ignore_index=True)
    q = out["query_id"].str[1:].astype(int)
    return (out.assign(_q=q).sort_values(["_q", "origen", "passage_id"], kind="stable")
            .drop(columns="_q").reset_index(drop=True))


# --------------------------------------------------------------------------- referencias (D35)


def _por_pasaje(gold: pd.DataFrame, pred: pd.DataFrame, pasajes: list[str]) -> pd.DataFrame:
    """TP, predichas y gold exactos por pasaje (para el bootstrap)."""
    g = set(zip(gold["passage_id"], gold["tipo"], gold["inicio"].astype(int),
                gold["fin"].astype(int)))
    p = set(zip(pred["passage_id"], pred["tipo"], pred["inicio"].astype(int),
                pred["fin"].astype(int)))
    filas = []
    for pid in pasajes:
        gp = {x for x in g if x[0] == pid}
        pp = {x for x in p if x[0] == pid}
        filas.append({"passage_id": pid, "tp": len(gp & pp), "npred": len(pp), "ngold": len(gp)})
    return pd.DataFrame(filas)


def _f1(tp, npred, ngold) -> float:
    p = tp / npred if npred else 0.0
    r = tp / ngold if ngold else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


def bootstrap_f1(gold: pd.DataFrame, pred: pd.DataFrame, pasajes: list[str], n: int = 10_000,
                 semilla: int = 42) -> tuple[float, float]:
    """IC95 del F1 micro remuestreando pasajes con reemplazo (cada copia cuenta aparte)."""
    t = _por_pasaje(gold, pred, pasajes)[["tp", "npred", "ngold"]].to_numpy(dtype=float)
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(t), size=(n, len(t)))
    s = t[idx].sum(axis=1)
    p = np.divide(s[:, 0], s[:, 1], out=np.zeros(n), where=s[:, 1] > 0)
    r = np.divide(s[:, 0], s[:, 2], out=np.zeros(n), where=s[:, 2] > 0)
    f = np.divide(2 * p * r, p + r, out=np.zeros(n), where=(p + r) > 0)
    return float(np.percentile(f, 2.5)), float(np.percentile(f, 97.5))


def f1_parcial(gold: pd.DataFrame, pred: pd.DataFrame) -> tuple[float, float, float]:
    """Complementaria: una predicción acierta si solapa al menos un carácter con un gold del mismo
    tipo en el mismo pasaje; un gold se recupera si alguna predicción lo solapa."""
    def solapa(a, b) -> bool:
        return a[0] == b[0] and a[1] == b[1] and a[2] < b[3] and b[2] < a[3]

    g = list(zip(gold["passage_id"], gold["tipo"], gold["inicio"].astype(int),
                 gold["fin"].astype(int)))
    p = list(zip(pred["passage_id"], pred["tipo"], pred["inicio"].astype(int),
                 pred["fin"].astype(int)))
    por_pid: dict[str, list] = {}
    for x in g:
        por_pid.setdefault(x[0], []).append(x)
    pred_ok = sum(any(solapa(x, y) for y in por_pid.get(x[0], [])) for x in p)
    por_pid_p: dict[str, list] = {}
    for x in p:
        por_pid_p.setdefault(x[0], []).append(x)
    gold_ok = sum(any(solapa(x, y) for y in por_pid_p.get(x[0], [])) for x in g)
    prec = pred_ok / len(p) if p else 0.0
    rec = gold_ok / len(g) if g else 0.0
    return prec, rec, (2 * prec * rec / (prec + rec) if prec + rec else 0.0)


def techo_humano(acuerdo: pd.DataFrame) -> pd.DataFrame:
    """F1 entre los dos anotadores antes de adjudicar, sumando las partes A y B, por tipo y en
    total (`salida/v2/09_acuerdo_gold.csv`)."""
    a = acuerdo[acuerdo["parte"].isin(PARTES_EVALUADAS) & (acuerdo["tipo"] != "micro")]
    filas = []
    for tipo, g in [*a.groupby("tipo"), ("TODOS", a)]:
        c, n1, n2 = (g["coincidencias"].sum(), g["n_anotador_1"].sum(), g["n_anotador_2"].sum())
        filas.append({"tipo": tipo, "f1": 2 * c / (n1 + n2) if n1 + n2 else float("nan"),
                      "pasajes": int(g.drop_duplicates(["parte"])["pasajes"].sum())})
    return pd.DataFrame(filas)


def referencias(gold: pd.DataFrame, pred: pd.DataFrame, linea_base: pd.DataFrame,
                fecha_v1: pd.DataFrame, acuerdo: pd.DataFrame | None, n: int = 10_000,
                semilla: int = 42) -> pd.DataFrame:
    """`salida/v2/09_referencias_f1.csv`. `pred` es `entidades.csv` (8 columnas, con `metodo`);
    `linea_base` y `fecha_v1`, predicciones con `passage_id, tipo, inicio, fin`. Todo sobre los
    pasajes con filas en el gold, como el kit."""
    pasajes = sorted(set(gold["passage_id"]))
    pred = pred[pred["passage_id"].isin(pasajes)]
    filas = []

    def fila(ref, metodo, tipo, p, r, f, inf=None, sup=None, nota=""):
        filas.append({"referencia": ref, "metodo": metodo, "tipo": tipo, "precision": round(p, 4),
                      "recall": round(r, 4), "f1": round(f, 4),
                      "ic95_inf": None if inf is None else round(inf, 4),
                      "ic95_sup": None if sup is None else round(sup, 4),
                      "pasajes": len(pasajes), "nota": nota})

    det = E.detalle(gold, pred, set(pasajes))
    for metodo in E.METODOS:
        sub = pred[pred["metodo"].isin(E.USA[metodo])]
        d = det[(det["metodo"] == metodo) & (det["tipo"] == "TODOS")].iloc[0]
        lo, hi = bootstrap_f1(gold, sub, pasajes, n, semilla)
        fila("sistema_exacto", metodo, "TODOS", d["precision"], d["recall"], d["f1"], lo, hi,
             f"cifra del kit; IC95 bootstrap sobre {len(pasajes)} pasajes, {n} remuestreos, "
             f"semilla {semilla}")
        fila("sistema_parcial", metodo, "TODOS", *f1_parcial(gold, sub),
             nota="complementaria: solape de al menos un carácter y mismo tipo")
    lb = linea_base[linea_base["passage_id"].isin(pasajes)].assign(metodo="regla")
    d = E.detalle(gold, lb, set(pasajes))
    for tipo in ("ORG", "LOC", "TODOS"):
        x = d[(d["metodo"] == "regla") & (d["tipo"] == tipo)].iloc[0]
        fila("linea_base_gazetteer", "regla", tipo, x["precision"], x["recall"], x["f1"],
             nota="solo gazetteer ORG y LOC, sin regex ni modelo (D35)")
    gf = gold[gold["tipo"] == "FECHA"]
    for nombre, fpred in (("fecha_reglas_v1", fecha_v1),
                          ("fecha_reglas_v2", pred[(pred["tipo"] == "FECHA")
                                                   & pred["metodo"].isin(E.USA["regla"])])):
        fp = fpred[fpred["passage_id"].isin(pasajes) & (fpred["tipo"] == "FECHA")]
        c = _por_pasaje(gf, fp, pasajes)[["tp", "npred", "ngold"]].sum()
        p = c["tp"] / c["npred"] if c["npred"] else 0.0
        r = c["tp"] / c["ngold"] if c["ngold"] else 0.0
        fila(nombre, "regla", "FECHA", p, r, _f1(c["tp"], c["npred"], c["ngold"]),
             nota="exploratoria (recorte 3 de D33): gold FECHA con criterio v1")
    if acuerdo is not None and len(acuerdo):
        for r in techo_humano(acuerdo).itertuples():
            filas.append({"referencia": "techo_humano", "metodo": "", "tipo": r.tipo,
                          "precision": None, "recall": None, "f1": round(r.f1, 4),
                          "ic95_inf": None, "ic95_sup": None, "pasajes": r.pasajes,
                          "nota": "F1 exacto entre los dos anotadores antes de adjudicar, "
                                  "partes A y B"})
    return pd.DataFrame(filas, columns=COLUMNAS_REFERENCIAS)


def rutas_v2() -> dict[str, Path]:
    s, d = config.DIR_SALIDA_V2, config.DIR_DATA_V2
    return {"ranking": s / "ranking.csv", "mejor": d / "mejor_modelo.json",
            "entidades": s / "entidades.csv", "unicas": s / "entidades_unicas.csv",
            "enriquecidas": s / "entidades_enriquecidas.csv",
            "solapes": s / "08_solapes_parciales.csv", "resumen": s / "08_resumen_extraccion.json",
            "ambito": s / "08_ambito_ie.csv", "gold": s / "gold_entidades.csv",
            "resultados": s / "resultados_ie.csv", "detalle": s / "09_ie_detalle.csv",
            "referencias": s / "09_referencias_f1.csv", "errores": s / "09_analisis_errores.csv",
            "resumen_errores": s / "09_resumen_errores.csv", "acuerdo": s / "09_acuerdo_gold.csv",
            "muestra_v1": config.DIR_ANOTACIONES / "muestra_gold.csv",
            "gold_v1": config.DIR_ANOTACIONES / "gold_entidades.csv"}
