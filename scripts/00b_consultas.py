"""00b · Escribe data/consultas.csv = kit + Q9 + Q10 desde config/consultas_q9q10.yaml. `make consultas`.

`--v2` (PRD v2 D25, WP-04, `make consultas-v2`): agrega Q11 a Q15 de
`config/v2/consultas_q11q15.yaml` (redacción de Diego y Arturo, `[VALIDAR]`). Exige que Q1 a Q10
queden idénticas a las de v1, carácter por carácter.
"""
from __future__ import annotations

import argparse

from mtx import config, consultas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2", action="store_true")
    v2 = ap.parse_args().v2
    cfg = config.cargar_yaml("consultas_q9q10.yaml")
    extra = list(cfg["consultas"])
    if v2:
        cfg2 = config.cargar_yaml("v2/consultas_q11q15.yaml")
        if not str(cfg2.get("estado", "")).startswith("aprobadas"):
            raise SystemExit("config/v2/consultas_q11q15.yaml no está aprobado (campo `estado`)")
        if [c["query_id"] for c in cfg2["consultas"]] != [f"Q{i}" for i in range(11, 16)]:
            raise SystemExit("Se esperan exactamente Q11 a Q15, en orden")
        extra += cfg2["consultas"]
    df = consultas.construir(extra)
    if v2:
        v1 = consultas.construir(cfg["consultas"])
        if not df.head(len(v1)).equals(v1):
            raise SystemExit("Q1 a Q10 cambiarían: no se escribe nada")
    config.DIR_DATA.mkdir(exist_ok=True)
    df.to_csv(config.CONSULTAS_CSV, index=False, encoding="utf-8")
    print(f"{len(df)} consultas en {config.CONSULTAS_CSV.relative_to(config.RAIZ)}; "
          f"estado de Q9 y Q10: {cfg['estado']}" + (f"; Q11 a Q15: {cfg2['estado']}" if v2 else ""))


if __name__ == "__main__":
    main()
