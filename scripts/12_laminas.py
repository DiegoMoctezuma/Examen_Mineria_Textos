"""12 · Láminas (PRD §6.15, skill hack-presentacion adaptada). `make laminas`.

1. Exporta a `laminas/deck/datos.json` todas las cifras que usa el deck, leídas de `salida/` y
   `data/` (ninguna se escribe a mano en `deck.js`).
2. Corre `node laminas/deck/deck.js` (pptxgenjs), que dibuja el deck con el estilo destilado de
   `referencias/original-*` (`laminas/deck/ESTILO.md`) y escribe `laminas/laminas.pptx`.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

import pandas as pd

from mtx import config

SAL, DECK = config.DIR_SALIDA, config.RAIZ / "laminas" / "deck"

CONSULTAS = {  # nombre corto en pantalla, ícono (laminas/deck/iconos) y color del anillo del ícono
    "Q1": ("Tren Maya", "q1", "02614C"), "Q2": ("Vacunas COVID-19", "q2", "012B60"),
    "Q3": ("Dos Bocas", "q3", "9E0C01"), "Q4": ("AIFA", "q4", "011E51"),
    "Q5": ("Sembrando Vida", "q5", "024B1B"), "Q6": ("Huachicol", "q6", "A3010F"),
    "Q7": ("Pensión adultos mayores", "q7", "5B0454"), "Q8": ("Salario mínimo", "q8", "013147"),
    "Q9": ("Banco del Bienestar", "q9", "780526"), "Q10": ("Tren Interoceánico", "q10", "02204E"),
}


def postings() -> list[dict]:
    md = (SAL / "02_postings.md").read_text(encoding="utf-8")
    out = []
    for termino, raiz, df, idf in re.findall(
            r"## `([^`]+)` → raíz `([^`]+)`\n\n- df = ([\d,]+) pasajes .*?idf = ([\d.]+)", md):
        out.append({"termino": termino, "raiz": raiz, "df": int(df.replace(",", "")),
                    "idf": float(idf)})
    return out


def main() -> int:
    est = json.loads((SAL / "01_estadisticas_corpus.json").read_text())
    lim = json.loads((SAL / "01_limpieza.json").read_text())
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["es_reportero"])
    cons = pd.read_csv(config.CONSULTAS_CSV, dtype=str).set_index("query_id")
    ir = pd.read_csv(SAL / "resultados_ir.csv")
    prom = ir[ir["query_id"].str.startswith("PROMEDIO")].set_index("modelo")
    g = pd.read_csv(SAL / "05_ir_ganador_por_consulta.csv").set_index("query_id")
    ie = pd.read_csv(SAL / "resultados_ie.csv")
    res = pd.read_csv(SAL / "respuestas.csv", dtype=str, keep_default_na=False)
    err = pd.read_csv(SAL / "09_analisis_errores.csv", dtype=str, keep_default_na=False)
    juicios = pd.read_csv(config.RAIZ / "juicios_relevancia.csv")
    gold = pd.read_csv(config.RAIZ / "gold_entidades.csv")
    resumen_ext = json.loads((SAL / "08_resumen_extraccion.json").read_text())

    def ejemplo(cat, pid):
        x = err[(err["categoria"] == cat) & (err["passage_id"] == pid)].iloc[0]
        return {"pasaje": pid, "tipo": x["tipo"], "gold": x["texto_gold"],
                "pred": x["texto_pred"]}

    datos = {
        "corpus": {"discursos": est["discursos"], "anio_ini": est["fecha_min"][:4],
                   "anio_fin": est["fecha_max"][:4],
                   "palabras_mediana": round(est["palabras"]["mediana"]),
                   "acotaciones": lim["acotaciones_eliminadas"],
                   "duplicados": lim["discursos_excluidos"], "pasajes": len(pas),
                   "pct_reporteros": round(100 * float(pas["es_reportero"].mean()), 2)},
        "humano": {"juicios": len(juicios), "gold_pasajes": int(gold["passage_id"].nunique()),
                   "gold_entidades": len(gold)},
        "consultas": [{"id": q, "nombre": n, "icono": i, "color": c,
                       "desde": cons.at[q, "desde"][:4], "hasta": cons.at[q, "hasta"][:4],
                       "ap_tfidf": float(g.at[q, "AP_tfidf_con_filtro"]),
                       "ap_bm25": float(g.at[q, "AP_bm25_con_filtro"]),
                       "respaldados": int(((res["query_id"] == q)
                                           & (res["estado"] == "respaldado_en_texto")).sum()),
                       "ambiguos": int(((res["query_id"] == q)
                                        & (res["estado"] == "ambiguo")).sum()),
                       "sin_evidencia": list(res.loc[(res["query_id"] == q)
                                                     & (res["estado"] == "no_encontrado"),
                                                     "campo_respuesta"])}
                      for q, (n, i, c) in CONSULTAS.items()],
        "postings": postings(),
        "map": {m: float(prom.at[m, "AP"]) for m in prom.index},
        "ie": {m: {t: {"f1": float(r["f1"]), "p": float(r["precision"]),
                       "r": float(r["recall"]), "gold": int(r["gold"])}
                   for t, r in d.set_index("tipo").iterrows()}
               for m, d in ie.groupby("metodo")},
        "fusion": resumen_ext["unicas_por_metodo"],
        "errores": [ejemplo("en_marca", "1122_3"), ejemplo("frontera:entidad_partida", "1188_80"),
                    ejemplo("tipo:obra_LOC_vs_ORG", "326_25")],
    }
    (DECK / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    p = subprocess.run(["node", "deck.js"], cwd=DECK, check=False)
    if p.returncode:
        return p.returncode
    copiar_notas()
    return 0


def copiar_notas() -> None:
    """Copia las notas del orador del deck a `laminas/guion.md` (una sola fuente de verdad)."""
    from pptx import Presentation

    prs = Presentation(str(config.RAIZ / "laminas" / "laminas.pptx"))
    bloques = []
    for i, sl in enumerate(prs.slides, start=1):
        notas = sl.notes_slide.notes_text_frame.text.strip() if sl.has_notes_slide else ""
        titulo = next((sh.text_frame.text for sh in sl.shapes
                       if sh.has_text_frame and sh.text_frame.text.strip()), "")
        bloques.append(f"## {i}. {' '.join(titulo.split())}\n\n{notas}\n")
    guion = config.RAIZ / "laminas" / "guion.md"
    texto = guion.read_text(encoding="utf-8")
    texto = re.sub(r"<!-- notas:inicio -->.*?<!-- notas:fin -->",
                   lambda _: "<!-- notas:inicio -->\n\n" + "\n".join(bloques)
                   + "\n<!-- notas:fin -->", texto, flags=re.DOTALL)
    guion.write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
