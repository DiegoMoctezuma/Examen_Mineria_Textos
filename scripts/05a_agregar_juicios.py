"""05a · Agregación y acuerdo de los juicios v2 (PRD v2 D24, WP-02). `make agregar-juicios`.

Corre después de `make cierre-juicios-v2` y se niega si la asignación o algún archivo de juicios
cambió desde el cierre. Mayoría de 3 juicios válidos (≥ 2 = relevante); un par con menos de 3
no se cierra y no se exporta. Escribe:

- `salida/v2/05a_juicios_agregados.csv`: un renglón por par con votos, relevante y unanimidad;
- `salida/v2/juicios_relevancia.csv`: las 4 columnas que lee el kit, solo pares cerrados, validado
  con `validar_juicios()`; nunca se edita a mano;
- `salida/v2/05a_acuerdo.csv` y `.json`: Fleiss global, por lote y por consulta, y Cohen por
  pareja. Es para el reporte, no para descartar a nadie.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import pandas as pd

from mtx import acuerdo as K
from mtx import anotadores as A
from mtx import cierres_v2 as Z
from mtx import config, pool
from mtx import gold_v2 as V
from mtx.app import componentes as C

SALIDA_V2 = config.DIR_SALIDA / "v2"
RUTA_AGREGADOS = SALIDA_V2 / "05a_juicios_agregados.csv"
RUTA_KIT = SALIDA_V2 / "juicios_relevancia.csv"
RUTA_ACUERDO = SALIDA_V2 / "05a_acuerdo.csv"
RUTA_ACUERDO_JSON = SALIDA_V2 / "05a_acuerdo.json"


def main() -> int:
    dir_anot = V.dir_anotaciones()
    ruta_cierre = Z.ruta_cierre_juicios(dir_anot)
    cierre = json.loads(ruta_cierre.read_text("utf-8")) if ruta_cierre.exists() else None
    ruta_asig = A.ruta_asignacion()
    errores = K.verificar_cierre(cierre, ruta_asig, dir_anot)
    if errores:
        print("No se agrega:", *errores, sep="\n- ", file=sys.stderr)
        return 1
    asig = A.leer_asignacion(ruta_asig)
    lar = K.largo(asig, dir_anot)
    agr = K.agregar(asig, lar)
    tabla = K.acuerdo(agr, lar)

    SALIDA_V2.mkdir(parents=True, exist_ok=True)
    agr.to_csv(RUTA_AGREGADOS, index=False, lineterminator="\n")
    K.exportar_kit(agr).to_csv(RUTA_KIT, index=False, lineterminator="\n")
    pasajes = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto"])
    v = pool.validar_juicios(RUTA_KIT, K.pool_de(asig, agr), pasajes)
    if v.errores:
        RUTA_KIT.unlink()
        print("La exportación no pasa validar_juicios(); no se escribe:", *v.errores,
              sep="\n- ", file=sys.stderr)
        return 1
    tabla.to_csv(RUTA_ACUERDO, index=False, lineterminator="\n")

    cerr = agr[agr["cerrado"]]
    glob = tabla[tabla["ambito"] == "global"].iloc[0]
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "cierre": {"commit": cierre.get("commit"), "fecha": cierre.get("fecha"),
                   "sha256": C.sha256_ruta(ruta_cierre)},
        "regla": "relevante = al menos 2 de 3 juicios válidos; omitidos no cuentan (D24)",
        "pares": len(agr), "pares_cerrados": len(cerr),
        "pares_sin_cerrar": agr[~agr["cerrado"]][["query_id", "passage_id"]].values.tolist(),
        "relevantes": int((cerr["relevante"] == "1").sum()),
        "unanimes": int(cerr["unanime"].sum()),
        "fleiss_global": {"pares": int(glob["pares"]),
                          "acuerdo_observado": float(glob["acuerdo_observado"]),
                          "kappa": float(glob["kappa"])},
        "fleiss_por_lote": {r.clave: {"jueces": r.jueces, "pares": int(r.pares),
                                      "kappa": float(r.kappa)}
                            for r in tabla[tabla["ambito"] == "lote"].itertuples()},
        "cohen_por_pareja": {r.clave: {"pares": int(r.pares), "kappa": float(r.kappa)}
                             for r in tabla[tabla["ambito"] == "pareja"].itertuples()},
        "avisos": v.avisos,
        "sha256": {p.name: C.sha256_ruta(p) for p in (RUTA_AGREGADOS, RUTA_KIT, RUTA_ACUERDO)},
    }
    RUTA_ACUERDO_JSON.write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=float)
                                 + "\n", encoding="utf-8")

    print(f"{len(cerr)} de {len(agr)} pares cerrados; {resumen['relevantes']} relevantes; "
          f"{resumen['unanimes']} unánimes")
    print(f"Fleiss global: {glob['kappa']} (acuerdo observado {glob['acuerdo_observado']})")
    for r in tabla[tabla["ambito"].isin(["lote", "pareja"])].itertuples():
        print(f"  {r.metrica:<6} {r.ambito} {r.clave:<16} κ {r.kappa}  ({int(r.pares)} pares)")
    for a in v.avisos:
        print(f"  aviso  {a}")
    print("Escritos:", *(str(p.relative_to(config.RAIZ)) for p in
                         (RUTA_AGREGADOS, RUTA_KIT, RUTA_ACUERDO, RUTA_ACUERDO_JSON)), sep="\n- ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
