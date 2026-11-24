"""WP-11 · Reglas FECHA v2 (PRD v2 D33). Suite bloqueante de `src/mtx/fecha_v2.py`.

Todos los ejemplos son frases inventadas: no salen del corpus ni del gold (Leo escribe estas reglas
sin ver el gold). Un caso que falle se conserva con `xfail(strict=True)` y su razón.
"""
from __future__ import annotations

from datetime import date

import pytest

from mtx import fecha_v2 as F
from mtx import reglas as R
from test_reglas import FECHAS_NEGATIVAS, FECHAS_POSITIVAS


def _fechas(texto: str, inicio_cuerpo: int = 0) -> list[str]:
    ents = F.extraer_reglas_v2(texto, inicio_cuerpo)
    for e in ents:
        assert 0 <= e.inicio < e.fin <= len(texto)
        assert texto[e.inicio:e.fin] == e.texto
    return [e.texto for e in ents if e.tipo == "FECHA"]


# =========================================================================== v1 se conserva


@pytest.mark.parametrize("texto,esperado", FECHAS_POSITIVAS)
def test_v2_conserva_positivos_v1(texto, esperado):
    assert _fechas(texto) == [esperado]


@pytest.mark.parametrize("texto", FECHAS_NEGATIVAS + [
    "Se hicieron en 2000 casas.", "Es el Cinco de Mayo.", "Le dicen Mayo.",
    "Hay más de 2000 elementos."])
def test_v2_conserva_negativos_v1(texto):
    assert _fechas(texto) == []


@pytest.mark.parametrize("texto,esperado", [
    ("Queremos que en 2021 esté en funcionamiento.", "2021"),
    ("Para enero aumenta la pensión.", "enero"),
    ("Opera a partir de diciembre de este año.", "diciembre de este año"),
    ("Queremos que para enero del 24 cobren el doble.", "enero del 24"),
])
def test_v2_conserva_ampliaciones_v1(texto, esperado):
    assert _fechas(texto) == [esperado]


def test_reglas_v1_no_cambian():
    """`reglas.extraer_reglas` sigue dando lo de v1 (las cifras v1 se reproducen)."""
    assert [e.texto for e in R.extraer_reglas("Creció de 2019 a 2024.", 0)] == ["2019", "2024"]
    assert [e.texto for e in R.extraer_reglas("Tomó posesión el 1o. de diciembre.", 0)] == []


# =========================================================================== formatos nuevos

POSITIVOS_V2 = [
    # día ordinal
    ("Tomó posesión el 1o. de diciembre de 2018.", "1o. de diciembre de 2018"),
    ("Arranca el 1º de julio.", "1º de julio"),
    ("Desde el 1° de enero de 2020 aplica.", "1° de enero de 2020"),
    ("Será el próximo 1ro de septiembre.", "próximo 1ro de septiembre"),
    # día y año en palabras
    ("Será el quince de enero.", "quince de enero"),
    ("Pasó el dos de octubre.", "dos de octubre"),
    ("Quince de marzo de 2021 fue la fecha.", "Quince de marzo de 2021"),
    ("Firmado el treinta y uno de diciembre.", "treinta y uno de diciembre"),
    ("Se firmó en enero de dos mil veinte.", "enero de dos mil veinte"),
    ("Llegó el 3 de mayo del dos mil diecinueve.", "3 de mayo del dos mil diecinueve"),
    ("Fue durante el año dos mil diecinueve.", "dos mil diecinueve"),
    ("Se inauguró en el dos mil veintidós.", "dos mil veintidós"),
    # mes abreviado
    ("Oficio del 15 dic 2023 enviado.", "15 dic 2023"),
    ("Oficio del 15-dic-23 enviado.", "15-dic-23"),
    ("Corte a dic. 2023 del avance.", "dic. 2023"),
    ("Corte a mar. 2021 del avance.", "mar. 2021"),
    # numéricas
    ("Con fecha 15-12-2023 se publicó.", "15-12-2023"),
    ("Con fecha 15.12.2023 se publicó.", "15.12.2023"),
    ("Registro 2023-12-15 en el sistema.", "2023-12-15"),
    ("Periodo 12/2023 en el informe.", "12/2023"),
    # intervalos
    ("Creció de 2019 a 2024.", "2019 a 2024"),
    ("Del 2019 al 2024 se construyó.", "2019 al 2024"),
    ("Entre 2019 y 2024 se hizo.", "2019 y 2024"),
    ("Desde 2019 hasta 2024 operó.", "2019 hasta 2024"),
    ("Se vacunó de enero a marzo de 2021.", "enero a marzo de 2021"),
    ("Va de enero de 2020 a marzo de 2021.", "enero de 2020 a marzo de 2021"),
    ("Se aplica de enero a marzo.", "enero a marzo"),
    ("Del 15 de enero al 3 de febrero de 2021 hubo vacunación.",
     "15 de enero al 3 de febrero de 2021"),
]


