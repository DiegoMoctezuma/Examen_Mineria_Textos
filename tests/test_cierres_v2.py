"""Cierres humanos v2 (PRD v2 §4, D24, D31 a D34): `cierre_juicios_v2.json` y
`cierre_gold_v2.json`. Todo en carpetas temporales con datos sintéticos; git simulado. Nunca toca
`anotaciones/`, `config/` ni `data/`."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from mtx import cierres_v2 as K
from mtx import gold_v2 as V


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


@pytest.fixture
def git_limpio(monkeypatch, tmp_path):
    """Git simulado: todo commiteado, `v2-inicio` → `reglas-fecha-v2` → modelo NER v2."""
    commits = {"v2-inicio": "c1", V.ETIQUETA_FECHA: "c2"}
    modelo = tmp_path / "modelo_ner.json"
    modelo.write_text(json.dumps({"modelo": "m/x", "revision": "r1"}), encoding="utf-8")
    monkeypatch.setattr(K, "MODELO_NER", modelo)
    monkeypatch.setattr(K, "sin_commitear", lambda rutas: [])
    monkeypatch.setattr(K, "commit_actual", lambda: "c9")
    monkeypatch.setattr(K, "commit_de_etiqueta", lambda n: commits.get(n))
    monkeypatch.setattr(K, "ultimo_commit_de", lambda r: "c3")
    monkeypatch.setattr(K, "es_ancestro", lambda a, b: a <= b)
    return commits


# =========================================================================== juicios


@pytest.fixture
def juicios(tmp_path, monkeypatch):
    anot = tmp_path / "anotaciones"
    (anot / "juicios_v2").mkdir(parents=True)
    monkeypatch.setenv("MTX_ANOTACIONES", str(anot))
    pas = pd.DataFrame([{"passage_id": f"{d}_0", "texto": f"texto {d}"} for d in (1, 2, 3)])
    filas = []
    for lote, jueces, origen, pids in (("1", ("diego", "luis", "arturo"), "v1", ("1_0", "2_0")),
                                       ("2", ("arturo", "gonzalo", "leo"), "app", ("3_0",))):
        for a in jueces:
            for orden, pid in enumerate(pids):
                filas.append({"lote": lote, "anotador": a, "origen": origen, "orden": str(orden),
                              "query_id": "Q1", "doc_id": pid.split("_")[0], "passage_id": pid,
                              "texto_sha256": _sha(f"texto {pid.split('_')[0]}")})
    asig = pd.DataFrame(filas, dtype=str)
    rutas = {n: tmp_path / n for n in ("asignacion.csv", "anotadores.yaml", "criterios.md")}
    for r in rutas.values():
        r.write_text("x", encoding="utf-8")
    return anot, asig, pas, rutas


def _juzgar(anot: Path, quien: str, valores: dict[str, str]) -> None:
    filas = [{"query_id": "Q1", "doc_id": pid.split("_")[0], "passage_id": pid, "relevante": v}
             for pid, v in valores.items()]
    pd.DataFrame(filas).to_csv(anot / "juicios_v2" / f"{quien}.csv", index=False,
                               lineterminator="\n")


def _todos(anot: Path) -> None:
    for a in ("diego", "luis", "arturo"):
        _juzgar(anot, a, {"1_0": "1", "2_0": "0"} | ({"3_0": "1"} if a == "arturo" else {}))
    for a in ("gonzalo", "leo"):
        _juzgar(anot, a, {"3_0": "0"})


def _cerrar_juicios(anot, asig, pas, rutas, **kw):
    return K.cerrar_juicios_v2(asig, pas, rutas["asignacion.csv"], rutas["anotadores.yaml"],
                               rutas["criterios.md"], {"sha256_pool": "p"}, anot, **kw)


def test_juicios_completos_se_cierran_una_sola_vez(juicios, git_limpio):
    anot, asig, pas, rutas = juicios
    _todos(anot)
    assert K.revisar_juicios_v2(asig, pas, anot).ok
    assert not K.juicios_cerrados(anot)
    c = _cerrar_juicios(anot, asig, pas, rutas)
    assert K.juicios_cerrados(anot)
    assert c["pares"] == 3 and c["pares_cerrados"] == 3 and c["pares_sin_cerrar"] == []
    assert c["pares_por_lote"] == {"1": 2, "2": 1} and c["commit"] == "c9"
    assert c["jueces"]["arturo"]["lotes"] == ["1", "2"] and c["jueces"]["arturo"]["juzgados"] == 3
    assert c["jueces"]["leo"]["sha256"] == K._sha(anot / "juicios_v2" / "leo.csv")
    disco = json.loads(K.ruta_cierre_juicios(anot).read_text(encoding="utf-8"))
    assert disco == c
    with pytest.raises(ValueError, match="no se reescribe"):
        _cerrar_juicios(anot, asig, pas, rutas)


def test_omitido_no_cuenta_y_el_par_no_se_cierra(juicios, git_limpio):
    anot, asig, pas, rutas = juicios
    _todos(anot)
    _juzgar(anot, "leo", {"3_0": ""})  # omitido por ahora
    rev = K.revisar_juicios_v2(asig, pas, anot)
    assert not rev.ok and any("1 de 3 pares con menos de 3" in e for e in rev.errores)
    with pytest.raises(ValueError, match="menos de 3"):
        _cerrar_juicios(anot, asig, pas, rutas)
    assert not K.juicios_cerrados(anot)
    c = _cerrar_juicios(anot, asig, pas, rutas, aceptar_incompletos=True)
    assert c["pares_sin_cerrar"] == [{"query_id": "Q1", "passage_id": "3_0"}]
    assert c["pares_cerrados"] == 2 and c["aceptar_incompletos"] and c["avisos"]


@pytest.mark.parametrize("dano,mensaje", [
    (lambda anot: (anot / "juicios_v2" / "gonzalo.csv").unlink(), "no existe gonzalo.csv"),
    (lambda anot: _juzgar(anot, "leo", {"3_0": "2"}), "fuera de"),
    (lambda anot: _juzgar(anot, "leo", {"3_0": "1", "1_0": "1"}), "fuera del pool"),
])
def test_archivos_mal_formados_bloquean(juicios, git_limpio, dano, mensaje):
    anot, asig, pas, rutas = juicios
    _todos(anot)
    dano(anot)
    rev = K.revisar_juicios_v2(asig, pas, anot)
    assert any(mensaje in e for e in rev.errores), rev.errores


def test_texto_cambiado_y_jueces_de_menos_bloquean(juicios, git_limpio):
    anot, asig, pas, rutas = juicios
    _todos(anot)
    pas.loc[pas["passage_id"] == "3_0", "texto"] = "otro texto"
    rev = K.revisar_juicios_v2(asig, pas, anot)
    assert any("cambiaron de texto" in e for e in rev.errores)
    menos = asig[~((asig["anotador"] == "leo"))]
    rev = K.revisar_juicios_v2(menos, pas, anot)
    assert any("sin 3 jueces" in e for e in rev.errores)


def test_juicios_sin_commitear_no_se_cierran(juicios, git_limpio, monkeypatch):
    anot, asig, pas, rutas = juicios
    _todos(anot)
    monkeypatch.setattr(K, "sin_commitear", lambda rutas: ["anotaciones/juicios_v2/leo.csv"])
    with pytest.raises(ValueError, match="Sin commitear"):
        _cerrar_juicios(anot, asig, pas, rutas)
    assert not K.juicios_cerrados(anot)


# =========================================================================== gold

TEXTO = "El IMSS pagó 20 mil millones de pesos en Tabasco el 15 de enero de 2021."
CONFIG = {
    "anotadores": [{"id": i, "nombre": i.title()} for i in ("diego", "gonzalo", "arturo", "leo")],
    "gold": {"no_anotan": ["leo"], "pasada_2_sin_etiqueta": True, "partes": {
        "seleccion": {"nombre": "Selección", "manifiesto": "v2/muestra_seleccion.csv",
                      "anotadores": ["diego", "arturo"], "adjudicador": "gonzalo",
                      "pasadas": [1, 2]}}},
}


def _span(s: str) -> tuple[int, int]:
    i = TEXTO.index(s)
    return i, i + len(s)


@pytest.fixture
def gold(tmp_path, monkeypatch):
    anot = tmp_path / "anotaciones"
    (anot / "v2").mkdir(parents=True)
    monkeypatch.setenv("MTX_ANOTACIONES", str(anot))
    ruta_cfg = tmp_path / "anotadores.yaml"
    ruta_cfg.write_text(yaml.safe_dump(CONFIG, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv("MTX_ANOTADORES", str(ruta_cfg))
    pas, filas = [], []
    for q in (1, 2):
        pid, t = f"{q}_0", f"{TEXTO} {q}"
        filas.append({"query_id": f"Q{q}", "passage_id": pid, "doc_id": q,
                      "texto_sha256": _sha(t), "semilla": 42, "version_muestra": 1})
        pas.append({"passage_id": pid, "texto": t, "texto_sha256": _sha(t)})
    pd.DataFrame(filas).to_csv(anot / "v2" / "muestra_seleccion.csv", index=False)
    otros = {n: tmp_path / n for n in ("criterios.md", "muestreo.json")}
    for r in otros.values():
        r.write_text("x", encoding="utf-8")
    return V.cargar_config(), anot, pd.DataFrame(pas), ruta_cfg, otros


def _anotar(cfg, anot, pas, quien, pid, pasada, ents):
    p = pas.set_index("passage_id")
    s = V.SesionAnotador(anot, quien, cfg)
    for tipo, frag in ents:
        s.agregar(s.token(), pid, pasada, p.at[pid, "texto"], p.at[pid, "texto_sha256"], tipo,
                  *_span(frag))
    s.marcar(s.token(), pid, pasada, p.at[pid, "texto_sha256"], True)


def _completar(cfg, anot, pas):
    """Dos pasadas anotadas por Diego y Arturo; Gonzalo incluye el LOC que solo propuso Arturo."""
    p = pas.set_index("passage_id")
    for pid in ("1_0", "2_0"):
        _anotar(cfg, anot, pas, "diego", pid, 1, [("ORG", "IMSS")])
        _anotar(cfg, anot, pas, "arturo", pid, 1, [("ORG", "IMSS"), ("LOC", "Tabasco")])
        for quien in ("diego", "arturo"):
            _anotar(cfg, anot, pas, quien, pid, 2, [("FECHA", "15 de enero de 2021")])
    s = V.SesionAdjudicador(anot, "gonzalo", cfg)
    for pid in ("1_0", "2_0"):
        texto, sha = p.at[pid, "texto"], p.at[pid, "texto_sha256"]
        s.decidir(s.token(), pid, 1, sha, "LOC", *_span("Tabasco"), "arturo", V.INCLUIR)
        for pasada in (1, 2):
            s.marcar(s.token(), pid, pasada, sha, texto, True)


def _cerrar_gold(cfg, anot, pas, ruta_cfg, otros):
    return K.cerrar_gold_v2(cfg, pas, ruta_cfg, otros["criterios.md"], otros["muestreo.json"],
                            anot)


def test_gold_completo_escribe_adjudicado_y_cierre(gold, git_limpio):
    cfg, anot, pas, ruta_cfg, otros = gold
    _completar(cfg, anot, pas)
    assert not K.gold_cerrado(anot)
    c = _cerrar_gold(cfg, anot, pas, ruta_cfg, otros)
    assert K.gold_cerrado(anot)
    adj = pd.read_csv(K.ruta_adjudicado(anot), dtype={"passage_id": str})
    assert list(adj.columns) == ["parte"] + V.COLUMNAS_GOLD
    assert len(adj) == 6 and set(adj["tipo"]) == {"ORG", "LOC", "FECHA"}
    assert (adj["texto"] == [t[i:f] for t, i, f in zip(
        pas.set_index("passage_id").loc[adj["passage_id"], "texto"], adj["inicio"],
        adj["fin"])]).all()
    s = c["partes"]["seleccion"]
    assert s["pasajes"] == 2 and s["pasajes_con_entidades"] == 2 and s["entidades"] == 6
    assert s["entidades_por_tipo"] == {"FECHA": 2, "LOC": 2, "ORG": 2}
    assert c["commit_reglas_fecha_v2"] == "c2" and c["commit_modelo_ner"] == "c3"
    assert c["modelo_ner"] == "m/x" and c["sha256_adjudicado"] == K._sha(K.ruta_adjudicado(anot))
    assert {Path(r).name for r in c["archivos"]} == {
        "diego.csv", "diego_estado.csv", "arturo.csv", "arturo_estado.csv",
        "adjudicado_gonzalo.csv", "adjudicado_gonzalo_estado.csv"}
    with pytest.raises(ValueError, match="no se reescribe"):
        _cerrar_gold(cfg, anot, pas, ruta_cfg, otros)


def test_gold_sin_adjudicar_no_se_cierra(gold, git_limpio):
    cfg, anot, pas, ruta_cfg, otros = gold
    for pid in ("1_0", "2_0"):
        _anotar(cfg, anot, pas, "diego", pid, 1, [("ORG", "IMSS")])
        _anotar(cfg, anot, pas, "arturo", pid, 1, [("ORG", "IMSS")])
    rev = K.revisar_gold_v2(cfg, pas, anot)
    assert any("sin adjudicar" in e for e in rev.errores)
    assert any("pasada 2: cerrados 0 de 2" in e for e in rev.errores)
    with pytest.raises(ValueError, match="No se puede cerrar"):
        _cerrar_gold(cfg, anot, pas, ruta_cfg, otros)
    assert not K.gold_cerrado(anot) and not K.ruta_adjudicado(anot).exists()


@pytest.mark.parametrize("cambio,mensaje", [
    (lambda c, mp: c.pop(V.ETIQUETA_FECHA), "Falta la etiqueta `reglas-fecha-v2`"),
    (lambda c, mp: mp.setattr(K, "ultimo_commit_de", lambda r: "c1"), "no tiene un commit v2"),
    (lambda c, mp: mp.setattr(K, "ultimo_commit_de", lambda r: "c0"), "no tiene un commit v2"),
    (lambda c, mp: mp.setattr(K, "sin_commitear", lambda r: ["anotaciones/gold_v2/diego.csv"]),
     "Sin commitear"),
])
def test_orden_de_congelaciones_y_commits(gold, git_limpio, monkeypatch, cambio, mensaje):
    cfg, anot, pas, ruta_cfg, otros = gold
    _completar(cfg, anot, pas)
    cambio(git_limpio, monkeypatch)
    with pytest.raises(ValueError, match=mensaje):
        _cerrar_gold(cfg, anot, pas, ruta_cfg, otros)
    assert not K.gold_cerrado(anot)


def test_modulo_no_lee_predicciones():
    fuente = Path(K.__file__).read_text(encoding="utf-8").split('"""', 2)[2]
    for prohibido in ("DIR_SALIDA", "cache_ner", "ner_modelo", "fusion", "ranking"):
        assert prohibido not in fuente
