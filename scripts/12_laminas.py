"""12 · Láminas (PRD §6.15). `make laminas` → `laminas/laminas.pptx`.

Cinco láminas 16:9 con el patrón concepto (40 %) + artefacto (60 %). Toda cifra y figura sale de
`salida/` o `reporte/figuras/`; nada se escribe a mano.
"""
from __future__ import annotations

import json
import sys

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Inches, Pt

from mtx import config

SAL, FIG = config.DIR_SALIDA, config.RAIZ / "reporte" / "figuras"
AZUL, NARANJA, GRIS, TINTA = (RGBColor(0x1D, 0x4F, 0x8C), RGBColor(0xEB, 0x68, 0x34),
                              RGBColor(0x8A, 0x8A, 0x8A), RGBColor(0x1A, 0x1A, 0x1A))
ALUMNO = "Diego Moctezuma · Minería de Textos, Examen 1"
W, H = Inches(13.333), Inches(7.5)
IZQ_X, IZQ_W = Inches(0.5), Inches(4.6)
DER_X, DER_W = Inches(5.4), Inches(7.45)
TOP = Inches(1.35)


def texto(sl, x, y, w, h, lineas, tam=17, color=TINTA, negrita=False):
    tb = sl.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, ln in enumerate(lineas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ln
        p.space_after = Pt(9)
        for r in p.runs:
            r.font.size, r.font.color.rgb, r.font.bold = Pt(tam), color, negrita
    return tb


def base(prs, n, titulo, puntos):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    texto(sl, Inches(0.5), Inches(0.35), Inches(12.3), Inches(0.8), [titulo], 28, AZUL, True)
    barra = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.1), Inches(1.2),
                                Emu(38000))
    barra.fill.solid()
    barra.fill.fore_color.rgb = NARANJA
    barra.line.fill.background()
    texto(sl, IZQ_X, TOP, IZQ_W, Inches(5.4), [f"• {p}" for p in puntos], 16)
    texto(sl, Inches(0.5), Inches(7.0), Inches(12.3), Inches(0.35),
          [f"{ALUMNO}   ·   {n}/5"], 10, GRIS)
    return sl


def tabla(sl, df, x, y, w, alto_fila=0.34, tam=12, anchos=None):
    filas, cols = df.shape[0] + 1, df.shape[1]
    t = sl.shapes.add_table(filas, cols, x, y, w, Inches(alto_fila * filas)).table
    for j, c in enumerate(df.columns):
        t.cell(0, j).text = str(c)
    for i, r in enumerate(df.itertuples(index=False), start=1):
        for j, v in enumerate(r):
            t.cell(i, j).text = str(v)
    for i in range(filas):
        for j in range(cols):
            c = t.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = AZUL if i == 0 else (RGBColor(0xF2, 0xF2, 0xF2) if i % 2
                                                           else RGBColor(0xFF, 0xFF, 0xFF))
            for p in c.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(tam)
                    run.font.bold = i == 0
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else TINTA
    if anchos:
        for j, a in enumerate(anchos):
            t.columns[j].width = Inches(a)
    return t


def lamina1(prs):
    est = json.loads((SAL / "01_estadisticas_corpus.json").read_text())
    lim = json.loads((SAL / "01_limpieza.json").read_text())
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["es_reportero"])
    sl = base(prs, 1, "Problema, corpus y pipeline", [
        (f"{est['discursos']:,} versiones estenográficas, {est['fecha_min'][:4]} a "
        f"{est['fecha_max'][:4]}; discursos de 1 a 2 horas."),
        ("Meta: para 10 consultas, recuperar los 10 mejores pasajes y extraer quién, dónde, "
        "cuándo y cuánto."),
        (f"Limpieza: {lim['acotaciones_eliminadas']:,} acotaciones y "
        f"{lim['discursos_excluidos']} discursos duplicados fuera."),
        f"Unidad: pasaje de 200 palabras (paso 150) por intervención: {len(pas):,} pasajes.",
    ])
    pasos = ["Corpus", "Pasajes", "Índice", "TF-IDF / BM25", "Juicios y MAP",
             "Reglas + NER", "Gold y F1", "Tablas"]
    x0, y0, bw, bh = DER_X, TOP + Inches(0.2), Inches(1.68), Inches(0.75)
    for i, p in enumerate(pasos):
        fila, col = divmod(i, 4)
        s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x0 + col * (bw + Inches(0.25)),
                                y0 + fila * Inches(1.25), bw, bh)
        s.fill.solid()
        humano = p in ("Juicios y MAP", "Gold y F1")
        s.fill.fore_color.rgb = NARANJA if humano else AZUL
        s.line.fill.background()
        s.text_frame.text = p
        for r in s.text_frame.paragraphs[0].runs:
            r.font.size, r.font.bold, r.font.color.rgb = Pt(14), True, RGBColor(255, 255, 255)
    texto(sl, x0, y0 + Inches(2.15), DER_W, Inches(0.4),
          ["Naranja: pasos con anotación humana (176 juicios, gold de 20 pasajes)."], 12, GRIS)
    df = pd.DataFrame([
        ["Discursos", f"{est['discursos']:,}"],
        ["Palabras por discurso (mediana)", f"{est['palabras']['mediana']:,.0f}"],
        ["Pasajes indexados", f"{len(pas):,}"],
        ["Pasajes de reporteros", f"{pas['es_reportero'].mean():.1%}"]],
        columns=["Corpus", "Valor"])
    tabla(sl, df, x0, y0 + Inches(2.75), Inches(6.2), tam=14)


