"""WP-10 (D34): adaptador spaCy, candidatos v2 y comparación sobre la selección. Sin red: modelos
simulados y frases inventadas."""
from __future__ import annotations

import re
from types import SimpleNamespace

import pandas as pd
import pytest

from mtx import comparacion_ner as C
from mtx import gold_v2 as V
from mtx import ner_modelo as N


def _cfg_spacy(**kw) -> N.ConfigModelo:
    base = {"slug": "sp", "repo_id": "es_falso", "revision": "3.8.0", "motor": "spacy",
            "licencia": "gpl-3.0", "mapa_etiquetas": {"PER": "PER", "ORG": "ORG", "LOC": "LOC"},
            "descartadas": ("MISC",)}
    base.update(kw)
    return N.ConfigModelo(**base)


class NlpFalso:
    """`nlp` falso: PER para palabras con mayúscula, MISC para «Mundial», LOC para «Tabasco»."""

    def __init__(self):
        self.llamadas = 0

    def __call__(self, texto):
        self.llamadas += 1
        ents = []
        for m in re.finditer(r"\b[A-ZÁÉÍÓÚÑ]\w+", texto):
            et = {"Mundial": "MISC", "Tabasco": "LOC"}.get(m.group(0), "PER")
            ents.append(SimpleNamespace(label_=et, start_char=m.start(), end_char=m.end()))
        return SimpleNamespace(ents=ents)


# --------------------------------------------------------------------------- adaptador spaCy


def test_spacy_offsets_de_caracter_y_posproceso():
    texto = "Ana viajó a Tabasco para el Mundial."
    crudas = N.inferir_pasaje(texto, NlpFalso(), None, _cfg_spacy())
    assert all(texto[c["inicio"]:c["fin"]] == c["texto"] for c in crudas)
    pp = N.posprocesar(texto, crudas, _cfg_spacy())
    assert [(e["tipo"], e["texto"]) for e in pp.entidades] == [("PER", "Ana"), ("LOC", "Tabasco")]
    assert pp.descartadas["MISC"] == 1


def test_spacy_usa_cache_por_modelo_y_version(tmp_path):
    pas = pd.DataFrame({"passage_id": ["1_1"], "texto": ["Habló Eva."], "texto_sha256": ["s1"]})
    nlp = NlpFalso()
    _, reg = N.ejecutar(_cfg_spacy(), pas, raiz=tmp_path, constructor=lambda c: (nlp, None))
    assert reg.inferidos == 1 and (tmp_path / "sp@3.8.0" / "1_1.json").exists()
    _, reg2 = N.ejecutar(_cfg_spacy(), pas, raiz=tmp_path, constructor=lambda c: (nlp, None))
    assert reg2.cacheados == 1 and nlp.llamadas == 1
    assert N.clave_cache(_cfg_spacy(revision="3.7.0"), "s1") != N.clave_cache(_cfg_spacy(), "s1")


def test_clave_de_transformers_conserva_las_claves_de_v1():
    c = N.ConfigModelo(slug="t", repo_id="a/b", revision="a" * 40, max_length_real=510,
                       ventana=480, solape=64)
    assert set(c.parametros_inferencia()) == {"repo_id", "revision", "tokenizador",
                                              "max_length_real", "ventana", "solape",
                                              "aggregation_strategy"}


# --------------------------------------------------------------------------- configuración


def test_config_spacy_sin_ventanas_y_motor_desconocido(tmp_path):
    ruta = tmp_path / "ner.yaml"
    ruta.write_text("principal: m\nmodelos:\n  m: {repo_id: a/b, revision: '" + "a" * 40 + "', "
                    "max_length_real: 510, ventana: 480, solape: 64}\n"
                    "  s: {motor: spacy, repo_id: es_x, revision: '3.8.0'}\n", encoding="utf-8")
    _, cfgs = N.cargar_config(ruta)
    assert cfgs["s"].motor == "spacy"
    ruta.write_text("principal: m\nmodelos:\n  m: {motor: onnx, repo_id: a/b, revision: x1}\n",
                    encoding="utf-8")
    with pytest.raises(ValueError, match="motor"):
        N.cargar_config(ruta)


def test_candidatos_v2_empiezan_por_el_principal(tmp_path):
    ruta = tmp_path / "ner.yaml"
    modelos = ("modelos:\n  m: {repo_id: a/b, revision: x1, max_length_real: 510, ventana: 480, "
               "solape: 64}\n  s: {motor: spacy, repo_id: es_x, revision: '3.8.0'}\n")
    ruta.write_text("principal: m\ncandidatos_v2: [s, m]\n" + modelos, encoding="utf-8")
    with pytest.raises(ValueError, match="principal"):
        N.candidatos_v2(ruta)
    ruta.write_text("principal: m\ncandidatos_v2: [m, z]\n" + modelos, encoding="utf-8")
    with pytest.raises(ValueError, match="sin entrada"):
        N.candidatos_v2(ruta)


