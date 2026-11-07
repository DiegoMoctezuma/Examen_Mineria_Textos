"""Ranking TF-IDF (coseno) y BM25 propio con filtro de fecha (PRD §6.4, U9, U10).

- TF-IDF: `TfidfVectorizer(analyzer=identidad, sublinear_tf=True, smooth_idf=True, min_df=1,
  norm="l2")`; `w = (1 + ln tf) * (ln((1+N)/(1+df)) + 1)`, normalizado L2.
- BM25: `idf = ln(1 + (N-df+0.5)/(df+0.5))`;
  `score = sum_t idf(t) * tf*(k1+1) / (tf + k1*(1 - b + b*dl/avgdl))` sobre términos únicos.
- Filtro: días inclusivos; primero se eligen los pasajes elegibles y después se ordena.
- Orden: `(-puntaje, doc_id, posicion)` con enteros; nunca por `passage_id` como cadena.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from . import preproceso
from .indice import Indice, identidad

MODELOS = ("tfidf", "bm25")
K = 10


# --------------------------------------------------------------------------- modelos


class BM25:
    """BM25 sobre el índice invertido (variante con idf positivo)."""

    def __init__(self, indice: Indice, k1: float = 1.5, b: float = 0.75):
        self.indice, self.k1, self.b = indice, k1, b
        self._norma = k1 * (1 - b + b * indice.longitud / indice.avgdl) if indice.avgdl else None
        self._arreglos: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    def _postings(self, termino: str) -> tuple[np.ndarray, np.ndarray]:
        if termino not in self._arreglos:
            fila = self.indice.postings[termino]
            self._arreglos[termino] = (np.fromiter(fila.keys(), dtype=np.int64, count=len(fila)),
                                       np.fromiter(fila.values(), dtype=np.float64, count=len(fila)))
        return self._arreglos[termino]

    def puntajes(self, tokens_consulta: list[str]) -> np.ndarray:
        """Puntaje de cada pasaje. Términos repetidos cuentan una vez; los ausentes aportan cero."""
        out = np.zeros(self.indice.N, dtype=np.float64)
        for termino in dict.fromkeys(tokens_consulta):
            if termino not in self.indice.postings:
                continue
            idx, tf = self._postings(termino)
            out[idx] += self.indice.idf_bm25(termino) * tf * (self.k1 + 1) / (
                tf + self._norma[idx])
        return out


def ajustar_tfidf(lista_tokens):
    """Ajusta el vectorizador sobre los tokens del cuerpo; devuelve `(vectorizador, matriz X)`."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(analyzer=identidad, sublinear_tf=True, smooth_idf=True, min_df=1,
                          norm="l2")
    return vec, vec.fit_transform(lista_tokens)


class Tfidf:
    """Similitud coseno entre el vector de la consulta y cada pasaje."""

    def __init__(self, vectorizador, matriz: sp.csr_matrix):
        self.vec, self.X = vectorizador, matriz.tocsr()

    def puntajes(self, tokens_consulta: list[str]) -> np.ndarray:
        q = self.vec.transform([tokens_consulta])  # L2; un vector nulo se queda en ceros
        return np.asarray((self.X @ q.T).todense()).ravel().astype(np.float64)


def guardar_tfidf(vec, X, ruta_pkl: Path, ruta_npz: Path) -> None:
    with open(ruta_pkl, "wb") as f:
        pickle.dump(vec, f, protocol=5)
    sp.save_npz(ruta_npz, X.tocsr())


def cargar_tfidf(ruta_pkl: Path, ruta_npz: Path) -> Tfidf:
    with open(ruta_pkl, "rb") as f:
        vec = pickle.load(f)
    return Tfidf(vec, sp.load_npz(ruta_npz))


# --------------------------------------------------------------------------- filtro y top-k


