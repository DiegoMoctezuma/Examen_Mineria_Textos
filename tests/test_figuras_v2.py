"""WP-16: figuras v2 con título, ejes nombrados, nombres de consulta y sin IDs ni rutas (D36, S6,
S8b, R04). Datos inventados; no se escriben imágenes."""
from __future__ import annotations

import pandas as pd
import pytest

from mtx import figuras_v2 as F


@pytest.fixture(scope="module")
def est():
    return F.cargar_estilo()


def _ejes_nombrados(fig) -> bool:
    lay = fig.layout
    xs = [getattr(lay, k) for k in dir(lay) if k.startswith("xaxis")]
    ys = [getattr(lay, k) for k in dir(lay) if k.startswith("yaxis")]
    return any(a.title.text for a in xs) and any(a.title.text for a in ys)


def _ok(fig, ejes: bool = True):
    assert fig.layout.title.text
    assert not F.tiene_id_o_ruta(fig)
    if ejes:
        assert _ejes_nombrados(fig)


def test_nombres_legibles(est):
    assert F.nombre_consulta(est, "Q3") == "Pregunta 3 · Dos Bocas"
    assert F.nombre_consulta(est, "Q15", corto=True) == "Acapulco tras Otis"
    assert F.nombre_modelo("bm25_lema_con_filtro") == "BM25 · lema · con filtro de fecha"
    assert F.nombre_modelo("tfidf_sin_filtro") == "TF-IDF · raíz · sin filtro"
    assert F.etiqueta_pasaje("2021-03-12", 2, "12.03.21 Versión estenográfica de la conferencia "
                             "de prensa matutina") == "Mañanera del 12 de marzo de 2021 · fragmento 3"


def test_estilo_tiene_las_15_consultas_y_la_paleta(est):
    assert set(est.nombres) == {f"Q{i}" for i in range(1, 16)}
    assert est.paleta["guinda"].startswith("#") and est.titulos and est.texto


def test_detecta_ids_y_rutas(est):
    go = F._go()
    assert F.tiene_id_o_ruta(go.Figure(go.Bar(x=["1122_3"], y=[1])))
    assert F.tiene_id_o_ruta(go.Figure(go.Bar(x=["salida/ranking.csv"], y=[1])))


def test_aviso_v1_solo_con_datos_v1(est):
    rel_fig = F.fig_ap([1, 0], 1, 1.0, "Pregunta 1", "BM25", est, "v1")
    assert F.AVISO_V1 in rel_fig.layout.title.subtitle.text
    assert F.AVISO_V1 not in F.fig_ap([1, 0], 1, 1.0, "P", "BM25", est, "v2"
                                      ).layout.title.subtitle.text


def test_subtitulo_largo_se_parte_en_lineas(est):
    fig = F.fig_ap([1] * 10, 10, 1.0, "Pregunta 1 · Tren Maya", "BM25 · raíz · con filtro de "
                   "fecha", est, "v1")
    assert fig.layout.title.subtitle.text.count("<br>") >= 2


def test_corpus_y_acotaciones(est):
    lim = {"discursos": 100, "discursos_excluidos": 3, "duplicados_exactos": 2,
           "casi_duplicados": 1, "discursos_con_pasajes": 96, "pasajes": 5000,
           "pasajes_de_reporteros_pct": 15.5, "acotaciones_eliminadas": 30,
           "acotaciones_por_tipo": {"inaudible": 20, "inicia video": 9, "…": 1}}
    _ok(F.fig_corpus(lim, est), ejes=False)
    fig = F.fig_acotaciones(lim, est)
    _ok(fig)
    assert "«…»" not in list(fig.data[0].y)


def test_oracion_ejemplo_prefiere_la_que_tiene_mas_terminos():
    cuerpo = ("Hoy es un día muy bonito para todos los que estamos aquí. "
              "Vamos a inaugurar la refinería de Dos Bocas en Paraíso, Tabasco, con toda la gente.")
    assert F.oracion_ejemplo(cuerpo, {"refin", "boc", "tabasc"}).startswith("Vamos")


def test_tokenizacion_e_idf(est):
    pasos = F.pasos_tokenizacion("Vamos a la refinería de Dos Bocas.")
    assert [p for p, _ in pasos][-1].startswith("4.") and "refin" in pasos[-1][1]
    con_lema = F.pasos_tokenizacion("Vamos a la refinería.", ["ir", "refinería"])
    assert not any("examen" in p or "proyecto final" in p for p, _ in con_lema)
    _ok(F.fig_tokenizacion(pasos, "Mañanera del 1 de julio de 2022 · fragmento 3", est),
        ejes=False)
    t = F.terminos_idf("combate al huachicol", {"combat": 100, "huachicol": 10}, 1000)
    assert t["palabra"].tolist() == ["combate", "huachicol"]
    assert t.set_index("palabra").at["huachicol", "pct"] == pytest.approx(0.01)
    _ok(F.fig_idf(t, "Huachicol", 1000, est))


