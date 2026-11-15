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


# --------------------------------------------------------------------------- v2 (PRD v2 D31, WP-08)

Q_AB = [f"Q{i}" for i in range(1, 11)]
Q_B = [f"Q{i}" for i in range(11, 16)]
PLAN_SA = [("seleccion", Q_AB, 1), ("a", Q_AB, 1)]
ESPERADO = {"seleccion": (Q_AB, 1), "a": (Q_AB, 1), "b": (Q_B, 2)}


def _pool_v2(consultas, por_q=6, compartidos=0, con_filtro=True):
    """Pool sintético con columna `variantes`; la mitad de los pares solo sin filtro."""
    filas = []
    for q in consultas:
        n = int(q[1:])
        ids = [f"{n * 100 + r}_0" for r in range(1, por_q + 1)]
        if compartidos and n > int(consultas[0][1:]):
            ids[:compartidos] = [f"{(n - 1) * 100 + r}_0" for r in range(1, compartidos + 1)]
        for p in ids:
            filas.append({"query_id": q, "passage_id": p, "doc_id": int(p.split("_")[0]),
                          "variantes": "tfidf_con_filtro|bm25_sin_filtro" if con_filtro
                          else "bm25_sin_filtro"})
        filas.append({"query_id": q, "passage_id": f"{n * 100 + 99}_0", "doc_id": n * 100 + 99,
                      "variantes": "tfidf_sin_filtro|bm25_sin_filtro"})
    return pd.DataFrame(filas)


def _pasajes_de(pool):
    pids = sorted(set(pool["passage_id"]))
    df = pd.DataFrame({"passage_id": pids, "texto": [TEXTO_LARGO] * len(pids),
                       "inicio_cuerpo": 0})
    df["texto_sha256"] = [hashlib.sha256(t.encode()).hexdigest() for t in df["texto"]]
    return df


def test_v2_universo_solo_con_filtro_y_sin_excluidos():
    pool = _pool_v2(Q_AB)
    excluir = {"101_0", "202_0"}
    u = M.universo_con_filtro(pool, excluir)
    assert not set(u["passage_id"]) & excluir
    assert not any(p.endswith("99_0") for p in u["passage_id"])  # solo sin filtro: fuera
    assert list(u.columns) == ["query_id", "passage_id", "doc_id"]


def test_v2_seleccion_y_a_una_por_consulta_disjuntas_y_sin_v1():
    pool = _pool_v2(Q_AB)
    excluir = {f"{q * 100 + 1}_0" for q in range(1, 11)}  # "ámbito v1" sintético
    u = M.universo_con_filtro(pool, excluir)
    m = M.sortear_v2(u, _pasajes_de(pool), PLAN_SA, protocolo=PROTOCOLO)
    sel, a = m.partes["seleccion"], m.partes["a"]
    for df in (sel, a):
        assert list(df.columns) == M.COLUMNAS_MANIFIESTO
        assert df["query_id"].value_counts().eq(1).all() and set(df["query_id"]) == set(Q_AB)
    assert not set(sel["passage_id"]) & set(a["passage_id"])
    assert not (set(sel["passage_id"]) | set(a["passage_id"])) & excluir
    assert M.errores_muestra_v2(m.partes, excluir, ESPERADO) == []
    pares = set(zip(pool["query_id"], pool["passage_id"]))
    assert all((f.query_id, f.passage_id) in pares for f in pd.concat([sel, a]).itertuples())


def test_v2_mismo_resultado_al_volver_a_correr():
    pool = _pool_v2(Q_AB)
    u = M.universo_con_filtro(pool, set())
    a = M.sortear_v2(u, _pasajes_de(pool), PLAN_SA, protocolo=PROTOCOLO)
    b = M.sortear_v2(u.sample(frac=1, random_state=5), _pasajes_de(pool), PLAN_SA,
                     protocolo=PROTOCOLO)
    for p in ("seleccion", "a"):
        pd.testing.assert_frame_equal(a.partes[p], b.partes[p])
    c = M.sortear_v2(u, _pasajes_de(pool), PLAN_SA, semilla=7, protocolo=PROTOCOLO)
    assert not all(c.partes[p].equals(a.partes[p]) for p in ("seleccion", "a"))


def test_v2_colisiones_entre_consultas_sin_duplicar():
    pool = _pool_v2(Q_AB, por_q=3, compartidos=2)  # cada consulta comparte 2 de 3 con la anterior
    u = M.universo_con_filtro(pool, set())
    m = M.sortear_v2(u, _pasajes_de(pool), PLAN_SA, protocolo=PROTOCOLO)
    todos = pd.concat(m.partes.values())
    assert todos["passage_id"].is_unique and len(todos) == 20


def test_v2_parte_b_dos_por_consulta_y_disjunta_de_las_previas():
    pool_ab = _pool_v2(Q_AB)
    u = M.universo_con_filtro(pool_ab, set())
    sa = M.sortear_v2(u, _pasajes_de(pool_ab), PLAN_SA, protocolo=PROTOCOLO)
    previos = set(pd.concat(sa.partes.values())["passage_id"])
    # el pool v2 de Q11 a Q15 reusa pasajes de Q1 a Q10 (incluidos los ya sorteados)
    pool_b = _pool_v2(Q_B)
    reuso = pool_ab[pool_ab["passage_id"].isin(previos)].assign(query_id="Q11")
    pool_b = pd.concat([pool_b, reuso], ignore_index=True)
    ub = M.universo_con_filtro(pool_b, previos)
    mb = M.sortear_v2(ub, _pasajes_de(pool_b), [("b", Q_B, 2)], protocolo=PROTOCOLO)
    b = mb.partes["b"]
    assert b["query_id"].value_counts().eq(2).all() and set(b["query_id"]) == set(Q_B)
    assert b["passage_id"].is_unique and not set(b["passage_id"]) & previos
    assert M.errores_muestra_v2({**sa.partes, "b": b}, set(), ESPERADO) == []


def test_v2_inviable_reporta_consultas_sin_ampliar():
    pool = _pool_v2(Q_AB, por_q=1)  # 1 pasaje por consulta y hacen falta 2
    u = M.universo_con_filtro(pool, set())
    with pytest.raises(M.MuestraInviable) as e:
        M.sortear_v2(u, _pasajes_de(pool), PLAN_SA, protocolo=PROTOCOLO)
    assert e.value.consultas  # nombra las consultas en conflicto


def test_v2_excluye_por_u13_antes_del_sorteo():
    pool = _pool_v2(Q_AB)
    pas = _pasajes_de(pool)
    corto = "101_0"
    pas.loc[pas["passage_id"] == corto, "texto"] = "buenos días"
    m = M.sortear_v2(M.universo_con_filtro(pool, set()), pas, PLAN_SA, protocolo=PROTOCOLO)
    assert corto in set(m.excluidos["passage_id"])
    assert corto not in set(pd.concat(m.partes.values())["passage_id"])


def test_v2_comprobacion_detecta_traslape_y_v1():
    df = pd.DataFrame({"query_id": Q_AB, "passage_id": [f"{i}_0" for i in range(10)],
                       "doc_id": range(10), "texto_sha256": "x", "semilla": 42,
                       "version_muestra": 1})
    err = M.errores_muestra_v2({"seleccion": df, "a": df}, {"0_0"}, ESPERADO)
    assert any("aparece en las partes" in e for e in err)
    assert any("predicciones visibles en v1" in e for e in err)
