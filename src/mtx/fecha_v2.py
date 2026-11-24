"""Reglas FECHA v2 (PRD v2 WP-11, D33): amplían las de v1 sin modificarlas.

`reglas.py` y `normalizacion.py` quedan como en `reglas-congeladas`, para que las cifras de FECHA
v1 se puedan reproducir (`scripts/08_extraer.py` compara esos archivos contra la etiqueta). Este
módulo detecta todo lo que detecta v1 y además los formatos que sugiere la referencia del profesor
(`docs/fecha_v2_origen.md`), adaptados al español:

- día ordinal (`1o. de diciembre`, `1º de julio`) y día en palabras (`quince de enero`);
- año en palabras tras mes o tras "año" (`enero de dos mil veinte`, `el año dos mil diecinueve`);
- mes abreviado con día y año (`15 dic 2023`, `15-dic-23`, `dic. 2023`);
- numéricas con guion o punto (`15-12-2023`, `15.12.2023`), ISO (`2023-12-15`) y mes/año (`12/2023`);
- intervalos explícitos de días entre meses, de meses y de años (`15 de enero al 3 de febrero`,
  `enero a marzo de 2021`, `2019 a 2024`): una sola entidad, como pide el criterio v1.

Ante dos candidatas FECHA que se solapan gana la más larga (a igual longitud, la que empieza antes),
así un intervalo reemplaza a las dos fechas sueltas que v1 emitía. Mismas reglas de span que v1
(D13): el modificador relativo va dentro; preposiciones y artículos introductorios, fuera.
"""
from __future__ import annotations

import re
from datetime import date

from mtx import reglas as R
from mtx.normalizacion import SIGLO_DOS_DIGITOS, _fecha, _vacio_fecha, normalizar_fecha

Entidad = R.Entidad

# =========================================================================== piezas

_DIAS_PALABRA = {
    "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
    "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciséis": 16, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintidós": 22, "veintidos": 22, "veintitrés": 23,
    "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30, "treinta y uno": 31,
}
_ABREV = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
          "sept": 9, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}
_NOMBRE_MES = {v: k for k, v in R.MESES.items() if k != "setiembre"}


def _alternancia(palabras, capitalizar=False) -> str:
    formas = []
    for p in sorted(palabras, key=len, reverse=True):
        formas.append(re.escape(p).replace(r"\ ", r"\s+"))
        if capitalizar:
            formas.append(re.escape(p[0].upper() + p[1:]).replace(r"\ ", r"\s+"))
    return "(?:" + "|".join(formas) + ")"


_MES = R._MES
# Con el día en palabras el mes va en minúscula: "Cinco de Mayo" es un nombre propio (v1 ya lo
# excluye en sus pruebas), "cinco de mayo" es una fecha. Por eso esta parte no ignora mayúsculas.
_MES_MINUS = "(?-i:" + _alternancia(R.MESES) + ")"
_DIA_PAL = "(?-i:" + _alternancia(_DIAS_PALABRA, capitalizar=True) + ")"
_DIA_ORD = r"(?:0?1\s?(?:o\.?|º|°|ro\.?|ero\.?))(?![\wáéíóúñü])"
_DIA = rf"(?:{_DIA_ORD}|{R._DIA})"
_ABR = r"(?:" + "|".join(sorted(_ABREV, key=len, reverse=True)) + r")"
_ANIO = R._ANIO
_UNIDADES_ANIO = [k for k, v in _DIAS_PALABRA.items() if v <= 30]
_ANIO_PAL = rf"(?:dos\s+mil(?:\s+{_alternancia(_UNIDADES_ANIO)})?(?![\wáéíóúñü]))"
_ANIO_PAL_ESTRICTO = rf"(?:dos\s+mil\s+{_alternancia(_UNIDADES_ANIO)}(?![\wáéíóúñü]))"
_DE_ANIO = rf"\s+(?:de|del)\s+(?:año\s+)?(?:{_ANIO}|{_ANIO_PAL})"
_MOD = R._MOD
_IZQ, _DER = R.IZQ, R.DER
_FIN_ANIO = R._FIN_ANIO
_NO_SUSTANTIVO = rf"(?!\s+(?!{R._TRAS_ANIO}{_DER})[a-záéíóúñü]+s{_DER})"
_SEP = r"[\s\-/.]+"

