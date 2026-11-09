"""06 · Reglas y gazetteers (PRD §6.7). `make reglas`.

1. Construye `config/gazetteer_extendido.csv` (kit + `config/gazetteer_manual.csv` + siglas que el
   alumno aceptó en la pestaña Gazetteer, `anotaciones/revision_siglas.csv`). Tras la etiqueta
   `reglas-congeladas` se niega a cambiarlo.
2. Mina siglas candidatas en el cuerpo de todos los pasajes → `salida/06_siglas_candidatas.csv`.
3. Aplica `extraer_reglas` a los pasajes únicos del top-10 con filtro del mejor modelo (ámbito de
   la IE, PRD §6.8) y escribe `salida/06_entidades_reglas.csv`, `salida/cantidades_auxiliares.csv`,
   `salida/06_colisiones_reglas.csv` y `salida/06_resumen_reglas.json`.

Las entidades por reglas no se muestran en la app mientras el gold esté abierto (modo ciego).
"""
from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd

from mtx import ambito as mod_ambito
from mtx import config, reglas

SALIDA = config.DIR_SALIDA
COLUMNAS_ENT = ["passage_id", "tipo", "texto", "inicio", "fin", "fuente", "en_marca"]


def congeladas() -> bool:
    r = subprocess.run(["git", "tag", "-l", "reglas-congeladas"], cwd=config.RAIZ,
                       capture_output=True, text=True, check=False)
    return bool(r.stdout.strip())


def main() -> int:
    nuevo = reglas.construir_extendido()
    actual = (pd.read_csv(reglas.GAZ_EXTENDIDO, dtype=str, keep_default_na=False)
              if reglas.GAZ_EXTENDIDO.exists() else None)
    if actual is None or not actual.equals(nuevo):
        if congeladas():
            print("El gazetteer extendido cambiaría y ya existe `reglas-congeladas`: no se "
                  "sobrescribe. Ver la skill integridad-congelacion (cambio exploratorio, D15).")
            return 1
        reglas.escribir_csv(nuevo, reglas.GAZ_EXTENDIDO)
        print(f"config/gazetteer_extendido.csv: {len(nuevo)} entradas")
    reglas.gazetteer_por_defecto.cache_clear()
    gaz, tipos_loc = reglas.gazetteer_por_defecto()

    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "texto", "inicio_cuerpo"])
    siglas = reglas.minar_siglas(pasajes, gaz)
    reglas.escribir_csv(siglas, SALIDA / "06_siglas_candidatas.csv")

    amb = mod_ambito.ambito_ie()[["query_id", "passage_id"]]
    unicos = pasajes[pasajes["passage_id"].isin(set(amb["passage_id"]))]
    ent, aux, col = [], [], []
    for pid, texto, ic in zip(unicos["passage_id"], unicos["texto"], unicos["inicio_cuerpo"]):
        det = reglas.extraer_reglas_detalle(texto, int(ic), (gaz, tipos_loc))
        ent += [{"passage_id": pid, "tipo": e.tipo, "texto": e.texto, "inicio": e.inicio,
                 "fin": e.fin, "fuente": e.fuente, "en_marca": e.en_marca}
                for e in det.entidades]
        aux += [{"passage_id": pid, "texto": a.texto, "inicio": a.inicio, "fin": a.fin,
                 "tipo_aux": a.tipo_aux, "valor_num": a.valor_num, "unidad": a.unidad,
                 "estado_normalizacion": a.estado_normalizacion, "regla_id": a.regla_id}
                for a in det.auxiliares]
        col += reglas.filas_colisiones(pid, det.colisiones)
    ent_df = pd.DataFrame(ent, columns=COLUMNAS_ENT).sort_values(["passage_id", "inicio"])
    aux_df = amb.merge(pd.DataFrame(aux, columns=[c for c in reglas.COLUMNAS_AUX
                                                  if c != "query_id"]), on="passage_id")
    aux_df = aux_df[reglas.COLUMNAS_AUX].sort_values(["query_id", "passage_id", "inicio"])
    col_df = pd.DataFrame(col, columns=reglas.COLUMNAS_COLISIONES)
    reglas.escribir_csv(ent_df, SALIDA / "06_entidades_reglas.csv")
    reglas.escribir_csv(aux_df, SALIDA / "cantidades_auxiliares.csv")
    reglas.escribir_csv(col_df, SALIDA / "06_colisiones_reglas.csv")

    resumen = {
        "ambito": {"pares_consulta_pasaje": len(amb), "pasajes_unicos": len(unicos)},
        "gazetteer": {"origen": nuevo["origen"].value_counts().to_dict(),
                      "etiqueta": nuevo["etiqueta"].value_counts().to_dict(),
                      "loc": len(reglas.leer_gazetteer(reglas.GAZ_LOC)),
                      "siglas_candidatas": len(siglas)},
        "entidades_por_tipo": ent_df["tipo"].value_counts().to_dict(),
        "entidades_por_fuente": ent_df["fuente"].value_counts().to_dict(),
        "entidades_en_marca": int(ent_df["en_marca"].sum()),
        "auxiliares": aux_df["tipo_aux"].value_counts().to_dict(),
        "colisiones": col_df["motivo"].value_counts().to_dict(),
    }
    (SALIDA / "06_resumen_reglas.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
