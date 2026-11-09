"""Gold (PRD §6.11, T10): búsqueda, validación en vivo, persistencia, `validar_gold()`, cierre y
modo ciego. Todo en carpetas temporales con textos sintéticos o pasajes fuera del ámbito de la IE;
nunca toca `anotaciones/` ni genera la muestra real."""
from __future__ import annotations

import hashlib
import json
import subprocess

import pandas as pd
import pytest

from mtx import config
from mtx import gold as G
from mtx.app import componentes as C

TEXTO = "SECRETARIO DE SALUD, JORGE ALCOCER VARELA: El IMSS pagó $500. Luego el IMSS (Pemex)."


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """20 pasajes sintéticos, 2 por consulta, con su manifiesto."""
    anot = tmp_path / "anotaciones"
    anot.mkdir()
    monkeypatch.setenv("MTX_ANOTACIONES", str(anot))
    monkeypatch.setattr(C, "reglas_congeladas", lambda: True)
    monkeypatch.setattr(G, "etiqueta_precede_al_gold", lambda ruta: None)
    filas, pas = [], []
    for q in range(1, 11):
        for k in range(2):
            pid = f"{q}_{k}"
            t = f"{TEXTO} Pasaje {pid}."
            filas.append({"query_id": f"Q{q}", "passage_id": pid, "doc_id": q,
                          "texto_sha256": _sha(t), "semilla": 42, "version_muestra": 1})
            pas.append({"passage_id": pid, "texto": t, "texto_sha256": _sha(t),
                        "inicio_cuerpo": TEXTO.index(":") + 2})
    r = G.rutas_gold()
    pd.DataFrame(filas).to_csv(r.muestra, index=False)
    return r, pd.DataFrame(pas)


# --------------------------------------------------------------------------- búsqueda y spans


def test_buscar_todas_las_apariciones_con_contexto():
    apar = G.buscar_apariciones(TEXTO, "IMSS")
    assert [(a["inicio"], a["fin"]) for a in apar] == [
        (i, i + 4) for i in (TEXTO.index("IMSS"), TEXTO.index("IMSS", TEXTO.index("IMSS") + 1))]
    assert all(TEXTO[a["inicio"]:a["fin"]] == "IMSS" for a in apar)
    assert len(apar[0]["antes"]) <= 40 and len(apar[0]["despues"]) <= 40
    assert G.buscar_apariciones(TEXTO, "") == [] and G.buscar_apariciones(TEXTO, "SAT") == []


@pytest.mark.parametrize("token,esperado", [("(Pemex).", "Pemex"), ("$500.", "$500"),
                                            ("«Tabasco»,", "Tabasco"), ("$", "$")])
def test_recortar_puntuacion_nunca_quita_el_signo_de_pesos(token, esperado):
    t = f"x {token} y"
    ini, fin = G.recortar_puntuacion(t, 2, 2 + len(token))
    assert t[ini:fin] == esperado


def test_validacion_en_vivo():
    filas = pd.DataFrame([{"passage_id": "p", "tipo": "ORG", "texto": "IMSS",
                           "inicio": TEXTO.index("IMSS"), "fin": TEXTO.index("IMSS") + 4}])
    i = TEXTO.index("IMSS")
    assert "Duplicado" in G.errores_span(TEXTO, filas, "ORG", i, i + 4)[0]
    assert "solapa" in G.errores_span(TEXTO, filas, "ORG", i - 3, i + 4)[0]
    assert "solapa" in G.errores_span(TEXTO, filas, "LOC", i + 1, i + 3)[0]  # anidada
    assert "espacio" in G.errores_span(TEXTO, filas.iloc[:0], "ORG", i - 1, i + 4)[0]
    assert "fuera de rango" in G.errores_span(TEXTO, filas, "ORG", 5, 5000)[0]
    assert "Tipo" in G.errores_span(TEXTO, filas.iloc[:0], "MISC", i, i + 4)[0]
    assert G.errores_span(TEXTO, filas, "ORG", i, i + 4, ignorar=0) == []


def test_spans_para_mostrar_marca_en_gris_alrededor_de_entidades():
    ic = TEXTO.index(":") + 2
    ini = TEXTO.index("JORGE")
    gp = pd.DataFrame([{"tipo": "PER", "inicio": ini, "fin": ini + 20}])
    spans = G.spans_para_mostrar(gp, ic)
    assert spans == [(0, ini, "marca"), (ini, ini + 20, "gold PER"), (ini + 20, ic, "marca")]
    C.html_desde_spans(TEXTO, spans)  # sin solapes


# --------------------------------------------------------------------------- persistencia


