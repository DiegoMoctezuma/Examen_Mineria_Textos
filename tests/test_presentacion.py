"""Pruebas de `mtx.presentacion` (PRD v2 WP-15): títulos y fechas reales del corpus, fecha
desconocida y que ningún texto visible lleve IDs."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from mtx import presentacion as P

MATUTINA = ("12.03.21 Versión estenográfica de la conferencia de prensa matutina del presidente "
            "Andrés Manuel López Obrador")


def fila(**kw):
    base = {"titulo": MATUTINA, "fecha": pd.Timestamp("2021-03-12"), "posicion": 2,
            "interlocutor": "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR", "es_reportero": False,
            "url": "https://ejemplo.mx/discurso", "passage_id": "1122_2", "doc_id": 1122}
    base.update(kw)
    return base


def test_ejemplo_del_prd():
    assert P.etiqueta_pasaje(fila()) == "Mañanera del 12 de marzo de 2021 · fragmento 3"


@pytest.mark.parametrize("fecha, esperado", [
    ("2024-09-30", "30 de septiembre de 2024"),
    (pd.Timestamp("2019-01-01"), "1 de enero de 2019"),
    (None, "fecha desconocida"),
    (pd.NaT, "fecha desconocida"),
    ("no es fecha", "fecha desconocida"),
])
def test_fecha_larga(fecha, esperado):
    assert P.fecha_larga(fecha) == esperado


def test_fecha_desconocida_en_el_titulo():
    assert P.etiqueta_pasaje(fila(fecha=pd.NaT)) == \
        "Mañanera (fecha desconocida) · fragmento 3"


@pytest.mark.parametrize("titulo, evento, lugar", [
    (MATUTINA, "Mañanera", None),
    (("16.02.24 Versión estenográfica de la conferencia de prensa matutina del presidente Andrés "
     "Manuel López Obrador, desde Culiacán, Sinaloa"), "Mañanera", "Culiacán, Sinaloa"),
    (("28.06.2019 Versión estenográfica de la conferencia de prensa del presidente Andrés Manuel "
     "López Obrador"), "Conferencia de prensa", None),
    ("26.02.21 Versión estenográfica. Inauguración del Hospital General de Querétaro",
     "Inauguración del Hospital General de Querétaro", None),
    ("09.03.19 Versión estenográfica. ‘Programas Integrales de Bienestar’, en Guadalajara, Jalisco",
     "Programas Integrales de Bienestar, en Guadalajara, Jalisco", None),
    (("14.07.19 Versión estenográfica. Diálogo con la comunidad del Hospital Rural Buenavista "
     "Tomatlán, desde Michoacán."), "Diálogo con la comunidad del Hospital Rural Buenavista Tomatlán",
     "Michoacán"),
    ("Discurso del presidente Andrés Manuel López Obrador en el Día de la Maestra y el Maestro",
     "Discurso en el Día de la Maestra y el Maestro", None),
    ("28.09.24 Inauguración y Abanderamiento: Sector Naval Boca de Chila, desde Compostela, Nayarit",
     "Inauguración y Abanderamiento: Sector Naval Boca de Chila", "Compostela, Nayarit"),
    ("", "Evento", None),
    (None, "Evento", None),
])
def test_evento_y_lugar_con_titulos_reales(titulo, evento, lugar):
    assert P.evento_y_lugar(titulo) == (evento, lugar)


def test_tema_largo_se_recorta_en_palabra():
    titulo = "10.09.24 Versión estenográfica. " + "Supervisión de construcción " * 8
    evento, _ = P.evento_y_lugar(titulo)
    assert len(evento) <= P.LARGO_TEMA and evento.endswith("…")
    assert not evento[:-1].endswith(" ")


def test_titulo_con_tema():
    f = P.ficha(fila(titulo="26.02.21 Versión estenográfica. Inauguración del Hospital General de "
                            "Querétaro", fecha="2021-02-26", posicion=0))
    assert f.titulo == ("Inauguración del Hospital General de Querétaro · 26 de febrero de 2021 · "
                        "fragmento 1")


@pytest.mark.parametrize("interlocutor, es_rep, esperado", [
    ("PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR", False, "Presidente Andrés Manuel López Obrador"),
    ("HUGO LÓPEZ-GATELL RAMÍREZ, SUBSECRETARIO DE PREVENCIÓN Y PROMOCIÓN DE LA SALUD", False,
     "Hugo López-Gatell Ramírez, Subsecretario de Prevención y Promoción de la Salud"),
    ("ZOÉ ROBLEDO ABURTO, DIRECTOR GENERAL DEL INSTITUTO MEXICANO DEL SEGURO SOCIAL (IMSS)", False,
     "Zoé Robledo Aburto, Director General del Instituto Mexicano del Seguro Social (IMSS)"),
    ("INTERLOCUTORA", True, "Pregunta de la prensa"),
    ("PREGUNTA", False, "Pregunta de la prensa"),
    ("VOZ MUJER", False, "Participante sin identificar"),
    ("INTERVENCIÓN HOMBRE", False, "Participante sin identificar"),
    ("MODERADORA", False, "Moderación"),
    ("DE VIDEO", False, "Video"),
    ("", False, "Participante sin identificar"),
    (None, False, "Participante sin identificar"),
])
def test_quien_habla(interlocutor, es_rep, esperado):
    assert P.quien_habla(interlocutor, es_rep) == esperado


def test_ficha_sin_ids_ni_rutas():
    f = P.ficha(fila())
    visible = " ".join([f.titulo, f.evento, f.fecha, f.lugar or "", f.habla])
    assert "1122" not in visible and "/" not in visible
    assert f.fragmento == 3 and f.url == "https://ejemplo.mx/discurso"


def test_fila_como_series_y_campos_faltantes():
    f = P.ficha(pd.Series({"titulo": MATUTINA, "fecha": pd.NaT}))
    assert f.titulo == "Mañanera (fecha desconocida) · fragmento 1"
    assert f.habla == "Participante sin identificar" and f.url is None


def test_todos_los_pasajes_reales_tienen_titulo_sin_ids():
    """Recorre un discurso por documento del corpus; no imprime contenido."""
    from mtx import config

    if not config.PASAJES_PARQUET.exists():
        pytest.skip("Sin data/pasajes.parquet (correr `make corpus`)")
    p = pd.read_parquet(config.PASAJES_PARQUET,
                        columns=["passage_id", "doc_id", "titulo", "fecha", "posicion", "interlocutor",
                                 "es_reportero"])
    id_visible = re.compile(r"\b\d+_\d+\b")
    for r in p.drop_duplicates("doc_id").itertuples():
        f = P.ficha(r._asdict())
        assert f.titulo and " · fragmento " in f.titulo
        assert r.passage_id not in f.titulo
        assert not id_visible.search(f.titulo)
    hablas = p.drop_duplicates("interlocutor").apply(
        lambda r: P.quien_habla(r["interlocutor"], r["es_reportero"]), axis=1)
    assert hablas.str.len().max() <= P.LARGO_HABLA
