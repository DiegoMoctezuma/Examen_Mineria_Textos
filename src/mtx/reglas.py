"""Extracción por reglas (PRD §6.7, D11, D13, D14, D15): regex FECHA y MONTO, cantidades
auxiliares, gazetteers ORG/LOC, regla de marca de interlocutor y resolución de colisiones.

Todo trabaja sobre el `texto` canónico completo (mayúsculas y acentos intactos), nunca sobre los
tokens de IR. Offsets: índices de carácter Python, `inicio` inclusivo y `fin` exclusivo, con
`texto[inicio:fin] == entidad.texto`.
"""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from mtx import config

KIT_GAZETTEER = config.RAIZ / "kit" / "gazetteer_dependencias.csv"
GAZ_MANUAL = config.DIR_CONFIG / "gazetteer_manual.csv"
GAZ_EXTENDIDO = config.DIR_CONFIG / "gazetteer_extendido.csv"
GAZ_LOC = config.DIR_CONFIG / "gazetteer_loc.csv"
REVISION_SIGLAS = config.DIR_ANOTACIONES / "revision_siglas.csv"

COLUMNAS_GAZ = ["nombre", "variantes", "siglas", "tipo", "etiqueta", "origen", "evidencia"]
COLUMNAS_AUX = ["query_id", "passage_id", "texto", "inicio", "fin", "tipo_aux", "valor_num",
                "unidad", "estado_normalizacion", "regla_id"]
COLUMNAS_SIGLAS = ["sigla", "nombre_propuesto", "frecuencia", "ejemplo"]
COLUMNAS_COLISIONES = ["passage_id", "fuente_ganadora", "tipo_ganador", "inicio_ganador",
                       "fin_ganador", "texto_ganador", "fuente_suprimida", "tipo_suprimido",
                       "inicio_suprimido", "fin_suprimido", "texto_suprimido", "motivo"]

JERARQUIA = ("regex_fecha", "regex_monto", "gazetteer_loc", "gazetteer_org", "marca")
"""Desempate ante solapes de igual longitud (PRD §6.7.8): gana la fuente que aparece antes."""

LETRA = "a-záéíóúñüA-ZÁÉÍÓÚÑÜ"
IZQ = r"(?<![\wáéíóúñüÁÉÍÓÚÑÜ])"
DER = r"(?![\wáéíóúñüÁÉÍÓÚÑÜ])"


@dataclass(frozen=True)
class Entidad:
    tipo: str          # PER | ORG | LOC | FECHA | MONTO
    texto: str
    inicio: int
    fin: int
    metodo: str = "regla"
    fuente: str = ""   # regex_fecha | regex_monto | gazetteer_org | gazetteer_loc | marca
    en_marca: bool = False


@dataclass(frozen=True)
class Auxiliar:
    """Cantidad auxiliar (D11): no es entidad del examen y nunca va a `entidades.csv`."""
    texto: str
    inicio: int
    fin: int
    tipo_aux: str      # PORCENTAJE | CANTIDAD
    valor_num: float | None
    unidad: str
    estado_normalizacion: str
    regla_id: str


@dataclass
class Colision:
    ganadora: Entidad
    suprimida: Entidad
    motivo: str        # span_mas_largo | jerarquia


@dataclass
class ResultadoReglas:
    entidades: list[Entidad] = field(default_factory=list)
    auxiliares: list[Auxiliar] = field(default_factory=list)
    colisiones: list[Colision] = field(default_factory=list)


# =========================================================================== FECHA

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
         "diciembre": 12}
_MES = "(?:" + "|".join(sorted(MESES, key=len, reverse=True)) + ")"
_DIA = r"(?:primero|[12]\d|3[01]|0?[1-9])"
_ANIO = r"(?:19\d\d|20[0-4]\d)"
_DE_ANIO = rf"\s+(?:de|del)\s+(?:año\s+)?{_ANIO}"
_MOD = r"(?:próximo|próxima|proximo|proxima|pasado|pasada|este|esta)"
# Palabras que pueden seguir a un año sin que este deje de serlo ("en 2019 y 2020", "de 2019 a
# 2024"); cualquier otra palabra en minúscula (p. ej. "2000 personas") anula el año aislado.
_TRAS_ANIO = (r"(?:a|al|y|e|o|u|hasta|que|cuando|se|no|ya|fue|fueron|era|es|para|con|en|el|la|"
              r"los|las|del|de|por|como|pero|porque|ni|lo|le|les|nos|me|mientras|donde|tenía|"
              r"había|hubo|teníamos|vamos|tenemos|estamos|hemos|iban|eran|más|menos|tras)")
