"""Gold v2 (PRD v2 D31 a D33, WP-09): doble anotación por pasadas, adjudicación, acuerdo y
validación. Todo en carpetas temporales con textos sintéticos; nunca toca `anotaciones/` ni
`config/`."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pandas as pd
import pytest
import yaml

from mtx import gold_v2 as V
from mtx.app import componentes as C

TEXTO = ("SECRETARIO DE SALUD, JORGE ALCOCER VARELA: El IMSS pagó 20 mil millones de pesos en "
         "Tabasco el 15 de enero de 2021.")
IC = TEXTO.index(":") + 2


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _span(s: str) -> tuple[int, int]:
    i = TEXTO.index(s)
    return i, i + len(s)


CONFIG = {
    "anotadores": [{"id": i, "nombre": i.title()} for i in
                   ("diego", "gonzalo", "arturo", "bruno", "leo", "luis")],
    "gold": {
        "no_anotan": ["leo"],
        "pasada_2_sin_etiqueta": False,
        "partes": {
            "seleccion": {"nombre": "Selección", "manifiesto": "v2/muestra_seleccion.csv",
                          "anotadores": ["diego", "luis"], "adjudicador": "arturo",
                          "pasadas": [1, 2]},
            "a": {"nombre": "Parte A", "manifiesto": "v2/muestra_gold_a.csv",
                  "anotadores": ["diego", "gonzalo"], "adjudicador": "bruno", "pasadas": [1, 2]},
        },
    },
}


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    anot = tmp_path / "anotaciones"
    (anot / "v2").mkdir(parents=True)
    monkeypatch.setenv("MTX_ANOTACIONES", str(anot))
    ruta_cfg = tmp_path / "anotadores.yaml"
    ruta_cfg.write_text(yaml.safe_dump(CONFIG, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv("MTX_ANOTADORES", str(ruta_cfg))
    monkeypatch.setattr(V, "etiqueta_existe", lambda nombre: False)
    pas = []
    for parte, prefijo in (("muestra_seleccion.csv", "s"), ("muestra_gold_a.csv", "a")):
        filas = []
        for q in range(1, 3):
            pid = f"{prefijo}{q}_0"
            t = f"{TEXTO} {pid}"
            filas.append({"query_id": f"Q{q}", "passage_id": pid, "doc_id": q,
                          "texto_sha256": _sha(t), "semilla": 42, "version_muestra": 1})
            pas.append({"passage_id": pid, "texto": t, "texto_sha256": _sha(t),
                        "inicio_cuerpo": IC})
        pd.DataFrame(filas).to_csv(anot / "v2" / parte, index=False)
    cfg = V.cargar_config()
    return cfg, anot, pd.DataFrame(pas).set_index("passage_id"), ruta_cfg


def _anotar(cfg, anot, pas, quien, pid, ents, pasada=1, cerrar=True):
    s = V.SesionAnotador(anot, quien, cfg)
    texto, sha = pas.at[pid, "texto"], pas.at[pid, "texto_sha256"]
    for tipo, frag in ents:
        ini, fin = _span(frag)
        s.agregar(s.token(), pid, pasada, texto, sha, tipo, ini, fin)
    if cerrar:
        s.marcar(s.token(), pid, pasada, sha, True)
    return s


# --------------------------------------------------------------------------- configuración


@pytest.mark.parametrize("cambio,mensaje", [
    (lambda c: c["gold"]["partes"]["a"].update(adjudicador="gonzalo"), "no puede anotar"),
    (lambda c: c["gold"]["partes"]["a"].update(anotadores=["diego", "leo"]), "no anota"),
    (lambda c: c["gold"]["partes"]["a"].update(adjudicador=None), "necesita adjudicador"),
    (lambda c: c["gold"]["partes"]["a"].update(anotadores=["diego", "nadie"]), "desconocido"),
])
def test_config_rechaza_papeles_invalidos(mundo, cambio, mensaje):
    _, anot, _, ruta = mundo
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    cambio(datos)
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match=mensaje):
        V.cargar_config(ruta, anot)


def test_config_real_cumple_d31():
    cfg = V.cargar_config()
    assert {p: (c.anotadores, c.adjudicador) for p, c in cfg.partes.items() if c.doble} == {
        "seleccion": (("diego", "arturo"), "gonzalo"), "a": (("diego", "gonzalo"), "luis"),
        "b": (("gonzalo", "arturo"), "diego")}
    # Recortes 2 y 3 (2026-11-23): sin reanotar la FECHA del gold v1 y pasada 2 sin etiqueta.
    assert "v1" not in cfg.partes
    assert "leo" in cfg.no_anotan and cfg.pasada_2_sin_etiqueta


# --------------------------------------------------------------------------- anotación por pasadas


def test_pasada_1_sin_fecha_y_pasada_2_cerrada_sin_etiqueta(mundo, monkeypatch):
    cfg, anot, pas, _ = mundo
    s = V.SesionAnotador(anot, "luis", cfg)
    pid = "s1_0"
    texto, sha = pas.at[pid, "texto"], pas.at[pid, "texto_sha256"]
    with pytest.raises(ValueError, match="solo se anota"):
        s.agregar(s.token(), pid, 1, texto, sha, "FECHA", *_span("15 de enero de 2021"))
    with pytest.raises(ValueError, match="reglas-fecha-v2"):
        s.agregar(s.token(), pid, 2, texto, sha, "FECHA", *_span("15 de enero de 2021"))
    monkeypatch.setattr(V, "etiqueta_existe", lambda nombre: nombre == V.ETIQUETA_FECHA)
    with pytest.raises(ValueError, match="solo se anota"):
        s.agregar(s.token(), pid, 2, texto, sha, "PER", *_span("JORGE ALCOCER VARELA"))
    s.agregar(s.token(), pid, 2, texto, sha, "FECHA", *_span("15 de enero de 2021"))
    g = V.leer_gold(anot, "luis")
    assert list(g.columns) == V.COLUMNAS_GOLD and list(g["pasada"]) == [2]


def test_cada_quien_solo_sus_pasajes_y_su_archivo(mundo):
    cfg, anot, pas, _ = mundo
    _anotar(cfg, anot, pas, "luis", "s1_0", [("PER", "JORGE ALCOCER VARELA")])
    assert V.ruta_gold(anot, "luis").exists() and not V.ruta_gold(anot, "diego").exists()
    s = V.SesionAnotador(anot, "gonzalo", cfg)
    with pytest.raises(ValueError, match="ninguna parte asignada"):
        s.agregar(s.token(), "s1_0", 1, pas.at["s1_0", "texto"], pas.at["s1_0", "texto_sha256"],
                  "ORG", *_span("IMSS"))
    assert [p.id for p in V.partes_de_anotador(cfg, "gonzalo")] == ["a"]
    assert V.partes_de_anotador(cfg, "leo") == [] and V.partes_de_anotador(cfg, "arturo") == []


def test_cerrar_sin_entidades_es_valido_y_editar_reabre(mundo):
    cfg, anot, pas, _ = mundo
    s = _anotar(cfg, anot, pas, "diego", "s1_0", [])
    assert V.estado_de(V.leer_estado(anot, "diego"), "s1_0", 1) == V.CERRADO
    s.agregar(s.token(), "s1_0", 1, pas.at["s1_0", "texto"], pas.at["s1_0", "texto_sha256"],
              "ORG", *_span("IMSS"))
    est = V.leer_estado(anot, "diego")
    assert V.estado_de(est, "s1_0", 1) == V.ABIERTO
    assert est["revision"].iloc[0] == 2


def test_solape_y_dos_pestanas(mundo):
    cfg, anot, pas, _ = mundo
    s = _anotar(cfg, anot, pas, "diego", "s1_0", [("PER", "JORGE ALCOCER VARELA")], cerrar=False)
    texto, sha = pas.at["s1_0", "texto"], pas.at["s1_0", "texto_sha256"]
    with pytest.raises(ValueError, match="solapa"):
        s.agregar(s.token(), "s1_0", 1, texto, sha, "PER", *_span("ALCOCER"))
    viejo = s.token()
    s.agregar(viejo, "s1_0", 1, texto, sha, "ORG", *_span("IMSS"))
    with pytest.raises(C.ConflictoEdicion):
        s.agregar(viejo, "s1_0", 1, texto, sha, "LOC", *_span("Tabasco"))


# --------------------------------------------------------------------------- adjudicación


def _par_con_desacuerdo(cfg, anot, pas, pid="s1_0"):
    _anotar(cfg, anot, pas, "diego", pid, [("PER", "JORGE ALCOCER VARELA"), ("ORG", "IMSS"),
                                           ("MONTO", "20 mil millones de pesos")])
    _anotar(cfg, anot, pas, "luis", pid, [("PER", "JORGE ALCOCER VARELA"), ("ORG", "IMSS"),
                                          ("MONTO", "20 mil millones"), ("LOC", "Tabasco")])


def test_adjudicar_requiere_las_dos_anotaciones_cerradas(mundo):
    cfg, anot, pas, _ = mundo
    _anotar(cfg, anot, pas, "diego", "s1_0", [("ORG", "IMSS")])
    s = V.SesionAdjudicador(anot, "arturo", cfg)
    with pytest.raises(ValueError, match="aún no cierran"):
        s.decidir(s.token(), "s1_0", 1, pas.at["s1_0", "texto_sha256"], "ORG", *_span("IMSS"),
                  "diego", V.INCLUIR)
    otro = V.SesionAdjudicador(anot, "bruno", cfg)  # adjudica A, no la selección
    with pytest.raises(ValueError, match="no adjudica"):
        otro.decidir(otro.token(), "s1_0", 1, pas.at["s1_0", "texto_sha256"], "ORG",
                     *_span("IMSS"), "diego", V.INCLUIR)


def test_candidatos_marcan_acuerdos_y_agrupan_desacuerdos(mundo):
    cfg, anot, pas, _ = mundo
    _par_con_desacuerdo(cfg, anot, pas)
    cand = V.candidatos(anot, cfg.partes["seleccion"], "s1_0", 1)
    amb = cand[cand["propuesta"] == V.AMBOS]
    assert set(amb["texto"]) == {"JORGE ALCOCER VARELA", "IMSS"} and (amb["grupo"] == 0).all()
    des = cand[cand["propuesta"] != V.AMBOS].set_index("texto")
    assert des.at["20 mil millones de pesos", "grupo"] == des.at["20 mil millones", "grupo"]
    assert des.at["Tabasco", "grupo"] != des.at["20 mil millones", "grupo"]
    assert des.at["Tabasco", "propuesta"] == "luis"


def test_adjudicacion_completa_bloquea_reanotar_y_da_el_gold_oficial(mundo):
    cfg, anot, pas, _ = mundo
    _par_con_desacuerdo(cfg, anot, pas)
    s = V.SesionAdjudicador(anot, "arturo", cfg)
    pid, texto, sha = "s1_0", pas.at["s1_0", "texto"], pas.at["s1_0", "texto_sha256"]
    with pytest.raises(ValueError, match="Faltan 3 desacuerdos"):
        s.marcar(s.token(), pid, 1, sha, texto, True)
    s.decidir(s.token(), pid, 1, sha, "MONTO", *_span("20 mil millones de pesos"), "diego",
              V.INCLUIR)
    s.decidir(s.token(), pid, 1, sha, "MONTO", *_span("20 mil millones"), "luis", V.INCLUIR)
    s.decidir(s.token(), pid, 1, sha, "LOC", *_span("Tabasco"), "luis", V.INCLUIR)
    with pytest.raises(ValueError, match="solapa"):
        s.marcar(s.token(), pid, 1, sha, texto, True)
    s.decidir(s.token(), pid, 1, sha, "MONTO", *_span("20 mil millones"), "luis", V.EXCLUIR)
    s.marcar(s.token(), pid, 1, sha, texto, True)
    adj = V.leer_adj(anot, "arturo")
    assert list(adj.columns) == V.COLUMNAS_ADJ and (adj["decision"] != "").all()
    # el anotador ya no reanota un pasaje en adjudicación
    d = V.SesionAnotador(anot, "luis", cfg)
    with pytest.raises(ValueError, match="adjudicación"):
        d.marcar(d.token(), pid, 1, sha, False)
    of = V.gold_oficial(cfg, anot)
    assert sorted(of["texto"]) == sorted(["JORGE ALCOCER VARELA", "IMSS",
                                          "20 mil millones de pesos", "Tabasco"])
    assert set(of.columns) >= set(V.COLUMNAS_GOLD) and (of["parte"] == "seleccion").all()


def test_adjudicacion_obsoleta_si_cambia_una_anotacion(mundo):
    cfg, anot, pas, _ = mundo
    pid, texto, sha = "s1_0", pas.at["s1_0", "texto"], pas.at["s1_0", "texto_sha256"]
    _anotar(cfg, anot, pas, "diego", pid, [("ORG", "IMSS")])
    _anotar(cfg, anot, pas, "luis", pid, [("ORG", "IMSS")])
    s = V.SesionAdjudicador(anot, "arturo", cfg)
    s.marcar(s.token(), pid, 1, sha, texto, True)
    assert len(V.gold_oficial(cfg, anot)) == 1
    # simula una anotación que llegó cambiada por git después de adjudicar
    ruta = V.ruta_gold(anot, "luis")
    g = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    g.loc[0, "tipo"] = "LOC"
    g.to_csv(ruta, index=False)
    assert V.gold_oficial(cfg, anot).empty
    v = V.validar_gold_v2(cfg, pas.reset_index(), anot, pasadas=(1,))
    assert any("obsoleta" in e for e in v.errores)


# --------------------------------------------------------------------------- acuerdo y validación


def test_acuerdo_f1_exacto_por_tipo_y_pendientes(mundo):
    cfg, anot, pas, _ = mundo
    tabla, pend = V.acuerdo(cfg, anot)
    assert tabla.empty and len(pend) == 2  # selección y A sin cerrar (pasada 2 cerrada)
    _par_con_desacuerdo(cfg, anot, pas, "s1_0")
    _anotar(cfg, anot, pas, "diego", "s2_0", [])
    _anotar(cfg, anot, pas, "luis", "s2_0", [])
    tabla, pend = V.acuerdo(cfg, anot)
    assert list(tabla.columns) == V.COLUMNAS_ACUERDO
    t = tabla[(tabla["parte"] == "seleccion")].set_index("tipo")
    assert t.at["PER", "f1"] == 1.0 and t.at["ORG", "f1"] == 1.0
    assert t.at["MONTO", "f1"] == 0.0 and t.at["LOC", "f1"] == 0.0
    assert t.at["micro", "coincidencias"] == 2
    assert math.isclose(t.at["micro", "f1"], round(2 * 2 / (3 + 4), 4))
    assert "Parte A, pasada 1" in " ".join(pend)
    assert set(tabla["parte"]) == {"seleccion", "todas"}


def test_validar_gold_v2_completo_y_con_faltantes(mundo):
    cfg, anot, pas, _ = mundo
    v = V.validar_gold_v2(cfg, pas.reset_index(), anot, pasadas=(1,))
    assert not v.ok and any("cerrados 0 de 2" in e for e in v.errores)
    for pid in ("s1_0", "s2_0"):
        _anotar(cfg, anot, pas, "diego", pid, [("ORG", "IMSS")])
        _anotar(cfg, anot, pas, "luis", pid, [("ORG", "IMSS")])
    for pid in ("a1_0", "a2_0"):
        _anotar(cfg, anot, pas, "diego", pid, [])
        _anotar(cfg, anot, pas, "gonzalo", pid, [("LOC", "Tabasco")])
    sa = V.SesionAdjudicador(anot, "arturo", cfg)
    sb = V.SesionAdjudicador(anot, "bruno", cfg)
    for s, ids in ((sa, ("s1_0", "s2_0")), (sb, ("a1_0", "a2_0"))):
        for pid in ids:
            texto, sha = pas.at[pid, "texto"], pas.at[pid, "texto_sha256"]
            if s is sb:
                s.decidir(s.token(), pid, 1, sha, "LOC", *_span("Tabasco"), "gonzalo",
                          V.EXCLUIR)
            s.marcar(s.token(), pid, 1, sha, texto, True)
    v = V.validar_gold_v2(cfg, pas.reset_index(), anot, pasadas=(1,), excluir_v1={"x_0"})
    assert v.ok, v.errores
    assert any("sin entidades" in a for a in v.avisos)  # la parte A quedó vacía: P04
    v = V.validar_gold_v2(cfg, pas.reset_index(), anot, pasadas=(1,), excluir_v1={"s1_0"})
    assert any("ámbito IE de v1" in e for e in v.errores)


def test_modulo_no_lee_predicciones():
    fuente = Path(V.__file__).read_text(encoding="utf-8")
    for prohibido in ("salida", "DIR_SALIDA", "cache_ner", "ner_modelo", "fusion", "ranking"):
        assert prohibido not in fuente.split('"""', 2)[2]


