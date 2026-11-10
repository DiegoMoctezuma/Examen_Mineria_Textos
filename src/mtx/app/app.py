"""App local de anotación (PRD §7). `make app` → `uv run streamlit run src/mtx/app/app.py`.

Solo registra las páginas; cada `vista_*.py` las dibuja y la lógica vive en `componentes.py`.
"""
from __future__ import annotations

import streamlit as st

from mtx.app import (
                     estilo,
                     vista_estado,
                     vista_gazetteer,
                     vista_gold,
                     vista_juicios,
                     vista_pendiente,
                     vista_valoraciones,
)

st.set_page_config(page_title="Anotación · Minería de Textos", page_icon="📝", layout="wide")
estilo.aplicar()

paginas = [
    st.Page(vista_estado.mostrar, title="Estado", url_path="estado", default=True),
    st.Page(vista_juicios.mostrar, title="Juicios", url_path="juicios"),
    st.Page(vista_gold.mostrar, title="Gold", url_path="gold"),
    st.Page(vista_gazetteer.mostrar, title="Gazetteer", url_path="gazetteer"),
    st.Page(vista_valoraciones.mostrar, title="Valoraciones", url_path="valoraciones"),
    st.Page(vista_pendiente.demo, title="Demo", url_path="demo"),
]
st.navigation(paginas, position="top").run()