# Contextos fuertes: el año solo se rechaza si le sigue un sustantivo en plural ("en 2000 casas");
# "en 2021 esté en funcionamiento" sí es FECHA.
_CTX_ANIO_FUERTE = (r"(?:en(?:\s+el)?|el\s+año|del\s+año|año|desde(?:\s+el)?|hasta(?:\s+el)?|"
                    r"para(?:\s+el)?|durante(?:\s+el)?|a\s+partir\s+del?)")
# Contextos ambiguos (también introducen cantidades: "más de 2000 personas"): se rechaza ante
# cualquier palabra en minúscula que no esté en `_TRAS_ANIO`.
_CTX_ANIO_DEBIL = r"(?:de|a|al|y|entre)"
_FIN_ANIO = r"(?![\d,.]\d)(?!\s*%)"
# Mes sin día (relativa resoluble con la fecha del discurso): solo tras un contexto temporal.
_CTX_MES = (r"(?:en|para|desde|hasta|durante|a\s+partir\s+de|antes\s+de|después\s+de|"
            r"mes\s+de|a\s+(?:fines|finales|principios|mediados)\s+de)")
_SUF_REL = r"\s+(?:de|del)\s+(?:este|presente|próximo|proximo|pasado|siguiente)\s+año"
_SUF_2D = r"\s+del?\s+\d{2}(?!\d)"

RE_FECHA = re.compile(
    "|".join([
        # intervalo explícito: "1 al 15 de enero de 2021" (el "del" introductorio queda fuera)
        rf"{IZQ}(?P<intervalo>{_DIA}\s+al\s+{_DIA}\s+de\s+{_MES}(?:{_DE_ANIO})?){DER}",
        # día, mes y año opcional, con modificador relativo opcional (D13)
        rf"{IZQ}(?P<dia_mes>(?:{_MOD}\s+)?{_DIA}\s+de\s+{_MES}(?:{_DE_ANIO})?){DER}",
        # mes y año: "diciembre de 2021", "diciembre del 2019"
        rf"{IZQ}(?P<mes_anio>(?:{_MOD}\s+)?{_MES}{_DE_ANIO}){DER}",
        # mes con año relativo o de dos dígitos: "diciembre de este año", "enero del 24"
        rf"{IZQ}(?P<mes_rel>(?:{_MOD}\s+)?{_MES}(?:{_SUF_REL}|{_SUF_2D})){DER}",
        # numérica: 15/12/2023, 1/1/19
        r"(?<![\d/])(?P<numerica>\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))(?![\d/])",
        # mes solo tras contexto temporal: "para enero", "en julio" (contexto fuera del span)
        (rf"{IZQ}{_CTX_MES}\s+(?P<mes_solo>{_MES}){DER}"
         rf"(?!{_DE_ANIO})(?!{_SUF_REL})(?!{_SUF_2D})"),
        # año aislado con contexto temporal (D13); el contexto queda fuera del span
        (rf"{IZQ}{_CTX_ANIO_FUERTE}\s+(?P<anio>{_ANIO}){_FIN_ANIO}"
         rf"(?!\s+(?!{_TRAS_ANIO}{DER})[a-záéíóúñü]+s{DER})"),
        (rf"{IZQ}{_CTX_ANIO_DEBIL}\s+(?P<anio_debil>{_ANIO}){_FIN_ANIO}"
         rf"(?!\s+(?!{_TRAS_ANIO}{DER})[a-záéíóúñü])"),
    ]),
    re.IGNORECASE,
)


def buscar_fechas(texto: str) -> list[Entidad]:
    out = []
    for m in RE_FECHA.finditer(texto):
        grupo = m.lastgroup
        ini, fin = m.span(grupo)
        out.append(Entidad("FECHA", texto[ini:fin], ini, fin, fuente="regex_fecha"))
    return out


# =========================================================================== MONTO y auxiliares

NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
PALABRA_NUM = r"un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|cien"
CIFRA = (rf"(?:(?:{NUM}|(?:{PALABRA_NUM})(?=\s))(?:\s+mil(?!\w)(?:\s+(?:{NUM}))?)?"
         rf"|mil(?!\w)(?:\s+(?:{NUM}))?)")
ESCALA = r"(?:\s+(?:millones|millón|billones|billón)(?!\w))?"
MONEDA = r"\s+(?:de\s+)?(?:pesos|dólares|dolares)(?!\w)"
LIMITE_IZQ = r"(?<![\w$.,])"
RE_MONTO = re.compile(
    rf"{LIMITE_IZQ}(?:\$\s?{CIFRA}{ESCALA}(?:{MONEDA})?|{CIFRA}{ESCALA}{MONEDA})", re.IGNORECASE)
RE_PORCENTAJE = re.compile(rf"{LIMITE_IZQ}(?:{NUM})\s*(?:por\s+ciento(?!\w)|%)", re.IGNORECASE)
UNIDADES_CANTIDAD = ("dosis", "vacunas", "litros", "barriles", "elementos", "sucursales",
                     "hectáreas", "beneficiarios", "sembradores", "kilómetros", "árboles")
"""PRD §6.7.3 más `vacunas`, `barriles` y `árboles` (Q2, Q6 y Q5), añadidas antes del gold."""
RE_CANTIDAD = re.compile(
    rf"{LIMITE_IZQ}{CIFRA}{ESCALA}\s+(?:de\s+)?(?P<unidad>{'|'.join(UNIDADES_CANTIDAD)})(?!\w)",
    re.IGNORECASE)

