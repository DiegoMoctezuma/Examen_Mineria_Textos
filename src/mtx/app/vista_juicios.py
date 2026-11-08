"""Pestaña Juicios (PRD §6.5): ciega al modelo, autoguardado atómico tras cada clic.

Botones: Relevante (1), No relevante (0), Omitir por ahora, Anterior y Siguiente, con atajos de
teclado `1`, `0`, `O`, `←` y `→`. Debajo, la lista de todos los pasajes de la consulta con el juicio
de cada uno y un salto por número, para revisar lo ya juzgado. "Omitido" se guarda con `relevante` vacío y es distinto de 0. No se muestran
puntajes, rangos, variantes ni qué modelo recuperó el pasaje, y nada viene preseleccionado.
"""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from mtx import consultas
from mtx.app import componentes as C

ESTADO_CLASE = {"1": "estado-1", "0": "estado-0", "": "estado-omitido", None: ""}


@st.cache_data(show_spinner="Cargando el pool…")
def _items(sha_pool: str) -> pd.DataFrame:
    """`sha_pool` solo sirve de llave de caché: si el pool cambia, se recarga."""
    return C.cargar_items()


def _iniciar(items: pd.DataFrame, forzar: bool = False) -> None:
    ss = st.session_state
    if forzar or "juicios" not in ss:
        ss.juicios, ss.token = C.cargar_juicios()
        ss.pos = {}
        ss.mensaje = None
    for q, g in items.groupby("query_id", sort=False):
        if q not in ss.pos:
            g = g.reset_index(drop=True)
            ss.pos[q] = C.siguiente_pendiente(g, ss.juicios, 0, incluir_actual=True) or 0


def _guardar(items, q, pid, valor) -> bool:
    ss = st.session_state
    try:
        ss.juicios, ss.token = C.guardar_juicio(items, ss.juicios, ss.token, q, pid, valor,
                                                insumos=C.insumos_actuales())
        return True
    except C.ConflictoEdicion as e:
        ss.mensaje = ("error", f"{e} No se guardó nada.")
    except (ValueError, OSError) as e:
        ss.mensaje = ("error", f"No se pudo guardar: {e}")
    return False


def _accion(items: pd.DataFrame, q: str, accion: str) -> None:
    """Callback de los botones: guarda y mueve la posición de la consulta `q`."""
    ss = st.session_state
    g = items[items["query_id"] == q].reset_index(drop=True)
    i = ss.pos[q]
    pid = g.at[i, "passage_id"]
    if accion == "anterior":
        ss.pos[q] = max(0, i - 1)
        return
    if accion == "siguiente":
        ss.pos[q] = min(i + 1, len(g) - 1)
        return
    if accion == "omitir":
        if C.valor_actual(ss.juicios, q, pid) in ("0", "1"):
            ss.pos[q] = min(i + 1, len(g) - 1)  # ya juzgado: solo avanza, no borra el juicio
            return
        if not _guardar(items, q, pid, ""):
            return
    elif not _guardar(items, q, pid, accion):
        return
    sig = C.siguiente_pendiente(g, ss.juicios, i)
    if sig is None:  # consulta completa (también al revisar): pasa al siguiente en orden
        ss.mensaje = ("exito", f"{q} completa: todos sus pasajes tienen juicio.")
        ss.pos[q] = min(i + 1, len(g) - 1)
    elif accion == "omitir" and sig == i:
        ss.mensaje = ("info", "Es el único pendiente de esta consulta.")
    else:
        ss.pos[q] = sig


def _ir_a(q: str) -> None:
    """Callback del salto por número: el campo cuenta desde 1, la posición desde 0."""
    ss = st.session_state
    ss.pos[q] = int(ss[f"ir_{q}"]) - 1


def _lista_pasajes(g: pd.DataFrame, q: str, i: int) -> None:
    """Todos los pasajes de la consulta en el orden de presentación, con el juicio actual. Ciega
    al modelo: sin puntajes, rangos ni variantes."""
    ss = st.session_state
    with st.expander(f"Todos los pasajes de {q} ({len(g)}): revisar o ir a uno"):
        tabla = pd.DataFrame({
            "#": range(1, len(g) + 1),
            "Tu juicio": [C.ETIQUETAS[C.valor_actual(ss.juicios, q, pid)]
                          for pid in g["passage_id"]],
            "doc_id": g["doc_id"].astype(str),
            "Inicio del pasaje": [t[int(c):int(c) + 140].strip() + "…"
                                  for t, c in zip(g["texto"], g["inicio_cuerpo"])],
        })
        st.dataframe(tabla.style.apply(
            lambda fila: ["font-weight: 700"] * len(fila) if fila["#"] == i + 1
            else [""] * len(fila), axis=1), hide_index=True, width="stretch",
            height=35 * (len(g) + 1) + 3)  # todas las filas visibles, sin desplazarse
        # El campo refleja siempre el pasaje actual; escribir un número (Enter) o usar +/- salta.
        ss[f"ir_{q}"] = i + 1
        c1, _ = st.columns([1, 3])
        c1.number_input("Ir al pasaje número (Enter)", min_value=1, max_value=len(g), step=1,
                        key=f"ir_{q}", on_change=_ir_a, args=(q,))


