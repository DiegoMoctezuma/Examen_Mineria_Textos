"""08b · Sorteo de la muestra gold y del conjunto de selección (PRD §6.11, D10, U13). `make muestra-gold`.

Requisitos: etiqueta `reglas-congeladas` (D15) y `data/mejor_modelo.json`. Escribe
`anotaciones/muestra_gold.csv` (20 pasajes, 2 por consulta) y, con `--seleccion`,
`anotaciones/muestra_seleccion.csv` (6 pasajes, P1, solo si se comparan modelos NER). Si un
manifiesto ya existe y el sorteo daría otro, se detiene sin sobrescribir. Registra en
`salida/08b_excluidos_muestra.csv` los pasajes excluidos por criterio objetivo (U13) y en
`salida/08b_resumen_muestra.json` los conteos. No imprime textos ni predicciones.

v2 (PRD v2 D31, WP-08), `make muestra-gold-v2 PARTES=seleccion,a` (sáb 14) o `PARTES=b` (dom 15):
escribe `anotaciones/v2/muestra_seleccion.csv`, `muestra_gold_a.csv` y `muestra_gold_b.csv`, con
hashes de texto, y su registro en `anotaciones/v2/muestreo_v2.json`. El ámbito IE v1, el gold v1 y
el pool v1 se leen de la etiqueta `v1.0-entrega`, no de `salida/`, para que la exclusión no cambie
aunque v2 regenere archivos. B sale del pool v2 (`--pool`) y excluye además selección y A. Solo
imprime conteos: ni IDs con rangos, ni textos, ni predicciones (D32).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from mtx import ambito, config, muestreo
from mtx.app import componentes as C

ANOT = config.DIR_ANOTACIONES


def _escribir(df: pd.DataFrame, ruta) -> str:
    """'escrito', 'sin cambios' o 'distinto' (no se sobrescribe)."""
    nuevo = df.to_csv(index=False, lineterminator="\n").encode("utf-8")
    if ruta.exists():
        return "sin cambios" if ruta.read_bytes() == nuevo else "distinto"
    C.escribir_atomico(ruta, nuevo, respaldo=False)
    return "escrito"


# --------------------------------------------------------------------------- v2

ETIQUETA_V1 = "v1.0-entrega"
CONSULTAS_AB = [f"Q{i}" for i in range(1, 11)]
CONSULTAS_B = [f"Q{i}" for i in range(11, 16)]
ESPERADO_V2 = {"seleccion": (CONSULTAS_AB, 1), "a": (CONSULTAS_AB, 1), "b": (CONSULTAS_B, 2)}


def _git_show(ruta: str, etiqueta: str = ETIQUETA_V1) -> str:
    r = subprocess.run(["git", "show", f"{etiqueta}:{ruta}"], cwd=config.RAIZ,
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise FileNotFoundError(f"No se pudo leer {ruta} en {etiqueta}: {r.stderr.strip()}")
    return r.stdout


def _sha_texto(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def exclusion_v1() -> tuple[set[str], dict]:
    """Pasajes con predicciones visibles en v1: ámbito IE (top-10 del ganador) y gold v1."""
    rk_txt = _git_show("salida/ranking.csv")
    modelo = json.loads(_git_show("data/mejor_modelo.json"))["modelo"]
    rk = pd.read_csv(io.StringIO(rk_txt), dtype={"passage_id": str})
    amb = set(rk.loc[rk["modelo"] == modelo, "passage_id"])
    gold_txt = _git_show("anotaciones/muestra_gold.csv")
    gold = set(pd.read_csv(io.StringIO(gold_txt), dtype={"passage_id": str})["passage_id"])
    if not amb:
        raise ValueError(f"El ranking de {ETIQUETA_V1} no tiene filas de {modelo}")
    return amb | gold, {
        "etiqueta": ETIQUETA_V1, "modelo_ir_v1": modelo, "ambito_ie_v1": len(amb),
        "gold_v1": len(gold), "gold_v1_dentro_del_ambito": len(gold & amb),
        "sha256_ranking_v1": _sha_texto(rk_txt), "sha256_muestra_gold_v1": _sha_texto(gold_txt),
        "sha256_ids_excluidos": _sha_texto("\n".join(sorted(amb | gold))),
    }


def main_v2(partes: list[str], ruta_pool: str | None) -> int:
    dir_v2 = ANOT / muestreo.SUBDIR_V2
    excluir, reg_excl = exclusion_v1()
    n_v1 = len(excluir)
    if partes == ["seleccion", "a"]:
        pool_txt, origen_pool = _git_show("salida/04_pool.csv"), f"{ETIQUETA_V1}:salida/04_pool.csv"
    elif partes == ["b"]:
        previas = [dir_v2 / muestreo.ARCHIVO_PARTE_V2[p] for p in ("seleccion", "a")]
        if not all(p.exists() for p in previas):
            print("La parte B se sortea después de la selección y la parte A (faltan sus "
                  "manifiestos).")
            return 1
        for p in previas:
            excluir |= set(pd.read_csv(p, dtype={"passage_id": str})["passage_id"])
        ruta = Path(ruta_pool or config.DIR_SALIDA / "v2" / "04_pool.csv")
        if not ruta.exists():
            print(f"Falta el pool v2 ({ruta}); la parte B se sortea con él congelado (WP-05).")
            return 1
        pool_txt, origen_pool = ruta.read_text(encoding="utf-8"), str(ruta.relative_to(config.RAIZ))
    else:
        print("PARTES debe ser `seleccion,a` (sáb 14) o `b` (dom 15).")
        return 1
    pool = pd.read_csv(io.StringIO(pool_txt), dtype={"passage_id": str})
    universo = muestreo.universo_con_filtro(pool, excluir)
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "texto", "inicio_cuerpo", "texto_sha256"])
    pasajes = pasajes[pasajes["passage_id"].isin(set(universo["passage_id"]))]
    plan = [(p, *ESPERADO_V2[p]) for p in partes]
    try:
        m = muestreo.sortear_v2(universo, pasajes, plan)
    except muestreo.MuestraInviable as e:
        print(f"{e}\nRegistra la excepción en docs/decisiones.md antes de seguir.")
        return 1
    err = muestreo.errores_muestra_v2(m.partes, excluir, ESPERADO_V2)
    if err:
        print("El sorteo no pasa la comprobación; no se escribe nada:", *err, sep="\n- ")
        return 1

    estados = {}
    for parte, df in m.partes.items():
        ruta = dir_v2 / muestreo.ARCHIVO_PARTE_V2[parte]
        estados[ruta.name] = _escribir(df, ruta)
    if "distinto" in estados.values():
        print("Un manifiesto v2 existente no coincide con el sorteo; no se sobrescribe. Revisa "
              "con la skill gold-anotacion (sustitución U13 o cambio de insumos).", estados)
        return 1
    grupo = "+".join(partes)
    ruta_reg = dir_v2 / "muestreo_v2.json"
    registro = json.loads(ruta_reg.read_text(encoding="utf-8")) if ruta_reg.exists() else {}
    nuevo = {
        "semilla": config.SEMILLA, "regla": "PRD v2 D31: pool con filtro, sin el ámbito IE ni el "
        "gold v1; emparejamiento global; sin estratos; exclusión U13 antes del sorteo",
        "pool": origen_pool, "sha256_pool": _sha_texto(pool_txt),
        "universo_pares": m.universo_pares, "universo_pasajes": m.universo_pasajes,
        "excluidos_u13": m.excluidos.to_dict("records"), "exclusion_v1": reg_excl,
        "excluidos_por_partes_previas": len(excluir) - n_v1,
        "partes": {p: {"archivo": f"{muestreo.SUBDIR_V2}/{muestreo.ARCHIVO_PARTE_V2[p]}",
                       "pasajes": len(df), "por_consulta": ESPERADO_V2[p][1],
                       "sha256": hashlib.sha256((dir_v2 / muestreo.ARCHIVO_PARTE_V2[p])
                                                .read_bytes()).hexdigest()}
                   for p, df in m.partes.items()},
    }
    previo = registro.get(grupo)
    if previo and {k: v for k, v in previo.items() if k != "fecha"} != nuevo:
        print(f"El registro de {grupo} en {ruta_reg.name} no coincide; no se sobrescribe.")
        return 1
    if not previo:
        registro[grupo] = {"fecha": datetime.now().isoformat(timespec="seconds"), **nuevo}
        C.escribir_atomico(ruta_reg, (json.dumps(registro, ensure_ascii=False, indent=2) + "\n")
                           .encode("utf-8"), respaldo=False)
    print(json.dumps({"grupo": grupo, "archivos": estados,
                      "universo_pasajes": m.universo_pasajes,
                      "excluidos_u13": len(m.excluidos),
                      "por_parte": {p: len(df) for p, df in m.partes.items()}},
                     ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seleccion", action="store_true",
                    help="escribe también el conjunto de selección (P1)")
    ap.add_argument("--v2", action="store_true", help="muestreo v2 (PRD v2 D31)")
    ap.add_argument("--partes", default="seleccion,a",
                    help="v2: `seleccion,a` (sáb 14) o `b` (dom 15)")
    ap.add_argument("--pool", default=None, help="v2, parte B: pool v2 (salida/v2/04_pool.csv)")
    a = ap.parse_args(argv)
    if a.v2:
        return main_v2([p.strip() for p in a.partes.split(",") if p.strip()], a.pool)
    if not C.reglas_congeladas():
        print("Falta la etiqueta `reglas-congeladas` (D15): congela reglas, gazetteers y "
              "criterio con `make congelar` antes de sortear la muestra.")
        return 1
    amb = ambito.ambito_ie()
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "texto", "inicio_cuerpo", "texto_sha256"])
    pasajes = pasajes[pasajes["passage_id"].isin(set(amb["passage_id"]))]
    try:
        m = muestreo.sortear(amb, pasajes)
    except muestreo.MuestraInviable as e:
        print(f"{e}\nRegistra la excepción en docs/decisiones.md antes de seguir.")
        return 1

    estados = {"muestra_gold.csv": _escribir(m.gold, ANOT / "muestra_gold.csv")}
    if a.seleccion:
        estados["muestra_seleccion.csv"] = _escribir(m.seleccion, ANOT / "muestra_seleccion.csv")
    if "distinto" in estados.values():
        print("Un manifiesto existente no coincide con el sorteo; no se sobrescribe. Revisa con "
              "la skill gold-anotacion (sustitución U13 o cambio de insumos).", estados)
        return 1
    m.excluidos.to_csv(config.DIR_SALIDA / "08b_excluidos_muestra.csv", index=False,
                       lineterminator="\n")
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "modelo_ir": ambito.mejor_modelo(), "semilla": config.SEMILLA,
        "universo_pares": len(amb), "universo_pasajes": int(amb["passage_id"].nunique()),
        "excluidos_u13": len(m.excluidos), "gold": len(m.gold),
        "seleccion": len(m.seleccion) if a.seleccion else 0,
        "estratos_rango_1_5_y_6_10": m.estratos_respetados, "avisos": m.avisos,
        "archivos": estados,
    }
    (config.DIR_SALIDA / "08b_resumen_muestra.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