_PALABRAS = {"un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
             "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "cien": 100}
_ESCALAS = {"millón": 10**6, "millones": 10**6, "billón": 10**12, "billones": 10**12}


def valor_cifra(texto: str) -> float | None:
    """Valor de una cifra hablada: "2 mil 500 millones" → 2.5e9; "1.5 billones" → 1.5e12;
    "mil 200" → 1200. `None` si la cifra no se puede interpretar sin ambigüedad (p. ej. punto
    como separador de miles, "1.200")."""
    t = texto.lower().replace("$", " ").strip()
    t = re.sub(r"\s+(?:de\s+)?(?:pesos|dólares|dolares)$", "", t)
    escala = 1
    m = re.search(r"\s+(millones|millón|billones|billón)$", t)
    if m:
        escala = _ESCALAS[m.group(1)]
        t = t[:m.start()].strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", t):
        return None  # "1.200": punto de miles o decimal, ambiguo (no cubierto, PRD §6.7.2)

    def num(s: str) -> float:
        return float(_PALABRAS[s]) if s in _PALABRAS else float(s.replace(",", ""))

    partes = t.split()
    try:
        if "mil" in partes:
            i = partes.index("mil")
            antes = num(partes[0]) if i == 1 else 1.0
            despues = num(partes[i + 1]) if len(partes) > i + 1 else 0.0
            base = antes * 1000 + despues
        else:
            base = num(partes[0])
    except (ValueError, KeyError, IndexError):
        return None
    return base * escala


def buscar_montos(texto: str) -> list[Entidad]:
    return [Entidad("MONTO", m.group(0), m.start(), m.end(), fuente="regex_monto")
            for m in RE_MONTO.finditer(texto)]


def buscar_auxiliares(texto: str) -> list[Auxiliar]:
    out = []
    for m in RE_PORCENTAJE.finditer(texto):
        num = re.match(NUM, m.group(0)).group(0)
        out.append(Auxiliar(m.group(0), m.start(), m.end(), "PORCENTAJE",
                            float(num.replace(",", "")), "porcentaje", "ok", "porcentaje"))
    for m in RE_CANTIDAD.finditer(texto):
        unidad = m.group("unidad").lower()
        cifra = m.group(0)[: m.start("unidad") - m.start()]
        cifra = re.sub(r"\s+de\s*$", "", cifra.strip())
        valor = valor_cifra(cifra)
        out.append(Auxiliar(m.group(0), m.start(), m.end(), "CANTIDAD", valor, unidad,
                            "ok" if valor is not None else "ambiguo", f"cantidad_{unidad}"))
    return sorted(out, key=lambda a: (a.inicio, a.fin))


# =========================================================================== gazetteers

SIGLAS_PALABRA_COMUN = frozenset({"Bienestar", "Salud", "Cultura"})
"""Siglas del kit que son sustantivos comunes ("pensión del Bienestar", "la Salud"): no se buscan
solas; el nombre completo sí. Decisión registrada en docs/decisiones.md."""
CONTEXTO_REQUERIDO = {"Patria": r"(?:(?<=vacuna )|(?<=vacunas )|(?<=Vacuna ))"}
"""Formas que solo cuentan tras un contexto fijo (D14: "Patria" es vacuna, "la Patria" no)."""


def _formas(fila: dict) -> list[str]:
    formas = [fila["nombre"]]
    formas += [v for v in str(fila.get("variantes", "") or "").split("|") if v.strip()]
    formas += [s for s in str(fila.get("siglas", "") or "").split("|") if s.strip()]
    return list(dict.fromkeys(f.strip() for f in formas if f.strip()))


def leer_gazetteer(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def etiqueta_kit(tipo: str) -> str:
    """PRD §6.7.4: `tipo == "obra"` → LOC; cualquier otro → ORG."""
    return "LOC" if tipo.strip().lower() == "obra" else "ORG"


def construir_extendido(kit: Path = KIT_GAZETTEER, manual: Path = GAZ_MANUAL,
                        revision: Path = REVISION_SIGLAS) -> pd.DataFrame:
    """`config/gazetteer_extendido.csv`: base del kit + entradas manuales (PRD y D14) + siglas
    minadas que el alumno aceptó en la pestaña Gazetteer. Las rechazadas no entran."""
    base = leer_gazetteer(kit)
    filas = {}
    for r in base.to_dict("records"):
        filas[r["nombre"]] = {"nombre": r["nombre"], "variantes": "", "siglas": r["siglas"],
                                  "tipo": r["tipo"], "etiqueta": etiqueta_kit(r["tipo"]),
                                  "origen": "kit", "evidencia": "kit/gazetteer_dependencias.csv"}
    if Path(manual).exists():
        for r in leer_gazetteer(manual).to_dict("records"):
            if r["nombre"] in filas:  # variante o sigla adicional de una fila del kit
                f = filas[r["nombre"]]
                for col in ("variantes", "siglas"):
                    extra = [x for x in r[col].split("|") if x]
                    actual = [x for x in f[col].split("|") if x]
                    f[col] = "|".join(dict.fromkeys(actual + extra))
                f["evidencia"] += f"; {r['evidencia']}"
            else:
                filas[r["nombre"]] = {"nombre": r["nombre"], "variantes": r["variantes"],
                                          "siglas": r["siglas"], "tipo": r["tipo"],
                                          "etiqueta": r["etiqueta"], "origen": "manual",
                                          "evidencia": r["evidencia"]}
    if Path(revision).exists():
        rev = pd.read_csv(revision, dtype=str, keep_default_na=False)
        for r in rev[rev["decision"].isin(["ORG", "LOC"])].to_dict("records"):
            nombre = r["nombre_final"].strip() or r["sigla"]
            filas[nombre] = {"nombre": nombre, "variantes": "", "siglas": r["sigla"],
                                 "tipo": "minado", "etiqueta": r["decision"], "origen": "minado",
                                 "evidencia": f"revisión del alumno; ejemplo: {r['ejemplo'][:120]}"}
    return pd.DataFrame(list(filas.values()), columns=COLUMNAS_GAZ)


@dataclass(frozen=True)
class Patron:
    forma: str
    etiqueta: str      # ORG | LOC
    nombre: str        # nombre canónico de la fila
    es_sigla: bool


class Gazetteer:
    """Motor de coincidencia (PRD §6.7.7).

    - Formas escapadas con `re.escape`, ordenadas por longitud descendente.
    - Límites de palabra que respetan acentos.
    - Formas de una sola palabra (siglas de ≤5 caracteres según el PRD y, por extensión, todo
      nombre de una palabra como "Guerrero", "Sonora" o "Morena"): sensibles a mayúsculas; se
      acepta la forma exacta y la forma toda en mayúsculas (marcas de interlocutor). Formas de
      varias palabras: insensibles a mayúsculas.
    - Dentro del gazetteer gana la coincidencia más larga.
    """

    def __init__(self, filas: pd.DataFrame):
        patrones: dict[tuple[str, bool], Patron] = {}
        for r in filas.to_dict("records"):
            siglas = {s.strip() for s in str(r.get("siglas", "") or "").split("|") if s.strip()}
            for forma in _formas(r):
                if forma in SIGLAS_PALABRA_COMUN:
                    continue
                sensible = len(forma.split()) == 1
                clave = (forma if sensible else forma.lower(), sensible)
                if clave not in patrones:  # la primera fila gana (LOC se carga antes que ORG)
                    patrones[clave] = Patron(forma, r["etiqueta"], r["nombre"], forma in siglas)
        self.patrones = patrones
        self._insens = {k: p for (k, sens), p in patrones.items() if not sens}
        self._sens = {}
        for (k, sens), p in patrones.items():
            if sens:
                self._sens.setdefault(k, p)
                self._sens.setdefault(k.upper(), p)
        sens = sorted({p.forma for (_, s), p in patrones.items() if s}, key=len, reverse=True)
        insens = sorted({p.forma for (_, s), p in patrones.items() if not s}, key=len, reverse=True)
        alts = []
        for f in sens:
            pre = CONTEXTO_REQUERIDO.get(f, "")
            variantes = {f, f.upper()}
            alts.append(pre + "(?:" + "|".join(re.escape(v) for v in sorted(variantes)) + ")")
        self._re_sens = re.compile(IZQ + "(?:" + "|".join(alts) + ")" + DER) if alts else None
        self._re_insens = (re.compile(IZQ + "(?:" + "|".join(re.escape(f) for f in insens) + ")"
                                      + DER, re.IGNORECASE) if insens else None)

    def _patron(self, texto: str, sensible: bool) -> Patron | None:
        return self._sens.get(texto) if sensible else self._insens.get(texto.lower())

    def buscar(self, texto: str) -> list[tuple[int, int, Patron]]:
        """Coincidencias sin solapes dentro del gazetteer: la más larga gana y, a igual
        longitud, la que empieza antes."""
        cand = []
        for rx, sensible in ((self._re_sens, True), (self._re_insens, False)):
            if rx is None:
                continue
            for m in rx.finditer(texto):
                p = self._patron(m.group(0), sensible)
                if p is not None:
                    cand.append((m.start(), m.end(), p))
        cand.sort(key=lambda c: (-(c[1] - c[0]), c[0]))
        tomados: list[tuple[int, int, Patron]] = []
        for c in cand:
            if all(c[1] <= t[0] or c[0] >= t[1] for t in tomados):
                tomados.append(c)
        return sorted(tomados, key=lambda c: c[0])


TIPOS_LOC_EXTENSIBLES = frozenset({"estado", "ciudad", "lugar"})
_RE_DE_LUGAR = re.compile(r"\s+(?:de|del)\s+(?:la\s+|el\s+)?")


def _extender_org_con_lugar(texto: str, coincidencias, tipos_loc: dict[str, str]):
    """PRD §3.6: una ORG de nombre completo seguida de "de <estado o ciudad>" es una sola ORG
    ("Secretaría de Salud de Tabasco"); el lugar interno no se emite como LOC."""
    out, saltar = [], set()
    for i, (ini, fin, p) in enumerate(coincidencias):
        if i in saltar:
            continue
        if p.etiqueta == "ORG" and not p.es_sigla and len(p.forma.split()) > 1:
            m = _RE_DE_LUGAR.match(texto, fin)
            if m and i + 1 < len(coincidencias):
                ini2, fin2, p2 = coincidencias[i + 1]
                if (ini2 == m.end() and p2.etiqueta == "LOC"
                        and tipos_loc.get(p2.nombre) in TIPOS_LOC_EXTENSIBLES):
                    out.append((ini, fin2, p, True))
                    saltar.add(i + 1)
                    continue
        out.append((ini, fin, p, False))
    return out


# =========================================================================== marca

CARGOS = frozenset(["PRESIDENTE", "PRESIDENTA", "SECRETARIO", "SECRETARIA", "SUBSECRETARIO", "SUBSECRETARIA", "DIRECTOR", "DIRECTORA", "SUBDIRECTOR", "SUBDIRECTORA", "GOBERNADOR", "GOBERNADORA", "JEFE", "JEFA", "TITULAR", "COMANDANTE", "COORDINADOR", "COORDINADORA", "PROCURADOR", "PROCURADORA", "FISCAL", "GENERAL", "ALMIRANTE", "EMBAJADOR", "EMBAJADORA", "CANCILLER", "VOCERO", "VOCERA", "ADMINISTRADOR", "ADMINISTRADORA", "COMISIONADO", "COMISIONADA", "DELEGADO", "DELEGADA", "ENCARGADO", "ENCARGADA", "RESPONSABLE", "MINISTRO", "MINISTRA", "SENADOR", "SENADORA", "DIPUTADO", "DIPUTADA", "ALCALDE", "ALCALDESA", "GERENTE", "CONSEJERO", "CONSEJERA", "ASESOR", "ASESORA", "OFICIAL", "MAYOR", "AGENTE", "INTEGRANTE", "MIEMBRO", "REPRESENTANTE", "TITULAR", "ABOGADO", "ABOGADA", "INVESTIGADOR", "INVESTIGADORA", "DOCTOR", "DOCTORA", "LICENCIADO", "LICENCIADA", "INGENIERO", "INGENIERA", "MAESTRO", "MAESTRA", "PROFESOR", "PROFESORA", "CIUDADANO", "CIUDADANA", "C."])
"""Cargos y tratamientos conocidos (PRD §6.7.6): se quitan, nunca se supone que lo que sigue es
persona sin comprobarlo."""
GENERICAS = frozenset(["PREGUNTA", "INTERLOCUTOR", "INTERLOCUTORA", "INTERLOCUTORES", "VOZ", "HOMBRE", "MUJER", "DE", "INTERVENCIÓN", "INTERVENCION", "MODERADOR", "MODERADORA", "PARTICIPANTE", "PARTICIPANTES", "ASISTENTE", "ASISTENTES", "PÚBLICO", "PUBLICO", "RESPUESTA", "AUDIO", "VIDEO", "VIDEOS", "PRESENTADOR", "PRESENTADORA", "LOCUTOR", "LOCUTORA", "NARRADOR", "NARRADORA", "TODOS", "CORO"])
PALABRAS_INSTITUCION = frozenset(["SECRETARÍA", "SECRETARIA", "DIRECCIÓN", "DIRECCION", "INSTITUTO", "COMISIÓN", "COMISION", "GOBIERNO", "CONSEJO", "CENTRO", "UNIDAD", "PROCURADURÍA", "FISCALÍA", "BANCO", "FONDO", "AGENCIA", "SERVICIO", "SISTEMA", "COORDINACIÓN", "COORDINACION", "OFICINA", "CÁMARA", "CAMARA", "PARTIDO", "NACIONAL", "FEDERAL", "MEXICANO", "MEXICANA", "EJÉRCITO", "EJERCITO", "GUARDIA", "ARMADA", "ASOCIACIÓN", "ASOCIACION", "ORGANIZACIÓN"])
PARTICULAS = frozenset({"DE", "DEL", "LA", "LAS", "LOS", "Y", "E", "SAN", "SANTA"})
_RE_PALABRA_NOMBRE = re.compile(r"[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ'\-.]*")


def _es_nombre(palabras: list[str]) -> bool:
    if not 2 <= len(palabras) <= 5:
        return False
    if palabras[0] in PARTICULAS or palabras[-1] in PARTICULAS:
        return False
    for p in palabras:
        if not _RE_PALABRA_NOMBRE.fullmatch(p):
            return False
        if p in CARGOS or p in GENERICAS or p in PALABRAS_INSTITUCION:
            return False
    return True


def _tramo(texto: str, ini: int, fin: int) -> tuple[int, int]:
    while ini < fin and texto[ini] in " \t":
        ini += 1
    while fin > ini and texto[fin - 1] in " \t":
        fin -= 1
    return ini, fin


def entidad_marca(texto: str, inicio_cuerpo: int) -> Entidad | None:
    """PER de la marca de interlocutor (PRD §6.7.6, §3.6).

    El corpus escribe "NOMBRE, CARGO" (al revés del ejemplo del PRD, "CARGO, NOMBRE"), así que se
    decide qué lado es el nombre por la lista de cargos: si el primer tramo empieza con un cargo,
    el nombre es lo que sigue a la última coma; si no, el nombre es el primer tramo. Sin coma, se
    quitan los cargos iniciales ("PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR"). Marcas genéricas o
    institucionales no producen PER (las ORG de la marca las encuentra el gazetteer).
    """
    if inicio_cuerpo <= 0:
        return None
    fin_marca = texto.rfind(":", 0, inicio_cuerpo)
    if fin_marca < 0:
        return None
    marca = texto[:fin_marca]
    comas = [m.start() for m in re.finditer(",", marca)]
    if comas:
        primero = marca[:comas[0]].split()
        if primero and primero[0] in CARGOS:
            ini, fin = comas[-1] + 1, fin_marca
        else:
            ini, fin = 0, comas[0]
    else:
        ini, fin = 0, fin_marca
        palabras = list(re.finditer(r"\S+", marca))
        k = 0
        while k < len(palabras) - 2 and palabras[k].group(0) in CARGOS:
            k += 1
        if k:
            ini = palabras[k].start()
    ini, fin = _tramo(texto, ini, fin)
    if ini >= fin or not _es_nombre(texto[ini:fin].split()):
        return None
    return Entidad("PER", texto[ini:fin], ini, fin, fuente="marca", en_marca=True)


# =========================================================================== colisiones y API


def resolver_colisiones(entidades: list[Entidad]) -> tuple[list[Entidad], list[Colision]]:
    """PRD §6.7.8: ante solape se conserva el span más largo; a igual longitud decide la
    jerarquía `regex_fecha > regex_monto > gazetteer_loc > gazetteer_org > marca`."""
    rango = {f: i for i, f in enumerate(JERARQUIA)}
    orden = sorted(entidades, key=lambda e: (-(e.fin - e.inicio), rango.get(e.fuente, 99),
                                             e.inicio))
    ganadoras: list[Entidad] = []
    colisiones: list[Colision] = []
    for e in orden:
        choque = next((g for g in ganadoras if e.inicio < g.fin and g.inicio < e.fin), None)
        if choque is None:
            ganadoras.append(e)
        else:
            motivo = ("span_mas_largo" if (choque.fin - choque.inicio) > (e.fin - e.inicio)
                      else "jerarquia")
            colisiones.append(Colision(choque, e, motivo))
    return sorted(ganadoras, key=lambda e: (e.inicio, e.fin, e.tipo)), colisiones


@lru_cache(maxsize=1)
def gazetteer_por_defecto() -> tuple[Gazetteer, dict[str, str]]:
    """LOC primero (gana ante una forma repetida) y luego el ORG extendido. Si
    `config/gazetteer_extendido.csv` no existe todavía, se construye en memoria."""
    loc = leer_gazetteer(GAZ_LOC)
    ext = leer_gazetteer(GAZ_EXTENDIDO) if GAZ_EXTENDIDO.exists() else construir_extendido()
    tipos_loc = dict(zip(loc["nombre"], loc["tipo"]))
    return Gazetteer(pd.concat([loc, ext], ignore_index=True)), tipos_loc


def extraer_reglas_detalle(texto: str, inicio_cuerpo: int,
                           gaz: tuple[Gazetteer, dict[str, str]] | None = None) -> ResultadoReglas:
    gazetteer, tipos_loc = gaz or gazetteer_por_defecto()
    cand: list[Entidad] = buscar_fechas(texto) + buscar_montos(texto)
    for ini, fin, p, _ext in _extender_org_con_lugar(texto, gazetteer.buscar(texto), tipos_loc):
        fuente = "gazetteer_loc" if p.etiqueta == "LOC" else "gazetteer_org"
        cand.append(Entidad(p.etiqueta, texto[ini:fin], ini, fin, fuente=fuente,
                            en_marca=ini < inicio_cuerpo))
    per = entidad_marca(texto, inicio_cuerpo)
    if per:
        cand.append(per)
    cand = [Entidad(e.tipo, e.texto, e.inicio, e.fin, e.metodo, e.fuente,
                    e.en_marca or e.inicio < inicio_cuerpo) for e in cand]
    entidades, colisiones = resolver_colisiones(cand)
    return ResultadoReglas(entidades, buscar_auxiliares(texto), colisiones)


def extraer_reglas(texto: str, inicio_cuerpo: int) -> list[Entidad]:
    """API del PRD §6.7.9."""
    return extraer_reglas_detalle(texto, inicio_cuerpo).entidades


def filas_colisiones(passage_id: str, colisiones: list[Colision]) -> list[dict]:
    return [{"passage_id": passage_id, "fuente_ganadora": c.ganadora.fuente,
                 "tipo_ganador": c.ganadora.tipo, "inicio_ganador": c.ganadora.inicio,
                 "fin_ganador": c.ganadora.fin, "texto_ganador": c.ganadora.texto,
                 "fuente_suprimida": c.suprimida.fuente, "tipo_suprimido": c.suprimida.tipo,
                 "inicio_suprimido": c.suprimida.inicio, "fin_suprimido": c.suprimida.fin,
                 "texto_suprimido": c.suprimida.texto, "motivo": c.motivo} for c in colisiones]


# =========================================================================== minado de siglas

_RE_SIGLA_PAREN = re.compile(
    r"((?:[A-ZÁÉÍÓÚÑ][\wáéíóúñü\-]*|de|del|la|las|los|y|e|para|en|el|a)"
    r"(?:\s+(?:[A-ZÁÉÍÓÚÑ][\wáéíóúñü\-]*|de|del|la|las|los|y|e|para|en|el|a)){1,7})"
    r"\s*\(([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ\-]{1,7})\)")
_RE_MAYUS = re.compile(r"(?<![\wáéíóúñüÁÉÍÓÚÑÜ\-])([A-ZÁÉÍÓÚÑ]{3,7})(?![\wáéíóúñüÁÉÍÓÚÑÜ\-])")
"""Tokens todo en mayúsculas; las piezas de palabras con guion ("T-MEC", "SARS-CoV-2") no
cuentan como sigla suelta."""
_PART_MIN = {"de", "del", "la", "las", "los", "y", "e", "para", "en", "el", "a"}
ROMANOS = re.compile(r"^[IVXLCDM]+$")


def minar_siglas(pasajes: pd.DataFrame, gazetteer: Gazetteer | None = None,
                 min_frecuencia: int = 20) -> pd.DataFrame:
    """Candidatas a sigla (PRD §6.7.4) desde el cuerpo de los pasajes (nunca la marca):

    1. patrón `Nombre Largo (SIGLAS)`: nombre de 2 a 8 palabras y siglas de 2 a 8 mayúsculas;
    2. frecuencia de tokens todo en mayúsculas de 3 a 7 letras que no estén en la stoplist.

    Se omiten las que el gazetteer ya reconoce. El alumno decide en la pestaña Gazetteer."""
    from mtx.preproceso import stoplist

    stop = {s.upper() for s in stoplist()}
    gaz = gazetteer or gazetteer_por_defecto()[0]
    frec: Counter = Counter()
    nombres: dict[str, Counter] = defaultdict(Counter)
    ejemplo: dict[str, str] = {}
    for texto, ic in zip(pasajes["texto"], pasajes["inicio_cuerpo"]):
        cuerpo = texto[int(ic):]
        for m in _RE_SIGLA_PAREN.finditer(cuerpo):
            palabras = m.group(1).split()
            while palabras and (palabras[0] in _PART_MIN or palabras[0].upper() in CARGOS
                                or palabras[0].upper() in PARTICULAS):
                palabras.pop(0)
            if 2 <= len(palabras) <= 8:
                nombres[m.group(2)][" ".join(palabras)] += 1
                ejemplo.setdefault(m.group(2), cuerpo[max(0, m.start() - 40): m.end() + 40])
        for m in _RE_MAYUS.finditer(cuerpo):
            s = m.group(1)
            if s in stop or ROMANOS.match(s):
                continue
            frec[s] += 1
            if s not in ejemplo:
                ejemplo[s] = cuerpo[max(0, m.start() - 60): m.end() + 60]
    filas = []
    for s in set(frec) | set(nombres):
        n = frec.get(s, 0) + sum(nombres[s].values())
        con_nombre = bool(nombres.get(s))
        if n < min_frecuencia and not (con_nombre and sum(nombres[s].values()) >= 3):
            continue
        if gaz.buscar(s):
            continue
        propuesto = nombres[s].most_common(1)[0][0] if con_nombre else ""
        filas.append({"sigla": s, "nombre_propuesto": propuesto, "frecuencia": n,
                          "ejemplo": " ".join(ejemplo.get(s, "").split())})
    df = pd.DataFrame(filas, columns=COLUMNAS_SIGLAS)
    return df.sort_values(["frecuencia", "sigla"], ascending=[False, True]).reset_index(drop=True)


def escribir_csv(df: pd.DataFrame, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
