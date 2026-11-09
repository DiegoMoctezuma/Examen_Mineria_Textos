"""T11 · Reglas y gazetteers (PRD §6.7.10, anexo B). Suite bloqueante.

Los ejemplos son sintéticos: no son anotaciones del corpus. Un caso que falle se conserva con
`xfail(strict=True)` y su razón; no se borra ni se maquilla.
"""
from __future__ import annotations

import itertools
from datetime import date

import pandas as pd
import pytest

from mtx import config
from mtx import reglas as R
from mtx.normalizacion import normalizar_fecha, normalizar_monto


def _tipo(texto: str, tipo: str, inicio_cuerpo: int = 0) -> list[str]:
    return [e.texto for e in R.extraer_reglas(texto, inicio_cuerpo) if e.tipo == tipo]


def _invariante(texto: str, entidades) -> None:
    for e in entidades:
        assert 0 <= e.inicio < e.fin <= len(texto)
        assert texto[e.inicio:e.fin] == e.texto


# =========================================================================== FECHA (§6.7.1)

FECHAS_POSITIVAS = [
    ("El 15 de diciembre de 2023 se inauguró.", "15 de diciembre de 2023"),
    ("Desde el primero de enero de 2020 aplica.", "primero de enero de 2020"),
    ("A partir del 1 de septiembre del 2021.", "1 de septiembre del 2021"),
    ("Se firmó en enero de 2021.", "enero de 2021"),
    ("Ocurrió en diciembre del 2019.", "diciembre del 2019"),
    ("Con fecha 15/12/2023 se publicó.", "15/12/2023"),
    ("Con fecha 1/1/19 se publicó.", "1/1/19"),
    ("Será el próximo 15 de enero en Palenque.", "próximo 15 de enero"),
    ("Fue el pasado 20 de noviembre.", "pasado 20 de noviembre"),
    ("Arranca este 1 de julio.", "este 1 de julio"),
    ("Se terminó en diciembre de 2021.", "diciembre de 2021"),
    ("Empezó en 2019 con el programa.", "2019"),
    ("Durante el año 2019 se avanzó.", "2019"),
    ("Funciona desde 2019.", "2019"),
    ("Vacunación del 1 al 15 de enero de 2021 en todo el país.", "1 al 15 de enero de 2021"),
]


@pytest.mark.parametrize("texto,esperado", FECHAS_POSITIVAS)
def test_fecha_positivos_span_exacto(texto, esperado):
    assert _tipo(texto, "FECHA") == [esperado]
    _invariante(texto, R.extraer_reglas(texto, 0))


FECHAS_NEGATIVAS = [
    "Llegaron 15 personas.", "Ver la página 15.", "Duró 2 horas.", "En 15 de los 32 estados.",
    "Son 15 de cada 100.", "El código 2019 no aplica.", "Asistieron más de 2000 personas.",
]


@pytest.mark.parametrize("texto", FECHAS_NEGATIVAS)
def test_fecha_negativos_sin_coincidencias(texto):
    assert _tipo(texto, "FECHA") == []


def test_31_de_febrero_se_detecta_pero_no_se_resuelve():
    assert _tipo("Dijo que el 31 de febrero de 2021 pagaría.", "FECHA") == ["31 de febrero de 2021"]
    n = normalizar_fecha("31 de febrero de 2021")
    assert n["fecha_iso"] == "" and n["estado_fecha"] == "no_resoluble"
    assert normalizar_fecha("31 de febrero")["estado_fecha"] == "no_resoluble"


def test_rango_de_anios_emite_dos_fechas_no_cubierto_como_intervalo():
    """No cubierto (PRD §6.7.1): `de 2019 a 2024` da dos FECHA de año."""
    assert _tipo("Creció de 2019 a 2024.", "FECHA") == ["2019", "2024"]


@pytest.mark.xfail(strict=True, reason="No cubierto (PRD §6.7.1): fechas totalmente en palabras")
def test_fecha_en_palabras_no_cubierta():
    assert _tipo("Será el quince de enero.", "FECHA") == ["quince de enero"]


