"""02 · Tokens, índice invertido y TF-IDF (PRD §6.2, §6.3). `make indice`.

Entradas: data/pasajes.parquet y data/consultas.csv.
Salidas: data/tokens.parquet, data/indice.pkl, data/indice_meta.json, data/tfidf.pkl,
data/tfidf_X.npz, salida/02_tokens_consultas.md, salida/02_postings.md y
salida/02_vocabulario_top.csv. Determinista; no lee juicios ni gold.

`--raiz lema` (PRD v2 D26, WP-03, `make indice-lema`): el mismo índice con lemas de spaCy en
`data/v2/` (tokens_lema.parquet, indice_lema.pkl, indice_lema_meta.json, tfidf_lema.pkl y
tfidf_lema_X.npz) y `salida/v2/02_comparacion_stem_lema.md`. No toca nada de v1 ni muestra rankings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import pandas as pd

from mtx import config, consultas, corpus, indice, preproceso, ranking

TERMINOS_POSTINGS = ["tren", "vacuna", "refinería", "huachicol"]


def md_tokens_consultas(cons: pd.DataFrame, ind: indice.Indice) -> str:
    L = ["# Tokens de las consultas", "",
         ("Cadena de PRD §6.2: NFC y minúsculas, `RE_TOKEN`, stoplist, longitud mínima 3 (salvo "
          "números) y Snowball en español. Cada token final indica su df en el índice "
          f"(N = {ind.N:,} pasajes); df 0 significa que el término no puntúa."), ""]
    for r in cons.itertuples(index=False):
        sin_stem = preproceso.tokenizar_sin_stem(r.consulta)
        finales = preproceso.tokenizar(r.consulta)
        originales = preproceso.RE_TOKEN.findall(r.consulta.lower())
        retirados = [t for t in originales if t not in sin_stem]
        L += [f"## {r.query_id}: {r.consulta}", "",
              f"- Palabras originales: {', '.join(originales)}",
              f"- Retiradas (stoplist o longitud): {', '.join(retirados) or '(ninguna)'}",
              f"- Tras stoplist, sin stemming: {', '.join(sin_stem)}",
              "- Tokens finales: " + ", ".join(f"`{t}` (df {ind.df.get(t, 0):,})"
                                               for t in finales),
              ""]
    return "\n".join(L)


def md_postings(muestras: list[dict], ind: indice.Indice) -> str:
    L = ["# Postings de muestra", "",
         (f"Índice invertido sobre {ind.N:,} pasajes (avgdl = {ind.avgdl:.2f} tokens del "
          "cuerpo). idf con la fórmula de BM25, ln(1 + (N - df + 0.5) / (df + 0.5)). Por término "
          "se muestran los 15 pasajes con mayor tf (desempate por `doc_id` y `posicion`); **es "
          "una muestra**: la lista completa de postings vive en `data/indice.pkl`."), ""]
    for m in muestras:
        L += [f"## `{m['palabra']}` → raíz `{m['raiz']}`", "",
              (f"- df = {m['df']:,} pasajes ({100 * m['df'] / ind.N:.2f} %), "
               f"frecuencia total = {m['cf']:,}, idf = {m['idf_bm25']:.4f}"), "",
              "| # | passage_id | fecha | tf | contexto (80 caracteres) |",
              "| ---: | --- | --- | ---: | --- |"]
        for i, t in enumerate(m["top"], 1):
            ctx = t["contexto"].replace("|", "\\|")
            L.append(f"| {i} | `{t['passage_id']}` | {t['fecha'] or 'desconocida'} | "
                     f"{t['tf']} | {ctx} |")
        L.append("")
    return "\n".join(L)


COMPARAR = [("maya", "mayo"), ("vacunas", "vacuna"), ("refinería", "refinerías"),
            ("presidente", "presidencia"), ("programa", "programas"), ("elecciones", "electoral")]


def md_comparacion(cons: pd.DataFrame, stem: indice.Indice, lema: indice.Indice,
                   segundos: float) -> str:
    """Vocabulario, pares de palabras y tokens de cada consulta con su df e idf en los dos índices.
    No contiene rankings ni puntajes de pasajes (D32)."""
    def tok(palabra, raiz, ind):
        t = preproceso.tokenizar(palabra, raiz)
        return ", ".join(f"`{x}` (df {ind.df.get(x, 0):,})" for x in t) or "(se descarta)"
    L = ["# Stem frente a lema", "",
         ("Mismo pipeline (NFC, `RE_TOKEN`, stoplist y longitud mínima sobre la superficie); solo "
          "cambia la raíz: Snowball en v1, lema de spaCy `es_core_news_md` en v2 (PRD v2 D26)."), "",
         "| | stem (v1) | lema (v2) |", "| --- | ---: | ---: |",
         f"| Pasajes | {stem.N:,} | {lema.N:,} |",
         f"| Vocabulario | {len(stem.postings):,} | {len(lema.postings):,} |",
         f"| Tokens por pasaje (avgdl) | {stem.avgdl:.2f} | {lema.avgdl:.2f} |",
         (f"| Pasajes sin tokens | {int((stem.longitud == 0).sum())} | "
          f"{int((lema.longitud == 0).sum())} |"), "",
         f"Lematizar el corpus tomó {segundos / 60:.1f} min.", "",
         "## Pares de palabras", "", "| palabra | stem (v1) | lema (v2) |", "| --- | --- | --- |"]
    for par in COMPARAR:
        for w in par:
            L.append(f"| {w} | {tok(w, 'stem', stem)} | {tok(w, 'lema', lema)} |")
    L += ["", "## Términos de cada consulta", "",
          "idf con la fórmula de BM25, ln(1 + (N - df + 0.5) / (df + 0.5)).", "",
          "| consulta | stem (v1): término (idf) | lema (v2): término (idf) |", "| --- | --- | --- |"]
    for q in cons.itertuples(index=False):
        a = ", ".join(f"`{t}` ({stem.idf_bm25(t):.2f})" for t in preproceso.tokenizar(q.consulta))
        b = ", ".join(f"`{t}` ({lema.idf_bm25(t):.2f})"
                      for t in preproceso.tokenizar(q.consulta, "lema"))
        L.append(f"| {q.query_id}: {q.consulta} | {a} | {b} |")
    return "\n".join(L)


def main_lema() -> None:
    from mtx import ranking as _r
    t0 = time.time()
    config.DIR_DATA_V2.mkdir(parents=True, exist_ok=True)
    config.DIR_SALIDA_V2.mkdir(parents=True, exist_ok=True)
    pasajes = pd.read_parquet(config.PASAJES_PARQUET)
    ids = list(pasajes["passage_id"])
    procesos = max(1, min(6, (os.cpu_count() or 2) - 2))
    toks = indice.tokenizar_pasajes(pasajes, raiz="lema", n_process=procesos)
    t1 = time.time()
    indice.guardar_tokens(ids, toks, config.TOKENS_LEMA_PARQUET)
    h_tokens = indice.hash_tokens(ids, toks)
    cfg = preproceso.configuracion_efectiva("lema")
    h_cfg = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode("utf-8")).hexdigest()
    ind = indice.construir(ids, toks)
    meta = indice.guardar(ind, config.INDICE_LEMA_PKL, config.INDICE_LEMA_META, h_tokens, h_cfg)
    vec, X = ranking.ajustar_tfidf(toks)
    ranking.guardar_tfidf(vec, X, config.TFIDF_LEMA_PKL, config.TFIDF_LEMA_NPZ)
    if len(vec.vocabulary_) != len(ind.postings):
        raise RuntimeError("TF-IDF y el índice no ven el mismo vocabulario (min_df debe ser 1)")
    meta |= {
        "sha256_pasajes": corpus.hash_pasajes(pasajes),
        "preproceso": cfg,
        "pasajes_sin_tokens": int((ind.longitud == 0).sum()),
        "tfidf": {"vocabulario": len(vec.vocabulary_), "nnz": int(X.nnz),
                  "sha256_pkl": indice.adaptadores_kit.sha256_archivo(config.TFIDF_LEMA_PKL),
                  "sha256_npz": indice.adaptadores_kit.sha256_archivo(config.TFIDF_LEMA_NPZ)},
        "sha256_tokens_parquet": indice.adaptadores_kit.sha256_archivo(config.TOKENS_LEMA_PARQUET),
        "procesos_spacy": procesos,
        "segundos": {"lematizar": round(t1 - t0, 1), "total": round(time.time() - t0, 1)},
    }
    config.INDICE_LEMA_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    stem = _r.cargar_buscador().bm25.indice
    (config.DIR_SALIDA_V2 / "02_comparacion_stem_lema.md").write_text(
        md_comparacion(consultas.cargar(), stem, ind, t1 - t0) + "\n", encoding="utf-8")
    print(f"Índice lematizado: {ind.N:,} pasajes, vocabulario {len(ind.postings):,} "
          f"(stem: {len(stem.postings):,}), avgdl {ind.avgdl:.2f}, en {meta['segundos']['total']} s")
    print(f"hash de tokens: {h_tokens}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", choices=preproceso.RAICES, default="stem")
    if ap.parse_args().raiz == "lema":
        main_lema()
    else:
        main_stem()


def main_stem() -> None:
    t0 = time.time()
    config.DIR_SALIDA.mkdir(exist_ok=True)
    pasajes = pd.read_parquet(config.PASAJES_PARQUET)
    ids = list(pasajes["passage_id"])

    toks = indice.tokenizar_pasajes(pasajes)
    indice.guardar_tokens(ids, toks, config.TOKENS_PARQUET)
    h_tokens = indice.hash_tokens(ids, toks)
    cfg = preproceso.configuracion_efectiva()
    h_cfg = preproceso.hash_stoplist()
    t1 = time.time()

    ind = indice.construir(ids, toks)
    meta = indice.guardar(ind, config.INDICE_PKL, config.INDICE_META, h_tokens, h_cfg)

    vec, X = ranking.ajustar_tfidf(toks)
    ranking.guardar_tfidf(vec, X, config.TFIDF_PKL, config.TFIDF_NPZ)
    if len(vec.vocabulary_) != len(ind.postings):
        raise RuntimeError("TF-IDF y el índice no ven el mismo vocabulario (min_df debe ser 1)")

    meta |= {
        "sha256_pasajes": corpus.hash_pasajes(pasajes),
        "preproceso": cfg,
        "pasajes_sin_tokens": int((ind.longitud == 0).sum()),
        "tfidf": {"vocabulario": len(vec.vocabulary_), "nnz": int(X.nnz),
                  "sha256_pkl": indice.adaptadores_kit.sha256_archivo(config.TFIDF_PKL),
                  "sha256_npz": indice.adaptadores_kit.sha256_archivo(config.TFIDF_NPZ)},
        "segundos": {"tokenizar": round(t1 - t0, 1), "total": None},
    }

    cons = consultas.cargar()
    (config.DIR_SALIDA / "02_tokens_consultas.md").write_text(
        md_tokens_consultas(cons, ind) + "\n", encoding="utf-8")
    muestras = []
    for palabra in TERMINOS_POSTINGS:
        (raiz,) = preproceso.tokenizar(palabra)
        muestras.append({"palabra": palabra} | indice.muestra_postings(ind, pasajes, raiz))
    (config.DIR_SALIDA / "02_postings.md").write_text(md_postings(muestras, ind) + "\n",
                                                       encoding="utf-8")
    indice.vocabulario_top(ind).to_csv(config.DIR_SALIDA / "02_vocabulario_top.csv", index=False)

    meta["segundos"]["total"] = round(time.time() - t0, 1)
    config.INDICE_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    print(f"{ind.N:,} pasajes, vocabulario {len(ind.postings):,}, avgdl {ind.avgdl:.2f}, "
          f"{meta['pasajes_sin_tokens']} pasajes sin tokens, en {meta['segundos']['total']} s")
    print(f"hash de tokens: {h_tokens}")


if __name__ == "__main__":
    main()
