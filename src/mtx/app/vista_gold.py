"""Pestaña Gold (PRD §6.11, D10, D19): anotación del gold de evaluación en modo ciego.

Modo principal: búsqueda por texto exacto con desambiguación de apariciones. Modo secundario:
primer y último token. Tabla editable (tipo, límites, borrar), "Pasaje revisado completo" (válido
con cero entidades) y "Cerrar gold" cuando `validar_gold()` pasa. Esta vista nunca lee
predicciones del sistema; la tabla de cada pasaje empieza vacía.
"""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from mtx import config
from mtx import gold as G
from mtx.app import componentes as C

COLORES = {"PER": "#ffc9a3", "ORG": "#a9d4ff", "LOC": "#b5ecb0", "FECHA": "#e2c4fb",
           "MONTO": "#ffe58a"}


@st.cache_data(show_spinner="Cargando pasajes…")
def _pasajes(ids: tuple[str, ...], mtime: float) -> pd.DataFrame:
    p = pd.read_parquet(config.PASAJES_PARQUET,
                        columns=["passage_id", "texto", "inicio_cuerpo", "texto_sha256",
                                 "titulo", "fecha", "interlocutor"])
    return p[p["passage_id"].isin(set(ids))].set_index("passage_id")


def _msg(tipo: str, texto: str) -> None:
    st.session_state.msg_gold = (tipo, texto)


def _accion(fn, *args) -> None:
    """Ejecuta una escritura y deja el resultado como mensaje; nunca escribe en silencio."""
    try:
        fn(*args)
        _msg("exito", "Guardado.")
    except C.ConflictoEdicion as e:
        _msg("error", f"{e} No se guardó nada.")
    except (ValueError, OSError) as e:
        _msg("error", f"No se guardó: {e}")


def _agregar_busqueda(r, tok, pid, texto, sha) -> None:
    ss = st.session_state
    apar = G.buscar_apariciones(texto, ss.get("buscar_texto", ""))
    k = ss.get("aparicion")
    if k is None or k >= len(apar):
        _msg("error", "Elige cuál aparición agregar.")
        return
    _accion(G.agregar, r, tok, pid, texto, sha, ss["tipo_busqueda"], apar[k]["inicio"],
            apar[k]["fin"])


def _agregar_tokens(r, tok, pid, texto, sha) -> None:
    ss = st.session_state
    toks = G.tokens(texto)
    a, b = ss["tok_ini"], ss["tok_fin"]
    if b < a:
        _msg("error", "El último token va antes del primero.")
        return
    ini, fin = toks[a][0], toks[b][1]
    if ss.get("recortar", True):
        ini, fin = G.recortar_puntuacion(texto, ini, fin)
    _accion(G.agregar, r, tok, pid, texto, sha, ss["tipo_tokens"], ini, fin)


def _editar_tabla(r, tok, pid, texto, sha, base: pd.DataFrame, clave: str) -> None:
    cambios = st.session_state[clave]
    filas = base.to_dict("records")
    for i, c in cambios.get("edited_rows", {}).items():
        filas[int(i)].update(c)
    filas = [f for f in filas if not f.get("borrar")]
    _accion(G.reemplazar_pasaje, r, tok, pid, texto, sha, filas)
    st.session_state.version_tabla = st.session_state.get("version_tabla", 0) + 1