@pytest.mark.parametrize("texto,esperado", POSITIVOS_V2)
def test_fecha_v2_positivos_span_exacto(texto, esperado):
    assert _fechas(texto) == [esperado]


NEGATIVOS_V2 = [
    "Es la avenida Cinco de Mayo.",          # nombre propio: mes en mayúscula
    "Fueron dos de los estados.",            # día en palabras sin mes
    "Se compraron dos mil computadoras.",    # cantidad, no año
    "En dos mil veinte escuelas hubo luz.",  # cantidad: sin "el" delante
    "En el dos mil veinte escuelas se abrieron.",  # sustantivo en plural después
    "Vimos el mar 2020 veces.",              # "mar" sin punto no es abreviatura
    "Versión 1.12.2023b del sistema.",       # pegado a letras
    "Marcó 13/2023 en la boleta.",           # mes 13
    "El 15-13-2023 no existe.",              # mes 13
    "Fueron de 2000 a 3000 personas.",       # rango de cantidades (v1 tomaba "2000")
]


@pytest.mark.parametrize("texto", NEGATIVOS_V2)
def test_fecha_v2_negativos(texto):
    assert _fechas(texto) == []


def test_enumeracion_de_anios_sigue_separada():
    """Criterio v1: una enumeración produce entidades separadas; solo "entre ... y" es intervalo."""
    assert _fechas("Pasó en 2019 y 2020.") == ["2019", "2020"]


def test_modificador_dentro_y_preposicion_fuera():
    assert _fechas("Será el próximo quince de enero.") == ["próximo quince de enero"]
    assert _fechas("Fue en el año dos mil diecinueve.") == ["dos mil diecinueve"]


def test_fecha_v2_en_marca_mayusculas():
    texto = "COMUNICADO DEL 1O. DE DICIEMBRE DE 2018: Buenos días."
    assert _fechas(texto, inicio_cuerpo=texto.index(":") + 1) == ["1O. DE DICIEMBRE DE 2018"]


def test_fecha_v2_convive_con_monto_y_gazetteer():
    texto = "El 1o. de julio de 2021 el IMSS pagó 5 mil millones de pesos en Tabasco."
    tipos = {(e.tipo, e.texto) for e in F.extraer_reglas_v2(texto, 0)}
    assert ("FECHA", "1o. de julio de 2021") in tipos
    assert ("MONTO", "5 mil millones de pesos") in tipos
    assert ("ORG", "IMSS") in tipos and ("LOC", "Tabasco") in tipos


# =========================================================================== normalización


