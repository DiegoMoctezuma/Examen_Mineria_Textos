"""Pestaña Gold v2 (PRD v2 D31 a D33, WP-09): doble anotación ciega por pasadas.

Pide quién anota y muestra solo las partes que le tocan (`config/v2/anotadores.yaml`). La pasada
1 ofrece PER, ORG, LOC y MONTO; la 2, solo FECHA, y se abre con `reglas-fecha-v2`. Solo lee y
escribe `anotaciones/gold_v2/<anotador>.csv`: nunca la anotación de la otra persona ni
predicciones del sistema; la tabla de cada pasaje empieza vacía. Mismo modo de captura que v1:
búsqueda por texto exacto con desambiguación, o primer y último token.
"""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from mtx import config
from mtx import gold as G
from mtx import gold_v2 as V
from mtx.app import componentes as C
from mtx.app import sesion
from mtx.app.vista_gold import COLORES

NOMBRE_PASADA = {1: "Pasada 1 · PER, ORG, LOC y MONTO", 2: "Pasada 2 · solo FECHA"}


@st.cache_data(show_spinner="Cargando pasajes…")
def pasajes(ids: tuple[str, ...], mtime: float) -> pd.DataFrame:
    p = pd.read_parquet(config.PASAJES_PARQUET,
                        columns=["passage_id", "texto", "inicio_cuerpo", "texto_sha256",
                                 "titulo", "fecha"])
    return p[p["passage_id"].isin(set(ids))].set_index("passage_id")


def _msg(tipo: str, texto: str) -> None:
    st.session_state.g2_msg = (tipo, texto)


def _accion(fn, *args) -> None:
    try:
        fn(*args)
        _msg("exito", "Guardado.")
    except C.ConflictoEdicion as e:
        _msg("error", f"{e} No se guardó nada.")
    except (ValueError, OSError) as e:
        _msg("error", f"No se guardó: {e}")


def mostrar_mensaje() -> None:
    msg = st.session_state.pop("g2_msg", None)
    if msg:
        {"error": st.error, "exito": st.success, "info": st.info}[msg[0]](msg[1])


def leyenda() -> None:
    st.markdown('<div class="leyenda">' + "".join(
        f'<span style="background:{c}">{t}</span>' for t, c in COLORES.items())
        + '<span style="background:transparent;color:inherit;opacity:.6">marca de '
        "interlocutor (también se anota)</span></div>", unsafe_allow_html=True)


def pasaje_html(texto: str, inicio_cuerpo: int, filas: pd.DataFrame) -> str:
    try:
        return C.html_desde_spans(texto, G.spans_para_mostrar(filas, inicio_cuerpo))
    except ValueError as e:
        st.error(f"Error de resaltado: {e}")
        return C.html_desde_spans(texto, [])


def _agregar_busqueda(s, tok, pid, pasada, texto, sha) -> None:
    ss = st.session_state
    apar = G.buscar_apariciones(texto, ss.get("g2_buscar", ""))
    k = ss.get("g2_aparicion")
    if k is None or k >= len(apar):
        _msg("error", "Elige cuál aparición agregar.")
        return
    _accion(s.agregar, tok, pid, pasada, texto, sha, ss["g2_tipo_b"], apar[k]["inicio"],
            apar[k]["fin"])


def _agregar_tokens(s, tok, pid, pasada, texto, sha) -> None:
    ss = st.session_state
    toks = G.tokens(texto)
    a, b = ss["g2_tok_ini"], ss["g2_tok_fin"]
    if b < a:
        _msg("error", "El último token va antes del primero.")
        return
    ini, fin = toks[a][0], toks[b][1]
    if ss.get("g2_recortar", True):
        ini, fin = G.recortar_puntuacion(texto, ini, fin)
    _accion(s.agregar, tok, pid, pasada, texto, sha, ss["g2_tipo_t"], ini, fin)


def _editar_tabla(s, tok, pid, pasada, texto, sha, base: pd.DataFrame, clave: str) -> None:
    cambios = st.session_state[clave]
    filas = base.to_dict("records")
    for i, c in cambios.get("edited_rows", {}).items():
        filas[int(i)].update(c)
    filas = [f for f in filas if not f.get("borrar")]
    _accion(s.reemplazar, tok, pid, pasada, texto, sha, filas)
    st.session_state.g2_version_tabla = st.session_state.get("g2_version_tabla", 0) + 1


