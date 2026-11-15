"""Juicios v2 con varios anotadores (PRD v2 D24, WP-01 y WP-02).

- Lista cerrada de anotadores y definición de lotes en `config/v2/anotadores.yaml`.
- Un archivo de juicios por persona: `anotaciones/juicios_v2/<anotador>.csv`, con las mismas
  cuatro columnas que v1 (`query_id,doc_id,passage_id,relevante`). Quién juzgó lo dice el nombre
  del archivo; cuándo, el historial `anotaciones/juicios_v2/<anotador>_historial.csv`.
- Asignación determinista y de solo agregar en `data/v2/asignacion_juicios.csv`: qué pares juzga
  cada quien, en qué orden y con qué huella de texto. `origen = app` se juzga en la app;
  `origen = v1` es un juicio de v1 importado sin cambios (Diego y Luis en el lote 1), que la app no
  muestra ni deja editar.

Ninguna función de este módulo produce, sugiere ni modifica valores de juicio: lee, valida y
copia lo que escribieron las personas.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from mtx import config, pool

DIR_V2_CONFIG = config.DIR_CONFIG / "v2"
DIR_V2_DATA = config.DIR_DATA / "v2"
SUBDIR_JUICIOS = "juicios_v2"
COLUMNAS_ASIGNACION = ["lote", "anotador", "origen", "orden", "query_id", "doc_id", "passage_id",
                       "texto_sha256"]
ORIGENES = ("app", "v1")


@dataclass(frozen=True)
class Anotador:
    id: str
    nombre: str
    coordinador: bool = False


def ruta_anotadores() -> Path:
    return Path(os.environ.get("MTX_ANOTADORES", DIR_V2_CONFIG / "anotadores.yaml"))


def ruta_asignacion() -> Path:
    return Path(os.environ.get("MTX_ASIGNACION", DIR_V2_DATA / "asignacion_juicios.csv"))


def _yaml(ruta: Path | None = None) -> dict:
    ruta = ruta or ruta_anotadores()
    return config.cargar_yaml(ruta.name, ruta.parent)


def cargar_anotadores(ruta: Path | None = None) -> dict[str, Anotador]:
    """Anotadores en el orden del YAML. `ValueError` si hay ids repetidos o mal formados."""
    datos = _yaml(ruta)
    out: dict[str, Anotador] = {}
    for a in datos["anotadores"]:
        i = str(a["id"])
        if not i.isascii() or not i.isidentifier() or i != i.lower():
            raise ValueError(f"id de anotador inválido: {i!r} (minúsculas ASCII, sin espacios)")
        if i in out:
            raise ValueError(f"id de anotador repetido: {i}")
        out[i] = Anotador(i, str(a["nombre"]), bool(a.get("coordinador", False)))
    return out


def cargar_lotes(ruta: Path | None = None) -> dict[str, dict]:
    return {str(k): v for k, v in (_yaml(ruta).get("lotes") or {}).items()}


def ruta_juicios(dir_anotaciones: Path, anotador: str) -> Path:
    return Path(dir_anotaciones) / SUBDIR_JUICIOS / f"{anotador}.csv"


def ruta_historial(dir_anotaciones: Path, anotador: str) -> Path:
    return Path(dir_anotaciones) / SUBDIR_JUICIOS / f"{anotador}_historial.csv"


# --------------------------------------------------------------------------- asignación


def leer_asignacion(ruta: Path | None = None) -> pd.DataFrame:
    ruta = ruta or ruta_asignacion()
    if not Path(ruta).exists():
        return pd.DataFrame(columns=COLUMNAS_ASIGNACION, dtype=str)
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)[COLUMNAS_ASIGNACION]


def asignar_lote(pool_csv: pd.DataFrame, lote: str, jueces_app: list[str],
                 jueces_v1: list[str], anotadores: dict[str, Anotador]) -> pd.DataFrame:
    """Filas de asignación de un lote: cada par del pool lo juzga cada juez del lote.

    Con 3 jueces por par y lotes definidos por persona (D24), todos los jueces de un lote ven
    todos sus pares, así que no hay sorteo de quién juzga qué. El orden de presentación es el del
    pool, que ya es una permutación con semilla 42 por consulta y no revela rangos.
    """
    desconocidos = sorted(set(jueces_app + jueces_v1) - set(anotadores))
    if desconocidos:
        raise ValueError(f"Jueces que no están en anotadores.yaml: {desconocidos}")
    if set(jueces_app) & set(jueces_v1):
        raise ValueError("Un juez no puede estar a la vez en `jueces` y `jueces_v1` del lote")
    filas = []
    for origen, jueces in (("v1", jueces_v1), ("app", jueces_app)):
        for a in jueces:
            for orden, p in enumerate(pool_csv.itertuples(index=False)):
                filas.append({"lote": str(lote), "anotador": a, "origen": origen,
                              "orden": str(orden), "query_id": p.query_id,
                              "doc_id": str(p.doc_id), "passage_id": p.passage_id,
                              "texto_sha256": p.texto_sha256})
    return pd.DataFrame(filas, columns=COLUMNAS_ASIGNACION)


def agregar_asignacion(existente: pd.DataFrame, nuevas: pd.DataFrame) -> pd.DataFrame:
    """Une sin modificar lo ya asignado. Volver a correr el mismo lote no cambia nada; si el lote
    ya existe con otras filas, `ValueError` (la asignación de un lote se congela al crearla)."""
    for lote in nuevas["lote"].unique():
        previo = existente[existente["lote"] == lote].reset_index(drop=True)
        nuevo = nuevas[nuevas["lote"] == lote].reset_index(drop=True)
        if len(previo) and not previo.equals(nuevo):
            raise ValueError(f"El lote {lote} ya está asignado con otras filas; la asignación no "
                             "se reescribe (ver integridad-congelacion)")
    nuevas = nuevas[~nuevas["lote"].isin(existente["lote"])]
    return pd.concat([existente, nuevas], ignore_index=True)[COLUMNAS_ASIGNACION]


def pares_de(asignacion: pd.DataFrame, anotador: str, origen: str = "app") -> pd.DataFrame:
    """Pares que `anotador` juzga en la app (o que importó de v1), en orden de lote y posición."""
    a = asignacion[(asignacion["anotador"] == anotador) & (asignacion["origen"] == origen)]
    return (a.assign(_l=a["lote"].astype(int), _o=a["orden"].astype(int))
            .sort_values(["_l", "_o"], kind="stable").drop(columns=["_l", "_o"])
            .reset_index(drop=True))


def validar_asignacion(asignacion: pd.DataFrame) -> list[str]:
    errores = []
    rep = asignacion.duplicated(["anotador", "query_id", "passage_id"], keep=False)
    if rep.any():
        errores.append(f"{int(rep.sum())} filas con el mismo anotador y par asignado dos veces")
    malos = sorted(set(asignacion["origen"]) - set(ORIGENES))
    if malos:
        errores.append(f"Orígenes desconocidos: {malos}")
    return errores


# --------------------------------------------------------------------------- importación v1


def importar_juicios_v1(origen: Path, pool_csv: pd.DataFrame, destino: Path) -> pd.DataFrame:
    """Copia sin cambios unos juicios v1 completos al formato v2.

    Exige que `origen` pase `validar_juicios()` contra el pool v1 (cobertura completa, sin
    omitidos) y que `destino` no exista o tenga exactamente las mismas filas. Devuelve los
    juicios en el orden del pool; no escribe nada (lo hace el script, de forma atómica)."""
    v = pool.validar_juicios(origen, pool_csv)
    if v.errores:
        raise ValueError("Los juicios de origen no pasan la validación:\n- "
                         + "\n- ".join(v.errores))
    j = pd.read_csv(origen, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    orden = {k: i for i, k in enumerate(zip(pool_csv["query_id"], pool_csv["passage_id"]))}
    j = (j.assign(_o=[orden[k] for k in zip(j["query_id"], j["passage_id"])])
         .sort_values("_o").drop(columns="_o")[pool.COLUMNAS_JUICIOS].reset_index(drop=True))
    if Path(destino).exists():
        previo = pd.read_csv(destino, dtype=str, keep_default_na=False)
        claves = ["query_id", "passage_id"]
        ya = previo.merge(j, on=claves, suffixes=("_d", "_o"))
        if (ya["relevante_d"] != ya["relevante_o"]).any():
            raise ValueError(f"{destino} ya existe con juicios distintos; no se sobrescribe")
    return j


# --------------------------------------------------------------------------- avance (sin valores)


def avance(asignacion: pd.DataFrame, dir_anotaciones: Path,
           anotadores: dict[str, Anotador]) -> pd.DataFrame:
    """Por anotador: asignados, juzgados (0/1), omitidos y pendientes. Solo conteos: nunca expone
    qué valor puso cada quien. Es para el coordinador y la pestaña Estado."""
    filas = []
    for a in anotadores.values():
        asig = asignacion[asignacion["anotador"] == a.id]
        if asig.empty:
            continue
        ruta = ruta_juicios(dir_anotaciones, a.id)
        hechos = {}
        if ruta.exists():
            j = pd.read_csv(ruta, dtype=str, keep_default_na=False)
            hechos = dict(zip(zip(j["query_id"], j["passage_id"]), j["relevante"]))
        v = [hechos.get(k) for k in zip(asig["query_id"], asig["passage_id"])]
        juzg = sum(x in ("0", "1") for x in v)
        filas.append({"anotador": a.id, "nombre": a.nombre,
                      "lotes": ",".join(sorted(set(asig["lote"]), key=int)),
                      "asignados": len(asig), "juzgados": juzg,
                      "omitidos": sum(x == "" for x in v), "pendientes": len(asig) - juzg})
    return pd.DataFrame(filas, columns=["anotador", "nombre", "lotes", "asignados", "juzgados",
                                        "omitidos", "pendientes"])