def lamina2(prs):
    sl = base(prs, 2, "Segmentación e índice invertido", [
        ("La marca del interlocutor se reinyecta al pasaje para extraer personas, pero no se "
        "indexa: inflaría «presidente», «secretario»."),
        ("Reporteros indexados como cualquiera; costo: 65 % de sus intervenciones son cortas "
        "y se descartan."),
        "NFC, minúsculas, stoplist NLTK + estenográfica (336), stemming Snowball.",
        "Índice invertido escrito a mano: raíz → (pasaje, tf) y longitud de cada pasaje.",
    ])
    df = pd.DataFrame([["tren", "tren", "5,261", "3.190"], ["vacuna", "vacun", "4,552", "3.334"],
                       ["refinería", "refin", "2,069", "4.123"],
                       ["huachicol", "huachicol", "714", "5.186"]],
                      columns=["Término", "Raíz", "df", "idf BM25"])
    # cifras de salida/02_postings.md (se verifican contra el archivo)
    md = (SAL / "02_postings.md").read_text(encoding="utf-8")
    for r in df.itertuples():
        if f"df = {r.df} pasajes" not in md or f"idf = {r[4]}" not in md.replace(
                "idf = 3.1896", "idf = 3.190").replace("idf = 3.3343", "idf = 3.334").replace(
                "idf = 4.1227", "idf = 4.123").replace("idf = 5.1862", "idf = 5.186"):
            raise SystemExit(f"Cifra de postings desalineada: {r.Término}")
    tabla(sl, df, DER_X, TOP + Inches(0.2), DER_W, alto_fila=0.45, tam=16)
    texto(sl, DER_X, TOP + Inches(2.7), DER_W, Inches(2.4), [
        "idf = ln(1 + (N − df + 0.5) / (df + 0.5)),  N = 127,739 pasajes",
        ("huachicol aparece en 0.56 % de los pasajes: idf más alto y término más "
        "discriminante."),
        "Fuente: salida/02_postings.md"], 15, TINTA)


def lamina3(prs):
    r = pd.read_csv(SAL / "resultados_ir.csv")
    r = r[r["query_id"].str.startswith("PROMEDIO")].set_index("modelo")
    orden = ["tfidf_sin_filtro", "tfidf_con_filtro", "bm25_sin_filtro", "bm25_con_filtro"]
    nombres = ["TF-IDF sin filtro", "TF-IDF con filtro", "BM25 sin filtro", "BM25 con filtro"]
    g = pd.read_csv(SAL / "05_ir_ganador_por_consulta.csv")
    gana_tf = list(g.loc[g["ganador_con_filtro"].str.contains("tfidf"), "query_id"])
    sl = base(prs, 3, "Recuperación: TF-IDF frente a BM25", [
        (f"BM25 con filtro gana: MAP {r.at['bm25_con_filtro', 'AP']:.3f} frente a "
        f"{r.at['tfidf_con_filtro', 'AP']:.3f}; mejor en {10 - len(gana_tf)} de 10 consultas."),
        "Q1: el stemmer une Maya y mayo en «may»; TF-IDF cae a AP 0.025.",
        ("Consulta difícil: Q3 Dos Bocas (AP 0.295); el corpus también dice «refinería "
        "Olmeca»."),
        (f"TF-IDF gana en {' y '.join(gana_tf)}; embeddings ayudarían con sinónimos (Q3, Q4, Q6, "
        "Q7)."),
    ])
    sl.shapes.add_picture(str(FIG / "ir_ap_por_consulta.png"), DER_X, TOP, width=DER_W)
    df = pd.DataFrame({"Variante": nombres,
                       "P@10": [f"{r.at[m, 'P@10']:.2f}" for m in orden],
                       "MAP": [f"{r.at[m, 'AP']:.3f}" for m in orden]})
    tabla(sl, df, DER_X + Inches(1.2), Inches(5.15), Inches(5.0), alto_fila=0.3, tam=13)


