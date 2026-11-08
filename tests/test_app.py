"""T15 · App de anotación: escritura atómica, dos pestañas, reanudación, resaltado, estados y
modo ciego (PRD §7). Todo en carpetas temporales: nunca toca `anotaciones/` ni `config/`.

Los juicios que se escriben aquí son de prueba (sintéticos), no juicios humanos.
"""
from __future__ import annotations

import os
import shutil

import pandas as pd
import pytest

from mtx import config, pool
from mtx.app import componentes as C

POOL_REAL = config.DIR_SALIDA / "04_pool.csv"
requiere_pool = pytest.mark.skipif(not POOL_REAL.exists() or not config.PASAJES_PARQUET.exists(),
                                   reason="requiere make corpus y make pool")


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Anotaciones, criterio y una copia del pool en `tmp_path`."""
    anot = tmp_path / "anotaciones"
    anot.mkdir()
    crit = tmp_path / "criterios_relevancia.md"
    crit.write_text("# Criterio de prueba\n\nTexto sintético para las pruebas.\n",
                    encoding="utf-8")
    copia = tmp_path / "04_pool.csv"
    shutil.copyfile(POOL_REAL, copia)
    monkeypatch.setenv("MTX_ANOTACIONES", str(anot))
    monkeypatch.setenv("MTX_CRITERIOS_RELEVANCIA", str(crit))
    r = C.Rutas(anotaciones=anot, criterios=crit, pool=copia, pasajes=config.PASAJES_PARQUET,
                consultas=config.CONSULTAS_CSV)
    return r


def _primeros(items, n=3, q="Q1"):
    return items[items["query_id"] == q].head(n)


# --------------------------------------------------------------------------- escritura atómica


def test_interrupcion_antes_del_reemplazo_deja_el_original_intacto(tmp_path, monkeypatch):
    ruta = tmp_path / "a.csv"
    ruta.write_bytes(b"original\n")
    C.escribir_atomico(ruta, b"version 2\n")
    assert ruta.read_bytes() == b"version 2\n"
    assert (tmp_path / "a.csv.bak").read_bytes() == b"original\n"

    def falla(*a, **k):
        raise OSError("corte simulado")
    monkeypatch.setattr(os, "replace", falla)
    with pytest.raises(OSError):
        C.escribir_atomico(ruta, b"version 3\n")
    assert ruta.read_bytes() == b"version 2\n"
    assert (tmp_path / "a.csv.bak").read_bytes() == b"version 2\n"
    assert not list(tmp_path.glob("*.tmp"))


@requiere_pool
def test_dos_pestanas_la_segunda_se_rechaza(entorno):
    r = entorno
    items = C.cargar_items(r)
    a = _primeros(items).iloc[0]
    j1, t1 = C.cargar_juicios(r)
    j2, t2 = C.cargar_juicios(r)  # otra pestaña carga lo mismo
    C.guardar_juicio(items, j1, t1, a.query_id, a.passage_id, "1", r)
    contenido = r.juicios.read_bytes()
    with pytest.raises(C.ConflictoEdicion, match="otra pestaña"):
        C.guardar_juicio(items, j2, t2, a.query_id, a.passage_id, "0", r)
    assert r.juicios.read_bytes() == contenido  # nunca se sobrescribe en silencio


@requiere_pool
def test_revision_historial_metadato_y_formato(entorno):
    r = entorno
    items = C.cargar_items(r)
    p3 = _primeros(items)
    j, t = C.cargar_juicios(r)
    insumos = C.insumos_actuales(r)
    for valor, it in zip(["1", "0", ""], p3.itertuples()):
        j, t = C.guardar_juicio(items, j, t, it.query_id, it.passage_id, valor, r, insumos)
    j, t = C.guardar_juicio(items, j, t, p3.iloc[0].query_id, p3.iloc[0].passage_id, "0", r,
                            insumos)
    crudo = r.juicios.read_bytes()
    assert not crudo.startswith(b"\xef\xbb\xbf")
    assert crudo.decode().splitlines()[0] == "query_id,doc_id,passage_id,relevante"
    disco = pd.read_csv(r.juicios, dtype=str, keep_default_na=False)
    assert list(disco["relevante"]) == ["0", "0", ""]  # omitido = vacío, no 0
    assert not disco.duplicated(["query_id", "passage_id"]).any()
    meta = C.leer_meta(r.juicios)
    assert meta["revision"] == 4 and meta["sha256"] == C.sha256_ruta(r.juicios)
    assert meta["sha256_pool"] == insumos["sha256_pool"]
    hist = pd.read_csv(r.historial, dtype=str, keep_default_na=False)
    assert list(hist["revision"]) == ["1", "2", "3", "4"]
    assert list(hist.iloc[-1][["anterior", "nuevo"]]) == ["1", "0"]
    assert hist.iloc[0]["anterior"] == "sin_fila"


@requiere_pool
def test_guardar_fuera_del_pool_o_valor_invalido_falla(entorno):
    r = entorno
    items = C.cargar_items(r)
    j, t = C.cargar_juicios(r)
    with pytest.raises(ValueError, match="no está en el pool"):
        C.guardar_juicio(items, j, t, "Q1", "999999_0", "1", r)
    with pytest.raises(ValueError, match="inválido"):
        C.guardar_juicio(items, j, t, items.iloc[0].query_id, items.iloc[0].passage_id, "2", r)
    assert not r.juicios.exists()


@requiere_pool
def test_reanudar_situa_en_el_primer_pendiente(entorno):
    r = entorno
    items = C.cargar_items(r)
    g = items[items["query_id"] == "Q1"].reset_index(drop=True)
    j, t = C.cargar_juicios(r)
    for i in (0, 1, 3):
        j, t = C.guardar_juicio(items, j, t, "Q1", g.at[i, "passage_id"], "1", r)
    j, t = C.guardar_juicio(items, j, t, "Q1", g.at[2, "passage_id"], "", r)  # omitido
    j2, _ = C.cargar_juicios(r)  # "cerrar y reabrir"
    assert C.siguiente_pendiente(g, j2, 0, incluir_actual=True) == 2  # el omitido sigue pendiente
    prog = C.progreso(items, j2).set_index("query_id")
    assert prog.at["Q1", "juzgados"] == 3 and prog.at["Q1", "omitidos"] == 1
    assert prog.at["Q1", "pendientes"] == len(g) - 3


# --------------------------------------------------------------------------- resaltado


def test_resaltado_escapa_y_respeta_offsets_fuera_del_bmp():
    marca = "SECRETARIA <X> & CÍA: "
    texto = marca + "𝐀 😀 la Refinería & <b>refinerías</b> de Dos Bocas"
    spans = C.spans_terminos(texto, len(marca), "refinería de Dos Bocas")
    assert [texto[i:f] for i, f, _ in spans] == ["Refinería", "refinerías", "Dos", "Bocas"]
    for i, f, _ in spans:
        assert 0 <= i < f <= len(texto)
    h = C.html_pasaje(texto, len(marca), "refinería de Dos Bocas")
    assert "<b>" not in h and "&lt;b&gt;" in h and "&amp;" in h
    assert '<mark class="marca">SECRETARIA &lt;X&gt; &amp; CÍA: </mark>' in h
    assert '<mark class="termino">Refinería</mark>' in h
    assert "𝐀 😀" in h


def test_spans_solapados_o_fuera_de_rango_son_error_visible():
    with pytest.raises(ValueError, match="solapados"):
        C.html_desde_spans("abcdef", [(0, 3, "a"), (2, 4, "b")])
    with pytest.raises(ValueError, match="fuera de rango"):
        C.html_desde_spans("abc", [(1, 9, "a")])


def test_la_marca_no_se_resalta_como_termino():
    marca = "SECRETARIO DE ENERGÍA, REFINERÍA: "
    spans = C.spans_terminos(marca + "La refinería avanza.", len(marca), "refinería")
    assert all(i >= len(marca) for i, _, _ in spans) and len(spans) == 1


# --------------------------------------------------------------------------- estados


def _estado(r, nombre, **kw):
    filas = {e["artefacto"].split(" (")[0]: e for e in C.estados_artefactos(r, **kw)}
    return filas[nombre]


@requiere_pool
def test_estados_criterio_y_juicios(entorno):
    r = entorno
    assert _estado(r, "Juicios")["estado"] == C.PENDIENTE_HUMANO
    assert _estado(r, "Criterio de relevancia")["estado"] == C.VALIDO
    sin = C.Rutas(r.anotaciones, r.criterios.with_name("no_existe.md"), r.pool, r.pasajes,
                  r.consultas)
    assert _estado(sin, "Criterio de relevancia")["estado"] == C.PENDIENTE_HUMANO
    # Un archivo de juicios con cobertura parcial no es "válido".
    items = C.cargar_items(r)
    j, t = C.cargar_juicios(r)
    it = items.iloc[0]
    C.guardar_juicio(items, j, t, it.query_id, it.passage_id, "1", r, C.insumos_actuales(r))
    e = _estado(r, "Juicios")
    assert e["estado"] == C.PENDIENTE_HUMANO and e["detalle"].startswith("1 de ")
    assert _estado(r, "Juicios exportados")["estado"] != C.VALIDO


@requiere_pool
def test_estados_obsoleto_si_cambian_pool_o_textos_y_error_si_cambia_el_criterio(entorno):
    r = entorno
    items = C.cargar_items(r)
    j, t = C.cargar_juicios(r)
    it = items.iloc[0]
    C.guardar_juicio(items, j, t, it.query_id, it.passage_id, "1", r, C.insumos_actuales(r))
    antes = r.juicios.read_bytes()

    p = pool.leer_pool(r.pool)
    p.loc[0, "texto_sha256"] = "x" * 64
    p.to_csv(r.pool, index=False)
    assert _estado(r, "Juicios")["estado"] == C.OBSOLETO

    shutil.copyfile(POOL_REAL, r.pool)
    pas = pd.read_parquet(r.pasajes, columns=["passage_id", "texto"])
    pas.loc[pas.passage_id == it.passage_id, "texto"] = "texto cambiado"
    e = _estado(r, "Juicios", pasajes=pas)
    assert e["estado"] == C.OBSOLETO and "se conservan" in e["detalle"]

    r.criterios.write_text("# Otro criterio\n", encoding="utf-8")
    assert _estado(r, "Criterio de relevancia")["estado"] == C.ERROR
    assert r.juicios.read_bytes() == antes  # ningún estado borra ni toca juicios


# --------------------------------------------------------------------------- modo ciego


@requiere_pool
def test_items_no_cargan_procedencia_del_pool(entorno):
    items = C.cargar_items(entorno)
    assert not {"variantes", "mejor_rango_tfidf", "mejor_rango_bm25", "puntaje", "rango"} & set(
        items.columns)


def test_gold_cerrado_depende_solo_del_archivo_de_cierre(tmp_path):
    r = C.Rutas(tmp_path, tmp_path / "c.md", tmp_path / "p.csv", tmp_path / "x", tmp_path / "y")
    assert not C.gold_cerrado(r)
    (tmp_path / "cierre_gold.json").write_text("{}")
    assert C.gold_cerrado(r)


# --------------------------------------------------------------------------- app y CLI


def _app_juicios():
    from mtx.app import vista_juicios
    vista_juicios.mostrar()


@requiere_pool
def test_app_juicios_bloquea_sin_criterio(entorno, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("MTX_CRITERIOS_RELEVANCIA", str(entorno.criterios.with_name("no.md")))
    at = AppTest.from_function(_app_juicios, default_timeout=60).run()
    assert not at.exception
    assert any("criterios_relevancia.md" in e.value for e in at.error)
    assert at.button(key="rel").disabled and at.button(key="norel").disabled


@requiere_pool
def test_app_juicios_guarda_avanza_y_es_ciega(entorno):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_function(_app_juicios, default_timeout=60).run()
    assert not at.exception
    assert not at.button(key="rel").disabled
    visible = " ".join(m.value for m in at.markdown)
    for oculto in ("tfidf", "bm25", "variante", "mejor_rango", "puntaje"):
        assert oculto not in visible.lower()
    assert "Sin juzgar" in visible
    at.button(key="rel").click().run()
    assert not at.exception
    disco = pd.read_csv(entorno.juicios, dtype=str, keep_default_na=False)
    assert list(disco["relevante"]) == ["1"]
    assert "Pasaje 2 de" in " ".join(m.value for m in at.markdown)
    at.button(key="omitir").click().run()
    disco = pd.read_csv(entorno.juicios, dtype=str, keep_default_na=False)
    assert list(disco["relevante"]) == ["1", ""]
    at.button(key="anterior").click().run()
    assert "Omitido por ahora" in " ".join(m.value for m in at.markdown)


@requiere_pool
def test_app_juicios_no_regresa_a_q1_tras_juzgar_en_otra_consulta(entorno):
    """Regresión: la etiqueta del selector llevaba el contador "Qn · j/t". En el navegador, al
    cambiar el contador tras un clic, Streamlit no hallaba la etiqueta enviada y volvía a Q1
    (reproducido con navegador real). AppTest no reproduce ese envío, así que la causa se fija
    exigiendo etiquetas estables: el ID de la consulta, sin contadores."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_function(_app_juicios, default_timeout=60).run()
    assert at.selectbox(key="consulta").options == [f"Q{i}" for i in range(1, 11)]
    at.selectbox(key="consulta").select("Q2").run()
    assert at.markdown[0].value.startswith('<p class="consulta">Q2:')
    for accion in ("rel", "norel", "omitir"):
        at.button(key=accion).click().run()
        assert not at.exception
        assert at.selectbox(key="consulta").value == "Q2"
        assert '<p class="consulta">Q2:' in " ".join(m.value for m in at.markdown)
    disco = pd.read_csv(entorno.juicios, dtype=str, keep_default_na=False)
    assert set(disco["query_id"]) == {"Q2"}
    assert list(disco["relevante"]) == ["1", "0", ""]


@requiere_pool
def test_cli_juicios(entorno):
    from rich.console import Console

    from mtx.app import cli
    teclas = iter(["Q2", "1", "0", "o", "a", "s"])
    with open(os.devnull, "w") as nulo:
        cli.juicios(entrada=lambda _: next(teclas), consola=Console(file=nulo))
    disco = pd.read_csv(entorno.juicios, dtype=str, keep_default_na=False)
    assert list(disco["query_id"]) == ["Q2"] * 3
    assert list(disco["relevante"]) == ["1", "0", ""]
