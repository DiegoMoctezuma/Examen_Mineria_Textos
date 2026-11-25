"""WP-07 (D30): AND y OR sobre un índice de juguete, con filtro de fecha. Sin red ni datos reales."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mtx import booleano as B
from mtx import figuras_v2 as F
from mtx import preproceso as P
from mtx.indice import construir

TEXTOS = ["el huachicol y el robo de combustible", "robo en la carretera",
          "combate al huachicol", "programa de apoyo", "robo de combustible en ductos"]
FECHAS = np.array(["2019-01-10", "2019-02-01", "2020-05-01", "2019-03-01", "2019-04-01"],
                  dtype="datetime64[ns]")


@pytest.fixture(scope="module")
def ind():
    return construir([f"{i}_0" for i in range(len(TEXTOS))], [P.tokenizar(t) for t in TEXTOS])


def test_and_es_interseccion_y_or_es_union(ind):
    tok = P.tokenizar("huachicol robo")
    assert B.conjunto(ind, tok, "AND").tolist() == [0]
    assert B.conjunto(ind, tok, "OR").tolist() == [0, 1, 2, 4]
    assert B.conjunto(ind, [], "AND").size == 0
    assert B.conjunto(ind, ["inexistente", *tok], "AND").size == 0
    with pytest.raises(ValueError):
        B.conjunto(ind, tok, "NOT")


def test_por_consulta_cuenta_dentro_de_la_ventana(ind):
    cons = pd.DataFrame({"query_id": ["Q6"], "consulta": ["huachicol y robo"],
                         "desde": ["2019-01-01"], "hasta": ["2019-12-31"]})
    t = B.por_consulta(ind, FECHAS, cons).set_index("operador")
    assert t.at["AND", "pasajes"] == 1 and t.at["OR", "pasajes"] == 4
    assert t.at["OR", "en_ventana"] == 3  # el 2_0 es de 2020
    assert t.at["OR", "elegibles_ventana"] == 4 and t.at["OR", "n_terminos"] == 2


def test_ejemplo_el_booleano_no_distingue_el_termino_raro(ind):
    e = B.ejemplo(ind, FECHAS, "huachicol y robo", "2019-01-01", "2019-12-31", "huachicol",
                  "robo", k=2)
    assert (e["or_en_ventana"], e["or_con_raro"], e["or_sin_raro"]) == (3, 1, 2)
    assert e["bm25_top"] == 2 and e["bm25_top_con_raro"] == 1
    assert [t["palabra"] for t in e["terminos"]] == ["huachicol", "robo"]
    md = B.markdown_ejemplo(e, "Huachicol")
    assert "| «robo» | `rob` |" in md and "_0" not in md


def test_figura_booleano():
    t = pd.DataFrame({"query_id": ["Q9", "Q9", "Q3", "Q3"], "operador": ["AND", "OR"] * 2,
                      "en_ventana": [0, 15700, 135, 20205]})
    fig = F.fig_booleano(t, F.cargar_estilo())
    assert "1 pregunta no devuelve nada" in fig.layout.title.subtitle.text
    assert not F.tiene_id_o_ruta(fig) and fig.layout.xaxis.title.text
    assert list(fig.data[0].text) == ["0", "135"]  # de abajo arriba: Q9, Q3
