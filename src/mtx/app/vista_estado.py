"""Pestaña Estado (PRD §7): cinco estados por artefacto, nunca "completado" solo por existir."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from mtx import config, corpus
from mtx.app import componentes as C

ICONOS = {C.VALIDO: "🟢", C.PENDIENTE_HUMANO: "🟡", C.PENDIENTE_TECNICO: "⚪",
          C.OBSOLETO: "🟠", C.ERROR: "🔴"}


@st.cache_data(show_spinner="Calculando la huella de los pasajes…")
def _hash_pasajes(mtime: float) -> str:
    return corpus.hash_pasajes(pd.read_parquet(config.PASAJES_PARQUET))


@st.cache_data(show_spinner=False)
def _textos(mtime: float) -> pd.DataFrame:
    return pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto"])


def mostrar() -> None:
    st.header("Estado del proyecto")
    st.caption("Un artefacto es **válido** solo si su validador pasa y sus hashes siguen "
               "vigentes. 🟢 válido · 🟡 pendiente humano · ⚪ pendiente técnico · "
               "🟠 obsoleto · 🔴 error")
    r = C.rutas()
    if r.pasajes.exists():
        mtime = r.pasajes.stat().st_mtime
        estados = C.estados_artefactos(r, _hash_pasajes(mtime), _textos(mtime))
    else:
        estados = C.estados_artefactos(r)
    tabla = pd.DataFrame(estados)
    tabla.insert(0, " ", tabla["estado"].map(ICONOS))
    st.dataframe(tabla, hide_index=True, width="stretch",
                 column_config={"artefacto": st.column_config.TextColumn(width="medium"),
                                "detalle": st.column_config.TextColumn(width="large")})
    if st.button("Actualizar"):
        st.rerun()
