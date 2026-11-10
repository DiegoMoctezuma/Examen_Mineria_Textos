"""Tablas de respuesta (PRD §6.13, U14, T14). Fixtures sintéticos, sin corpus ni modelos."""
from __future__ import annotations

import pandas as pd
import pytest
import yaml

from mtx import respuestas as RS
from mtx.fusion import sin_acentos

PRESI = "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: "
T1 = (PRESI + "La pensión será de dos mil 550 pesos bimestrales. El IMSS no paga nada. "
      "El año pasado se invirtieron 120 mil millones de pesos en otras obras de la ciudad "
      "de Puebla y en caminos rurales muy lejos de aquí.")
T2 = ("INTERLOCUTOR: ¿Es cierto que Pemex pagará 500 pesos al día a cada trabajador?")
T3 = (PRESI + "Cada sembrador recibe 5 mil pesos mensuales. Además, como lo hemos dicho en "
      "varias ocasiones aquí, el presupuesto total del programa es de 30 mil millones de pesos "
      "para este año en todo el país.")


def _pas(**extra):
    filas = [
        {"passage_id": "1_1", "doc_id": 1, "fecha": pd.Timestamp("2021-01-02"), "texto": T1,
         "inicio_cuerpo": len(PRESI), "interlocutor": "PRESIDENTE", "es_reportero": False,
         "intervencion_id": 10, "rango": 1},
        {"passage_id": "2_1", "doc_id": 2, "fecha": pd.Timestamp("2021-02-02"), "texto": T2,
         "inicio_cuerpo": len("INTERLOCUTOR: "), "interlocutor": "INTERLOCUTOR",
         "es_reportero": True, "intervencion_id": 20, "rango": 2},
        {"passage_id": "3_1", "doc_id": 3, "fecha": pd.Timestamp("2021-03-02"), "texto": T3,
         "inicio_cuerpo": len(PRESI), "interlocutor": "PRESIDENTE", "es_reportero": False,
         "intervencion_id": 30, "rango": 3},
    ]
    return pd.DataFrame(filas).set_index("passage_id")


def _ent(pid, tipo, frag, texto, q="Q1", en_marca=False, **extra):
    i = texto.index(frag)
    base = {"query_id": q, "passage_id": pid, "tipo": tipo, "texto": frag, "inicio": i,
            "fin": i + len(frag), "en_marca": en_marca, "canonico": "",
            "texto_normalizado": sin_acentos(frag), "fecha_iso": "", "valor_num": "",
            "moneda": ""}
    base.update(extra)
    return base


ENT = pd.DataFrame([
    _ent("1_1", "PER", "ANDRÉS MANUEL LÓPEZ OBRADOR", T1, en_marca=True),
    _ent("1_1", "MONTO", "dos mil 550 pesos", T1, valor_num="2550", moneda="MXN"),
    _ent("1_1", "ORG", "IMSS", T1, canonico="Instituto Mexicano del Seguro Social"),
    _ent("1_1", "MONTO", "120 mil millones de pesos", T1, valor_num="120000000000", moneda="MXN"),
    _ent("1_1", "LOC", "Puebla", T1),
    _ent("2_1", "ORG", "Pemex", T2),
    _ent("2_1", "MONTO", "500 pesos", T2, valor_num="500", moneda="MXN"),
    _ent("3_1", "MONTO", "5 mil pesos", T3, valor_num="5000", moneda="MXN"),
    _ent("3_1", "MONTO", "30 mil millones de pesos", T3, valor_num="30000000000", moneda="MXN"),
    _ent("3_1", "PER", "Andrés Manuel López Obrador", T3 + " Andrés Manuel López Obrador",
         texto_normalizado="andres manuel lopez obrador"),
])
LISTA = {"andres manuel lopez obrador"}
AUX = pd.DataFrame(columns=["query_id", "passage_id", "texto", "inicio", "fin", "tipo_aux",
                            "valor_num", "unidad"])


def _campo(tipo, patrones, **kw):
    return RS.Campo(kw.pop("q", "Q1"), kw.pop("campo", "c"), kw.pop("fuente", "entidad"), tipo,
                    tuple(patrones), "relación de prueba", **kw)


