"""Pestaña Adjudicación (PRD v2 D31, WP-09): un tercero resuelve los desacuerdos del gold doble.

Solo muestra las partes que adjudica quien abrió la sesión (que nunca es anotador de ellas) y solo
los pasajes que los dos anotadores ya cerraron en esa pasada. Enseña las dos anotaciones como
"Anotación 1" y "Anotación 2", sin nombres, y nunca predicciones del sistema. Lo que coincide en
tipo e intervalo entra solo; cada desacuerdo se incluye o se excluye, sin nada preseleccionado.
Guarda en `anotaciones/gold_v2/adjudicado_<adjudicador>.csv`.
"""
from __future__ import annotations

import html

import streamlit as st

from mtx import config
from mtx import gold_v2 as V
from mtx.app import componentes as C
from mtx.app import sesion
from mtx.app import vista_gold_v2 as W

DECISION = {V.INCLUIR: "Incluir", V.EXCLUIR: "Excluir"}


def _accion(fn, *args) -> None:
    try:
        fn(*args)
        W._msg("exito", "Guardado.")
    except C.ConflictoEdicion as e:
        W._msg("error", f"{e} No se guardó nada.")
    except (ValueError, OSError) as e:
        W._msg("error", f"No se guardó: {e}")


def _decidir(s, tok, pid, pasada, sha, c, clave) -> None:
    _accion(s.decidir, tok, pid, pasada, sha, c["tipo"], c["inicio"], c["fin"],
            c["propuesta"], st.session_state[clave] or "")


def estado_pasaje(dir_anot, parte, est_adj, pid, pasada, sha) -> str:
    f = est_adj[(est_adj["passage_id"] == pid) & (est_adj["pasada"] == pasada)]
    if len(f) and f["huella"].iloc[0] != V.huella(dir_anot, parte, pid, pasada):
        return "obsoleto"
    if len(f) and f["estado"].iloc[0] == V.CERRADO:
        return "adjudicado"
    if not V.listo_para_adjudicar(dir_anot, parte, pid, pasada, sha):
        return "esperando anotadores"
    return "en adjudicación" if len(f) else "por adjudicar"


