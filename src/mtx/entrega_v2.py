"""Condiciones v2 de `make validar` (PRD v2 §9, WP-14), numeradas después de las 15 de v1.

16. Juicios v2 cerrados y agregados: 3 juicios válidos por par (o excepción registrada) y acuerdo.
17. Cierres y etiquetas en orden: `v2-inicio` → `reglas-fecha-v2` → `modelo_ner.json` v2 →
    `cierre_gold_v2.json` (D33, D34, §9 criterio 5).
18. Muestras v2 disjuntas entre sí y del gold y el ámbito IE de v1 (D31).
19. IR v2 reproducible con el kit, ganador D28 y robustez D29.
20. IE v2 reproducible con el kit sobre el gold oficial v2, con techo humano y línea base (D35).
21. Tablas de respuesta v2 de las 15 consultas y sus valoraciones vigentes.
22. Guion v2 con ensayo cronometrado entre 15:00 y 20:00 y revisión ciega registrada (§9, criterios
    7 y 9; WP-17 y WP-18).

Además, `raiz_c02` a `raiz_c08` sustituyen a las condiciones 2 a 8 de v1 cuando la raíz ya tiene
los seis CSV v2 (`make promover-v2`, D28): mismo contrato de columnas, contra las fuentes v2.

Mismos estados que `entrega.py`; nunca escribe datos humanos ni salidas.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from mtx import adaptadores_kit, config
from mtx.entrega import FALLA, OK, PENDIENTE, RE_TIEMPO, Contexto, Resultado

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


def c22_presentacion_v2(cx: Contexto) -> Resultado:
    titulo = "Guion v2 con tiempo medido de 15:00 a 20:00 y revisión ciega registrada"
    guion = cx.raiz / "laminas" / "guion_v2.md"
    if not guion.exists():
        return Resultado(22, titulo, PENDIENTE, ["falta laminas/guion_v2.md (WP-17)"])
    pend, det = [], []
    m = RE_TIEMPO.search(guion.read_text(encoding="utf-8"))
    if not m:
        pend.append("el guion v2 no registra «Tiempo medido: m:ss» (ensayo cronometrado)")
    elif not 15 * 60 <= int(m.group(1)) * 60 + int(m.group(2)) <= 20 * 60:
        det.append(f"tiempo medido {m.group(1)}:{m.group(2)} fuera de 15:00 a 20:00 (PV6)")
    if not (cx.raiz / "docs" / "revision_ciega_respuesta.md").exists():
        pend.append("falta docs/revision_ciega_respuesta.md (WP-18)")
    if det:
        return Resultado(22, titulo, FALLA, det + pend)
    if pend:
        return Resultado(22, titulo, PENDIENTE, pend)
    return Resultado(22, titulo, OK, [(f"tiempo medido {m.group(1)}:{m.group(2)}; revisión ciega "
                                      "registrada")])


# --------------------------------------------------------------------------- raíz promovida (D28)


def _rutas_ir_v2(cx: Contexto):
    from mtx import evaluacion_v2 as E

    s2, a = cx.raiz / S2, cx.raiz / "anotaciones"
    return E.RutasV2(juicios=s2 / "juicios_relevancia.csv",
                     agregados=s2 / "05a_juicios_agregados.csv",
                     acuerdo_json=s2 / "05a_acuerdo.json",
                     cierre_juicios=a / "cierre_juicios_v2.json",
                     ranking8=s2 / "ranking_8_variantes.csv", consultas=cx.rp.app.consultas,
                     dir_salida=s2, mejor_modelo=cx.raiz / "data" / "v2" / "mejor_modelo.json")


def _consultas(cx: Contexto) -> pd.DataFrame:
    return pd.read_csv(cx.rp.app.consultas, dtype=str, keep_default_na=False)


def raiz_c02(cx: Contexto) -> Resultado:
    from mtx import evaluacion, pool, promocion
    from mtx.entrega import COLUMNAS_ENTIDADES, COLUMNAS_GOLD, COLUMNAS_RESULTADOS_IE, _cabecera
    from mtx.ranking import COLUMNAS_RANKING

    titulo = "Seis CSV v2 en la raíz, con columnas exactas y copia de salida/v2 (D28)"
    det = promocion.verificar(cx.raiz)
    columnas = dict(zip(promocion.NOMBRES, (COLUMNAS_RANKING, pool.COLUMNAS_JUICIOS,
                                            evaluacion.COLUMNAS_RESULTADOS_IR, COLUMNAS_ENTIDADES,
                                            COLUMNAS_GOLD, COLUMNAS_RESULTADOS_IE)))
    for n, cols in columnas.items():
        ruta = cx.raiz / n
        if not ruta.exists():
            continue
        if ruta.read_bytes().startswith(b"\xef\xbb\xbf"):
            det.append(f"{n}: tiene BOM")
        if _cabecera(ruta) != cols:
            det.append(f"{n}: columnas {_cabecera(ruta)}; se esperan {cols}")
    return Resultado(2, titulo, FALLA if det else OK,
                     det or ["los seis son copia de salida/v2 y coinciden con el registro"])


def raiz_c03(cx: Contexto) -> Resultado:
    from mtx.ranking import validar_ranking

    titulo = "ranking.csv v2: 15 × 4 × 10, preprocesamiento ganador, rangos, pasajes y ventanas"
    r = pd.read_csv(cx.raiz / "ranking.csv", dtype=str, keep_default_na=False)
    cons = _consultas(cx)
    det = validar_ranking(r, cons)
    esperado = len(cons) * 4 * 10
    if len(r) != esperado:
        det.append(f"{len(r)} filas; se esperan {esperado} ({len(cons)} × 4 × 10)")
    if not pd.to_numeric(r["puntaje"], errors="coerce").map(pd.notna).all():
        det.append("Hay puntajes no finitos")
    faltan = set(r["passage_id"]) - set(cx.pasajes()["passage_id"])
    if faltan:
        det.append(f"{len(faltan)} passage_id no existen en data/pasajes.parquet")
    return Resultado(3, titulo, FALLA if det else OK, det or [f"{len(r)} filas válidas"])


def raiz_c04(cx: Contexto) -> Resultado:
    from mtx import evaluacion_v2 as E

    titulo = "juicios_relevancia.csv v2: mayoría de 3 sobre el 100 % del pool v2, {0, 1}"
    det = E.validar_insumos(_rutas_ir_v2(cx))
    j = pd.read_csv(cx.raiz / "juicios_relevancia.csv", dtype=str, keep_default_na=False)
    pool_v2 = pd.read_csv(cx.raiz / S2 / "04_pool.csv", dtype=str, keep_default_na=False)
    if set(zip(j["query_id"], j["passage_id"])) != set(zip(pool_v2["query_id"],
                                                         pool_v2["passage_id"])):
        det.append("los juicios no cubren exactamente los pares de salida/v2/04_pool.csv")
    if len(j) != len(pool_v2):
        det.append(f"{len(j)} juicios para {len(pool_v2)} pares del pool")
    if not set(j["relevante"]) <= {"0", "1"}:
        det.append("hay valores de relevante fuera de {0, 1}")
    return Resultado(4, titulo, FALLA if det else OK,
                     det or [f"{len(j)} juicios agregados del cierre v2 (D24)"])


def raiz_c05(cx: Contexto) -> Resultado:
    from mtx import evaluacion
    from mtx import evaluacion_v2 as E

    titulo = "resultados_ir.csv v2 se regenera con el kit; ganador por D28"
    rk, ju, res_r = (cx.raiz / n for n in ("ranking.csv", "juicios_relevancia.csv",
                                           "resultados_ir.csv"))
    det = []
    with tempfile.TemporaryDirectory() as tmp:
        nuevo = adaptadores_kit.ejecutar_evaluador("ir", ju, rk, Path(tmp))
        if nuevo.read_bytes() != res_r.read_bytes():
            det.append("El kit no reproduce resultados_ir.csv: `make evaluar-ir-v2` y "
                       "`make promover-v2`")
    det += evaluacion.validar_resultados_ir(evaluacion.leer_resultados(res_r), _consultas(cx))
    ruta_m = cx.raiz / "data" / "v2" / "mejor_modelo.json"
    m = json.loads(ruta_m.read_text(encoding="utf-8"))
    ocho = evaluacion.leer_resultados(cx.raiz / S2 / "05_ir_8_variantes.csv")
    if m.get("modelo") != E.elegir_ganador_v2(ocho)["modelo"]:
        det.append("data/v2/mejor_modelo.json no sigue la regla D28")
    for clave, ruta in (("sha256_ranking_csv_v2", rk), ("sha256_juicios_relevancia_csv_v2", ju)):
        if m.get(clave) != adaptadores_kit.sha256_archivo(ruta):
            det.append(f"data/v2/mejor_modelo.json: {clave} ya no corresponde a {ruta.name}")
    return Resultado(5, titulo, FALLA if det else OK,
                     det or [(f"el kit reproduce la raíz; ganador {m.get('modelo')} (MAP "
                             f"{m.get('MAP')})")])


def raiz_c06(cx: Contexto) -> Resultado:
    from mtx import fusion

    titulo = "entidades.csv v2: método, offsets, claves, reglas FECHA v2 congeladas"
    ent = pd.read_csv(cx.raiz / "entidades.csv", dtype={"passage_id": str, "query_id": str},
                      keep_default_na=False)
    det = fusion.validar_entidades(ent, dict(zip(cx.pasajes()["passage_id"],
                                                 cx.pasajes()["texto"])))
    resumen = cx.raiz / S2 / "08_resumen_extraccion.json"
    if not resumen.exists():
        det.append("falta salida/v2/08_resumen_extraccion.json")
    elif not json.loads(resumen.read_text(encoding="utf-8")).get("reglas_fecha_v2_vigentes"):
        det.append("la extracción v2 se corrió con reglas distintas de `reglas-fecha-v2`")
    return Resultado(6, titulo, FALLA if det else OK,
                     det or [f"{len(ent)} filas; contrato de 8 columnas y offsets en verde"])


def raiz_c07(cx: Contexto) -> Resultado:
    titulo = "gold_entidades.csv v2: gold v1 más partes A y B, cierre v2, offsets"
    if not (cx.raiz / "anotaciones" / "cierre_gold_v2.json").exists():
        return Resultado(7, titulo, FALLA, ["la raíz es v2 pero no existe cierre_gold_v2.json"])
    g = pd.read_csv(cx.raiz / "gold_entidades.csv", dtype={"passage_id": str},
                    keep_default_na=False)
    textos = dict(zip(cx.pasajes()["passage_id"], cx.pasajes()["texto"]))
    det = []
    for r in g.itertuples(index=False):
        t = textos.get(r.passage_id)
        if t is None:
            det.append(f"{r.passage_id}: no existe en data/pasajes.parquet")
        elif t[int(r.inicio):int(r.fin)] != r.texto:
            det.append(f"{r.passage_id} {r.inicio}-{r.fin}: el texto no coincide con el pasaje")
    if g.duplicated(["passage_id", "tipo", "inicio", "fin"]).any():
        det.append("hay entidades repetidas")
    return Resultado(7, titulo, FALLA if det else OK,
                     det[:10] or [(f"{len(g)} entidades en {g['passage_id'].nunique()} pasajes; "
                                  "offsets en verde")])


def raiz_c08(cx: Contexto) -> Resultado:
    from mtx.entrega import COLUMNAS_RESULTADOS_IE

    titulo = "resultados_ie.csv v2 reproducible con el kit sobre el gold v2"
    ruta = cx.raiz / "resultados_ie.csv"
    det = []
    with tempfile.TemporaryDirectory() as tmp:
        nuevo = adaptadores_kit.ejecutar_evaluador("ie", cx.raiz / "gold_entidades.csv",
                                                    cx.raiz / "entidades.csv", Path(tmp))
        if nuevo.read_bytes() != ruta.read_bytes():
            det.append("El kit no reproduce resultados_ie.csv: `make evaluar-ie-v2` y "
                       "`make promover-v2`")
    res = pd.read_csv(ruta)
    if list(res.columns) != COLUMNAS_RESULTADOS_IE:
        det.append(f"columnas de resultados_ie.csv: {list(res.columns)}")
    faltan = [m for m in ("regla", "modelo", "combinado")
              if not ((res["metodo"] == m) & (res["tipo"] == "TODOS")).any()]
    if faltan:
        det.append(f"faltan filas TODOS de {faltan}")
    if not (cx.raiz / S2 / "09_referencias_f1.csv").exists():
        det.append("falta salida/v2/09_referencias_f1.csv")
    return Resultado(8, titulo, FALLA if det else OK,
                     det or ["el kit reproduce la raíz; referencias del F1 presentes"])


RAIZ_V2 = {2: raiz_c02, 3: raiz_c03, 4: raiz_c04, 5: raiz_c05, 6: raiz_c06, 7: raiz_c07,
           8: raiz_c08}


CONDICIONES_V2 = [c16_juicios_v2, c17_orden, c18_muestras, c19_ir_v2, c20_ie_v2, c21_tablas_v2,
                  c22_presentacion_v2]
