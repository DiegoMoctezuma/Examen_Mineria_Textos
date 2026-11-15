"""WP-01 y WP-02 (asignación) · juicios v2 con varios anotadores (PRD v2 D24).

Archivos por persona, pares asignados, nada de juicios ajenos, asignación congelada e
importación v1 sin cambios. Todo en carpetas temporales; los juicios de aquí son sintéticos.
"""
from __future__ import annotations

import shutil

import pandas as pd
import pytest

from mtx import anotadores as A
from mtx import config, pool
from mtx.app import componentes as C

POOL_REAL = config.DIR_SALIDA / "04_pool.csv"
requiere_pool = pytest.mark.skipif(not POOL_REAL.exists() or not config.PASAJES_PARQUET.exists(),
                                   reason="requiere make corpus y make pool")


@pytest.fixture
def lista():
    return A.cargar_anotadores()


@pytest.fixture
def pool_chico():
    return pd.DataFrame({
        "query_id": ["Q1", "Q1", "Q2"], "passage_id": ["1_1", "2_3", "3_2"],
        "doc_id": ["1", "2", "3"], "texto_sha256": ["a", "b", "c"]})


@pytest.fixture
def v2(tmp_path, monkeypatch):
    """Anotaciones, criterio y asignación temporales: arturo y bruno juzgan Q1 y Q2 en la app;
    leo solo Q3; diego viene de v1."""
    anot = tmp_path / "anotaciones"
    anot.mkdir()
    crit = tmp_path / "criterios_relevancia.md"
    crit.write_text("# Criterio de prueba\n", encoding="utf-8")
    yaml_ = tmp_path / "anotadores.yaml"
    shutil.copyfile(A.DIR_V2_CONFIG / "anotadores.yaml", yaml_)
    asig = tmp_path / "asignacion_juicios.csv"
    for k, v in {"MTX_ANOTACIONES": anot, "MTX_CRITERIOS_RELEVANCIA": crit,
                 "MTX_ANOTADORES": yaml_, "MTX_ASIGNACION": asig}.items():
        monkeypatch.setenv(k, str(v))
    p = pool.leer_pool(POOL_REAL)
    a = A.asignar_lote(p[p["query_id"].isin(["Q1", "Q2"])], "1", ["arturo", "bruno"], ["diego"],
                       A.cargar_anotadores())
    b = A.asignar_lote(p[p["query_id"] == "Q3"], "2", ["leo"], [], A.cargar_anotadores())
    A.agregar_asignacion(a, b).to_csv(asig, index=False)
    return tmp_path


# --------------------------------------------------------------------------- lista y asignación


def test_lista_de_anotadores_es_la_del_equipo(lista):
    assert list(lista) == ["diego", "gonzalo", "arturo", "bruno", "leo", "luis"]
    assert [a.id for a in lista.values() if a.coordinador] == ["diego"]
    assert lista["leo"].nombre.startswith("Leo Yahir")


def test_asignar_lote_da_cada_par_a_cada_juez_en_orden_del_pool(pool_chico, lista):
    a = A.asignar_lote(pool_chico, "1", ["arturo"], ["diego", "luis"], lista)
    assert len(a) == 9
    assert a.groupby("anotador").size().to_dict() == {"arturo": 3, "diego": 3, "luis": 3}
    assert set(a.loc[a["anotador"] == "arturo", "origen"]) == {"app"}
    assert set(a.loc[a["anotador"] == "luis", "origen"]) == {"v1"}
    assert list(A.pares_de(a, "arturo")["passage_id"]) == list(pool_chico["passage_id"])


def test_asignar_lote_rechaza_jueces_desconocidos_o_duplicados(pool_chico, lista):
    with pytest.raises(ValueError, match="no están"):
        A.asignar_lote(pool_chico, "1", ["fulano"], [], lista)
    with pytest.raises(ValueError, match="a la vez"):
        A.asignar_lote(pool_chico, "1", ["luis"], ["luis"], lista)


def test_asignacion_es_idempotente_y_congelada(pool_chico, lista):
    a = A.asignar_lote(pool_chico, "1", ["arturo"], [], lista)
    todo = A.agregar_asignacion(A.agregar_asignacion(a.iloc[0:0], a), a)
    assert todo.equals(a)
    otra = A.asignar_lote(pool_chico, "1", ["bruno"], [], lista)
    with pytest.raises(ValueError, match="no se reescribe"):
        A.agregar_asignacion(a, otra)


# --------------------------------------------------------------------------- app por anotador


@requiere_pool
def test_cada_anotador_ve_solo_sus_pares(v2):
    arturo, leo, diego = (C.cargar_items(C.rutas(x)) for x in ("arturo", "leo", "diego"))
    assert set(arturo["query_id"]) == {"Q1", "Q2"}
    assert set(leo["query_id"]) == {"Q3"}
    assert diego.empty  # sus juicios vienen de v1: no se editan en la app
    for oculto in ("variantes", "mejor_rango_tfidf", "mejor_rango_bm25"):
        assert oculto not in arturo.columns
    assert not C.textos_cambiados(arturo)


