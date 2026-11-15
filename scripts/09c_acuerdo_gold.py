"""09c · Acuerdo entre anotadores del gold v2, el techo humano (PRD v2 D31, D35). `make acuerdo-gold`.

F1 exacto (tipo e intervalo) entre los dos anotadores de cada parte, antes de adjudicar, por
pasada y tipo, con una fila `micro` por parte y la parte `todas`. Solo entra una parte y pasada
cuando las dos personas cerraron todos sus pasajes; las demás se listan como pendientes. Escribe
`salida/v2/09_acuerdo_gold.csv`. No imprime entidades ni textos, solo conteos.
"""
from __future__ import annotations

import sys

from mtx import config
from mtx import gold_v2 as V


def main() -> int:
    tabla, pendientes = V.acuerdo(V.cargar_config())
    destino = config.DIR_SALIDA / "v2" / "09_acuerdo_gold.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(destino, index=False, lineterminator="\n")
    print(f"{destino.relative_to(config.RAIZ)}: {len(tabla)} filas")
    for p in pendientes:
        print(f"- pendiente: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