def test_stem_lema_e_indice(est):
    pares = pd.DataFrame({"palabra": ["maya", "mayo"], "stem": ["may", "may"],
                          "df_stem": [10, 10], "lema": ["maya", "mayo"], "df_lema": [6, 4]})
    fig = F.fig_stem_lema(pares, est)
    _ok(fig, ejes=False)
    assert "examen" not in F.textos_visibles(fig) and "proyecto final" not in F.textos_visibles(fig)
    post = [{"palabra": "huachicol", "raiz": "huachicol", "df": 7, "idf": 5.1,
             "top": [("Mañanera del 25 de enero de 2019 · fragmento 26", 7)]}]
    _ok(F.fig_indice(post, 1000, est), ejes=False)


def test_ap_explicado_y_ap_por_consulta(est):
    fig = F.fig_ap([0, 1, 1, 0], 4, 0.29, "Pregunta 3 · Dos Bocas", "BM25", est)
    _ok(fig)
    assert "(1/2 + 2/3) / 4" in fig.layout.title.subtitle.text
    ap = pd.DataFrame({"query_id": ["Q1", "Q2", "Q1", "Q2"],
                       "modelo": ["bm25_con_filtro"] * 2 + ["tfidf_con_filtro"] * 2,
                       "AP": ["0.5", "0.4", "0.2", "0.1"]})
    fig = F.fig_ap_consulta(ap, ["bm25_con_filtro", "tfidf_con_filtro"], est)
    _ok(fig)
    assert list(fig.data[0].x) == ["Tren Maya", "Vacunas COVID-19"]


def test_map_con_y_sin_intervalo(est):
    m = pd.DataFrame({"modelo": ["bm25_con_filtro", "tfidf_con_filtro"], "map": [0.48, 0.3],
                      "inf": [0.4, 0.2], "sup": [0.55, 0.38]})
    fig = F.fig_map(m, "bm25_con_filtro", est)
    _ok(fig)
    assert fig.data[0].error_x.array is not None and "48.0 %" in fig.layout.title.text
    sin = m.assign(inf=float("nan"), sup=float("nan"))
    assert F.fig_map(sin, "bm25_con_filtro", est).data[0].error_x.array is None


def test_ie(est):
    res = pd.DataFrame([{"metodo": m, "tipo": t, "precision": 0.5, "recall": 0.4, "f1": 0.44}
                        for m in ("regla", "modelo", "combinado") for t in ("PER", "FECHA")])
    _ok(F.fig_prf(res, est))
    ref = pd.DataFrame([
        {"referencia": "sistema_exacto", "metodo": "combinado", "tipo": "PER", "f1": 0.7,
         "ic95_inf": 0.6, "ic95_sup": 0.8},
        {"referencia": "sistema_exacto", "metodo": "combinado", "tipo": "TODOS", "f1": 0.65,
         "ic95_inf": 0.55, "ic95_sup": 0.75},
        {"referencia": "techo_humano", "metodo": "", "tipo": "PER", "f1": 0.9,
         "ic95_inf": None, "ic95_sup": None},
        {"referencia": "linea_base_gazetteer", "metodo": "regla", "tipo": "PER", "f1": 0.3,
         "ic95_inf": None, "ic95_sup": None}])
    res_c = pd.DataFrame([{"metodo": "combinado", "tipo": t, "f1": f, "gold": g}
                          for t, f, g in (("PER", 0.7, 10), ("FECHA", 0.5, 8), ("TODOS", 0.65, 18))])
    fig = F.fig_f1_referencias(ref, res_c, est)
    _ok(fig)
    assert list(fig.data[0].x) == ["Personas", "Fechas", "Todas"] and len(fig.data) == 4
    intervalo = fig.data[1]  # solo en «Todas»
    assert list(intervalo.x) == ["Todas"] and intervalo.error_y.array[0] > 0
    techo = next(d for d in fig.data if d.name and "techo" in d.name)
    assert pd.isna(list(techo.y)[1])  # sin rombo de techo en Fechas
    assert "solo 8 fechas anotadas" in fig.layout.title.subtitle.text
    assert "gold" not in F.textos_visibles(fig)
    err = pd.DataFrame({"error": ["FP", "FN", "FN"], "categoria": ["frontera", "omision",
                                                                    "frontera:entidad_partida"],
                        "tipo": ["LOC"] * 3, "metodo": ["modelo"] * 3, "n": [3, 2, 1]})
    fig = F.fig_errores(err, est)
    _ok(fig)
    assert "Límites del nombre distintos" in list(fig.data[0].y)


def test_estados(est):
    resp = pd.DataFrame({"query_id": ["Q1", "Q1", "Q11"],
                         "estado": ["respaldado_en_texto", "ambiguo", "no_encontrado"]})
    fig = F.fig_estados(resp, est)
    _ok(fig)
    assert "Guardia Nacional" in list(fig.data[0].y)


def test_modulo_no_lee_ni_escribe_archivos():
    import inspect

    fuente = inspect.getsource(F)
    for prohibido in ("to_csv", "write_image", "read_csv", "read_parquet", "anotaciones"):
        assert prohibido not in fuente
