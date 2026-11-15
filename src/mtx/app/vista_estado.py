"""Pestaña Estado (PRD §7): cinco estados por artefacto, nunca "completado" solo por existir."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from mtx import anotadores, config, corpus
from mtx.app import componentes as C

ICONOS = {C.VALIDO: "🟢", C.PENDIENTE_HUMANO: "🟡", C.PENDIENTE_TECNICO: "⚪",
          C.OBSOLETO: "🟠", C.ERROR: "🔴"}


@st.cache_data(show_spinner="Calculando la huella de los pasajes…")
def _hash_pasajes(mtime: float) -> str:
    return corpus.hash_pasajes(pd.read_parquet(config.PASAJES_PARQUET))


@st.cache_data(show_spinner=False)
def _textos(mtime: float) -> pd.DataFrame:
    return pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto", "texto_sha256"])


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
    _avance_v2()
    if st.button("Actualizar"):
        st.rerun()


def _avance_v2() -> None:
    """Avance de los juicios v2 (D24): el propio para quien juzga y, solo para el coordinador, el
    de todos. Únicamente conteos: nunca qué valor puso cada quien."""
    st.subheader("Juicios v2")
    try:
        lista = anotadores.cargar_anotadores()
    except FileNotFoundError:
        st.caption("Sin lista de anotadores v2.")
        return
    asig = anotadores.leer_asignacion()
    if asig.empty:
        st.caption("Aún no hay asignación: `make asignar-juicios LOTE=1`.")
        return
    tabla = anotadores.avance(asig, C.rutas().anotaciones, lista)
    yo = st.session_state.get("anotador")
    if yo not in lista:
        st.caption("Elige tu nombre en la pestaña Juicios para ver tu avance.")
        return
    if not lista[yo].coordinador:
        tabla = tabla[tabla["anotador"] == yo]
    st.dataframe(tabla.drop(columns="anotador"), hide_index=True, width="stretch")
