"""NER: posproceso U15, ventanas T12 y caché D18, sin red (pipeline simulado). Ejemplos sintéticos."""
from __future__ import annotations

import itertools
import re

import pandas as pd
import pytest

from mtx import ner_modelo as N


def _cfg(**kw) -> N.ConfigModelo:
    base = {"slug": "falso", "repo_id": "org/falso", "revision": "a" * 40, "max_length_real": 510,
                "ventana": 20, "solape": 5, "mapa_etiquetas": {"PER": "PER", "PERSON": "PER", "ORG": "ORG",
                                                      "LOC": "LOC", "GPE": "LOC"},
                "descartadas": ("MISC", "OTH")}
    base.update(kw)
    return N.ConfigModelo(**base)


class TokPalabras:
    """Tokenizador falso: un subtoken por palabra (`\\S+`), con offsets reales."""
    is_fast = True

    def __call__(self, texto, add_special_tokens=False, return_offsets_mapping=False):
        offs = [(m.start(), m.end()) for m in re.finditer(r"\S+", texto)]
        ids = list(range(len(offs) + (2 if add_special_tokens else 0)))
        return {"input_ids": ids, "offset_mapping": offs}


class PipeNombres:
    """Pipeline falso: marca como PER cada palabra que empieza con mayúscula; cuenta llamadas."""

    def __init__(self):
        self.llamadas = 0

    def __call__(self, textos, batch_size=8):
        self.llamadas += 1
        return [[{"entity_group": "PER", "score": 0.9, "word": m.group(0), "start": m.start(),
                  "end": m.end()} for m in re.finditer(r"\b[A-ZÁÉÍÓÚÑ]\w+", t)] for t in textos]


def _crudas(texto, *spans):
    return [{"etiqueta": et, "inicio": i, "fin": f, "texto": texto[i:f], "confianza": c}
            for et, i, f, c in spans]


# --------------------------------------------------------------------------- mapa y recorte


def test_mapa_de_etiquetas_y_descartes_contados():
    t = "Ana vio la ONU en Perú con Patria."
    cr = _crudas(t, ("PERSON", 0, 3, .9), ("ORG", 11, 14, .9), ("GPE", 18, 22, .9),
                 ("MISC", 27, 33, .9), ("B-OTH", 27, 33, .5), ("EVENT", 0, 3, .4))
    pp = N.posprocesar(t, cr, _cfg())
    assert [(e["tipo"], e["texto"]) for e in pp.entidades] == [
        ("PER", "Ana"), ("ORG", "ONU"), ("LOC", "Perú")]
    assert pp.descartadas == {"MISC": 1, "OTH": 1, "EVENT": 1}


def test_recorte_de_extremos_conserva_el_signo_de_pesos():
    t = 'Dijo: "(Pemex)", con $500 y «Tabasco».'
    cr = _crudas(t, ("ORG", 6, 15, .9), ("ORG", 20, 25, .9), ("LOC", 28, 38, .9))
    pp = N.posprocesar(t, cr, _cfg())
    assert [e["texto"] for e in pp.entidades] == ["Pemex", "$500", "Tabasco"]
    for e in pp.entidades:
        assert t[e["inicio"]:e["fin"]] == e["texto"]


def test_span_solo_puntuacion_se_descarta_y_se_cuenta():
    t = "Hola, «» adiós."
    pp = N.posprocesar(t, _crudas(t, ("PER", 6, 8, .9)), _cfg())
    assert pp.entidades == [] and pp.descartadas == {"vacia_tras_recorte": 1}


def test_invariante_roto_en_crudo_es_error():
    t = "Ana López"
    with pytest.raises(ValueError, match="crudo"):
        N.posprocesar(t, [{"etiqueta": "PER", "inicio": 0, "fin": 3, "texto": "Eva",
                           "confianza": .9}], _cfg())


# --------------------------------------------------------------------------- uniones


def test_union_intrapalabra_siempre_sin_registro():
    t = "Llegó López."
    pp = N.posprocesar(t, _crudas(t, ("PER", 6, 8, .9), ("PER", 8, 11, .8)), _cfg())
    assert [e["texto"] for e in pp.entidades] == ["López"] and pp.uniones == []


def test_union_interpalabra_registrada_y_crudo_conservado():
    t = "Habló Andrés López Obrador hoy."
    cr = _crudas(t, ("PER", 6, 18, .95), ("PER", 19, 26, .7))
    pp = N.posprocesar(t, cr, _cfg(), passage_id="1_1")
    assert [e["texto"] for e in pp.entidades] == ["Andrés López Obrador"]
    assert [e["texto"] for e in pp.sin_union_interpalabra] == ["Andrés López", "Obrador"]
    assert len(pp.uniones) == 1
    u = pp.uniones[0]
    assert set(u) == set(N.COLUMNAS_UNIONES)
    assert (u["inicio_union"], u["fin_union"], u["texto_union"]) == (6, 26, "Andrés López Obrador")
    assert (u["confianza_1"], u["confianza_2"]) == (.95, .7)


def test_no_une_tipos_distintos_ni_separadores_largos():
    t = "Pemex Tabasco y Ana  Eva"
    cr = _crudas(t, ("ORG", 0, 5, .9), ("LOC", 6, 13, .9), ("PER", 16, 19, .9),
                 ("PER", 21, 24, .9))
    assert len(N.posprocesar(t, cr, _cfg()).entidades) == 4


# --------------------------------------------------------------------------- ventanas (T12)


