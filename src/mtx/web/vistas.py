"""Páginas de la demo web. La lógica de datos está en `datos.py` y el HTML en `componentes.py`."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from mtx import presentacion as P
from mtx.respuestas import MAX_VALORES
from mtx.web import componentes as C
from mtx.web import datos as D

EJEMPLO = "Q3"   # refinería de Dos Bocas (D36: ejemplo guiado precargado)
EXPLICA_MODELOS = (
    "Los dos métodos puntúan cada fragmento por las palabras que comparte con la consulta. "
    "<strong>TF-IDF</strong> premia las palabras raras en el corpus y compara la consulta con el "
    "fragmento como dos vectores. <strong>BM25</strong> también premia las palabras raras, pero "
    "deja de sumar cuando una palabra se repite mucho y compensa la longitud del fragmento, así "
    "que los textos largos no ganan solo por largos.")
# `app.py` registra aquí sus páginas para poder enlazarlas entre sí.
PAGINAS: dict = {}


@st.cache_resource(show_spinner="Cargando los resultados del experimento…")
def artefactos() -> D.Artefactos:
    return D.cargar_artefactos()


@st.cache_data(show_spinner=False)
def cifras() -> dict:
    return D.cifras()


def html(x: str) -> None:
    st.markdown(x, unsafe_allow_html=True)


def nombre(consulta: str) -> str:
    return consulta[:1].upper() + consulta[1:]


def meta_consulta(c: dict) -> str:
    return (f"Consulta del experimento | del {P.fecha_larga(c['desde'])} al "
            f"{P.fecha_larga(c['hasta'])}")


# --------------------------------------------------------------------------- inicio


@st.cache_data(show_spinner=False)
def conteo_ventana(desde: str, hasta: str) -> tuple[int, int]:
    return D.conteo_ventana(desde, hasta)


def fragmento_ilustrativo(a: D.Artefactos, q: str) -> tuple:
    """Del top-10 del ganador, el fragmento con más tipos de entidad en el cuerpo (desempate: el
    mejor rango). Solo elige qué mostrar; no cambia ningún resultado."""
    mejor = None
    for r in a.top(q, a.mejor).itertuples():
        fila = a.pasajes.loc[r.passage_id]
        ents = a.entidades_de(q, r.passage_id)
        tipos = ents[ents["inicio"] >= int(fila["inicio_cuerpo"])]["tipo"].nunique()
        if mejor is None or tipos > mejor[0]:
            mejor = (tipos, r.rango, fila, ents)
    return mejor


def inicio() -> None:
    from mtx import preproceso

    a = artefactos()
    cifras()
    c = a.consulta(EJEMPLO)
    consulta = c["consulta"]
    html(C.migas(["Inicio"]))
    html(C.etiqueta("Ejemplo guiado"))
    principal, lateral = st.columns([2.1, 1], gap="large")
    with lateral:
        html(C.tarjeta_guinda(
            "¿Qué hace este buscador?",
            "<p>Busca en las versiones estenográficas de las mañaneras y otros eventos públicos, "
            "de diciembre de 2018 a septiembre de 2024, los fragmentos que responden a una "
            "pregunta, y arma una respuesta en la que cada dato lleva la cita que lo respalda."
            "</p><p>A la izquierda, paso a paso, lo que pasa con una pregunta real.</p>"))
        if PAGINAS:
            st.write("")
            st.page_link(PAGINAS["libre"], label="Hacer mi propia búsqueda →")
            st.page_link(PAGINAS["consultas"], label="Ver las consultas del experimento →")
    with principal:
        html(C.titulo("Así responde el buscador una pregunta",
                      "Seguimos una consulta del experimento de principio a fin: qué se busca, "
                      "qué fragmentos encuentra, qué datos extrae de ellos y cómo los junta en una "
                      "respuesta."))

        # 1 · La pregunta
        filtro = f"{P.fecha_larga(c['desde'])} – {P.fecha_larga(c['hasta'])}"
        html(C.paso(1, "La pregunta",
                    C.buscador(nombre(consulta), filtro)
                    + f'<p>Queremos saber <strong>{C.e(c["pregunta_extraccion"].lower())}</strong>'
                    '. Cada consulta del experimento trae su propia ventana de fechas, y solo se '
                    'busca dentro de ella.</p>'))

        # 2 · La búsqueda
        en_ventana, total = conteo_ventana(c["desde"], c["hasta"])
        tokens = preproceso.tokenizar(consulta, "stem")
        top = a.top(EJEMPLO, a.mejor)
        html(C.paso(2, "La búsqueda",
                    '<p>Se quitan las palabras vacías como «de» o «en», y cada palabra se reduce a '
                    'su raíz, para que «refinería», «refinerías» y «refinar» cuenten igual:</p>'
                    f'<div>{C.raices(tokens)}</div>'
                    '<div class="embudo">'
                    f'<div><strong>{total:,}</strong><span>fragmentos en total</span></div>'
                    f'<div><strong>{en_ventana:,}</strong><span>dentro de las fechas</span></div>'
                    f'<div><strong>10</strong><span>mejores según {D.NOMBRE_MODELO[a.mejor]}'
                    '</span></div></div>'
                    f'<p>{D.NOMBRE_MODELO[a.mejor]} puntúa cada fragmento por cuántas de esas '
                    'raíces contiene y qué tan raras son en el corpus. Estos son los tres primeros; '
                    'en amarillo, las palabras que coinciden:</p>'))
        for r in top.head(3).itertuples():
            html(C.tarjeta_pasaje(a.pasajes.loc[r.passage_id], rango=r.rango,
                                  contexto=a.contexto(r.passage_id), consulta=consulta))

        # 3 · Las entidades
        _, rango, fila, ents = fragmento_ilustrativo(a, EJEMPLO)
        html(C.paso(3, "Los datos de cada fragmento",
                    '<p>En cada uno de los 10 fragmentos, reglas escritas a mano y un modelo de '
                    'lenguaje marcan personas, organizaciones, lugares, fechas y montos. Así se '
                    f've el fragmento número {rango}:</p>{C.leyenda()}'))
        html(C.tarjeta_pasaje(fila, ents, rango=rango, contexto=a.contexto(fila["passage_id"])))

        # 4 · La respuesta
        muestra = []
        for campo, renglones in renglones_respuesta(a, EJEMPLO).items():
            ok = [x for est, x in renglones if est == "respaldado_en_texto"]
            if ok:
                muestra.append(C.tarjeta_campo(campo, ok[:1]))
        html(C.paso(4, "La respuesta",
                    '<p>Las entidades se ordenan según la pregunta (organizaciones, responsables, '
                    'montos) y cada una se muestra con la oración que la contiene. '
                    f'{EXPLICA_ESTADOS} Un dato por campo:</p>' + "".join(muestra)))
        if PAGINAS:
            st.page_link(PAGINAS["consultas"], label="Ver la respuesta completa y la comparación "
                         "TF-IDF frente a BM25 →", query_params={"q": EJEMPLO})


# --------------------------------------------------------------------------- consultas


def consultas() -> None:
    a = artefactos()
    ids = list(a.consultas["query_id"])
    nombres = {q: nombre(a.consulta(q)["consulta"]) for q in ids}
    pedida = st.query_params.get("q", EJEMPLO)
    html(C.migas(["Inicio", "Las consultas"]))
    q = st.selectbox("Elige una consulta", ids, index=ids.index(pedida) if pedida in ids else 0,
                     format_func=nombres.get)
    if q != pedida:
        st.query_params["q"] = q
    if len(ids) < 15:
        st.caption("Por ahora se muestran las diez consultas de la primera ronda; las cinco "
                   "nuevas se agregan cuando cierre la evaluación de la segunda.")
    c = a.consulta(q)
    html(C.titulo(nombres[q], f"Pregunta: {c['pregunta_extraccion']}.", meta_consulta(c)))
    t_resp, t_pas, t_comp = st.tabs(["Respuesta", "Fragmentos y entidades",
                                     "TF-IDF frente a BM25"])
    with t_resp:
        respuesta(a, q)
    with t_pas:
        html(C.leyenda())
        st.caption(f"Los 10 mejores fragmentos según {D.NOMBRE_MODELO[a.mejor]}, el método que "
                   "ganó en la evaluación.")
        for r in a.top(q, a.mejor).itertuples():
            html(C.tarjeta_pasaje(a.pasajes.loc[r.passage_id], a.entidades_de(q, r.passage_id),
                                  rango=r.rango, contexto=a.contexto(r.passage_id)))
    with t_comp:
        comparacion(a, q)


def renglones_respuesta(a: D.Artefactos, q: str) -> dict[str, list[tuple[str, str]]]:
    """Por campo, los renglones de la respuesta como (estado, html). Los valores que salen de la
    misma cita van juntos en un solo renglón."""
    res = a.respuestas[a.respuestas["query_id"] == q]
    evi = a.evidencias[a.evidencias["query_id"] == q]
    veces = (evi.assign(n=pd.to_numeric(evi["n_discursos"], errors="coerce"))
             .groupby(["campo_respuesta", "valor"])["n"].max())
    salida: dict[str, list[tuple[str, str]]] = {}
    for campo in dict.fromkeys(res["campo_respuesta"]):
        g = res[(res["campo_respuesta"] == campo) & (res["estado"] != "no_encontrado")]
        grupos: dict[tuple, list[dict]] = {}
        for f in g.to_dict("records"):
            grupos.setdefault((f["estado"], f["passage_id"], f["cita"], f["unidad"]), []).append(f)
        renglones = []
        for (estado, pid, cita, unidad), fs in grupos.items():
            valores = list(dict.fromkeys(f["valor"] for f in fs))
            fila = a.pasajes.loc[pid] if pid in a.pasajes.index else None
            ficha = P.ficha(fila) if fila is not None else None
            ns = [veces.get((campo, v)) for v in valores]
            ns = [int(n) for n in ns if n is not None and pd.notna(n)]
            renglones.append((estado, C.renglon_respuesta(
                valores, unidad, estado, cita,
                ficha.titulo if ficha else P.fecha_larga(fs[0]["fecha_documento"]),
                ficha.habla if ficha else P.quien_habla(fs[0]["interlocutor"]),
                max(ns) if ns else None)))
        salida[campo] = renglones
    return salida


EXPLICA_ESTADOS = (
    '<strong>Respaldado en el texto</strong>: la misma oración liga el dato con el tema (por '
    'ejemplo, habla de construir, invertir o participar). Es lo que dice el texto, no una '
    'verificación de que sea verdad. <strong>Ambiguo</strong>: el dato aparece, pero la oración '
    'no lo liga con el tema, o lo dice un reportero al preguntar.')


def respuesta(a: D.Artefactos, q: str) -> None:
    html(f'<p class="explica">Cada dato sale de los 10 mejores fragmentos y lleva su cita. '
         f'{EXPLICA_ESTADOS}</p>')
    cols = st.columns(2, gap="medium")
    for i, (campo, renglones) in enumerate(renglones_respuesta(a, q).items()):
        h = [x for _, x in renglones]
        with cols[i % 2]:
            html(C.tarjeta_campo(campo, h[:MAX_VALORES], h[MAX_VALORES:]))


def comparacion(a: D.Artefactos, q: str) -> None:
    k = cifras()
    html(f'<p class="explica">{EXPLICA_MODELOS} En la evaluación con juicios humanos, BM25 obtuvo '
         f'una precisión promedio (MAP) de {k["map"]["bm25"]:.2f} contra {k["map"]["tfidf"]:.2f} '
         f'de TF-IDF; de cada 10 fragmentos, en promedio {k["p10"]["bm25"] * 10:.1f} fueron '
         f'relevantes con BM25 y {k["p10"]["tfidf"] * 10:.1f} con TF-IDF.</p>')
    tops = {m: a.top(q, m) for m in D.MODELOS}
    comunes = set(tops["tfidf"]["passage_id"]) & set(tops["bm25"]["passage_id"])
    st.caption(f"{len(comunes)} de 10 fragmentos aparecen en los dos; están marcados en dorado.")
    cols = st.columns(2, gap="medium")
    for col, m in zip(cols, D.MODELOS):
        with col:
            gana = '<span class="gana">ganador</span>' if m == a.mejor else ""
            html(f'<div class="col-tit">{D.NOMBRE_MODELO[m]}{gana}</div>')
            for r in tops[m].itertuples():
                html(C.tarjeta_mini(a.pasajes.loc[r.passage_id], r.rango,
                                    r.passage_id in comunes, a.contexto(r.passage_id)))


# --------------------------------------------------------------------------- otras


def libre() -> None:
    html(C.migas(["Inicio", "Consulta libre"]))
    html(C.etiqueta("En construcción"))
    st.info("Esta sección se arma en el bloque B5.")


def como_funciona() -> None:
    k = cifras()
    html(C.migas(["Inicio", "Cómo funciona"]))
    html(C.titulo("Cómo funciona",
                  "Del texto de las conferencias a una respuesta con citas, en cinco pasos."))
    pasos = [
        ("1. Los textos",
         (f"{k['discursos']:,} versiones estenográficas de diciembre de 2018 a septiembre de 2024. "
         "Se limpian las acotaciones (como «aplausos») y se separa quién habla en cada "
         "intervención.")),
        ("2. Los fragmentos",
         (f"Cada intervención se parte en fragmentos de unas {k['palabras_por_pasaje']:.0f} "
         f"palabras en promedio: {k['pasajes']:,} en total. Los "
         "de menos de 40 palabras se descartan, sean de quien sean, porque son demasiado cortos "
         "para entenderse solos.")),
        ("3. La búsqueda",
         (f"{EXPLICA_MODELOS} Ambos aceptan un filtro de fechas. Con juicios de relevancia hechos "
         f"por personas, BM25 logró una precisión promedio de {k['map']['bm25']:.2f} y TF-IDF de "
         f"{k['map']['tfidf']:.2f}.")),
        ("4. Las entidades",
         ("Reglas escritas a mano (fechas, montos, listas de organizaciones y lugares) y un "
         "modelo de lenguaje entrenado para reconocer nombres marcan personas, organizaciones, "
         "lugares, fechas y montos. Comparadas contra una anotación manual, juntas encuentran "
         f"más: el {k['recall']['combinado'] * 100:.0f} % de las entidades, contra el "
         f"{k['recall']['regla'] * 100:.0f} % de las reglas solas y el "
         f"{k['recall']['modelo'] * 100:.0f} % del modelo solo, con un F1 de "
         f"{k['f1']['combinado']:.3f} (reglas {k['f1']['regla']:.3f}, modelo "
         f"{k['f1']['modelo']:.3f}).")),
        ("5. La respuesta",
         ("Para cada pregunta se juntan las entidades de los 10 mejores fragmentos y cada valor se "
         "muestra con su cita. Las preguntas de los reporteros sí se buscan, porque nombran el "
         f"tema (son el {k['pct_reporteros']:.1f} % de los fragmentos), pero lo que dice un "
         "reportero nunca cuenta como respaldo: queda como «ambiguo».")),
    ]
    for t, cuerpo in pasos:
        html(f'<section class="campo-tarjeta"><h3>{C.e(t)}</h3><p>{cuerpo}</p></section>')