def _responder(campo, ent=ENT):
    ent_q, *_ = RS.excluir(ent[ent["query_id"] == campo.query_id], LISTA)
    ic = {k: int(v) for k, v in _pas()["inicio_cuerpo"].items()}
    cands = RS.candidatos(campo, ent_q, AUX, RS.Filtros(), ic)
    return RS.agregar(campo, RS.responder_campo(campo, cands, _pas(), ent_q))


def test_u14_exclusiones_marca_y_lista_solo_per():
    filtradas, n_marca, n_lista = RS.excluir(ENT, LISTA)
    assert (n_marca, n_lista) == (1, 1)
    assert not filtradas["en_marca"].any()
    assert "andres manuel lopez obrador" not in set(filtradas.loc[filtradas.tipo == "PER",
                                                                   "texto_normalizado"])
    # la lista no toca ORG/LOC/MONTO aunque compartieran forma
    org = ENT.assign(tipo="ORG", en_marca=False)
    assert RS.excluir(org, LISTA)[2] == 0


def test_q7_bimestral_solo_con_patron_en_contexto():
    filas, _ = _responder(_campo("MONTO", ["bimestr"], unidad="MXN bimestral"))
    est = {f["valor"]: (f["estado"], f["unidad"]) for f in filas}
    assert est["dos mil 550 pesos"] == ("respaldado_en_texto", "MXN bimestral")
    # lejos de "bimestrales" (más de 60 caracteres y en otra oración)
    assert est["120 mil millones de pesos"] == ("ambiguo", "MXN")


def test_q5_monto_por_beneficiario_distinto_del_presupuesto():
    filas, _ = _responder(_campo("MONTO", ["mensual|por sembrador|cada sembrador"]))
    est = {f["valor"]: f["estado"] for f in filas}
    assert est["5 mil pesos"] == "respaldado_en_texto"
    assert est["30 mil millones de pesos"] == "ambiguo"


def test_t14_reportero_nunca_respaldado_e_interlocutor_conservado():
    filas, _ = _responder(_campo("MONTO", ["diari|al dia"], unidad="MXN diario"))
    f = next(x for x in filas if x["valor"] == "500 pesos")
    assert f["estado"] == "ambiguo" and f["interlocutor"] == "INTERLOCUTOR"
    assert "pregunta (reportero)" in f["relacion"] and f["regla_relacion"].endswith(":reportero")
    assert f["unidad"] == "MXN"  # sin relación respaldada no se le pone "diario"


def test_cita_exacta_con_offsets_y_relacion_dentro():
    filas, _ = _responder(_campo("MONTO", ["bimestr"]))
    f = next(x for x in filas if x["estado"] == "respaldado_en_texto")
    assert T1[f["evidencia_inicio"]:f["evidencia_fin"]] == f["cita"]
    assert "bimestrales" in f["cita"] and f["valor"] in f["cita"]
    assert f["cita"] == f["cita"].strip()


def test_no_encontrado_con_evidencia_vacia_y_contrato():
    filas, ev = _responder(_campo("FECHA", ["aument"]))
    assert ev == [] and len(filas) == 1 and filas[0]["estado"] == "no_encontrado"
    res = pd.DataFrame(filas, columns=RS.COLUMNAS_RESPUESTAS)
    assert RS.validar_respuestas(res, {"1_1": T1}) == []
    malo = res.assign(passage_id="1_1")
    assert RS.validar_respuestas(malo, {"1_1": T1})
    assert len(RS.COLUMNAS_RESPUESTAS) == 16


def test_ventanas_solapadas_de_una_intervencion_son_un_evento():
    """Mismo valor en dos ventanas de la misma intervención: 2 pasajes, 1 evento, 1 discurso."""
    pas = _pas()
    otro = pas.loc[["1_1"]].rename(index={"1_1": "1_2"}).assign(rango=4)
    pas2 = pd.concat([pas, otro])
    ent = pd.concat([ENT, pd.DataFrame([dict(_ent("1_1", "MONTO", "dos mil 550 pesos", T1,
                                                  valor_num="2550", moneda="MXN"),
                                             passage_id="1_2")])])
    campo = _campo("MONTO", ["bimestr"])
    ent_q, *_ = RS.excluir(ent, LISTA)
    ic = {k: int(v) for k, v in pas2["inicio_cuerpo"].items()}
    cands = RS.candidatos(campo, ent_q, AUX, RS.Filtros(), ic)
    filas, ev = RS.agregar(campo, RS.responder_campo(campo, cands, pas2, ent_q))
    e = next(x for x in ev if x["valor"] == "dos mil 550 pesos")
    assert (e["frecuencia"], e["n_pasajes"], e["n_eventos"], e["n_discursos"]) == (2, 2, 1, 1)
    assert sum(f["valor"] == "dos mil 550 pesos" for f in filas) == 1