# Cada patrón tiene un solo grupo con nombre: el span de la entidad. Se aplican por separado (no en
# alternancia) para que un patrón no consuma el texto que otro reconocería más largo.
PATRONES_V2 = {
    # día en cifra u ordinal, con año en cifra o en palabras: "1o. de diciembre de 2018"
    "dia_mes": rf"{_IZQ}(?P<dia_mes>(?:{_MOD}\s+)?{_DIA}\s+de\s+{_MES}(?:{_DE_ANIO})?){_DER}",
    # día en palabras: "quince de enero", "dos de octubre de mil..." (año en cifra o palabras)
    "dia_palabra": (rf"{_IZQ}(?P<dia_palabra>(?:{_MOD}\s+)?{_DIA_PAL}\s+de\s+{_MES_MINUS}"
                    rf"(?:{_DE_ANIO})?){_DER}"),
    # mes con año en palabras: "enero de dos mil veinte"
    "mes_anio": rf"{_IZQ}(?P<mes_anio>(?:{_MOD}\s+)?{_MES}{_DE_ANIO}){_DER}",
    # mes abreviado con día y año: "15 dic 2023", "15-dic-23", "15 dic. 2023"
    "dia_abrev": (rf"(?<![\w/.\-])(?P<dia_abrev>{R._DIA}{_SEP}{_ABR}\.?{_SEP}(?:{_ANIO}|\d{{2}}))"
                  r"(?![\wáéíóúñü])(?![/.\-]\w)"),
    # mes abreviado y año: "dic. 2023", "dic-2023"; "mar" y "may" sin punto son palabras comunes
    "abrev_anio": (rf"{_IZQ}(?P<abrev_anio>(?:(?:{_ABR})\.|(?:{_ABR})-|"
                   rf"(?:ene|feb|abr|jun|jul|ago|sept|sep|oct|nov|dic)(?=\s))\s*{_ANIO})"
                   rf"(?![\d,.]\d)"),
    # numérica con guion o punto, día-mes-año: "15-12-2023", "15.12.2023"
    "numerica_sep": (r"(?<![\d/.\-])(?P<numerica_sep>(?:0?[1-9]|[12]\d|3[01])(?P<sep>[\-.])"
                     rf"(?:0?[1-9]|1[0-2])(?P=sep){_ANIO})(?![\wáéíóúñü])(?![/.\-]\w)"),
    # ISO: "2023-12-15"
    "iso": (rf"(?<![\d\-])(?P<iso>{_ANIO}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))"
            r"(?![\d\-])"),
    # mes/año: "12/2023"
    "mes_num": rf"(?<![\d/])(?P<mes_num>(?:0?[1-9]|1[0-2])/{_ANIO})(?![\d/])",
    # intervalo de días entre meses: "15 de enero al 3 de febrero de 2021"
    "iv_dias": (rf"{_IZQ}(?P<iv_dias>{_DIA}\s+de\s+{_MES}(?:{_DE_ANIO})?\s+(?:al|hasta\s+el)\s+"
                rf"{_DIA}\s+de\s+{_MES}(?:{_DE_ANIO})?){_DER}"),
    # intervalo de meses con año al final: "enero a marzo de 2021", "enero de 2020 a marzo de 2021"
    "iv_meses": (rf"{_IZQ}(?P<iv_meses>{_MES}(?:{_DE_ANIO})?\s+(?:a|al|hasta)\s+{_MES}{_DE_ANIO})"
                 rf"{_DER}"),
    # intervalo de meses sin año, solo con "de" o "desde" delante: "de enero a marzo"
    "iv_meses_ctx": (rf"{_IZQ}(?:de|desde)\s+(?P<iv_meses_ctx>{_MES}\s+(?:a|al|hasta)\s+{_MES})"
                     rf"{_DER}(?!{_DE_ANIO})"),
    # intervalo de años: "de 2019 a 2024", "del 2019 al 2024", "desde 2019 hasta 2024"
    "iv_anios": (rf"{_IZQ}(?:de|del|desde(?:\s+el)?)\s+(?P<iv_anios>{_ANIO}\s+(?:a|al|hasta"
                 rf"(?:\s+el)?)\s+{_ANIO}){_FIN_ANIO}{_NO_SUSTANTIVO}"),
    # "entre 2019 y 2024" (una enumeración sin "entre" da fechas separadas, como en v1)
    "iv_anios_entre": (rf"{_IZQ}entre(?:\s+el)?\s+(?P<iv_anios_entre>{_ANIO}\s+y\s+(?:el\s+)?"
                       rf"{_ANIO}){_FIN_ANIO}{_NO_SUSTANTIVO}"),
    # año en palabras tras "año": "el año dos mil diecinueve"
    "anio_palabra": rf"{_IZQ}(?:el\s+año|del\s+año|año)\s+(?P<anio_palabra>{_ANIO_PAL}){_DER}",
    # año en palabras tras "en el", "desde el"...: exige la unidad ("dos mil" solo es cantidad)
    "anio_palabra_ctx": (rf"{_IZQ}(?:en|desde|hasta|para|durante)\s+el\s+"
                         rf"(?P<anio_palabra_ctx>{_ANIO_PAL_ESTRICTO}){_NO_SUSTANTIVO}"),
}
_COMPILADOS = {n: re.compile(p, re.IGNORECASE) for n, p in PATRONES_V2.items()}


