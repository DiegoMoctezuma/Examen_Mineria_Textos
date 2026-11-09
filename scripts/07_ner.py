"""07 · NER con modelo (PRD §6.8). `make ner`.

`--modelo <slug>` (por defecto el principal de `config/ner.yaml`), `--forzar` reinfiere aunque haya
caché, `--verificar` corre además la verificación técnica P06 (requiere red la primera vez).

Ámbito: pasajes únicos del top-10 con filtro del mejor modelo de IR (≤100). Salidas:
`data/cache_ner/{slug}@{rev}/` (crudo, versionado en git), `salida/entidades_{slug}.csv` (8
columnas, `metodo = modelo`), `salida/07_entidades_{slug}_sin_union.csv` (antes de la unión
interpalabra, para medir su efecto), `salida/07_uniones_spans.csv`, `salida/07_registro_ner.json` y,
si no existe, `data/modelo_ner.json` provisional (`criterio: tecnico`, D09).

Las predicciones no se muestran en la app mientras el gold esté abierto (modo ciego).
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime

import pandas as pd

from mtx import ambito, config
from mtx import ner_modelo as N

SALIDA = config.DIR_SALIDA
RUTA_MODELO_NER = config.DIR_DATA / "modelo_ner.json"
EJEMPLOS_DESARROLLO = [
    ("El secretario de Salud, Jorge Alcocer Varela, viajó con Andrés Manuel López Obrador a "
    "Tabasco para ver la refinería de Dos Bocas de Pemex."),
    "La Comisión Federal de Electricidad y el IMSS firmaron un convenio en Mérida, Yucatán.",
]


def verificar(cfg: N.ConfigModelo) -> list[str]:
    """P06 sin gold: pesos de token-classification, mapa real de etiquetas, tokenizador rápido
    con offsets, límite real y funcionamiento sobre ejemplos de desarrollo sintéticos."""
    import torch
    import transformers
    from transformers import AutoModelForTokenClassification

    lineas = [f"# Verificación técnica del NER (P06): `{cfg.repo_id}`", "",
              f"- Fecha: {datetime.now().isoformat(timespec='seconds')}",
              f"- Revisión fija: `{cfg.revision}`",
              (f"- Entorno: Python {platform.python_version()}, transformers "
              f"{transformers.__version__}, torch {torch.__version__} (CPU, device={cfg.device})")]
    t0 = time.perf_counter()
    m = AutoModelForTokenClassification.from_pretrained(cfg.repo_id, revision=cfg.revision)
    pipe, tok = N.construir_pipeline(cfg)
    lineas.append(f"- Carga del modelo y el pipeline: {time.perf_counter() - t0:.1f} s")
    arq = m.config.architectures or []
    etiquetas = sorted({N.etiqueta_base(v) for v in m.config.id2label.values()} - {"O"})
    limite = min(m.config.max_position_embeddings, tok.model_max_length)
    limite_real = limite - tok.num_special_tokens_to_add()
    enc = tok("Hola México", return_offsets_mapping=True)
    checks = [
        ("Pesos de clasificación de tokens (cabeza NER)",
         any("TokenClassification" in a for a in arq), ", ".join(arq)),
        ("Mapa real de etiquetas (`id2label`)", bool(etiquetas),
         ", ".join(sorted(m.config.id2label.values()))),
        ("Etiquetas del mapa del proyecto presentes en el modelo",
         set(cfg.mapa_etiquetas) <= set(etiquetas),
         f"mapa {cfg.mapa_etiquetas}; descartadas {list(cfg.descartadas)}"),
        ("Tokenizador rápido con `offset_mapping`", tok.is_fast and "offset_mapping" in enc,
         f"is_fast={tok.is_fast}"),
        ("Límite real coincide con `config/ner.yaml`", limite_real == cfg.max_length_real,
         f"min(max_position_embeddings, model_max_length) − especiales = {limite_real}"),
    ]
    for i, texto in enumerate(EJEMPLOS_DESARROLLO, 1):
        pp = N.posprocesar(texto, N.inferir_pasaje(texto, pipe, tok, cfg), cfg)
        ok = all(texto[e["inicio"]:e["fin"]] == e["texto"] for e in pp.entidades)
        checks.append((f"Ejemplo de desarrollo {i} (sintético, fuera de la muestra gold)",
                       ok and bool(pp.entidades),
                       "; ".join(f"{e['tipo']} «{e['texto']}»" for e in pp.entidades)))
    lineas += ["", "| Comprobación | Resultado | Detalle |", "| --- | --- | --- |"]
    lineas += [f"| {n} | {'✔' if ok else '✘'} | {d} |" for n, ok, d in checks]
    fallas = [n for n, ok, _ in checks if not ok]
    lineas += ["", "Resultado: " + ("**aprobado**." if not fallas
                                    else f"**falla** en {', '.join(fallas)}.")]
    (SALIDA / "07_verificacion_ner.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return fallas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modelo")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--verificar", action="store_true")
    a = ap.parse_args(argv)
    principal, cfgs = N.cargar_config()
    slug = a.modelo or principal
    cfg = cfgs[slug]

    if a.verificar:
        fallas = verificar(cfg)
        print("Verificación P06:", "aprobada" if not fallas else f"falla: {fallas}",
              "→ salida/07_verificacion_ner.md")
        if fallas:
            return 1

    amb = ambito.ambito_ie()
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "texto", "texto_sha256"])
    unicos = pasajes[pasajes["passage_id"].isin(set(amb["passage_id"]))].reset_index(drop=True)
    t0 = time.perf_counter()
    crudos, reg = N.ejecutar(cfg, unicos, forzar=a.forzar)
    total = time.perf_counter() - t0

    textos = dict(zip(unicos["passage_id"], unicos["texto"]))
    filas, sin_union, uniones, descartadas = [], [], [], {}
    for pid in unicos["passage_id"]:
        pp = N.posprocesar(textos[pid], crudos[pid]["entidades_crudas"], cfg, pid)
        filas += [{"passage_id": pid, **{k: e[k] for k in ("tipo", "texto", "inicio", "fin")}}
                  for e in pp.entidades]
        sin_union += [{"passage_id": pid, **{k: e[k] for k in ("tipo", "texto", "inicio", "fin")}}
                      for e in pp.sin_union_interpalabra]
        uniones += pp.uniones
        for k, v in pp.descartadas.items():
            descartadas[k] = descartadas.get(k, 0) + v

    def exportar(lista: list[dict], ruta) -> pd.DataFrame:
        df = amb[["query_id", "doc_id", "passage_id"]].merge(
            pd.DataFrame(lista, columns=["passage_id", "tipo", "texto", "inicio", "fin"]),
            on="passage_id")
        df["metodo"] = "modelo"
        df = df[N.COLUMNAS_ENTIDADES].sort_values(["query_id", "passage_id", "inicio", "fin"])
        df.to_csv(ruta, index=False, lineterminator="\n")
        return df

    ent = exportar(filas, SALIDA / f"entidades_{slug}.csv")
    exportar(sin_union, SALIDA / f"07_entidades_{slug}_sin_union.csv")
    pd.DataFrame(uniones, columns=N.COLUMNAS_UNIONES).to_csv(
        SALIDA / "07_uniones_spans.csv", index=False, lineterminator="\n")

    registro = {
        "modelo": cfg.repo_id, "slug": slug, "revision": cfg.revision,
        "version_posproceso": cfg.version_posproceso,
        "parametros_inferencia": cfg.parametros_inferencia(),
        "pasajes": len(unicos), **N.registro_dict(reg),
        "segundos_totales": round(total, 2),
        "entidades_por_tipo": ent.drop_duplicates(["passage_id", "tipo", "inicio", "fin"])[
            "tipo"].value_counts().to_dict(),
        "uniones_interpalabra": len(uniones), "descartadas": descartadas,
    }
    previo = SALIDA / "07_registro_ner.json"
    hist = json.loads(previo.read_text()) if previo.exists() else {}
    hist[slug] = registro
    previo.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not RUTA_MODELO_NER.exists() and slug == principal:
        RUTA_MODELO_NER.write_text(json.dumps(N.modelo_ner_json(cfg), ensure_ascii=False,
                                              indent=2) + "\n", encoding="utf-8")
        print("data/modelo_ner.json provisional (criterio técnico, D09)")
    print(json.dumps(registro, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