def mostrar() -> None:
    st.header("Gold de evaluación")
    r = G.rutas_gold()
    if not C.reglas_congeladas():
        st.warning("El gold se abre después de congelar reglas, gazetteers y criterio "
                   "(`make congelar`, D15). Antes termina la revisión de siglas.")
        return
    if not r.muestra.exists():
        st.info("Falta la muestra: corre `make muestra-gold`.")
        return
    man = pd.read_csv(r.muestra, dtype={"passage_id": str, "texto_sha256": str})
    pas = _pasajes(tuple(man["passage_id"]), config.PASAJES_PARQUET.stat().st_mtime)
    gold, estado, tok = G.cargar(r)
    cerrado_gold = r.cierre.exists()

    # ---- barra lateral: selector estable, progreso, contadores y convenciones
    st.sidebar.subheader("Pasaje")
    ids = list(man["passage_id"])
    consulta = dict(zip(man["passage_id"], man["query_id"]))
    pid = st.sidebar.selectbox("Pasaje", ids, key="pasaje_gold",
                               format_func=lambda p: f"{consulta[p]} · {p}",
                               label_visibility="collapsed")
    cerrados = sum(G.estado_de(estado, p) == G.CERRADO for p in ids)
    st.sidebar.progress(cerrados / len(ids), text=f"Revisados completos: {cerrados} de {len(ids)}")
    st.sidebar.markdown(" ".join(
        f'<span class="chip-q{" completa" if G.estado_de(estado, p) == G.CERRADO else ""}">'
        f'{consulta[p]} {p}</span>' for p in ids), unsafe_allow_html=True)
    cuenta = gold["tipo"].value_counts()
    st.sidebar.markdown(" · ".join(f"{t} {int(cuenta.get(t, 0))}" for t in G.TIPOS))
    with st.sidebar.expander("Convenciones (criterio de anotación)"):
        ruta_crit = config.DIR_CONFIG / "criterios_anotacion.md"
        if ruta_crit.exists():
            st.markdown(ruta_crit.read_text(encoding="utf-8"))

    msg = st.session_state.pop("msg_gold", None)
    if msg:
        {"error": st.error, "exito": st.success, "info": st.info}[msg[0]](msg[1])
    if cerrado_gold:
        st.info("El gold está cerrado (`cierre_gold.json`): solo lectura. Un cambio exige "
                "revisión explícita y nueva versión (skill gold-anotacion).")

    # ---- pasaje
    p = pas.loc[pid]
    texto, ic, sha = p["texto"], int(p["inicio_cuerpo"]), p["texto_sha256"]
    if sha != man.set_index("passage_id").at[pid, "texto_sha256"]:
        st.error("El texto de este pasaje cambió desde el sorteo: no se puede anotar.")
        return
    gp = gold[gold["passage_id"] == pid].reset_index(drop=True)
    est = G.estado_de(estado, pid)
    st.markdown(f"**{consulta[pid]} · {pid}** · {len(gp)} entidades · estado **{est}** · "
                f"{html.escape(str(p['titulo']))}")
    st.markdown('<div class="leyenda">' + "".join(
        f'<span style="background:{c}">{t}</span>' for t, c in COLORES.items())
        + '<span style="background:transparent;color:inherit;opacity:.6">marca de '
        "interlocutor (también se anota)</span></div>", unsafe_allow_html=True)
    try:
        cuerpo = C.html_desde_spans(texto, G.spans_para_mostrar(gp, ic))
    except ValueError as e:
        st.error(f"Error de resaltado: {e}")
        cuerpo = C.html_desde_spans(texto, [])
    st.markdown(f'<div class="pasaje">{cuerpo}</div>', unsafe_allow_html=True)
    off = cerrado_gold

    # ---- agregar
    modo_b, modo_t = st.tabs(["Buscar texto (principal)", "Por tokens (casos difíciles)"])
    with modo_b:
        c1, c2 = st.columns([3, 1])
        c1.text_input("Texto exacto de la entidad", key="buscar_texto", disabled=off)
        c2.selectbox("Tipo", G.TIPOS, key="tipo_busqueda", index=None,
                     placeholder="Elige", disabled=off)
        apar = G.buscar_apariciones(texto, st.session_state.get("buscar_texto", ""))
        if st.session_state.get("buscar_texto") and not apar:
            st.warning("No aparece tal cual en el pasaje (revisa mayúsculas, acentos y "
                       "espacios).")
        if apar:
            st.radio("Aparición", list(range(len(apar))), key="aparicion", index=None,
                     format_func=lambda k: f"…{apar[k]['antes']}[{texto[apar[k]['inicio']:apar[k]['fin']]}]"
                                           f"{apar[k]['despues']}… ({apar[k]['inicio']}-{apar[k]['fin']})",
                     disabled=off)
        st.button("Agregar", key="agregar_b", type="primary",
                  disabled=off or not apar or st.session_state.get("tipo_busqueda") is None,
                  on_click=_agregar_busqueda, args=(r, tok, pid, texto, sha))
    with modo_t:
        toks = G.tokens(texto)
        etiqueta = [f"{i}: {t}" for i, (_, _, t) in enumerate(toks)]
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.selectbox("Primer token", range(len(toks)), key="tok_ini",
                     format_func=etiqueta.__getitem__, disabled=off)
        c2.selectbox("Último token", range(len(toks)), key="tok_fin",
                     format_func=etiqueta.__getitem__, disabled=off)
        c3.selectbox("Tipo", G.TIPOS, key="tipo_tokens", index=None, placeholder="Elige",
                     disabled=off)
        st.checkbox("Recortar puntuación (nunca quita $)", value=True, key="recortar")
        st.button("Agregar", key="agregar_t", type="primary",
                  disabled=off or st.session_state.get("tipo_tokens") is None,
                  on_click=_agregar_tokens, args=(r, tok, pid, texto, sha))

    # ---- tabla editable
    st.subheader("Entidades de este pasaje")
    if gp.empty:
        st.caption("Sin entidades. Si el pasaje no tiene ninguna, ciérralo igual: es válido.")
    else:
        base = gp[["tipo", "texto", "inicio", "fin"]].assign(borrar=False)
        clave = f"tabla_{pid}_{st.session_state.get('version_tabla', 0)}"
        st.data_editor(
            base, key=clave, hide_index=True, width="stretch", disabled=off or ["texto"],
            column_config={
                "tipo": st.column_config.SelectboxColumn("Tipo", options=list(G.TIPOS),
                                                         required=True),
                "inicio": st.column_config.NumberColumn("Inicio", step=1, min_value=0),
                "fin": st.column_config.NumberColumn("Fin", step=1, min_value=1),
                "borrar": st.column_config.CheckboxColumn("Borrar"),
            },
            on_change=_editar_tabla, args=(r, tok, pid, texto, sha, base, clave))

    c1, c2, _ = st.columns([1.4, 1, 2])
    if est == G.CERRADO:
        c1.button("Reabrir pasaje", disabled=off,
                  on_click=_accion, args=(G.marcar, r, tok, pid, sha, False))
    else:
        c1.button("Pasaje revisado completo", type="primary", disabled=off,
                  on_click=_accion, args=(G.marcar, r, tok, pid, sha, True))

    # ---- cierre del gold
    st.divider()
    if not cerrado_gold:
        v = G.validar_gold(r, pas.reset_index())
        if v.ok:
            st.success("Todo listo: el gold pasa la validación.")
            if st.button("Cerrar gold", type="primary"):
                try:
                    G.cerrar_gold(r, pas.reset_index())
                    _msg("exito", "Gold cerrado: cierre_gold.json escrito y gold_entidades.csv "
                         "exportado a la raíz.")
                except ValueError as e:
                    _msg("error", str(e))
                st.rerun()
        else:
            with st.expander(f"Pendiente para cerrar el gold ({len(v.errores)})"):
                for e in v.errores:
                    st.write(f"- {e}")
        for a in v.avisos:
            st.caption(a)
