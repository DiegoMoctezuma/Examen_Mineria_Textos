"""Agregación y acuerdo de los juicios v2 (PRD v2 D24, WP-02).

- **Mayoría:** un par es relevante con al menos 2 votos de 3 juicios válidos. Un omitido (vacío) no
  cuenta como 0: un par con menos de 3 juicios válidos no se cierra y no entra a
  `juicios_relevancia.csv`.
- **Acuerdo:** kappa de Fleiss (global, por lote y por consulta) sobre los pares con 3 juicios
  válidos, acuerdo observado y kappa de Cohen por pareja de jueces sobre los pares que comparten.
  Es información para el reporte, nunca un criterio para descartar a un juez.

Solo lee los archivos humanos y cuenta; ningún valor de juicio se produce, sugiere ni modifica.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import pandas as pd

from mtx import anotadores as A
from mtx import pool

JUECES_POR_PAR = 3
MINIMO_RELEVANTE = 2
VALORES = ("0", "1")
CLAVE = ["query_id", "passage_id"]
COLUMNAS_LARGO = ["lote", "query_id", "doc_id", "passage_id", "anotador", "relevante"]
COLUMNAS_AGREGADOS = ["lote", "orden", "query_id", "doc_id", "passage_id", "jueces", "validos",
                      "votos_relevante", "relevante", "unanime", "cerrado"]
COLUMNAS_ACUERDO = ["ambito", "clave", "metrica", "jueces", "pares", "acuerdo_observado",
                    "acuerdo_esperado", "kappa"]


def largo(asignacion: pd.DataFrame, dir_anot: Path) -> pd.DataFrame:
    """Un renglón por (par asignado, juez) con su valor: `0`, `1` o vacío (omitido o ausente).
    Los juicios que no corresponden a la asignación del juez se ignoran (los marca el cierre)."""
    filas = []
    for a in sorted(set(asignacion["anotador"])):
        asig = asignacion[asignacion["anotador"] == a]
        ruta = A.ruta_juicios(dir_anot, a)
        hechos = {}
        if ruta.exists():
            j = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            hechos = dict(zip(zip(j["query_id"], j["passage_id"]), j["relevante"]))
        for r in asig.itertuples(index=False):
            v = hechos.get((r.query_id, r.passage_id), "")
            filas.append({"lote": r.lote, "query_id": r.query_id, "doc_id": r.doc_id,
                          "passage_id": r.passage_id, "anotador": a,
                          "relevante": v if v in VALORES else ""})
    return pd.DataFrame(filas, columns=COLUMNAS_LARGO)


def agregar(asignacion: pd.DataFrame, lar: pd.DataFrame) -> pd.DataFrame:
    """Un renglón por par en el orden de la asignación (lote y posición). `relevante` es `1`/`0`
    si el par está cerrado (3 juicios válidos) y vacío si no."""
    orden = (asignacion.assign(_l=asignacion["lote"].astype(int),
                               _o=asignacion["orden"].astype(int))
             .sort_values(["_l", "_o"], kind="stable")
             .drop_duplicates(CLAVE)[["lote", "orden", "query_id", "doc_id", "passage_id"]])
    val = lar[lar["relevante"].isin(VALORES)]
    cuenta = (val.assign(_r=(val["relevante"] == "1").astype(int)).groupby(CLAVE)
              .agg(validos=("_r", "size"), votos_relevante=("_r", "sum")).reset_index())
    jueces = (lar.groupby(CLAVE)["anotador"].apply(lambda s: ",".join(sorted(s)))
              .rename("jueces").reset_index())
    out = orden.merge(jueces, on=CLAVE, how="left").merge(cuenta, on=CLAVE, how="left")
    out[["validos", "votos_relevante"]] = out[["validos", "votos_relevante"]].fillna(0).astype(int)
    out["cerrado"] = out["validos"] >= JUECES_POR_PAR
    out["relevante"] = [("1" if v >= MINIMO_RELEVANTE else "0") if c else ""
                        for v, c in zip(out["votos_relevante"], out["cerrado"])]
    out["unanime"] = out["cerrado"] & ((out["votos_relevante"] == 0)
                                       | (out["votos_relevante"] == out["validos"]))
    return out[COLUMNAS_AGREGADOS].reset_index(drop=True)


def exportar_kit(agregados: pd.DataFrame) -> pd.DataFrame:
    """`juicios_relevancia.csv` del kit: las 4 columnas de v1, solo pares cerrados."""
    c = agregados[agregados["cerrado"]]
    return c[pool.COLUMNAS_JUICIOS].reset_index(drop=True)


# --------------------------------------------------------------------------- acuerdo


def fleiss(votos: pd.Series, n: int = JUECES_POR_PAR) -> dict:
    """Kappa de Fleiss binario con `n` jueces por par; `votos` = votos «relevante» de cada par
    (todos con exactamente `n` juicios válidos)."""
    v = pd.Series(votos, dtype=float)
    N = len(v)
    if N == 0:
        return {"pares": 0, "acuerdo_observado": float("nan"),
                "acuerdo_esperado": float("nan"), "kappa": float("nan")}
    p_i = (v ** 2 + (n - v) ** 2 - n) / (n * (n - 1))
    po = float(p_i.mean())
    p1 = float(v.sum() / (N * n))
    pe = p1 ** 2 + (1 - p1) ** 2
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return {"pares": N, "acuerdo_observado": round(po, 4), "acuerdo_esperado": round(pe, 4),
            "kappa": round(kappa, 4)}


def cohen(a: pd.Series, b: pd.Series) -> dict:
    """Kappa de Cohen binario entre dos jueces sobre los mismos pares (valores `0`/`1`)."""
    a, b = pd.Series(a).astype(int).to_numpy(), pd.Series(b).astype(int).to_numpy()
    N = len(a)
    if N == 0:
        return {"pares": 0, "acuerdo_observado": float("nan"),
                "acuerdo_esperado": float("nan"), "kappa": float("nan")}
    po = float((a == b).mean())
    pa, pb = float(a.mean()), float(b.mean())
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return {"pares": N, "acuerdo_observado": round(po, 4), "acuerdo_esperado": round(pe, 4),
            "kappa": round(kappa, 4)}


def acuerdo(agregados: pd.DataFrame, lar: pd.DataFrame) -> pd.DataFrame:
    """Fleiss global, por lote y por consulta (pares cerrados) y Cohen por pareja de jueces."""
    c = agregados[agregados["cerrado"]]
    filas = []

    def fila(ambito, clave, metrica, jueces, d):
        filas.append({"ambito": ambito, "clave": clave, "metrica": metrica, "jueces": jueces, **d})

    fila("global", "todos", "fleiss", "", fleiss(c["votos_relevante"]))
    for lote, g in c.groupby("lote", sort=False):
        fila("lote", str(lote), "fleiss", g["jueces"].iloc[0], fleiss(g["votos_relevante"]))
    for q in sorted(c["query_id"].unique(), key=lambda q: int(q[1:])):
        fila("consulta", q, "fleiss", "", fleiss(c[c["query_id"] == q]["votos_relevante"]))
    val = lar[lar["relevante"].isin(VALORES)]
    ancho = val.pivot_table(index=CLAVE, columns="anotador", values="relevante",
                            aggfunc="first")
    for x, y in itertools.combinations(sorted(ancho.columns), 2):
        par = ancho[[x, y]].dropna()
        if len(par):
            fila("pareja", f"{x}-{y}", "cohen", f"{x},{y}", cohen(par[x], par[y]))
    return pd.DataFrame(filas, columns=COLUMNAS_ACUERDO)


# --------------------------------------------------------------------------- cierre


def verificar_cierre(cierre: dict | None, ruta_asignacion: Path, dir_anot: Path) -> list[str]:
    """La agregación solo corre sobre lo cerrado: existe `cierre_juicios_v2.json` y la asignación
    y el archivo de cada juez son byte a byte los que registró."""
    from mtx.app import componentes as C

    if cierre is None:
        return ["No existe anotaciones/cierre_juicios_v2.json: primero `make cierre-juicios-v2`"]
    errores = []
    if C.sha256_ruta(ruta_asignacion) != cierre.get("sha256_asignacion"):
        errores.append("data/v2/asignacion_juicios.csv cambió después del cierre")
    for a, d in (cierre.get("jueces") or {}).items():
        ruta = A.ruta_juicios(dir_anot, a)
        if not ruta.exists():
            errores.append(f"{a}: falta {ruta.name}, registrado en el cierre")
        elif C.sha256_ruta(ruta) != d.get("sha256"):
            errores.append(f"{a}: {ruta.name} cambió después del cierre")
    return errores


def pool_de(asignacion: pd.DataFrame, agregados: pd.DataFrame) -> pd.DataFrame:
    """Pool contra el que se valida la exportación: los pares cerrados con su huella de texto."""
    p = asignacion.drop_duplicates(CLAVE)[["query_id", "doc_id", "passage_id", "texto_sha256"]]
    cerr = agregados[agregados["cerrado"]][CLAVE]
    return cerr.merge(p, on=CLAVE)[["query_id", "doc_id", "passage_id", "texto_sha256"]]
