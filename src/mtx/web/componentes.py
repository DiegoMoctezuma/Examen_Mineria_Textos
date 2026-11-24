"""Piezas HTML de la demo web, sin Streamlit (se prueban con pytest).

Todo texto variable pasa por `html.escape`; ningún bloque lleva `passage_id`, `doc_id` ni rutas
(PRD v2 D36). Los pasajes se nombran con `mtx.presentacion`.
"""
from __future__ import annotations

import html

import pandas as pd

from mtx import presentacion as P
from mtx.app.componentes import html_desde_spans, spans_terminos
from mtx.web import resumen

TIPOS = {"PER": "Persona", "ORG": "Organización", "LOC": "Lugar", "FECHA": "Fecha",
         "MONTO": "Monto"}
# Ante spans solapados se muestra uno solo: primero el confirmado por regla y modelo.
PRIORIDAD_METODO = {"ambos": 0, "regla": 1, "modelo": 2}


def e(texto) -> str:
    return html.escape(str(texto))


def spans_entidades(ents: pd.DataFrame, inicio_cuerpo: int) -> list[tuple[int, int, str]]:
    """Spans del cuerpo para resaltar, relativos a `inicio_cuerpo`, sin solapes: si dos entidades
    se cruzan gana la de método más fuerte y después la más larga."""
    if ents is None or ents.empty:
        return []
    filas = ents.assign(
        _p=ents["metodo"].map(PRIORIDAD_METODO).fillna(3) if "metodo" in ents else 3,
        _l=ents["fin"].astype(int) - ents["inicio"].astype(int))
    elegidos: list[tuple[int, int, str]] = []
    for f in filas.sort_values(["_p", "_l", "inicio"], ascending=[True, False, True]).itertuples():
        ini, fin = int(f.inicio) - inicio_cuerpo, int(f.fin) - inicio_cuerpo
        if ini < 0 or f.tipo not in TIPOS:
            continue
        if any(ini < b and a < fin for a, b, _ in elegidos):
            continue
        elegidos.append((ini, fin, f"ent e-{f.tipo}"))
    return sorted(elegidos)


def html_cuerpo(texto: str, inicio_cuerpo: int, ents: pd.DataFrame | None = None) -> str:
    """Cuerpo del pasaje (sin la marca del interlocutor) con las entidades resaltadas por tipo."""
    cuerpo = texto[inicio_cuerpo:]
    spans = spans_entidades(ents, inicio_cuerpo) if ents is not None else []
    spans = [(a, b, c) for a, b, c in spans if b <= len(cuerpo)]
    return html_desde_spans(cuerpo, spans)


def html_cuerpo_terminos(texto: str, inicio_cuerpo: int, consulta: str) -> str:
    """Cuerpo del pasaje con las palabras que coinciden con la consulta resaltadas (misma raíz
    que usa el índice)."""
    spans = [(a - inicio_cuerpo, b - inicio_cuerpo, "termino")
             for a, b, _ in spans_terminos(texto, inicio_cuerpo, consulta)]
    return html_desde_spans(texto[inicio_cuerpo:], spans)


def buscador(consulta: str, filtro: str) -> str:
    """Caja de búsqueda ilustrativa (no editable) con la consulta y su filtro de fechas."""
    return (f'<div class="buscador"><span class="lupa">⌕</span><span class="q">{e(consulta)}'
            f'</span><span class="filtro">{e(filtro)}</span></div>')


def raices(tokens: list[str]) -> str:
    return "".join(f'<span class="raiz">{e(t)}</span>' for t in tokens)


def paso(n: int, titulo_: str, cuerpo: str) -> str:
    """Un paso del recorrido guiado. `cuerpo` ya es HTML."""
    return (f'<section class="paso"><div class="paso-num">{n}</div><div class="paso-cuerpo">'
            f'<h2>{e(titulo_)}</h2>{cuerpo}</div></section>')


def leyenda() -> str:
    chips = "".join(f'<span class="ent e-{t}">{e(n)}</span>' for t, n in TIPOS.items())
    return f'<div class="leyenda"><span class="leyenda-tit">Entidades:</span>{chips}</div>'


def encabezado(nombre: str, lema: str) -> str:
    return (f'<div class="franja"><div class="marca"><span class="marca-nombre">{e(nombre)}'
            f'</span><span class="marca-lema">{e(lema)}</span></div></div>')


