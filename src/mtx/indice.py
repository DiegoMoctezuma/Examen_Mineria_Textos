"""Índice invertido construido a mano (PRD §6.3).

Estructura: `postings[termino][idx] = tf`, con `idx` el índice interno estable de cada pasaje
(posición en `ids`, que sigue el orden de `data/pasajes.parquet`). Además `df`, `N`,
`longitud` (tokens del cuerpo) y `avgdl`. Se ajusta una sola vez sobre todos los pasajes: filtrar
por fecha no recalcula N, df, idf ni avgdl.
"""
from __future__ import annotations

import hashlib
import json
import math
import pickle
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import adaptadores_kit, preproceso


def identidad(tokens):
    """Analizador identidad para scikit-learn. Definida a nivel de módulo (no lambda) para poder
    persistir el vectorizador con pickle y cargarlo en otro proceso."""
    return tokens


@dataclass
class Indice:
    ids: list[str]
    postings: dict[str, dict[int, int]]
    longitud: np.ndarray
    df: dict[str, int] = field(default_factory=dict)
    N: int = 0
    avgdl: float = 0.0
    _idx_de: dict[str, int] | None = field(default=None, repr=False)

    @property
    def idx_de(self) -> dict[str, int]:
        if self._idx_de is None:
            self._idx_de = {p: i for i, p in enumerate(self.ids)}
        return self._idx_de

    def idf_bm25(self, termino: str) -> float:
        """idf positivo de BM25: ln(1 + (N - df + 0.5) / (df + 0.5)). Cero si no existe."""
        d = self.df.get(termino, 0)
        return math.log(1 + (self.N - d + 0.5) / (d + 0.5)) if d else 0.0


def construir(ids: list[str], lista_tokens: Iterable[list[str]]) -> Indice:
    """Construye el índice. `lista_tokens` entrega, en el orden de `ids`, los tokens del cuerpo."""
    postings: dict[str, dict[int, int]] = {}
    longitud = np.zeros(len(ids), dtype=np.int32)
    n = 0
    for idx, tokens in enumerate(lista_tokens):
        longitud[idx] = len(tokens)
        for termino, tf in Counter(tokens).items():
            fila = postings.get(termino)
            if fila is None:
                postings[termino] = {idx: tf}
            else:
                fila[idx] = tf
        n += 1
    if n != len(ids):
        raise ValueError(f"Se recibieron {n} listas de tokens para {len(ids)} pasajes")
    df = {t: len(f) for t, f in postings.items()}
    N = len(ids)
    return Indice(ids=list(ids), postings=postings, longitud=longitud, df=df, N=N,
                  avgdl=float(longitud.mean()) if N else 0.0)


def matriz_conteos(lista_tokens: Iterable[list[str]]):
    """Verificación cruzada: `CountVectorizer` con analizador identidad sobre los mismos tokens."""
    from sklearn.feature_extraction.text import CountVectorizer
    vec = CountVectorizer(analyzer=identidad)
    return vec, vec.fit_transform(lista_tokens)


def guardar(indice: Indice, ruta_pkl: Path, ruta_meta: Path, hash_tokens: str,
            hash_config: str) -> dict:
    """Persiste el índice (pickle protocolo 5) y su metadato de invalidación."""
    ruta_pkl = Path(ruta_pkl)
    ruta_pkl.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_pkl, "wb") as f:
        pickle.dump(indice, f, protocol=5)
    meta = {
        "N": indice.N, "vocabulario": len(indice.postings), "avgdl": indice.avgdl,
        "construido": datetime.now().isoformat(timespec="seconds"),
        "sha256_tokens": hash_tokens, "sha256_configuracion_preproceso": hash_config,
        "sha256_indice": adaptadores_kit.sha256_archivo(ruta_pkl),
    }
    Path(ruta_meta).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def cargar(ruta_pkl: Path, ruta_meta: Path | None = None, hash_tokens: str | None = None) -> Indice:
    """Carga el índice. Si se da `hash_tokens`, exige que coincida con el del metadato: nunca se
    usa un índice viejo con tokens nuevos."""
    if hash_tokens is not None and ruta_meta is not None:
        meta = json.loads(Path(ruta_meta).read_text(encoding="utf-8"))
        if meta["sha256_tokens"] != hash_tokens:
            raise ValueError("El índice no corresponde a los tokens actuales: reconstruir con "
                             "`make indice`")
    with open(ruta_pkl, "rb") as f:
        return pickle.load(f)


