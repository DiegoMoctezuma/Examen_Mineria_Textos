"""04 · Pool de relevancia (PRD §6.5, D06). `make pool`.

Entradas: ranking.csv (salida/), data/pasajes.parquet y data/consultas.csv.
Salidas: salida/04_pool.csv, salida/04_pool_resumen.csv y salida/04_pool_meta.json.

Si el pool ya existe, se reconstruye en memoria y se compara. Si cambió y ya hay juicios en
anotaciones/juicios_relevancia.csv, se detiene sin sobrescribir nada y enumera las diferencias.
Nunca escribe en anotaciones/.

`--v2` (PRD v2 D27, WP-05, `make pool-v2`): unión de los top-10 de las 8 variantes de
`salida/v2/ranking_8_variantes.csv` para Q1 a Q15, con el tope de 450 pares de D27. Escribe
`salida/v2/04_pool.csv`, `04_pool_resumen.csv`, `04_pool_lote2.csv` (los pares que no estaban en el
pool v1: el lote 2 de juicios) y `04_pool_meta.json`. Exige los 176 pares v1 y las 15 consultas; si
el pool ya existe y cambió con el lote 2 asignado, se detiene. Solo imprime conteos (D32).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

import pandas as pd

from mtx import adaptadores_kit, config, consultas, pool

RUTA_POOL = config.DIR_SALIDA / "04_pool.csv"
RUTA_JUICIOS = config.DIR_ANOTACIONES / "juicios_relevancia.csv"
RUTA_CRITERIOS = config.DIR_CONFIG / "criterios_relevancia.md"


def hay_juicios() -> bool:
    if not RUTA_JUICIOS.exists():
        return False
    return len(pd.read_csv(RUTA_JUICIOS, dtype=str, keep_default_na=False)) > 0


def main_v2() -> None:
    from mtx import anotadores
    ruta_ranking = config.DIR_SALIDA_V2 / "ranking_8_variantes.csv"
    ranking8 = pd.read_csv(ruta_ranking, dtype=str, keep_default_na=False)
    cons = consultas.cargar()
    esperadas = [f"Q{i}" for i in range(1, 16)]
    if list(cons["query_id"]) != esperadas or sorted(set(ranking8["query_id"]), key=lambda q: int(q[1:])) != esperadas:
        sys.exit("El pool v2 necesita Q1 a Q15 en data/consultas.csv y en el ranking de 8 "
                 "variantes: `make consultas-v2 ranking-v2`.")
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "doc_id", "fecha", "texto", "texto_sha256"])
    crudo, usadas = pool.construir_pool_v2(ranking8, pasajes, cons)
    nuevo = pool.como_texto(pool.formatear_pool(crudo))
    v1 = pool.leer_pool(RUTA_POOL)
    faltan = set(zip(v1["query_id"], v1["passage_id"])) - set(zip(nuevo["query_id"],
                                                                     nuevo["passage_id"]))
    if faltan:
        sys.exit(f"El pool v2 no contiene {len(faltan)} pares del pool v1: revisar el ranking.")
    lote2 = pool.pares_nuevos(nuevo, v1)

    ruta = config.DIR_SALIDA_V2 / "04_pool.csv"
    if ruta.exists():
        dif = pool.diferencias_pool(pool.leer_pool(ruta), nuevo)
        if not dif:
            print(f"El pool v2 no cambió ({len(nuevo)} pares); no se reescribe.")
            return
        asign = anotadores.leer_asignacion()
        if (asign["lote"] == "2").any():
            print("ALTO: el pool v2 cambió y el lote 2 ya está asignado. No se sobrescribe nada.",
                  *dif[:50], sep="\n- ")
            sys.exit(1)
        print(f"El pool v2 cambió ({len(dif)} diferencias) y el lote 2 no está asignado: se reescribe.")
    config.DIR_SALIDA_V2.mkdir(parents=True, exist_ok=True)
    nuevo.to_csv(ruta, index=False, encoding="utf-8")
    lote2.to_csv(config.DIR_SALIDA_V2 / "04_pool_lote2.csv", index=False, encoding="utf-8")
    resumen = pool.resumen_pool(nuevo.assign(en_ventana=nuevo["en_ventana"] == "1"), usadas)
    resumen["pares_nuevos"] = resumen["query_id"].map(lote2.groupby("query_id").size()).fillna(0).astype(int)
    resumen.to_csv(config.DIR_SALIDA_V2 / "04_pool_resumen.csv", index=False)
    meta = {
        "construido": datetime.now().isoformat(timespec="seconds"),
        "pares": len(nuevo), "pasajes_distintos": int(nuevo["passage_id"].nunique()),
        "pares_v1": len(v1), "pares_lote2": len(lote2),
        "variantes": list(usadas), "tope_450_aplicado": len(usadas) < 8,
        "por_consulta": dict(zip(resumen["query_id"], resumen["pasajes"].astype(int))),
        "semilla_orden": config.SEMILLA,
        "sha256_pool": pool.hash_pool(pool.leer_pool(ruta)),
        "sha256_pool_csv": adaptadores_kit.sha256_archivo(ruta),
        "sha256_lote2_csv": adaptadores_kit.sha256_archivo(config.DIR_SALIDA_V2 / "04_pool_lote2.csv"),
        "sha256_ranking_8_variantes": adaptadores_kit.sha256_archivo(ruta_ranking),
        "sha256_consultas_csv": adaptadores_kit.sha256_archivo(config.CONSULTAS_CSV),
        "sha256_indice_meta": adaptadores_kit.sha256_archivo(config.INDICE_META),
        "sha256_indice_lema_meta": adaptadores_kit.sha256_archivo(config.INDICE_LEMA_META),
        "sha256_criterios_relevancia": adaptadores_kit.sha256_archivo(RUTA_CRITERIOS),
    }
    (config.DIR_SALIDA_V2 / "04_pool_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Pool v2: {meta['pares']} pares ({meta['pares_v1']} de v1 y {meta['pares_lote2']} "
          f"nuevos para el lote 2); variantes: {len(usadas)}"
          + ("; se aplicó el tope de 450 (D27)" if meta["tope_450_aplicado"] else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2", action="store_true")
    if ap.parse_args().v2:
        main_v2()
    else:
        main_v1()


def main_v1() -> None:
    ruta_ranking = config.DIR_SALIDA / "ranking.csv"
    ranking = pd.read_csv(ruta_ranking, dtype=str, keep_default_na=False)
    cons = consultas.cargar_v1()
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "doc_id", "fecha", "texto", "texto_sha256"])

    nuevo = pool.formatear_pool(pool.construir_pool(ranking, pasajes, cons))
    nuevo_texto = pool.como_texto(nuevo)

    if RUTA_POOL.exists():
        dif = pool.diferencias_pool(pool.leer_pool(RUTA_POOL), nuevo_texto)
        if not dif:
            print(f"El pool no cambió ({len(nuevo)} pares); no se reescribe.")
            return
        if hay_juicios():
            print("ALTO: el pool cambió y ya hay juicios en anotaciones/juicios_relevancia.csv.",
                  "No se sobrescribe nada. Ver skill integridad-congelacion (tabla de "
                  "invalidación) antes de seguir. Diferencias:", *dif[:50], sep="\n- ")
            sys.exit(1)
        print(f"El pool cambió ({len(dif)} diferencias) y aún no hay juicios: se reescribe.")

    config.DIR_SALIDA.mkdir(exist_ok=True)
    nuevo.to_csv(RUTA_POOL, index=False, encoding="utf-8")
    resumen = pool.resumen_pool(nuevo.assign(en_ventana=nuevo["en_ventana"].astype(bool)))
    resumen.to_csv(config.DIR_SALIDA / "04_pool_resumen.csv", index=False)

    meta = {
        "construido": datetime.now().isoformat(timespec="seconds"),
        "pares": len(nuevo), "pasajes_distintos": int(nuevo["passage_id"].nunique()),
        "por_consulta": dict(zip(resumen["query_id"], resumen["pasajes"].astype(int))),
        "fuera_de_rango_15_40": resumen.loc[resumen["fuera_de_rango_esperado"] == 1,
                                            "query_id"].tolist(),
        "semilla_orden": config.SEMILLA,
        "sha256_pool": pool.hash_pool(pool.leer_pool(RUTA_POOL)),
        "sha256_pool_csv": adaptadores_kit.sha256_archivo(RUTA_POOL),
        "sha256_ranking_csv": adaptadores_kit.sha256_archivo(ruta_ranking),
        "sha256_consultas_csv": adaptadores_kit.sha256_archivo(config.CONSULTAS_CSV),
        "sha256_indice_meta": adaptadores_kit.sha256_archivo(config.INDICE_META),
        "sha256_criterios_relevancia": (adaptadores_kit.sha256_archivo(RUTA_CRITERIOS)
                                        if RUTA_CRITERIOS.exists() else None),
    }
    (config.DIR_SALIDA / "04_pool_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Pool: {meta['pares']} pares (consulta, pasaje), {meta['pasajes_distintos']} pasajes "
          f"distintos; por consulta: {meta['por_consulta']}")
    if meta["fuera_de_rango_15_40"]:
        print(f"AVISO: fuera del rango esperado de 15 a 40: {meta['fuera_de_rango_15_40']}")
    if meta["sha256_criterios_relevancia"] is None:
        print("Pendiente (alumno): config/criterios_relevancia.md antes del primer juicio.")


if __name__ == "__main__":
    main()
