"""Pool de relevancia (D06) y validación de los juicios humanos (PRD §6.5).

- Pool por consulta: unión sin duplicados de los top-10 de las cuatro variantes de `ranking.csv`.
  Un pasaje compartido entre consultas aparece una vez por consulta y recibe un juicio
  independiente en cada una (T08).
- Orden de presentación: IDs ordenados por `(doc_id, posicion)` y barajados con semilla 42,
  un generador nuevo por consulta. El orden de filas de `salida/04_pool.csv` es ese orden.
- La procedencia (`variantes`, `mejor_rango_*`) queda para auditoría; la app no la muestra.

Este módulo nunca escribe en `anotaciones/`: solo lee los juicios para validarlos.
"""
from __future__ import annotations

import hashlib
import io
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .ranking import MODELOS_OFICIALES, mascara_fecha

COLUMNAS_POOL = ["query_id", "passage_id", "doc_id", "fecha", "en_ventana", "variantes",
                 "mejor_rango_tfidf", "mejor_rango_bm25", "texto", "texto_sha256"]
COLUMNAS_JUICIOS = ["query_id", "doc_id", "passage_id", "relevante"]
TAM_ESPERADO = (15, 40)


def _clave(pid: str) -> tuple[int, int]:
    d, p = pid.split("_")
    return int(d), int(p)


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- construcción


def construir_pool(ranking: pd.DataFrame, pasajes: pd.DataFrame, consultas: pd.DataFrame,
                   semilla: int = config.SEMILLA) -> pd.DataFrame:
    """Pool de las consultas de `consultas`, en su orden, con las columnas de `COLUMNAS_POOL`.

    `ranking` puede venir de `ranking.csv` leído como texto; `pasajes` debe contener todos los
    `passage_id` del ranking (si falta alguno, `KeyError`).
    """
    r = ranking.assign(rango=ranking["rango"].astype(int))
    if not set(r["modelo"]) <= set(MODELOS_OFICIALES):
        raise ValueError(f"Modelos desconocidos en el ranking: {set(r['modelo'])}")
    p = pasajes.set_index("passage_id")
    faltan = set(r["passage_id"]) - set(p.index)
    if faltan:
        raise KeyError(f"{len(faltan)} passage_id del ranking no están en los pasajes: "
                       f"{sorted(faltan, key=_clave)[:5]}")
    bloques = []
    for q in consultas.itertuples(index=False):
        rq = r[r["query_id"] == q.query_id]
        if rq.empty:
            raise ValueError(f"{q.query_id} no tiene filas en el ranking")
        ids = sorted(set(rq["passage_id"]), key=_clave)
        orden = np.random.default_rng(semilla).permutation(len(ids))
        ids = [ids[i] for i in orden]
        filas = []
        for pid in ids:
            de = rq[rq["passage_id"] == pid]
            variantes = [m for m in MODELOS_OFICIALES if m in set(de["modelo"])]
            rango = {fam: de.loc[de["modelo"].str.startswith(fam), "rango"].min()
                     for fam in ("tfidf", "bm25")}
            filas.append({
                "query_id": q.query_id, "passage_id": pid, "doc_id": int(p.at[pid, "doc_id"]),
                "fecha": p.at[pid, "fecha"], "variantes": "|".join(variantes),
                "mejor_rango_tfidf": rango["tfidf"], "mejor_rango_bm25": rango["bm25"],
                "texto": p.at[pid, "texto"], "texto_sha256": p.at[pid, "texto_sha256"],
            })
        b = pd.DataFrame(filas)
        f = pd.to_datetime(b["fecha"]).to_numpy(dtype="datetime64[ns]")
        b["en_ventana"] = mascara_fecha(f, q.desde, q.hasta) & ~np.isnat(f)
        bloques.append(b)
    pool = pd.concat(bloques, ignore_index=True)
    for c in ("mejor_rango_tfidf", "mejor_rango_bm25"):
        pool[c] = pool[c].astype("Int64")
    return pool[COLUMNAS_POOL]