def migas(pasos: list[str]) -> str:
    partes = ['<span class="casa" aria-label="Inicio">⌂</span>']
    for i, p in enumerate(pasos):
        clase = "actual" if i == len(pasos) - 1 else ""
        partes.append(f'<span class="sep">›</span><span class="{clase}">{e(p)}</span>')
    return f'<nav class="migas">{"".join(partes)}</nav>'


def etiqueta(texto: str) -> str:
    """Etiqueta de sección con punta de flecha, como "Publicaciones recientes" en gob.mx."""
    return f'<div class="etiqueta-fila"><span class="etiqueta">{e(texto)}</span></div>'


def titulo(texto: str, entrada: str | None = None, meta: str | None = None) -> str:
    partes = [f'<h1 class="titulo">{e(texto)}</h1>']
    if entrada:
        partes.append(f'<p class="entrada">{e(entrada)}</p>')
    if meta:
        partes.append(f'<p class="meta">{e(meta)}</p>')
    return "".join(partes)


def _fragmento_contexto(rotulo: str, fila) -> str:
    """Un vecino del contexto: quién habla, su frase representativa (cita textual elegida por
    `resumen.py`) y el texto completo en un desplegable."""
    f = P.ficha(fila)
    texto, ic = str(fila["texto"]), int(fila["inicio_cuerpo"])
    frase = resumen.frase_representativa(texto, ic)
    return (f'<div class="ctx"><p class="ctx-tit">{e(rotulo)} · fragmento {f.fragmento} · '
            f'{e(f.habla)}</p><p class="ctx-frase"><span>Frase representativa</span>'
            f'«{e(frase)}»</p><details class="ctx-completo"><summary>Leer completo</summary>'
            f'<div class="ctx-texto">{e(texto[ic:])}</div></details></div>')


def html_contexto(contexto: tuple | None) -> str:
    """Desplegable con el fragmento anterior y el siguiente del mismo discurso. Reemplaza el enlace
    al sitio original, que ya no sirve las versiones estenográficas."""
    if not contexto or all(x is None for x in contexto):
        return ""
    antes, despues = contexto
    partes = []
    if antes is not None:
        partes.append(_fragmento_contexto("Antes", antes))
    partes.append('<div class="ctx-aqui">▲ antes · este fragmento · después ▼</div>')
    if despues is not None:
        partes.append(_fragmento_contexto("Después", despues))
    return (f'<details class="contexto"><summary>Ver contexto</summary>{"".join(partes)}'
            f'</details>')


def _cabeza(f: P.Ficha, rango: int | None, extra: str = "") -> str:
    num = f'<span class="rango">{rango}</span>' if rango is not None else ""
    habla_cls = "habla prensa" if f.habla == P.PRENSA else "habla"
    lugar = f' · <span class="lugar">{e(f.lugar)}</span>' if f.lugar else ""
    return (f'<header>{num}<div><h3>{e(f.titulo)}</h3>'
            f'<p class="{habla_cls}">{e(f.habla)}{lugar}{extra}</p></div></header>')


def tarjeta_pasaje(fila, ents: pd.DataFrame | None = None, rango: int | None = None,
                   nota: str | None = None, contexto: tuple | None = None,
                   consulta: str | None = None) -> str:
    """Tarjeta de un pasaje: título legible, quién habla, lugar, texto con entidades resaltadas
    (o, con `consulta`, con las palabras de la consulta) y el contexto del discurso. `fila` trae
    las columnas de `pasajes.parquet`."""
    f = P.ficha(fila)
    nota_html = f'<p class="nota">{e(nota)}</p>' if nota else ""
    if consulta is not None:
        cuerpo = html_cuerpo_terminos(str(fila["texto"]), int(fila["inicio_cuerpo"]), consulta)
    else:
        cuerpo = html_cuerpo(str(fila["texto"]), int(fila["inicio_cuerpo"]), ents)
    return (f'<article class="pasaje-tarjeta">{_cabeza(f, rango)}{nota_html}'
            f'<div class="pasaje-texto">{cuerpo}</div>{html_contexto(contexto)}</article>')