# =========================================================================== detección


# "de 2000 a 3000 personas": el primer número es una cantidad aunque parezca año (v1 lo tomaba).
_RE_RANGO_CANTIDAD = re.compile(rf"\s+(?:a|al|y|e|hasta)\s+\d[\d,.]*\s+[a-záéíóúñü]+s{_DER}",
                                re.IGNORECASE)


def _es_rango_de_cantidades(texto: str, ini: int, fin: int) -> bool:
    return texto[ini:fin].isdigit() and bool(_RE_RANGO_CANTIDAD.match(texto, fin))


def buscar_fechas_v2(texto: str) -> list[Entidad]:
    """Candidatas de v1 más las de v2; entre FECHA que se solapan gana la más larga."""
    cand = [(e.inicio, e.fin) for e in R.buscar_fechas(texto)
            if not _es_rango_de_cantidades(texto, e.inicio, e.fin)]
    for nombre, rx in _COMPILADOS.items():
        for m in rx.finditer(texto):
            cand.append(m.span(nombre))
    elegidas: list[tuple[int, int]] = []
    for ini, fin in sorted(set(cand), key=lambda s: (-(s[1] - s[0]), s[0])):
        if all(fin <= a or b <= ini for a, b in elegidas):
            elegidas.append((ini, fin))
    return [R.Entidad("FECHA", texto[a:b], a, b, fuente="regex_fecha") for a, b in sorted(elegidas)]



def extraer_reglas_v2_detalle(texto: str, inicio_cuerpo: int, gaz=None) -> R.ResultadoReglas:
    """Igual que `reglas.extraer_reglas_detalle`, con FECHA v2 en lugar de FECHA v1. MONTO,
    gazetteers, marca, auxiliares y colisiones son los de v1, sin cambios."""
    gazetteer, tipos_loc = gaz or R.gazetteer_por_defecto()
    cand: list[Entidad] = buscar_fechas_v2(texto) + R.buscar_montos(texto)
    for ini, fin, p, _ext in R._extender_org_con_lugar(texto, gazetteer.buscar(texto), tipos_loc):
        fuente = "gazetteer_loc" if p.etiqueta == "LOC" else "gazetteer_org"
        cand.append(Entidad(p.etiqueta, texto[ini:fin], ini, fin, fuente=fuente,
                            en_marca=ini < inicio_cuerpo))
    per = R.entidad_marca(texto, inicio_cuerpo)
    if per:
        cand.append(per)
    cand = [Entidad(e.tipo, e.texto, e.inicio, e.fin, e.metodo, e.fuente,
                    e.en_marca or e.inicio < inicio_cuerpo) for e in cand]
    entidades, colisiones = R.resolver_colisiones(cand)
    return R.ResultadoReglas(entidades, R.buscar_auxiliares(texto), colisiones)