# --------------------------------------------------------------------------- app


def _app_gold():
    from mtx.app import vista_gold_v2
    vista_gold_v2.mostrar()


def _app_adj():
    from mtx.app import vista_adjudicacion
    vista_adjudicacion.mostrar()


@pytest.fixture
def app_mundo(mundo, monkeypatch):
    """Los pasajes sintéticos sustituyen la lectura del parquet."""
    from mtx.app import vista_gold_v2
    _, _, pas, _ = mundo
    monkeypatch.setattr(vista_gold_v2, "pasajes",
                        lambda ids, mtime: pas.assign(titulo="Versión", fecha="2021-01-15"))
    return mundo


def _como(at, quien):
    at.selectbox(key="elegir_anotador").select(quien).run()
    assert not at.exception, at.exception
    return at


def test_app_gold_v2_ciega_y_por_pasada(app_mundo):
    from streamlit.testing.v1 import AppTest
    cfg, anot, pas, _ = app_mundo
    _anotar(cfg, anot, pas, "diego", "s1_0", [("ORG", "IMSS")])
    at = _como(AppTest.from_function(_app_gold, default_timeout=60).run(), "luis")
    assert at.selectbox(key="g2_tipo_b").options == ["PER", "ORG", "LOC", "MONTO"]
    assert list(at.selectbox(key="g2_parte").options) == ["Selección"]
    visible = " ".join(m.value for m in at.markdown)
    assert "gold ORG" not in visible  # la anotación de Diego no se ve
    at.text_input(key="g2_buscar").input("IMSS").run()
    at.radio(key="g2_aparicion").set_value(0).run()
    at.selectbox(key="g2_tipo_b").select("ORG").run()
    at.button(key="g2_agregar_b").click().run()
    assert not at.exception
    assert list(V.leer_gold(anot, "luis")["texto"]) == ["IMSS"]
    at.button(key="g2_cerrar").click().run()
    assert V.estado_de(V.leer_estado(anot, "luis"), "s1_0", 1) == V.CERRADO