def mostrar() -> None:
    st.header("Adjudicación del gold v2")
    yo = sesion.anotador(
        "¿Quién va a adjudicar?", "Adjudicas como",
        "Solo verás las partes que adjudicas, cuando las dos anotaciones estén cerradas. Nunca "
        "verás lo que predice el sistema.")
    if yo is None:
        return
    try:
        cfg = V.cargar_config()
    except (ValueError, KeyError) as e:
        st.error(f"Configuración del gold v2 inválida: {e}")
        return
    mias = V.partes_de_adjudicador(cfg, yo)
    if not mias:
        st.info("No adjudicas ninguna parte del gold v2 (PRD v2 D31).")
        return
    dir_anot = V.dir_anotaciones()

    st.sidebar.subheader("Parte")
    nombres = {p.id: p.nombre for p in mias}
    pid_parte = st.sidebar.selectbox("Parte", list(nombres), key="adj_parte",
                                     format_func=nombres.get, label_visibility="collapsed")
    parte = cfg.partes[pid_parte]
    abiertas = [x for x in parte.pasadas if V.pasada_abierta(cfg, x)]
    if not abiertas:
        st.info(f"{parte.nombre}: todavía no hay pasada abierta.")
        return
    pasada = st.sidebar.radio("Pasada", abiertas, key=f"adj_pasada_{pid_parte}",
                              format_func=W.NOMBRE_PASADA.get)
    man = V.manifiesto(parte)
    if man is None:
        st.info(f"Falta la muestra de {parte.nombre}.")
        return
    s = V.SesionAdjudicador(dir_anot, yo, cfg)
    adj, est_adj, tok = s.cargar()
    ids = list(man["passage_id"])
    consulta = dict(zip(man["passage_id"], man["query_id"]))
    sha_man = dict(zip(man["passage_id"], man["texto_sha256"]))
    estados = {p: estado_pasaje(dir_anot, parte, est_adj, p, pasada, sha_man[p]) for p in ids}
    pid = st.sidebar.selectbox("Pasaje", ids, key=f"adj_pasaje_{pid_parte}",
                               format_func=lambda p: f"{consulta[p]} · {p} · {estados[p]}")
    hechos = sum(e == "adjudicado" for e in estados.values())
    st.sidebar.progress(hechos / len(ids), text=f"Adjudicados: {hechos} de {len(ids)}")
    W.mostrar_mensaje()

    pas = W.pasajes(tuple(ids), config.PASAJES_PARQUET.stat().st_mtime)
    p = pas.loc[pid]
    texto, ic, sha = p["texto"], int(p["inicio_cuerpo"]), p["texto_sha256"]
    if sha != sha_man[pid]:
        st.error("El texto de este pasaje cambió desde el sorteo: no se puede adjudicar.")
        return
    st.markdown(f"**{consulta[pid]} · {pid}** · {W.NOMBRE_PASADA[pasada]} · estado "
                f"**{estados[pid]}** · {html.escape(str(p['titulo']))}")
    if estados[pid] == "esperando anotadores":
        st.info("Las dos anotaciones de este pasaje todavía no están cerradas.")
        return
    if estados[pid] == "obsoleto":
        st.warning("Una anotación cambió después de adjudicar: revisa de nuevo los desacuerdos "
                   "y vuelve a cerrar el pasaje.")

    cand = V.candidatos(dir_anot, parte, pid, pasada)
    decs = s.decisiones(adj, pid, pasada)
    etiqueta = {a: f"Anotación {i}" for i, a in enumerate(parte.anotadores, 1)}
    W.leyenda()
    cols = st.columns(2)
    for col, a in zip(cols, parte.anotadores):
        f = cand[cand["propuesta"].isin([a, V.AMBOS])].assign(passage_id=pid)
        col.markdown(f"**{etiqueta[a]}** · {len(f)} entidades")
        col.markdown(f'<div class="pasaje">{W.pasaje_html(texto, ic, f)}</div>',
                     unsafe_allow_html=True)

    acuerdos = cand[cand["propuesta"] == V.AMBOS]
    desac = cand[cand["propuesta"] != V.AMBOS]
    st.subheader(f"Coinciden ({len(acuerdos)}): entran al gold")
    if len(acuerdos):
        st.dataframe(acuerdos[["tipo", "texto", "inicio", "fin"]], hide_index=True,
                     width="stretch")
    st.subheader(f"Desacuerdos ({len(desac)})")
    if desac.empty:
        st.caption("Sin desacuerdos: cierra el pasaje.")
    cerrado = estados[pid] == "adjudicado"
    for g, grupo in desac.groupby("grupo"):
        st.markdown(f"**Desacuerdo {g}**" + (" · se solapan: incluye a lo más una"
                                             if len(grupo) > 1 else ""))
        for c in grupo.to_dict("records"):
            clave = f"adj_{pid}_{pasada}_{c['tipo']}_{c['inicio']}_{c['fin']}_{c['propuesta']}"
            actual = decs.get((c["tipo"], c["inicio"], c["fin"], c["propuesta"]), "")
            st.radio(f"{etiqueta[c['propuesta']]}: {c['tipo']} «{c['texto']}» "
                     f"({c['inicio']}-{c['fin']})", list(DECISION), key=clave,
                     index=list(DECISION).index(actual) if actual else None,
                     format_func=DECISION.get, horizontal=True, disabled=cerrado,
                     on_change=_decidir, args=(s, tok, pid, pasada, sha, c, clave))

    incl = cand[[c.propuesta == V.AMBOS or decs.get(
        (c.tipo, int(c.inicio), int(c.fin), c.propuesta)) == V.INCLUIR
        for c in cand.itertuples()]].assign(passage_id=pid)
    st.subheader(f"Gold adjudicado de este pasaje ({len(incl)})")
    st.markdown(f'<div class="pasaje">{W.pasaje_html(texto, ic, incl)}</div>',
                unsafe_allow_html=True)
    c1, _ = st.columns([1.4, 3])
    if cerrado:
        c1.button("Reabrir adjudicación", key="adj_reabrir",
                  on_click=_accion, args=(s.marcar, tok, pid, pasada, sha, texto, False))
    else:
        pend = V.errores_adjudicacion(cand, decs, texto)
        c1.button("Pasaje adjudicado", key="adj_cerrar", type="primary", disabled=bool(pend),
                  on_click=_accion, args=(s.marcar, tok, pid, pasada, sha, texto, True))
        for e in pend:
            st.caption(e)