def test_contradictorio_se_conserva_sin_mayoria_y_orden_de_corte():
    campo = _campo("MONTO", ["pesos"], unico_por_evento=True)
    filas, _ = _responder(campo)
    t1 = [f for f in filas if f["passage_id"] == "1_1"]
    assert {f["estado"] for f in t1} == {"contradictorio"} and len(t1) == 2
    assert len({f["grupo_evento"] for f in t1}) == 1
    # orden: respaldado antes que contradictorio, antes que ambiguo
    rangos = [RS.RANGO_ESTADO[f["estado"]] for f in filas]
    assert rangos == sorted(rangos)


def test_filtro_por_gazetteer():
    f = RS.Filtros(d14={"Pfizer"}, entidades_federativas={"Puebla"})
    assert f.acepta("d14", "Pfizer", "pfizer") and not f.acepta("d14", "", "imss")
    assert f.acepta("entidades_federativas", "", "puebla")
    assert f.acepta("", "", "cualquiera")


def test_valoraciones_validar_e_invalidar(tmp_path):
    ruta = tmp_path / "valoraciones.yaml"
    hashes = {"Q1": "a" * 64, "Q2": "b" * 64}
    assert RS.validar_valoraciones(ruta, hashes)  # falta el archivo
    tok = RS.guardar_valoracion(ruta, "", "Q1", "Creíble a medias.", "a" * 64)
    with pytest.raises(ValueError):
        RS.guardar_valoracion(ruta, tok, "Q2", "   ", "b" * 64)
    from mtx.app.componentes import ConflictoEdicion
    with pytest.raises(ConflictoEdicion):
        RS.guardar_valoracion(ruta, "viejo", "Q2", "Algo.", "b" * 64)
    tok = RS.guardar_valoracion(ruta, tok, "Q2", "Le faltan montos.", "b" * 64)
    assert RS.validar_valoraciones(ruta, hashes) == []
    assert RS.validar_valoraciones(ruta, {**hashes, "Q2": "c" * 64}) == [
        "Q2: valoración invalidada (la tabla cambió); reescribirla"]
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert datos["Q1"]["texto"] == "Creíble a medias." and list(datos) == ["Q1", "Q2"]
    assert "invalidada" in RS.bloque_valoracion(datos["Q2"], "c" * 64)
    assert "[VALIDAR] pendiente" in RS.bloque_valoracion(None, "x")


def test_hash_tabla_solo_cambia_con_contenido_sustancial():
    res = pd.DataFrame([{"campo_respuesta": "c", "valor": "v", "estado": "ambiguo",
                         "passage_id": "1_1", "cita": "x", "unidad": "MXN"}])
    h = RS.hash_tabla(res)
    assert RS.hash_tabla(res.assign(cita="otra", unidad="")) == h
    assert RS.hash_tabla(res.assign(estado="respaldado_en_texto")) != h


def test_app_valoraciones_guarda_sin_precargar(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    from mtx import config
    if not (config.DIR_SALIDA / "10_hashes_tablas.json").exists():
        pytest.skip("sin tablas generadas")
    monkeypatch.setenv("MTX_ANOTACIONES", str(tmp_path))
    at = AppTest.from_function(_app_val, default_timeout=60).run()
    assert not at.exception
    area = at.text_area[0]
    assert area.value == ""  # nunca precarga texto
    at.button[[b.label for b in at.button].index("Guardar valoración")].click().run()
    assert not (tmp_path / "valoraciones.yaml").exists()  # vacío: no se guarda
    at.text_area[0].input("Texto escrito por el alumno.").run()
    at.button[[b.label for b in at.button].index("Guardar valoración")].click().run()
    datos = yaml.safe_load((tmp_path / "valoraciones.yaml").read_text(encoding="utf-8"))
    assert datos["Q1"]["texto"] == "Texto escrito por el alumno."
    assert len(datos["Q1"]["tabla_sha256"]) == 64


def _app_val():
    from mtx.app import estilo, vista_valoraciones
    estilo.aplicar()
    vista_valoraciones.mostrar()
