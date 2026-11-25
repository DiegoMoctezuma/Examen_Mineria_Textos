"""Pruebas de la demo web (PRD v2 WP-15): HTML sin IDs ni rutas, resaltado desde offsets sin
solapes, contexto del discurso y carga de artefactos v1. Sin red."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from mtx import config
from mtx.web import componentes as C
from mtx.web import datos as D
from mtx.web import resumen

ID_VISIBLE = re.compile(r"\b\d+_\d+\b")


def fila(texto="PRESIDENTE: Hola <b>& México 🇲🇽 y Pemex.", ic=12, **kw):
    base = {"passage_id": "77_4", "doc_id": 77, "titulo": "01.02.21 Versión estenográfica de la "
            "conferencia de prensa matutina del presidente Andrés Manuel López Obrador",
            "fecha": pd.Timestamp("2021-02-01"), "posicion": 4,
            "interlocutor": "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR", "es_reportero": False,
            "url": "https://ejemplo.mx/x", "texto": texto, "inicio_cuerpo": ic}
    base.update(kw)
    return pd.Series(base)


def ents(*filas):
    return pd.DataFrame(filas, columns=["passage_id", "tipo", "texto", "inicio", "fin", "metodo"])


def sin_etiquetas(h: str) -> str:
    return re.sub(r"<[^>]+>", " ", h)


def test_resaltado_respeta_offsets_con_caracteres_especiales():
    f = fila()
    t = f["texto"]
    i = t.index("México")
    j = t.index("Pemex")
    h = C.html_cuerpo(t, 12, ents(("77_4", "LOC", "México", i, i + 6, "regla"),
                                  ("77_4", "ORG", "Pemex", j, j + 5, "ambos")))
    assert '<mark class="ent e-LOC">México</mark>' in h
    assert '<mark class="ent e-ORG">Pemex</mark>' in h
    assert "&lt;b&gt;&amp;" in h and "<b>" not in h
    assert "PRESIDENTE" not in h          # la marca del interlocutor no se muestra


def test_spans_solapados_se_resuelven_sin_error():
    t = "X: El Tren Maya avanza."
    i = t.index("Tren Maya")
    e = ents(("1_0", "LOC", "Tren Maya", i, i + 9, "regla"),
             ("1_0", "ORG", "Tren Maya", i, i + 9, "ambos"),
             ("1_0", "LOC", "Maya", i + 5, i + 9, "modelo"),
             ("1_0", "PER", "X", 0, 1, "modelo"))           # en la marca: se descarta
    spans = C.spans_entidades(e, 3)
    assert spans == [(i - 3, i + 6, "ent e-ORG")]
    C.html_cuerpo(t, 3, e)                                    # no lanza


def test_tarjeta_sin_ids_y_con_contexto(monkeypatch):
    monkeypatch.setattr(resumen, "idf_indice", dict)
    antes = fila(texto="VOZ: antes 12_3 no", ic=5, passage_id="77_3", posicion=3,
                 interlocutor="VOZ MUJER")
    h = C.tarjeta_pasaje(fila(), contexto=(antes, None))
    visible = sin_etiquetas(h)
    assert "77_4" not in h and "77_3" not in h
    assert "Mañanera del 1 de febrero de 2021 · fragmento 5" in visible
    assert "Antes · fragmento 4 · Participante sin identificar" in visible
    assert "Ver contexto" in visible and "Después" not in visible
    assert "Frase representativa" in visible and "Leer completo" in visible


def test_frase_representativa_elige_la_oracion_central():
    from mtx import preproceso

    texto = ("VOZ: Buenos días a todos los presentes en este lugar tan bonito hoy. "
             "La refinería de Dos Bocas procesará petróleo crudo para producir gasolinas. "
             "El petróleo crudo y las gasolinas son la base de la refinería nueva. Gracias.")
    idf = {t: 1.0 for t in preproceso.tokenizar(texto, "stem")}
    frase = resumen.frase_representativa(texto, 5, idf)
    assert frase.startswith("La refinería de Dos Bocas")
    assert frase in " ".join(texto.split())            # cita textual


def test_frase_representativa_recorta_y_tiene_respaldo():
    largo = "VOZ: " + " ".join(f"palabra{i}" for i in range(60)) + "."
    frase = resumen.frase_representativa(largo, 5, {})
    assert frase.endswith("…") and len(frase.split()) == resumen.MAX_PALABRAS
    corto = "VOZ: Sí, claro."
    assert resumen.frase_representativa(corto, 5, {}) == "Sí, claro."


def test_tarjeta_mini_y_renglon_respuesta():
    h = C.tarjeta_mini(fila(), 2, en_ambos=True)
    assert "en los dos" in h and "77_4" not in h
    r = C.renglon_respuesta(["Reforma", "El Universal"], "", "respaldado_en_texto",
                            "medios como Reforma, El Universal <y> otros", "Mañanera", "Prensa", 3)
    assert "<strong>Reforma</strong>" in r and "<strong>El Universal</strong>" in r
    assert "&lt;y&gt;" in r and "mencionado en 3 discursos" in r


def test_tarjeta_campo_oculta_los_sobrantes():
    h = C.tarjeta_campo("montos", ["<div>a</div>"], ["<div>b</div>", "<div>c</div>"])
    assert "Montos" in h and "Ver 2 valores más" in h
    assert "Sin evidencia" in C.tarjeta_campo("montos", [])


def test_bloqueo_de_la_muestra_v2(tmp_path):
    (tmp_path / "anotaciones" / "v2").mkdir(parents=True)
    (tmp_path / "anotaciones" / "v2" / "muestra_gold_b.csv").write_text(
        "query_id,passage_id\nQ11,5_1\n", encoding="utf-8")
    assert D.pasajes_bloqueados(tmp_path) == {"5_1"}
    assert D.version_datos(tmp_path) == "v1"
    for nombre in ("cierre_juicios_v2.json", "cierre_gold_v2.json"):
        (tmp_path / "anotaciones" / nombre).write_text("{}", encoding="utf-8")
    assert D.pasajes_bloqueados(tmp_path) == frozenset()
    assert D.version_datos(tmp_path) == "v2"


def test_version_forzada_a_v1(tmp_path, monkeypatch):
    (tmp_path / "anotaciones").mkdir()
    for nombre in ("cierre_juicios_v2.json", "cierre_gold_v2.json"):
        (tmp_path / "anotaciones" / nombre).write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MTX_DEMO_VERSION", "v1")
    assert D.version_datos(tmp_path) == "v1"


requiere_datos = pytest.mark.skipif(not config.PASAJES_PARQUET.exists(),
                                    reason="Sin data/pasajes.parquet (correr `make corpus`)")


@requiere_datos
def test_artefactos_v1_y_contexto(monkeypatch):
    monkeypatch.delenv("MTX_DEMO_RAIZ", raising=False)
    a = D.cargar_v1()
    assert list(a.consultas["query_id"]) == [f"Q{i}" for i in range(1, 11)]
    assert set(a.ranking["modelo"]) == {"tfidf", "bm25"} and a.mejor in D.MODELOS
    assert a.ner_libre                                 # v1: mrm8488 en la consulta libre
    for q in a.consultas["query_id"]:
        assert len(a.top(q, "bm25")) == 10 and len(a.top(q, "tfidf")) == 10
    pid = a.top("Q3", a.mejor)["passage_id"].iloc[0]
    antes, despues = a.contexto(pid)
    actual = a.pasajes.loc[pid]
    for vecino in (antes, despues):
        if vecino is not None:
            assert vecino["doc_id"] == actual["doc_id"]
    if antes is not None:
        assert antes["posicion"] < actual["posicion"]
    if despues is not None:
        assert despues["posicion"] > actual["posicion"]


def _pagina_consultas():
    from mtx.web import vistas
    vistas.consultas()


def _pagina_como_funciona():
    from mtx.web import vistas
    vistas.como_funciona()


def _visible(at) -> str:
    assert not at.exception, [x.value for x in at.exception]
    return sin_etiquetas(" ".join(m.value for m in at.markdown))


@requiere_datos
def test_paginas_sin_ids_ni_rutas():
    from streamlit.testing.v1 import AppTest

    paginas = [AppTest.from_file(str(config.RAIZ / "src/mtx/web/app.py"), default_timeout=120),
               AppTest.from_function(_pagina_como_funciona, default_timeout=60)]
    for q in ("Q1", "Q3", "Q8"):
        at = AppTest.from_function(_pagina_consultas, default_timeout=120)
        at.query_params["q"] = q
        paginas.append(at)
    for at in paginas:
        visible = _visible(at.run())
        assert not ID_VISIBLE.search(visible), ID_VISIBLE.search(visible)
        assert "salida/" not in visible and ".csv" not in visible


# --------------------------------------------------------------------------- consulta libre

class BuscadorFalso:
    """Devuelve 15 pasajes ordenados; los de puntaje 0 al final."""

    def __init__(self, ceros: int = 0, tokens=("gasolin",)):
        self.ceros, self.tokens = ceros, list(tokens)

    def buscar(self, consulta, desde, hasta, modelo, k):
        n = 15
        punt = [float(n - i) if i < n - self.ceros else 0.0 for i in range(n)]
        tabla = pd.DataFrame({"rango": range(1, n + 1),
                              "passage_id": [f"{i}_0" for i in range(n)],
                              "puntaje": punt, "sin_senal_lexica": [int(p == 0) for p in punt]})
        return tabla.head(k), {"tokens": self.tokens, "elegibles": 500}


def test_libre_salta_bloqueados_y_rellena():
    from mtx.web import libre as L

    r = L.buscar(BuscadorFalso(), "gasolina", bloqueados=frozenset({"1_0", "3_0", "14_0"}))
    for m in ("tfidf", "bm25"):
        ids = list(r.tops[m]["passage_id"])
        assert len(ids) == 10 and not {"1_0", "3_0"} & set(ids)
        assert list(r.tops[m]["rango"]) == list(range(1, 11))
    assert r.ocultos == 2 and r.avisos == []        # 14_0 no habría salido entre los 10


def test_libre_sin_coincidencias_y_sin_terminos():
    from mtx.web import libre as L

    r = L.buscar(BuscadorFalso(ceros=15), "xyzzy")
    assert r.tops["bm25"].empty and r.avisos == [L.AVISOS["nada"]]
    r = L.buscar(BuscadorFalso(ceros=11), "algo raro")
    assert len(r.tops["bm25"]) == 4 and "Solo 4 fragmentos" in r.avisos[0]
    r = L.buscar(BuscadorFalso(tokens=()), "de la")
    assert r.avisos == [L.AVISOS["sin_terminos"]]


def test_libre_une_reglas_y_modelo_por_span():
    from types import SimpleNamespace

    from mtx.web import libre as L

    texto = "VOZ: Pemex invirtió en Tabasco."
    i, j = texto.index("Pemex"), texto.index("Tabasco")

    def reglas(t, ic):
        return [SimpleNamespace(tipo="ORG", inicio=i, fin=i + 5),
                SimpleNamespace(tipo="LOC", inicio=j, fin=j + 7)]

    def modelo(t, pid):
        return [{"tipo": "ORG", "inicio": i, "fin": i + 5}, {"tipo": "PER", "inicio": 0, "fin": 3}]

    e = L.entidades_pasaje("9_1", texto, 5, reglas, modelo)
    assert dict(zip(e["texto"], e["metodo"])) == {"VOZ": "modelo", "Pemex": "ambos",
                                                  "Tabasco": "regla"}
    assert C.spans_entidades(e, 5) == [(i - 5, i, "ent e-ORG"), (j - 5, j + 2, "ent e-LOC")]
    assert list(L.entidades_pasaje("9_1", texto, 5, reglas)["metodo"]) == ["regla", "regla"]


# --------------------------------------------------------------------------- arranque


def test_arranque_descarga_lo_que_falta_y_verifica(tmp_path, monkeypatch):
    import json
    import sys
    import types

    from mtx.web import arranque

    contenido = b"datos de prueba"
    import hashlib
    m = {"repo_id": "u/x", "revision": "abc", "archivos": {
        "data/a.bin": hashlib.sha256(contenido).hexdigest()}}
    man = tmp_path / "artefactos_demo.json"
    man.write_text(json.dumps(m), encoding="utf-8")
    llamadas = []

    def falso(repo_id, filename, repo_type, revision, local_dir):
        llamadas.append((repo_id, filename, repo_type, revision))
        destino = local_dir / filename
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido if revision == "abc" else b"otro")
        return str(destino)

    monkeypatch.setitem(sys.modules, "huggingface_hub",
                        types.SimpleNamespace(hf_hub_download=falso))
    assert arranque.asegurar_artefactos(tmp_path, man) == ["data/a.bin"]
    assert llamadas == [("u/x", "data/a.bin", "dataset", "abc")]
    assert arranque.asegurar_artefactos(tmp_path, man) == []          # ya existe: no baja
    (tmp_path / "data/a.bin").unlink()
    m["revision"] = "malo"
    man.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(RuntimeError, match="sha256"):
        arranque.asegurar_artefactos(tmp_path, man)
    assert not (tmp_path / "data/a.bin").exists()
    assert arranque.asegurar_artefactos(tmp_path, tmp_path / "no_existe.json") == []


# --------------------------------------------------------------------------- v2 y D32 en el contexto


def test_contexto_oculta_vecinos_bloqueados():
    vec = pd.DataFrame({"anterior": [None, "1_0", "1_1"], "siguiente": ["1_1", "1_2", None]},
                       index=["1_0", "1_1", "1_2"])
    pas = pd.DataFrame({"passage_id": ["1_0", "1_1", "1_2"]}).set_index("passage_id", drop=False)
    antes, despues = D.contexto("1_1", vec, pas)
    assert antes["passage_id"] == "1_0" and despues["passage_id"] == "1_2"
    antes, despues = D.contexto("1_1", vec, pas, frozenset({"1_2"}))
    assert antes["passage_id"] == "1_0" and despues is None


def _repo_v2(tmp_path, preprocesamiento="lema"):
    """Repo mínimo con las salidas v2 que lee la demo (contenido sintético)."""
    import json

    r = tmp_path
    for d in ("data/v2", "salida/v2", "anotaciones/v2"):
        (r / d).mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"passage_id": ["1_0", "1_1", "2_0"], "doc_id": [1, 1, 2],
                  "fecha": pd.to_datetime(["2020-01-01"] * 3), "titulo": ["t"] * 3,
                  "url": [""] * 3, "posicion": [0, 1, 0], "interlocutor": ["X"] * 3,
                  "es_reportero": [False] * 3, "texto": ["X: hola mundo"] * 3,
                  "inicio_cuerpo": [3] * 3}).to_parquet(r / "data/pasajes.parquet")
    (r / "data/consultas.csv").write_text(
        "query_id,consulta,desde,hasta,pregunta_extraccion\n"
        + "".join(f"Q{i},tema {i},2019-01-01,2020-12-31,qué\n" for i in range(1, 16)),
        encoding="utf-8")
    (r / "data/v2/mejor_modelo.json").write_text(json.dumps(
        {"modelo": "bm25_con_filtro", "preprocesamiento": preprocesamiento}), encoding="utf-8")
    (r / "data/modelo_ner.json").write_text(json.dumps({"slug": "xlmr_large_davlan"}), encoding="utf-8")
    filas = [{"query_id": "Q11", "modelo": f"{m}_con_filtro", "variante": "con_filtro",
              "rango": 1, "passage_id": "1_0", "puntaje": 1.0} for m in ("tfidf", "bm25")]
    pd.DataFrame(filas).to_csv(r / "salida/v2/ranking.csv", index=False)
    pd.DataFrame(columns=["query_id", "passage_id", "tipo", "texto", "inicio", "fin", "metodo"]
                 ).to_csv(r / "salida/v2/entidades.csv", index=False)
    pd.DataFrame({"query_id": ["Q11"], "campo_respuesta": ["c"], "passage_id": ["1_0"],
                  "estado": ["ambiguo"]}).to_csv(r / "salida/v2/respuestas.csv", index=False)
    pd.DataFrame({"query_id": ["Q11"]}).to_csv(r / "salida/v2/10_evidencias.csv", index=False)
    ir = pd.DataFrame({"query_id": ["Q1", "Q11"] + ["PROMEDIO (MAP = AP)"] * 2,
                       "modelo": ["bm25_con_filtro"] * 2 + ["tfidf_con_filtro", "bm25_con_filtro"],
                       "P@10": [0.9, 0.4, 0.4, 0.6], "AP": [0.8, 0.3, 0.3, 0.5]})
    ir.to_csv(r / "salida/v2/resultados_ir.csv", index=False)
    ie = pd.DataFrame({"metodo": ["regla", "modelo", "combinado"], "tipo": ["TODOS"] * 3,
                       "precision": [0.9] * 3, "recall": [0.6, 0.5, 0.8], "f1": [0.7, 0.6, 0.8]})
    ie.to_csv(r / "salida/v2/resultados_ie.csv", index=False)
    (r / "salida/01_limpieza.json").write_text(json.dumps(
        {"discursos": 3, "pasajes": 3, "palabras_por_pasaje_media": 2.0,
         "pasajes_de_reporteros_pct": 0.0}), encoding="utf-8")
    (r / "anotaciones/v2/muestra_gold_b.csv").write_text("query_id,passage_id\nQ11,1_1\n",
                                                         encoding="utf-8")
    return r


def test_cargar_v2_lee_salida_v2(tmp_path):
    r = _repo_v2(tmp_path)
    a = D.cargar_v2(r)
    assert a.version == "v2" and len(a.consultas) == 15
    assert a.mejor == "bm25" and a.raiz_indice == "lema" and a.ner_slug == "xlmr_large_davlan"
    assert not a.ner_libre                             # XLM-R large no cabe en la nube
    assert a.bloqueados == {"1_1"}                     # sin cierre del gold todavía
    assert a.contexto("1_0") == (None, None)           # su vecino 1_1 está bloqueado
    k = D.cifras(r, "v2")
    assert k["map"] == {"tfidf": 0.3, "bm25": 0.5} and k["f1"]["combinado"] == 0.8
    assert k["p10_consulta"] == {"tfidf": {}, "bm25": {"Q1": 0.9, "Q11": 0.4}}


def test_cargar_v2_avisa_lo_que_falta(tmp_path):
    r = _repo_v2(tmp_path)
    (r / "salida/v2/entidades.csv").unlink()
    with pytest.raises(FileNotFoundError, match="salida/v2/entidades.csv"):
        D.cargar_v2(r)


def test_version_v2_con_los_dos_cierres(tmp_path):
    r = _repo_v2(tmp_path, "stem")
    assert D.version_datos(r) == "v1"
    for nombre in ("cierre_juicios_v2.json", "cierre_gold_v2.json"):
        (r / "anotaciones" / nombre).write_text("{}", encoding="utf-8")
    a = D.cargar_artefactos(r)
    assert a.version == "v2" and a.raiz_indice == "stem" and a.bloqueados == frozenset()


def test_resumen_de_la_consulta_libre_sin_modelo():
    from mtx.web import vistas as V

    pas = pd.DataFrame({"inicio_cuerpo": [5]}, index=["9_1"])
    e = {"9_1": ents(("9_1", "ORG", "Pemex", 5, 10, "regla"))}
    assert "solo el modelo de lenguaje" in V.resumen_extraccion(e, pas)
    sin = V.resumen_extraccion(e, pas, con_modelo=False)
    assert "Todas salen de las reglas" in sin and "modelo" not in sin


def test_caso_dificil_con_cifras_de_los_archivos(tmp_path, monkeypatch):
    from mtx.web import vistas as V

    r = _repo_v2(tmp_path)
    monkeypatch.setattr(V, "DIFICIL", "Q11")
    h = V.caso_dificil(D.cargar_v2(r), D.cifras(r, "v2"))
    assert "9 de los 10" in h and "solo 4" in h and "1 de sus 1 datos" in h
    assert not ID_VISIBLE.search(h)