def test_config_real_candidatos_con_revision_fija_y_licencia():
    principal, cfgs = N.cargar_config()
    lista = N.candidatos_v2()
    assert lista[0] == principal and len(lista) >= 3
    for s in lista[1:]:
        c = cfgs[s]
        assert c.licencia
        assert set(c.mapa_etiquetas.values()) == {"PER", "ORG", "LOC"}
        if c.motor == "transformers":
            assert re.fullmatch(r"[0-9a-f]{40}", c.revision)
        else:
            assert re.fullmatch(r"\d+\.\d+\.\d+", c.revision)


# --------------------------------------------------------------------------- comparación


def _cfgs():
    return {s: N.ConfigModelo(slug=s, repo_id=f"org/{s}", revision="a" * 40, max_length_real=510,
                              ventana=480, solape=64) for s in ("v1", "otro")}


def _ent(*filas):
    return pd.DataFrame([{"passage_id": p, "tipo": t, "texto": "x", "inicio": i, "fin": f,
                          "metodo": "modelo"} for p, t, i, f in filas],
                        columns=["passage_id", "tipo", "texto", "inicio", "fin", "metodo"])


def test_gana_el_mejor_f1_micro():
    gold = _ent(("p1", "PER", 0, 3), ("p1", "LOC", 10, 15))
    preds = {"v1": _ent(("p1", "PER", 0, 3)), "otro": _ent(("p1", "PER", 0, 3),
                                                            ("p1", "LOC", 10, 15))}
    t = C.comparar(gold, preds, _cfgs(), {"p1"}, ["v1", "otro"])
    assert t[t["elegido"]]["slug"].unique().tolist() == ["otro"]
    assert set(t["tipo"]) == {"PER", "ORG", "LOC", "TODOS"}


def test_empate_a_tres_decimales_gana_el_principal():
    gold = _ent(("p1", "PER", 0, 3), ("p1", "ORG", 5, 8))
    preds = {"v1": _ent(("p1", "PER", 0, 3)), "otro": _ent(("p1", "ORG", 5, 8))}
    t = C.comparar(gold, preds, _cfgs(), {"p1"}, ["v1", "otro"])
    assert C.elegir(t, ["v1", "otro"]) == "v1"
    assert C.elegir(t, ["otro", "v1"]) == "otro"


def test_falsos_positivos_en_pasaje_sin_gold_cuentan():
    gold = _ent(("p1", "PER", 0, 3))
    preds = {"v1": _ent(("p1", "PER", 0, 3)),
             "otro": _ent(("p1", "PER", 0, 3), ("p2", "ORG", 0, 4))}
    t = C.comparar(gold, preds, _cfgs(), {"p1", "p2"}, ["v1", "otro"])
    micro = t[t["tipo"] == "TODOS"].set_index("slug")
    assert micro.loc["otro", "fp"] == 1 and micro.loc["v1", "f1"] > micro.loc["otro", "f1"]


def test_solo_lee_la_seleccion_pasada_1_y_tipos_del_modelo(monkeypatch):
    filas = [("seleccion", 1, "PER"), ("seleccion", 1, "MONTO"), ("seleccion", 2, "FECHA"),
             ("a", 1, "PER"), ("b", 1, "ORG")]
    g = pd.DataFrame([{"parte": p, "passage_id": "x", "tipo": t, "texto": "x", "inicio": 0,
                       "fin": 1, "pasada": n} for p, n, t in filas])
    monkeypatch.setattr(V, "gold_oficial", lambda cfg, d=None: g)
    out = C.gold_seleccion(None)
    assert out[["parte", "pasada", "tipo"]].values.tolist() == [["seleccion", 1, "PER"]]


def test_faltan_adjudicar_exige_cierre_y_huella_vigente(monkeypatch, tmp_path):
    parte = V.Parte("seleccion", "Selección", tmp_path / "m.csv", ("d", "a"), "g", (1, 2))
    cfg = V.ConfigGold({"seleccion": parte}, (), True)
    monkeypatch.setattr(V, "manifiesto", lambda p: pd.DataFrame({"passage_id": ["p1", "p2", "p3"]}))
    monkeypatch.setattr(V, "leer_estado_adj", lambda d, a: pd.DataFrame(
        {"passage_id": ["p1", "p2", "p3"], "pasada": [1, 1, 2],
         "estado": [V.CERRADO, V.CERRADO, V.CERRADO], "huella": ["h", "vieja", "h"],
         "revision": [1, 1, 1]}))
    monkeypatch.setattr(V, "huella", lambda d, p, pid, n: "h")
    assert C.faltan_adjudicar(cfg, tmp_path) == ["p2", "p3"]


def test_modelo_ner_v2_conserva_las_claves_que_leen_08_y_09():
    gold = _ent(("p1", "PER", 0, 3))
    preds = {"v1": _ent(("p1", "PER", 0, 3)), "otro": _ent()}
    cfgs = _cfgs()
    t = C.comparar(gold, preds, cfgs, {"p1"}, ["v1", "otro"])
    d = C.modelo_ner_v2(cfgs["v1"], t, 10)
    assert {"modelo", "slug", "revision", "f1_seleccion", "criterio"} <= set(d)
    assert d["version"] == 2 and d["f1_seleccion"] == 1.0 and set(d["candidatos"]) == {"v1",
                                                                                        "otro"}