@pytest.mark.parametrize("texto,iso,precision,estado", [
    ("15 de diciembre de 2023", "2023-12-15", "dia", "ok"),
    ("primero de enero de 2020", "2020-01-01", "dia", "ok"),
    ("1 de septiembre del 2021", "2021-09-01", "dia", "ok"),
    ("diciembre de 2021", "2021-12", "mes", "ok"),
    ("2019", "2019", "anio", "ok"),
    ("15/12/2023", "2023-12-15", "dia", "ok"),
    ("1/1/19", "2019-01-01", "dia", "ok"),
    ("1/1/85", "", "dia", "ambiguo_siglo"),
    ("29 de febrero de 2023", "", "dia", "no_resoluble"),
    ("29 de febrero de 2024", "2024-02-29", "dia", "ok"),
])
def test_normalizacion_fecha(texto, iso, precision, estado):
    n = normalizar_fecha(texto)
    assert (n["fecha_iso"], n["precision_fecha"], n["estado_fecha"]) == (iso, precision, estado)


def test_normalizacion_intervalo_y_relativas_con_ancla():
    n = normalizar_fecha("1 al 15 de enero de 2021")
    assert (n["fecha_inicio"], n["fecha_fin"], n["precision_fecha"]) == (
        "2021-01-01", "2021-01-15", "intervalo")
    ancla = date(2023, 12, 20)
    assert normalizar_fecha("próximo 15 de enero", ancla)["fecha_iso"] == "2024-01-15"
    assert normalizar_fecha("pasado 20 de noviembre", ancla)["fecha_iso"] == "2023-11-20"
    sin = normalizar_fecha("próximo 15 de enero")
    assert sin["fecha_iso"] == "" and sin["estado_fecha"] == "parcial_sin_ancla"


# =========================================================================== MONTO (§6.7.2)

MONTOS_POSITIVOS = [
    "20 mil millones de pesos", "2 mil 500 millones de pesos", "1,200 millones de pesos",
    "$1,200 millones", "$ 5 mil", "5 mil pesos", "500 pesos", "2 mil millones de dólares",
    "100 millones de dólares", "1.5 billones de pesos", "6 mil 300 pesos", "mil 200 pesos",
    "un millón de pesos", "dos mil millones de pesos",
]


@pytest.mark.parametrize("monto", MONTOS_POSITIVOS)
def test_monto_positivos_span_exacto(monto):
    texto = f"Se invirtieron {monto} en la obra."
    assert _tipo(texto, "MONTO") == [monto]
    _invariante(texto, R.extraer_reglas(texto, 0))


@pytest.mark.parametrize("texto", [
    "Llegaron 20 mil personas.", "Se aplicaron 15 millones de dosis.",
    "Se sembraron 3 millones de árboles.", "Subió 20 por ciento.", "Subió 20%.",
    "Ver la página 20.", "Subió 20 por año.",
])
def test_monto_negativos(texto):
    assert _tipo(texto, "MONTO") == []


def test_monto_no_empieza_a_mitad_de_cifra():
    assert _tipo("Costó 1500 pesos.", "MONTO") == ["1500 pesos"]


@pytest.mark.parametrize("texto,valor,moneda,escala", [
    ("20 mil millones de pesos", "20000000000", "MXN", "mil_millones"),
    ("2 mil 500 millones de pesos", "2500000000", "MXN", "mil_millones"),
    ("1,200 millones de pesos", "1200000000", "MXN", "mil_millones"),
    ("$1,200 millones", "1200000000", "", "mil_millones"),
    ("$ 5 mil", "5000", "", "mil"),
    ("500 pesos", "500", "MXN", "uno"),
    ("2 mil millones de dólares", "2000000000", "USD", "mil_millones"),
    ("1.5 billones de pesos", "1500000000000", "MXN", "billones"),
    ("6 mil 300 pesos", "6300", "MXN", "mil"),
    ("mil 200 pesos", "1200", "MXN", "mil"),
    ("un millón de pesos", "1000000", "MXN", "millones"),
    ("dos mil millones de pesos", "2000000000", "MXN", "mil_millones"),
])
def test_normalizacion_monto(texto, valor, moneda, escala):
    n = normalizar_monto(texto)
    assert (n["valor_num"], n["moneda"], n["escala"]) == (valor, moneda, escala)


def test_monto_punto_de_miles_queda_sin_valor():
    """No cubierto (PRD §6.7.2): `1.200 pesos` es ambiguo; se detecta sin valor numérico."""
    assert _tipo("Costó 1.200 pesos.", "MONTO") == ["1.200 pesos"]
    assert normalizar_monto("1.200 pesos")["estado_monto"] == "ambiguo"


# =========================================================================== auxiliares (§6.7.3)