def test_app_gold_v2_sin_partes_para_leo_y_arturo(app_mundo):
    from streamlit.testing.v1 import AppTest
    for quien in ("leo", "arturo"):
        at = _como(AppTest.from_function(_app_gold, default_timeout=60).run(), quien)
        assert any("No tienes pasajes gold" in i.value for i in at.info)


def test_app_adjudicacion_espera_y_luego_muestra_anonimo(app_mundo):
    from streamlit.testing.v1 import AppTest
    cfg, anot, pas, _ = app_mundo
    at = _como(AppTest.from_function(_app_adj, default_timeout=60).run(), "arturo")
    assert any("todavía no están cerradas" in i.value for i in at.info)
    _par_con_desacuerdo(cfg, anot, pas)
    at = _como(AppTest.from_function(_app_adj, default_timeout=60).run(), "arturo")
    assert not at.exception
    visible = " ".join(m.value for m in at.markdown) + " ".join(r.label for r in at.radio)
    assert "Anotación 1" in visible and "diego" not in visible.lower()
    assert all(r.value is None for r in at.radio if r.key.startswith("adj_s1_0"))
    assert at.button(key="adj_cerrar").disabled
    at = _como(AppTest.from_function(_app_adj, default_timeout=60).run(), "diego")
    assert any("No adjudicas" in i.value for i in at.info)  # la selección no es suya
