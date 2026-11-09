"""Normalización prudente (PRD §6.10): representaciones auxiliares que nunca modifican el span.

FECHA: `fecha_iso` en `AAAA-MM-DD`, `AAAA-MM` o `AAAA` según la precisión; intervalos con inicio
y fin; días imposibles se detectan y quedan como `no_resoluble`. Las relativas (`próximo`,
`pasado`, sin año) solo se resuelven con una fecha ancla válida (la del discurso).
MONTO: `Decimal` para el cálculo; moneda MXN, USD o vacía; escala; ambiguos sin valor.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from mtx.reglas import MESES

SIGLO_DOS_DIGITOS = 30
"""Año de dos dígitos: 00-30 → 2000-2030 (el corpus va de 2018 a 2024); 31-99 es ambiguo y queda
sin `fecha_iso`."""

_DIA = {"primero": 1}
_RE_INTERVALO = re.compile(r"(?P<d1>\w+)\s+al\s+(?P<d2>\w+)\s+de\s+(?P<mes>\w+)"
                           r"(?:\s+(?:de|del)\s+(?:año\s+)?(?P<anio>\d{4}))?$", re.IGNORECASE)
_RE_DIA_MES = re.compile(r"(?:(?P<mod>\w+)\s+)?(?P<dia>\w+)\s+de\s+(?P<mes>[a-z]+)"
                         r"(?:\s+(?:de|del)\s+(?:año\s+)?(?P<anio>\d{4}))?$", re.IGNORECASE)
_RE_MES_ANIO = re.compile(r"(?:(?P<mod>\w+)\s+)?(?P<mes>[a-z]+)\s+(?:de|del)\s+(?:año\s+)?"
                          r"(?P<anio>\d{4})$", re.IGNORECASE)
_RE_NUMERICA = re.compile(r"(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<anio>\d{4}|\d{2})$")
_RE_ANIO = re.compile(r"(?P<anio>\d{4})$")
_RE_MES_REL = re.compile(r"(?:\w+\s+)?(?P<mes>[a-z]+)\s+(?:(?:de|del)\s+(?P<rel>este|presente|"
                         r"próximo|proximo|pasado|siguiente)\s+año|del?\s+(?P<dd>\d{2}))$",
                         re.IGNORECASE)
_MODS = {"próximo": "proximo", "próxima": "proximo", "proximo": "proximo", "proxima": "proximo",
         "pasado": "pasado", "pasada": "pasado", "este": "este", "esta": "este"}


def _vacio_fecha(**kw) -> dict:
    base = {"fecha_iso": "", "fecha_inicio": "", "fecha_fin": "", "precision_fecha": "",
                "fecha_relativo": "", "fecha_ancla": "", "resuelta_desde_ancla": False, "estado_fecha": ""}
    base.update(kw)
    return base


def _dia(s: str) -> int | None:
    s = s.lower()
    if s in _DIA:
        return _DIA[s]
    return int(s) if s.isdigit() else None


def _fecha(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _resolver_relativa(mes: int, dia: int, mod: str, ancla: date | None) -> tuple[date | None, str]:
    """Siguiente o anterior ocurrencia estricta del día y mes respecto al ancla; sin modificador
    (o "este"), el año del ancla."""
    if ancla is None:
        return None, "parcial_sin_ancla"
    candidatos = [_fecha(ancla.year + k, mes, dia) for k in (-1, 0, 1)]
    candidatos = [c for c in candidatos if c is not None]
    if not candidatos:
        return None, "no_resoluble"
    if mod == "proximo":
        posteriores = [c for c in candidatos if c > ancla]
        return (min(posteriores), "resuelta") if posteriores else (None, "no_resoluble")
    if mod == "pasado":
        anteriores = [c for c in candidatos if c < ancla]
        return (max(anteriores), "resuelta") if anteriores else (None, "no_resoluble")
    f = _fecha(ancla.year, mes, dia)
    return (f, "resuelta") if f else (None, "no_resoluble")


def normalizar_fecha(texto: str, ancla: date | None = None) -> dict:
    t = " ".join(texto.split())
    ancla_iso = ancla.isoformat() if ancla else ""

    m = _RE_INTERVALO.match(t)
    if m and m.group("mes").lower() in MESES:
        mes, d1, d2 = MESES[m.group("mes").lower()], _dia(m.group("d1")), _dia(m.group("d2"))
        if m.group("anio"):
            anio = int(m.group("anio"))
            f1, f2 = _fecha(anio, mes, d1 or 0), _fecha(anio, mes, d2 or 0)
            if f1 is None or f2 is None or f1 > f2:
                return _vacio_fecha(precision_fecha="intervalo", estado_fecha="no_resoluble")
            return _vacio_fecha(fecha_inicio=f1.isoformat(), fecha_fin=f2.isoformat(),
                                precision_fecha="intervalo", estado_fecha="ok")
        return _vacio_fecha(precision_fecha="intervalo", estado_fecha="parcial_sin_anio",
                            fecha_ancla=ancla_iso)

    m = _RE_NUMERICA.match(t)
    if m:
        anio = int(m.group("anio"))
        if len(m.group("anio")) == 2:
            if anio > SIGLO_DOS_DIGITOS:
                return _vacio_fecha(precision_fecha="dia", estado_fecha="ambiguo_siglo")
            anio += 2000
        f = _fecha(anio, int(m.group("mes")), int(m.group("dia")))
        if f is None:
            return _vacio_fecha(precision_fecha="dia", estado_fecha="no_resoluble")
        return _vacio_fecha(fecha_iso=f.isoformat(), precision_fecha="dia", estado_fecha="ok")

    m = _RE_DIA_MES.match(t)
    if m and m.group("mes").lower() in MESES and _dia(m.group("dia")) is not None:
        mes, dia = MESES[m.group("mes").lower()], _dia(m.group("dia"))
        mod = _MODS.get((m.group("mod") or "").lower(), "")
        if m.group("anio"):
            f = _fecha(int(m.group("anio")), mes, dia)
            if f is None:
                return _vacio_fecha(precision_fecha="dia", fecha_relativo=mod,
                                    estado_fecha="no_resoluble")
            return _vacio_fecha(fecha_iso=f.isoformat(), precision_fecha="dia",
                                fecha_relativo=mod, estado_fecha="ok")
        if _fecha(2024, mes, dia) is None:  # 2024 es bisiesto: solo rechaza días imposibles
            return _vacio_fecha(precision_fecha="dia", fecha_relativo=mod,
                                estado_fecha="no_resoluble")
        f, estado = _resolver_relativa(mes, dia, mod, ancla)
        return _vacio_fecha(fecha_iso=f.isoformat() if f else "", precision_fecha="dia",
                            fecha_relativo=mod or "sin_anio", fecha_ancla=ancla_iso,
                            resuelta_desde_ancla=f is not None, estado_fecha=estado)

    m = _RE_MES_ANIO.match(t)
    if m and m.group("mes").lower() in MESES:
        return _vacio_fecha(fecha_iso=f"{int(m.group('anio')):04d}-"
                                      f"{MESES[m.group('mes').lower()]:02d}",
                            precision_fecha="mes", estado_fecha="ok")

    m = _RE_MES_REL.match(t)
    if m and m.group("mes").lower() in MESES:
        mes = MESES[m.group("mes").lower()]
        if m.group("dd"):
            yy = int(m.group("dd"))
            if yy > SIGLO_DOS_DIGITOS:
                return _vacio_fecha(precision_fecha="mes", estado_fecha="ambiguo_siglo")
            return _vacio_fecha(fecha_iso=f"{2000 + yy:04d}-{mes:02d}", precision_fecha="mes",
                                estado_fecha="ok")
        if ancla is None:
            return _vacio_fecha(precision_fecha="mes", fecha_relativo="este_anio",
                                estado_fecha="parcial_sin_ancla")
        delta = {"próximo": 1, "proximo": 1, "siguiente": 1, "pasado": -1}.get(
            m.group("rel").lower(), 0)
        return _vacio_fecha(fecha_iso=f"{ancla.year + delta:04d}-{mes:02d}",
                            precision_fecha="mes", fecha_relativo="anio_relativo",
                            fecha_ancla=ancla_iso, resuelta_desde_ancla=True, estado_fecha="ok")

    if t.lower() in MESES:  # mes solo: año del discurso si hay ancla
        mes = MESES[t.lower()]
        if ancla is None:
            return _vacio_fecha(precision_fecha="mes", fecha_relativo="sin_anio",
                                estado_fecha="parcial_sin_ancla")
        return _vacio_fecha(fecha_iso=f"{ancla.year:04d}-{mes:02d}", precision_fecha="mes",
                            fecha_relativo="sin_anio", fecha_ancla=ancla_iso,
                            resuelta_desde_ancla=True, estado_fecha="ok")

    m = _RE_ANIO.match(t)
    if m:
        return _vacio_fecha(fecha_iso=m.group("anio"), precision_fecha="anio", estado_fecha="ok")
    return _vacio_fecha(estado_fecha="no_reconocida")


# =========================================================================== MONTO

def normalizar_monto(texto: str) -> dict:
    """`valor_num` en unidades (Decimal como texto estable), `moneda` ∈ {MXN, USD, ""}, `escala`
    y `estado_monto`. `$` sin palabra de moneda no fija la moneda."""
    from mtx.reglas import valor_cifra

    t = " ".join(texto.lower().split())
    moneda = "USD" if re.search(r"d[oó]lares", t) else ("MXN" if "pesos" in t else "")
    valor = valor_cifra(t)
    if valor is None:
        return {"valor_num": "", "moneda": moneda, "escala": "", "estado_monto": "ambiguo"}
    try:
        d = Decimal(f"{valor:.2f}").normalize()
    except InvalidOperation:
        return {"valor_num": "", "moneda": moneda, "escala": "", "estado_monto": "ambiguo"}
    # Escala por magnitud del valor, no por la palabra: "1,200 millones" y "2 mil 500 millones"
    # son ambos del orden de mil millones.
    escala = next(n for lim, n in ((Decimal(10) ** 12, "billones"),
                                   (Decimal(10) ** 9, "mil_millones"),
                                   (Decimal(10) ** 6, "millones"), (Decimal(10) ** 3, "mil"),
                                   (Decimal(0), "uno")) if d >= lim)
    return {"valor_num": format(d, "f"), "moneda": moneda, "escala": escala,
                "estado_monto": "ok" if moneda else "sin_moneda"}
