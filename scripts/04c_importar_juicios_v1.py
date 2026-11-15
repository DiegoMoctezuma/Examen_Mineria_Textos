"""Importa sin cambios unos juicios v1 completos como juicios v2 de una persona (PRD v2 D24, PV2).

    make importar-juicios ANOTADOR=diego ORIGEN=anotaciones/juicios_relevancia.csv
    make importar-juicios ANOTADOR=luis ORIGEN=/ruta/al/juicios_relevancia.csv

Valida el origen contra el pool v1 (cobertura completa, sin omitidos), comprueba que el
anotador tenga esos pares asignados con `origen = v1` y escribe
`anotaciones/juicios_v2/<anotador>.csv` de forma atómica, con un metadato que guarda el hash del
origen. Nunca cambia un valor ni sobrescribe juicios distintos ya importados.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from mtx import anotadores as A
from mtx import config, pool
from mtx.app import componentes as C


def _ruta_relativa(ruta: Path) -> str:
    """Relativa al repo si está dentro; si no, solo el nombre (no guarda rutas de otra máquina)."""
    try:
        return str(ruta.resolve().relative_to(config.RAIZ))
    except ValueError:
        return ruta.name


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anotador", required=True)
    ap.add_argument("--origen", required=True, type=Path)
    ap.add_argument("--lote", default="1")
    args = ap.parse_args()
    if args.anotador not in A.cargar_anotadores():
        raise SystemExit(f"{args.anotador} no está en {A.ruta_anotadores()}")
    d = A.cargar_lotes()[args.lote]
    ruta_pool = config.RAIZ / d["pool"]
    p = pool.leer_pool(ruta_pool)
    asig = A.pares_de(A.leer_asignacion(), args.anotador, origen="v1")
    asig = asig[asig["lote"] == args.lote]
    if set(zip(asig["query_id"], asig["passage_id"])) != set(zip(p["query_id"], p["passage_id"])):
        raise SystemExit(f"{args.anotador} no tiene el lote {args.lote} asignado como v1; corre "
                         f"`make asignar-juicios LOTE={args.lote}` y revisa anotadores.yaml")
    r = C.rutas(args.anotador)
    j = A.importar_juicios_v1(args.origen, p, r.juicios)
    if r.juicios.exists():
        print(f"{r.juicios} ya tiene estos juicios: sin cambios.")
        return
    C.escribir_atomico(r.juicios, C._csv_bytes(j), respaldo=False)
    meta = {"revision": 1, "sha256": C.sha256_ruta(r.juicios),
            "actualizado": datetime.now().isoformat(timespec="seconds"),
            "origen": "importado_v1", "lote": args.lote,
            "ruta_origen": _ruta_relativa(args.origen), "sha256_origen": C.sha256_ruta(args.origen),
            "sha256_pool_v1": pool.hash_pool(p), "sha256_criterios": C.sha256_ruta(r.criterios)}
    C.escribir_atomico(Path(str(r.juicios) + ".meta.json"),
                       (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
                       respaldo=False)
    print(f"{len(j)} juicios de {args.anotador} importados sin cambios → {r.juicios}")


if __name__ == "__main__":
    main()
