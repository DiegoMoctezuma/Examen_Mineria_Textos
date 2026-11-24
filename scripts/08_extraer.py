"""08 · Extracción final: reglas congeladas + NER fijado, fusionados (PRD §6.9). `make extraer`.

Sobre los pasajes únicos del top-10 con filtro del mejor modelo de IR:

1. Reglas: `extraer_reglas_detalle` con el gazetteer extendido (el código y la configuración
   deben ser los de `reglas-congeladas`; si no, la corrida queda marcada como exploratoria).
2. Modelo: el de `data/modelo_ner.json`, leído de la caché `data/cache_ner/` y posprocesado. No
   infiere: si falta un pasaje en la caché, se detiene y pide `make ner`.
3. Fusión por span exacto (D12) y asociación a cada consulta (T08).

Salidas: `entidades.csv` (raíz y `salida/`, 8 columnas), `salida/entidades_unicas.csv`,
`salida/entidades_enriquecidas.csv`, `salida/08_solapes_parciales.csv`,
`salida/08_resumen_extraccion.json` y la entrada `08_extraer` del manifiesto de ejecución.

`--v2` (PRD v2 D33, D34; WP-12, `make extraer-v2`): después de `cierre_gold_v2.json`, con FECHA
v2 (`fecha_v2.extraer_reglas_v2_detalle`, etiqueta `reglas-fecha-v2`), el NER de
`data/modelo_ner.json` v2 y el ámbito v2 (top-10 del ganador v2 ∪ gold v2). Mismos archivos, en
`salida/v2/`; la raíz conserva los de v1 hasta WP-14.
"""
from __future__ import annotations

import json
import shutil
import sys
import time

import pandas as pd

from mtx import ambito, config, fusion, manifiesto
from mtx import ner_modelo as N
from mtx import reglas as R

SALIDA = config.DIR_SALIDA
RUTA_MODELO_NER = config.DIR_DATA / "modelo_ner.json"
EXCLUIDOS_DE_REGLAS = (":(exclude)config/ner.yaml",)


def reglas_congeladas_vigentes() -> bool:
    """Ningún archivo que existía en `reglas-congeladas` (reglas, normalización, `config/`) se
    modificó, renombró ni borró. Los archivos agregados después (p. ej. la configuración de las
    tablas de H8) no forman parte de lo congelado y no cuentan. `config/ner.yaml` tampoco: el NER
    se congela aparte (D09, D34: `data/modelo_ner.json` y la clave de caché), y en v2 solo se le
    agregaron candidatos (2026-11-24, ver docs/decisiones.md)."""
    if not manifiesto.git("tag", "-l", "reglas-congeladas"):
        return False
    r = manifiesto.git("diff", "--name-only", "--diff-filter=MDRT", "reglas-congeladas", "--",
                       "src/mtx/reglas.py",
                       "src/mtx/normalizacion.py", "config/", *EXCLUIDOS_DE_REGLAS)
    return r == ""


def fecha_v2_vigente() -> bool:
    """`fecha_v2.py`, `reglas.py`, `normalizacion.py` y `config/` como en `reglas-fecha-v2`."""
    if not manifiesto.git("tag", "-l", "reglas-fecha-v2"):
        return False
    r = manifiesto.git("diff", "--name-only", "--diff-filter=MDRT", "reglas-fecha-v2", "--",
                       "src/mtx/fecha_v2.py", "src/mtx/reglas.py", "src/mtx/normalizacion.py",
                       "config/", *EXCLUIDOS_DE_REGLAS)
    return r == ""


def entidades_reglas(pasajes: pd.DataFrame, extractor=None) -> pd.DataFrame:
    """`extractor`: `reglas.extraer_reglas_detalle` (v1, por defecto) o el de FECHA v2."""
    extractor = extractor or R.extraer_reglas_detalle
    R.gazetteer_por_defecto.cache_clear()
    gaz = R.gazetteer_por_defecto()
    filas = []
    for pid, texto, ic in zip(pasajes["passage_id"], pasajes["texto"], pasajes["inicio_cuerpo"]):
        for e in extractor(texto, int(ic), gaz).entidades:
            filas.append({"passage_id": pid, "tipo": e.tipo, "texto": e.texto,
                          "inicio": e.inicio, "fin": e.fin, "fuente": e.fuente,
                          "en_marca": e.en_marca, "puntaje_modelo": None})
    return pd.DataFrame(filas, columns=fusion.COLUMNAS_FUENTE)


