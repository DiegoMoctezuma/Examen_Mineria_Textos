"""99 · Condiciones de entrega (PRD §13.2). `make validar`.

Imprime las 15 condiciones con estado y causa. Si los juicios pasan la validación, los copia a la
raíz (condición 4); no escribe nada más.

Opciones:
  --parcial       solo FALLA bloquea (PENDIENTE de hitos futuros no); útil antes de H9.
  --sin-pruebas   no corre pytest (condición 13 queda PENDIENTE).
  --solo 1,4,5    corre solo esas condiciones.
"""
from __future__ import annotations

import argparse
import sys

from mtx import entrega, evaluacion

ICONO = {entrega.OK: "✔", entrega.PENDIENTE: "…", entrega.FALLA: "✘", entrega.AVISO: "!"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parcial", action="store_true")
    ap.add_argument("--sin-pruebas", action="store_true")
    ap.add_argument("--solo", type=lambda s: {int(x) for x in s.split(",")})
    a = ap.parse_args(argv)

    cx = entrega.Contexto(evaluacion.rutas_ir(), correr_pruebas=not a.sin_pruebas)
    resultados = entrega.validar(cx, a.solo)
    for r in resultados:
        print(f"{ICONO[r.estado]} {r.numero:>2}. [{r.estado}] {r.titulo}")
        for d in r.detalle:
            print(f"       - {d}")
    conteo = {e: sum(r.estado == e for r in resultados) for e in ICONO}
    print("\n" + ", ".join(f"{n} {e}" for e, n in conteo.items() if n))
    codigo = entrega.codigo_salida(resultados, a.parcial)
    if codigo:
        print("La entrega aún no está lista." if not a.parcial else
              "Hay condiciones en FALLA.")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
