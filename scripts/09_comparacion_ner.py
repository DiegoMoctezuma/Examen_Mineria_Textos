"""09 · Comparación de candidatos NER sobre la selección v2 (PRD v2 D34, WP-10). Lo corre Diego.

    make verificar-ner-v2    # verifica cada candidato → salida/v2/07_candidatos_ner.md (red)
    make inferir-seleccion   # infiere solo sobre los 10 pasajes de la selección → data/cache_ner/
    make comparacion-ner     # compara contra la selección adjudicada → salida/v2/09_comparacion_ner.csv
    make fijar-ner-v2        # lo mismo y escribe data/modelo_ner.json v2 (una sola vez)

Orden (D32, D34): Diego y Arturo cierran la selección → se infiere sobre esos pasajes → Gonzalo
adjudica → se compara y se fija `modelo_ner.json` v2 con commit anterior a `cierre_gold_v2.json`.
Las predicciones de la selección no se commitean mientras Gonzalo adjudica (modo ciego). Este
script imprime solo conteos y cifras, nunca entidades.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime

import pandas as pd

from mtx import cierres_v2 as K
from mtx import comparacion_ner as C
from mtx import config
from mtx import gold_v2 as V
from mtx import ner_modelo as N

SALIDA_V2 = config.DIR_SALIDA / "v2"
RUTA_TABLA = SALIDA_V2 / "09_comparacion_ner.csv"
RUTA_VERIFICACION = SALIDA_V2 / "07_candidatos_ner.md"
RUTA_REGISTRO = SALIDA_V2 / "07_registro_ner_seleccion.json"
RUTA_MODELO_NER = config.DIR_DATA / "modelo_ner.json"
EJEMPLO = ("El secretario de Salud, Jorge Alcocer Varela, viajó con Andrés Manuel López Obrador a "
           "Tabasco para ver la refinería de Dos Bocas de Pemex.")


def _seleccion() -> pd.DataFrame:
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "texto", "texto_sha256"])
    return C.pasajes_seleccion(V.cargar_config(), pasajes)


def verificar(slugs: list[str], cfgs: dict[str, N.ConfigModelo]) -> int:
    """PV de D34 sin gold: etiquetas reales, licencia, tamaño, límite y un ejemplo sintético."""
    lineas = ["# Candidatos NER v2 (D34, WP-10)", "",
              f"- Fecha: {datetime.now().isoformat(timespec='seconds')}",
              f"- Entorno: Python {platform.python_version()}, CPU", "",
              ("| Candidato | Revisión | Motor | Licencia | Parámetros | Etiquetas reales | "
               "Límite | Ejemplo sintético | Resultado |"),
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    fallas = 0
    for slug in slugs:
        c = cfgs[slug]
        try:
            pipe, tok = N.construir_pipeline(c)
            if c.motor == "spacy":
                etiquetas = sorted(pipe.get_pipe("ner").labels)
                params, limite = "—", f"{pipe.max_length:,} caracteres"
                ok_lim = True
            else:
                m = pipe.model
                etiquetas = sorted({N.etiqueta_base(v) for v in m.config.id2label.values()}
                                   - {"O"})
                params = f"{sum(p.numel() for p in m.parameters()) / 1e6:.0f} M"
                real = min(m.config.max_position_embeddings, tok.model_max_length) \
                    - tok.num_special_tokens_to_add()
                limite, ok_lim = str(real), real >= c.max_length_real
            pp = N.posprocesar(EJEMPLO, N.inferir_pasaje(EJEMPLO, pipe, tok, c), c)
            ok_ej = bool(pp.entidades) and all(EJEMPLO[e["inicio"]:e["fin"]] == e["texto"]
                                               for e in pp.entidades)
            ok_map = set(c.mapa_etiquetas) <= set(etiquetas)
            ok = ok_lim and ok_ej and ok_map and bool(c.licencia)
            ejemplo = "; ".join(f"{e['tipo']} «{e['texto']}»" for e in pp.entidades)
        except Exception as e:  # noqa: BLE001 — se registra la falla del candidato
            ok, etiquetas, params, limite, ejemplo = False, [], "—", "—", f"error: {e}"
        fallas += not ok
        lineas.append(f"| {c.repo_id} | `{c.revision[:12]}` | {c.motor} | {c.licencia or '—'} | "
                      f"{params} | {', '.join(etiquetas)} | {limite} | {ejemplo} | "
                      f"{'✔' if ok else '✘'} |")
    lineas += ["", ("Descartados al verificar (2026-11-24): "
                    "`PlanTL-GOB-ES/roberta-base-bne-capitel-ner` (ya no está publicado en Hugging "
                    "Face; solo quedan copias de terceros sin procedencia verificable) y "
                    "`MMG/xlm-roberta-large-ner-spanish` (no declara licencia)."), "",
               ("El mapa de cada candidato a PER, ORG y LOC y sus etiquetas descartadas están en "
                "`config/ner.yaml`.")]
    SALIDA_V2.mkdir(parents=True, exist_ok=True)
    RUTA_VERIFICACION.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"{RUTA_VERIFICACION.relative_to(config.RAIZ)}: {len(slugs) - fallas} de {len(slugs)} "
          "candidatos aprobados")
    return 1 if fallas else 0


def inferir(slugs: list[str], cfgs: dict[str, N.ConfigModelo], forzar: bool) -> dict:
    sel = _seleccion()
    registro = {}
    for slug in slugs:
        _, reg = N.ejecutar(cfgs[slug], sel, forzar=forzar)
        registro[slug] = {"pasajes": len(sel), **N.registro_dict(reg)}
        print(f"  {slug:<20} {len(sel)} pasajes: {reg.inferidos} inferidos, {reg.cacheados} de "
              f"caché, {reg.segundos_carga + reg.segundos_inferencia:.1f} s")
    SALIDA_V2.mkdir(parents=True, exist_ok=True)
    RUTA_REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return registro


def comparar(slugs: list[str], cfgs: dict[str, N.ConfigModelo], fijar: bool) -> int:
    cfg_gold = V.cargar_config()
    faltan = C.faltan_adjudicar(cfg_gold)
    if faltan:
        print(f"La selección no está adjudicada: faltan {len(faltan)} de 10 pasajes en la pasada 1 "
              f"({', '.join(faltan[:3])}…). Gonzalo adjudica primero.", file=sys.stderr)
        return 1
    sel = _seleccion()
    textos = dict(zip(sel["passage_id"], sel["texto"]))
    preds = {}
    for slug in slugs:
        crudos, reg = N.ejecutar(cfgs[slug], sel)
        if reg.inferidos:
            print(f"  aviso  {slug}: {reg.inferidos} pasajes no estaban en caché y se infirieron")
        preds[slug] = C.predicciones(cfgs[slug], crudos, textos)
    gold = C.gold_seleccion(cfg_gold)
    tabla = C.comparar(gold, preds, cfgs, set(textos), slugs)
    SALIDA_V2.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(RUTA_TABLA, index=False, lineterminator="\n")
    micro = tabla[tabla["tipo"] == "TODOS"]
    print(f"{RUTA_TABLA.relative_to(config.RAIZ)} · gold de la selección: {len(gold)} entidades "
          f"PER/ORG/LOC en {gold['passage_id'].nunique()} de {len(textos)} pasajes")
    for r in micro.itertuples():
        print(f"  {r.slug:<20} F1 {r.f1:.3f}  P {r.precision:.3f}  R {r.recall:.3f}"
              f"{'   ← elegido' if r.elegido else ''}")
    if not fijar:
        return 0
    if K.gold_cerrado():
        print("El gold v2 ya está cerrado: modelo_ner.json v2 tenía que fijarse antes (D34).",
              file=sys.stderr)
        return 1
    previo = json.loads(RUTA_MODELO_NER.read_text("utf-8")) if RUTA_MODELO_NER.exists() else {}
    if previo.get("version") == 2:
        print("data/modelo_ner.json v2 ya está fijado; no se reescribe.", file=sys.stderr)
        return 1
    elegido = micro[micro["elegido"]]["slug"].iloc[0]
    d = C.modelo_ner_v2(cfgs[elegido], tabla, len(textos))
    RUTA_MODELO_NER.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(f"data/modelo_ner.json v2: {d['modelo']} (F1 {d['f1_seleccion']:.3f}). Haz commit "
          "antes de cerrar el gold: feat(ner): ...")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("que", choices=["verificar", "inferir", "comparar"])
    ap.add_argument("--fijar", action="store_true",
                    help="con `comparar`: escribe data/modelo_ner.json v2")
    ap.add_argument("--forzar", action="store_true", help="con `inferir`: ignora la caché")
    ap.add_argument("--modelo", action="append", help="limita a estos candidatos")
    a = ap.parse_args()
    _, cfgs = N.cargar_config()
    slugs = N.candidatos_v2()
    if a.modelo:
        if a.fijar:
            ap.error("--fijar compara a todos los candidatos; quita --modelo")
        slugs = [s for s in slugs if s in a.modelo]
    if a.que == "verificar":
        return verificar(slugs, cfgs)
    if a.que == "inferir":
        inferir(slugs, cfgs, a.forzar)
        return 0
    return comparar(slugs, cfgs, a.fijar)


if __name__ == "__main__":
    sys.exit(main())
