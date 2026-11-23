"""03 · Rankings TF-IDF y BM25, con y sin filtro de fecha (PRD §6.4). `make ranking`.

Entradas: data/consultas.csv (Q1 a Q10) y lo que deja `make indice`.
Salidas: salida/ranking.csv (copia idéntica en la raíz tras validar), salida/03_ranking_detalle.csv,
salida/03_solape_modelos.csv, salida/03_excluidos_por_filtro.csv y salida/03_resumen.json.
No lee juicios ni gold.

`--v2` (PRD v2 D26, WP-03, `make ranking-v2`): las 8 variantes {tfidf, bm25} × {con, sin}_filtro ×
{stem, lema} en `salida/v2/ranking_8_variantes.csv`, con el formato de `ranking.csv`. Exige que las 4
de stem sean idénticas a `salida/ranking.csv` en las consultas que ya tenía. No toca `ranking.csv`
y solo imprime conteos.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys

import pandas as pd

from mtx import adaptadores_kit, config, consultas, ranking


def main_v2() -> None:
    config.DIR_SALIDA_V2.mkdir(parents=True, exist_ok=True)
    cons = consultas.cargar()
    stem = ranking.cargar_buscador(verificar_pasajes=True)
    lema = ranking.cargar_buscador(verificar_pasajes=True, raiz="lema")
    v = ranking.formatear_ranking(ranking.variantes_v2(stem, lema, cons))
    ruta = config.DIR_SALIDA_V2 / "ranking_8_variantes.csv"
    v.to_csv(ruta, index=False, encoding="utf-8")
    leido = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    problemas = ranking.validar_ranking(leido, cons, ranking.MODELOS_V2)
    v1 = pd.read_csv(config.DIR_SALIDA / "ranking.csv", dtype=str, keep_default_na=False)
    mio = leido[leido["modelo"].isin(ranking.MODELOS_OFICIALES)
                & leido["query_id"].isin(set(v1["query_id"]))].reset_index(drop=True)
    if not mio.equals(v1.reset_index(drop=True)):
        problemas.append("Las variantes de stem no son idénticas a salida/ranking.csv (v1)")
    if problemas:
        print("ranking_8_variantes.csv NO es válido:", *problemas, sep="\n- ")
        sys.exit(1)
    print(f"ranking_8_variantes.csv: {len(leido)} filas, {leido['query_id'].nunique()} consultas, "
          f"{leido['modelo'].nunique()} variantes; stem idéntico a v1")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2", action="store_true")
    if ap.parse_args().v2:
        main_v2()
    else:
        main_v1()


def main_v1() -> None:
    config.DIR_SALIDA.mkdir(exist_ok=True)
    cons = consultas.cargar_v1()
    buscador = ranking.cargar_buscador(verificar_pasajes=True)

    estados: dict = {}
    v = ranking.variantes_oficiales(buscador, cons, estados)

    ruta = config.DIR_SALIDA / "ranking.csv"
    ranking.formatear_ranking(v).to_csv(ruta, index=False, encoding="utf-8")
    leido = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    problemas = ranking.validar_ranking(leido, cons)
    if problemas:
        print("ranking.csv NO es válido; no se copia a la raíz:", *problemas, sep="\n- ")
        sys.exit(1)
    shutil.copyfile(ruta, config.RAIZ / "ranking.csv")

    p = buscador.pasajes.set_index("passage_id")
    det = ranking.formatear_ranking(v).assign(
        interlocutor=v["passage_id"].map(p["interlocutor"]).to_numpy(),
        es_reportero=v["passage_id"].map(p["es_reportero"]).astype(int).to_numpy(),
        titulo=v["passage_id"].map(p["titulo"]).to_numpy(),
        sin_senal_lexica=v["sin_senal_lexica"].to_numpy(),
        texto=v["passage_id"].map(p["texto"]).str.slice(0, 400).to_numpy(),
    )
    det.to_csv(config.DIR_SALIDA / "03_ranking_detalle.csv", index=False, encoding="utf-8")

    solape = ranking.solape_modelos(v)
    solape.to_csv(config.DIR_SALIDA / "03_solape_modelos.csv", index=False)
    excl = ranking.excluidos_por_filtro(v, cons, estados)
    excl.to_csv(config.DIR_SALIDA / "03_excluidos_por_filtro.csv", index=False)

    filas = v.groupby(["query_id", "modelo"]).size()
    excepciones = [{"query_id": q, "modelo": m, "filas": int(n),
                    "motivo": "; ".join(estados[(q, m)]["avisos"])}
                   for (q, m), n in filas.items() if n != ranking.K]
    con_ceros = [{"query_id": q, "modelo": m, "filas_sin_senal": int(g["sin_senal_lexica"].sum())}
                 for (q, m), g in v.groupby(["query_id", "modelo"]) if g["sin_senal_lexica"].any()]
    identicos = solape.loc[solape["identico_tfidf_vs_bm25_con_filtro"] == 1, "query_id"].tolist()
    resumen = {
        "filas": len(v), "consultas": int(v["query_id"].nunique()),
        "excepciones_a_10_filas": excepciones, "filas_sin_senal_lexica": con_ceros,
        "consultas_con_ranking_identico_tfidf_bm25_con_filtro": identicos,
        "todas_identicas": len(identicos) == len(cons),
        "sha256_ranking_csv": adaptadores_kit.sha256_archivo(ruta),
        "sha256_indice_meta": adaptadores_kit.sha256_archivo(config.INDICE_META),
        "tokens_por_consulta": {q.query_id: estados[(q.query_id, "bm25_con_filtro")]["tokens"]
                                for q in cons.itertuples(index=False)},
    }
    (config.DIR_SALIDA / "03_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"ranking.csv: {len(v)} filas, {resumen['consultas']} consultas, 4 variantes; "
          f"copiado a la raíz")
    print(f"Excepciones a 10 filas: {len(excepciones)}; variantes con filas sin señal léxica: "
          f"{len(con_ceros)}; consultas con TF-IDF = BM25 (con filtro): {identicos or 'ninguna'}")


if __name__ == "__main__":
    main()
