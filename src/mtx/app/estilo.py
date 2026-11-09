"""Estilo sobrio y común para todas las páginas.

Los resaltados fijan color de fondo y de texto a la vez: con `color: inherit`, el tema oscuro de
Streamlit ponía texto claro sobre fondo amarillo claro y no se leía. Contraste del término
(#1a1a1a sobre #ffd666) ≈ 13:1, válido en tema claro y oscuro.
"""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
.pasaje {font-size: 1.08rem; line-height: 1.75; padding: 1.1rem 1.3rem; border-radius: 10px;
         border: 1px solid rgba(128,128,128,.35); background: rgba(128,128,128,.06);
         max-width: 62rem; white-space: pre-wrap;}
.pasaje mark.termino {background: #ffd666; color: #1a1a1a; font-weight: 600;
                      padding: .05em .2em; border-radius: 3px;
                      box-decoration-break: clone; -webkit-box-decoration-break: clone;}
.pasaje mark.marca {background: transparent; color: inherit; opacity: .6;
                    font-variant: small-caps;}
.consulta {font-size: 1.6rem; font-weight: 600; margin: 0 0 .2rem 0;}
.pregunta {color: inherit; opacity: .75; margin-bottom: .6rem;}
.estado-juicio {display: inline-block; padding: .15rem .6rem; border-radius: 999px;
                font-size: .85rem; border: 1px solid rgba(128,128,128,.45);}
.estado-1 {background: #d9f2df; color: #1b5e20;}
.estado-0 {background: #f6dada; color: #8e1c1c;}
.estado-omitido {background: #eeeeee; color: #333;}
.pasaje mark.gold {color: #1a1a1a; font-weight: 600; padding: .05em .2em; border-radius: 3px;
                   box-decoration-break: clone; -webkit-box-decoration-break: clone;}
.pasaje mark.PER {background: #ffc9a3;} .pasaje mark.ORG {background: #a9d4ff;}
.pasaje mark.LOC {background: #b5ecb0;} .pasaje mark.FECHA {background: #e2c4fb;}
.pasaje mark.MONTO {background: #ffe58a;}
.leyenda span {display: inline-block; margin-right: .5rem; padding: 0 .4rem; border-radius: 3px;
               color: #1a1a1a; font-size: .85rem; font-weight: 600;}
.chip-q {display: inline-block; margin: 0 .25rem .3rem 0; padding: .05rem .45rem;
         border-radius: 999px; font-size: .8rem; border: 1px solid rgba(128,128,128,.45);}
.chip-q.completa {background: #d9f2df; color: #1b5e20; border-color: #9fd3ab;}
</style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