@pytest.mark.parametrize("texto,tipo,valor,unidad", [
    ("Subió 20%.", "PORCENTAJE", 20.0, "porcentaje"),
    ("Subió 20 por ciento.", "PORCENTAJE", 20.0, "porcentaje"),
    ("Subió 3.5 por ciento.", "PORCENTAJE", 3.5, "porcentaje"),
    ("Llegaron 15 millones de dosis.", "CANTIDAD", 15e6, "dosis"),
    ("Se robaron 100 mil litros.", "CANTIDAD", 1e5, "litros"),
    ("Participan 30 mil elementos.", "CANTIDAD", 3e4, "elementos"),
    ("Hay 200 mil sembradores.", "CANTIDAD", 2e5, "sembradores"),
    ("Abrieron 2 mil 700 sucursales.", "CANTIDAD", 2700.0, "sucursales"),
])
def test_cantidades_auxiliares(texto, tipo, valor, unidad):
    det = R.extraer_reglas_detalle(texto, 0)
    assert [(a.tipo_aux, a.valor_num, a.unidad) for a in det.auxiliares] == [(tipo, valor, unidad)]
    assert all(e.tipo != "MONTO" for e in det.entidades)
    assert not any(isinstance(a, R.Entidad) for a in det.auxiliares)
    for a in det.auxiliares:
        assert texto[a.inicio:a.fin] == a.texto


# =========================================================================== gazetteer (§6.7.4-7)


@pytest.fixture(scope="module")
def extendido():
    return R.construir_extendido(revision=config.RAIZ / "no_existe.csv")


OBLIGATORIAS = ["IMSS", "ISSSTE", "Pemex", "CFE", "Sedena", "Semar", "Conagua", "Fonatur",
                "Insabi", "Cofepris", "Birmex", "Pfizer", "AstraZeneca", "CanSino", "Sputnik V",
                "COVAX", "Coparmex", "CCE", "Concanaco", "Conasami", "Morena", "PAN", "PRI", "PRD",
                "ONU", "OMS", "OPS", "FMI", "Banco Mundial", "Banxico", "SAT", "Guardia Nacional",
                "Secretaría del Bienestar", "STPS", "SICT", "Sener", "Sedatu", "Grupo Carso",
                "ICA"]


@pytest.mark.parametrize("forma", OBLIGATORIAS)
def test_gazetteer_entradas_obligatorias(extendido, forma):
    formas = {f for r in extendido.to_dict("records") for f in R._formas(r)}
    assert forma in formas
    assert _tipo(f"Habló con {forma} ayer.", "ORG") == [forma]


def test_extendido_columnas_y_etiquetas(extendido):
    assert list(extendido.columns) == R.COLUMNAS_GAZ
    assert set(extendido["etiqueta"]) <= {"ORG", "LOC"}
    assert set(extendido["origen"]) <= {"kit", "minado", "manual"}
    kit = pd.read_csv(R.KIT_GAZETTEER, dtype=str)
    assert len(kit) == 76
    obras = extendido[extendido["tipo"] == "obra"]
    assert len(obras) == 4 and set(obras["etiqueta"]) == {"LOC"}


def test_gazetteer_loc_32_entidades_y_lugares():
    loc = pd.read_csv(R.GAZ_LOC, dtype=str, keep_default_na=False)
    assert list(loc.columns) == R.COLUMNAS_GAZ
    assert (loc["tipo"] == "estado").sum() == 32
    for lugar in ["Palenque", "Cancún", "Tulum", "Mérida", "Chetumal", "Escárcega", "Tula",
                  "Salamanca", "Minatitlán", "Salina Cruz", "Coatzacoalcos", "Santa Lucía",
                  "Istmo de Tehuantepec", "Estados Unidos", "Washington", "China", "Rusia",
                  "India", "Argentina", "Cuba", "CDMX", "Edomex", "Michoacán de Ocampo",
                  "Veracruz de Ignacio de la Llave", "Coahuila de Zaragoza"]:
        assert _tipo(f"Fuimos a {lugar} ayer.", "LOC") == [lugar], lugar


@pytest.mark.parametrize("texto,esperado", [
    ("Avanza el Tren Maya.", "Tren Maya"), ("Vive en la Ciudad de México.", "Ciudad de México"),
    ("La refinería de Dos Bocas.", "Dos Bocas"), ("Visitó la refinería Olmeca.", "refinería Olmeca"),
    ("Se inauguró el AIFA.", "AIFA"), ("Avanza el Tren Interoceánico.", "Tren Interoceánico"),
])
def test_obras_y_lugares_son_loc(texto, esperado):
    assert _tipo(texto, "LOC") == [esperado]


