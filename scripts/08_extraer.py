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


def reglas_congeladas_vigentes() -> bool:
    """El código de reglas y `config/` coinciden con la etiqueta `reglas-congeladas`."""
    if not manifiesto.git("tag", "-l", "reglas-congeladas"):
        return False
    r = manifiesto.git("diff", "--name-only", "reglas-congeladas", "--", "src/mtx/reglas.py",
                       "src/mtx/normalizacion.py", "config/")
    return r == ""


def entidades_reglas(pasajes: pd.DataFrame) -> pd.DataFrame:
    R.gazetteer_por_defecto.cache_clear()
    gaz = R.gazetteer_por_defecto()
    filas = []
    for pid, texto, ic in zip(pasajes["passage_id"], pasajes["texto"], pasajes["inicio_cuerpo"]):
        for e in R.extraer_reglas_detalle(texto, int(ic), gaz).entidades:
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


def main() -> int:
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
