"""Descubrimiento de Q9 y Q10 con pasajes sintéticos (PRD §5.2)."""
from __future__ import annotations

import pandas as pd

from mtx import descubrimiento


def pasajes_demo():
    filas = [
        ("1_0", 1, 0, "2019-05-01", "Guardia Nacional", "La Guardia Nacional y el despliegue de elementos"),
        ("1_1", 1, 1, "2019-06-01", "PREGUNTA", "Hablamos del TREN INTEROCEÁNICO en Salina Cruz"),
        ("2_0", 2, 0, "2023-01-01", "PREGUNTA", "La guardia nacional otra vez"),
        ("3_0", 3, 0, "2019-07-01", "PREGUNTA", "Nada relacionado"),
    ]
    df = pd.DataFrame(filas, columns=["passage_id", "doc_id", "posicion", "fecha", "interlocutor", "cuerpo"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["texto"] = df["interlocutor"] + ": " + df["cuerpo"]
    df["inicio_cuerpo"] = df["interlocutor"].str.len() + 2
    return df


CAND = {"tema": "GN", "terminos": ["guardia nacional", "despliegue", "elementos"],
        "desde": "2019-01-01", "hasta": "2020-12-31", "pregunta": "?"}


def test_conteos_en_corpus_y_en_ventana():
    p = pasajes_demo()
    r = descubrimiento.analizar_candidato(p, descubrimiento.cuerpo_normalizado(p), CAND)
    assert (r["pasajes_total"], r["pasajes_ventana"]) == (2, 1)
    assert r["pasajes_ventana_2_terminos"] == 1
    assert r["discursos_total"] == 2 and r["discursos_ventana"] == 1
    assert r["por_anio"] == {2019: 1, 2023: 1}
    assert r["ejemplos"][0]["passage_id"] == "1_0"


def test_la_busqueda_ignora_acentos_mayusculas_y_la_marca():
    p = pasajes_demo()
    norm = descubrimiento.cuerpo_normalizado(p)
    cand = {**CAND, "terminos": ["interoceanico"], "desde": "2019-01-01", "hasta": "2019-12-31"}
    assert descubrimiento.analizar_candidato(p, norm, cand)["pasajes_ventana"] == 1
    # "guardia nacional" aparece en la marca de 1_0, pero la marca no se busca
    p.loc[3, "texto"] = "Guardia Nacional: nada"
    p.loc[3, "inicio_cuerpo"] = len("Guardia Nacional: ")
    assert descubrimiento.analizar_candidato(p, descubrimiento.cuerpo_normalizado(p), CAND)["pasajes_total"] == 2


def test_v2_ejemplos_al_azar_sin_pasajes_del_gold():
    """WP-04 (D32): los ejemplos no salen de las muestras del gold y no se ordenan por señal."""
    p = pasajes_demo()
    cand = CAND | {"hasta": "2023-12-31"}
    norm = descubrimiento.cuerpo_normalizado(p)
    r = descubrimiento.analizar_candidato(p, norm, cand, excluir=frozenset({"1_0"}), semilla=42)
    assert [e["passage_id"] for e in r["ejemplos"]] == ["2_0"]
    assert r["pasajes_ventana"] == 2  # los conteos no excluyen nada
    otra = descubrimiento.analizar_candidato(p, norm, cand, semilla=42)
    assert [e["passage_id"] for e in otra["ejemplos"]] == ["1_0", "2_0"]  # orden cronológico