def entidades_modelo(pasajes: pd.DataFrame, cfg: N.ConfigModelo) -> pd.DataFrame:
    filas, faltan = [], []
    for pid, texto, sha, ic in zip(pasajes["passage_id"], pasajes["texto"],
                                   pasajes["texto_sha256"], pasajes["inicio_cuerpo"]):
        crudo = N.leer_cache(cfg, pid, sha)
        if crudo is None:
            faltan.append(pid)
            continue
        for e in N.posprocesar(texto, crudo["entidades_crudas"], cfg, pid).entidades:
            filas.append({"passage_id": pid, "tipo": e["tipo"], "texto": e["texto"],
                          "inicio": e["inicio"], "fin": e["fin"], "fuente": "modelo",
                          "en_marca": e["inicio"] < int(ic),
                          "puntaje_modelo": e["confianza"]})
    if faltan:
        raise SystemExit(f"Faltan {len(faltan)} pasajes en la caché NER ({faltan[:5]}…): "
                         "corre `make ner` antes de extraer.")
    return pd.DataFrame(filas, columns=fusion.COLUMNAS_FUENTE)


def main_v2() -> int:
    from mtx import cierres_v2, fecha_v2, ie_v2
    from mtx import gold_v2 as V

    t0 = time.perf_counter()
    if not cierres_v2.gold_cerrado():
        print("El gold v2 no está cerrado: no se extrae sobre sus pasajes (D32).", file=sys.stderr)
        return 1
    r = ie_v2.rutas_v2()
    elegido = json.loads(RUTA_MODELO_NER.read_text(encoding="utf-8"))
    if elegido.get("version") != 2 or not r["mejor"].exists():
        print("Faltan data/modelo_ner.json v2 o data/v2/mejor_modelo.json.", file=sys.stderr)
        return 1
    _, cfgs = N.cargar_config()
    cfg = cfgs[elegido["slug"]]
    if (cfg.repo_id, cfg.revision) != (elegido["modelo"], elegido["revision"]):
        raise SystemExit("config/ner.yaml no coincide con data/modelo_ner.json.")
    vigente = fecha_v2_vigente()
    if not vigente:
        print("AVISO: reglas o config/ difieren de `reglas-fecha-v2`: corrida EXPLORATORIA.")

    amb = ie_v2.ambito_ie_v2(r["ranking"], r["mejor"],
                             ie_v2.pasajes_gold_v2(V.cargar_config(), r["muestra_v1"]))
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "texto", "texto_sha256", "inicio_cuerpo",
                                   "fecha"])
    pas = pas[pas["passage_id"].isin(set(amb["passage_id"]))].reset_index(drop=True)
    textos = dict(zip(pas["passage_id"], pas["texto"]))

    reg = entidades_reglas(pas, fecha_v2.extraer_reglas_v2_detalle)
    mod = entidades_modelo(pas, cfg)
    unicas, solapes = fusion.fusionar_unicas(reg, mod)
    ent = fusion.asociar_consultas(unicas, amb)[fusion.COLUMNAS_ENTIDADES]
    errores = fusion.validar_entidades(ent, textos)
    if errores:
        print("entidades.csv v2 no cumple el contrato:", *errores, sep="\n- ")
        return 1
    doc = amb.drop_duplicates("passage_id").set_index("passage_id")["doc_id"]
    unicas_out = unicas.assign(doc_id=unicas["passage_id"].map(doc).astype(int))
    unicas_out = unicas_out.sort_values(["passage_id", "inicio", "fin", "tipo"])
    gaz = [R.leer_gazetteer(R.GAZ_EXTENDIDO), R.leer_gazetteer(R.GAZ_LOC)]
    version = (f"reglas-fecha-v2@{manifiesto.git('rev-parse', '--short', 'reglas-fecha-v2^{}')}"
               f"+{cfg.slug}+posproceso{cfg.version_posproceso}"
               + ("" if vigente else "+exploratorio"))
    enr = fusion.enriquecer(ent, unicas, dict(zip(pas["passage_id"], pas["fecha"])),
                            fusion.mapa_canonico(gaz), cfg.repo_id, cfg.revision, version,
                            normalizador_fecha=fecha_v2.normalizar_fecha_v2)
    config.DIR_SALIDA_V2.mkdir(parents=True, exist_ok=True)
    R.escribir_csv(amb, r["ambito"])
    R.escribir_csv(ent, r["entidades"])
    R.escribir_csv(unicas_out[fusion.COLUMNAS_UNICAS], r["unicas"])
    R.escribir_csv(enr, r["enriquecidas"])
    R.escribir_csv(solapes, r["solapes"])
    resumen = {
        "modelo": cfg.repo_id, "slug": cfg.slug, "revision": cfg.revision,
        "reglas_fecha_v2_vigentes": vigente, "version_extractor": version,
        "pasajes": len(pas), "pares_consulta_pasaje": len(amb),
        "pasajes_por_origen": amb.drop_duplicates("passage_id")["origen"].value_counts().to_dict(),
        "filas_entidades": len(ent), "entidades_unicas": len(unicas),
        "unicas_por_tipo_y_metodo": {t: g["metodo"].value_counts().to_dict()
                                     for t, g in unicas.groupby("tipo")},
        "solapes_parciales": solapes["clase"].value_counts().to_dict(),
        "segundos": round(time.perf_counter() - t0, 2),
    }
    r["resumen"].write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps({k: v for k, v in resumen.items() if k != "unicas_por_tipo_y_metodo"},
                     ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    if "--v2" in sys.argv[1:]:
        return main_v2()
    t0 = time.perf_counter()
    elegido = json.loads(RUTA_MODELO_NER.read_text(encoding="utf-8"))
    _, cfgs = N.cargar_config()
    cfg = cfgs[elegido["slug"]]
    if (cfg.repo_id, cfg.revision) != (elegido["modelo"], elegido["revision"]):
        raise SystemExit("config/ner.yaml no coincide con data/modelo_ner.json.")
    congeladas = reglas_congeladas_vigentes()
    if not congeladas:
        print("AVISO: reglas o config/ difieren de `reglas-congeladas`: corrida EXPLORATORIA.")

    amb = ambito.ambito_ie()
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "texto", "texto_sha256", "inicio_cuerpo",
                                   "fecha"])
    pas = pas[pas["passage_id"].isin(set(amb["passage_id"]))].reset_index(drop=True)
    textos = dict(zip(pas["passage_id"], pas["texto"]))

    reg, mod = entidades_reglas(pas), entidades_modelo(pas, cfg)
    unicas, solapes = fusion.fusionar_unicas(reg, mod)
    ent = fusion.asociar_consultas(unicas, amb)[fusion.COLUMNAS_ENTIDADES]
    errores = fusion.validar_entidades(ent, textos)
    if errores:
        print("entidades.csv no cumple el contrato:", *errores, sep="\n- ")
        return 1

    doc = amb.drop_duplicates("passage_id").set_index("passage_id")["doc_id"]
    unicas_out = unicas.assign(doc_id=unicas["passage_id"].map(doc).astype(int))
    unicas_out = unicas_out.sort_values(["passage_id", "inicio", "fin", "tipo"])
    gaz = [R.leer_gazetteer(R.GAZ_EXTENDIDO), R.leer_gazetteer(R.GAZ_LOC)]
    version = (f"reglas-congeladas@{manifiesto.git('rev-parse', '--short', 'reglas-congeladas^{}')}"
               f"+posproceso{cfg.version_posproceso}" + ("" if congeladas else "+exploratorio"))
    enr = fusion.enriquecer(ent, unicas, dict(zip(pas["passage_id"], pas["fecha"])),
                            fusion.mapa_canonico(gaz), cfg.repo_id, cfg.revision, version)

    rutas = {"entidades": SALIDA / "entidades.csv",
             "unicas": SALIDA / "entidades_unicas.csv",
             "enriquecidas": SALIDA / "entidades_enriquecidas.csv",
             "solapes": SALIDA / "08_solapes_parciales.csv"}
    R.escribir_csv(ent, rutas["entidades"])
    R.escribir_csv(unicas_out[fusion.COLUMNAS_UNICAS], rutas["unicas"])
    R.escribir_csv(enr, rutas["enriquecidas"])
    R.escribir_csv(solapes, rutas["solapes"])
    shutil.copyfile(rutas["entidades"], config.RAIZ / "entidades.csv")

    resumen = {
        "modelo": cfg.repo_id, "revision": cfg.revision, "criterio_modelo": elegido["criterio"],
        "reglas_congeladas_vigentes": congeladas, "version_extractor": version,
        "pasajes": len(pas), "pares_consulta_pasaje": len(amb),
        "filas_entidades": len(ent), "entidades_unicas": len(unicas),
        "unicas_por_metodo": unicas["metodo"].value_counts().to_dict(),
        "unicas_por_tipo_y_metodo": {t: g["metodo"].value_counts().to_dict()
                                     for t, g in unicas.groupby("tipo")},
        "solapes_parciales": solapes["clase"].value_counts().to_dict(),
        "reglas": len(reg), "modelo_filas": len(mod),
    }
    (SALIDA / "08_resumen_extraccion.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    entradas = [config.PASAJES_PARQUET, SALIDA / "ranking.csv", config.DIR_DATA / "mejor_modelo.json",
                RUTA_MODELO_NER, R.GAZ_EXTENDIDO, R.GAZ_LOC, config.DIR_CONFIG / "ner.yaml"]
    manifiesto.registrar("08_extraer", entradas, [*rutas.values(), config.RAIZ / "entidades.csv"],
                         time.perf_counter() - t0,
                         {"modelo": cfg.repo_id, "revision": cfg.revision,
                          "version_extractor": version})
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
