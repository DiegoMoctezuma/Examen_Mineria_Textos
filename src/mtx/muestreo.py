"""Muestras del gold de evaluación y del conjunto de selección (PRD §6.11, D10, U13, T09).

Universo: top-10 con filtro del mejor modelo de IR. Gold: 20 pasajes únicos, 2 por consulta, por
emparejamiento global reproducible (semilla 42): una plaza del rango 1-5 y otra del 6-10; si no
existe asignación completa con esos estratos, se intenta sin estratos y, si tampoco, se reporta la
inviabilidad con las consultas en conflicto (nunca se amplía al top-20 ni se duplican IDs).
Selección (P1): 6 pasajes de 6 consultas distintas, disjuntos del gold.

Sustitución (U13): solo por criterio objetivo y medible; los pasajes que lo cumplen se excluyen
antes del sorteo y quedan registrados con su cifra. "No tiene entidades" nunca es motivo.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from mtx import config
from mtx.preproceso import tokenizar_sin_stem

COLUMNAS_MANIFIESTO = ["query_id", "passage_id", "doc_id", "texto_sha256", "semilla",
                       "version_muestra"]
RUTA_PROTOCOLO = config.DIR_CONFIG / "protocolo.txt"
MIN_PALABRAS_CONTENIDO = 25
MAX_FRACCION_PROTOCOLO = 0.5
ESTRATOS = ((1, 5), (6, 10))


class MuestraInviable(ValueError):
    def __init__(self, consultas: list[str], detalle: str):
        self.consultas = consultas
        super().__init__(f"No existe asignación completa; consultas en conflicto: "
                         f"{', '.join(consultas)}. {detalle}")


def leer_protocolo(ruta: Path = RUTA_PROTOCOLO) -> frozenset[str]:
    return frozenset(lin.strip().lower() for lin in Path(ruta).read_text(encoding="utf-8")
                     .splitlines() if lin.strip() and not lin.startswith("#"))


def motivo_sustitucion(texto: str, inicio_cuerpo: int, protocolo: frozenset[str]) -> str | None:
    """Criterio objetivo de U13 con su cifra, o None si el pasaje es elegible."""
    cuerpo = texto[inicio_cuerpo:]
    if not cuerpo.strip() or "�" in cuerpo:
        return "causa técnica: texto vacío o con caracteres corruptos"
    contenido = len(tokenizar_sin_stem(cuerpo))
    if contenido < MIN_PALABRAS_CONTENIDO:
        return f"menos de {MIN_PALABRAS_CONTENIDO} palabras de contenido ({contenido})"
    palabras = re.findall(r"[a-záéíóúñü]+", cuerpo.lower())
    frac = sum(p in protocolo for p in palabras) / max(len(palabras), 1)
    if frac > MAX_FRACCION_PROTOCOLO:
        return f"más de la mitad en fórmulas de protocolo ({frac:.0%})"
    return None


def _orden_natural(q: str) -> tuple:
    return (int(q[1:]) if q[1:].isdigit() else 10**6, q)


@dataclass
class Muestra:
    gold: pd.DataFrame
    seleccion: pd.DataFrame
    excluidos: pd.DataFrame
    estratos_respetados: bool
    avisos: list[str] = field(default_factory=list)


def _emparejar(plazas: list[tuple[str, int]], candidatos: dict[tuple[str, int], list[str]]
               ) -> dict[tuple[str, int], str] | None:
    """Emparejamiento bipartito plaza → pasaje (algoritmo de Kuhn) con el orden de preferencia
    dado por el sorteo: determinista para la misma semilla. None si no es completo."""
    dueno: dict[str, tuple[str, int]] = {}

    def aumentar(plaza, vistos) -> bool:
        for pid in candidatos[plaza]:
            if pid in vistos:
                continue
            vistos.add(pid)
            if pid not in dueno or aumentar(dueno[pid], vistos):
                dueno[pid] = plaza
                return True
        return False

    for plaza in plazas:
        if not aumentar(plaza, set()):
            return None
    return {plaza: pid for pid, plaza in dueno.items()}


def _sin_asignacion(plazas, candidatos) -> list[str]:
    """Consultas cuyas plazas no pueden llenarse juntas (para el mensaje de inviabilidad)."""
    fallan = []
    for i in range(len(plazas)):
        if _emparejar(plazas[: i + 1], candidatos) is None:
            fallan.append(plazas[i][0])
    return sorted(set(fallan), key=_orden_natural)


def sortear(amb: pd.DataFrame, pasajes: pd.DataFrame, semilla: int = config.SEMILLA,
            por_consulta: int = 2, n_seleccion: int = 6, protocolo: frozenset[str] | None = None,
            version: int = 1) -> Muestra:
    """`amb`: `query_id, passage_id, doc_id, rango` (top-10 con filtro del mejor modelo).
    `pasajes`: `passage_id, texto, inicio_cuerpo, texto_sha256`."""
    protocolo = protocolo if protocolo is not None else leer_protocolo()
    info = pasajes.set_index("passage_id")
    excl = []
    for pid in sorted(set(amb["passage_id"])):
        m = motivo_sustitucion(info.at[pid, "texto"], int(info.at[pid, "inicio_cuerpo"]),
                               protocolo)
        if m:
            excl.append({"passage_id": pid, "motivo": m})
    excluidos = pd.DataFrame(excl, columns=["passage_id", "motivo"])
    eleg = amb[~amb["passage_id"].isin(set(excluidos["passage_id"]))]

    rng = random.Random(semilla)
    consultas = sorted(amb["query_id"].unique(), key=_orden_natural)
    preferencia = {}
    for q in consultas:  # un orden de sorteo por consulta, fijo para la semilla
        ids = sorted(eleg.loc[eleg["query_id"] == q, "passage_id"])
        rng.shuffle(ids)
        preferencia[q] = ids
    rango = {(r.query_id, r.passage_id): int(r.rango) for r in eleg.itertuples(index=False)}
    doc_de = dict(zip(amb["passage_id"], amb["doc_id"]))

    def candidatos(con_estratos: bool):
        plazas, cand = [], {}
        for q in consultas:
            for k in range(por_consulta):
                plaza = (q, k)
                plazas.append(plaza)
                lo, hi = ESTRATOS[k] if con_estratos and por_consulta == len(ESTRATOS) else (1, 10**6)
                cand[plaza] = [p for p in preferencia[q] if lo <= rango[(q, p)] <= hi]
        return plazas, cand

    avisos, estratos = [], True
    plazas, cand = candidatos(True)
    asign = _emparejar(plazas, cand)
    if asign is None:
        estratos = False
        avisos.append("Sin asignación completa con estratos de rango 1-5 y 6-10; se asigna sin "
                      "estratos.")
        plazas, cand = candidatos(False)
        asign = _emparejar(plazas, cand)
        if asign is None:
            raise MuestraInviable(_sin_asignacion(plazas, cand),
                                  "No se amplía al top-20 ni se duplican IDs.")

    def manifiesto(pares: list[tuple[str, str]]) -> pd.DataFrame:
        df = pd.DataFrame(pares, columns=["query_id", "passage_id"])
        df["doc_id"] = df["passage_id"].map(doc_de)
        df["texto_sha256"] = df["passage_id"].map(info["texto_sha256"])
        df["semilla"] = semilla
        df["version_muestra"] = version
        df["_o"] = df["query_id"].map(_orden_natural)
        return df.sort_values(["_o", "passage_id"]).drop(columns="_o").reset_index(drop=True)[
            COLUMNAS_MANIFIESTO]

    gold = manifiesto([(q, asign[(q, k)]) for q in consultas for k in range(por_consulta)])

    usados = set(gold["passage_id"])
    orden_q = list(consultas)
    rng.shuffle(orden_q)
    sel = []
    for q in orden_q:
        if len(sel) == n_seleccion:
            break
        libre = next((p for p in preferencia[q] if p not in usados), None)
        if libre:
            sel.append((q, libre))
            usados.add(libre)
    if len(sel) < n_seleccion:
        avisos.append(f"Solo {len(sel)} pasajes de selección disponibles (se esperaban "
                      f"{n_seleccion}).")
    return Muestra(gold, manifiesto(sel), excluidos, estratos, avisos)
