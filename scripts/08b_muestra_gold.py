"""08b · Sorteo de la muestra gold y del conjunto de selección (PRD §6.11, D10, U13). `make muestra-gold`.

Requisitos: etiqueta `reglas-congeladas` (D15) y `data/mejor_modelo.json`. Escribe
`anotaciones/muestra_gold.csv` (20 pasajes, 2 por consulta) y, con `--seleccion`,
`anotaciones/muestra_seleccion.csv` (6 pasajes, P1, solo si se comparan modelos NER). Si un
manifiesto ya existe y el sorteo daría otro, se detiene sin sobrescribir. Registra en
`salida/08b_excluidos_muestra.csv` los pasajes excluidos por criterio objetivo (U13) y en
`salida/08b_resumen_muestra.json` los conteos. No imprime textos ni predicciones.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

import pandas as pd

from mtx import ambito, config, muestreo
from mtx.app import componentes as C

ANOT = config.DIR_ANOTACIONES


def _escribir(df: pd.DataFrame, ruta) -> str:
    """'escrito', 'sin cambios' o 'distinto' (no se sobrescribe)."""
    nuevo = df.to_csv(index=False, lineterminator="\n").encode("utf-8")
    if ruta.exists():
        return "sin cambios" if ruta.read_bytes() == nuevo else "distinto"
    C.escribir_atomico(ruta, nuevo, respaldo=False)
    return "escrito"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seleccion", action="store_true",
                    help="escribe también el conjunto de selección (P1)")
    a = ap.parse_args(argv)
    if not C.reglas_congeladas():
        print("Falta la etiqueta `reglas-congeladas` (D15): congela reglas, gazetteers y "
              "criterio con `make congelar` antes de sortear la muestra.")
        return 1
    amb = ambito.ambito_ie()
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "texto", "inicio_cuerpo", "texto_sha256"])
    pasajes = pasajes[pasajes["passage_id"].isin(set(amb["passage_id"]))]
    try:
        m = muestreo.sortear(amb, pasajes)
    except muestreo.MuestraInviable as e:
        print(f"{e}\nRegistra la excepción en docs/decisiones.md antes de seguir.")
        return 1

    estados = {"muestra_gold.csv": _escribir(m.gold, ANOT / "muestra_gold.csv")}
    if a.seleccion:
        estados["muestra_seleccion.csv"] = _escribir(m.seleccion, ANOT / "muestra_seleccion.csv")
    if "distinto" in estados.values():
        print("Un manifiesto existente no coincide con el sorteo; no se sobrescribe. Revisa con "
              "la skill gold-anotacion (sustitución U13 o cambio de insumos).", estados)
        return 1
    m.excluidos.to_csv(config.DIR_SALIDA / "08b_excluidos_muestra.csv", index=False,
                       lineterminator="\n")
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "modelo_ir": ambito.mejor_modelo(), "semilla": config.SEMILLA,
        "universo_pares": len(amb), "universo_pasajes": int(amb["passage_id"].nunique()),
        "excluidos_u13": len(m.excluidos), "gold": len(m.gold),
        "seleccion": len(m.seleccion) if a.seleccion else 0,
        "estratos_rango_1_5_y_6_10": m.estratos_respetados, "avisos": m.avisos,
        "archivos": estados,
    }
    (config.DIR_SALIDA / "08b_resumen_muestra.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
