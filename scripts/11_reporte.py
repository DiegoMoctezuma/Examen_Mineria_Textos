"""11 · Reporte PDF (PRD §6.14). `make reporte`.

1. Exige las diez valoraciones vigentes del alumno (`[VALIDAR]` de H8).
2. Rellena en `reporte/reporte.md` los bloques `<!-- tabla:NOMBRE -->` … `<!-- /tabla:NOMBRE -->`
   con tablas calculadas desde `salida/` (ninguna cifra se escribe a mano) y la sección 8 del
   README entre `<!-- resultados:inicio -->` y `<!-- resultados:fin -->`. La prosa no se toca.
3. Compila `reporte.md` → HTML (pandoc, MathML, `reporte/estilo.css`) → PDF con Chrome sin
   ventana (el de kaleido). Ruta alternativa a XeLaTeX documentada en `docs/decisiones.md`.
4. Cuenta páginas con `pypdf` y falla si no quedan entre 4 y 6.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

from mtx import config
from mtx import respuestas as RS

RAIZ, SAL = config.RAIZ, config.DIR_SALIDA
DIR_REP = RAIZ / "reporte"
MD, HTML, PDF, CSS = (DIR_REP / "reporte.md", DIR_REP / "reporte.html", DIR_REP / "reporte.pdf",
                      DIR_REP / "estilo.css")
NOMBRES = {"tfidf_sin_filtro": "TF-IDF sin filtro", "tfidf_con_filtro": "TF-IDF con filtro",
           "bm25_sin_filtro": "BM25 sin filtro", "bm25_con_filtro": "BM25 con filtro"}
ORDEN_MODELOS = list(NOMBRES)
TIPOS = ["PER", "ORG", "LOC", "FECHA", "MONTO", "TODOS"]


def md_tabla(df: pd.DataFrame, alinear_num: bool = True) -> str:
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "| " + " | ".join(
        "---:" if alinear_num and pd.api.types.is_numeric_dtype(df[c]) else "---"
        for c in df.columns) + " |"
    filas = ["| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in r) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *filas])


def f(x, d=3) -> str:
    return f"{float(x):.{d}f}"


def t_corpus() -> str:
    est = json.loads((SAL / "01_estadisticas_corpus.json").read_text())
    lim = json.loads((SAL / "01_limpieza.json").read_text())
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["es_reportero"])
    filas = [
        ("Discursos en el snapshot", f"{est['discursos']:,}"),
        ("Periodo", f"{est['fecha_min']} a {est['fecha_max']}"),
        ("Palabras por discurso (mediana)", f"{est['palabras']['mediana']:,.0f}"),
        ("Duplicados exactos / casi duplicados excluidos",
         f"{lim['duplicados_exactos']} / {lim['casi_duplicados']}"),
        ("Acotaciones eliminadas (inaudible, video, etc.)", f"{lim['acotaciones_eliminadas']:,}"),
        ("Pasajes indexados", f"{len(pas):,}"),
        ("Pasajes de reporteros", (f"{int(pas['es_reportero'].sum()):,} "
                                  f"({pas['es_reportero'].mean():.1%})")),
    ]
    return md_tabla(pd.DataFrame(filas, columns=["Concepto", "Valor"]))


def t_ir(ruta: Path) -> str:
    r = pd.read_csv(ruta)
    r = r[r["query_id"].str.startswith("PROMEDIO")].set_index("modelo").loc[ORDEN_MODELOS]
    return md_tabla(pd.DataFrame({"Variante": [NOMBRES[m] for m in r.index],
                                  "P@5": [f(x, 2) for x in r["P@5"]],
                                  "P@10": [f(x, 2) for x in r["P@10"]],
                                  "MAP": [f(x) for x in r["AP"]]}))


def t_ir_consulta() -> str:
    g = pd.read_csv(SAL / "05_ir_ganador_por_consulta.csv")
    return md_tabla(pd.DataFrame({
        "Consulta": list(g["query_id"]),
        "AP TF-IDF": [f(x) for x in g["AP_tfidf_con_filtro"]],
        "AP BM25": [f(x) for x in g["AP_bm25_con_filtro"]],
        "Gana": ["BM25" if "bm25" in x else "TF-IDF" for x in g["ganador_con_filtro"]]}))


def t_ie() -> str:
    r = pd.read_csv(SAL / "resultados_ie.csv")
    filas = []
    for m in ["regla", "modelo", "combinado"]:
        s = r[r["metodo"] == m].set_index("tipo")
        filas.append([m] + [("s/c" if m == "modelo" and t in ("FECHA", "MONTO") else
                             f(s.at[t, "f1"], 2)) for t in TIPOS]
                     + [f(s.at["TODOS", "precision"], 2), f(s.at["TODOS", "recall"], 2)])
    gold = r[r["metodo"] == "combinado"].set_index("tipo")["gold"]
    filas.append(["soporte gold"] + [str(int(gold[t])) for t in TIPOS] + ["", ""])
    return md_tabla(pd.DataFrame(filas, columns=["Método"] + [f"F1 {t}" for t in TIPOS]
                                 + ["P TODOS", "R TODOS"]), alinear_num=False)


def t_errores() -> str:
    e = pd.read_csv(SAL / "09_resumen_errores.csv")
    e["principal"] = e["categoria"].str.split(":").str[0]
    e = e[e["categoria"] == e["principal"]]  # sin subcategorías para no contar doble
    p = e.pivot_table(index="principal", columns="error", values="n", aggfunc="sum",
                      fill_value=0).reset_index()
    p.columns = ["Categoría", *[f"{c} (filas)" for c in p.columns[1:]]]
    return md_tabla(p)


def t_respuestas() -> str:
    res = pd.read_csv(SAL / "respuestas.csv", dtype=str, keep_default_na=False)
    val = yaml.safe_load((config.DIR_ANOTACIONES / "valoraciones.yaml").read_text()) or {}
    cons = pd.read_csv(config.CONSULTAS_CSV).set_index("query_id")
    filas = []
    for q in sorted(res["query_id"].unique(), key=lambda x: int(x[1:])):
        g = res[res["query_id"] == q]
        n = g["estado"].value_counts()
        vacios = ", ".join(g.loc[g["estado"] == "no_encontrado", "campo_respuesta"]) or "ninguno"
        filas.append(f"**{q} {cons.at[q, 'consulta']}.** {n.get('respaldado_en_texto', 0)} "
                     f"valores respaldados, {n.get('ambiguo', 0)} ambiguos; campos sin "
                     f"evidencia: {vacios}. *Valoración humana:* "
                     + " ".join(str(val.get(q, {}).get("texto", "")).split()))
    return "\n\n".join(filas)


def t_readme() -> str:
    r = pd.read_csv(SAL / "resultados_ir.csv")
    r = r[r["query_id"].str.startswith("PROMEDIO")].set_index("modelo").loc[ORDEN_MODELOS]
    ie = pd.read_csv(SAL / "resultados_ie.csv")
    c = ie[ie["metodo"] == "combinado"].set_index("tipo")
    return ("MAP por variante (`resultados_ir.csv`, relevancia temática):\n\n"
            + md_tabla(pd.DataFrame({"Variante": [NOMBRES[m] for m in r.index],
                                     "MAP": [f(x) for x in r["AP"]]}))
            + "\n\nF1 del método combinado por tipo (`resultados_ie.csv`, 20 pasajes gold):\n\n"
            + md_tabla(pd.DataFrame({"Tipo": TIPOS, "F1": [f(c.at[t, "f1"]) for t in TIPOS]})))


TABLAS = {"corpus": t_corpus, "ir": lambda: t_ir(SAL / "resultados_ir.csv"),
          "ir_ventana": lambda: t_ir(SAL / "05_resultados_ir_ventana.csv"),
          "ir_consulta": t_ir_consulta, "ie": t_ie, "errores": t_errores,
          "respuestas": t_respuestas}


def rellenar(texto: str, nombre: str, contenido: str, ini: str, fin: str) -> str:
    patron = re.compile(re.escape(ini) + r".*?" + re.escape(fin), re.DOTALL)
    if not patron.search(texto):
        raise SystemExit(f"Falta el bloque {ini} … {fin} ({nombre})")
    return patron.sub(lambda _: f"{ini}\n{contenido}\n{fin}", texto)


def chrome() -> str | None:
    cand = [Path.home() / "Library/Application Support/choreographer/deps/chrome-mac-arm64/"
            "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    for c in cand:
        if c.exists():
            return str(c)
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        if shutil.which(n):
            return shutil.which(n)
    return None


def main() -> int:
    hashes = json.loads((SAL / "10_hashes_tablas.json").read_text())
    pend = RS.validar_valoraciones(config.DIR_ANOTACIONES / "valoraciones.yaml", hashes)
    if pend:
        print("[VALIDAR] faltan valoraciones vigentes del alumno:", *pend, sep="\n- ")
        return 1
    texto = MD.read_text(encoding="utf-8")
    for nombre, fn in TABLAS.items():
        texto = rellenar(texto, nombre, fn(), f"<!-- tabla:{nombre} -->", f"<!-- /tabla:{nombre} -->")
    MD.write_text(texto, encoding="utf-8")
    readme = RAIZ / "README.md"
    readme.write_text(rellenar(readme.read_text(encoding="utf-8"), "readme", t_readme(),
                               "<!-- resultados:inicio -->", "<!-- resultados:fin -->"),
                      encoding="utf-8")
    PANDOC = next((p for p in ("/opt/homebrew/bin/pandoc", shutil.which("pandoc")) if p and Path(p).exists()), None)
    if not PANDOC:
        print("Falta pandoc: tablas actualizadas, PDF no generado.")
        return 1
    subprocess.run([PANDOC, str(MD.name), "-o", str(HTML.name), "--standalone", "--math-method=mathml",
                    "--css", CSS.name, "--embed-resources", "--metadata", "lang=es-MX"],
                   cwd=DIR_REP, check=True)
    nav = chrome()
    if not nav:
        print("No se encontró Chrome: `make setup` lo instala (plotly_get_chrome).")
        return 1
    subprocess.run([nav, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={PDF}", HTML.as_uri()], check=True, capture_output=True)
    from pypdf import PdfReader
    n = len(PdfReader(PDF).pages)
    print(f"reporte/reporte.pdf: {n} páginas")
    return 0 if 4 <= n <= 6 else 1


if __name__ == "__main__":
    sys.exit(main())
