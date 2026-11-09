"""Pestaña Gazetteer (PRD §6.7.4, `[VALIDAR]`): el alumno revisa las siglas candidatas.

Por candidata: ORG, LOC o descartar, y el nombre completo si lo conoce. Cada edición se guarda al
momento (escritura atómica) en `anotaciones/revision_siglas.csv` y reconstruye
`config/gazetteer_extendido.csv`. Ninguna decisión viene preseleccionada. Tras la etiqueta
`reglas-congeladas` la tabla queda de solo lectura.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from mtx import reglas
from mtx.app import componentes as C

ETIQUETA_DECISION = {"": "— pendiente —", "ORG": "ORG", "LOC": "LOC", "descartar": "Descartar"}


def _guardar(base: pd.DataFrame, token: str, clave: str, posiciones: list[int]) -> None:
    """Callback del editor: aplica las celdas editadas y guarda en el acto. `posiciones` traduce
    la fila mostrada (posición en la vista, quizá filtrada) a la fila de `base`."""
    ss = st.session_state
    cambios = ss[clave].get("edited_rows", {})
    df = base.copy()
    for i, fila in cambios.items():
        for col, valor in fila.items():
            if col == "decision":
                valor = next((k for k, v in ETIQUETA_DECISION.items() if v == valor), valor)
            df.at[posiciones[int(i)], col] = "" if valor is None else str(valor).strip()
    try:
        C.guardar_revision_siglas(df, token)
        ss.msg_gaz = ("exito", "Guardado.")
    except C.ConflictoEdicion as e:
        ss.msg_gaz = ("error", f"{e} No se guardó nada.")
    except (ValueError, OSError) as e:
        ss.msg_gaz = ("error", f"No se pudo guardar: {e}")
    ss.version_gaz = ss.get("version_gaz", 0) + 1  # reinicia el editor con lo guardado


def mostrar() -> None:
    st.header("Gazetteer: revisión de siglas")
    r = C.rutas()
    if not r.siglas_candidatas.exists():
        st.warning("Faltan las candidatas: corre `make reglas`.")
        return
    congeladas = C.reglas_congeladas()
    df, token = C.cargar_revision_siglas(r)
    res = C.resumen_revision(df)

    st.sidebar.subheader("Revisión de siglas")
    hechas = res["candidatas"] - res["pendientes"]
    st.sidebar.progress(hechas / max(res["candidatas"], 1),
                        text=f"{hechas} de {res['candidatas']} revisadas")
    base = reglas.leer_gazetteer(reglas.KIT_GAZETTEER)
    manual = reglas.leer_gazetteer(reglas.GAZ_MANUAL)
    nuevas_manual = int((~manual["nombre"].isin(base["nombre"])).sum())
    st.sidebar.markdown(
        f"- Base del kit: **{len(base)}**\n- Manuales (PRD y D14): **{nuevas_manual}**\n"
        f"- Aceptadas: **{res['ORG']} ORG**, **{res['LOC']} LOC**\n"
        f"- Descartadas: **{res['descartadas']}**")

    st.markdown(
        "Siglas en mayúsculas que aparecen en el cuerpo de los discursos y que el gazetteer "
        "aún no reconoce. Para cada una decide **ORG** (dependencia, empresa, partido, "
        "organismo), **LOC** (lugar u obra) o **Descartar** (no es organización ni lugar, "
        "p. ej. una enfermedad o un impuesto). Si conoces el nombre completo, escríbelo en "
        "*nombre_final*; si lo dejas vacío, se usa la sigla. Cada cambio se guarda solo.")
    if congeladas:
        st.info("Las reglas están congeladas (`reglas-congeladas`): la revisión es de solo "
                "lectura. Un cambio ahora sería exploratorio (D15).")
    msg = st.session_state.pop("msg_gaz", None)
    if msg:
        {"error": st.error, "exito": st.success}[msg[0]](msg[1])

    solo_pend = st.toggle("Mostrar solo pendientes", value=False)
    vista = df.copy()
    vista["decision"] = vista["decision"].map(ETIQUETA_DECISION).fillna(vista["decision"])
    vista["frecuencia"] = pd.to_numeric(vista["frecuencia"], errors="coerce").astype("Int64")
    if solo_pend:
        vista = vista[df["decision"] == ""]
    posiciones = vista.index.tolist()
    clave = f"ed_siglas_{st.session_state.get('version_gaz', 0)}_{int(solo_pend)}"
    st.data_editor(
        vista, key=clave, hide_index=True, width="stretch", height=640,
        disabled=congeladas or ["sigla", "nombre_propuesto", "frecuencia", "ejemplo"],
        column_order=["sigla", "decision", "nombre_final", "frecuencia", "nombre_propuesto",
                      "ejemplo"],
        column_config={
            "sigla": st.column_config.TextColumn("Sigla", width="small"),
            "decision": st.column_config.SelectboxColumn(
                "Decisión", options=list(ETIQUETA_DECISION.values()), required=True,
                width="medium"),
            "nombre_final": st.column_config.TextColumn("Nombre completo (opcional)",
                                                        width="medium"),
            "frecuencia": st.column_config.NumberColumn("Frecuencia", width="small"),
            "nombre_propuesto": st.column_config.TextColumn("Nombre hallado en el texto",
                                                            width="medium"),
            "ejemplo": st.column_config.TextColumn("Ejemplo de uso", width="large"),
        },
        on_change=_guardar, args=(df, token, clave, posiciones),
    )