def _barra_lateral(items, prog) -> str:
    ss = st.session_state
    st.sidebar.subheader("Consulta")
    # Las opciones del selector deben ser estables entre recargas: Streamlit guarda la etiqueta
    # mostrada y, si cambia (p. ej. un contador "5/18" → "6/18" tras un clic), no la encuentra y
    # regresa a la primera opción. Por eso el progreso va aparte, no en la etiqueta.
    q = st.sidebar.selectbox("Consulta", list(prog["query_id"]), key="consulta",
                             label_visibility="collapsed")
    st.sidebar.markdown(" ".join(
        f'<span class="chip-q{" completa" if r.juzgados == r.total else ""}">'
        f'{r.query_id} {r.juzgados}/{r.total}</span>' for r in prog.itertuples(index=False)),
        unsafe_allow_html=True)
    fila = prog.set_index("query_id").loc[q]
    st.sidebar.progress(fila["juzgados"] / fila["total"],
                        text=f"Esta consulta: {fila['juzgados']} de {fila['total']}"
                        + (f" · {fila['omitidos']} omitidos" if fila["omitidos"] else ""))
    tot, hechos = int(prog["total"].sum()), int(prog["juzgados"].sum())
    st.sidebar.progress(hechos / tot, text=f"Global: {hechos} de {tot}")
    st.sidebar.divider()
    if st.sidebar.button("Guardar", width="stretch",
                         help="Cada clic ya se guarda solo; esto comprueba que el disco coincide"):
        if C.sha256_ruta(C.rutas().juicios) == ss.token:
            rev = C.leer_meta(C.rutas().juicios).get("revision", 0)
            ss.mensaje = ("exito", f"Todo guardado (revisión {rev}).")
        else:
            ss.mensaje = ("error", "El archivo cambió desde otra pestaña: recarga.")
    if st.sidebar.button("Recargar desde disco", width="stretch"):
        _iniciar(items, forzar=True)
    if st.sidebar.button("Ir al primer pendiente", width="stretch"):
        g = items[items["query_id"] == q].reset_index(drop=True)
        sig = C.siguiente_pendiente(g, ss.juicios, 0, incluir_actual=True)
        if sig is not None:
            ss.pos[q] = sig
    return q


def mostrar() -> None:
    r = C.rutas()
    if not r.pool.exists():
        st.warning("Falta el pool: corre `make pool`.")
        return
    items = _items(C.sha256_ruta(r.pool))
    _iniciar(items)
    ss = st.session_state
    prog = C.progreso(items, ss.juicios)
    q = _barra_lateral(items, prog)

    bloqueos = []
    if not r.criterios.exists():
        bloqueos.append("Falta `config/criterios_relevancia.md`. El criterio lo escribe el "
                        "alumno antes del primer juicio (D07); hasta entonces no se puede juzgar.")
    bloqueos += [f"{c}. No se puede seguir juzgando: ver la skill `integridad-congelacion`."
                 for c in C.cambios_en_insumos(r)]
    for b in bloqueos:
        st.error(b)

    cons = consultas.cargar().set_index("query_id")
    st.markdown(f'<p class="consulta">{q}: {html.escape(cons.at[q, "consulta"])}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="pregunta">Pregunta de extracción (ayuda): '
                f'{html.escape(cons.at[q, "pregunta_extraccion"])}</p>', unsafe_allow_html=True)
    if r.criterios.exists():
        with st.expander("Criterio de relevancia (la fecha y el modelo no cuentan)"):
            st.markdown(r.criterios.read_text(encoding="utf-8"))

    if ss.mensaje:
        tipo, texto = ss.mensaje
        {"error": st.error, "exito": st.success, "info": st.info}[tipo](texto)
        ss.mensaje = None

    g = items[items["query_id"] == q].reset_index(drop=True)
    i = min(ss.pos[q], len(g) - 1)
    it = g.iloc[i]
    valor = C.valor_actual(ss.juicios, q, it["passage_id"])
    clase = ESTADO_CLASE[valor]
    st.markdown(
        f'Pasaje {i + 1} de {len(g)} · <span class="estado-juicio {clase}">'
        f'{C.ETIQUETAS[valor]}</span>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 3])
    c1.markdown(f"**doc_id** {it['doc_id']}")
    c2.markdown(f"**Interlocutor** {it['interlocutor'] or '(sin marca)'}")
    c3.markdown(f"**Fecha** {it['fecha'] or 'desconocida'} · *no cuenta para el juicio*")
    st.caption(it["titulo"])
    try:
        cuerpo = C.html_pasaje(it["texto"], int(it["inicio_cuerpo"]), cons.at[q, "consulta"])
    except ValueError as e:
        st.error(f"Error de resaltado (se muestra el texto sin marcas): {e}")
        cuerpo = C.html_desde_spans(it["texto"], [])
    st.markdown(f'<div class="pasaje">{cuerpo}</div>', unsafe_allow_html=True)
    st.write("")

    off = bool(bloqueos)
    b1, b2, b3, b4, b5, _ = st.columns([1.3, 1.3, 1.3, 1, 1, 1])
    b1.button("Relevante (1)", key="rel", type="primary", shortcut="1", disabled=off,
              on_click=_accion, args=(items, q, "1"), width="stretch")
    b2.button("No relevante (0)", key="norel", shortcut="0", disabled=off,
              on_click=_accion, args=(items, q, "0"), width="stretch")
    b3.button("Omitir por ahora", key="omitir", shortcut="o", disabled=off,
              on_click=_accion, args=(items, q, "omitir"), width="stretch")
    b4.button("Anterior", key="anterior", shortcut="left", disabled=i == 0,
              on_click=_accion, args=(items, q, "anterior"), width="stretch")
    b5.button("Siguiente", key="siguiente", shortcut="right", disabled=i == len(g) - 1,
              on_click=_accion, args=(items, q, "siguiente"), width="stretch")
    st.write("")
    _lista_pasajes(g, q, i)
