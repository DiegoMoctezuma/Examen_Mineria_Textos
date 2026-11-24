"""09d · Cierres humanos de v2 (PRD v2 §4, D24, D31 a D34). Lo corre el coordinador.

    make revisar-cierres-v2          # solo revisa los dos cierres; no escribe nada
    make cierre-juicios-v2           # escribe anotaciones/cierre_juicios_v2.json
    make cierre-gold-v2              # escribe anotaciones/gold_v2/adjudicado.csv y cierre_gold_v2.json

Antes de cerrar hay que integrar en `proyecto-final` todas las ramas `anotacion/<id>` y
commitearlas: el cierre guarda el commit y los hashes de cada archivo, y se niega a cerrar con
cambios sin commitear. Ningún cierre se reescribe. Imprime solo conteos e IDs, nunca valores de
juicio ni entidades. Después de cerrar, haz commit de los archivos escritos (`data(cierre): ...`).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys

import pandas as pd

from mtx import anotadores as A
from mtx import cierres_v2 as K
from mtx import config
from mtx import gold_v2 as V

RUTA_CRITERIOS_REL = config.DIR_CONFIG / "criterios_relevancia.md"
RUTA_CRITERIOS_IE = config.DIR_CONFIG / "criterios_anotacion.md"
RUTA_META_POOL = config.DIR_SALIDA / "v2" / "04_pool_meta.json"


def _pasajes() -> pd.DataFrame:
    return pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto", "texto_sha256"])


def _exclusion_v1() -> set[str]:
    """Ámbito IE de v1 y gold v1, leídos de `v1.0-entrega` como en el sorteo (08b)."""
    ruta = config.RAIZ / "scripts" / "08b_muestra_gold.py"
    spec = importlib.util.spec_from_file_location("muestra_gold_08b", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.exclusion_v1()[0]


def _agrupar(errores: list[str]) -> list[str]:
    """«Parte A, pasada 1: 277_0 sin adjudicar» × n → una línea por parte y pasada."""
    out, sin_adj = [], {}
    for e in errores:
        m = re.fullmatch(r"(.+, pasada \d): \S+ sin adjudicar", e)
        if m:
            if m.group(1) not in sin_adj:
                out.append(m.group(1))
            sin_adj[m.group(1)] = sin_adj.get(m.group(1), 0) + 1
        else:
            out.append(e)
    return [f"{e}: {sin_adj[e]} pasajes sin adjudicar" if e in sin_adj else e for e in out]


def _imprimir(titulo: str, rev: K.Revision) -> None:
    print(f"\n== {titulo}: {'listo para cerrar' if rev.ok else 'todavía no se puede cerrar'}")
    for e in _agrupar(rev.errores):
        print(f"  ERROR  {e}")
    for a in rev.avisos:
        print(f"  aviso  {a}")


def _resumen_juicios(rev: K.Revision) -> None:
    r = rev.resumen
    print(f"  pares: {r['pares']} (por lote: {r['pares_por_lote']}); con 3 juicios válidos: "
          f"{r['pares_cerrados']}")
    for a, d in r["jueces"].items():
        print(f"  {a:<8} lotes {','.join(d['lotes'])}: {d['juzgados']} de {d['asignados']} "
              "juzgados")


def _resumen_gold(rev: K.Revision) -> None:
    for pid, d in rev.resumen["partes"].items():
        print(f"  {d['nombre']:<10} {d['pasajes']} pasajes; en el gold oficial hasta ahora: "
              f"{d['pasajes_con_entidades']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("que", choices=["juicios", "gold", "revisar"])
    ap.add_argument("--aceptar-incompletos", action="store_true",
                    help="cerrar los juicios aunque haya pares con menos de 3 juicios válidos; "
                         "se listan y la agregación no los cuenta (D24). Regístralo en "
                         "docs/decisiones.md")
    args = ap.parse_args()
    pasajes = _pasajes()
    asig, ruta_asig, ruta_anot = A.leer_asignacion(), A.ruta_asignacion(), A.ruta_anotadores()
    cfg = V.cargar_config()
    ruta_muestreo = V.dir_anotaciones() / "v2" / "muestreo_v2.json"

    if args.que == "revisar":
        rj = K.revisar_juicios_v2(asig, pasajes, aceptar_incompletos=args.aceptar_incompletos)
        _imprimir("Juicios v2" + (" (ya cerrados)" if K.juicios_cerrados() else ""), rj)
        _resumen_juicios(rj)
        rg = K.revisar_gold_v2(cfg, pasajes, excluir_v1=_exclusion_v1())
        rg.errores += K.revisar_orden_gold()
        _imprimir("Gold v2" + (" (ya cerrado)" if K.gold_cerrado() else ""), rg)
        _resumen_gold(rg)
        return 0

    try:
        if args.que == "juicios":
            meta = json.loads(RUTA_META_POOL.read_text("utf-8")) if RUTA_META_POOL.exists() \
                else None
            c = K.cerrar_juicios_v2(asig, pasajes, ruta_asig, ruta_anot, RUTA_CRITERIOS_REL,
                                    meta, aceptar_incompletos=args.aceptar_incompletos)
            print(f"{K.ruta_cierre_juicios().relative_to(config.RAIZ)}: {c['pares_cerrados']} "
                  f"de {c['pares']} pares cerrados, commit {c['commit'][:7]}")
        else:
            c = K.cerrar_gold_v2(cfg, pasajes, ruta_anot, RUTA_CRITERIOS_IE, ruta_muestreo,
                                 excluir_v1=_exclusion_v1())
            print(f"{K.ruta_cierre_gold().relative_to(config.RAIZ)} y "
                  f"{K.ruta_adjudicado().relative_to(config.RAIZ)}: {c['entidades']} entidades, "
                  f"commit {c['commit'][:7]}")
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    for a in c["avisos"]:
        print(f"  aviso  {a}")
    print("Haz commit de los archivos escritos antes de seguir (data(cierre): ...).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
