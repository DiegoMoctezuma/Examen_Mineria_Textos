"""09 · Evaluación de IE (PRD §6.12). `make evaluar-ie`.

Comprueba antes de evaluar: `reglas-congeladas` antes del primer commit del gold, gold cerrado y
válido, `data/modelo_ner.json` versionado antes del gold (D09) y `entidades.csv` producido por
`make extraer` con ese modelo. Luego:

1. Cifra oficial: `kit/evaluar.py ie gold_entidades.csv entidades.csv` → `resultados_ie.csv`
   (raíz y `salida/`, sin tocar).
2. `salida/09_ie_detalle.csv`: P/R/F1, TP/FP/FN y soporte por método y tipo, verificado contra
   el kit; estados `sin_cobertura` y `no_aplicable`.
3. `salida/09_evaluacion_20_ids.csv`: lo mismo sobre los 20 IDs del manifiesto (P04).
4. `salida/09_analisis_errores.csv` y `salida/09_resumen_errores.csv` (método combinado).
5. Figuras `reporte/figuras/ie_f1_por_tipo_metodo.png` e `ie_errores_por_categoria.png`.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

from mtx import adaptadores_kit, config, manifiesto
from mtx import evaluacion_ie as E
from mtx import gold as G
from mtx import reglas as R
from mtx.fusion import CLAVE, sin_acentos

SALIDA = config.DIR_SALIDA
FIGURAS = config.RAIZ / "reporte" / "figuras"


def _primer_commit(ruta: str) -> str:
    log = manifiesto.git("log", "--format=%H", "--diff-filter=A", "--", ruta).splitlines()
    return log[-1] if log else ""


def prerrequisitos(rg: G.RutasGold, pasajes: pd.DataFrame) -> list[str]:
    err = []
    if not rg.cierre.exists():
        err.append("Falta anotaciones/cierre_gold.json: el gold no está cerrado.")
    v = G.validar_gold(rg, pasajes)
    err += [f"validar_gold: {e}" for e in v.errores]
    precede = G.etiqueta_precede_al_gold(rg.gold)
    if precede:
        err.append(precede)
    c_modelo, c_gold = (_primer_commit("data/modelo_ner.json"),
                        _primer_commit("anotaciones/gold_entidades.csv"))
    antes = c_gold and c_modelo != c_gold and subprocess.run(
        ["git", "merge-base", "--is-ancestor", c_modelo, c_gold], cwd=config.RAIZ,
        check=False).returncode == 0
    if not c_modelo or (c_gold and not antes):
        err.append("data/modelo_ner.json debe estar versionado antes del primer commit del gold "
                   "(D09).")
    man = json.loads(manifiesto.MANIFIESTO.read_text()) if manifiesto.MANIFIESTO.exists() else {}
    ext = man.get("08_extraer", {})
    elegido = json.loads((config.DIR_DATA / "modelo_ner.json").read_text())
    ent = config.RAIZ / "entidades.csv"
    if not ent.exists():
        err.append("Falta entidades.csv: corre `make extraer`.")
    elif ext.get("salidas", {}).get("entidades.csv") != manifiesto.sha256(ent):
        err.append("entidades.csv no es el que registró `make extraer` en el manifiesto.")
    elif (ext.get("modelo"), ext.get("revision")) != (elegido["modelo"], elegido["revision"]):
        err.append("entidades.csv se generó con otro modelo que data/modelo_ner.json.")
    return err


def obras() -> set[str]:
    nombres = set()
    for ruta in (R.KIT_GAZETTEER, R.GAZ_LOC, R.GAZ_EXTENDIDO):
        g = R.leer_gazetteer(ruta)
        for f in g[g["tipo"].str.lower() == "obra"].to_dict("records"):
            for x in [f["nombre"], *f.get("siglas", "").split("|"), *f.get("variantes", "").split("|")]:
                if x.strip():
                    nombres.add(sin_acentos(x.strip()))
    return nombres


def main() -> int:
    t0 = time.perf_counter()
    rg = G.rutas_gold()
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "texto", "texto_sha256", "inicio_cuerpo"])
    err = prerrequisitos(rg, pas)
    if err:
        print("No se evalúa:", *err, sep="\n- ")
        return 1

    gold_raiz, ent_raiz = config.RAIZ / "gold_entidades.csv", config.RAIZ / "entidades.csv"
    with tempfile.TemporaryDirectory() as tmp:
        oficial = adaptadores_kit.ejecutar_evaluador("ie", gold_raiz, ent_raiz,
                                                     Path(tmp)).read_bytes()
    for destino in (config.RAIZ / "resultados_ie.csv", SALIDA / "resultados_ie.csv"):
        destino.write_bytes(oficial)
    kit = pd.read_csv(SALIDA / "resultados_ie.csv")

    gold = pd.read_csv(gold_raiz, dtype={"passage_id": str})
    ent = pd.read_csv(ent_raiz, dtype={"passage_id": str, "query_id": str})
    ids_kit = set(gold["passage_id"])
    det = E.detalle(gold, ent, ids_kit)
    distinto = E.coincide_con_kit(det, kit)
    if distinto:
        print("El detalle no reproduce al kit (revisar antes de reportar):", *distinto,
              sep="\n- ")
        return 1
    R.escribir_csv(det, SALIDA / "09_ie_detalle.csv")

    man = pd.read_csv(rg.muestra, dtype={"passage_id": str})
    ids_20 = set(man["passage_id"])
    comp = E.detalle(gold, ent, ids_20).assign(
        base="20_ids_del_manifiesto", pasajes_base=len(ids_20), pasajes_kit=len(ids_kit),
        pasajes_sin_entidades_gold=len(ids_20 - ids_kit))
    R.escribir_csv(comp, SALIDA / "09_evaluacion_20_ids.csv")

    enr = pd.read_csv(SALIDA / "entidades_enriquecidas.csv", dtype={"passage_id": str},
                      keep_default_na=False)
    pred = enr.drop_duplicates(CLAVE)[[*CLAVE, "texto", "metodo", "fuentes"]]
    errores = E.analizar_errores(gold, pred, pas, obras())
    R.escribir_csv(errores, SALIDA / "09_analisis_errores.csv")
    resumen = E.resumen_errores(errores)
    R.escribir_csv(resumen, SALIDA / "09_resumen_errores.csv")

    avisos = E.alertas_u19(det)
    figuras: list[Path] = []
    try:
        figuras = E.figuras_ie(det, errores, FIGURAS)
    except Exception as e:  # noqa: BLE001 - sin kaleido la cifra oficial no se pierde
        avisos.append(f"No se generaron las figuras: {e}")

    salidas = [config.RAIZ / "resultados_ie.csv", SALIDA / "resultados_ie.csv",
               SALIDA / "09_ie_detalle.csv", SALIDA / "09_evaluacion_20_ids.csv",
               SALIDA / "09_analisis_errores.csv", SALIDA / "09_resumen_errores.csv", *figuras]
    manifiesto.registrar(
        "09_evaluar_ie", [gold_raiz, ent_raiz, SALIDA / "entidades_enriquecidas.csv",
                          adaptadores_kit.DIR_KIT / "evaluar.py", rg.cierre],
        salidas, time.perf_counter() - t0,
        {"pasajes_evaluados_kit": len(ids_kit), "pasajes_manifiesto": len(ids_20),
         "avisos": avisos})

    t = det.set_index(["metodo", "tipo"])
    print(kit.to_string(index=False))
    print(f"\nPasajes evaluados por el kit: {len(ids_kit)} de {len(ids_20)} del manifiesto.")
    print("F1 TODOS:", {m: float(t.at[(m, "TODOS"), "f1"]) for m in E.METODOS})
    print("Errores combinado:", errores.drop_duplicates(["error", "passage_id", "tipo", "inicio",
                                                         "fin"])["error"].value_counts().to_dict())
    for a in avisos:
        print("AVISO:", a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