def tarjeta_mini(fila, rango: int, en_ambos: bool, contexto: tuple | None = None) -> str:
    """Renglón compacto del top-10 para comparar modelos: título, quién habla, inicio del texto y
    el fragmento completo en un desplegable."""
    f = P.ficha(fila)
    marca = ' · <span class="en-ambos">en los dos</span>' if en_ambos else ""
    cuerpo = str(fila["texto"])[int(fila["inicio_cuerpo"]):]
    return (f'<article class="pasaje-tarjeta mini{" comun" if en_ambos else ""}">'
            f'{_cabeza(f, rango, marca)}<p class="inicio-texto">{e(recorte(cuerpo, 170))}</p>'
            f'<details class="contexto"><summary>Leer fragmento</summary>'
            f'<div class="ctx-texto">{e(cuerpo)}</div></details>'
            f'{html_contexto(contexto)}</article>')


def recorte(texto: str, largo: int) -> str:
    return P.recortar(texto, largo)


ESTADOS = {"respaldado_en_texto": ("Respaldado en el texto", "ok"),
           "ambiguo": ("Ambiguo", "amb"),
           "contradictorio": ("Contradictorio", "contra"),
           "no_encontrado": ("Sin evidencia", "nada")}


def _cita_con_valores(cita: str, valores: list[str]) -> str:
    """La cita con la primera aparición de cada valor en negritas (búsqueda literal, sin
    solapes)."""
    spans: list[tuple[int, int]] = []
    for v in valores:
        i = cita.find(v) if v else -1
        if i >= 0 and not any(i < b and a < i + len(v) for a, b in spans):
            spans.append((i, i + len(v)))
    partes, fin = [], 0
    for a, b in sorted(spans):
        partes.append(f"{e(cita[fin:a])}<strong>{e(cita[a:b])}</strong>")
        fin = b
    partes.append(e(cita[fin:]))
    return "".join(partes)


def renglon_respuesta(valores: list[str], unidad: str, estado: str, cita: str, fuente: str,
                      habla: str, n_discursos: int | None = None) -> str:
    """Uno o varios valores que salen de la misma cita: valores, estado, cita y de dónde sale."""
    etiqueta_, clase = ESTADOS.get(estado, (estado, "nada"))
    uni = f' <span class="unidad">{e(unidad)}</span>' if unidad else ""
    veces = (f" · mencionado en {n_discursos} discursos" if n_discursos and n_discursos > 1
             else "")
    texto_valores = " · ".join(e(v) for v in valores)
    return (f'<div class="resp-renglon"><div class="resp-valor"><span>{texto_valores}{uni}'
            f'</span><span class="estado {clase}">{e(etiqueta_)}</span></div>'
            f'<blockquote>{_cita_con_valores(cita, valores)}</blockquote>'
            f'<p class="resp-fuente">{e(fuente)} · {e(habla)}{e(veces)}</p></div>')


def tarjeta_campo(campo: str, renglones: list[str], ocultos: list[str] | None = None,
                  vacio: str = "Sin evidencia en los 10 mejores fragmentos.") -> str:
    """Tarjeta de un campo de la respuesta (p. ej. "Montos de inversión")."""
    cuerpo = "".join(renglones) if renglones else f'<p class="nota">{e(vacio)}</p>'
    mas = ""
    if ocultos:
        mas = (f'<details class="mas"><summary>Ver {len(ocultos)} valores más</summary>'
               f'{"".join(ocultos)}</details>')
    return (f'<section class="campo-tarjeta"><h3>{e(campo[:1].upper() + campo[1:])}</h3>'
            f'{cuerpo}{mas}</section>')


def tarjeta_guinda(titulo_: str, cuerpo: str) -> str:
    """Recuadro guinda de la columna lateral (como la encuesta de gob.mx). `cuerpo` ya es HTML."""
    return (f'<aside class="tarjeta-guinda"><div class="tg-tit">{e(titulo_)}</div>'
            f'<div class="tg-cuerpo">{cuerpo}</div></aside>')


def pie() -> str:
    return ('<footer class="pie"><div><strong>Datisa</strong> · Minería de Textos, proyecto final '
            '2026</div><div>Proyecto escolar. No es un sitio oficial ni está afiliado a ninguna '
            'dependencia de gobierno. Fuente: versiones estenográficas públicas de las '
            'conferencias presidenciales 2018 a 2024.</div></footer>')