def test_agregar_cerrar_con_cero_entidades_y_reabrir_al_editar(mundo):
    r, pas = mundo
    t, sha = pas.at[0, "texto"], pas.at[0, "texto_sha256"]
    _, _, tok = G.cargar(r)
    tok = G.marcar(r, tok, "1_0", sha, True)  # cero entidades: válido
    _, est, _ = G.cargar(r)
    assert est.iloc[0][["estado", "n_entidades", "revision"]].tolist() == ["cerrado", 0, 1]
    i = t.index("IMSS")
    tok = G.agregar(r, tok, "1_0", t, sha, "ORG", i, i + 4)
    gold, est, _ = G.cargar(r)
    assert gold[["tipo", "texto"]].values.tolist() == [["ORG", "IMSS"]]
    assert est.iloc[0][["estado", "n_entidades", "revision"]].tolist() == ["abierto", 1, 2]
    assert r.gold.read_bytes()[:3] != b"\xef\xbb\xbf"
    assert list(pd.read_csv(r.gold).columns) == G.COLUMNAS_GOLD


def test_dos_pestanas_y_bloqueos(mundo, monkeypatch):
    r, pas = mundo
    t, sha = pas.at[0, "texto"], pas.at[0, "texto_sha256"]
    _, _, tok = G.cargar(r)
    i = t.index("IMSS")
    G.agregar(r, tok, "1_0", t, sha, "ORG", i, i + 4)
    with pytest.raises(C.ConflictoEdicion):
        G.agregar(r, tok, "1_0", t, sha, "PER", 0, 3)
    _, _, tok = G.cargar(r)
    with pytest.raises(ValueError, match="Duplicado"):
        G.agregar(r, tok, "1_0", t, sha, "ORG", i, i + 4)
    monkeypatch.setattr(C, "reglas_congeladas", lambda: False)
    with pytest.raises(ValueError, match="reglas-congeladas"):
        G.marcar(r, tok, "1_0", sha, True)


def test_reemplazar_pasaje_edita_tipo_limites_y_borra(mundo):
    r, pas = mundo
    t, sha = pas.at[0, "texto"], pas.at[0, "texto_sha256"]
    _, _, tok = G.cargar(r)
    i = t.index("IMSS")
    j = t.index("Pemex")
    tok = G.agregar(r, tok, "1_0", t, sha, "ORG", i, i + 4)
    tok = G.agregar(r, tok, "1_0", t, sha, "LOC", j, j + 5)
    tok = G.reemplazar_pasaje(r, tok, "1_0", t, sha, [{"tipo": "ORG", "inicio": j, "fin": j + 5}])
    gold, _, _ = G.cargar(r)
    assert gold[["tipo", "texto"]].values.tolist() == [["ORG", "Pemex"]]
    with pytest.raises(ValueError):
        G.reemplazar_pasaje(r, tok, "1_0", t, sha, [{"tipo": "ORG", "inicio": j, "fin": j + 5},
                                                     {"tipo": "LOC", "inicio": j, "fin": j + 2}])


# --------------------------------------------------------------------------- validar y cerrar (T10)


def _cerrar_todos(r, pas, con_entidad=("1_0",)):
    _, _, tok = G.cargar(r)
    for f in pas.itertuples(index=False):
        if f.passage_id in con_entidad:
            i = f.texto.index("IMSS")
            tok = G.agregar(r, tok, f.passage_id, f.texto, f.texto_sha256, "ORG", i, i + 4)
        tok = G.marcar(r, tok, f.passage_id, f.texto_sha256, True)


def test_validar_gold_t10_pasajes_sin_entidades_son_validos(mundo, tmp_path):
    r, pas = mundo
    v = G.validar_gold(r, pas)
    assert not v.ok and any("cerrados: 0 de 20" in e for e in v.errores)
    _cerrar_todos(r, pas)
    v = G.validar_gold(r, pas)
    assert v.ok, v.errores
    assert v.cerrados == 20 and v.pasajes_con_entidades == 1
    assert any("19 pasajes cerrados sin entidades" in a for a in v.avisos)
    cierre = G.cerrar_gold(r, pas, raiz=tmp_path)
    datos = json.loads(r.cierre.read_text())
    assert datos["pasajes"] == 20 and datos["entidades"] == 1 == cierre["entidades"]
    assert (tmp_path / "gold_entidades.csv").read_bytes() == r.gold.read_bytes()
    _, _, tok = G.cargar(r)
    with pytest.raises(ValueError, match="cerrado"):
        G.marcar(r, tok, "1_0", pas.at[0, "texto_sha256"], False)


def test_validar_gold_detecta_hash_cambiado_y_seleccion_no_disjunta(mundo):
    r, pas = mundo
    _cerrar_todos(r, pas)
    pas2 = pas.copy()
    pas2.loc[0, "texto_sha256"] = "otro"
    assert any("cambió desde el sorteo" in e for e in G.validar_gold(r, pas2).errores)
    pd.read_csv(r.muestra).head(1).to_csv(r.seleccion, index=False)
    assert any("disjunta" in e for e in G.validar_gold(r, pas).errores)


def test_cerrar_gold_invalido_no_escribe(mundo, tmp_path):
    r, pas = mundo
    with pytest.raises(ValueError):
        G.cerrar_gold(r, pas, raiz=tmp_path)
    assert not r.cierre.exists() and not (tmp_path / "gold_entidades.csv").exists()