def mostrar() -> None:
    st.header("Gold v2")
    yo = sesion.anotador(
        "¿Quién va a anotar?", "Anotas como",
        "Cada quien anota solo sus pasajes y en su propio archivo. No verás la anotación de la "
        "otra persona ni lo que predice el sistema.")
    if yo is None:
        return
    try:
        cfg = V.cargar_config()
    except (ValueError, KeyError) as e:
        st.error(f"Configuración del gold v2 inválida: {e}")
        return
    mias = V.partes_de_anotador(cfg, yo)
    if not mias:
        st.info("No tienes pasajes gold asignados (PRD v2 D31).")
        return

    # ---- barra lateral: parte, pasada, pasaje y progreso
    st.sidebar.subheader("Parte")
    nombres = {p.id: p.nombre for p in mias}
    pid_parte = st.sidebar.selectbox("Parte", list(nombres), key="g2_parte",
                                     format_func=nombres.get, label_visibility="collapsed")
    parte = cfg.partes[pid_parte]
    abiertas = [x for x in parte.pasadas if V.pasada_abierta(cfg, x)]
    if 2 in parte.pasadas and 2 not in abiertas:
        st.sidebar.caption("La pasada 2 (FECHA) se abre con la etiqueta `reglas-fecha-v2` "
                           "(D33).")
    if not abiertas:
        st.info(f"{parte.nombre}: todavía no hay pasada abierta para ti.")
        return
    pasada = st.sidebar.radio("Pasada", abiertas, key=f"g2_pasada_{pid_parte}",
                              format_func=NOMBRE_PASADA.get)
    man = V.manifiesto(parte)
    if man is None:
        st.info(f"Falta la muestra de {parte.nombre}: `make muestra-gold-v2`.")
        return
    s = V.SesionAnotador(V.dir_anotaciones(), yo, cfg)
    gold, estado, tok = s.cargar()
    ids = list(man["passage_id"])
    consulta = dict(zip(man["passage_id"], man["query_id"]))
    pid = st.sidebar.selectbox("Pasaje", ids, key=f"g2_pasaje_{pid_parte}",
                               format_func=lambda p: f"{consulta[p]} · {p}")
    cerrados = sum(V.estado_de(estado, p, pasada) == V.CERRADO for p in ids)
    st.sidebar.progress(cerrados / len(ids),
                        text=f"Revisados completos: {cerrados} de {len(ids)}")
    st.sidebar.markdown(" ".join(
        f'<span class="chip-q{" completa" if V.estado_de(estado, p, pasada) == V.CERRADO else ""}'
        f'">{consulta[p]} {p}</span>' for p in ids), unsafe_allow_html=True)
    with st.sidebar.expander("Convenciones (criterio de anotación)"):
        ruta_crit = config.DIR_CONFIG / "criterios_anotacion.md"
        if ruta_crit.exists():
            st.markdown(ruta_crit.read_text(encoding="utf-8"))
    mostrar_mensaje()

    # ---- pasaje
    pas = pasajes(tuple(ids), config.PASAJES_PARQUET.stat().st_mtime)
    p = pas.loc[pid]
    texto, ic, sha = p["texto"], int(p["inicio_cuerpo"]), p["texto_sha256"]
    if sha != man.set_index("passage_id").at[pid, "texto_sha256"]:
        st.error("El texto de este pasaje cambió desde el sorteo: no se puede anotar.")
        return
    propias = gold[gold["passage_id"] == pid]
    actual = propias[propias["pasada"] == pasada].reset_index(drop=True)
    ctx = pd.concat([propias[propias["pasada"] != pasada][["passage_id", "tipo", "texto",
                                                           "inicio", "fin"]],
                     V.contexto_v1(V.dir_anotaciones(), parte, pid)], ignore_index=True)
    est = V.estado_de(estado, pid, pasada)
    bloqueado = V.adjudicacion_iniciada(V.dir_anotaciones(), parte, pid, pasada)
    st.markdown(f"**{consulta[pid]} · {pid}** · {NOMBRE_PASADA[pasada]} · {len(actual)} "
                f"entidades · estado **{est}** · {html.escape(str(p['titulo']))}")
    leyenda()
    st.markdown(f'<div class="pasaje">{pasaje_html(texto, ic, pd.concat([actual, ctx]))}</div>',
                unsafe_allow_html=True)
    if len(ctx):
        st.caption(f"También se resaltan {len(ctx)} entidades de otra pasada (solo lectura).")
    if bloqueado:
        st.info("Este pasaje ya está en adjudicación: solo lectura.")
    off = bloqueado
    tipos = list(V.TIPOS_PASADA[pasada])

    # ---- agregar
    modo_b, modo_t = st.tabs(["Buscar texto (principal)", "Por tokens (casos difíciles)"])
    with modo_b:
        c1, c2 = st.columns([3, 1])
        c1.text_input("Texto exacto de la entidad", key="g2_buscar", disabled=off)
        c2.selectbox("Tipo", tipos, key="g2_tipo_b", index=None, placeholder="Elige",
                     disabled=off)
        apar = G.buscar_apariciones(texto, st.session_state.get("g2_buscar", ""))
        if st.session_state.get("g2_buscar") and not apar:
            st.warning("No aparece tal cual en el pasaje (revisa mayúsculas, acentos y "
                       "espacios).")
        if apar:
            hechas = {(int(f["inicio"]), int(f["fin"])): f["tipo"]
                      for f in actual.to_dict("records")}

            def _etiqueta(k: int) -> str:
                a = apar[k]
                ya = hechas.get((a["inicio"], a["fin"]))
                return (f"{'✓ ya agregada como ' + ya + ' · ' if ya else ''}"
                        f"…{a['antes']}[{texto[a['inicio']:a['fin']]}]{a['despues']}… "
                        f"({a['inicio']}-{a['fin']})")

            st.caption(f"{len(apar)} apariciones. Cada aparición es una entidad: agrégalas una "
                       "por una.")
            st.radio("Aparición", list(range(len(apar))), key="g2_aparicion", index=None,
                     format_func=_etiqueta, disabled=off)
        st.button("Agregar", key="g2_agregar_b", type="primary",
                  disabled=off or not apar or st.session_state.get("g2_tipo_b") is None,
                  on_click=_agregar_busqueda, args=(s, tok, pid, pasada, texto, sha))
    with modo_t:
        toks = G.tokens(texto)
        etiqueta = [f"{i}: {t}" for i, (_, _, t) in enumerate(toks)]
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.selectbox("Primer token", range(len(toks)), key="g2_tok_ini",
                     format_func=etiqueta.__getitem__, disabled=off)
        c2.selectbox("Último token", range(len(toks)), key="g2_tok_fin",
                     format_func=etiqueta.__getitem__, disabled=off)
        c3.selectbox("Tipo", tipos, key="g2_tipo_t", index=None, placeholder="Elige",
                     disabled=off)
        st.checkbox("Recortar puntuación (nunca quita $)", value=True, key="g2_recortar")
        st.button("Agregar", key="g2_agregar_t", type="primary",
                  disabled=off or st.session_state.get("g2_tipo_t") is None,
                  on_click=_agregar_tokens, args=(s, tok, pid, pasada, texto, sha))

    # ---- tabla editable de esta pasada
    st.subheader("Tus entidades en esta pasada")
    if actual.empty:
        st.caption("Sin entidades. Si el pasaje no tiene ninguna, ciérralo igual: es válido.")
    else:
        base = actual[["tipo", "texto", "inicio", "fin"]].assign(borrar=False)
        clave = f"g2_tabla_{pid}_{pasada}_{st.session_state.get('g2_version_tabla', 0)}"
        st.data_editor(
            base, key=clave, hide_index=True, width="stretch", disabled=off or ["texto"],
            column_config={
                "tipo": st.column_config.SelectboxColumn("Tipo", options=tipos, required=True),
                "inicio": st.column_config.NumberColumn("Inicio", step=1, min_value=0),
                "fin": st.column_config.NumberColumn("Fin", step=1, min_value=1),
                "borrar": st.column_config.CheckboxColumn("Borrar"),
            },
            on_change=_editar_tabla, args=(s, tok, pid, pasada, texto, sha, base, clave))

    c1, _ = st.columns([1.4, 3])
    if est == V.CERRADO:
        c1.button("Reabrir pasaje", key="g2_reabrir", disabled=off,
                  on_click=_accion, args=(s.marcar, tok, pid, pasada, sha, False))
    else:
        c1.button("Pasaje revisado completo", key="g2_cerrar", type="primary", disabled=off,
                  on_click=_accion, args=(s.marcar, tok, pid, pasada, sha, True))
