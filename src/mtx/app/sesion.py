"""Quién usa la app en esta sesión (PRD v2 D24): lista cerrada de `config/v2/anotadores.yaml`,
sin contraseña, recordada en la sesión y en la URL (`?anotador=arturo`). La comparten las
pestañas Juicios, Gold y Adjudicación: al cambiar de persona se borra todo el estado de la sesión,
para que nada de una persona quede a la vista de otra."""
from __future__ import annotations

import html

import streamlit as st

from mtx import anotadores


def _fijar() -> None:
    ss = st.session_state
    elegido = ss.elegir_anotador
    for k in list(ss.keys()):
        del ss[k]
    ss.anotador = elegido
    st.query_params["anotador"] = elegido


def _cambiar() -> None:
    ss = st.session_state
    for k in list(ss.keys()):
        del ss[k]
    st.query_params.pop("anotador", None)


def anotador(pregunta: str, rol: str, ayuda: str) -> str | None:
    """Id del anotador de esta sesión, o None mientras no elija (y entonces dibuja el selector).
    `rol`: frase de la barra lateral ("Juzgas como", "Anotas como")."""
    ss = st.session_state
    try:
        lista = anotadores.cargar_anotadores()
    except FileNotFoundError:
        st.error(f"Falta {anotadores.ruta_anotadores()} (lista de anotadores v2).")
        return None
    url = st.query_params.get("anotador")
    if "anotador" not in ss and url in lista:
        ss.anotador = url
    if ss.get("anotador") in lista:
        a = lista[ss.anotador]
        st.sidebar.markdown(f"{rol} **{html.escape(a.nombre)}**")
        st.sidebar.button("Cambiar de anotador", on_click=_cambiar, width="stretch")
        st.sidebar.divider()
        return ss.anotador
    st.subheader(pregunta)
    st.selectbox("Tu nombre", list(lista), index=None, key="elegir_anotador",
                 format_func=lambda i: lista[i].nombre, placeholder="Elige tu nombre",
                 on_change=_fijar)
    st.caption(ayuda)
    return None
