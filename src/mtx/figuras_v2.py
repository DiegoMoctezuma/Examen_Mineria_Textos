"""Figuras y ejemplos de v2 para láminas y reporte (PRD v2 WP-16, D36, tabla 1.3).

Cada función recibe datos ya leídos de `salida/` (o del índice, para los ejemplos de postings y
tokenización) y devuelve una figura de plotly con título y ejes nombrados. Solo lee su estilo
(`config/v2/estilo.yaml`); las salidas las lee y las imágenes las escribe `scripts/11b_figuras_v2.py`, que además registra de qué archivo salió cada
cifra (`salida/v2/figuras/figuras.json`).

Reglas de estilo de venta (D36, R03, S3, S6, S8b): paleta y tipografía de `config/v2/estilo.yaml`;
nombres de consulta en vez de Qn; ejes con nombre; porcentajes donde ayudan; ningún ID de pasaje
ni ruta a la vista (los pasajes se nombran por fecha y fragmento).

Con datos v1 (antes de los cierres) cada figura lleva el subtítulo «Cifras preliminares del examen
(v1)», para que nadie la confunda con la versión final; con datos v2 se regeneran igual.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from mtx import config
from mtx import preproceso as P

RUTA_ESTILO = config.DIR_CONFIG / "v2" / "estilo.yaml"
AVISO_V1 = "Cifras preliminares del examen (v1)"
TIPOS = ("PER", "ORG", "LOC", "FECHA", "MONTO")
NOMBRE_TIPO = {"PER": "Personas", "ORG": "Organizaciones", "LOC": "Lugares", "FECHA": "Fechas",
               "MONTO": "Montos", "TODOS": "Todas"}
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
RE_ID = re.compile(r"\b\d{1,4}_\d{1,4}\b")


@dataclass
class Estilo:
    paleta: dict[str, str]
    titulos: str
    texto: str
    nombres: dict[str, str]
    ejemplos: dict = field(default_factory=dict)
    patrones: dict[str, str] = field(default_factory=dict)
    estados: dict[str, str] = field(default_factory=dict)
    metodos: dict[str, str] = field(default_factory=dict)


def cargar_estilo(ruta: Path = RUTA_ESTILO) -> Estilo:
    import yaml

    d = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    return Estilo(d["paleta"], d["tipografia"]["titulos"], d["tipografia"]["texto"],
                  d["nombres_consulta"], d.get("ejemplos", {}), d.get("patrones_error", {}),
                  d.get("estados", {}), d.get("metodos", {}))


def nombre_consulta(est: Estilo, q: str, corto: bool = False) -> str:
    """"Pregunta 3 · Dos Bocas" (S3); `corto` deja solo el nombre."""
    nombre = est.nombres.get(q, q)
    return nombre if corto else f"Pregunta {q.lstrip('Q')} · {nombre}"


def nombre_modelo(m: str) -> str:
    """"bm25_lema_con_filtro" → "BM25 · lema · con fecha"."""
    familia = "BM25" if m.startswith("bm25") else "TF-IDF"
    raiz = "lema" if "_lema_" in m else "raíz"
    filtro = "con filtro de fecha" if m.endswith("con_filtro") else "sin filtro"
    return f"{familia} · {raiz} · {filtro}"


def fecha_larga(fecha) -> str:
    f = pd.Timestamp(fecha)
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


def etiqueta_pasaje(fecha, posicion: int, titulo: str = "") -> str:
    """Pasaje por fecha y fragmento, nunca por ID (S8b). El fragmento cuenta desde 1, como en la
    demo web (`presentacion.py`); "Mañanera" solo si el título es de la conferencia matutina."""
    evento = "Mañanera" if "matutina" in str(titulo).lower() else "Evento"
    return f"{evento} del {fecha_larga(fecha)} · fragmento {int(posicion) + 1}"


def miles(n: float) -> str:
    return f"{round(n):,}"


def pct(x: float, dec: int = 1) -> str:
    return f"{100 * x:.{dec}f} %"


# --------------------------------------------------------------------------- base


def _go():
    import plotly.graph_objects as go
    return go


def _lineas(texto: str, ancho: int) -> list[str]:
    import textwrap
    return textwrap.wrap(texto, ancho) if texto else []


def _subtitulo(subtitulo: str | None, version: str, ancho: int) -> list[str]:
    """Subtítulo partido en líneas (no se corta a la derecha) y el aviso de v1 en su propia línea."""
    return _lineas(subtitulo or "", ancho) + ([AVISO_V1] if version == "v1" else [])


def _base(fig, est: Estilo, titulo: str, x: str | None, y: str | None, version: str,
          subtitulo: str | None = None, alto: int = 620, ancho: int = 1100):
    pal = est.paleta
    lineas = _subtitulo(subtitulo, version, int(ancho / 10))
    arriba = 70 + 24 * len(lineas)
    fig.update_layout(
        title={"text": titulo, "x": 0.02, "xanchor": "left", "y": 1, "yref": "container",
               "yanchor": "top", "pad": {"t": 22},
               "font": {"family": est.titulos, "size": 24, "color": pal["guinda_oscuro"]},
               "subtitle": {"text": "<br>".join(lineas),
                            "font": {"family": est.titulos, "size": 16,
                                     "color": pal["guinda"]}}},
        font={"family": est.texto, "size": 15, "color": pal["texto"]},
        paper_bgcolor=pal["fondo"], plot_bgcolor=pal["fondo"], width=ancho,
        height=alto + 24 * len(lineas),
        margin={"l": 80, "r": 40, "t": arriba + 30, "b": 80},
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 1, "xanchor": "right",
                "title": None})
    if x is not None:
        fig.update_xaxes(title_text=x, showline=True, linecolor=pal["gris"], gridcolor="#EEEEEE")
    if y is not None:
        fig.update_yaxes(title_text=y, showline=True, linecolor=pal["gris"], gridcolor="#EEEEEE")
    return fig


def _tabla(est: Estilo, encabezados: list[str], columnas: list[list], anchos=None):
    go, pal = _go(), est.paleta
    return go.Table(
        columnwidth=anchos,
        header={"values": [f"<b>{h}</b>" for h in encabezados], "fill_color": pal["guinda"],
                "font": {"color": "white", "family": est.titulos, "size": 15}, "align": "left",
                "height": 34},
        cells={"values": columnas, "fill_color": [[pal["fondo"], "#F7F2EA"] * 20],
               "font": {"family": est.texto, "size": 14, "color": pal["texto"]},
               "align": "left", "height": 30})


# --------------------------------------------------------------------------- corpus (S2a, S2b)


def fig_corpus(limpieza: dict, est: Estilo, version: str = "v2"):
    """S2a: de los discursos descargados a los fragmentos que entran al índice."""
    go, pal = _go(), est.paleta
    etapas = ["Discursos descargados", "Sin duplicados", "Con al menos un fragmento útil"]
    valores = [limpieza["discursos"], limpieza["discursos"] - limpieza["discursos_excluidos"],
               limpieza["discursos_con_pasajes"]]
    notas = ["", (f"{limpieza['duplicados_exactos']} duplicados exactos y "
                 f"{limpieza['casi_duplicados']} casi duplicado fuera"), ""]
    fig = go.Figure(go.Bar(x=valores[::-1], y=etapas[::-1], orientation="h",
                           marker_color=[pal["dorado"], pal["guinda"], pal["guinda_oscuro"]],
                           text=[f"{miles(v)}  {n}".strip() for v, n in zip(valores, notas)][::-1],
                           textposition="inside", insidetextanchor="start",
                           textfont={"color": "white", "size": 16}))
    fig.update_xaxes(range=[0, valores[0] * 1.05])
    sub = (f"El {limpieza['pasajes_de_reporteros_pct']:.1f} % de los fragmentos son preguntas "
           "de reporteros: se indexan porque nombran el tema")
    return _base(fig, est, f"De {miles(valores[0])} discursos a {miles(limpieza['pasajes'])} "
                           "fragmentos que se pueden buscar", "Discursos", None, version, sub,
                 alto=420)


def fig_acotaciones(limpieza: dict, est: Estilo, n: int = 8, version: str = "v2"):
    """S2b: qué son las acotaciones, con los ejemplos reales más frecuentes."""
    go, pal = _go(), est.paleta
    tipos = {k: v for k, v in limpieza["acotaciones_por_tipo"].items() if any(c.isalpha() for c in k)}
    top = sorted(tipos.items(), key=lambda kv: -kv[1])[:n]
    fig = go.Figure(go.Bar(x=[v for _, v in top][::-1], y=[f"«{k}»" for k, _ in top][::-1],
                           orientation="h", marker_color=pal["dorado"],
                           text=[miles(v) for _, v in top][::-1], textposition="outside"))
    total = limpieza["acotaciones_eliminadas"]
    return _base(fig, est, "Acotaciones: notas del transcriptor, no palabras de nadie",
                 "Veces que aparece en las versiones estenográficas", "Acotación", version,
                 f"Se quitaron {miles(total)} antes de indexar; estas son las {n} más comunes",
                 alto=520)


# --------------------------------------------------------------------------- texto (S4c, S4d, R09)


def oracion_ejemplo(cuerpo: str, terminos: set[str], minimo: int = 8, maximo: int = 45) -> str:
    """La oración del cuerpo (de 8 a 45 palabras) con más términos distintos de la consulta (en
    raíz); empate, la primera. Si ninguna tiene ese largo, las primeras 45 palabras."""
    oraciones = [o.strip() for o in re.split(r"(?<=[.!?])\s+", unicodedata.normalize("NFC", cuerpo))]
    buenas = [o for o in oraciones if minimo <= len(o.split()) <= maximo]
    if not buenas:
        return " ".join(cuerpo.split()[:maximo])
    return max(buenas, key=lambda o: len(terminos & set(P.tokenizar(o))))


def pasos_tokenizacion(oracion: str, lemas: list[str] | None = None) -> list[tuple[str, str]]:
    """S4c: cada etapa de PRD §6.2 sobre una oración real, como la ve el índice."""
    palabras = P.RE_TOKEN.findall(unicodedata.normalize("NFC", oracion).lower())
    sin_vacias = P.tokenizar_sin_stem(oracion)
    pasos = [("1. Oración original", oracion),
             ("2. Minúsculas y palabras", " · ".join(palabras)),
             ("3. Sin palabras vacías que no distinguen temas", " · ".join(sin_vacias)),
             ("4. Raíz (stemming, examen)", " · ".join(P.tokenizar(oracion)))]
    if lemas is not None:
        pasos.append(("5. Lema (proyecto final)", " · ".join(lemas)))
    return pasos


def fig_tokenizacion(pasos: list[tuple[str, str]], fuente: str, est: Estilo, version: str = "v2"):
    go = _go()
    fig = go.Figure(_tabla(est, ["Etapa", "Resultado"], [[p for p, _ in pasos],
                                                          [t for _, t in pasos]], [0.28, 0.72]))
    return _base(fig, est, "Cómo se convierte una oración en términos del índice", None, None,
                 version, fuente, alto=480)


def terminos_idf(consulta: str, df: dict[str, int], N: int) -> pd.DataFrame:
    """Palabras de la consulta tras palabras vacías, su raíz, df, % de fragmentos e idf de BM25."""
    import math

    filas = []
    for palabra in dict.fromkeys(P.tokenizar_sin_stem(consulta)):
        raiz = P.tokenizar(palabra)[0]
        d = df.get(raiz, 0)
        filas.append({"palabra": palabra, "raiz": raiz, "df": d, "pct": d / N,
                      "idf": math.log(1 + (N - d + 0.5) / (d + 0.5)) if d else 0.0})
    return pd.DataFrame(filas)


def fig_idf(t: pd.DataFrame, nombre: str, N: int, est: Estilo, version: str = "v2"):
    """S4d: barra de % de fragmentos que contienen el término, con el idf al lado."""
    go, pal = _go(), est.paleta
    t = t.sort_values("pct")
    fig = go.Figure(go.Bar(x=100 * t["pct"], y=[f"«{p}»" for p in t["palabra"]], orientation="h",
                           marker_color=pal["dorado_claro"],
                           text=[f"{100 * p:.2f} % · idf {i:.2f}" for p, i in zip(t["pct"],
                                                                                  t["idf"])],
                           textposition="outside"))
    fig.update_xaxes(range=[0, 100 * t["pct"].max() * 1.45])
    return _base(fig, est, "La unidad es el idf: entre más raro el término, más pesa",
                 "% de fragmentos que contienen el término", f"Palabras de «{nombre}»", version,
                 f"{miles(N)} fragmentos; idf = ln(1 + (N − df + 0,5) / (df + 0,5))", alto=460)


def fig_stem_lema(pares: pd.DataFrame, est: Estilo, version: str = "v2"):
    """Stem contra lema: qué palabras junta cada uno y en cuántos fragmentos aparece la raíz."""
    go = _go()
    fig = go.Figure(_tabla(est, ["Palabra", "Raíz (examen)", "Fragmentos", "Lema (proyecto final)",
                                 "Fragmentos"],
                           [list(pares["palabra"]), list(pares["stem"]),
                            [miles(x) for x in pares["df_stem"]], list(pares["lema"]),
                            [miles(x) for x in pares["df_lema"]]]))
    return _base(fig, est, "El stemming junta «maya» con «mayo»; el lema las separa", None, None,
                 version, "Misma limpieza y mismas palabras vacías; solo cambia la raíz",
                 alto=480)


def fig_indice(postings: list[dict], N: int, est: Estilo, version: str = "v2"):
    """R09: el índice invertido como lista de fragmentos por término."""
    go = _go()
    filas = [[], [], [], []]
    for p in postings:
        filas[0].append(f"«{p['palabra']}» → {p['raiz']}")
        filas[1].append(f"{miles(p['df'])} ({100 * p['df'] / N:.2f} %)")
        filas[2].append(f"{p['idf']:.2f}")
        filas[3].append("<br>".join(f"{e} · {tf} veces" for e, tf in p["top"]))
    fig = go.Figure(_tabla(est, ["Término", "Fragmentos que lo contienen", "idf",
                                 "Primeros de su lista (los de más apariciones)"],
                           filas, [0.18, 0.17, 0.07, 0.58]))
    fig.data[0].cells.height = 74
    return _base(fig, est, "El índice invertido: para cada término, la lista de fragmentos donde "
                           "aparece", None, None, version,
                 "Buscar es leer solo las listas de los términos de la consulta", alto=520)


def fig_booleano(t: pd.DataFrame, est: Estilo, version: str = "v2"):
    """R07 (D30): fragmentos que devuelve el booleano por pregunta dentro de su ventana, frente a
    los 10 ordenados de BM25. Escala logarítmica: AND va de 0 a cientos y OR a decenas de miles."""
    go, pal = _go(), est.paleta
    qs = sorted(t["query_id"].unique(), key=lambda q: -int(q.lstrip("Q")))
    piv = t.pivot(index="query_id", columns="operador", values="en_ventana").reindex(qs)
    nombres = [nombre_consulta(est, q, True) for q in qs]
    # log no admite 0: los vacíos se dibujan en 0.8 y la etiqueta dice 0
    barras = [go.Bar(name=nombre, y=nombres, x=[max(v, 0.8) for v in piv[op]], orientation="h",
                     marker_color=color, text=[miles(v) for v in piv[op]],
                     textposition="outside", cliponaxis=False)
              for op, nombre, color in (("AND", "Y: todas las palabras", pal["dorado"]),
                                        ("OR", "O: cualquier palabra", pal["gris"]))]
    fig = go.Figure(barras)
    fig.add_vline(x=10, line={"color": pal["guinda"], "width": 3, "dash": "dash"})
    fig.add_annotation(x=1, xref="x", y=1.0, yref="paper", yanchor="bottom", xanchor="left",
                       text="BM25: siempre 10, ordenados", showarrow=False,
                       font={"color": pal["guinda"], "size": 14})
    fig.update_xaxes(type="log", range=[-0.2, 5.2], dtick=1)
    fig.update_layout(barmode="group")
    vacias = int((piv["AND"] == 0).sum())
    cuantas = "1 pregunta no devuelve" if vacias == 1 else f"{vacias} preguntas no devuelven"
    sub = ("El booleano no ordena ni usa el idf" + (f"; con Y, {cuantas} nada" if vacias else ""))
    return _base(fig, est, "Con Y casi nada, con O miles, y ninguno dice cuál leer primero",
                 "Fragmentos devueltos dentro del periodo (escala logarítmica)", "Pregunta", version,
                 sub, alto=200 + 46 * len(qs), ancho=1200)


# --------------------------------------------------------------------------- IR (S5a, S6)


def fig_ap(rel: list[int], total: int, ap: float, nombre: str, modelo: str, est: Estilo,
           version: str = "v2"):
    """S5a: AP explicado con una consulta real: precisión en cada fragmento relevante."""
    go, pal = _go(), est.paleta
    precisiones, vistos = [], 0
    for i, r in enumerate(rel, 1):
        vistos += r
        precisiones.append(f"{vistos}/{i}" if r else "")
    fig = go.Figure(go.Bar(x=list(range(1, len(rel) + 1)), y=[1] * len(rel),
                           marker_color=[pal["guinda"] if r else pal["dorado_claro"] for r in rel],
                           text=[f"precisión<br>{p}" if p else "no<br>relevante"
                                 for p in precisiones], textposition="inside",
                           insidetextanchor="middle",
                           textfont={"color": [("white" if r else pal["texto"]) for r in rel]}))
    fig.update_yaxes(showticklabels=False, range=[0, 1])
    fig.update_xaxes(tickmode="linear", dtick=1)
    sumas = " + ".join(p for p in precisiones if p) or "0"
    sub = (f"{modelo}. AP = ({sumas}) / {total} relevantes conocidos = {ap:.3f} ({pct(ap)}); "
           "el MAP es el promedio del AP de todas las preguntas")
    return _base(fig, est, f"Cómo se calcula el AP: «{nombre}»", "Posición en el top 10",
                 "Fragmento recuperado", version, sub, alto=420)


def fig_map(maps: pd.DataFrame, ganador: str, est: Estilo, version: str = "v2"):
    """MAP en % por modelo (S5a), con intervalo de confianza bootstrap cuando existe (D29)."""
    go, pal = _go(), est.paleta
    m = maps.sort_values("map")
    con_ic = m["inf"].notna().all()
    err = ({"type": "data", "symmetric": False, "array": 100 * (m["sup"] - m["map"]),
            "arrayminus": 100 * (m["map"] - m["inf"]), "color": pal["texto"]} if con_ic else None)
    fig = go.Figure(go.Bar(x=100 * m["map"], y=[nombre_modelo(x) for x in m["modelo"]],
                           orientation="h", error_x=err,
                           marker_color=[pal["guinda"] if x == ganador else pal["gris"]
                                         for x in m["modelo"]],
                           text=[pct(x) for x in m["map"]], textposition="inside",
                           textfont={"color": "white"}))
    sub = ("Barras: intervalo de confianza del 95 % (bootstrap sobre las preguntas)" if con_ic
           else "Promedio del AP de las preguntas con juicios")
    return _base(fig, est, f"{nombre_modelo(ganador)} recupera mejor: MAP de "
                           f"{pct(float(maps.set_index('modelo').at[ganador, 'map']))}",
                 "MAP (%)", "Modelo", version, sub, alto=80 + 55 * len(m) + 160)


def fig_ap_consulta(ap: pd.DataFrame, modelos: list[str], est: Estilo, version: str = "v2"):
    """S6: AP por pregunta con nombres y ejes; `ap` tiene query_id, modelo y AP."""
    go, pal = _go(), est.paleta
    colores = [pal["guinda"], pal["dorado"], pal["gris"], pal["guinda_oscuro"]]
    qs = sorted(ap["query_id"].unique(), key=lambda q: int(q.lstrip("Q")))
    barras = []
    for modelo, color in zip(modelos, colores):
        g = ap[ap["modelo"] == modelo].set_index("query_id").reindex(qs)
        barras.append(go.Bar(name=nombre_modelo(modelo), x=[nombre_consulta(est, q, True)
                                                            for q in qs],
                             y=100 * g["AP"].astype(float), marker_color=color))
    fig = go.Figure(barras)
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[0, 100])
    fig.update_xaxes(tickangle=-35)
    return _base(fig, est, "Precisión promedio (AP) por pregunta", "Pregunta", "AP (%)", version,
                 "Más alto es mejor: los relevantes aparecen antes en el top 10", alto=600,
                 ancho=1250)


# --------------------------------------------------------------------------- IE (S7, S7c, S8)


def fig_prf(res: pd.DataFrame, est: Estilo, version: str = "v2"):
    """S7c: precisión, recall y F1 por tipo y método (`resultados_ie.csv`)."""
    from plotly.subplots import make_subplots

    go, pal = _go(), est.paleta
    colores = {"regla": pal["dorado"], "modelo": pal["gris"], "combinado": pal["guinda"]}
    tipos = [t for t in TIPOS if t in set(res["tipo"])]
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
                        subplot_titles=("Precisión", "Recall", "F1"))
    for j, met in enumerate(("precision", "recall", "f1"), 1):
        for metodo in ("regla", "modelo", "combinado"):
            g = res[res["metodo"] == metodo].set_index("tipo").reindex(tipos)
            fig.add_trace(go.Bar(name=est.metodos.get(metodo, metodo),
                                 x=[NOMBRE_TIPO[t] for t in tipos],
                                 y=100 * g[met].astype(float), marker_color=colores[metodo],
                                 showlegend=j == 1), row=1, col=j)
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[0, 100])
    fig = _base(fig, est, "Qué tan bien se extrae cada tipo de entidad", None, "%", version,
                "Precisión: de lo extraído, cuánto es correcto. Recall: de lo que hay, cuánto se "
                "encontró", alto=560, ancho=1300)
    for j in (1, 2, 3):
        fig.update_xaxes(title_text="Tipo de entidad", tickangle=0, tickfont={"size": 12},
                         row=1, col=j)
    fig.update_layout(legend={"y": 1.1})
    return fig


def fig_f1_referencias(ref: pd.DataFrame, est: Estilo, version: str = "v2"):
    """S7a (D35): F1 combinado por tipo con su intervalo, el techo humano y la línea base."""
    go, pal = _go(), est.paleta
    sis = ref[(ref["referencia"] == "sistema_exacto") & (ref["metodo"] == "combinado")]
    tipos = [t for t in (*TIPOS, "TODOS") if t in set(sis["tipo"])]
    s = sis.set_index("tipo").reindex(tipos)
    fig = go.Figure(go.Bar(
        name="Sistema (combinado)", x=[NOMBRE_TIPO[t] for t in tipos], y=100 * s["f1"],
        marker_color=pal["guinda"],
        error_y={"type": "data", "symmetric": False, "array": 100 * (s["ic95_sup"] - s["f1"]),
                 "arrayminus": 100 * (s["f1"] - s["ic95_inf"]), "color": pal["texto"]}))
    for nombre, clave, simbolo, color in (("Acuerdo entre dos personas (techo)", "techo_humano",
                                           "diamond", pal["dorado"]),
                                          ("Solo diccionario (línea base)", "linea_base_gazetteer",
                                           "x", pal["gris"])):
        r = ref[ref["referencia"] == clave].drop_duplicates("tipo").set_index("tipo")
        r = r.reindex(tipos)
        fig.add_trace(go.Scatter(name=nombre, x=[NOMBRE_TIPO[t] for t in tipos],
                                 y=100 * r["f1"].astype(float), mode="markers",
                                 marker={"symbol": simbolo, "size": 16, "color": color,
                                         "line": {"width": 1, "color": pal["texto"]}}))
    fig.update_yaxes(range=[0, 105])
    return _base(fig, est, "¿Está bien el F1? Comparado con lo que logran dos personas",
                 "Tipo de entidad", "F1 (%)", version,
                 "Barras de error: intervalo del 95 % (bootstrap sobre los pasajes del gold)",
                 alto=560)


def fig_errores(resumen: pd.DataFrame, est: Estilo, version: str = "v2"):
    """S8: errores agrupados por patrón, separando lo de más y lo que faltó."""
    go, pal = _go(), est.paleta
    r = resumen.assign(patron=resumen["categoria"].str.split(":").str[0])
    t = r.groupby(["patron", "error"])["n"].sum().unstack(fill_value=0)
    t = t.reindex(columns=["FP", "FN"], fill_value=0)
    t = t.assign(total=t.sum(axis=1)).sort_values("total")
    nombres = [est.patrones.get(p, p) for p in t.index]
    fig = go.Figure([go.Bar(name="Detecciones de más", y=nombres, x=t["FP"], orientation="h",
                            marker_color=pal["guinda"]),
                     go.Bar(name="Entidades que faltaron", y=nombres, x=t["FN"], orientation="h",
                            marker_color=pal["dorado"])])
    fig.update_layout(barmode="stack")
    return _base(fig, est, "Los errores se concentran en pocos patrones", "Errores", "Patrón",
                 version, "Cada patrón tiene una causa y un arreglo propuesto", alto=460)


# --------------------------------------------------------------------------- respuestas (S9)


def fig_estados(resp: pd.DataFrame, est: Estilo, version: str = "v2"):
    """S9: estado de los valores de cada tabla de respuesta, con la definición en la leyenda."""
    go, pal = _go(), est.paleta
    colores = {"respaldado_en_texto": pal["guinda"], "ambiguo": pal["dorado"],
               "contradictorio": pal["guinda_oscuro"], "no_encontrado": pal["gris"]}
    qs = sorted(resp["query_id"].unique(), key=lambda q: -int(q.lstrip("Q")))
    t = resp.groupby(["query_id", "estado"]).size().unstack(fill_value=0).reindex(qs, fill_value=0)
    barras = [go.Bar(name=est.estados.get(e, e), y=[nombre_consulta(est, q, True) for q in qs],
                     x=t[e], orientation="h", marker_color=colores[e])
              for e in colores if e in t.columns]
    fig = go.Figure(barras)
    fig.update_layout(barmode="stack", legend={"orientation": "v", "y": -0.2})
    return _base(fig, est, "Qué tan respaldada está cada respuesta", "Valores en la tabla",
                 "Pregunta", version, None, alto=200 + 38 * len(qs) + 140)


def textos_visibles(fig) -> str:
    """Todo el texto que se dibuja (títulos, ejes, etiquetas, celdas), para revisar que no haya IDs
    ni rutas (S8b, R04)."""
    return fig.to_json()


def tiene_id_o_ruta(fig) -> bool:
    texto = textos_visibles(fig)
    return bool(RE_ID.search(texto)) or "salida/" in texto or ".csv" in texto
