"""Demo web pública (PRD v2 WP-15). `make demo-web` → `uv run streamlit run src/mtx/web/app.py`.

Solo arma el encabezado, el menú y el pie; cada página vive en `vistas.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

# En Streamlit Community Cloud el paquete no se instala: se agrega `src/` al camino de importación.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st

from mtx import config
from mtx.web import arranque, estilo, vistas
from mtx.web import componentes as C

st.set_page_config(page_title="Datisa · Buscador de conferencias", page_icon="🔎",
                   layout="wide", initial_sidebar_state="collapsed")
estilo.aplicar()


@st.cache_resource(show_spinner="Preparando los datos de la demo (solo la primera vez)…")
def _preparar_datos() -> list[str]:
    return arranque.asegurar_artefactos(config.RAIZ)


_preparar_datos()

paginas = [
    st.Page(vistas.inicio, title="Inicio", url_path="inicio", default=True),
    st.Page(vistas.consultas, title="Las consultas", url_path="consultas"),
    st.Page(vistas.libre, title="Consulta libre", url_path="libre"),
    st.Page(vistas.como_funciona, title="Cómo funciona", url_path="como-funciona"),
]
vistas.PAGINAS.update({"inicio": paginas[0], "consultas": paginas[1], "libre": paginas[2]})
navegacion = st.navigation(paginas, position="hidden")

st.markdown(C.encabezado("Datisa", "Buscador de conferencias matutinas 2018–2024"),
            unsafe_allow_html=True)
with st.container(key="menu", horizontal=True):
    for p in paginas:
        st.page_link(p)

navegacion.run()
st.markdown(C.pie(), unsafe_allow_html=True)
