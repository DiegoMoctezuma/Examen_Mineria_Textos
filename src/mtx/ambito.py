"""Ámbito de la IE (PRD §6.8, D08): pares (consulta, pasaje) del top-10 con filtro del mejor
modelo de IR, fijado en `data/mejor_modelo.json`."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from mtx import config


def mejor_modelo(ruta: Path = config.DIR_DATA / "mejor_modelo.json") -> str:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))["modelo"]


def ambito_ie(ranking: Path = config.DIR_SALIDA / "ranking.csv",
              ruta_mejor: Path = config.DIR_DATA / "mejor_modelo.json") -> pd.DataFrame:
    """`query_id, passage_id, doc_id, rango` del top-10 del mejor modelo, ordenado."""
    modelo = mejor_modelo(ruta_mejor)
    rk = pd.read_csv(ranking, dtype={"passage_id": str})
    sel = rk[rk["modelo"] == modelo][["query_id", "passage_id", "doc_id", "rango"]]
    if sel.empty:
        raise ValueError(f"El ranking no tiene filas de {modelo}")
    return sel.reset_index(drop=True)