def formatear_pool(pool: pd.DataFrame) -> pd.DataFrame:
    """Para el CSV: fecha ISO o vacía, `en_ventana` como 0/1, rango ausente vacío."""
    out = pool.copy()
    out["fecha"] = pd.to_datetime(out["fecha"]).dt.strftime("%Y-%m-%d").fillna("")
    out["en_ventana"] = out["en_ventana"].astype(int)
    return out


def leer_pool(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def como_texto(pool_formateado: pd.DataFrame) -> pd.DataFrame:
    """El pool tal como quedaría al escribirlo y leerlo de `04_pool.csv` (todo como texto).
    Se usa para comparar un pool en memoria con el del disco sin falsas diferencias."""
    buf = io.StringIO()
    pool_formateado.to_csv(buf, index=False)
    buf.seek(0)
    return pd.read_csv(buf, dtype=str, keep_default_na=False)


def hash_pool(pool_csv: pd.DataFrame) -> str:
    """Huella del pool leído como texto: membresía, orden, metadatos y hash de cada texto."""
    h = hashlib.sha256()
    for fila in pool_csv.drop(columns=["texto"]).astype(str).itertuples(index=False):
        h.update("\x1f".join(fila).encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()


def diferencias_pool(viejo: pd.DataFrame, nuevo: pd.DataFrame) -> list[str]:
    """Diferencias legibles entre dos pools leídos como texto (vacía si son iguales)."""
    dif = []
    kv = set(zip(viejo["query_id"], viejo["passage_id"]))
    kn = set(zip(nuevo["query_id"], nuevo["passage_id"]))
    for q, pid in sorted(kv - kn):
        dif.append(f"Sale del pool: {q} {pid}")
    for q, pid in sorted(kn - kv):
        dif.append(f"Entra al pool: {q} {pid}")
    comunes = viejo.merge(nuevo, on=["query_id", "passage_id"], suffixes=("_v", "_n"))
    for c in ("texto_sha256", "fecha", "en_ventana", "variantes", "mejor_rango_tfidf",
              "mejor_rango_bm25", "doc_id"):
        cambia = comunes[comunes[f"{c}_v"] != comunes[f"{c}_n"]]
        for r in cambia.itertuples(index=False):
            dif.append(f"Cambia {c} en {r.query_id} {r.passage_id}")
    if not dif and hash_pool(viejo) != hash_pool(nuevo):
        dif.append("Cambia el orden de presentación")
    return dif


def resumen_pool(pool: pd.DataFrame) -> pd.DataFrame:
    """Tamaño por consulta, pasajes en ventana y aportes exclusivos de cada variante."""
    filas = []
    for qid, g in pool.groupby("query_id", sort=False):
        var = g["variantes"].str.split("|")
        fila = {"query_id": qid, "pasajes": len(g), "en_ventana": int(g["en_ventana"].sum()),
                "fuera_de_ventana": int((~g["en_ventana"].astype(bool)).sum()),
                "en_las_cuatro": int((var.str.len() == 4).sum())}
        for m in MODELOS_OFICIALES:
            fila[f"solo_{m}"] = int(var.map(lambda v, m=m: v == [m]).sum())
        fila["fuera_de_rango_esperado"] = int(not TAM_ESPERADO[0] <= len(g) <= TAM_ESPERADO[1])
        filas.append(fila)
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- validación de juicios


@dataclass
class Validacion:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    juzgados: int = 0
    esperados: int = 0

    @property
    def ok(self) -> bool:
        return not self.errores


def validar_juicios(ruta_juicios: Path, pool_csv: pd.DataFrame,
                    pasajes: pd.DataFrame | None = None) -> Validacion:
    """Comprueba los juicios contra el pool (solo lectura; PRD §6.5, §13.2).

    `relevante` vacío significa "omitido por ahora" y cuenta como pendiente de cobertura.
    Errores (impiden exportar): formato del archivo, columnas, valores fuera de {0, 1}, pares
    repetidos o fuera del pool, `doc_id` incoherente, cobertura incompleta y `texto_sha256` del
    pool distinto del texto actual (si se dan `pasajes`). Aviso: consulta sin relevantes.
    """
    v = Validacion(esperados=len(pool_csv))
    ruta = Path(ruta_juicios)
    if not ruta.exists():
        v.errores.append(f"No existe {ruta}")
        return v
    crudo = ruta.read_bytes()
    if crudo.startswith(b"\xef\xbb\xbf"):
        v.errores.append("El archivo tiene BOM; debe ser UTF-8 sin BOM")
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError:
        v.errores.append("El archivo no es UTF-8")
        return v
    cabecera = texto.lstrip("﻿").splitlines()[0] if texto.strip() else ""
    if cabecera != ",".join(COLUMNAS_JUICIOS):
        v.errores.append(f"Cabecera {cabecera!r}; se espera {','.join(COLUMNAS_JUICIOS)!r} "
                         "(separador coma)")
        return v
    j = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    # `relevante` vacío = omitido por ahora (sin juzgar): cuenta como pendiente, nunca como 0.
    pendientes = j[j["relevante"] == ""]
    v.juzgados = int(j["relevante"].isin(["0", "1"]).sum())

    malos = j[~j["relevante"].isin(["0", "1", ""])]
    if len(malos):
        v.errores.append(f"{len(malos)} juicios con `relevante` fuera de {{0, 1}}: "
                         f"{_pares(malos)}")
    rep = j[j.duplicated(["query_id", "passage_id"], keep=False)]
    if len(rep):
        v.errores.append(f"Pares (query_id, passage_id) con más de un juicio: {_pares(rep)}")
    partes = j["passage_id"].str.split("_", n=1).str[0]
    incoh = j[partes != j["doc_id"]]
    if len(incoh):
        v.errores.append(f"`doc_id` no coincide con el `passage_id`: {_pares(incoh)}")

    kp = set(zip(pool_csv["query_id"], pool_csv["passage_id"]))
    kj = set(zip(j["query_id"], j["passage_id"]))
    fuera = kj - kp
    kj -= set(zip(pendientes["query_id"], pendientes["passage_id"]))
    if fuera:
        v.errores.append(f"{len(fuera)} juicios fuera del pool: {sorted(fuera)[:5]}")
    faltan = kp - kj
    if faltan:
        por_q = pd.Series([q for q, _ in faltan]).value_counts().sort_index(
            key=lambda i: i.str[1:].astype(int))
        v.errores.append(f"Cobertura incompleta: faltan {len(faltan)} de {len(kp)} juicios ("
                         + ", ".join(f"{q}: {n}" for q, n in por_q.items())
                         + f"); {len(pendientes)} de ellos omitidos por ahora")

    if pasajes is not None:
        actual = pasajes.set_index("passage_id")["texto"]
        distintos = [pid for pid, h in zip(pool_csv["passage_id"], pool_csv["texto_sha256"])
                     if pid not in actual.index or sha256_texto(actual[pid]) != h]
        if distintos:
            v.errores.append(f"{len(set(distintos))} pasajes del pool cambiaron de texto o ya no "
                             f"existen (corpus o segmentación distintos): {sorted(set(distintos))[:5]}")

    validos = j[j["relevante"].isin(["0", "1"])]
    for qid in pool_csv["query_id"].unique():
        rel = validos[(validos["query_id"] == qid) & (validos["relevante"] == "1")]
        if rel.empty:
            v.avisos.append(f"{qid} no tiene ningún relevante: AP indefinido para {qid}; se "
                            "discute en el reporte y no se altera ningún juicio")
    return v


def _pares(df: pd.DataFrame, n: int = 5) -> str:
    pares = list(zip(df["query_id"], df["passage_id"]))
    return ", ".join(f"{q} {p}" for q, p in pares[:n]) + (" ..." if len(pares) > n else "")


def exportar_juicios(ruta_juicios: Path, destino: Path, validacion: Validacion) -> None:
    """Copia byte a byte los juicios a la raíz del repo, solo si `validacion` no tiene errores."""
    if not validacion.ok:
        raise ValueError("Los juicios no pasaron la validación; no se exportan:\n- "
                         + "\n- ".join(validacion.errores))
    shutil.copyfile(ruta_juicios, destino)
