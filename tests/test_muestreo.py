"""T09 · Muestreo del gold y del conjunto de selección (PRD §6.11, D10, U13). Datos sintéticos."""
from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from mtx import muestreo as M

TEXTO_LARGO = " ".join(f"palabra{i} contenido sustantivo" for i in range(30))
PROTOCOLO = frozenset({"buenos", "días", "gracias", "presidente", "muchas"})


def _mundo(n_consultas=10, compartidos=0):
    """Top-10 por consulta; los primeros `compartidos` pasajes de cada consulta se repiten en la
    siguiente (colisiones artificiales)."""
    filas = []
    for qi in range(1, n_consultas + 1):
        ids = [f"{qi * 100 + r}_0" for r in range(1, 11)]
        if compartidos and qi > 1:
            ids[:compartidos] = [f"{(qi - 1) * 100 + r}_0" for r in range(1, compartidos + 1)]
        filas += [{"query_id": f"Q{qi}", "passage_id": p, "doc_id": int(p.split("_")[0]),
                   "rango": r} for r, p in enumerate(ids, 1)]
    amb = pd.DataFrame(filas)
    pids = sorted(set(amb["passage_id"]))
    pasajes = pd.DataFrame({"passage_id": pids, "texto": [TEXTO_LARGO] * len(pids),
                            "inicio_cuerpo": 0})
    pasajes["texto_sha256"] = [hashlib.sha256(t.encode()).hexdigest() for t in pasajes["texto"]]
    return amb, pasajes


def test_mismo_ranking_y_semilla_mismo_manifiesto():
    amb, pas = _mundo()
    a = M.sortear(amb, pas, protocolo=PROTOCOLO)
    b = M.sortear(amb.sample(frac=1, random_state=3), pas, protocolo=PROTOCOLO)
    pd.testing.assert_frame_equal(a.gold, b.gold)
    pd.testing.assert_frame_equal(a.seleccion, b.seleccion)
    assert not M.sortear(amb, pas, semilla=7, protocolo=PROTOCOLO).gold.equals(a.gold)


def test_veinte_ids_unicos_dos_por_consulta_y_estratos():
    amb, pas = _mundo()
    m = M.sortear(amb, pas, protocolo=PROTOCOLO)
    assert list(m.gold.columns) == M.COLUMNAS_MANIFIESTO
    assert len(m.gold) == 20 and m.gold["passage_id"].is_unique
    assert m.gold["query_id"].value_counts().eq(2).all()
    assert m.estratos_respetados
    r = amb.set_index(["query_id", "passage_id"])["rango"]
    rangos = m.gold.apply(lambda f: r[(f.query_id, f.passage_id)], axis=1)
    por_q = rangos.groupby(m.gold["query_id"]).apply(sorted)
    assert all(a <= 5 < b for a, b in por_q)
    assert (m.gold["semilla"] == 42).all() and (m.gold["version_muestra"] == 1).all()


def test_colisiones_resueltas_sin_duplicar():
    amb, pas = _mundo(compartidos=5)  # la mitad alta de cada top-10 se comparte
    m = M.sortear(amb, pas, protocolo=PROTOCOLO)
    assert len(m.gold) == 20 and m.gold["passage_id"].is_unique
    pares = set(zip(amb["query_id"], amb["passage_id"]))
    assert all((q, p) in pares for q, p in zip(m.gold["query_id"], m.gold["passage_id"]))


def test_caso_imposible_reporta_consultas_en_conflicto():
    amb, pas = _mundo(n_consultas=3)
    # Q2 y Q3 comparten exactamente los mismos 3 pasajes: 4 plazas, 3 pasajes
    comunes = ["900_0", "901_0", "902_0"]
    amb = amb[amb["query_id"] == "Q1"]
    extra = [{"query_id": q, "passage_id": p, "doc_id": int(p.split("_")[0]), "rango": r}
             for q in ("Q2", "Q3") for r, p in enumerate(comunes, 1)]
    amb = pd.concat([amb, pd.DataFrame(extra)], ignore_index=True)
    pas = pd.concat([pas, pd.DataFrame({"passage_id": comunes, "texto": TEXTO_LARGO,
                                        "inicio_cuerpo": 0, "texto_sha256": "x"})])
    with pytest.raises(M.MuestraInviable) as e:
        M.sortear(amb, pas, protocolo=PROTOCOLO)
    assert set(e.value.consultas) <= {"Q2", "Q3"} and e.value.consultas


def test_sin_estratos_si_no_hay_asignacion_estratificada():
    amb, pas = _mundo(n_consultas=2)
    amb = amb[amb["rango"] <= 5]  # nadie en el estrato 6-10
    m = M.sortear(amb, pas, protocolo=PROTOCOLO, n_seleccion=2)
    assert not m.estratos_respetados and len(m.gold) == 4 and m.avisos


def test_seleccion_disjunta_seis_consultas_distintas():
    amb, pas = _mundo()
    m = M.sortear(amb, pas, protocolo=PROTOCOLO)
    assert len(m.seleccion) == 6 and m.seleccion["query_id"].is_unique
    assert not set(m.seleccion["passage_id"]) & set(m.gold["passage_id"])


@pytest.mark.parametrize("texto,motivo", [
    ("Buenos días, presidente. Muchas gracias.", "menos de 25"),
    (" ".join(["gracias buenos días presidente"] * 10) + " " + " ".join(
        f"tema{i}" for i in range(26)), "protocolo"),
    ("", "causa técnica"),
    (TEXTO_LARGO, None),
])
def test_criterios_objetivos_de_sustitucion(texto, motivo):
    m = M.motivo_sustitucion(texto, 0, PROTOCOLO)
    assert (m is None) if motivo is None else (motivo in m)


def test_excluidos_no_entran_y_el_sustituto_es_el_siguiente_sorteado():
    amb, pas = _mundo()
    base = M.sortear(amb, pas, protocolo=PROTOCOLO)
    retirado = base.gold.iloc[0]["passage_id"]
    pas2 = pas.copy()
    pas2.loc[pas2["passage_id"] == retirado, "texto"] = "Buenos días, gracias."
    m = M.sortear(amb, pas2, protocolo=PROTOCOLO)
    assert retirado not in set(m.gold["passage_id"])
    assert list(m.excluidos["passage_id"]) == [retirado]
    assert "palabras de contenido" in m.excluidos.iloc[0]["motivo"]
    assert m.gold["query_id"].value_counts().eq(2).all()


def test_protocolo_real_existe_y_no_incluye_palabras_funcionales():
    p = M.leer_protocolo()
    assert {"gracias", "buenos", "días"} <= p
    assert not p & {"de", "la", "que", "el", "en", "y"}
