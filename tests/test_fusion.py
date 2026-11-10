"""Fusión reglas + modelo (D12, D16, T08, T13). Fixtures sintéticos, nunca el gold."""
from __future__ import annotations

import pandas as pd
import pytest

from mtx import fusion as F

TEXTO = "Fonatur y el Tren Maya llegan a Mérida el 15 de enero de 2021 con 2 mil millones de pesos."


def _fila(pid, tipo, frag, fuente="gazetteer_org", puntaje=None, desde=0, texto=TEXTO):
    ini = texto.index(frag, desde)
    return {"passage_id": pid, "tipo": tipo, "texto": frag, "inicio": ini,
            "fin": ini + len(frag), "fuente": fuente, "en_marca": False,
            "puntaje_modelo": puntaje}


@pytest.fixture
def fuentes():
    reglas = pd.DataFrame([
        _fila("1_1", "ORG", "Fonatur"),                              # exacta → ambos
        _fila("1_1", "LOC", "Tren Maya", "gazetteer_loc"),           # parcial con "Maya"
        _fila("1_1", "LOC", "Mérida", "gazetteer_loc"),              # tipo distinto
        _fila("1_1", "FECHA", "15 de enero de 2021", "regex_fecha"),  # solo regla
    ], columns=F.COLUMNAS_FUENTE)
    modelo = pd.DataFrame([
        _fila("1_1", "ORG", "Fonatur", "modelo", 0.99),
        _fila("1_1", "LOC", "Maya", "modelo", 0.80),
        _fila("1_1", "ORG", "Mérida", "modelo", 0.60),
        _fila("1_1", "PER", "pesos", "modelo", 0.30),                # solo modelo
    ], columns=F.COLUMNAS_FUENTE)
    return reglas, modelo


def test_t13_exacta_parcial_y_tipo_distinto(fuentes):
    unicas, solapes = F.fusionar_unicas(*fuentes)
    m = {(f["tipo"], f["texto"]): f["metodo"] for f in unicas.to_dict("records")}
    assert m == {("ORG", "Fonatur"): "ambos", ("LOC", "Tren Maya"): "regla",
                 ("LOC", "Maya"): "modelo", ("LOC", "Mérida"): "regla",
                 ("ORG", "Mérida"): "modelo", ("FECHA", "15 de enero de 2021"): "regla",
                 ("PER", "pesos"): "modelo"}
    assert unicas.set_index("texto").loc["Fonatur", "fuentes"] == "gazetteer_org|modelo"
    clases = sorted(zip(solapes["clase"], solapes["texto_regla"], solapes["texto_modelo"]))
    assert clases == [("solape_parcial", "Tren Maya", "Maya"),
                      ("tipo_distinto", "Mérida", "Mérida")]
    assert solapes.set_index("texto_regla").loc["Tren Maya", "longitud_solape"] == 4


def test_t08_pasaje_compartido_entre_consultas(fuentes):
    unicas, _ = F.fusionar_unicas(*fuentes)
    amb = pd.DataFrame({"query_id": ["Q3", "Q1", "Q10"], "passage_id": ["1_1", "1_1", "2_1"],
                        "doc_id": [1, 1, 2]})
    ent = F.asociar_consultas(unicas, amb)[F.COLUMNAS_ENTIDADES]
    assert list(ent["query_id"].unique()) == ["Q1", "Q3"]  # orden numérico; Q10 sin entidades
    q1 = ent[ent.query_id == "Q1"].drop(columns="query_id").reset_index(drop=True)
    q3 = ent[ent.query_id == "Q3"].drop(columns="query_id").reset_index(drop=True)
    assert q1.equals(q3) and len(q1) == len(unicas)
    # el kit compara conjuntos (passage_id, tipo, inicio, fin): la vista única no cuenta doble
    assert len(ent.drop_duplicates(F.CLAVE)) == len(unicas)