# --------------------------------------------------------------------------- tokens


def tokenizar_pasajes(pasajes: pd.DataFrame) -> list[list[str]]:
    """Tokens del cuerpo de cada pasaje (D03), en el orden de `pasajes`."""
    return [preproceso.tokenizar_pasaje(t, i)
            for t, i in zip(pasajes["texto"], pasajes["inicio_cuerpo"])]


def hash_tokens(ids: list[str], lista_tokens: list[list[str]]) -> str:
    """Huella del contenido de `tokens.parquet` (ids, orden y tokens), independiente del formato
    binario del archivo."""
    h = hashlib.sha256()
    for pid, toks in zip(ids, lista_tokens):
        h.update(pid.encode("utf-8"))
        h.update(b"\x1f")
        h.update(" ".join(toks).encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()


def guardar_tokens(ids: list[str], lista_tokens: list[list[str]], ruta: Path) -> None:
    pd.DataFrame({"passage_id": ids, "tokens": lista_tokens}).to_parquet(ruta, index=False)


def cargar_tokens(ruta: Path) -> tuple[list[str], list[list[str]]]:
    df = pd.read_parquet(ruta)
    return list(df["passage_id"]), [list(t) for t in df["tokens"]]


# --------------------------------------------------------------------------- muestras para el reporte


def contexto(cuerpo: str, raiz: str, ancho: int = 80) -> str:
    """`ancho` caracteres del cuerpo alrededor de la primera palabra cuya raíz es `raiz`."""
    texto = unicodedata.normalize("NFC", cuerpo)
    for m in preproceso.RE_TOKEN.finditer(texto):
        if preproceso.tokenizar(m.group(0)) == [raiz]:
            centro = (m.start() + m.end()) // 2
            ini = max(0, min(centro - ancho // 2, len(texto) - ancho))
            return " ".join(texto[ini:ini + ancho].split())
    return " ".join(texto[:ancho].split())


def muestra_postings(ind: Indice, pasajes: pd.DataFrame, raiz: str, n: int = 15) -> dict:
    """df, idf (BM25) y los `n` pasajes con mayor tf de un término; desempate (doc_id, posicion)."""
    fila = ind.postings.get(raiz, {})
    p = pasajes.iloc[list(fila)].assign(tf=list(fila.values()))
    p = p.sort_values(["tf", "doc_id", "posicion"], ascending=[False, True, True]).head(n)
    return {
        "raiz": raiz, "df": ind.df.get(raiz, 0), "idf_bm25": ind.idf_bm25(raiz),
        "cf": int(sum(fila.values())),
        "top": [{"passage_id": r.passage_id, "tf": int(r.tf),
                 "fecha": "" if pd.isna(r.fecha) else r.fecha.date().isoformat(),
                 "contexto": contexto(r.texto[r.inicio_cuerpo:], raiz)}
                for r in p.itertuples(index=False)],
    }


def vocabulario_top(ind: Indice, n: int = 200) -> pd.DataFrame:
    """Los `n` términos con mayor df (desempate alfabético), con cf e idf de BM25."""
    filas = [{"termino": t, "df": ind.df[t], "cf": int(sum(f.values())),
              "df_pct": round(100 * ind.df[t] / ind.N, 3), "idf_bm25": round(ind.idf_bm25(t), 6)}
             for t, f in ind.postings.items()]
    return (pd.DataFrame(filas).sort_values(["df", "termino"], ascending=[False, True])
            .head(n).reset_index(drop=True))