def validar_ventana(desde, hasta) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Normaliza la ventana. Lanza `ValueError` si un límite es inválido o `desde > hasta`."""
    def conv(x, nombre):
        if x is None or (isinstance(x, str) and not x.strip()) or (not isinstance(x, str)
                                                                    and pd.isna(x)):
            return None
        try:
            return pd.Timestamp(x).normalize()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Límite '{nombre}' inválido: {x!r}") from e
    d, h = conv(desde, "desde"), conv(hasta, "hasta")
    if d is not None and h is not None and d > h:
        raise ValueError(f"Ventana invertida: desde ({d.date()}) es posterior a hasta ({h.date()})")
    return d, h


def mascara_fecha(fechas: np.ndarray, desde, hasta) -> np.ndarray:
    """Elegibles: `desde <= fecha <= hasta` (inclusivo). Sin límites: todos. NaT: fuera si hay
    algún límite."""
    d, h = validar_ventana(desde, hasta)
    # Se compara por día: una fecha con hora dentro del último día sigue siendo elegible.
    f = np.asarray(fechas, dtype="datetime64[ns]").astype("datetime64[D]")
    if d is None and h is None:
        return np.ones(len(f), dtype=bool)
    ok = ~np.isnat(f)
    if d is not None:
        ok &= f >= np.datetime64(d.date(), "D")
    if h is not None:
        ok &= f <= np.datetime64(h.date(), "D")
    return ok


def top_k(puntajes: np.ndarray, elegibles: np.ndarray, doc_ids: np.ndarray,
          posiciones: np.ndarray, k: int = K) -> np.ndarray:
    """Índices de los `min(k, n_elegibles)` mejores, ordenados por `(-puntaje, doc_id, posicion)`.

    Nunca rellena con pasajes excluidos ni con ceros inventados (U10).
    """
    cand = np.flatnonzero(elegibles)
    if cand.size == 0:
        return cand
    orden = np.lexsort((posiciones[cand], doc_ids[cand], -puntajes[cand]))
    return cand[orden[:k]]


# --------------------------------------------------------------------------- buscador


class Buscador:
    """Une los dos modelos con los metadatos de los pasajes. `pasajes` conserva el orden de
    `indice.ids`."""

    def __init__(self, indice: Indice, tfidf: Tfidf, pasajes: pd.DataFrame,
                 k1: float = 1.5, b: float = 0.75):
        if list(pasajes["passage_id"]) != indice.ids:
            raise ValueError("Los pasajes no coinciden con el orden del índice")
        self.pasajes = pasajes.reset_index(drop=True)
        self.bm25, self.tfidf = BM25(indice, k1, b), tfidf
        self.doc_id = self.pasajes["doc_id"].to_numpy(dtype=np.int64)
        self.posicion = self.pasajes["posicion"].to_numpy(dtype=np.int64)
        self.fecha = self.pasajes["fecha"].to_numpy(dtype="datetime64[ns]")

    def puntajes(self, modelo: str, tokens: list[str]) -> np.ndarray:
        if modelo == "bm25":
            return self.bm25.puntajes(tokens)
        if modelo == "tfidf":
            return self.tfidf.puntajes(tokens)
        raise ValueError(f"Modelo desconocido: {modelo!r}; use {MODELOS}")

    def buscar(self, consulta: str, desde=None, hasta=None, modelo: str = "bm25",
               k: int = K) -> tuple[pd.DataFrame, dict]:
        """Top-k para una consulta libre. Devuelve `(resultados, estado)`.

        `estado`: tokens de la consulta, pasajes elegibles, excluidos por el filtro, excluidos
        por fecha desconocida y avisos. Una consulta sin tokens devuelve cero filas y un aviso.
        """
        tokens = preproceso.tokenizar(consulta)
        elegibles = mascara_fecha(self.fecha, desde, hasta)
        con_filtro = desde is not None or hasta is not None
        estado = {
            "tokens": tokens, "modelo": modelo, "elegibles": int(elegibles.sum()),
            "excluidos_por_filtro": int((~elegibles).sum()),
            "excluidos_fecha_desconocida": int(np.isnat(self.fecha).sum()) if con_filtro else 0,
            "avisos": [],
        }
        if not tokens:
            estado["avisos"].append("La consulta no tiene términos tras el preprocesamiento.")
            return self._tabla(np.array([], dtype=int), np.array([])), estado
        puntajes = self.puntajes(modelo, tokens)
        sel = top_k(puntajes, elegibles, self.doc_id, self.posicion, k)
        if sel.size < k:
            estado["avisos"].append(f"Solo hay {sel.size} pasajes elegibles; no se rellena.")
        if sel.size and (puntajes[sel] == 0).any():
            estado["avisos"].append("Hay resultados con puntaje 0 (sin señal léxica).")
        return self._tabla(sel, puntajes[sel]), estado

    def _tabla(self, sel: np.ndarray, puntajes: np.ndarray) -> pd.DataFrame:
        p = self.pasajes.iloc[sel]
        return pd.DataFrame({
            "rango": np.arange(1, len(sel) + 1), "passage_id": p["passage_id"].to_numpy(),
            "doc_id": self.doc_id[sel], "fecha": p["fecha"].to_numpy(),
            "posicion": self.posicion[sel], "puntaje": puntajes,
            "sin_senal_lexica": (puntajes == 0).astype(int),
        })


def variantes_oficiales(buscador: Buscador, consultas: pd.DataFrame) -> pd.DataFrame:
    """Las cuatro variantes por consulta (`modelo` + `variante`) en el formato de `ranking.csv`
    más `sin_senal_lexica`."""
    filas = []
    for q in consultas.itertuples(index=False):
        for modelo in MODELOS:
            for variante in ("con_filtro", "sin_filtro"):
                desde, hasta = (q.desde, q.hasta) if variante == "con_filtro" else (None, None)
                res, _ = buscador.buscar(q.consulta, desde, hasta, modelo, K)
                res = res.assign(query_id=q.query_id, modelo=f"{modelo}_{variante}",
                                 variante=variante)
                filas.append(res)
    cols = ["query_id", "modelo", "variante", "rango", "passage_id", "doc_id", "fecha",
            "posicion", "puntaje", "sin_senal_lexica"]
    return pd.concat(filas, ignore_index=True)[cols]
