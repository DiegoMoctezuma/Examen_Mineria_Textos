"""Fusión reglas + modelo (PRD §6.9, D12, D16) y enriquecimiento prudente (PRD §6.10).

- Coincidencia exacta `(passage_id, tipo, inicio, fin)` en ambas fuentes → una fila `ambos`.
- Solo en una fuente → `regla` o `modelo`. Sin prioridad entre fuentes, sin umbral de puntaje y
  sin ajustar spans: ante un solape parcial o un mismo span con tipo distinto sobreviven las dos
  filas y la discrepancia se registra en `salida/08_solapes_parciales.csv`.
- Se extrae una vez por pasaje y se asocia a cada consulta que lo recuperó (T08).
- `entidades.csv` tiene exactamente 8 columnas; todo lo auxiliar va a `entidades_enriquecidas.csv`.
- La normalización nunca toca `inicio`, `fin` ni `texto`.
"""
from __future__ import annotations

import unicodedata
from datetime import date

import pandas as pd

from mtx.normalizacion import normalizar_fecha, normalizar_monto

TIPOS = ("PER", "ORG", "LOC", "FECHA", "MONTO")
METODOS = ("regla", "modelo", "ambos")
COLUMNAS_ENTIDADES = ["query_id", "doc_id", "passage_id", "tipo", "texto", "inicio", "fin",
                      "metodo"]
COLUMNAS_UNICAS = ["passage_id", "doc_id", "tipo", "texto", "inicio", "fin", "metodo"]
COLUMNAS_FUENTE = ["passage_id", "tipo", "texto", "inicio", "fin", "fuente", "en_marca",
                   "puntaje_modelo"]
COLUMNAS_SOLAPES = ["passage_id", "clase", "tipo_regla", "inicio_regla", "fin_regla",
                    "texto_regla", "fuente_regla", "tipo_modelo", "inicio_modelo", "fin_modelo",
                    "texto_modelo", "longitud_solape"]
COLUMNAS_ENRIQUECIDAS = COLUMNAS_ENTIDADES + [
    "fuentes", "en_marca", "modelo_id", "modelo_revision", "puntaje_modelo", "version_extractor",
    "canonico", "texto_normalizado", "estado_identidad",
    "fecha_iso", "fecha_inicio", "fecha_fin", "precision_fecha", "fecha_relativo", "fecha_ancla",
    "resuelta_desde_ancla", "estado_fecha",
    "valor_num", "valor_min", "valor_max", "moneda", "escala", "estado_monto"]
CLAVE = ["passage_id", "tipo", "inicio", "fin"]
ORDEN = ["query_id", "passage_id", "inicio", "fin", "tipo"]


def _clave(f: dict) -> tuple:
    return (f["passage_id"], f["tipo"], int(f["inicio"]), int(f["fin"]))


def fusionar_unicas(reglas: pd.DataFrame, modelo: pd.DataFrame) -> tuple[pd.DataFrame,
                                                                          pd.DataFrame]:
    """Une las dos fuentes por pasaje. Devuelve (únicas con procedencia, solapes parciales).

    `reglas` y `modelo` tienen `COLUMNAS_FUENTE` (sin `query_id`). Las únicas llevan
    `COLUMNAS_UNICAS` sin `doc_id` más `fuentes`, `en_marca` y `puntaje_modelo`."""
    r = {_clave(f): f for f in reglas.to_dict("records")}
    m = {_clave(f): f for f in modelo.to_dict("records")}
    if len(r) != len(reglas) or len(m) != len(modelo):
        raise ValueError("Una fuente trae claves (passage_id, tipo, inicio, fin) repetidas.")
    filas = []
    for k in sorted(set(r) | set(m)):
        fr, fm = r.get(k), m.get(k)
        base = fr or fm
        metodo = "ambos" if fr and fm else ("regla" if fr else "modelo")
        fuentes = "|".join(x for x in (fr and fr["fuente"], fm and "modelo") if x)
        filas.append({"passage_id": k[0], "tipo": k[1], "texto": base["texto"],
                      "inicio": k[2], "fin": k[3], "metodo": metodo, "fuentes": fuentes,
                      "en_marca": bool(base["en_marca"]),
                      "puntaje_modelo": fm["puntaje_modelo"] if fm else None})
    unicas = pd.DataFrame(filas, columns=["passage_id", "tipo", "texto", "inicio", "fin",
                                          "metodo", "fuentes", "en_marca", "puntaje_modelo"])
    return unicas, solapes_parciales(r, m)


