"""Rutas del repositorio, constantes y carga de `config/*.yaml`."""
from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
DIR_CONFIG = RAIZ / "config"
DIR_DATA = RAIZ / "data"
DIR_SALIDA = RAIZ / "salida"
DIR_ANOTACIONES = RAIZ / "anotaciones"

PASAJES_PARQUET = DIR_DATA / "pasajes.parquet"
CORPUS_META = DIR_DATA / "corpus_meta.json"
CONSULTAS_CSV = DIR_DATA / "consultas.csv"
TOKENS_PARQUET = DIR_DATA / "tokens.parquet"
INDICE_PKL = DIR_DATA / "indice.pkl"
INDICE_META = DIR_DATA / "indice_meta.json"
TFIDF_PKL = DIR_DATA / "tfidf.pkl"
TFIDF_NPZ = DIR_DATA / "tfidf_X.npz"

SEMILLA = 42
"""Semilla única del proyecto (muestreo del gold, PRD D10)."""


def cargar_yaml(nombre: str, dir_config: Path = DIR_CONFIG) -> dict:
    """Lee `config/<nombre>` como diccionario."""
    with open(dir_config / nombre, encoding="utf-8") as f:
        return yaml.safe_load(f)
