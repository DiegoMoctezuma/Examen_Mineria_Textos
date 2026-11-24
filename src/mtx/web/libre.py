"""Consulta libre de la demo web: búsqueda con los dos modelos y entidades en caliente.

Sin Streamlit, para probarlo con pytest. La vista (`vistas.libre`) solo cachea y dibuja.

- Recupera con el índice guardado (`ranking.Buscador`), con filtro de fechas opcional.
- Quita los pasajes bloqueados por D32 (muestra del gold v2 antes de su cierre) y rellena con los
  siguientes, para que siempre haya hasta 10.
- Extrae entidades de los 10 de BM25 con las reglas (las de v1, o FECHA v2 con datos v2) y el NER,
  y las une por span exacto como en `13_demo.py`. No se les atribuye MAP ni F1: la consulta está
  fuera del experimento.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

from mtx import ranking
from mtx import reglas as R

COLUMNAS_ENT = ["passage_id", "tipo", "texto", "inicio", "fin", "metodo"]
AVISOS = {
    "sin_terminos": "La búsqueda no tiene palabras con contenido (solo palabras vacías como «de» "
                    "o «la»). Prueba con otras palabras.",
    "nada": "Ninguna de las palabras buscadas aparece en las conferencias del periodo elegido.",
    "pocos": "Solo {n} fragmentos del periodo contienen alguna de las palabras buscadas.",
}


@dataclass
class Resultado:
    texto: str
    tokens: list[str]
    tops: dict[str, pd.DataFrame]           # modelo → rango, passage_id, puntaje
    elegibles: int
    avisos: list[str] = field(default_factory=list)
    ocultos: int = 0                        # pasajes bloqueados por D32 que se saltaron
    segundos: float = 0.0


def buscar(buscador: ranking.Buscador, texto: str, desde=None, hasta=None,
           bloqueados: frozenset[str] = frozenset(), k: int = ranking.K) -> Resultado:
    t0 = time.perf_counter()
    tops, estado, ocultos = {}, {}, 0
    for modelo in ("tfidf", "bm25"):
        tabla, estado = buscador.buscar(texto, desde, hasta, modelo, k + len(bloqueados))
        fuera = tabla["passage_id"].isin(bloqueados).to_numpy()
        # bloqueados que habrían quedado entre los k mostrados
        visibles = (~fuera).cumsum()
        ocultos = max(ocultos, int((fuera & (visibles < k)).sum()))
        # sin palabras en común (puntaje 0) el orden es arbitrario: no se muestran
        tabla = tabla[~fuera & (tabla["puntaje"] > 0).to_numpy()].head(k).reset_index(drop=True)
        tabla["rango"] = range(1, len(tabla) + 1)
        tops[modelo] = tabla[["rango", "passage_id", "puntaje", "sin_senal_lexica"]]
    avisos = []
    if not estado["tokens"]:
        avisos.append(AVISOS["sin_terminos"])
    elif tops["bm25"].empty:
        avisos.append(AVISOS["nada"])
    elif len(tops["bm25"]) < k:
        avisos.append(AVISOS["pocos"].format(n=len(tops["bm25"])))
    return Resultado(texto, list(estado["tokens"]), tops, int(estado["elegibles"]), avisos,
                     ocultos, round(time.perf_counter() - t0, 2))


def extractor_reglas(version: str):
    """Reglas de la versión de datos: FECHA v2 solo con datos v2 (D33)."""
    if version == "v2":
        from mtx import fecha_v2
        return fecha_v2.extraer_reglas_v2
    return R.extraer_reglas


def entidades_pasaje(passage_id: str, texto: str, inicio_cuerpo: int, reglas_fn,
                     modelo_fn=None) -> pd.DataFrame:
    """Reglas ∪ modelo por span exacto (tipo, inicio, fin); `metodo` dice de dónde salió.
    `modelo_fn(texto, passage_id)` devuelve dicts con tipo, inicio y fin; sin él, solo reglas."""
    reg = {(e.tipo, e.inicio, e.fin) for e in reglas_fn(texto, inicio_cuerpo)}
    mod = set()
    if modelo_fn is not None:
        mod = {(e["tipo"], int(e["inicio"]), int(e["fin"])) for e in modelo_fn(texto, passage_id)}
    filas = []
    for tipo, ini, fin in sorted(reg | mod, key=lambda x: (x[1], x[2], x[0])):
        metodo = "ambos" if (tipo, ini, fin) in reg and (tipo, ini, fin) in mod else (
            "regla" if (tipo, ini, fin) in reg else "modelo")
        filas.append({"passage_id": passage_id, "tipo": tipo, "texto": texto[ini:fin],
                      "inicio": ini, "fin": fin, "metodo": metodo})
    return pd.DataFrame(filas, columns=COLUMNAS_ENT)


def modelo_ner(slug: str | None = None):
    """Carga un NER de `config/ner.yaml` con su revisión fija (por omisión, el principal; con
    datos v2, el ganador de `data/modelo_ner.json`, que puede ser de spaCy) y devuelve una función
    `(texto, passage_id) → entidades posprocesadas`."""
    from mtx import ner_modelo as N
    principal, cfgs = N.cargar_config()
    cfg = cfgs[slug or principal]
    pipe, tok = N.construir_pipeline(cfg)

    def inferir(texto: str, passage_id: str) -> list[dict]:
        crudas = N.inferir_pasaje(texto, pipe, tok, cfg)
        return N.posprocesar(texto, crudas, cfg, passage_id).entidades

    return inferir
