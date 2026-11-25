"""03b · Booleano exploratorio (PRD v2 D30, WP-07, `make booleano`).

AND y OR sobre el índice stem para las 15 consultas, con su ventana de fechas. Escribe
`salida/v2/03b_booleano.csv` y `salida/v2/03b_ejemplo_huachicol.md`. Solo cuenta pasajes: no
lista ninguno ni lee anotaciones (D32).
"""
from __future__ import annotations

import sys

import pandas as pd

from mtx import booleano as B
from mtx import config
from mtx import indice as I
from mtx import ranking as RK

SALIDA = config.DIR_SALIDA_V2
EJEMPLO = {"query_id": "Q6", "raro": "huachicol", "comun": "robo", "nombre": "Huachicol"}


def main() -> int:
    r = RK.rutas_indice("stem")
    ids, toks = I.cargar_tokens(r["tokens"])
    ind = I.cargar(r["pkl"], r["meta"], I.hash_tokens(ids, toks))
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "doc_id", "posicion",
                                                           "fecha"])
    if list(pas["passage_id"]) != ind.ids:
        print("data/pasajes.parquet no sigue el orden del índice: corre `make indice`.",
              file=sys.stderr)
        return 1
    fechas = pas["fecha"].to_numpy(dtype="datetime64[ns]")
    cons = pd.read_csv(config.CONSULTAS_CSV, dtype=str, keep_default_na=False)
    tabla = B.por_consulta(ind, fechas, cons)
    SALIDA.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(SALIDA / "03b_booleano.csv", index=False, lineterminator="\n")
    q = cons.set_index("query_id").loc[EJEMPLO["query_id"]]
    e = B.ejemplo(ind, fechas, q["consulta"], q["desde"], q["hasta"], EJEMPLO["raro"],
                  EJEMPLO["comun"], pas["doc_id"].to_numpy(dtype="int64"),
                  pas["posicion"].to_numpy(dtype="int64"))
    (SALIDA / "03b_ejemplo_huachicol.md").write_text(B.markdown_ejemplo(e, EJEMPLO["nombre"]),
                                                     encoding="utf-8")
    vacias = tabla[(tabla["operador"] == "AND") & (tabla["en_ventana"] == 0)]
    print(f"salida/v2/03b_booleano.csv: {len(cons)} consultas × AND/OR; AND vacío en la ventana "
          f"en {len(vacias)}. Ejemplo en salida/v2/03b_ejemplo_huachicol.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
