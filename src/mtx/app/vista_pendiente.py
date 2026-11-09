"""Pestañas que se construyen en hitos posteriores (PRD §12.2)."""
from __future__ import annotations

import streamlit as st


def gold() -> None:
    st.header("Gold")
    st.info("Se construye en H5 y H6 (skill `gold-anotacion`): muestra sorteada, búsqueda por "
            "texto con desambiguación y modo ciego hasta `anotaciones/cierre_gold.json`.")


def demo() -> None:
    st.header("Demo")
    st.info("P2. Mientras tanto, la demo oficial es `make demo Q=Q3` en la terminal.")
