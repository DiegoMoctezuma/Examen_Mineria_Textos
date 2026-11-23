"""`data/consultas.csv` = filas del kit tal cual + Q9 + Q10 (PRD §3.2, §5.2).

Todos los scripts leen de esa copia, nunca de `kit/consultas.csv`. Q1 a Q8 no se reformulan.
"""
from __future__ import annotations

import pandas as pd

from . import adaptadores_kit, config

COLUMNAS = ["query_id", "consulta", "desde", "hasta", "pregunta_extraccion"]


def construir(extra: list[dict], dir_kit=adaptadores_kit.DIR_KIT) -> pd.DataFrame:
    """Kit + consultas propias. Falla si falta una columna o se repite un `query_id`."""
    kit = pd.read_csv(dir_kit / "consultas.csv", dtype=str, keep_default_na=False)
    propias = pd.DataFrame(extra, columns=COLUMNAS, dtype=str)
    todas = pd.concat([kit, propias], ignore_index=True)
    if todas["query_id"].duplicated().any():
        raise ValueError("query_id repetido: Q9 y Q10 no pueden reusar ids del kit")
    if (todas["desde"] > todas["hasta"]).any():
        raise ValueError("Ventana invertida: desde posterior a hasta")
    return todas


CONSULTAS_V1 = tuple(f"Q{i}" for i in range(1, 11))


def cargar() -> pd.DataFrame:
    """Lee `data/consultas.csv`: Q1 a Q10 y, desde WP-04 de v2, también Q11 a Q15."""
    return pd.read_csv(config.CONSULTAS_CSV, dtype=str, keep_default_na=False)


def solo_v1(cons: pd.DataFrame) -> pd.DataFrame:
    """Q1 a Q10, las consultas de v1. Los caminos v1 (ranking, pool, evaluación y entrega v1) las
    usan para que agregar Q11 a Q15 no reescriba ni invalide ningún artefacto v1."""
    return cons[cons["query_id"].isin(CONSULTAS_V1)].reset_index(drop=True)


def cargar_v1() -> pd.DataFrame:
    return solo_v1(cargar())