def test_longest_match_dentro_del_gazetteer():
    t = "El Aeropuerto Internacional Felipe Ángeles y el Banco del Bienestar."
    assert _tipo(t, "LOC") == ["Aeropuerto Internacional Felipe Ángeles"]
    assert _tipo(t, "ORG") == ["Banco del Bienestar"]
    assert _tipo("Llegó a Baja California Sur.", "LOC") == ["Baja California Sur"]


def test_siglas_sensibles_a_mayusculas_y_palabra_comun():
    assert _tipo("El IMSS y el imss.", "ORG") == ["IMSS"]
    assert _tipo("Compré pan y el PAN votó.", "ORG") == ["PAN"]
    assert _tipo("El SAT y el sat.", "ORG") == ["SAT"]
    assert _tipo("La vacuna de COVAX.", "ORG") == ["COVAX"]
    assert _tipo("Pemex y PEMEX y pemex.", "ORG") == ["Pemex", "PEMEX"]
    assert _tipo("Un guerrero en Guerrero.", "LOC") == ["Guerrero"]


def test_limites_de_palabra_con_acentos():
    assert _tipo("Palenqueño y Palenque.", "LOC") == ["Palenque"]
    assert _tipo("Méridaña y Mérida.", "LOC") == ["Mérida"]
    assert _tipo("El IMSSó no existe.", "ORG") == []


def test_secretaria_con_lugar_es_una_sola_org():
    t = "La Secretaría de Salud de Tabasco informó."
    assert _tipo(t, "ORG") == ["Secretaría de Salud de Tabasco"]
    assert _tipo(t, "LOC") == []


def test_siglas_de_palabra_comun_no_se_buscan_solas():
    assert _tipo("La pensión del Bienestar y la Salud.", "ORG") == []
    assert _tipo("La Secretaría de Salud informó.", "ORG") == ["Secretaría de Salud"]


def test_farmaceuticas_y_vacunas_son_org_y_patria_requiere_contexto():
    t = "Llegaron Pfizer, AstraZeneca, Sputnik V, CanSino y la vacuna Patria; viva la Patria."
    assert _tipo(t, "ORG") == ["Pfizer", "AstraZeneca", "Sputnik V", "CanSino", "Patria"]
    assert _tipo("La Patria es primero.", "ORG") == []


# =========================================================================== marca (§6.7.6)


def _marca(texto: str):
    ic = texto.index(":") + 2
    return [(e.tipo, e.texto, e.fuente, e.en_marca) for e in R.extraer_reglas(texto, ic)
            if e.inicio < ic]


def test_marca_cargo_coma_nombre():
    assert _marca("SECRETARIO DE SALUD, JORGE ALCOCER VARELA: Buenos días.") == [
        ("PER", "JORGE ALCOCER VARELA", "marca", True)]


def test_marca_nombre_coma_cargo_formato_del_corpus():
    r = _marca("ZOÉ ROBLEDO ABURTO, DIRECTOR GENERAL DEL INSTITUTO MEXICANO DEL SEGURO SOCIAL "
               "(IMSS): Gracias.")
    assert ("PER", "ZOÉ ROBLEDO ABURTO", "marca", True) in r
    assert ("ORG", "IMSS", "gazetteer_org", True) in r
    assert ("ORG", "INSTITUTO MEXICANO DEL SEGURO SOCIAL", "gazetteer_org", True) in r


def test_marca_presidente_quita_cargo_por_lista():
    assert _marca("PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: Muy bien.") == [
        ("PER", "ANDRÉS MANUEL LÓPEZ OBRADOR", "marca", True)]


def test_marca_sin_coma_que_coincide_con_gazetteer_es_org():
    assert _marca("SECRETARÍA DE LA DEFENSA NACIONAL (SEDENA): Informe.") == [
        ("ORG", "SECRETARÍA DE LA DEFENSA NACIONAL", "gazetteer_org", True),
        ("ORG", "SEDENA", "gazetteer_org", True)]


@pytest.mark.parametrize("marca", ["PREGUNTA", "INTERLOCUTOR", "INTERLOCUTORA", "VOZ MUJER",
                                   "VOZ DE HOMBRE", "INTERVENCIÓN", "MODERADORA"])
def test_marcas_genericas_sin_entidad(marca):
    assert _marca(f"{marca}: ¿Qué opina?") == []