def solapes_parciales(r: dict, m: dict) -> pd.DataFrame:
    """Discrepancias entre fuentes, solo entre claves que no coinciden exactamente:
    `tipo_distinto` (mismo span) o `solape_parcial` (spans que se enciman sin ser iguales)."""
    por_pasaje: dict[str, list] = {}
    for k, f in m.items():
        if k not in r:
            por_pasaje.setdefault(k[0], []).append(f)
    filas = []
    for kr in sorted(r):
        if kr in m:
            continue
        fr = r[kr]
        for fm in por_pasaje.get(kr[0], []):
            ini, fin = max(kr[2], int(fm["inicio"])), min(kr[3], int(fm["fin"]))
            if ini >= fin:
                continue
            mismo_span = (kr[2], kr[3]) == (int(fm["inicio"]), int(fm["fin"]))
            filas.append({"passage_id": kr[0],
                          "clase": "tipo_distinto" if mismo_span else "solape_parcial",
                          "tipo_regla": kr[1], "inicio_regla": kr[2], "fin_regla": kr[3],
                          "texto_regla": fr["texto"], "fuente_regla": fr["fuente"],
                          "tipo_modelo": fm["tipo"], "inicio_modelo": int(fm["inicio"]),
                          "fin_modelo": int(fm["fin"]), "texto_modelo": fm["texto"],
                          "longitud_solape": fin - ini})
    return pd.DataFrame(filas, columns=COLUMNAS_SOLAPES)


def asociar_consultas(unicas: pd.DataFrame, ambito: pd.DataFrame) -> pd.DataFrame:
    """Repite cada entidad bajo cada consulta que recuperó su pasaje (T08)."""
    amb = ambito[["query_id", "passage_id", "doc_id"]].drop_duplicates()
    out = amb.merge(unicas, on="passage_id", how="inner")
    out["doc_id"] = out["doc_id"].astype(int)
    out["inicio"] = out["inicio"].astype(int)
    out["fin"] = out["fin"].astype(int)
    return ordenar(out)


def ordenar(df: pd.DataFrame) -> pd.DataFrame:
    """Orden determinista `query_id` (Q1…Q10 numérico), `passage_id`, `inicio`."""
    clave_q = df["query_id"].str[1:].astype(int)
    return (df.assign(_q=clave_q).sort_values(["_q", "passage_id", "inicio", "fin", "tipo"])
            .drop(columns="_q").reset_index(drop=True))


def validar_entidades(ent: pd.DataFrame, textos: dict[str, str]) -> list[str]:
    """Contrato de `entidades.csv` (PRD §3.5, D16)."""
    err = []
    if list(ent.columns) != COLUMNAS_ENTIDADES:
        err.append(f"Columnas {list(ent.columns)} ≠ {COLUMNAS_ENTIDADES}")
        return err
    if ent.duplicated(["query_id", *CLAVE]).any():
        err.append("Claves (query_id, passage_id, tipo, inicio, fin) duplicadas")
    if not ent["tipo"].isin(TIPOS).all():
        err.append(f"Tipos fuera de dominio: {sorted(set(ent['tipo']) - set(TIPOS))}")
    if not ent["metodo"].isin(METODOS).all():
        err.append(f"Métodos fuera de dominio: {sorted(set(ent['metodo']) - set(METODOS))}")
    malas = [f"{f['passage_id']} {f['inicio']}-{f['fin']}" for f in ent.to_dict("records")
             if not (0 <= f["inicio"] < f["fin"] <= len(textos[f["passage_id"]])
                     and textos[f["passage_id"]][f["inicio"]:f["fin"]] == f["texto"])]
    if malas:
        err.append(f"Offsets que no cumplen el invariante: {malas[:5]}")
    if not ent.equals(ordenar(ent)):
        err.append("No está ordenado por query_id, passage_id, inicio")
    return err


