"""Frase representativa de un fragmento (resumen extractivo) para el contexto de la demo web.

Se elige la oración del cuerpo cuyo vector TF-IDF más se parece al del fragmento completo (similitud
coseno, con el mismo preprocesamiento y los mismos IDF que el índice). Es una cita textual: no se
redacta nada. Las oraciones de menos de `MIN_PALABRAS` no cuentan y la elegida se recorta a
`MAX_PALABRAS` con "…".
"""
from __future__ import annotations

import math
import pickle
from collections import Counter
from functools import lru_cache

from mtx import preproceso
from mtx.respuestas import oraciones

MIN_PALABRAS = 8
MAX_PALABRAS = 30


@lru_cache(maxsize=1)
def idf_indice() -> dict[str, float]:
    """IDF del vectorizador TF-IDF guardado (`data/tfidf.pkl`)."""
    from mtx.web import datos
    with open(datos.raiz() / "data" / "tfidf.pkl", "rb") as f:
        vec = pickle.load(f)
    return dict(zip(vec.get_feature_names_out(), vec.idf_))


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """tf sublineal × idf, como el vectorizador del índice (sin normalizar)."""
    return {t: (1 + math.log(n)) * idf[t] for t, n in Counter(tokens).items() if t in idf}


def _coseno(a: dict[str, float], b: dict[str, float]) -> float:
    num = sum(v * b.get(k, 0.0) for k, v in a.items())
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def recortar_palabras(oracion: str, maximo: int = MAX_PALABRAS) -> str:
    palabras = oracion.split()
    if len(palabras) <= maximo:
        return " ".join(palabras)
    return " ".join(palabras[:maximo]).rstrip(" ,;:") + "…"


def frase_representativa(texto: str, inicio_cuerpo: int,
                         idf: dict[str, float] | None = None) -> str:
    """La oración más parecida al fragmento completo, recortada. Si ninguna tiene al menos
    `MIN_PALABRAS` palabras, el inicio del fragmento."""
    idf = idf_indice() if idf is None else idf
    cuerpo = _vector(preproceso.tokenizar(texto[inicio_cuerpo:], "stem"), idf)
    mejor: tuple[float, str] | None = None
    for a, b in oraciones(texto, inicio_cuerpo):
        if a < inicio_cuerpo:
            continue
        oracion = " ".join(texto[a:b].split())
        if len(oracion.split()) < MIN_PALABRAS:
            continue
        s = _coseno(_vector(preproceso.tokenizar(oracion, "stem"), idf), cuerpo)
        if mejor is None or s > mejor[0]:
            mejor = (s, oracion)
    if mejor is None:
        return recortar_palabras(" ".join(texto[inicio_cuerpo:].split()))
    return recortar_palabras(mejor[1])
