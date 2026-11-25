"""Nombres legibles de pasajes para la demo web y las láminas (PRD v2 WP-15, S8b, D36).

El público nunca ve un `passage_id`: cada pasaje se presenta por su evento, su fecha y su número de
fragmento, por ejemplo "Mañanera del 12 de marzo de 2021 · fragmento 3", y por quién habla. Todo
sale de las columnas de `data/pasajes.parquet` (`titulo`, `fecha`, `posicion`, `interlocutor`,
`es_reportero`, `url`); el módulo no lee archivos.

El número de fragmento es `posicion + 1`: `posicion` empieza en 0 y "fragmento 0" no se lee bien.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
FECHA_DESCONOCIDA = "fecha desconocida"
LARGO_TEMA = 90
LARGO_HABLA = 90

# Tipos de evento con nombre corto: la etiqueta dice "<tipo> del <fecha>".
MANANERA = "Mañanera"
CONFERENCIA = "Conferencia de prensa"
DISCURSO = "Discurso"
TIPOS_CORTOS = (MANANERA, CONFERENCIA)

_RE_FECHA_TITULO = re.compile(r"^\s*\d{1,2}\.\d{1,2}\.\d{2,4}\s+")
_RE_VERSION = re.compile(r"^versi[oó]n estenogr[aá]fica(\.\s*|\s+de\s+la\s+)", re.IGNORECASE)
_RE_DESDE = re.compile(r",\s*desde\s+(?P<lugar>[^,].*?)\.?\s*$", re.IGNORECASE)
_RE_DEL_PRESIDENTE = re.compile(r"^discurso\s+del?\s+presidente\s+Andr[eé]s\s+Manuel\s+L[oó]pez\s+"
                                r"Obrador\s*", re.IGNORECASE)
_COMILLAS = str.maketrans("", "", "‘’“”\"")

# Interlocutores que no son una persona identificada.
PRENSA = "Pregunta de la prensa"
_PRENSA = {"INTERLOCUTORA", "INTERLOCUTOR", "PREGUNTA", "PREGUNTA INTERLOCUTORA",
           "PREGUNTA INTERLOCUTOR"}
_GENERICOS = (
    (re.compile(r"^(VOZ|INTERVENCI[OÓ]N)\b"), "Participante sin identificar"),
    (re.compile(r"^MODERADORA?$"), "Moderación"),
    (re.compile(r"^(DE\s+)?VIDEO$"), "Video"),
)
_PARTICULAS = {"a", "al", "de", "del", "e", "el", "en", "la", "las", "lo", "los", "o", "para",
               "por", "u", "y"}


@dataclass(frozen=True)
class Ficha:
    """Lo que el público ve de un pasaje. Ningún campo contiene IDs ni rutas."""

    titulo: str           # "Mañanera del 12 de marzo de 2021 · fragmento 3"
    evento: str           # "Mañanera" o el tema del evento
    fecha: str            # "12 de marzo de 2021" o "fecha desconocida"
    lugar: str | None     # "Morelia, Michoacán" cuando el título dice ", desde ..."
    fragmento: int        # posicion + 1
    habla: str            # "Presidente Andrés Manuel López Obrador", "Pregunta de la prensa", ...
    es_reportero: bool
    url: str | None       # versión estenográfica original


def fecha_larga(fecha) -> str:
    """`2021-03-12` → "12 de marzo de 2021"; vacía o inválida → "fecha desconocida"."""
    if fecha is None:
        return FECHA_DESCONOCIDA
    try:
        f = pd.Timestamp(fecha)
    except (ValueError, TypeError):
        return FECHA_DESCONOCIDA
    if pd.isna(f):
        return FECHA_DESCONOCIDA
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


def recortar(texto: str, largo: int) -> str:
    """Corta en la última palabra completa que cabe y agrega "…"."""
    texto = " ".join(str(texto).split())
    if len(texto) <= largo:
        return texto
    corte = texto[:largo - 1].rsplit(" ", 1)[0].rstrip(" ,;:.–-")
    return f"{corte}…"


def evento_y_lugar(titulo: str | None) -> tuple[str, str | None]:
    """Tipo o tema del evento a partir del título del discurso, y el lugar si dice ", desde ..."."""
    t = _RE_FECHA_TITULO.sub("", str(titulo or "")).strip()
    t = _RE_VERSION.sub("", t).translate(_COMILLAS).strip()
    if not t:
        return "Evento", None
    m = _RE_DESDE.search(t)
    lugar = m.group("lugar").strip() if m else None
    base = t[:m.start()].strip() if m else t
    baja = base.lower()
    if "conferencia de prensa matutina" in baja:
        return MANANERA, lugar
    if "conferencia de prensa" in baja:
        return CONFERENCIA, lugar
    if _RE_DEL_PRESIDENTE.match(base):
        resto = _RE_DEL_PRESIDENTE.sub("", base).strip()
        return recortar(f"{DISCURSO} {resto}".strip(), LARGO_TEMA), lugar
    tema = base[0].upper() + base[1:]
    return recortar(tema.rstrip("."), LARGO_TEMA), lugar


def _palabra(p: str, primera: bool) -> str:
    if p.startswith("(") or not any(c.isalpha() for c in p):
        return p                       # siglas entre paréntesis, números
    baja = p.lower()
    if not primera and baja in _PARTICULAS:
        return baja
    # "LÓPEZ-GATELL" → "López-Gatell"
    return "-".join(s[:1].upper() + s[1:] for s in baja.split("-"))


def nombre_propio(texto: str) -> str:
    """"ZOÉ ROBLEDO ABURTO, DIRECTOR GENERAL DEL INSTITUTO MEXICANO DEL SEGURO SOCIAL (IMSS)" →
    "Zoé Robledo Aburto, Director General del Instituto Mexicano del Seguro Social (IMSS)":
    mayúscula inicial, partículas en minúscula y siglas entre paréntesis intactas."""
    palabras = str(texto).split()
    return " ".join(_palabra(p, i == 0) for i, p in enumerate(palabras))


def quien_habla(interlocutor: str | None, es_reportero: bool = False) -> str:
    """Interlocutor legible. Lo que dice la prensa se distingue siempre (D36: nunca es respaldo)."""
    crudo = " ".join(str(interlocutor or "").split()).strip(" :.")
    clave = crudo.upper()
    if es_reportero or clave in _PRENSA:
        return PRENSA
    if not crudo:
        return "Participante sin identificar"
    for patron, nombre in _GENERICOS:
        if patron.match(clave):
            return nombre
    return recortar(nombre_propio(crudo), LARGO_HABLA)


def _valor(fila, campo: str, defecto=None):
    try:
        v = fila[campo]
    except (KeyError, IndexError):
        return defecto
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return defecto
    return v


def titulo_pasaje(evento: str, fecha: str, fragmento: int) -> str:
    """"Mañanera del 12 de marzo de 2021 · fragmento 3"; con tema largo, "<tema> · <fecha> · ..."."""
    if evento in TIPOS_CORTOS:
        cuando = f"del {fecha}" if fecha != FECHA_DESCONOCIDA else f"({FECHA_DESCONOCIDA})"
        cabeza = f"{evento} {cuando}"
    else:
        cabeza = f"{evento} · {fecha}"
    return f"{cabeza} · fragmento {fragmento}"


def ficha(fila) -> Ficha:
    """Ficha de un pasaje desde una fila (Series o dict) con las columnas de `pasajes.parquet`."""
    evento, lugar = evento_y_lugar(_valor(fila, "titulo", ""))
    fecha = fecha_larga(_valor(fila, "fecha"))
    fragmento = int(_valor(fila, "posicion", 0)) + 1
    es_rep = bool(_valor(fila, "es_reportero", False))
    url = _valor(fila, "url")
    return Ficha(titulo=titulo_pasaje(evento, fecha, fragmento), evento=evento, fecha=fecha,
                 lugar=lugar, fragmento=fragmento,
                 habla=quien_habla(_valor(fila, "interlocutor"), es_rep), es_reportero=es_rep,
                 url=str(url) if url else None)


def etiqueta_pasaje(fila) -> str:
    """Atajo: solo el título legible del pasaje."""
    return ficha(fila).titulo
