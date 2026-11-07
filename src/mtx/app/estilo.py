"""Estilo sobrio y común para todas las páginas."""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
.pasaje {font-size: 1.08rem; line-height: 1.75; padding: 1.1rem 1.3rem; border-radius: 10px;
         border: 1px solid rgba(128,128,128,.35); background: rgba(128,128,128,.06);
         max-width: 62rem; white-space: pre-wrap;}
.pasaje mark.termino {background: #ffe08a; color: inherit; padding: 0 .12em; border-radius: 3px;}
.pasaje mark.marca {background: transparent; color: #8a8a8a; font-variant: small-caps;}
.consulta {font-size: 1.6rem; font-weight: 600; margin: 0 0 .2rem 0;}
.pregunta {color: #6b6b6b; margin-bottom: .6rem;}
.estado-juicio {display: inline-block; padding: .15rem .6rem; border-radius: 999px;
                font-size: .85rem; border: 1px solid rgba(128,128,128,.45);}
.estado-1 {background: #d9f2df; color: #1b5e20;}
.estado-0 {background: #f6dada; color: #8e1c1c;}
.estado-omitido {background: #eeeeee; color: #555;}
</style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