# =========================================================================== colisiones (§6.7.8)


def test_colision_gana_el_span_mas_largo():
    largo = R.Entidad("ORG", "Banco de México", 0, 15, fuente="gazetteer_org")
    corto = R.Entidad("LOC", "México", 9, 15, fuente="gazetteer_loc")
    ganadoras, col = R.resolver_colisiones([corto, largo])
    assert ganadoras == [largo]
    assert col[0].suprimida == corto and col[0].motivo == "span_mas_largo"


def test_colision_empate_por_jerarquia():
    fecha = R.Entidad("FECHA", "2019", 5, 9, fuente="regex_fecha")
    loc = R.Entidad("LOC", "2019", 5, 9, fuente="gazetteer_loc")
    org = R.Entidad("ORG", "ABCD", 5, 9, fuente="gazetteer_org")
    marca = R.Entidad("PER", "ABCD", 5, 9, fuente="marca")
    ganadoras, col = R.resolver_colisiones([marca, org, loc, fecha])
    assert ganadoras == [fecha]
    assert [c.suprimida.fuente for c in col] == ["gazetteer_loc", "gazetteer_org", "marca"]
    assert all(c.motivo == "jerarquia" for c in col)
    filas = R.filas_colisiones("1_1", col)
    assert set(filas[0]) == set(R.COLUMNAS_COLISIONES)


def test_jerarquia_regex_sobre_gazetteer():
    assert R.JERARQUIA == ("regex_fecha", "regex_monto", "gazetteer_loc", "gazetteer_org",
                           "marca")


# =========================================================================== offsets reales (T11)


@pytest.mark.skipif(not config.PASAJES_PARQUET.exists(), reason="requiere make corpus")
def test_invariante_de_offsets_en_200_pasajes_reales():
    p = pd.read_parquet(config.PASAJES_PARQUET, columns=["texto", "inicio_cuerpo"])
    con_marca = p[p["inicio_cuerpo"] > 0].sample(150, random_state=config.SEMILLA)
    sin_marca = p.sample(50, random_state=config.SEMILLA + 1)
    total = 0
    for texto, ic in zip(pd.concat([con_marca, sin_marca])["texto"],
                         pd.concat([con_marca, sin_marca])["inicio_cuerpo"]):
        det = R.extraer_reglas_detalle(texto, int(ic))
        _invariante(texto, det.entidades)
        for a in det.auxiliares:
            assert texto[a.inicio:a.fin] == a.texto
        for e in det.entidades:
            assert e.en_marca == (e.inicio < int(ic))
        orden = [(e.inicio, e.fin) for e in det.entidades]
        assert all(a[1] <= b[0] for a, b in itertools.pairwise(orden)), "solapes tras resolver"
        total += len(det.entidades)
    assert total > 0


# =========================================================================== FECHA: ampliaciones
# Añadidas antes del gold tras revisar los 99 pasajes del ámbito (docs/decisiones.md): meses sin
# día con contexto temporal y años seguidos de verbo. Ejemplos sintéticos.


@pytest.mark.parametrize("texto,esperado", [
    ("Queremos que en 2021 esté en funcionamiento.", "2021"),
    ("Para enero aumenta la pensión.", "enero"),
    ("Opera a partir de diciembre de este año.", "diciembre de este año"),
    ("Se inaugura el mes de noviembre del presente año.", "noviembre del presente año"),
    ("Queremos que para enero del 24 cobren el doble.", "enero del 24"),
    ("Va a estar lista en junio.", "junio"),
])
def test_fecha_mes_sin_dia_y_anio_con_verbo(texto, esperado):
    assert _tipo(texto, "FECHA") == [esperado]


@pytest.mark.parametrize("texto", ["Se hicieron en 2000 casas.", "Es el Cinco de Mayo.",
                                   "Le dicen Mayo.", "Hay más de 2000 elementos."])
def test_fecha_ampliaciones_negativos(texto):
    assert _tipo(texto, "FECHA") == []


def test_normalizacion_mes_relativo():
    ancla = date(2023, 6, 10)
    assert normalizar_fecha("enero del 24")["fecha_iso"] == "2024-01"
    assert normalizar_fecha("diciembre de este año", ancla)["fecha_iso"] == "2023-12"
    assert normalizar_fecha("julio", ancla)["fecha_iso"] == "2023-07"
    assert normalizar_fecha("julio")["estado_fecha"] == "parcial_sin_ancla"