@requiere_pool
def test_dos_anotadores_mismo_par_escriben_archivos_distintos(v2):
    ra, rb = C.rutas("arturo"), C.rutas("bruno")
    ia, ib = C.cargar_items(ra), C.cargar_items(rb)
    q, pid = ia.at[0, "query_id"], ia.at[0, "passage_id"]
    ja, ta = C.cargar_juicios(ra)
    C.guardar_juicio(ia, ja, ta, q, pid, "1", ra, C.insumos_actuales(ra))
    jb, tb = C.cargar_juicios(rb)
    assert jb.empty  # bruno no ve el juicio de arturo
    C.guardar_juicio(ib, jb, tb, q, pid, "0", rb, C.insumos_actuales(rb))
    assert ra.juicios != rb.juicios
    assert pd.read_csv(ra.juicios, dtype=str)["relevante"].tolist() == ["1"]
    assert pd.read_csv(rb.juicios, dtype=str)["relevante"].tolist() == ["0"]
    assert ra.juicios.parent.name == "juicios_v2" and ra.historial.exists()
    assert not (ra.anotaciones / "juicios_relevancia.csv").exists()  # v1 no se toca


@requiere_pool
def test_par_no_asignado_no_se_puede_juzgar(v2):
    ra, rl = C.rutas("arturo"), C.rutas("leo")
    ia, il = C.cargar_items(ra), C.cargar_items(rl)
    q, pid = il.at[0, "query_id"], il.at[0, "passage_id"]
    ja, ta = C.cargar_juicios(ra)
    with pytest.raises(ValueError, match="no está en el pool"):
        C.guardar_juicio(ia, ja, ta, q, pid, "1", ra)


@requiere_pool
def test_la_app_no_lee_archivos_ajenos(v2, monkeypatch):
    rb = C.rutas("bruno")
    rb.juicios.parent.mkdir(parents=True, exist_ok=True)
    rb.juicios.write_text("esto no es un CSV de juicios\x00", encoding="utf-8")
    leidos = []
    original = pd.read_csv
    monkeypatch.setattr(pd, "read_csv", lambda ruta, *a, **k: (leidos.append(str(ruta)),
                                                               original(ruta, *a, **k))[1])
    ra = C.rutas("arturo")
    ia = C.cargar_items(ra)
    ja, ta = C.cargar_juicios(ra)
    C.guardar_juicio(ia, ja, ta, ia.at[0, "query_id"], ia.at[0, "passage_id"], "1", ra)
    C.cargar_juicios(ra)
    assert not any("bruno" in x for x in leidos)


@requiere_pool
def test_cambio_de_texto_bloquea(v2):
    ra = C.rutas("arturo")
    items = C.cargar_items(ra)
    items.loc[0, "texto_sha256"] = "otro"
    avisos = C.cambios_en_insumos(ra, items)
    assert avisos and "texto" in avisos[0]


@requiere_pool
def test_avance_solo_cuenta(v2, lista):
    ra = C.rutas("arturo")
    ia = C.cargar_items(ra)
    ja, ta = C.cargar_juicios(ra)
    C.guardar_juicio(ia, ja, ta, ia.at[0, "query_id"], ia.at[0, "passage_id"], "1", ra)
    tabla = A.avance(A.leer_asignacion(), ra.anotaciones, lista).set_index("anotador")
    assert tabla.at["arturo", "juzgados"] == 1
    assert tabla.at["arturo", "pendientes"] == len(ia) - 1
    assert "relevante" not in tabla.columns and "gonzalo" not in tabla.index


# --------------------------------------------------------------------------- importación v1


@requiere_pool
def test_importar_juicios_v1_copia_sin_cambios_y_no_sobrescribe(tmp_path):
    p = pool.leer_pool(POOL_REAL)
    origen = config.DIR_ANOTACIONES / "juicios_relevancia.csv"
    if not origen.exists():
        pytest.skip("requiere los juicios v1")
    destino = tmp_path / "diego.csv"
    j = A.importar_juicios_v1(origen, p, destino)
    v1 = pd.read_csv(origen, dtype=str, keep_default_na=False)
    assert j.sort_values(["query_id", "passage_id"]).reset_index(drop=True).equals(
        v1.sort_values(["query_id", "passage_id"]).reset_index(drop=True))
    distinto = j.copy()
    distinto.loc[0, "relevante"] = "1" if j.at[0, "relevante"] == "0" else "0"
    distinto.to_csv(destino, index=False)
    with pytest.raises(ValueError, match="no se sobrescribe"):
        A.importar_juicios_v1(origen, p, destino)


@requiere_pool
def test_importar_juicios_v1_exige_cobertura_completa(tmp_path):
    p = pool.leer_pool(POOL_REAL)
    incompleto = tmp_path / "incompleto.csv"
    p[pool.COLUMNAS_JUICIOS[:3]].head(10).assign(relevante="1").to_csv(incompleto, index=False)
    with pytest.raises(ValueError, match="Cobertura incompleta"):
        A.importar_juicios_v1(incompleto, p, tmp_path / "x.csv")


# --------------------------------------------------------------------------- vista


def _app_juicios():
    from mtx.app import vista_juicios
    vista_juicios.mostrar()


@requiere_pool
def test_app_pide_anotador_y_lo_recuerda_en_la_url(v2):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_function(_app_juicios, default_timeout=60).run()
    assert not at.exception and not at.button
    assert at.selectbox(key="elegir_anotador").value is None
    at.selectbox(key="elegir_anotador").select("leo").run()
    assert at.query_params["anotador"] in ("leo", ["leo"])
    assert at.selectbox(key="consulta").options == ["Q3"]
    at.button(key="norel").click().run()
    assert pd.read_csv(C.rutas("leo").juicios, dtype=str)["relevante"].tolist() == ["0"]
    otra = AppTest.from_function(_app_juicios, default_timeout=60)
    otra.query_params["anotador"] = "diego"
    otra.run()
    assert any("No tienes pares asignados" in i.value for i in otra.info)