def test_t12_texto_largo_oracion_enorme_cobertura_completa():
    palabras = [f"palabra{i}" for i in range(97)]
    texto = " ".join(palabras)  # una sola oración sin puntos
    offs = TokPalabras()(texto)["offset_mapping"]
    tramos = N.ventanas(offs, len(texto), ventana=20, solape=5)
    assert tramos[0][0] == 0 and tramos[-1][1] == len(texto)
    assert all(b[0] <= a[1] for a, b in itertools.pairwise(tramos))
    assert len(tramos) > 1
    assert N.ventanas(offs, len(texto), 20, 5) == tramos  # determinista
    for a, b in tramos:
        assert len(TokPalabras()(texto[a:b])["offset_mapping"]) <= 20


def test_t12_entidad_en_el_borde_se_deduplica_priorizando_la_no_cortada():
    cfg = _cfg()
    texto = " ".join(["x"] * 19 + ["Zapata"] + ["y"] * 30)
    crudas = N.inferir_pasaje(texto, PipeNombres(), TokPalabras(), cfg)
    zapatas = [e for e in crudas if e["texto"] == "Zapata"]
    assert len(zapatas) == 1 and zapatas[0]["cortada"] is False
    assert texto[zapatas[0]["inicio"]:zapatas[0]["fin"]] == "Zapata"


def test_deduplicacion_por_confianza_entre_no_cortadas():
    a = {"etiqueta": "PER", "inicio": 0, "fin": 5, "texto": "", "confianza": .6, "cortada": False}
    b = {"etiqueta": "ORG", "inicio": 0, "fin": 5, "texto": "", "confianza": .9, "cortada": False}
    c = {"etiqueta": "PER", "inicio": 0, "fin": 5, "texto": "", "confianza": .99, "cortada": True}
    assert N.deduplicar([a, b, c]) == [b]


def test_ventana_que_excede_el_limite_es_error():
    cfg = _cfg(max_length_real=10, ventana=10, solape=2)

    class TokLargo(TokPalabras):
        def __call__(self, texto, add_special_tokens=False, return_offsets_mapping=False):
            r = super().__call__(texto, add_special_tokens, return_offsets_mapping)
            if add_special_tokens:
                r["input_ids"] = r["input_ids"] * 3
            return r
    with pytest.raises(ValueError, match="excede"):
        N.inferir_pasaje(" ".join(["a"] * 30), PipeNombres(), TokLargo(), cfg)


# --------------------------------------------------------------------------- caché (D18)


def _pasajes():
    return pd.DataFrame({"passage_id": ["1_1", "2_3"],
                         "texto": ["Habló Ana con Eva.", "Fue a Mérida."],
                         "texto_sha256": ["s1", "s2"]})


def test_cache_misma_clave_no_reinfiere_y_forzar_si(tmp_path):
    cfg, pipe = _cfg(), PipeNombres()
    llamadas = []

    def constructor(c):
        llamadas.append(c.slug)
        return pipe, TokPalabras()
    crudos, reg = N.ejecutar(cfg, _pasajes(), raiz=tmp_path, constructor=constructor)
    assert reg.inferidos == 2 and len(llamadas) == 1
    assert (tmp_path / f"falso@{'a' * 8}" / "1_1.json").exists()
    crudos2, reg2 = N.ejecutar(cfg, _pasajes(), raiz=tmp_path, constructor=constructor)
    assert reg2.cacheados == 2 and reg2.inferidos == 0 and len(llamadas) == 1
    assert crudos2 == crudos
    _, reg3 = N.ejecutar(cfg, _pasajes(), forzar=True, raiz=tmp_path, constructor=constructor)
    assert reg3.inferidos == 2 and len(llamadas) == 2


def test_clave_cambia_con_revision_fragmentacion_y_texto_no_con_posproceso():
    base = _cfg()
    k = N.clave_cache(base, "s1")
    assert N.clave_cache(_cfg(revision="b" * 40), "s1") != k
    assert N.clave_cache(_cfg(solape=6), "s1") != k
    assert N.clave_cache(_cfg(ventana=21), "s1") != k
    assert N.clave_cache(base, "s2") != k
    assert N.clave_cache(_cfg(version_posproceso=2), "s1") == k
    assert N.clave_cache(_cfg(lote=4), "s1") == k


def test_cache_con_texto_cambiado_se_trata_como_ausente(tmp_path):
    cfg = _cfg()
    N.ejecutar(cfg, _pasajes(), raiz=tmp_path, constructor=lambda c: (PipeNombres(), TokPalabras()))
    otro = _pasajes().assign(texto_sha256=["s1", "nuevo"])
    _, reg = N.ejecutar(cfg, otro, raiz=tmp_path,
                        constructor=lambda c: (PipeNombres(), TokPalabras()))
    assert (reg.cacheados, reg.inferidos) == (1, 1)


# --------------------------------------------------------------------------- configuración


def test_config_real_tiene_revision_fija_y_es_coherente():
    principal, cfgs = N.cargar_config()
    cfg = cfgs[principal]
    assert re.fullmatch(r"[0-9a-f]{40}", cfg.revision)
    assert cfg.ventana <= cfg.max_length_real and cfg.solape < cfg.ventana


def test_config_rechaza_revision_main(tmp_path):
    ruta = tmp_path / "ner.yaml"
    ruta.write_text("principal: m\nmodelos:\n  m: {repo_id: a/b, revision: main, "
                    "max_length_real: 510, ventana: 480, solape: 64}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="revisión"):
        N.cargar_config(ruta)


def test_modelo_ner_json_tiene_las_claves_de_d09():
    d = N.modelo_ner_json(_cfg())
    assert {"modelo", "revision", "f1_seleccion", "f1_seleccion_alternativa",
            "criterio"} <= set(d)
    assert d["criterio"] == "tecnico"
