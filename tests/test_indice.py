"""T03 · Índice invertido a mano contra `CountVectorizer` (PRD §6.3)."""
from __future__ import annotations

import pickle
import random
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from mtx import config, indice
from mtx.preproceso import tokenizar_pasaje

# Pasajes sintéticos con marca de interlocutor: "ZOÉ ROBLEDO" y "ALCOCER" solo aparecen en marcas.
MARCAS = ["ZOÉ ROBLEDO ABURTO: ", "JORGE ALCOCER VARELA: ", "", "PREGUNTA: "]
CUERPOS = [
    "La vacuna llegó a Tabasco. La vacuna se aplicó en hospitales.",
    "Vacunas y más vacunas para Tabasco y Chiapas.",
    "El tren avanza en Chiapas; el tren llega a Palenque. Tren, tren.",
    "",  # cuerpo vacío: longitud 0, sin postings
]


def _fixture():
    textos = [m + c for m, c in zip(MARCAS, CUERPOS)]
    ids = [f"0_{i}" for i in range(len(textos))]
    toks = [tokenizar_pasaje(t, len(m)) for t, m in zip(textos, MARCAS)]
    return ids, toks


def test_conteos_conocidos_del_fixture():
    ids, toks = _fixture()
    ind = indice.construir(ids, toks)
    assert ind.N == 4
    assert ind.postings["vacun"] == {0: 2, 1: 2}  # "vacuna" y "vacunas" comparten raíz
    assert ind.postings["tren"] == {2: 4}
    assert ind.df["tabasc"] == 2 and ind.df["chiap"] == 2
    assert list(ind.longitud) == [len(t) for t in toks]
    assert ind.longitud[3] == 0
    assert ind.avgdl == pytest.approx(np.mean([len(t) for t in toks]))
    assert ind.idx_de["0_2"] == 2 and ind.ids[2] == "0_2"


def test_nombres_solo_en_marcas_tienen_df_cero_en_ambos():
    ids, toks = _fixture()
    ind = indice.construir(ids, toks)
    vec, X = indice.matriz_conteos(toks)
    vocab = vec.vocabulary_
    for nombre in ("zoe", "robled", "alcoc", "jorg", "pregunt"):
        assert ind.df.get(nombre, 0) == 0
        assert nombre not in vocab


def _comparar_con_countvectorizer(ind, toks, terminos):
    vec, X = indice.matriz_conteos(toks)
    X = X.tocsc()
    assert set(vec.vocabulary_) == set(ind.postings)
    for t in terminos:
        col = X[:, vec.vocabulary_[t]]
        assert ind.df[t] == col.nnz, t
        assert sum(ind.postings[t].values()) == col.sum(), t
        filas, _ = col.nonzero()
        assert set(filas) == set(ind.postings[t]), t
        for i, tf in ind.postings[t].items():
            assert col[i, 0] == tf, (t, i)


def test_fixture_coincide_con_countvectorizer():
    ids, toks = _fixture()
    ind = indice.construir(ids, toks)
    _comparar_con_countvectorizer(ind, toks, list(ind.postings))


@pytest.mark.skipif(not config.PASAJES_PARQUET.exists(), reason="requiere make corpus")
def test_50_terminos_aleatorios_de_pasajes_reales():
    p = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto", "inicio_cuerpo"])
    p = p.sample(2000, random_state=config.SEMILLA)
    toks = [tokenizar_pasaje(t, i) for t, i in zip(p["texto"], p["inicio_cuerpo"])]
    ind = indice.construir(list(p["passage_id"]), toks)
    terminos = random.Random(config.SEMILLA).sample(sorted(ind.postings), 50)
    _comparar_con_countvectorizer(ind, toks, terminos)


def test_numero_de_listas_distinto_de_ids_falla():
    with pytest.raises(ValueError):
        indice.construir(["a", "b"], [["x"]])


def test_idf_bm25_positivo_y_cero_para_ausentes():
    ids, toks = _fixture()
    ind = indice.construir(ids, toks)
    assert ind.idf_bm25("vacun") == pytest.approx(np.log(1 + (4 - 2 + 0.5) / (2 + 0.5)))
    assert ind.idf_bm25("inexistente") == 0.0
    assert all(ind.idf_bm25(t) > 0 for t in ind.postings)


def test_guardar_y_cargar_con_hash(tmp_path):
    ids, toks = _fixture()
    ind = indice.construir(ids, toks)
    pkl, meta = tmp_path / "indice.pkl", tmp_path / "indice_meta.json"
    m = indice.guardar(ind, pkl, meta, hash_tokens="abc", hash_config="cfg")
    assert m["N"] == 4 and m["vocabulario"] == len(ind.postings)
    otro = indice.cargar(pkl, meta, hash_tokens="abc")
    assert otro.postings == ind.postings and otro.ids == ind.ids
    with pytest.raises(ValueError, match="reconstruir"):
        indice.cargar(pkl, meta, hash_tokens="otro")


def test_countvectorizer_persistido_se_carga_en_otro_proceso(tmp_path):
    """`identidad` está a nivel de módulo: el pickle se puede cargar en un proceso nuevo."""
    _, toks = _fixture()
    vec, _ = indice.matriz_conteos(toks)
    ruta = tmp_path / "vec.pkl"
    ruta.write_bytes(pickle.dumps(vec, protocol=5))
    codigo = ("import pickle,sys; v=pickle.load(open(sys.argv[1],'rb')); "
              "print(v.transform([['tren','tren']]).sum())")
    r = subprocess.run([sys.executable, "-c", codigo, str(ruta)], capture_output=True, text=True,
                       check=True)
    assert r.stdout.strip() == "2"
