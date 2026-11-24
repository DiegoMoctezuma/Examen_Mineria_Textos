"""WP-13: mapa de campos de Q11 a Q15 y valoraciones v2 por persona. Datos inventados."""
from __future__ import annotations

import importlib.util
import re

from mtx import config
from mtx import respuestas as RS


def _script():
    spec = importlib.util.spec_from_file_location("tablas10", config.RAIZ / "scripts" / "10_tablas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mapa_define_las_15_consultas_con_patrones_sin_acentos():
    mapa = RS.cargar_mapa(config.DIR_CONFIG / "tablas_respuesta.yaml")
    assert set(mapa) == {f"Q{i}" for i in range(1, 16)}
    for q in (f"Q{i}" for i in range(11, 16)):
        assert mapa[q], q
        for c in mapa[q]:
            assert c.fuente in ("entidad", "auxiliar") and c.relacion
            for p in c.patrones:
                assert p == p.lower() and not re.search(r"[áéíóúñü]", p), (q, c.campo, p)
                re.compile(p)


def test_valoraciones_v2_se_unen_por_persona_y_las_repetidas_quedan_pendientes(tmp_path, capsys):
    d = tmp_path / "valoraciones_v2"
    d.mkdir()
    RS.guardar_valoracion(d / "luis.yaml", "", "Q11", "Creíble.", "a" * 64)
    tok = RS.guardar_valoracion(d / "arturo.yaml", "", "Q12", "Le faltan montos.", "b" * 64)
    RS.guardar_valoracion(d / "arturo.yaml", tok, "Q11", "Otra opinión.", "a" * 64)
    v = _script().valoraciones_v2(tmp_path)
    assert set(v) == {"Q12"} and v["Q12"]["texto"] == "Le faltan montos."
    assert "Q11" in capsys.readouterr().out
