"""Pestaña Valoraciones (PRD §6.13.5, H8): el alumno lee cada tabla de respuesta y escribe 2 a 3
líneas (¿es creíble?, ¿qué le falta?, ¿qué está mal?). La app guarda el texto con la huella de la
tabla; si `make tablas` cambia la tabla, la valoración queda invalidada. Nunca precarga texto.

v2 (WP-13): si existen las tablas de `make tablas-v2`, se elige v1 o v2. En v2 cada persona escribe
solo su archivo, `anotaciones/valoraciones_v2/<anotador>.yaml`, para que tres personas valoren en
tres computadoras sin chocar."""
from __future__ import annotations

import json

import streamlit as st

from mtx import config
from mtx import respuestas as RS
from mtx.app import componentes as C
from mtx.app import sesion

DIR_TABLAS = config.DIR_SALIDA / "tablas_respuesta"
HASHES = config.DIR_SALIDA / "10_hashes_tablas.json"
DIR_TABLAS_V2 = config.DIR_SALIDA_V2 / "tablas_respuesta"
HASHES_V2 = config.DIR_SALIDA_V2 / "10_hashes_tablas.json"


def _ruta():
    ss = st.session_state
    if ss.get("val_version") == "v2" and ss.get("anotador"):
        return C.rutas().anotaciones / "valoraciones_v2" / f"{ss.anotador}.yaml"
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
    ss = st.session_state
    version = "v1"
    if HASHES_V2.exists():
        version = st.sidebar.radio("Tablas", ["v2", "v1"], key="val_version", horizontal=True)
    hashes_ruta, dir_tablas = (HASHES_V2, DIR_TABLAS_V2) if version == "v2" else (HASHES,
                                                                                DIR_TABLAS)
    if version == "v2" and not sesion.anotador(
            "¿Quién valora?", "valoraciones v2",
            "Cada quien guarda solo sus valoraciones en su propio archivo."):
        return
    if not hashes_ruta.exists():
        st.info("Faltan las tablas: corre `make tablas`.")
        return
    hashes = json.loads(hashes_ruta.read_text(encoding="utf-8"))
    if ss.get("val_ruta") != str(_ruta()):
        ss.val_ruta = str(_ruta())
        ss.pop("token_val", None)
        for k in [k for k in ss if str(k).startswith("val_Q")]:
            del ss[k]
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

    md = (dir_tablas / f"{q}.md").read_text(encoding="utf-8")
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
