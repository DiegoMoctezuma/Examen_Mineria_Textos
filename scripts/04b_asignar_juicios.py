"""Asigna un lote de juicios v2 (PRD v2 D24, WP-02): `make asignar-juicios LOTE=1`.

Lee la definición del lote en `config/v2/anotadores.yaml` y su pool, y agrega sus filas a
`data/v2/asignacion_juicios.csv`. Determinista: volver a correrlo no cambia nada; si el lote ya
existe con otras filas, se detiene (la asignación se congela al crearla).
"""
from __future__ import annotations

import argparse

from mtx import anotadores as A
from mtx import config, pool
from mtx.app.componentes import _csv_bytes, escribir_atomico


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lote", required=True)
    args = ap.parse_args()
    lotes = A.cargar_lotes()
    if args.lote not in lotes:
        raise SystemExit(f"El lote {args.lote} no está definido en {A.ruta_anotadores()}")
    d = lotes[args.lote]
    p = pool.leer_pool(config.RAIZ / d["pool"])
    nuevas = A.asignar_lote(p, args.lote, list(d.get("jueces", [])),
                            list(d.get("jueces_v1", [])), A.cargar_anotadores())
    previa = A.leer_asignacion()
    todas = A.agregar_asignacion(previa, nuevas)
    errores = A.validar_asignacion(todas)
    if errores:
        raise SystemExit("\n".join(errores))
    if len(todas) == len(previa):
        print(f"Lote {args.lote} ya asignado: sin cambios ({A.ruta_asignacion()}).")
        return
    escribir_atomico(A.ruta_asignacion(), _csv_bytes(todas), respaldo=False)
    resumen = nuevas.groupby(["anotador", "origen"]).size()
    print(f"Lote {args.lote}: {nuevas['passage_id'].count() // max(1, nuevas['anotador'].nunique())}"
          f" pares → {A.ruta_asignacion()}")
    for (a, o), n in resumen.items():
        print(f"  {a:8s} {o:3s} {n}")


if __name__ == "__main__":
    main()