def extraer_reglas_v2(texto: str, inicio_cuerpo: int) -> list[Entidad]:
    return extraer_reglas_v2_detalle(texto, inicio_cuerpo).entidades


# =========================================================================== normalización

_RE_ORD = re.compile(r"(?<!\d)0?1\s?(?:o\.?|º|°|ro\.?|ero\.?)(?=\s)", re.IGNORECASE)
_RE_ANIO_PAL = re.compile(rf"{_ANIO_PAL}", re.IGNORECASE)
_RE_DIA_PAL = re.compile(rf"{_IZQ}{_alternancia(_DIAS_PALABRA)}(?=\s+de\s)", re.IGNORECASE)
_RE_ABREV = re.compile(rf"(?<![\wáéíóúñü])({_ABR})\.?(?![\wáéíóúñü])", re.IGNORECASE)
_RE_ESPACIOS = re.compile(r"\s+")


def _anio_palabra(s: str) -> int:
    partes = _RE_ESPACIOS.sub(" ", s.lower()).split(" ", 2)
    return 2000 + (_DIAS_PALABRA[partes[2]] if len(partes) > 2 else 0)


def _anio_dos_digitos(yy: int) -> int | None:
    return 2000 + yy if yy <= SIGLO_DOS_DIGITOS else None


def canonizar(texto: str) -> str:
    """Lleva una FECHA v2 a la forma que entiende `normalizar_fecha` de v1: ordinal → cifra, día y
    año en palabras → cifras, mes abreviado → nombre completo. Solo para normalizar; el span de
    la entidad nunca cambia."""
    s = _RE_ESPACIOS.sub(" ", texto.strip())
    s = _RE_ORD.sub("1", s)
    s = _RE_ANIO_PAL.sub(lambda m: str(_anio_palabra(m.group(0))), s)
    s = re.sub(r"treinta\s+y\s+uno", "31", s, flags=re.IGNORECASE)
    s = _RE_DIA_PAL.sub(lambda m: str(_DIAS_PALABRA[m.group(0).lower()]), s)
    return s


_RE_ISO = re.compile(r"(?P<anio>\d{4})-(?P<mes>\d{2})-(?P<dia>\d{2})$")
_RE_NUM_SEP = re.compile(r"(?P<dia>\d{1,2})[\-.](?P<mes>\d{1,2})[\-.](?P<anio>\d{4})$")
_RE_MES_NUM = re.compile(r"(?P<mes>\d{1,2})/(?P<anio>\d{4})$")
_RE_DIA_ABREV = re.compile(rf"(?P<dia>\d{{1,2}}|primero){_SEP}(?P<mes>{_ABR})\.?{_SEP}"
                           r"(?P<anio>\d{4}|\d{2})$", re.IGNORECASE)
_RE_ABREV_ANIO = re.compile(rf"(?P<mes>{_ABR})[.\-]?\s*(?P<anio>\d{{4}})$", re.IGNORECASE)
_RE_IV_ANIOS = re.compile(r"(?P<a1>\d{4})\s+(?:a|al|hasta(?:\s+el)?|y(?:\s+el)?)\s+(?P<a2>\d{4})$",
                          re.IGNORECASE)
_RE_IV_MESES = re.compile(rf"(?P<m1>{_MES})(?:\s+(?:de|del)\s+(?:año\s+)?(?P<a1>\d{{4}}))?\s+"
                          rf"(?:a|al|hasta)\s+(?P<m2>{_MES})(?:\s+(?:de|del)\s+(?:año\s+)?"
                          r"(?P<a2>\d{4}))?$", re.IGNORECASE)
