"""Tablas de respuesta con evidencia (PRD §6.13, D17, U14, T14).

Por consulta, sobre su top-10 con filtro del mejor modelo:

1. Exclusiones (U14): entidades dentro de la marca de interlocutor y PER de
   `config/excluir_tablas.yaml`. Son filtros de presentación; las entradas no se tocan.
2. Cada campo de `config/tablas_respuesta.yaml` toma sus candidatos (entidades o cantidades
   auxiliares) y busca la relación en el contexto: ±60 caracteres alrededor del span y la oración
   que lo contiene. Si todos los patrones del campo aparecen, el
   valor es `respaldado_en_texto` con una cita exacta; si no, `ambiguo`. Lo que dice un reportero
   nunca pasa de `ambiguo`.
3. Agrupación por `canonico` (verificado en el gazetteer) o forma normalizada. Las evidencias de un
   mismo valor en una misma intervención (ventanas solapadas) son un solo evento.
4. `contradictorio` solo en campos con `unico_por_evento: true`, cuando una misma intervención da
   dos valores distintos con evidencia. Nunca se resuelve por mayoría.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from mtx.fusion import sin_acentos

COLUMNAS_RESPUESTAS = ["query_id", "campo_respuesta", "valor", "unidad", "relacion", "estado",
                       "passage_id", "doc_id", "fecha_documento", "evidencia_inicio",
                       "evidencia_fin", "cita", "entidades_referencia", "regla_relacion",
                       "grupo_evento", "interlocutor"]
ESTADOS = ("respaldado_en_texto", "ambiguo", "contradictorio", "no_encontrado")
RANGO_ESTADO = {"respaldado_en_texto": 0, "contradictorio": 1, "ambiguo": 2}
COLUMNAS_EVIDENCIAS = [*COLUMNAS_RESPUESTAS, "clave", "rango", "frecuencia", "n_pasajes",
                       "n_discursos", "n_eventos"]
VENTANA = 60
MAX_VALORES = 8
RE_ORACION = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class Campo:
    query_id: str
    campo: str
    fuente: str
    tipo: str
    patrones: tuple[str, ...]
    relacion: str
    unidades: tuple[str, ...] = ()
    filtro: str = ""
    unidad: str = ""
    unico_por_evento: bool = False


def cargar_mapa(ruta: Path) -> dict[str, list[Campo]]:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    mapa = {}
    for q, campos in datos.items():
        mapa[q] = [Campo(q, c["campo"], c["fuente"], c["tipo"], tuple(c["patrones_contexto"]),
                         c["relacion"], tuple(c.get("unidades", ())), c.get("filtro", ""),
                         c.get("unidad", ""), bool(c.get("unico_por_evento", False)))
                   for c in campos]
    return mapa


def cargar_exclusiones(ruta: Path) -> set[str]:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    return {sin_acentos(x).strip() for x in datos.get("per", [])}


# --------------------------------------------------------------------------- contexto

def normalizar_mismo_largo(s: str) -> str:
    """Minúsculas sin acentos carácter por carácter, conservando la longitud (para mapear las
    posiciones de los patrones al texto original)."""
    return "".join((sin_acentos(c) or c)[:1] for c in s)


def oraciones(texto: str, inicio_cuerpo: int) -> list[tuple[int, int]]:
    """Oraciones del cuerpo; la marca de interlocutor es su propio tramo."""
    tramos = [(0, inicio_cuerpo)] if inicio_cuerpo > 0 else []
    ini = inicio_cuerpo
    for m in RE_ORACION.finditer(texto, inicio_cuerpo):
        tramos.append((ini, m.start()))
        ini = m.end()
    if ini < len(texto):
        tramos.append((ini, len(texto)))
    return [t for t in tramos if t[1] > t[0]]


def _indice_oracion(tramos: list[tuple[int, int]], pos: int) -> int:
    for i, (a, b) in enumerate(tramos):
        if a <= pos < b:
            return i
    return len(tramos) - 1


def contexto(texto: str, tramos: list[tuple[int, int]], ini: int, fin: int,
             inicio_cuerpo: int) -> tuple[int, int, tuple[int, int]]:
    """(inicio, fin) del contexto: ±60 caracteres ∪ la oración que contiene el span, sin entrar en
    la marca de interlocutor. Devuelve también esa oración.

    "La oración contigua" del PRD §6.13.2 se lee como la oración del span: incluir además las
    vecinas haría que el presupuesto total herede el "mensual" del monto por beneficiario de la
    oración de al lado, que es justo lo que la regla debe separar (decisión del 2026-11-09)."""
    i = _indice_oracion(tramos, ini)
    oa, ob = tramos[i]
    a = max(inicio_cuerpo, min(ini - VENTANA, oa))
    b = min(len(texto), max(fin + VENTANA, ob))
    return max(0, a), b, tramos[i]


def evidencia(texto: str, tramos: list[tuple[int, int]], ini: int, fin: int,
              inicio_cuerpo: int, patrones: tuple[str, ...]) -> tuple[bool, int, int]:
    """¿Aparecen todos los patrones en el contexto? Devuelve (respaldado, cita_inicio, cita_fin):
    la cita va de la oración del span a la última coincidencia usada, siempre dentro del
    contexto, de modo que `texto[cita_inicio:cita_fin]` contiene la relación."""
    a, b, (oa, ob) = contexto(texto, tramos, ini, fin, inicio_cuerpo)
    norm = normalizar_mismo_largo(texto[a:b])
    lo, hi = min(oa, ini), max(ob, fin)
    lo, hi = max(lo, a), min(hi, b)
    for p in patrones:
        ms = list(re.finditer(p, norm))
        if not ms:
            return False, oa, ob  # sin relación: la cita es la oración del span
        m = min(ms, key=lambda m: abs((a + m.start()) - ini))  # la coincidencia más cercana
        lo, hi = min(lo, a + m.start()), max(hi, a + m.end())
    return True, lo, hi


def _limpiar_cita(texto: str, a: int, b: int) -> tuple[int, int]:
    while a < b and texto[a].isspace():
        a += 1
    while b > a and texto[b - 1].isspace():
        b -= 1
    return a, b


# --------------------------------------------------------------------------- candidatos

def excluir(ent_q: pd.DataFrame, lista: set[str]) -> tuple[pd.DataFrame, int, int]:
    """U14: quita entidades en la marca y PER de la lista. Devuelve (filtradas, n_marca, n_lista)."""
    en_marca = ent_q["en_marca"].astype(str).str.lower().isin(["true", "1"])
    n_marca = int(en_marca.sum())
    resto = ent_q[~en_marca]
    de_lista = (resto["tipo"] == "PER") & resto["texto_normalizado"].isin(lista)
    return resto[~de_lista], n_marca, int(de_lista.sum())


@dataclass
class Filtros:
    d14: set[str] = field(default_factory=set)
    entidades_federativas: set[str] = field(default_factory=set)
    organizacion_empresarial: set[str] = field(default_factory=set)

    def acepta(self, nombre_filtro: str, canonico: str, normalizado: str) -> bool:
        if not nombre_filtro:
            return True
        conj = getattr(self, nombre_filtro)
        return bool(canonico) and canonico in conj or normalizado in {sin_acentos(x) for x in conj}


def filtros_desde_gazetteers(extendido: pd.DataFrame, loc: pd.DataFrame,
                             kit: pd.DataFrame) -> Filtros:
    d14 = set(extendido.loc[extendido["evidencia"].str.contains("D14", na=False), "nombre"])
    estados = set(loc.loc[loc["tipo"] == "estado", "nombre"])
    emp = set(kit.loc[kit["tipo"] == "organización empresarial", "nombre"])
    return Filtros(d14, estados, emp)


def clave_valor(f: dict, fuente: str) -> str:
    if fuente == "auxiliar":
        return f"{f['valor_num']}|{f['unidad']}" if f["valor_num"] != "" else sin_acentos(f["texto"])
    if f["tipo"] == "FECHA" and f.get("fecha_iso"):
        return f["fecha_iso"]
    if f["tipo"] == "MONTO" and f.get("valor_num"):
        return f"{f['valor_num']}|{f.get('moneda', '')}"
    return f.get("canonico") or f.get("texto_normalizado") or sin_acentos(f["texto"])


def candidatos(campo: Campo, ent_q: pd.DataFrame, aux_q: pd.DataFrame,
               filtros: Filtros, ic: dict[str, int]) -> list[dict]:
    if campo.fuente == "auxiliar":
        sel = aux_q[(aux_q["tipo_aux"] == campo.tipo) & aux_q["unidad"].isin(campo.unidades)]
        filas = [f for f in sel.to_dict("records") if int(f["inicio"]) >= ic[f["passage_id"]]]
    else:
        sel = ent_q[ent_q["tipo"] == campo.tipo]
        filas = [f for f in sel.to_dict("records")
                 if filtros.acepta(campo.filtro, f.get("canonico", ""),
                                   f.get("texto_normalizado", ""))]
    return filas


# --------------------------------------------------------------------------- respuestas

def _unidad(campo: Campo, f: dict, respaldado: bool) -> str:
    """La unidad del campo (p. ej. "MXN bimestral") solo cuando la relación está respaldada; si
    no, la que trae el valor (moneda o unidad de la cantidad)."""
    if campo.fuente == "auxiliar":
        return (campo.unidad if respaldado and campo.unidad else "") or str(f["unidad"])
    moneda = f.get("moneda", "") if campo.tipo == "MONTO" else ""
    if campo.unidad and respaldado:
        return campo.unidad.replace("MXN", moneda) if moneda and moneda != "MXN" else campo.unidad
    return moneda


def _habla(es_reportero: bool, cita: str) -> str:
    if es_reportero:
        return "pregunta (reportero)"
    return "pregunta" if "¿" in cita else "declaración"


def responder_campo(campo: Campo, cands: list[dict], pas: pd.DataFrame,
                    ent_q: pd.DataFrame) -> list[dict]:
    """Una fila por evidencia (todas), ya con estado; la agregación viene después."""
    filas = []
    for f in cands:
        p = pas.loc[f["passage_id"]]
        texto, ic = p["texto"], int(p["inicio_cuerpo"])
        ini, fin = int(f["inicio"]), int(f["fin"])
        tramos = oraciones(texto, ic)
        ok, ca, cb = evidencia(texto, tramos, ini, fin, ic, campo.patrones)
        ca, cb = _limpiar_cita(texto, ca, cb)
        reportero = bool(p["es_reportero"])
        estado = "respaldado_en_texto" if ok and not reportero else "ambiguo"
        regla = (f"{campo.query_id}:{campo.campo}:" + " + ".join(campo.patrones) if ok
                 else f"{campo.query_id}:{campo.campo}:sin_patron")
        if reportero:
            regla += ":reportero"
        refs = ent_q[(ent_q["passage_id"] == f["passage_id"]) & (ent_q["inicio"] >= ca)
                     & (ent_q["fin"] <= cb) & ~((ent_q["inicio"] == ini) & (ent_q["fin"] == fin))
                     & ent_q["tipo"].isin(["ORG", "PER", "LOC"])]
        filas.append({
            "query_id": campo.query_id, "campo_respuesta": campo.campo, "valor": f["texto"],
            "unidad": _unidad(campo, f, estado == "respaldado_en_texto"),
            "relacion": f"{campo.relacion} · {_habla(reportero, texto[ca:cb])}",
            "estado": estado, "passage_id": f["passage_id"], "doc_id": int(p["doc_id"]),
            "fecha_documento": "" if pd.isna(p["fecha"]) else pd.Timestamp(p["fecha"]).date().isoformat(),
            "evidencia_inicio": ca, "evidencia_fin": cb, "cita": texto[ca:cb],
            "entidades_referencia": "|".join(dict.fromkeys(refs["texto"].tolist()[:5])),
            "regla_relacion": regla,
            "grupo_evento": f"{campo.query_id}-i{p['intervencion_id']}",
            "interlocutor": p["interlocutor"], "clave": clave_valor(f, campo.fuente),
            "rango": int(p["rango"])})
    return filas


def agregar(campo: Campo, evid: list[dict]) -> tuple[list[dict], list[dict]]:
    """(filas de respuestas.csv, evidencias con conteos). Una fila por valor con su mejor
    evidencia; `no_encontrado` si no hay ninguno."""
    if not evid:
        vacia = dict.fromkeys(COLUMNAS_RESPUESTAS, "")
        vacia.update(query_id=campo.query_id, campo_respuesta=campo.campo,
                     relacion=campo.relacion, estado="no_encontrado",
                     regla_relacion=f"{campo.query_id}:{campo.campo}:sin_candidatos")
        return [vacia], []
    df = pd.DataFrame(evid)
    if campo.unico_por_evento:
        resp = df[df["estado"] == "respaldado_en_texto"]
        choque = resp.groupby("grupo_evento")["clave"].nunique()
        eventos = set(choque[choque > 1].index)
        marca = df["grupo_evento"].isin(eventos) & (df["estado"] == "respaldado_en_texto")
        df.loc[marca, "estado"] = "contradictorio"
    conteo = df.groupby("clave").agg(frecuencia=("passage_id", "size"),
                                     n_pasajes=("passage_id", "nunique"),
                                     n_discursos=("doc_id", "nunique"),
                                     n_eventos=("grupo_evento", "nunique"))
    df = df.join(conteo, on="clave")
    df["_r"] = df["estado"].map(RANGO_ESTADO)
    df = df.sort_values(["_r", "rango", "passage_id", "evidencia_inicio"])
    mejores = df.drop_duplicates("clave").sort_values(
        ["_r", "n_discursos", "frecuencia", "valor"], ascending=[True, False, False, True])
    evid_out = df.drop(columns="_r")[COLUMNAS_EVIDENCIAS]
    return mejores.drop(columns="_r").to_dict("records"), evid_out.to_dict("records")


def validar_respuestas(res: pd.DataFrame, textos: dict[str, str]) -> list[str]:
    err = []
    if list(res.columns) != COLUMNAS_RESPUESTAS:
        return [f"Columnas {list(res.columns)} ≠ contrato de 16"]
    malos = sorted(set(res["estado"]) - set(ESTADOS))
    if malos:
        err.append(f"Estados fuera de dominio: {malos}")
    for f in res.to_dict("records"):
        if f["estado"] == "no_encontrado":
            if any(str(f[c]) not in ("", "nan") for c in ("valor", "passage_id", "cita",
                                                          "evidencia_inicio", "evidencia_fin")):
                err.append(f"{f['query_id']}·{f['campo_respuesta']}: no_encontrado con evidencia")
            continue
        t = textos[str(f["passage_id"])]
        a, b = int(f["evidencia_inicio"]), int(f["evidencia_fin"])
        if t[a:b] != f["cita"]:
            err.append(f"{f['query_id']}·{f['campo_respuesta']}·{f['valor']}: cita sin offsets")
    return err


# --------------------------------------------------------------------------- Markdown

def hash_tabla(res_q: pd.DataFrame) -> str:
    """Huella del contenido sustancial de una consulta: campos, valores, estados y pasajes."""
    cols = ["campo_respuesta", "valor", "estado", "passage_id"]
    datos = res_q[cols].astype(str).to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(datos.encode()).hexdigest()


def _celda(s: object, largo: int | None = None) -> str:
    s = " ".join(str(s).split()).replace("|", "\\|")
    return s if largo is None or len(s) <= largo else s[:largo - 1].rstrip() + "…"


def _cita_breve(f: dict, largo: int = 170) -> str:
    cita = str(f["cita"])
    if len(cita) <= largo:
        return cita
    pos = cita.find(str(f["valor"]))
    pos = max(0, pos - largo // 3) if pos >= 0 else 0
    pre = "…" if pos else ""
    return pre + cita[pos:pos + largo].rstrip() + "…"


ETIQUETA_ESTADO = {"respaldado_en_texto": "respaldado", "ambiguo": "ambiguo",
                   "contradictorio": "contradictorio", "no_encontrado": "sin evidencia"}


def markdown_consulta(q: str, consulta: dict, res_q: pd.DataFrame, evid_q: pd.DataFrame,
                      contexto_linea: str, valoracion: str) -> str:
    lineas = [f"# {q} · {consulta['consulta']}", "",
              f"**Pregunta:** {consulta['pregunta_extraccion']}", "", contexto_linea, ""]
    for campo, g in res_q.groupby("campo_respuesta", sort=False):
        lineas += [f"## {campo}", ""]
        if (g["estado"] == "no_encontrado").all():
            lineas += ["Sin evidencia en el top-10.", ""]
            continue
        cont = evid_q[evid_q["campo_respuesta"] == campo].drop_duplicates("clave").set_index(
            "clave")
        lineas += ["| Valor | Unidad | Estado | Pasaje | Fecha | Discursos | Cita breve |",
                   "| --- | --- | --- | --- | --- | --- | --- |"]
        for f in g.head(MAX_VALORES).to_dict("records"):
            nd = int(cont.at[f["clave"], "n_discursos"]) if f["clave"] in cont.index else 1
            lineas.append(
                f"| {_celda(f['valor'], 60)} | {_celda(f['unidad'])} | "
                f"{ETIQUETA_ESTADO[f['estado']]} | {f['passage_id']} | {f['fecha_documento']} | "
                f"{nd} | {_celda(_cita_breve(f))} |")
        if len(g) > MAX_VALORES:
            lineas.append(f"\n{len(g) - MAX_VALORES} valores más en `salida/respuestas.csv`.")
        lineas.append("")
    lineas += ["## Valoración del alumno", "", valoracion, ""]
    return "\n".join(lineas)


def bloque_valoracion(entrada: dict | None, hash_actual: str) -> str:
    if not entrada or not str(entrada.get("texto", "")).strip():
        return "valoracion: [VALIDAR] pendiente del alumno"
    if entrada.get("tabla_sha256") != hash_actual:
        return ("valoracion: [VALIDAR] invalidada: la tabla cambió desde que se escribió.\n\n"
                f"> {str(entrada['texto']).strip()}")
    texto = "\n".join(f"> {x}" for x in str(entrada["texto"]).strip().splitlines())
    return f"valoracion:\n\n{texto}"


def validar_valoraciones(ruta: Path, hashes: dict[str, str]) -> list[str]:
    """`[VALIDAR]` previo al reporte: 10 entradas no vacías, escritas sobre la tabla vigente."""
    if not Path(ruta).exists():
        return [f"Falta {Path(ruta).name}: el alumno escribe las valoraciones en la app"]
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    err = []
    for q, h in hashes.items():
        e = datos.get(q)
        if not e or not str(e.get("texto", "")).strip():
            err.append(f"{q}: valoración pendiente")
        elif e.get("tabla_sha256") != h:
            err.append(f"{q}: valoración invalidada (la tabla cambió); reescribirla")
    return err


# --------------------------------------------------------------------------- valoraciones

def leer_valoraciones(ruta: Path) -> dict:
    ruta = Path(ruta)
    return (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}) if ruta.exists() else {}


def guardar_valoracion(ruta: Path, token: str, q: str, texto: str, tabla_sha256: str) -> str:
    """Escribe la valoración del alumno para `q` con la huella de la tabla que leyó. Solo la usa
    la app (el alumno escribe el texto). Rechaza texto vacío y ediciones desde otra pestaña.
    Devuelve el nuevo token."""
    from datetime import datetime

    from mtx.app import componentes as C

    texto = texto.strip()
    if not texto:
        raise ValueError("La valoración está vacía.")
    if C.sha256_ruta(ruta) != token:
        raise C.ConflictoEdicion("valoraciones.yaml cambió desde otra pestaña: recarga.")
    datos = leer_valoraciones(ruta)
    datos[q] = {"texto": texto, "tabla_sha256": tabla_sha256,
                "fecha": datetime.now().isoformat(timespec="seconds")}
    orden = dict(sorted(datos.items(), key=lambda kv: int(str(kv[0])[1:])))
    contenido = ("# Valoraciones del alumno (PRD §6.13.5). Las escribe el alumno en la app;\n"
                 "# `tabla_sha256` es la huella de la tabla valorada.\n"
                 + yaml.safe_dump(orden, allow_unicode=True, sort_keys=False, width=100))
    C.escribir_atomico(Path(ruta), contenido.encode("utf-8"))
    return C.sha256_ruta(ruta)
