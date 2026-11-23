"""Preprocesamiento para IR (PRD §6.2, D03).

Cadena exacta: NFC y minúsculas; tokens alfanuméricos; stoplist; descarte de tokens de longitud
2 o menos salvo numéricos; stemming Snowball en español. Los pasajes se indexan con
`tokenizar_pasaje`, que solo ve el cuerpo (`texto[inicio_cuerpo:]`); las consultas con `tokenizar`.

En v1 se usó stemming y no lematización por velocidad (127 mil pasajes), por no depender de spaCy
y porque basta para consultas cortas.

v2 (PRD v2 D26, WP-03) agrega `raiz="lema"`: misma normalización, mismo `RE_TOKEN`, misma stoplist y
mismo filtro de longitud, aplicados a la forma de superficie; solo el último paso cambia de raíz
Snowball a lema de spaCy `es_core_news_md` (sin parser ni NER). spaCy analiza el texto completo para
que el morfologizador vea el contexto, y cada token de `RE_TOKEN` toma el lema del token de spaCy con
el mismo intervalo; si spaCy lo partió distinto (p. ej. `covid-19`), se queda la superficie. El
camino `raiz="stem"` no cambia: las variantes v1 salen idénticas.

Política de tokens: `RE_TOKEN` conserva letras (con acentos y ñ), dígitos y un guion interno
(`covid-19`). Las siglas y los nombres propios no se retiran; el texto se pasa a minúsculas.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from functools import lru_cache

from nltk.stem.snowball import SnowballStemmer

from . import config

RE_TOKEN = re.compile(r"[a-záéíóúñü0-9]+(?:-[a-záéíóúñü0-9]+)?", re.IGNORECASE)

_STEMMER = SnowballStemmer("spanish")

RAICES = ("stem", "lema")
MODELO_LEMA = "es_core_news_md"


@lru_cache(maxsize=1)
def stoplist() -> frozenset[str]:
    """Stoplist efectiva: lista de NLTK en español (copia versionada) ∪ estenográfica.

    `config/stopwords_es.txt` es una copia exacta de `nltk.corpus.stopwords.words("spanish")`
    (313 palabras): se usa siempre esta copia para que el resultado no dependa de `nltk_data`.
    """
    palabras: set[str] = set()
    for nombre in ("stopwords_es.txt", "stoplist_extra.txt"):
        texto = (config.DIR_CONFIG / nombre).read_text(encoding="utf-8")
        palabras.update(unicodedata.normalize("NFC", p.strip().lower())
                        for p in texto.splitlines() if p.strip())
    return frozenset(palabras)


@lru_cache(maxsize=1)
def hash_stoplist() -> str:
    return hashlib.sha256("\n".join(sorted(stoplist())).encode("utf-8")).hexdigest()


def configuracion_efectiva(raiz: str = "stem") -> dict:
    """Parámetros congelados del preprocesamiento, para el manifiesto y `tokens.parquet`."""
    cfg = {
        "regex_token": RE_TOKEN.pattern,
        "stemmer": "SnowballStemmer('spanish')",
        "longitud_minima_no_numerica": 3,
        "stoplist_palabras": len(stoplist()),
        "stoplist_sha256": hash_stoplist(),
    }
    if raiz == "lema":
        import spacy
        nlp = _nlp()
        cfg = {k: v for k, v in cfg.items() if k != "stemmer"} | {
            "lematizador": f"spacy {spacy.__version__} · {MODELO_LEMA} {nlp.meta['version']}",
            "componentes": list(nlp.pipe_names),
        }
    return cfg


@lru_cache(maxsize=500_000)
def _raiz(token: str) -> str:
    return _STEMMER.stem(token)


def _se_queda(tok: str, paradas: frozenset[str]) -> bool:
    return tok not in paradas and (len(tok) > 2 or tok.isdigit())


def tokenizar_sin_stem(texto: str) -> list[str]:
    """Tokens tras stoplist y filtro de longitud, sin stemming (para mostrar su efecto)."""
    paradas = stoplist()
    return [t for t in RE_TOKEN.findall(unicodedata.normalize("NFC", texto).lower())
            if _se_queda(t, paradas)]


def tokenizar(texto: str, raiz: str = "stem") -> list[str]:
    """Tokens finales. Se usa para consultas y, vía `tokenizar_pasaje`, pasajes."""
    if raiz == "lema":
        return lematizar([texto])[0]
    if raiz != "stem":
        raise ValueError(f"Raíz desconocida: {raiz!r}; use {RAICES}")
    return [_raiz(t) for t in tokenizar_sin_stem(texto)]


def tokenizar_pasaje(texto: str, inicio_cuerpo: int, raiz: str = "stem") -> list[str]:
    """Tokeniza solo `texto[inicio_cuerpo:]`: la marca de interlocutor no entra al índice (D03)."""
    return tokenizar(texto[inicio_cuerpo:], raiz)


# --------------------------------------------------------------------------- lematización (v2)


@lru_cache(maxsize=1)
def _nlp():
    import spacy
    return spacy.load(MODELO_LEMA, disable=["parser", "ner"])


def _lemas_de_doc(texto: str, doc) -> list[str]:
    """Tokens de `RE_TOKEN` que pasan la stoplist y el filtro de longitud (sobre la superficie en
    minúsculas, como en v1), reemplazados por el lema del token de spaCy con el mismo intervalo."""
    paradas = stoplist()
    lema_en = {t.idx: (t.idx + len(t.text), t.lemma_) for t in doc}
    salida = []
    for m in RE_TOKEN.finditer(texto):
        sup = m.group(0).lower()
        if not _se_queda(sup, paradas):
            continue
        fin, lema = lema_en.get(m.start(), (None, ""))
        lema = unicodedata.normalize("NFC", lema).lower()
        salida.append(lema if fin == m.end() and lema and not any(c.isspace() for c in lema)
                      else sup)
    return salida


def lematizar(textos, n_process: int = 1, batch_size: int = 256) -> list[list[str]]:
    """Tokens lematizados de cada texto, en orden. `n_process > 1` usa varios procesos de spaCy;
    el resultado no depende de ese número."""
    nfc = [unicodedata.normalize("NFC", t) for t in textos]
    docs = _nlp().pipe(nfc, batch_size=batch_size, n_process=n_process)
    return [_lemas_de_doc(t, d) for t, d in zip(nfc, docs)]