@pytest.mark.parametrize("texto,iso,precision,estado", [
    ("1o. de diciembre de 2018", "2018-12-01", "dia", "ok"),
    ("1º de julio de 2019", "2019-07-01", "dia", "ok"),
    ("quince de enero de 2021", "2021-01-15", "dia", "ok"),
    ("treinta y uno de diciembre de 2020", "2020-12-31", "dia", "ok"),
    ("enero de dos mil veinte", "2020-01", "mes", "ok"),
    ("3 de mayo del dos mil diecinueve", "2019-05-03", "dia", "ok"),
    ("dos mil diecinueve", "2019", "anio", "ok"),
    ("15 dic 2023", "2023-12-15", "dia", "ok"),
    ("15-dic-23", "2023-12-15", "dia", "ok"),
    ("15-dic-85", "", "dia", "ambiguo_siglo"),
    ("dic. 2023", "2023-12", "mes", "ok"),
    ("15-12-2023", "2023-12-15", "dia", "ok"),
    ("15.12.2023", "2023-12-15", "dia", "ok"),
    ("2023-12-15", "2023-12-15", "dia", "ok"),
    ("31-02-2023", "", "dia", "no_resoluble"),
    ("12/2023", "2023-12", "mes", "ok"),
    # lo que v1 ya resolvía se delega sin cambios
    ("15 de diciembre de 2023", "2023-12-15", "dia", "ok"),
    ("2019", "2019", "anio", "ok"),
    ("1/1/85", "", "dia", "ambiguo_siglo"),
])
def test_normalizacion_v2(texto, iso, precision, estado):
    n = F.normalizar_fecha_v2(texto)
    assert (n["fecha_iso"], n["precision_fecha"], n["estado_fecha"]) == (iso, precision, estado)


@pytest.mark.parametrize("texto,inicio,fin", [
    ("2019 a 2024", "2019", "2024"),
    ("2019 y el 2024", "2019", "2024"),
    ("enero a marzo de 2021", "2021-01", "2021-03"),
    ("enero de 2020 a marzo de 2021", "2020-01", "2021-03"),
    ("15 de enero al 3 de febrero de 2021", "2021-01-15", "2021-02-03"),
    ("1 al 15 de enero de 2021", "2021-01-01", "2021-01-15"),  # forma de v1
])
def test_normalizacion_v2_intervalos(texto, inicio, fin):
    n = F.normalizar_fecha_v2(texto)
    assert (n["fecha_inicio"], n["fecha_fin"], n["precision_fecha"], n["estado_fecha"]) == (
        inicio, fin, "intervalo", "ok")


def test_normalizacion_v2_intervalos_no_resolubles():
    assert F.normalizar_fecha_v2("2024 a 2019")["estado_fecha"] == "no_resoluble"
    assert F.normalizar_fecha_v2("enero a marzo")["estado_fecha"] == "parcial_sin_anio"


def test_normalizacion_v2_relativas_con_ancla():
    ancla = date(2023, 12, 20)
    assert F.normalizar_fecha_v2("próximo quince de enero", ancla)["fecha_iso"] == "2024-01-15"
    assert F.normalizar_fecha_v2("próximo 1o. de enero", ancla)["fecha_iso"] == "2024-01-01"
    sin = F.normalizar_fecha_v2("próximo quince de enero")
    assert sin["fecha_iso"] == "" and sin["estado_fecha"] == "parcial_sin_ancla"


def test_canonizar_no_toca_el_span():
    texto = "Firmado el 1o. de diciembre de 2018."
    e = next(e for e in F.extraer_reglas_v2(texto, 0) if e.tipo == "FECHA")
    F.normalizar_fecha_v2(e.texto)
    assert texto[e.inicio:e.fin] == "1o. de diciembre de 2018"


def test_invariante_de_offsets_en_200_pasajes_reales():
    """Solo comprueba offsets y que no queden solapes; no imprime ni compara contenido."""
    import itertools

    import pandas as pd

    from mtx import config

    p = pd.read_parquet(config.PASAJES_PARQUET, columns=["texto", "inicio_cuerpo"])
    muestra = pd.concat([p[p["inicio_cuerpo"] > 0].sample(150, random_state=config.SEMILLA),
                         p.sample(50, random_state=config.SEMILLA + 1)])
    for texto, ic in zip(muestra["texto"], muestra["inicio_cuerpo"]):
        ents = F.extraer_reglas_v2(texto, int(ic))
        for e in ents:
            assert texto[e.inicio:e.fin] == e.texto and e.en_marca == (e.inicio < int(ic))
        orden = [(e.inicio, e.fin) for e in ents]
        assert all(a[1] <= b[0] for a, b in itertools.pairwise(orden)), "solapes tras resolver"