def test_etiqueta_debe_preceder_al_primer_commit_del_gold(tmp_path, monkeypatch):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "a.txt").write_text("x")
    git("add", ".")
    git("commit", "-qm", "base")
    monkeypatch.setattr(config, "RAIZ", tmp_path)
    ruta = tmp_path / "gold_entidades.csv"
    assert "Falta la etiqueta" in G.etiqueta_precede_al_gold(ruta)
    git("tag", "reglas-congeladas")
    assert G.etiqueta_precede_al_gold(ruta) is None
    ruta.write_text("passage_id,tipo,texto,inicio,fin\n")
    git("add", ".")
    git("commit", "-qm", "gold")
    assert G.etiqueta_precede_al_gold(ruta) is None
    git("tag", "-d", "reglas-congeladas")
    git("tag", "reglas-congeladas")  # ahora apunta después del gold
    assert "no precede" in G.etiqueta_precede_al_gold(ruta)


# --------------------------------------------------------------------------- app (modo ciego)


def _app_gold():
    from mtx.app import vista_gold
    vista_gold.mostrar()


@pytest.mark.skipif(not config.PASAJES_PARQUET.exists(), reason="requiere make corpus")
def test_app_gold_bloqueada_sin_congelar_y_ciega(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    from mtx import ambito
    anot = tmp_path / "anotaciones"
    anot.mkdir()
    monkeypatch.setenv("MTX_ANOTACIONES", str(anot))
    monkeypatch.setattr(C, "reglas_congeladas", lambda: False)
    at = AppTest.from_function(_app_gold, default_timeout=60).run()
    assert not at.exception and "make congelar" in at.warning[0].value

    # Manifiesto con pasajes FUERA del ámbito de la IE (no es la muestra real)
    p = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto_sha256"])
    fuera = p[~p["passage_id"].isin(set(ambito.ambito_ie()["passage_id"]))].sample(
        20, random_state=1)
    man = fuera.assign(query_id=[f"Q{i // 2 + 1}" for i in range(20)], doc_id=0, semilla=42,
                       version_muestra=1)
    man[["query_id", "passage_id", "doc_id", "texto_sha256", "semilla",
         "version_muestra"]].to_csv(anot / "muestra_gold.csv", index=False)
    monkeypatch.setattr(C, "reglas_congeladas", lambda: True)
    at = AppTest.from_function(_app_gold, default_timeout=60).run()
    assert not at.exception
    visible = " ".join(m.value for m in at.markdown).lower()
    for oculto in ("confianza", "bert", "gazetteer_", "regex_", "metodo", "entidades_"):
        assert oculto not in visible
    assert "0 entidades" in visible


@pytest.mark.skipif(not config.PASAJES_PARQUET.exists(), reason="requiere make corpus")
def test_app_gold_buscar_elegir_aparicion_agregar_y_cerrar(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    from mtx import ambito
    anot = tmp_path / "anotaciones"
    anot.mkdir()
    monkeypatch.setenv("MTX_ANOTACIONES", str(anot))
    monkeypatch.setattr(C, "reglas_congeladas", lambda: True)
    p = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto", "texto_sha256"])
    fuera = p[~p["passage_id"].isin(set(ambito.ambito_ie()["passage_id"]))]
    # pasaje de desarrollo con una palabra repetida (fuera del ámbito de la IE)
    con_rep = fuera[fuera["texto"].str.count(r"\bMéxico\b") >= 2].head(1)
    resto = fuera[~fuera["passage_id"].isin(con_rep["passage_id"])].sample(19, random_state=2)
    man = pd.concat([con_rep, resto]).assign(
        query_id=[f"Q{i // 2 + 1}" for i in range(20)], doc_id=0, semilla=42, version_muestra=1)
    man[["query_id", "passage_id", "doc_id", "texto_sha256", "semilla",
         "version_muestra"]].to_csv(anot / "muestra_gold.csv", index=False)
    pid, texto = con_rep.iloc[0]["passage_id"], con_rep.iloc[0]["texto"]

    at = AppTest.from_function(_app_gold, default_timeout=60).run()
    at.text_input(key="buscar_texto").input("México").run()
    assert at.button(key="agregar_b").disabled  # sin tipo ni aparición elegidos
    at.selectbox(key="tipo_busqueda").select("LOC").run()
    radio = at.radio(key="aparicion")
    assert len(radio.options) == texto.count("México") and radio.value is None
    radio.set_value(1).run()
    at.button(key="agregar_b").click().run()
    assert not at.exception
    g = pd.read_csv(anot / "gold_entidades.csv")
    segunda = texto.find("México", texto.find("México") + 1)
    assert g[["passage_id", "tipo", "texto", "inicio", "fin"]].values.tolist() == [
        [pid, "LOC", "México", segunda, segunda + 6]]
    at.button[[b.label for b in at.button].index("Pasaje revisado completo")].click().run()
    est = pd.read_csv(anot / "estado_gold.csv")
    assert est[["passage_id", "estado", "n_entidades"]].values.tolist() == [[pid, "cerrado", 1]]
