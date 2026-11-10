"""10 · Tablas de respuesta con evidencia (PRD §6.13). `make tablas`.

Sobre el top-10 con filtro del mejor modelo de cada consulta. Entradas:
`salida/entidades_enriquecidas.csv`, `salida/cantidades_auxiliares.csv`, `data/pasajes.parquet`,
`config/tablas_respuesta.yaml` y `config/excluir_tablas.yaml`. Salidas: `salida/respuestas.csv`
(16 columnas), `salida/10_evidencias.csv` (todas las evidencias con frecuencia, pasajes, discursos
y eventos), `salida/10_exclusiones.csv`, `salida/tablas_respuesta/Q1.md` … `Q10.md`, `todas.md` y
`salida/10_hashes_tablas.json` (huella de cada tabla para invalidar valoraciones).

Las valoraciones las escribe el alumno en la pestaña Valoraciones de la app
(`anotaciones/valoraciones.yaml`); este script solo las lee.
"""
from __future__ import annotations

import json
import sys
import time

import pandas as pd

from mtx import ambito, config, manifiesto
from mtx import reglas as R
from mtx import respuestas as RS
from mtx.app import componentes as C

SALIDA = config.DIR_SALIDA
DIR_TABLAS = SALIDA / "tablas_respuesta"
MAPA = config.DIR_CONFIG / "tablas_respuesta.yaml"
EXCLUIR = config.DIR_CONFIG / "excluir_tablas.yaml"


def ruta_valoraciones():
    return C.rutas().anotaciones / "valoraciones.yaml"


def main() -> int:
    t0 = time.perf_counter()
    import yaml

    mapa, lista = RS.cargar_mapa(MAPA), RS.cargar_exclusiones(EXCLUIR)
    cons = pd.read_csv(config.CONSULTAS_CSV, dtype=str, keep_default_na=False).set_index(
        "query_id")
    faltan = [q for q in cons.index if q not in mapa]
    if faltan:
        print(f"config/tablas_respuesta.yaml no define {faltan}: no se generan tablas.")
        return 1
    modelo = ambito.mejor_modelo()
    amb = ambito.ambito_ie()
    ent = pd.read_csv(SALIDA / "entidades_enriquecidas.csv", dtype={"passage_id": str},
                      keep_default_na=False)
    aux = pd.read_csv(SALIDA / "cantidades_auxiliares.csv", dtype={"passage_id": str},
                      keep_default_na=False)
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "doc_id", "fecha", "texto", "inicio_cuerpo",
                                   "interlocutor", "es_reportero", "intervencion_id"])
    pas = pas[pas["passage_id"].isin(set(amb["passage_id"]))].set_index("passage_id")
    ic = pas["inicio_cuerpo"].astype(int).to_dict()
    filtros = RS.filtros_desde_gazetteers(R.leer_gazetteer(R.GAZ_EXTENDIDO),
                                          R.leer_gazetteer(R.GAZ_LOC),
                                          R.leer_gazetteer(R.KIT_GAZETTEER))
    vals = ruta_valoraciones()
    valoraciones = (yaml.safe_load(vals.read_text(encoding="utf-8")) or {}) if vals.exists() else {}

    filas, evidencias, exclusiones, hashes, md = [], [], [], {}, {}
    for q in cons.index:
        amb_q = amb[amb["query_id"] == q]
        pas_q = pas.loc[amb_q["passage_id"]].assign(rango=amb_q["rango"].to_numpy())
        ent_q, n_marca, n_lista = RS.excluir(ent[ent["query_id"] == q], lista)
        exclusiones += [{"query_id": q, "motivo": "en_marca", "n": n_marca},
                        {"query_id": q, "motivo": "lista_excluir_tablas", "n": n_lista}]
        aux_q = aux[aux["query_id"] == q]
        filas_q, evid_q = [], []
        for campo in mapa[q]:
            cands = RS.candidatos(campo, ent_q, aux_q, filtros, ic)
            ev = RS.responder_campo(campo, cands, pas_q, ent_q)
            mejores, ev_out = RS.agregar(campo, ev)
            filas_q += mejores
            evid_q += ev_out
        res_q = pd.DataFrame(filas_q)
        for c in RS.COLUMNAS_RESPUESTAS + ["clave"]:
            if c not in res_q:
                res_q[c] = ""
        hashes[q] = RS.hash_tabla(res_q)
        linea = (f"Top-10 de `{modelo}` con filtro de fecha ({cons.at[q, 'desde']} a "
                 f"{cons.at[q, 'hasta']}). Excluidas antes de agregar: {n_marca} entidades en la "
                 f"marca de interlocutor y {n_lista} PER de `config/excluir_tablas.yaml`. "
                 "\"Respaldado\" significa que el texto lo afirma, no que sea verdad. "
                 f"Huella de la tabla: `{hashes[q][:12]}`.")
        md[q] = RS.markdown_consulta(q, cons.loc[q].to_dict(), res_q,
                                     pd.DataFrame(evid_q, columns=RS.COLUMNAS_EVIDENCIAS), linea,
                                     RS.bloque_valoracion(valoraciones.get(q), hashes[q]))
        filas += res_q[RS.COLUMNAS_RESPUESTAS].to_dict("records")
        evidencias += evid_q

    res = pd.DataFrame(filas, columns=RS.COLUMNAS_RESPUESTAS)
    errores = RS.validar_respuestas(res, pas["texto"].to_dict())
    if errores:
        print("respuestas.csv no cumple el contrato:", *errores[:10], sep="\n- ")
        return 1
    DIR_TABLAS.mkdir(parents=True, exist_ok=True)
    R.escribir_csv(res, SALIDA / "respuestas.csv")
    R.escribir_csv(pd.DataFrame(evidencias, columns=RS.COLUMNAS_EVIDENCIAS),
                   SALIDA / "10_evidencias.csv")
    R.escribir_csv(pd.DataFrame(exclusiones), SALIDA / "10_exclusiones.csv")
    for q, texto in md.items():
        (DIR_TABLAS / f"{q}.md").write_text(texto, encoding="utf-8")
    (DIR_TABLAS / "todas.md").write_text("\n\n---\n\n".join(md.values()), encoding="utf-8")
    (SALIDA / "10_hashes_tablas.json").write_text(json.dumps(hashes, indent=2) + "\n",
                                                   encoding="utf-8")

    pend = RS.validar_valoraciones(vals, hashes)
    salidas = [SALIDA / "respuestas.csv", SALIDA / "10_evidencias.csv",
               SALIDA / "10_exclusiones.csv", SALIDA / "10_hashes_tablas.json",
               *(DIR_TABLAS / f"{q}.md" for q in md), DIR_TABLAS / "todas.md"]
    manifiesto.registrar("10_tablas", [SALIDA / "entidades_enriquecidas.csv",
                                       SALIDA / "cantidades_auxiliares.csv", MAPA, EXCLUIR,
                                       config.DIR_DATA / "mejor_modelo.json"],
                         salidas, time.perf_counter() - t0,
                         {"valoraciones_pendientes": len(pend)})
    resumen = res.groupby(["query_id", "estado"]).size().unstack(fill_value=0)
    resumen = resumen.loc[sorted(resumen.index, key=lambda q: int(q[1:]))]
    print(resumen.to_string())
    print(f"\n{len(res)} filas en salida/respuestas.csv; tablas en {DIR_TABLAS}")
    vigentes = 0 if not vals.exists() else len(hashes) - len(pend)
    print(f"Valoraciones vigentes: {vigentes} de {len(hashes)}. Se escriben en la pestaña "
          "Valoraciones de la app." if vigentes < len(hashes) else "Valoraciones completas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
