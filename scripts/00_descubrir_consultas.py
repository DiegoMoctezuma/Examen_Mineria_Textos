"""00 · Candidatos para Q9 y Q10 (PRD §5.2). `make explorar`.

Requiere `data/pasajes.parquet` (`make corpus`). Escribe `salida/00_candidatos_q9q10.md`.
No elige consultas ni modifica `data/consultas.csv`.

`--v2` (PRD v2 D25, WP-04): candidatos para Q11 a Q15 desde `config/v2/candidatos_q11q15.yaml` en
`salida/v2/00_candidatos_q11q15.md`. Los ejemplos son al azar (semilla 42) y nunca pasajes de las
muestras del gold v1 o v2, para que nadie que anota vea rankings ni sus pasajes (D32).
"""
from __future__ import annotations

import argparse

import pandas as pd

from mtx import adaptadores_kit, config, descubrimiento


def excluir_gold() -> frozenset[str]:
    """Pasajes de todas las muestras del gold (v1 y v2) ya sorteadas."""
    rutas = [config.RAIZ / "anotaciones" / "muestra_gold.csv",
             *sorted((config.RAIZ / "anotaciones" / "v2").glob("muestra_*.csv"))]
    return frozenset(pid for r in rutas if r.exists()
                     for pid in pd.read_csv(r, dtype=str)["passage_id"])


def main_v2() -> None:
    pasajes = pd.read_parquet(config.PASAJES_PARQUET)
    norm = descubrimiento.cuerpo_normalizado(pasajes)
    cands = config.cargar_yaml("v2/candidatos_q11q15.yaml")["candidatos"]
    excl = excluir_gold()
    res = [descubrimiento.analizar_candidato(pasajes, norm, c, excluir=excl, semilla=42)
           for c in cands]
    actuales = pd.read_csv(config.CONSULTAS_CSV, dtype=str, keep_default_na=False)
    config.DIR_SALIDA_V2.mkdir(parents=True, exist_ok=True)
    ruta = config.DIR_SALIDA_V2 / "00_candidatos_q11q15.md"
    ruta.write_text(descubrimiento.a_markdown(res, actuales.head(10), "Candidatos para Q11 a Q15",
                                              al_azar=True), encoding="utf-8")
    print(f"Escrito {ruta.relative_to(config.RAIZ)} ({len(cands)} candidatos, "
          f"{len(excl)} pasajes del gold fuera de los ejemplos)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2", action="store_true")
    v2 = ap.parse_args().v2
    if not config.PASAJES_PARQUET.exists():
        raise SystemExit("Falta data/pasajes.parquet: corre primero `make corpus`.")
    if v2:
        return main_v2()
    pasajes = pd.read_parquet(config.PASAJES_PARQUET)
    norm = descubrimiento.cuerpo_normalizado(pasajes)
    cands = config.cargar_yaml("candidatos_q9q10.yaml")["candidatos"]
    resultados = [descubrimiento.analizar_candidato(pasajes, norm, c) for c in cands]
    obligatorias = pd.read_csv(adaptadores_kit.DIR_KIT / "consultas.csv")
    config.DIR_SALIDA.mkdir(exist_ok=True)
    ruta = config.DIR_SALIDA / "00_candidatos_q9q10.md"
    ruta.write_text(descubrimiento.a_markdown(resultados, obligatorias), encoding="utf-8")
    print(f"Escrito {ruta.relative_to(config.RAIZ)}")


if __name__ == "__main__":
    main()
