"""Modelo booleano como contraste exploratorio (PRD v2 D30, WP-07, R07).

AND y OR sobre el índice stem con los mismos tokens de cada consulta que usa el ranking
(`preproceso.tokenizar`) y el mismo filtro de fecha (`ranking.mascara_fecha`). No entra al pool ni
compite por el ganador: responde con evidencia por qué no se usó. El booleano devuelve un conjunto
sin orden, no usa el idf ni la tf, y con AND una consulta larga se queda casi vacía.

Funciones puras sobre un `Indice`; el script `scripts/03b_booleano.py` escribe las salidas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mtx import preproceso as P
from mtx import ranking as RK
from mtx.indice import Indice

OPERADORES = ("AND", "OR")
COLUMNAS = ["query_id", "consulta", "operador", "terminos", "n_terminos", "pasajes",
            "en_ventana", "elegibles_ventana"]


def conjunto(ind: Indice, tokens: list[str], operador: str) -> np.ndarray:
    """Índices (posición en `ind.ids`) de los pasajes que cumplen la consulta booleana."""
    if operador not in OPERADORES:
        raise ValueError(f"Operador desconocido: {operador!r}; use {OPERADORES}")
    listas = [set(ind.postings.get(t, {})) for t in dict.fromkeys(tokens)]
    if not listas:
        return np.array([], dtype=int)
    res = set.intersection(*listas) if operador == "AND" else set.union(*listas)
    return np.array(sorted(res), dtype=int)


def por_consulta(ind: Indice, fechas: np.ndarray, consultas: pd.DataFrame) -> pd.DataFrame:
    """Por consulta y operador: pasajes que devuelve en todo el corpus y dentro de su ventana."""
    filas = []
    for q in consultas.itertuples(index=False):
        tokens = list(dict.fromkeys(P.tokenizar(q.consulta)))
        ventana = RK.mascara_fecha(fechas, q.desde, q.hasta)
        for op in OPERADORES:
            sel = conjunto(ind, tokens, op)
            filas.append({"query_id": q.query_id, "consulta": q.consulta, "operador": op,
                          "terminos": " ".join(tokens), "n_terminos": len(tokens),
                          "pasajes": int(sel.size), "en_ventana": int(ventana[sel].sum()),
                          "elegibles_ventana": int(ventana.sum())})
    return pd.DataFrame(filas, columns=COLUMNAS)


def ejemplo(ind: Indice, fechas: np.ndarray, consulta: str, desde, hasta, raro: str,
            comun: str, doc_ids: np.ndarray | None = None, posiciones: np.ndarray | None = None,
            k: int = RK.K) -> dict:
    """Cómo trata el booleano a un término raro y a uno común de la misma consulta, frente a BM25.

    `raro` y `comun` son palabras de la consulta (antes del stemming). Cuenta, dentro de la
    ventana, cuántos pasajes del OR tienen el término raro, cuántos solo el común, y cuántos de los
    `k` primeros de BM25 tienen el raro (mismo desempate que el ranking si se dan `doc_ids` y
    `posiciones`).
    """
    tokens = list(dict.fromkeys(P.tokenizar(consulta)))
    t_raro, t_comun = P.tokenizar(raro)[0], P.tokenizar(comun)[0]
    ventana = RK.mascara_fecha(fechas, desde, hasta)
    o = conjunto(ind, tokens, "OR")
    o = o[ventana[o]]
    con_raro = set(ind.postings.get(t_raro, {}))
    puntajes = RK.BM25(ind).puntajes(tokens)
    n = len(ind.ids)
    top = RK.top_k(puntajes, ventana, np.arange(n) if doc_ids is None else doc_ids,
                   np.zeros(n, dtype=int) if posiciones is None else posiciones, k)
    terminos = [{"palabra": w, "termino": t, "df": ind.df.get(t, 0), "idf": ind.idf_bm25(t)}
                for w in dict.fromkeys(P.tokenizar_sin_stem(consulta))
                for t in P.tokenizar(w)[:1]]
    return {
        "consulta": consulta, "terminos": terminos, "raro": t_raro, "comun": t_comun,
        "and_en_ventana": int(ventana[conjunto(ind, tokens, "AND")].sum()),
        "or_en_ventana": int(o.size),
        "or_con_raro": int(sum(i in con_raro for i in o)),
        "or_sin_raro": int(sum(i not in con_raro for i in o)),
        "bm25_top": int(top.size), "bm25_top_con_raro": int(sum(i in con_raro for i in top)),
    }


def markdown_ejemplo(e: dict, nombre: str) -> str:
    filas = "\n".join(f"| «{t['palabra']}» | `{t['termino']}` | {t['df']:,} | {t['idf']:.2f} |"
                      for t in e["terminos"])
    r, c = e["raro"], e["comun"]
    return "\n".join([
        f"# Booleano contra BM25: «{nombre}»", "",
        (f"Consulta: «{e['consulta']}», con su ventana de fechas. Exploratorio (PRD v2 D30): no "
        "entra al pool ni compite por el ganador."), "",
        "| palabra | término | fragmentos (df) | idf (BM25) |", "| --- | --- | ---: | ---: |",
        filas, "",
        (f"- **AND** (todas las palabras): {e['and_en_ventana']:,} fragmentos en la ventana, sin "
        "orden."),
        (f"- **OR** (cualquier palabra): {e['or_en_ventana']:,} fragmentos en la ventana, sin orden. "
        f"De ellos, {e['or_con_raro']:,} tienen `{r}` y {e['or_sin_raro']:,} no lo tienen: un "
        f"fragmento que solo dice `{c}` entra igual que uno que dice `{r}`, porque el booleano no "
        "usa el idf."),
        (f"- **BM25** devuelve {e['bm25_top']} fragmentos ordenados; {e['bm25_top_con_raro']} de "
        f"ellos tienen `{r}`, porque su idf pesa más."), ""])
