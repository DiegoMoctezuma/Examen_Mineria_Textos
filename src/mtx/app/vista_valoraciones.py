"""Pestaña Valoraciones (PRD §6.13.5, H8): el alumno lee cada tabla de respuesta y escribe 2 a 3
líneas (¿es creíble?, ¿qué le falta?, ¿qué está mal?). La app guarda el texto con la huella de la
tabla; si `make tablas` cambia la tabla, la valoración queda invalidada. Nunca precarga texto."""
from __future__ import annotations

import json

import streamlit as st

from mtx import config
from mtx import respuestas as RS
from mtx.app import componentes as C

DIR_TABLAS = config.DIR_SALIDA / "tablas_respuesta"
HASHES = config.DIR_SALIDA / "10_hashes_tablas.json"


def _ruta():
    return C.rutas().anotaciones / "valoraciones.yaml"


def _guardar(q: str, h: str) -> None:
    ss = st.session_state
    try:
        ss.token_val = RS.guardar_valoracion(_ruta(), ss.token_val, q, ss.get(f"val_{q}", ""), h)
        ss.toast_val = f"Valoración de {q} guardada."
    except C.ConflictoEdicion as e:
        ss.msg_val = f"{e} No se guardó nada."
    except (ValueError, OSError) as e:
        ss.msg_val = f"No se guardó: {e}"


def mostrar() -> None:
    st.header("Valoraciones de las tablas de respuesta")
    if not HASHES.exists():
        st.info("Faltan las tablas: corre `make tablas`.")
        return
    hashes = json.loads(HASHES.read_text(encoding="utf-8"))
    ss = st.session_state
    if "token_val" not in ss or st.sidebar.button("Recargar desde disco"):
        ss.token_val = C.sha256_ruta(_ruta())
    datos = RS.leer_valoraciones(_ruta())

    def estado(q: str) -> str:
        e = datos.get(q)
        if not e or not str(e.get("texto", "")).strip():
            return "pendiente"
        return "vigente" if e.get("tabla_sha256") == hashes[q] else "invalidada"

    qs = list(hashes)
    q = st.sidebar.selectbox("Consulta", qs, key="q_val")
    hechas = sum(estado(x) == "vigente" for x in qs)
    st.sidebar.progress(hechas / len(qs), text=f"Valoraciones vigentes: {hechas} de {len(qs)}")
    st.sidebar.markdown(" ".join(
        f'<span class="chip-q{" completa" if estado(x) == "vigente" else ""}">{x}</span>'
        for x in qs), unsafe_allow_html=True)

    if t := ss.pop("toast_val", None):
        st.toast(t)
    if m := ss.pop("msg_val", None):
        st.error(m)

    md = (DIR_TABLAS / f"{q}.md").read_text(encoding="utf-8")
    cuerpo = md.split("\n## Valoración del alumno")[0]
    st.markdown(cuerpo)
    st.divider()
    st.subheader(f"Tu valoración de {q}")
    st.caption("2 a 3 líneas: ¿es creíble?, ¿qué le falta?, ¿qué está mal? Escríbela tú; la "
               "app no sugiere texto.")
    e = estado(q)
    if e == "invalidada":
        st.warning("La tabla cambió desde que escribiste esta valoración: revísala y guárdala de "
                   "nuevo.")
    if f"val_{q}" not in ss:
        ss[f"val_{q}"] = str((datos.get(q) or {}).get("texto", ""))
    st.text_area("Valoración", key=f"val_{q}", height=130, label_visibility="collapsed")
    st.button("Guardar valoración", type="primary", on_click=_guardar, args=(q, hashes[q]))
    st.caption(f"Estado: **{e}** · huella de la tabla `{hashes[q][:12]}`")
