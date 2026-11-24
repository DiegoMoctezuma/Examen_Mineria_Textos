"""D32: la demo oculta los pasajes de la muestra v2 hasta `cierre_gold_v2.json`. Datos inventados."""
from __future__ import annotations

import importlib.util

import pandas as pd

from mtx import cierres_v2 as K
from mtx import config


def _anotaciones(tmp_path):
    (tmp_path / "v2").mkdir()
    for nombre, pid in (("muestra_seleccion", "1_1"), ("muestra_gold_a", "2_1"),
                        ("muestra_gold_b", "3_1")):
        pd.DataFrame({"query_id": ["Q1"], "passage_id": [pid], "doc_id": [pid[0]]}).to_csv(
            tmp_path / "v2" / f"{nombre}.csv", index=False)
    return tmp_path


def test_bloqueados_hasta_el_cierre_del_gold(tmp_path):
    d = _anotaciones(tmp_path)
    assert K.pasajes_bloqueados_v2(d) == {"1_1", "2_1", "3_1"}
    K.ruta_cierre_gold(d).parent.mkdir(parents=True, exist_ok=True)
    K.ruta_cierre_gold(d).write_text("{}")
    assert K.pasajes_bloqueados_v2(d) == set()


def test_demo_no_muestra_texto_ni_entidades_de_un_bloqueado(monkeypatch):
    spec = importlib.util.spec_from_file_location("demo13", config.RAIZ / "scripts" / "13_demo.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    monkeypatch.setattr(demo, "bloqueados", lambda: {"9_1"})
    pas = pd.DataFrame({"passage_id": ["8_1", "9_1"], "fecha": ["2020-01-01"] * 2,
                        "texto": ["Habló Ana.", "Texto secreto de Eva."], "inicio_cuerpo": [0, 0],
                        "interlocutor": ["X", "Y"]}).set_index("passage_id")
    ents = pd.DataFrame({"passage_id": ["9_1"], "tipo": ["PER"], "texto": ["Eva"],
                         "inicio": [17], "fin": [20], "metodo": ["modelo"]})
    with demo.con.capture() as cap:
        demo.mostrar_pasajes(["8_1", "9_1"], pas, ents, "prueba")
    salida = cap.get()
    assert "secreto" not in salida and "Eva" not in salida and "oculto" in salida
    assert "Habló Ana" in salida
