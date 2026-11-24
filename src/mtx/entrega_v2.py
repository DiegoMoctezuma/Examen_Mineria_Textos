"""Condiciones v2 de `make validar` (PRD v2 §9, WP-14), numeradas después de las 15 de v1.

16. Juicios v2 cerrados y agregados: 3 juicios válidos por par (o excepción registrada) y acuerdo.
17. Cierres y etiquetas en orden: `v2-inicio` → `reglas-fecha-v2` → `modelo_ner.json` v2 →
    `cierre_gold_v2.json` (D33, D34, §9 criterio 5).
18. Muestras v2 disjuntas entre sí y del gold y el ámbito IE de v1 (D31).
19. IR v2 reproducible con el kit, ganador D28 y robustez D29.
20. IE v2 reproducible con el kit sobre el gold oficial v2, con techo humano y línea base (D35).
21. Tablas de respuesta v2 de las 15 consultas y sus valoraciones vigentes.

Mismos estados que `entrega.py`; nunca escribe datos humanos ni salidas.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from mtx import adaptadores_kit, config
from mtx.entrega import FALLA, OK, PENDIENTE, Contexto, Resultado

S2 = "salida/v2"


def _git(cx: Contexto, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cx.raiz, capture_output=True, text=True,
                          check=False)


def _commit_de(cx: Contexto, ruta: str) -> str:
    """Primer commit que agregó `ruta` (vacío si no está versionada)."""
    p = _git(cx, "log", "--format=%H", "--diff-filter=A", "--", ruta)
    lineas = p.stdout.split()
    return lineas[-1] if lineas else ""


def _ultimo_commit_de(cx: Contexto, ruta: str) -> str:
    p = _git(cx, "log", "-1", "--format=%H", "--", ruta)
    return p.stdout.strip()


def _antes(cx: Contexto, a: str, b: str) -> bool:
    return bool(a and b) and _git(cx, "merge-base", "--is-ancestor", a, b).returncode == 0 \
        and _git(cx, "rev-parse", a).stdout != _git(cx, "rev-parse", b).stdout


def _json(ruta: Path) -> dict | None:
    return json.loads(ruta.read_text("utf-8")) if ruta.exists() else None


def _kit(cx: Contexto, modo: str, ref: Path, pred: Path) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        return adaptadores_kit.ejecutar_evaluador(modo, ref, pred, Path(tmp)).read_bytes()


# --------------------------------------------------------------------------- condiciones


def c16_juicios_v2(cx: Contexto) -> Resultado:
    titulo = "Juicios v2: cierre, 3 juicios válidos por par, agregación y acuerdo (D24)"
    cierre = _json(cx.raiz / "anotaciones" / "cierre_juicios_v2.json")
    if cierre is None:
        return Resultado(16, titulo, PENDIENTE, ["sin anotaciones/cierre_juicios_v2.json"])
    reg = _json(cx.raiz / S2 / "05a_acuerdo.json")
    if reg is None:
        return Resultado(16, titulo, PENDIENTE, [("falta salida/v2/05a_acuerdo.json: "
                                                 "`make agregar-juicios`")])
    det = []
    for nombre in ("juicios_relevancia.csv", "05a_juicios_agregados.csv"):
        ruta = cx.raiz / S2 / nombre
        if not ruta.exists() or reg.get("sha256", {}).get(nombre) != adaptadores_kit.sha256_archivo(ruta):
            det.append(f"{S2}/{nombre} no es el que registró la agregación")
    if not (cx.raiz / S2 / "05a_acuerdo.csv").exists():
        det.append("falta salida/v2/05a_acuerdo.csv")
    sin = reg.get("pares_sin_cerrar") or []
    if sin and not cierre.get("aceptar_incompletos"):
        det.append(f"{len(sin)} pares con menos de 3 juicios válidos sin excepción registrada")
    if det:
        return Resultado(16, titulo, FALLA, det)
    nota = f"; {len(sin)} pares fuera por excepción registrada" if sin else ""
    return Resultado(16, titulo, OK, [(f"{reg['pares_cerrados']} de {reg['pares']} pares "
                                      f"cerrados, Fleiss {reg['fleiss_global']['kappa']}{nota}")])


def c17_orden(cx: Contexto) -> Resultado:
    titulo = "Cierres y etiquetas en orden: v2-inicio, reglas-fecha-v2, NER v2, cierre del gold"
    pend, det = [], []
    inicio = _git(cx, "rev-parse", "v2-inicio^{}").stdout.strip()
    fecha = _git(cx, "rev-parse", "reglas-fecha-v2^{}").stdout.strip()
    if _git(cx, "tag", "-l", "reglas-fecha-v2").stdout.strip() == "":
        pend.append("sin etiqueta reglas-fecha-v2")
    modelo = _json(cx.raiz / "data" / "modelo_ner.json") or {}
    c_modelo = _ultimo_commit_de(cx, "data/modelo_ner.json") if modelo.get("version") == 2 else ""
    if not c_modelo:
        pend.append("data/modelo_ner.json v2 sin commit (`make fijar-ner-v2`)")
    c_juicios = _commit_de(cx, "anotaciones/cierre_juicios_v2.json")
    c_gold = _commit_de(cx, "anotaciones/cierre_gold_v2.json")
    if not c_juicios:
        pend.append("cierre_juicios_v2.json sin commit")
    if not c_gold:
        pend.append("cierre_gold_v2.json sin commit")
    if fecha and not _antes(cx, inicio, fecha):
        det.append("reglas-fecha-v2 no desciende de v2-inicio")
    if c_modelo and not _antes(cx, inicio, c_modelo):
        det.append("modelo_ner.json v2 no es posterior a v2-inicio")
    if c_gold and fecha and not _antes(cx, fecha, c_gold):
        det.append("cierre_gold_v2.json no es posterior a reglas-fecha-v2")
    if c_gold and c_modelo and not _antes(cx, c_modelo, c_gold):
        det.append("modelo_ner.json v2 no tiene commit anterior a cierre_gold_v2.json (D34)")
    if det:
        return Resultado(17, titulo, FALLA, det)
    if pend:
        return Resultado(17, titulo, PENDIENTE, pend)
    return Resultado(17, titulo, OK, ["v2-inicio → reglas-fecha-v2 → NER v2 → cierre del gold"])


def c18_muestras(cx: Contexto) -> Resultado:
    from mtx import ambito
    from mtx import gold_v2 as V

    titulo = "Muestras v2 disjuntas entre sí y del gold y el ámbito IE de v1 (D31)"
    cfg = V.cargar_config(dir_anot=cx.raiz / "anotaciones")
    partes = {}
    for p in cfg.partes.values():
        m = V.manifiesto(p)
        if m is None:
            return Resultado(18, titulo, PENDIENTE, [f"falta el manifiesto de {p.nombre}"])
        partes[p.nombre] = set(m["passage_id"])
    det = []
    nombres = list(partes)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            if partes[a] & partes[b]:
                det.append(f"{a} y {b} comparten {len(partes[a] & partes[b])} pasajes")
    v1_gold = set(pd.read_csv(cx.raiz / "anotaciones" / "muestra_gold.csv",
                              dtype=str)["passage_id"])
    v1_amb = set(ambito.ambito_ie(cx.raiz / "salida" / "ranking.csv",
                                  cx.raiz / "data" / "mejor_modelo.json")["passage_id"])
    for n, ids in partes.items():
        if ids & v1_gold:
            det.append(f"{n} comparte {len(ids & v1_gold)} pasajes con el gold v1")
        if ids & v1_amb:
            det.append(f"{n} comparte {len(ids & v1_amb)} pasajes con el ámbito IE de v1")
    if det:
        return Resultado(18, titulo, FALLA, det)
    return Resultado(18, titulo, OK, [", ".join(f"{n} {len(i)}" for n, i in partes.items())
                                      + "; ninguno en el gold ni el ámbito de v1"])


def c19_ir_v2(cx: Contexto) -> Resultado:
    titulo = "IR v2 reproducible con el kit, ganador D28 y robustez D29"
    juicios, r8 = cx.raiz / S2 / "juicios_relevancia.csv", cx.raiz / S2 / "ranking_8_variantes.csv"
    salida8, rob = cx.raiz / S2 / "05_ir_8_variantes.csv", cx.raiz / S2 / "05_robustez.csv"
    mejor = cx.raiz / "data" / "v2" / "mejor_modelo.json"
    faltan = [str(p.relative_to(cx.raiz)) for p in (juicios, r8, salida8, rob, mejor)
              if not p.exists()]
    if faltan:
        return Resultado(19, titulo, PENDIENTE, [(f"faltan {', '.join(faltan)} "
                                                 "(`make evaluar-ir-v2`)")])
    det = []
    if _kit(cx, "ir", juicios, r8) != salida8.read_bytes():
        det.append("el kit no reproduce salida/v2/05_ir_8_variantes.csv")
    from mtx import evaluacion_v2 as E

    res8 = pd.read_csv(salida8, keep_default_na=False, na_values=[""])
    elegido = json.loads(mejor.read_text("utf-8"))
    if E.elegir_ganador_v2(res8)["modelo"] != elegido.get("modelo"):
        det.append("data/v2/mejor_modelo.json no coincide con la regla D28")
    analisis = set(pd.read_csv(rob)["analisis"])
    for a in ("map_ic95_bootstrap", "permutacion_pareada"):
        if a not in analisis:
            det.append(f"05_robustez.csv sin {a}")
    if det:
        return Resultado(19, titulo, FALLA, det)
    return Resultado(19, titulo, OK, [(f"ganador {elegido['modelo']} (MAP {elegido['MAP']:.4f}); "
                                      "kit reproducido; IC95 y permutación presentes")])


def c20_ie_v2(cx: Contexto) -> Resultado:
    titulo = "IE v2 reproducible con el kit sobre el gold v2, con techo humano y línea base"
    gold, ent = cx.raiz / S2 / "gold_entidades.csv", cx.raiz / S2 / "entidades.csv"
    res, refs = cx.raiz / S2 / "resultados_ie.csv", cx.raiz / S2 / "09_referencias_f1.csv"
    faltan = [str(p.relative_to(cx.raiz)) for p in (gold, ent, res, refs) if not p.exists()]
    if faltan:
        return Resultado(20, titulo, PENDIENTE, [(f"faltan {', '.join(faltan)} "
                                                 "(`make extraer-v2` y `make evaluar-ie-v2`)")])
    det = []
    if _kit(cx, "ie", gold, ent) != res.read_bytes():
        det.append("el kit no reproduce salida/v2/resultados_ie.csv")
    referencias = set(pd.read_csv(refs)["referencia"])
    for r in ("techo_humano", "linea_base_gazetteer", "sistema_exacto"):
        if r not in referencias:
            det.append(f"09_referencias_f1.csv sin {r}")
    n = pd.read_csv(gold, dtype=str)["passage_id"].nunique()
    if det:
        return Resultado(20, titulo, FALLA, det)
    return Resultado(20, titulo, OK, [(f"kit reproducido; {n} pasajes con entidades en el gold v2; "
                                      "techo humano y línea base presentes")])


def c21_tablas_v2(cx: Contexto) -> Resultado:
    titulo = "Tablas de respuesta v2 de las 15 consultas y valoraciones vigentes"
    hashes = _json(cx.raiz / S2 / "10_hashes_tablas.json")
    if hashes is None:
        return Resultado(21, titulo, PENDIENTE, ["faltan las tablas v2 (`make tablas-v2`)"])
    det = []
    if len(hashes) != 15:
        det.append(f"{len(hashes)} tablas v2; se esperan 15")
    import importlib.util

    spec = importlib.util.spec_from_file_location("tablas10", config.RAIZ / "scripts" /
                                                  "10_tablas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    val = mod.valoraciones_v2(cx.raiz / "anotaciones")
    pend = [q for q, h in hashes.items()
            if (val.get(q) or {}).get("tabla_sha256") != h
            or not str((val.get(q) or {}).get("texto", "")).strip()]
    if det:
        return Resultado(21, titulo, FALLA, det)
    if pend:
        return Resultado(21, titulo, PENDIENTE, [(f"valoraciones v2 pendientes o invalidadas: "
                                                 f"{', '.join(pend)}")])
    return Resultado(21, titulo, OK, ["15 tablas y 15 valoraciones vigentes"])


CONDICIONES_V2 = [c16_juicios_v2, c17_orden, c18_muestras, c19_ir_v2, c20_ie_v2, c21_tablas_v2]
