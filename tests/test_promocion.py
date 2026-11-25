"""WP-14 (D28): promoción de los seis CSV v2 a la raíz, bloqueo de v1 y condiciones 2 y 12. Archivos
inventados en carpetas temporales."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from mtx import entrega_v2 as W
from mtx import promocion as P
from mtx.entrega import FALLA, OK

CABECERAS = {
    "ranking.csv": "query_id,modelo,variante,rango,passage_id,doc_id,fecha,posicion,puntaje",
    "juicios_relevancia.csv": "query_id,doc_id,passage_id,relevante",
    "resultados_ir.csv": ("query_id,modelo,P@5,P@10,AP,relevantes_recuperados,"
                          "relevantes_en_pool,no_juzgados"),
    "entidades.csv": "query_id,doc_id,passage_id,tipo,texto,inicio,fin,metodo",
    "gold_entidades.csv": "passage_id,tipo,texto,inicio,fin",
    "resultados_ie.csv": "metodo,tipo,precision,recall,f1,tp,predichas,gold",
}


def _repo(tmp_path, requisitos=True):
    s2 = tmp_path / "salida" / "v2"
    s2.mkdir(parents=True)
    for n, cab in CABECERAS.items():
        (s2 / n).write_text(f"{cab}\nv2\n")
        (tmp_path / n).write_text(f"{cab}\nv1\n")
    if requisitos:
        for r in P.REQUISITOS:
            (tmp_path / r).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / r).write_text("{}")
    return s2


def test_sin_requisitos_no_toca_la_raiz(tmp_path):
    _repo(tmp_path, requisitos=False)
    inf = P.promover(tmp_path)
    assert not inf.ok and any("cierre_gold_v2" in e for e in inf.errores)
    assert (tmp_path / "ranking.csv").read_text().endswith("v1\n")
    assert not P.raiz_es_v2(tmp_path)


def test_promueve_registra_y_es_idempotente(tmp_path):
    _repo(tmp_path)
    inf = P.promover(tmp_path)
    assert inf.ok and sorted(inf.copiados) == sorted(P.NOMBRES)
    assert all((tmp_path / n).read_text().endswith("v2\n") for n in P.NOMBRES)
    reg = json.loads(P.registro(tmp_path).read_text())
    assert set(reg["sha256"]) == set(P.NOMBRES) and P.verificar(tmp_path) == []
    antes = P.registro(tmp_path).read_text()
    assert P.promover(tmp_path).copiados == [] and P.registro(tmp_path).read_text() == antes


def test_verificar_detecta_raiz_editada_o_v2_regenerado(tmp_path):
    s2 = _repo(tmp_path)
    P.promover(tmp_path)
    (tmp_path / "entidades.csv").write_text("otra cosa\n")
    assert any("entidades.csv" in e for e in P.verificar(tmp_path))
    P.promover(tmp_path)
    (s2 / "ranking.csv").write_text(CABECERAS["ranking.csv"] + "\nnuevo\n")
    assert any("ranking.csv" in e for e in P.verificar(tmp_path))


def test_bloquea_v1_solo_con_la_raiz_promovida(tmp_path):
    _repo(tmp_path)
    P.bloquear_v1("evaluar-ir", tmp_path)  # sin promoción no hace nada
    P.promover(tmp_path)
    with pytest.raises(SystemExit, match="v1.0-entrega"):
        P.bloquear_v1("evaluar-ir", tmp_path)


def test_condicion_2_con_la_raiz_v2(tmp_path):
    _repo(tmp_path)
    P.promover(tmp_path)
    cx = SimpleNamespace(raiz=tmp_path)
    assert W.raiz_c02(cx).estado == OK
    (tmp_path / "salida" / "v2" / "gold_entidades.csv").write_text("passage_id,tipo\nx\n")
    (tmp_path / "gold_entidades.csv").write_text("passage_id,tipo\nx\n")
    r = W.raiz_c02(cx)
    assert r.estado == FALLA and any("columnas" in d for d in r.detalle)


def test_validar_cambia_2_a_8_por_las_de_la_raiz_v2(tmp_path, monkeypatch):
    from mtx import entrega

    _repo(tmp_path)
    P.promover(tmp_path)
    llamadas = []
    for n in W.RAIZ_V2:
        monkeypatch.setitem(W.RAIZ_V2, n, lambda cx, n=n: llamadas.append(n) or
                            entrega.Resultado(n, "v2", OK, []))
    cx = entrega.Contexto(SimpleNamespace(dir_raiz=tmp_path), correr_pruebas=False)
    res = entrega.validar(cx, solo=set(range(2, 9)))
    assert sorted(llamadas) == list(range(2, 9)) and all(r.titulo == "v2" for r in res)


def test_excepcion_de_la_condicion_12(tmp_path, monkeypatch):
    from mtx import entrega

    (tmp_path / "laminas").mkdir()
    (tmp_path / "laminas" / "guion.md").write_text("# Guion v1\n")
    (tmp_path / "laminas" / "laminas.pptx").write_text("x")
    (tmp_path / "docs").mkdir()
    dec = tmp_path / "docs" / "decisiones.md"
    dec.write_text("- Más de 5 láminas por decisión del alumno\n")
    monkeypatch.setattr("pptx.Presentation", lambda ruta: SimpleNamespace(slides=[1] * 12))
    cx = entrega.Contexto(SimpleNamespace(dir_raiz=tmp_path), correr_pruebas=False)
    assert entrega.c12_laminas(cx).estado == FALLA
    dec.write_text(dec.read_text() + f"- {entrega.EXCEPCION_12}: el guion v1 no se cronometró\n")
    r = entrega.c12_laminas(cx)
    assert r.estado == OK and "condición 22" in r.detalle[0]