# =========================================================================== enriquecimiento

def sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def mapa_canonico(gazetteers: list[pd.DataFrame]) -> dict[str, str]:
    """Forma (nombre, sigla o variante, sin acentos ni mayúsculas) → nombre canónico. Solo
    equivalencias escritas en los gazetteers; una forma que apunta a dos nombres se descarta."""
    mapa: dict[str, set] = {}
    for g in gazetteers:
        for f in g.to_dict("records"):
            formas = [f["nombre"], *f["siglas"].split("|"), *f["variantes"].split("|")]
            for x in filter(None, (s.strip() for s in formas)):
                mapa.setdefault(sin_acentos(x), set()).add(f["nombre"])
    return {k: next(iter(v)) for k, v in mapa.items() if len(v) == 1}


def _ancla(fecha) -> date | None:
    if fecha is None or pd.isna(fecha):
        return None
    d = pd.Timestamp(fecha).date()
    return d if date(2018, 1, 1) <= d <= date(2025, 12, 31) else None


VACIO_FECHA = dict.fromkeys(["fecha_iso", "fecha_inicio", "fecha_fin", "precision_fecha",
                             "fecha_relativo", "fecha_ancla", "resuelta_desde_ancla",
                             "estado_fecha"], "")
VACIO_MONTO = dict.fromkeys(["valor_num", "valor_min", "valor_max", "moneda", "escala",
                             "estado_monto"], "")


def enriquecer(ent: pd.DataFrame, unicas: pd.DataFrame, fechas: dict[str, object],
               canonico: dict[str, str], modelo_id: str, modelo_revision: str,
               version_extractor: str) -> pd.DataFrame:
    """`entidades_enriquecidas.csv`: las 8 columnas intactas + procedencia, identidad, tiempo y
    dinero. `fechas` es passage_id → fecha del discurso (ancla de fechas relativas)."""
    proc = unicas.set_index(CLAVE)[["fuentes", "en_marca", "puntaje_modelo"]]
    filas = []
    for f in ent.to_dict("records"):
        p = proc.loc[(f["passage_id"], f["tipo"], f["inicio"], f["fin"])]
        usa_modelo = f["metodo"] in ("modelo", "ambos")
        extra = {"fuentes": p["fuentes"], "en_marca": bool(p["en_marca"]),
                 "modelo_id": modelo_id if usa_modelo else "",
                 "modelo_revision": modelo_revision if usa_modelo else "",
                 "puntaje_modelo": ("" if pd.isna(p["puntaje_modelo"])
                                    else f"{float(p['puntaje_modelo']):.4f}"),
                 "version_extractor": version_extractor,
                 "canonico": "", "texto_normalizado": sin_acentos(f["texto"]),
                 "estado_identidad": "", **VACIO_FECHA, **VACIO_MONTO}
        if f["tipo"] in ("ORG", "LOC"):
            c = canonico.get(sin_acentos(f["texto"]), "")
            extra["canonico"] = c
            extra["estado_identidad"] = "gazetteer" if c else "sin_equivalencia"
        elif f["tipo"] == "PER":
            extra["estado_identidad"] = "sin_vincular"  # vínculo de personas: P2, recortado
        elif f["tipo"] == "FECHA":
            nf = normalizar_fecha(f["texto"], _ancla(fechas.get(f["passage_id"])))
            extra.update({k: ("" if v is None else str(v)) for k, v in nf.items()})
        elif f["tipo"] == "MONTO":
            extra.update({k: str(v) for k, v in normalizar_monto(f["texto"]).items()})
        filas.append({**f, **extra})
    out = pd.DataFrame(filas, columns=COLUMNAS_ENRIQUECIDAS)
    if not out[COLUMNAS_ENTIDADES].equals(ent[COLUMNAS_ENTIDADES]):
        raise AssertionError("El enriquecimiento alteró las 8 columnas oficiales.")
    return out
