"""Artefactos que carga la demo web y la versión de datos que le toca (PRD v2 D32, WP-15).

- **v1** hasta que existan `anotaciones/cierre_juicios_v2.json` y `anotaciones/cierre_gold_v2.json`:
  Q1 a Q10 con `ranking.csv`, `entidades.csv`, `salida/respuestas.csv` y `data/mejor_modelo.json`.
- **v2** después de ambos cierres (se conecta en cuanto WP-12 y WP-13 dejen sus salidas).
- Mientras no exista `cierre_gold_v2.json`, los pasajes de la muestra del gold v2 se bloquean: la
  consulta libre no los muestra (D32: nadie ve predicciones de esos pasajes antes del cierre).

`MTX_DEMO_RAIZ` cambia la carpeta raíz (en el servidor, donde se descargan los artefactos) y
`MTX_DEMO_VERSION=v1` fuerza v1 aunque existan los cierres.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from mtx import config, consultas

MODELOS = ("tfidf", "bm25")
NOMBRE_MODELO = {"tfidf": "TF-IDF", "bm25": "BM25"}
MUESTRAS_V2 = ("muestra_seleccion.csv", "muestra_gold_a.csv", "muestra_gold_b.csv")
COLUMNAS_PASAJE = ["passage_id", "doc_id", "fecha", "titulo", "url", "posicion", "interlocutor",
                   "es_reportero", "texto", "inicio_cuerpo"]


def raiz() -> Path:
    return Path(os.environ.get("MTX_DEMO_RAIZ") or config.RAIZ)


def cierres_v2(r: Path | None = None) -> dict[str, bool]:
    a = (r or raiz()) / "anotaciones"
    return {"juicios": (a / "cierre_juicios_v2.json").exists(),
            "gold": (a / "cierre_gold_v2.json").exists()}


def version_datos(r: Path | None = None) -> str:
    """"v2" solo con los dos cierres; si no, "v1". `MTX_DEMO_VERSION=v1` fuerza v1."""
    if os.environ.get("MTX_DEMO_VERSION") == "v1":
        return "v1"
    return "v2" if all(cierres_v2(r).values()) else "v1"


def pasajes_bloqueados(r: Path | None = None) -> frozenset[str]:
    """IDs de las muestras del gold v2 mientras no exista `cierre_gold_v2.json`. Solo se leen los
    IDs de la muestra; nunca las anotaciones."""
    r = r or raiz()
    if cierres_v2(r)["gold"]:
        return frozenset()
    ids: set[str] = set()
    for nombre in MUESTRAS_V2:
        ruta = r / "anotaciones" / "v2" / nombre
        if ruta.exists():
            ids |= set(pd.read_csv(ruta, dtype=str, usecols=["passage_id"])["passage_id"])
    return frozenset(ids)


@dataclass
class Artefactos:
    """Todo lo precalculado de las consultas del experimento, ya filtrado a lo que se muestra."""

    version: str
    consultas: pd.DataFrame     # query_id, consulta, desde, hasta, pregunta_extraccion
    ranking: pd.DataFrame       # query_id, modelo (tfidf|bm25), rango, passage_id, puntaje
    mejor: str                  # "bm25" o "tfidf": el ganador por MAP
    entidades: pd.DataFrame     # query_id, passage_id, tipo, texto, inicio, fin, metodo
    respuestas: pd.DataFrame    # salida de respuestas.csv
    evidencias: pd.DataFrame    # salida/10_evidencias.csv (conteos por valor)
    pasajes: pd.DataFrame       # pasajes de `ranking` y sus vecinos, indexados por passage_id
    vecinos: pd.DataFrame       # anterior y siguiente de cada pasaje del mismo discurso

    def consulta(self, query_id: str) -> dict:
        return self.consultas.set_index("query_id").loc[query_id].to_dict()

    def top(self, query_id: str, modelo: str) -> pd.DataFrame:
        r = self.ranking
        return r[(r["query_id"] == query_id) & (r["modelo"] == modelo)].sort_values("rango")

    def entidades_de(self, query_id: str, passage_id: str) -> pd.DataFrame:
        e = self.entidades
        return e[(e["query_id"] == query_id) & (e["passage_id"] == passage_id)]

    def contexto(self, passage_id: str) -> tuple[pd.Series | None, pd.Series | None]:
        return contexto(passage_id, self.vecinos, self.pasajes)


def _modelo_corto(nombre: str) -> str:
    """"bm25_con_filtro" → "bm25"."""
    return nombre.split("_", 1)[0]


def cargar_v1(r: Path | None = None) -> Artefactos:
    r = r or raiz()
    cons = consultas.solo_v1(pd.read_csv(r / "data" / "consultas.csv", dtype=str,
                                         keep_default_na=False))
    rk = pd.read_csv(r / "ranking.csv", dtype={"passage_id": str, "query_id": str})
    rk = rk[rk["variante"] == "con_filtro"].copy()
    rk["modelo"] = rk["modelo"].map(_modelo_corto)
    rk = rk[["query_id", "modelo", "rango", "passage_id", "puntaje"]].reset_index(drop=True)
    mejor = _modelo_corto(json.loads((r / "data" / "mejor_modelo.json").read_text(
        encoding="utf-8"))["modelo"])
    ent = pd.read_csv(r / "entidades.csv", dtype={"passage_id": str}, keep_default_na=False)
    res = pd.read_csv(r / "salida" / "respuestas.csv", dtype=str, keep_default_na=False)
    evi = pd.read_csv(r / "salida" / "10_evidencias.csv", dtype=str, keep_default_na=False)
    ids = set(rk["passage_id"]) | set(ent["passage_id"]) | set(res["passage_id"]) - {""}
    vec = indice_vecinos(r)
    vec = vec[vec.index.isin(ids)]
    ids |= set(vec["anterior"].dropna()) | set(vec["siguiente"].dropna())
    return Artefactos("v1", cons, rk, mejor, ent, res, evi, cargar_pasajes(ids, r), vec)


def cargar_artefactos(r: Path | None = None) -> Artefactos:
    version = version_datos(r)
    if version == "v1":
        return cargar_v1(r)
    raise NotImplementedError("Los artefactos v2 de la demo se conectan después de los cierres "
                              "(WP-12 y WP-13); mientras, `MTX_DEMO_VERSION=v1`.")


def indice_vecinos(r: Path | None = None) -> pd.DataFrame:
    """Para cada pasaje, el `passage_id` anterior y el siguiente del mismo discurso (por
    `posicion`; los fragmentos descartados por cortos no cuentan). Vacío en los extremos."""
    p = pd.read_parquet((r or raiz()) / "data" / "pasajes.parquet",
                        columns=["passage_id", "doc_id", "posicion"])
    p = p.sort_values(["doc_id", "posicion"])
    g = p.groupby("doc_id")["passage_id"]
    return pd.DataFrame({"anterior": g.shift(1), "siguiente": g.shift(-1)}
                        ).set_index(p["passage_id"])


def contexto(passage_id: str, vecinos: pd.DataFrame, pasajes: pd.DataFrame
             ) -> tuple[pd.Series | None, pd.Series | None]:
    """Filas del pasaje anterior y del siguiente, si existen y están cargadas."""
    if passage_id not in vecinos.index:
        return None, None
    v = vecinos.loc[passage_id]
    return tuple(pasajes.loc[x] if isinstance(x, str) and x in pasajes.index else None
                 for x in (v["anterior"], v["siguiente"]))


def cargar_pasajes(ids: set[str] | None = None, r: Path | None = None) -> pd.DataFrame:
    """Pasajes con lo que necesita la vista, indexados por `passage_id`; `ids=None` los trae todos."""
    p = pd.read_parquet((r or raiz()) / "data" / "pasajes.parquet", columns=COLUMNAS_PASAJE)
    if ids is not None:
        p = p[p["passage_id"].isin(ids)]
    return p.set_index("passage_id", drop=False)


def cifras(r: Path | None = None) -> dict:
    """Cifras que la demo cita, leídas de los archivos oficiales (nunca escritas a mano):
    MAP por modelo con filtro, F1 de la extracción combinada y datos del corpus (v1)."""
    r = r or raiz()
    ir = pd.read_csv(r / "resultados_ir.csv", dtype={"query_id": str})
    prom = ir[ir["query_id"].str.startswith("PROMEDIO")].set_index("modelo")
    ie = pd.read_csv(r / "resultados_ie.csv").set_index(["metodo", "tipo"])
    lim = json.loads((r / "salida" / "01_limpieza.json").read_text(encoding="utf-8"))
    return {
        "map": {m: float(prom.at[f"{m}_con_filtro", "AP"]) for m in MODELOS},
        "p10": {m: float(prom.at[f"{m}_con_filtro", "P@10"]) for m in MODELOS},
        "f1": {m: float(ie.at[(m, "TODOS"), "f1"]) for m in ("regla", "modelo", "combinado")},
        "recall": {m: float(ie.at[(m, "TODOS"), "recall"])
                   for m in ("regla", "modelo", "combinado")},
        "discursos": int(lim["discursos"]),
        "pasajes": int(lim["pasajes"]),
        "palabras_por_pasaje": float(lim["palabras_por_pasaje_media"]),
        "pct_reporteros": float(lim["pasajes_de_reporteros_pct"]),
    }


def conteo_ventana(desde, hasta, r: Path | None = None) -> tuple[int, int]:
    """(fragmentos dentro de la ventana de fechas, fragmentos totales)."""
    from mtx import ranking
    f = pd.read_parquet((r or raiz()) / "data" / "pasajes.parquet", columns=["fecha"])
    m = ranking.mascara_fecha(f["fecha"].to_numpy(dtype="datetime64[ns]"), desde, hasta)
    return int(m.sum()), len(m)