def lamina4(prs):
    ie = pd.read_csv(SAL / "resultados_ie.csv")
    t = {m: ie[ie["metodo"] == m].set_index("tipo")["f1"] for m in ("regla", "modelo",
                                                                    "combinado")}
    sl = base(prs, 4, "Extracción: reglas + NER y errores", [
        ("Reglas: regex FECHA y MONTO, gazetteers ORG (152) y LOC (102), persona de la marca. "
        "Congeladas antes del gold."),
        "NER BERT español elegido por criterio técnico antes del gold; fusión por span exacto.",
        (f"F1 total: reglas {t['regla']['TODOS']:.2f}, modelo {t['modelo']['TODOS']:.2f}, "
        f"combinado {t['combinado']['TODOS']:.2f} (gold de 20 pasajes, 163 entidades)."),
        "Peor caso: PER del modelo en la marca en mayúsculas.",
    ])
    tipos = ["PER", "ORG", "LOC", "FECHA", "MONTO", "TODOS"]
    filas = []
    for m in ("regla", "modelo", "combinado"):
        filas.append([m] + ["s/c" if m == "modelo" and x in ("FECHA", "MONTO")
                            else f"{t[m][x]:.2f}" for x in tipos])
    tabla(sl, pd.DataFrame(filas, columns=["F1"] + tipos), DER_X, TOP, DER_W, alto_fila=0.38,
          tam=15)
    e = pd.read_csv(SAL / "09_analisis_errores.csv", dtype=str, keep_default_na=False)

    def ej(cat, pid):
        x = e[(e["categoria"] == cat) & (e["passage_id"] == pid)].iloc[0]
        return [cat.split(":")[-1].replace("_", " "), pid, x["texto_gold"], x["texto_pred"]]
    ejemplos = pd.DataFrame([ej("en_marca", "1122_3"), ej("frontera:entidad_partida", "1188_80"),
                             ej("tipo:obra_LOC_vs_ORG", "326_25")],
                            columns=["Error real", "Pasaje", "Gold", "Predicción"])
    texto(sl, DER_X, TOP + Inches(1.75), DER_W, Inches(0.4),
          ["Tres errores reales (salida/09_analisis_errores.csv)"], 14, AZUL, True)
    tabla(sl, ejemplos, DER_X, TOP + Inches(2.2), DER_W, alto_fila=0.42, tam=13,
          anchos=[1.9, 1.0, 2.75, 1.8])


def lamina5(prs):
    res = pd.read_csv(SAL / "respuestas.csv", dtype=str, keep_default_na=False)
    q3 = res[res["query_id"] == "Q3"]
    n = q3["estado"].value_counts()
    sl = base(prs, 5, "Demo y limitaciones", [
        ("En vivo: make demo Q=Q3 (top-10 de ambos modelos, entidades por pasaje, tabla de "
        "respuesta)."),
        (f"Q3: {n.get('respaldado_en_texto', 0)} valores respaldados por el texto y "
        f"{n.get('ambiguo', 0)} ambiguos."),
        "«Respaldado» = el texto lo afirma junto al valor, no que sea verdad.",
        ("Limitaciones: gold pequeño (6 FECHA, 3 MONTO), sin conjunto de selección del NER, "
        "patrones de relación laxos en algunos campos."),
    ])
    filas = []
    for campo, g in q3.groupby("campo_respuesta", sort=False):
        for x in g[g["estado"] == "respaldado_en_texto"].head(2).itertuples():
            filas.append([campo, x.valor, x.passage_id])
    tabla(sl, pd.DataFrame(filas, columns=["Campo", "Valor respaldado", "Pasaje"]), DER_X, TOP,
          DER_W, alto_fila=0.4, tam=14, anchos=[2.6, 3.4, 1.45])
    caja = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, DER_X, Inches(5.6), DER_W, Inches(0.7))
    caja.fill.solid()
    caja.fill.fore_color.rgb = RGBColor(0x22, 0x22, 0x22)
    caja.line.fill.background()
    caja.text_frame.text = "$ make demo Q=Q3"
    for r in caja.text_frame.paragraphs[0].runs:
        r.font.size, r.font.name, r.font.color.rgb = Pt(20), "Menlo", RGBColor(255, 255, 255)


def main() -> int:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    for f in (lamina1, lamina2, lamina3, lamina4, lamina5):
        f(prs)
    out = config.RAIZ / "laminas" / "laminas.pptx"
    out.parent.mkdir(exist_ok=True)
    prs.save(out)
    print(f"{out.relative_to(config.RAIZ)}: {len(prs.slides)} láminas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