def test_contrato_y_validacion(fuentes):
    unicas, _ = F.fusionar_unicas(*fuentes)
    amb = pd.DataFrame({"query_id": ["Q1"], "passage_id": ["1_1"], "doc_id": [1]})
    ent = F.asociar_consultas(unicas, amb)[F.COLUMNAS_ENTIDADES]
    assert list(ent.columns) == F.COLUMNAS_ENTIDADES and len(ent.columns) == 8
    assert F.validar_entidades(ent, {"1_1": TEXTO}) == []
    malo = ent.copy()
    malo.loc[0, "metodo"] = "fusion"
    malo.loc[1, "inicio"] += 1
    err = " ".join(F.validar_entidades(malo, {"1_1": TEXTO}))
    assert "Métodos fuera de dominio" in err and "invariante" in err
    assert F.validar_entidades(pd.concat([ent, ent.head(1)]), {"1_1": TEXTO})


def test_clave_repetida_en_una_fuente_es_error(fuentes):
    reglas, modelo = fuentes
    with pytest.raises(ValueError, match="repetidas"):
        F.fusionar_unicas(pd.concat([reglas, reglas.head(1)]), modelo)


def test_determinismo_bytes_identicos(fuentes, tmp_path):
    amb = pd.DataFrame({"query_id": ["Q2", "Q1"], "passage_id": ["1_1", "1_1"], "doc_id": [1, 1]})
    salidas = []
    for i, orden in enumerate((1, -1)):
        r, m = (x.iloc[::orden] for x in fuentes)  # orden de entrada distinto
        unicas, sol = F.fusionar_unicas(r, m)
        ent = F.asociar_consultas(unicas, amb)[F.COLUMNAS_ENTIDADES]
        ruta = tmp_path / f"e{i}.csv"
        ent.to_csv(ruta, index=False, lineterminator="\n")
        sol.to_csv(tmp_path / f"s{i}.csv", index=False, lineterminator="\n")
        salidas.append((ruta.read_bytes(), (tmp_path / f"s{i}.csv").read_bytes()))
    assert salidas[0] == salidas[1]


def test_enriquecer_no_altera_columnas_oficiales(fuentes):
    unicas, _ = F.fusionar_unicas(*fuentes)
    amb = pd.DataFrame({"query_id": ["Q1"], "passage_id": ["1_1"], "doc_id": [1]})
    ent = F.asociar_consultas(unicas, amb)[F.COLUMNAS_ENTIDADES]
    gaz = pd.DataFrame([{"nombre": "Fondo Nacional de Fomento al Turismo", "variantes": "",
                         "siglas": "Fonatur", "tipo": "", "etiqueta": "ORG", "origen": "kit",
                         "evidencia": ""}])
    enr = F.enriquecer(ent, unicas, {"1_1": pd.Timestamp("2020-06-01")},
                       F.mapa_canonico([gaz]), "m/x", "abc", "v1")
    assert list(enr.columns[:8]) == F.COLUMNAS_ENTIDADES
    assert enr[F.COLUMNAS_ENTIDADES].equals(ent)
    f = enr.set_index("texto")
    assert f.loc["Fonatur", "canonico"] == "Fondo Nacional de Fomento al Turismo"
    assert f.loc["Fonatur", "modelo_id"] == "m/x" and f.loc["Fonatur", "puntaje_modelo"] == "0.9900"
    assert f.loc["Tren Maya", "estado_identidad"] == "sin_equivalencia"
    assert f.loc["Tren Maya", "modelo_id"] == ""  # solo regla
    assert f.loc["15 de enero de 2021", "fecha_iso"] == "2021-01-15"
    assert not set(F.COLUMNAS_ENRIQUECIDAS[8:]) & set(ent.columns)


def test_mapa_canonico_descarta_formas_ambiguas():
    g = pd.DataFrame([
        {"nombre": "A uno", "variantes": "", "siglas": "AU", "tipo": "", "etiqueta": "ORG",
         "origen": "", "evidencia": ""},
        {"nombre": "A otro", "variantes": "", "siglas": "AU", "tipo": "", "etiqueta": "ORG",
         "origen": "", "evidencia": ""}])
    m = F.mapa_canonico([g])
    assert "au" not in m and m["a uno"] == "A uno"
