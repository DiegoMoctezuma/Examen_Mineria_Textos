"""Comparación de candidatos NER sobre la selección v2 adjudicada (PRD v2 D34, WP-10).

- **Ámbito:** solo los pasajes del manifiesto de la parte `seleccion` del gold v2. Antes de
  `cierre_gold_v2.json` no se infiere sobre ningún otro pasaje v2 (D32).
- **Criterio fijo:** F1 micro exacto de `(passage_id, tipo, inicio, fin)` en PER, ORG y LOC, del
  modelo solo (sin reglas ni gazetteer), sobre los 10 pasajes de la selección; un pasaje sin
  entidades en el gold cuenta sus falsos positivos. Empate a 3 decimales: gana el principal v1
  (`mrm8488`), que va primero en `candidatos_v2`; entre otros, el primero de la lista.
- **Gold:** el oficial de la selección (lo que coincide más lo que incluyó el adjudicador), pasada
  1, solo con adjudicación cerrada y vigente en todos los pasajes. Las partes A y B nunca se leen:
  el gold no elige el modelo.

Ninguna función produce ni modifica anotaciones; solo las lee para medir.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from mtx import evaluacion_ie as E
from mtx import gold_v2 as V
from mtx import ner_modelo as N

PARTE = "seleccion"
PASADA = 1
TIPOS = ("PER", "ORG", "LOC")
DECIMALES_EMPATE = 3
COLUMNAS = ["slug", "modelo", "revision", "motor", "tipo", "precision", "recall", "f1", "tp",
            "fp", "fn", "soporte", "predichas", "elegido"]


def parte_seleccion(cfg_gold: V.ConfigGold) -> V.Parte:
    if PARTE not in cfg_gold.partes:
        raise ValueError(f"config/v2/anotadores.yaml no tiene la parte `{PARTE}` del gold")
    return cfg_gold.partes[PARTE]


def pasajes_seleccion(cfg_gold: V.ConfigGold, pasajes: pd.DataFrame) -> pd.DataFrame:
    """`passage_id, texto, texto_sha256` de la selección. `ValueError` si el texto cambió desde el
    sorteo (la huella del manifiesto no coincide con la de `data/pasajes.parquet`)."""
    m = V.manifiesto(parte_seleccion(cfg_gold))
    if m is None or m.empty:
        raise ValueError("No existe el manifiesto de la selección")
    sel = m[["passage_id", "texto_sha256"]].merge(
        pasajes[["passage_id", "texto", "texto_sha256"]], on="passage_id", how="left",
        suffixes=("_muestra", ""))
    malos = sel[sel["texto_sha256"] != sel["texto_sha256_muestra"]]["passage_id"].tolist()
    if malos:
        raise ValueError(f"Pasajes de la selección con texto distinto al del sorteo: {malos}")
    return sel[["passage_id", "texto", "texto_sha256"]].reset_index(drop=True)


def faltan_adjudicar(cfg_gold: V.ConfigGold, dir_anot: Path | None = None) -> list[str]:
    """Pasajes de la selección sin adjudicación cerrada y vigente en la pasada 1."""
    p = parte_seleccion(cfg_gold)
    dir_anot = Path(dir_anot or V.dir_anotaciones())
    est = V.leer_estado_adj(dir_anot, p.adjudicador)
    est = est[(est["estado"] == V.CERRADO) & (est["pasada"].astype(int) == PASADA)]
    listos = {r.passage_id for r in est.itertuples()
              if r.huella == V.huella(dir_anot, p, r.passage_id, PASADA)}
    return [pid for pid in V.manifiesto(p)["passage_id"] if pid not in listos]


def gold_seleccion(cfg_gold: V.ConfigGold, dir_anot: Path | None = None) -> pd.DataFrame:
    g = V.gold_oficial(cfg_gold, dir_anot)
    return g[(g["parte"] == PARTE) & (g["pasada"].astype(int) == PASADA)
             & g["tipo"].isin(TIPOS)].reset_index(drop=True)


def predicciones(cfg: N.ConfigModelo, crudos: dict[str, dict],
                 textos: dict[str, str]) -> pd.DataFrame:
    """Entidades del modelo solo, posprocesadas igual que en la tubería (U15)."""
    filas = []
    for pid, texto in textos.items():
        pp = N.posprocesar(texto, crudos[pid]["entidades_crudas"], cfg, pid)
        filas += [{"passage_id": pid, "tipo": e["tipo"], "texto": e["texto"],
                   "inicio": e["inicio"], "fin": e["fin"], "metodo": "modelo"}
                  for e in pp.entidades if e["tipo"] in TIPOS]
    return pd.DataFrame(filas, columns=["passage_id", "tipo", "texto", "inicio", "fin", "metodo"])


def comparar(gold: pd.DataFrame, preds: dict[str, pd.DataFrame], cfgs: dict[str, N.ConfigModelo],
             pasajes: set[str], orden: list[str]) -> pd.DataFrame:
    """Una fila por candidato y tipo (PER, ORG, LOC y TODOS = micro), con `elegido` marcado."""
    filas = []
    for slug in orden:
        det = E.detalle(gold, preds[slug], pasajes)
        det = det[(det["metodo"] == "modelo") & det["tipo"].isin((*TIPOS, "TODOS"))]
        c = cfgs[slug]
        for r in det.itertuples():
            filas.append({"slug": slug, "modelo": c.repo_id, "revision": c.revision,
                          "motor": c.motor, "tipo": r.tipo, "precision": r.precision,
                          "recall": r.recall, "f1": r.f1, "tp": r.tp, "fp": r.fp, "fn": r.fn,
                          "soporte": r.soporte, "predichas": r.predichas, "elegido": False})
    tabla = pd.DataFrame(filas, columns=COLUMNAS)
    tabla.loc[tabla["slug"] == elegir(tabla, orden), "elegido"] = True
    return tabla


def elegir(tabla: pd.DataFrame, orden: list[str]) -> str:
    """Mayor F1 micro redondeado a 3 decimales; en empate, el primero de `orden` (el principal)."""
    micro = tabla[tabla["tipo"] == "TODOS"].set_index("slug")["f1"].round(DECIMALES_EMPATE)
    mejor = micro.max()
    return next(s for s in orden if s in micro.index and micro[s] == mejor)


def modelo_ner_v2(cfg: N.ConfigModelo, tabla: pd.DataFrame, pasajes: int) -> dict:
    """`data/modelo_ner.json` v2: las claves de D09 (las que leen 08 y 09) más el detalle de D34."""
    micro = tabla[tabla["tipo"] == "TODOS"].set_index("slug")
    d = N.modelo_ner_json(cfg, criterio="f1_seleccion_v2", f1=float(micro.loc[cfg.slug, "f1"]))
    d.update({
        "version": 2,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "regla": ("F1 micro exacto PER, ORG y LOC del modelo solo sobre la selección v2 "
                  "adjudicada; empate a 3 decimales gana mrm8488 (D34)"),
        "pasajes_seleccion": pasajes,
        "candidatos": {s: {"modelo": r.modelo, "revision": r.revision, "f1": float(r.f1)}
                       for s, r in micro.iterrows()},
        "comparacion": "salida/v2/09_comparacion_ner.csv",
    })
    return d
