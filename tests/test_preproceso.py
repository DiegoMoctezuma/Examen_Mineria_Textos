"""T02b · Preprocesamiento (PRD §6.2): tokens de las consultas, marca fuera del índice."""
from __future__ import annotations

import pandas as pd
import pytest

from mtx import consultas, preproceso
from mtx.preproceso import tokenizar, tokenizar_pasaje, tokenizar_sin_stem

TERMINOS_CLAVE = {
    "Q3": ["dos", "bocas"], "Q4": ["santa", "lucía"], "Q5": ["sembrando", "vida"],
    "Q6": ["huachicol"], "Q8": ["mínimo"],
}


def test_terminos_clave_de_las_consultas_sobreviven():
    cons = consultas.cargar().set_index("query_id")["consulta"]
    for qid, claves in TERMINOS_CLAVE.items():
        sin_stem = tokenizar_sin_stem(cons[qid])
        for clave in claves:
            assert clave in sin_stem, f"{clave} se perdió en {qid}: {sin_stem}"


def test_ninguna_consulta_queda_sin_tokens():
    for r in consultas.cargar().itertuples():
        assert tokenizar(r.consulta), r.query_id


def test_covid_19_es_un_solo_token_y_19_numerico_sobrevive():
    assert "covid-19" in tokenizar("La vacuna contra el COVID-19")
    assert tokenizar("el 19") == ["19"]
    assert tokenizar("de la a") == []  # longitud y stoplist


def test_minusculas_nfc_y_acentos():
    descompuesto = "pensión"  # "pensión" con tilde combinada
    assert tokenizar(descompuesto) == tokenizar("PENSIÓN") == ["pension"]


def test_stoplist_estenografica_y_nltk():
    for p in ("presidente", "gracias", "obrador", "para", "los"):
        assert p in preproceso.stoplist()
    assert tokenizar("Presidente, gracias por la pregunta") == tokenizar("por")  # todo cae
    assert len(preproceso.hash_stoplist()) == 64


def test_la_stoplist_respaldo_coincide_con_nltk_si_esta_disponible():
    nltk_corpus = pytest.importorskip("nltk.corpus")
    try:
        oficial = set(nltk_corpus.stopwords.words("spanish"))
    except LookupError:
        pytest.skip("nltk_data no disponible")
    respaldo = set((preproceso.config.DIR_CONFIG / "stopwords_es.txt").read_text(
        encoding="utf-8").split())
    assert respaldo == oficial


def test_siglas_y_nombres_propios_no_se_retiran():
    assert "pemex" in tokenizar("Pemex y la CFE")
    assert "cfe" in tokenizar("Pemex y la CFE")


def test_tokenizar_pasaje_equivale_a_tokenizar_el_cuerpo():
    marca = "SECRETARIO DE SALUD, JORGE ALCOCER VARELA: "
    texto = marca + "La vacuna llegó a Tabasco."
    assert tokenizar_pasaje(texto, len(marca)) == tokenizar(texto[len(marca):])


def test_ningun_token_proviene_solo_de_la_marca():
    marca = "ZOÉ ROBLEDO ABURTO: "
    toks = tokenizar_pasaje(marca + "Los hospitales del IMSS crecen.", len(marca))
    assert not {"zoe", "robled", "abur"} & set(toks)
    assert "hospital" in toks


def test_cambiar_la_marca_no_cambia_los_tokens():
    cuerpo = "Se construye el aeropuerto en Santa Lucía."
    a = tokenizar_pasaje("PREGUNTA: " + cuerpo, len("PREGUNTA: "))
    b = tokenizar_pasaje("INTERLOCUTORA: " + cuerpo, len("INTERLOCUTORA: "))
    assert a == b


def test_pasajes_sin_marca_inicio_cero():
    assert tokenizar_pasaje("vacunas en Tabasco", 0) == tokenizar("vacunas en Tabasco")


@pytest.mark.skipif(not preproceso.config.PASAJES_PARQUET.exists(), reason="requiere make corpus")
def test_con_pasajes_reales_la_marca_nunca_aporta_tokens():
    p = pd.read_parquet(preproceso.config.PASAJES_PARQUET).sample(300, random_state=42)
    for r in p.itertuples():
        assert tokenizar_pasaje(r.texto, r.inicio_cuerpo) == tokenizar(r.texto[r.inicio_cuerpo:])


def test_caminos_v1_solo_con_q1_a_q10():
    """Agregar Q11 a Q15 (PRD v2 D25) no cambia lo que leen ranking, pool, evaluación y entrega v1."""
    cons = pd.DataFrame({"query_id": ["Q1", "Q10", "Q11", "Q15"], "consulta": ["a", "b", "c", "d"]})
    assert list(consultas.solo_v1(cons)["query_id"]) == ["Q1", "Q10"]