_RE_IV_DIAS = re.compile(rf"(?P<d1>\d{{1,2}}|primero)\s+de\s+(?P<m1>{_MES})(?:\s+(?:de|del)\s+"
                         rf"(?:año\s+)?(?P<a1>\d{{4}}))?\s+(?:al|hasta\s+el)\s+(?P<d2>\d{{1,2}}|"
                         rf"primero)\s+de\s+(?P<m2>{_MES})(?:\s+(?:de|del)\s+(?:año\s+)?"
                         r"(?P<a2>\d{4}))?$", re.IGNORECASE)


def _num_dia(s: str) -> int:
    return 1 if s.lower() == "primero" else int(s)


def _dia_ok(anio: int, mes: int, dia: int) -> dict:
    f = _fecha(anio, mes, dia)
    if f is None:
        return _vacio_fecha(precision_fecha="dia", estado_fecha="no_resoluble")
    return _vacio_fecha(fecha_iso=f.isoformat(), precision_fecha="dia", estado_fecha="ok")


def _mes_ok(anio: int, mes: int) -> dict:
    if not 1 <= mes <= 12:
        return _vacio_fecha(precision_fecha="mes", estado_fecha="no_resoluble")
    return _vacio_fecha(fecha_iso=f"{anio:04d}-{mes:02d}", precision_fecha="mes", estado_fecha="ok")


def _intervalo(inicio: str, fin: str) -> dict:
    if inicio > fin:
        return _vacio_fecha(precision_fecha="intervalo", estado_fecha="no_resoluble")
    return _vacio_fecha(fecha_inicio=inicio, fecha_fin=fin, precision_fecha="intervalo",
                        estado_fecha="ok")


def normalizar_fecha_v2(texto: str, ancla: date | None = None) -> dict:
    """Mismas columnas y estados que `normalizacion.normalizar_fecha`. Lo que v1 ya entiende (tras
    `canonizar`) se le delega; aquí solo se resuelven las formas nuevas."""
    s = canonizar(texto)
    if m := _RE_ISO.match(s) or _RE_NUM_SEP.match(s):
        return _dia_ok(int(m["anio"]), int(m["mes"]), int(m["dia"]))
    if m := _RE_MES_NUM.match(s):
        return _mes_ok(int(m["anio"]), int(m["mes"]))
    if m := _RE_DIA_ABREV.match(s):
        anio = int(m["anio"]) if len(m["anio"]) == 4 else _anio_dos_digitos(int(m["anio"]))
        if anio is None:
            return _vacio_fecha(precision_fecha="dia", estado_fecha="ambiguo_siglo")
        return _dia_ok(anio, _ABREV[m["mes"].lower()], _num_dia(m["dia"]))
    if m := _RE_ABREV_ANIO.match(s):
        return _mes_ok(int(m["anio"]), _ABREV[m["mes"].lower()])
    if m := _RE_IV_ANIOS.match(s):
        return _intervalo(m["a1"], m["a2"])
    if m := _RE_IV_DIAS.match(s):
        a2 = m["a2"] or m["a1"]
        a1 = m["a1"] or a2
        if a2 is None:
            return _vacio_fecha(precision_fecha="intervalo", estado_fecha="parcial_sin_anio",
                                fecha_ancla=ancla.isoformat() if ancla else "")
        f1 = _fecha(int(a1), R.MESES[m["m1"].lower()], _num_dia(m["d1"]))
        f2 = _fecha(int(a2), R.MESES[m["m2"].lower()], _num_dia(m["d2"]))
        if f1 is None or f2 is None:
            return _vacio_fecha(precision_fecha="intervalo", estado_fecha="no_resoluble")
        return _intervalo(f1.isoformat(), f2.isoformat())
    if m := _RE_IV_MESES.match(s):
        a2 = m["a2"] or m["a1"]
        a1 = m["a1"] or a2
        if a2 is None:
            return _vacio_fecha(precision_fecha="intervalo", estado_fecha="parcial_sin_anio",
                                fecha_ancla=ancla.isoformat() if ancla else "")
        return _intervalo(f"{int(a1):04d}-{R.MESES[m['m1'].lower()]:02d}",
                          f"{int(a2):04d}-{R.MESES[m['m2'].lower()]:02d}")
    return normalizar_fecha(s, ancla)
