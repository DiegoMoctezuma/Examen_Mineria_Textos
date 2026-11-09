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


def _cargar_foto(forzar: bool = False) -> None:
    """Foto de la revisión al abrir la sesión (o al recargar). El editor se monta siempre sobre
    esta foto y con la misma clave: así no se reinicia tras cada guardado y no se pierde la
    posición. Lo editado vive en el estado del editor y se guarda encima de la foto."""
    ss = st.session_state
    if forzar or "gaz_foto" not in ss:
        ss.gaz_foto, ss.gaz_token = C.cargar_revision_siglas()
        ss.gaz_epoca = ss.get("gaz_epoca", 0) + 1


def _guardar(clave: str, posiciones: list[int]) -> None:
    """Callback del editor: aplica todas las celdas editadas sobre la foto y guarda en el acto.
    `posiciones` traduce la fila mostrada (quizá filtrada) a la fila de la foto."""
    ss = st.session_state
    df = ss.gaz_foto.copy()
    for i, fila in ss[clave].get("edited_rows", {}).items():
        for col, valor in fila.items():
            if col == "decision":
                valor = next((k for k, v in ETIQUETA_DECISION.items() if v == valor), valor)
            df.at[posiciones[int(i)], col] = "" if valor is None else str(valor).strip()
    try:
        ss.gaz_token = C.guardar_revision_siglas(df, ss.gaz_token)
        ss.toast_gaz = "Guardado"
    except C.ConflictoEdicion as e:
        ss.msg_gaz = f"{e} No se guardó nada. Usa «Recargar desde disco»."
    except (ValueError, OSError) as e:
        ss.msg_gaz = f"No se pudo guardar: {e}"


def _cambiar_filtro() -> None:
    _cargar_foto(forzar=True)  # al cambiar el filtro se parte de lo guardado


def mostrar() -> None:
    st.header("Gazetteer: revisión de siglas")
    r = C.rutas()
    if not r.siglas_candidatas.exists():
        st.warning("Faltan las candidatas: corre `make reglas`.")
        return
    ss = st.session_state
    _cargar_foto()
    congeladas = C.reglas_congeladas()
    res = C.resumen_revision(C.cargar_revision_siglas(r)[0])  # lo guardado en disco

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
    if st.sidebar.button("Recargar desde disco", width="stretch"):
        _cargar_foto(forzar=True)

    st.markdown(
        "Siglas en mayúsculas que aparecen en el cuerpo de los discursos y que el gazetteer "
        "aún no reconoce. Para cada una decide **ORG** (dependencia, empresa, partido, "
        "organismo), **LOC** (lugar u obra) o **Descartar** (no es organización ni lugar, "
        "p. ej. una enfermedad o un impuesto). Si conoces el nombre completo, escríbelo en "
        "*nombre completo*; si lo dejas vacío, se usa la sigla. Cada cambio se guarda solo, "
        "sin mover la tabla.")
    if congeladas:
        st.info("Las reglas están congeladas (`reglas-congeladas`): la revisión es de solo "
                "lectura. Un cambio ahora sería exploratorio (D15).")
    if "msg_gaz" in ss:
        st.error(ss.pop("msg_gaz"))
    if "toast_gaz" in ss:
        st.toast(ss.pop("toast_gaz"), icon="✅")

    solo_pend = st.toggle("Mostrar solo pendientes", key="gaz_solo_pend",
                          on_change=_cambiar_filtro,
                          help="Filtra según lo guardado al activarlo; las filas que decidas "
                               "después no desaparecen hasta que recargues.")
    foto = ss.gaz_foto
    vista = foto.copy()
    vista["decision"] = vista["decision"].map(ETIQUETA_DECISION).fillna(vista["decision"])
    vista["frecuencia"] = pd.to_numeric(vista["frecuencia"], errors="coerce").astype("Int64")
    if solo_pend:
        vista = vista[foto["decision"] == ""]
    posiciones = vista.index.tolist()
    clave = f"ed_siglas_{ss.gaz_epoca}"
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
        on_change=_guardar, args=(clave, posiciones),
    )
