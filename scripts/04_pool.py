"""04 · Pool de relevancia (PRD §6.5, D06). `make pool`.

Entradas: ranking.csv (salida/), data/pasajes.parquet y data/consultas.csv.
Salidas: salida/04_pool.csv, salida/04_pool_resumen.csv y salida/04_pool_meta.json.

Si el pool ya existe, se reconstruye en memoria y se compara. Si cambió y ya hay juicios en
anotaciones/juicios_relevancia.csv, se detiene sin sobrescribir nada y enumera las diferencias.
Nunca escribe en anotaciones/.
"""
from __future__ import annotations

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


def main() -> None:
    ruta_ranking = config.DIR_SALIDA / "ranking.csv"
    ranking = pd.read_csv(ruta_ranking, dtype=str, keep_default_na=False)
    cons = consultas.cargar()
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
