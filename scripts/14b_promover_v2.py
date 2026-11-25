"""14b · Promoción de los seis CSV v2 a la raíz (PRD v2 D28, WP-14, `make promover-v2`).

Copia byte a byte `salida/v2/{ranking, juicios_relevancia, resultados_ir, entidades,
gold_entidades, resultados_ie}.csv` a la raíz y registra sus sha256 en
`salida/v2/promocion_raiz.json`. Exige los dos cierres v2 y las salidas de `make all-v2`. Los CSV
de v1 siguen en `salida/` y `anotaciones/`, y en la etiqueta `v1.0-entrega`.
"""
from __future__ import annotations

import sys

from mtx import promocion


def main() -> int:
    inf = promocion.promover()
    if not inf.ok:
        print("No se promueve:", *inf.errores, sep="\n- ", file=sys.stderr)
        return 1
    cambio = ", ".join(inf.copiados) if inf.copiados else "ninguno (la raíz ya era v2)"
    print(f"Raíz con los seis CSV v2. Copiados: {cambio}. Registro: salida/v2/promocion_raiz.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
