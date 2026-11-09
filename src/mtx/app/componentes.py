"""Lógica de la app de anotación sin Streamlit: persistencia, juicios, resaltado y estados.

La comparten `vista_*.py` (Streamlit) y `cli.py` (alternativa con `input()`, PRD §7).

Persistencia (D19, T15): CSV bajo `anotaciones/` reescrito tras cada acción con escritura atómica
(temporal en el mismo directorio, `fsync`, respaldo `.bak` del anterior y `os.replace`). Cada
sesión guarda el sha256 del archivo que cargó; si al guardar el disco ya no coincide, se rechaza
la escritura (`ConflictoEdicion`): otra pestaña o proceso lo editó. Un metadato
`<archivo>.meta.json` lleva el número de revisión y los hashes de los insumos congelados al
primer juicio; un historial `juicios_historial.csv` registra cada cambio.

Juicios: `relevante` ∈ {"1", "0", ""}; vacío = "omitido por ahora", distinto de 0. La app nunca
precarga ni sugiere valores y no muestra puntajes, rangos ni variantes (ciega al modelo).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from mtx import config, pool
from mtx.preproceso import RE_TOKEN, tokenizar

COLUMNAS_HISTORIAL = ["momento", "revision", "query_id", "passage_id", "anterior", "nuevo"]
ETIQUETAS = {"1": "Relevante", "0": "No relevante", "": "Omitido por ahora", None: "Sin juzgar"}


# --------------------------------------------------------------------------- rutas


@dataclass(frozen=True)
class Rutas:
    anotaciones: Path
    criterios: Path
    pool: Path
    pasajes: Path
    consultas: Path

    @property
    def juicios(self) -> Path:
        return self.anotaciones / "juicios_relevancia.csv"

    @property
    def historial(self) -> Path:
        return self.anotaciones / "juicios_historial.csv"

    @property
    def cierre_gold(self) -> Path:
        return self.anotaciones / "cierre_gold.json"

    @property
    def revision_siglas(self) -> Path:
        return self.anotaciones / "revision_siglas.csv"

    @property
    def gazetteer_extendido(self) -> Path:
        """`MTX_GAZETTEER_EXTENDIDO` permite que las pruebas no toquen `config/`."""
        return Path(os.environ.get("MTX_GAZETTEER_EXTENDIDO",
                                   config.DIR_CONFIG / "gazetteer_extendido.csv"))

    @property
    def siglas_candidatas(self) -> Path:
        return Path(os.environ.get("MTX_SIGLAS_CANDIDATAS",
                                   config.DIR_SALIDA / "06_siglas_candidatas.csv"))

    @property
    def criterios_anotacion(self) -> Path:
        return config.DIR_CONFIG / "criterios_anotacion.md"


def rutas() -> Rutas:
    """Rutas efectivas. `MTX_ANOTACIONES` y `MTX_CRITERIOS_RELEVANCIA` permiten que las pruebas
    usen carpetas temporales sin tocar `anotaciones/` ni `config/`."""
    return Rutas(
        anotaciones=Path(os.environ.get("MTX_ANOTACIONES", config.DIR_ANOTACIONES)),
        criterios=Path(os.environ.get("MTX_CRITERIOS_RELEVANCIA",
                                      config.DIR_CONFIG / "criterios_relevancia.md")),
        pool=config.DIR_SALIDA / "04_pool.csv",
        pasajes=config.PASAJES_PARQUET,
        consultas=config.CONSULTAS_CSV,
    )


# --------------------------------------------------------------------------- escritura atómica


class ConflictoEdicion(RuntimeError):
    """El archivo cambió en disco desde que esta sesión lo cargó."""


def sha256_ruta(ruta: Path) -> str:
    """sha256 del archivo, o cadena vacía si no existe (token de concurrencia)."""
    ruta = Path(ruta)
    return hashlib.sha256(ruta.read_bytes()).hexdigest() if ruta.exists() else ""


def escribir_atomico(ruta: Path, contenido: bytes, respaldo: bool = True) -> None:
    """Temporal en el mismo directorio + `fsync` + respaldo `.bak` + `os.replace`. Si algo falla
    antes del reemplazo, el archivo original queda intacto."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f"{ruta.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(contenido)
            f.flush()
            os.fsync(f.fileno())
        if respaldo and ruta.exists():
            shutil.copy2(ruta, ruta.with_name(ruta.name + ".bak"))
        os.replace(tmp, ruta)
    finally:
        if tmp.exists():
            tmp.unlink()


def _csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, lineterminator="\n").encode("utf-8")


def leer_meta(ruta_csv: Path) -> dict:
    m = Path(str(ruta_csv) + ".meta.json")
    return json.loads(m.read_text(encoding="utf-8")) if m.exists() else {}


# --------------------------------------------------------------------------- juicios


def cargar_items(r: Rutas | None = None) -> pd.DataFrame:
    """Pares del pool en orden de presentación, con lo que el anotador puede ver. Las columnas
    de procedencia del pool (`variantes`, `mejor_rango_*`) no se cargan: modo ciego."""
    r = r or rutas()
    p = pd.read_csv(r.pool, dtype=str, keep_default_na=False,
                    usecols=["query_id", "passage_id", "doc_id", "fecha", "texto",
                             "texto_sha256"])
    meta = pd.read_parquet(r.pasajes, columns=["passage_id", "titulo", "interlocutor",
                                               "inicio_cuerpo"]).set_index("passage_id")
    p["titulo"] = p["passage_id"].map(meta["titulo"]).fillna("")
    p["interlocutor"] = p["passage_id"].map(meta["interlocutor"]).fillna("")
    p["inicio_cuerpo"] = p["passage_id"].map(meta["inicio_cuerpo"]).fillna(0).astype(int)
    p["orden"] = range(len(p))
    return p


def cargar_juicios(r: Rutas | None = None) -> tuple[pd.DataFrame, str]:
    """Juicios del disco (todo como texto) y el token de concurrencia de esta carga."""
    r = r or rutas()
    if not r.juicios.exists():
        return pd.DataFrame(columns=pool.COLUMNAS_JUICIOS, dtype=str), ""
    df = pd.read_csv(r.juicios, dtype=str, keep_default_na=False)
    return df[pool.COLUMNAS_JUICIOS], sha256_ruta(r.juicios)


def valor_actual(juicios: pd.DataFrame, query_id: str, passage_id: str) -> str | None:
    """'1', '0', '' (omitido) o None (sin fila: nunca visto)."""
    f = juicios[(juicios["query_id"] == query_id) & (juicios["passage_id"] == passage_id)]
    return None if f.empty else f["relevante"].iloc[0]


def guardar_juicio(items: pd.DataFrame, juicios: pd.DataFrame, token: str, query_id: str,
                   passage_id: str, valor: str, r: Rutas | None = None,
                   insumos: dict | None = None) -> tuple[pd.DataFrame, str]:
    """Registra `valor` ('1', '0' o '' para omitir) y reescribe el CSV atómicamente.

    Devuelve los juicios nuevos y el token nuevo. `ConflictoEdicion` si el disco cambió desde la
    carga; `ValueError` si el par no está en el pool o el valor no es válido. `insumos` (hashes
    de pool y criterios) se fija en el metadato con el primer juicio y no se reescribe después.
    """
    r = r or rutas()
    if valor not in ("1", "0", ""):
        raise ValueError(f"Valor de juicio inválido: {valor!r}")
    fila_item = items[(items["query_id"] == query_id) & (items["passage_id"] == passage_id)]
    if fila_item.empty:
        raise ValueError(f"{query_id} {passage_id} no está en el pool")
    if sha256_ruta(r.juicios) != token:
        raise ConflictoEdicion("Editado desde otra pestaña o proceso: recarga antes de guardar.")

    anterior = valor_actual(juicios, query_id, passage_id)
    if anterior == valor:
        return juicios, token
    otras = juicios[~((juicios["query_id"] == query_id) & (juicios["passage_id"] == passage_id))]
    nueva = pd.DataFrame([{"query_id": query_id, "doc_id": fila_item["doc_id"].iloc[0],
                           "passage_id": passage_id, "relevante": valor}])
    todos = pd.concat([otras, nueva], ignore_index=True)
    orden = dict(zip(zip(items["query_id"], items["passage_id"]), items["orden"]))
    todos = (todos.assign(_o=[orden.get(k, len(orden)) for k in
                              zip(todos["query_id"], todos["passage_id"])])
             .sort_values("_o", kind="stable").drop(columns="_o"))[pool.COLUMNAS_JUICIOS]

    meta = leer_meta(r.juicios)
    revision = int(meta.get("revision", 0)) + 1
    escribir_atomico(r.juicios, _csv_bytes(todos))
    nuevo_token = sha256_ruta(r.juicios)

    hist = (pd.read_csv(r.historial, dtype=str, keep_default_na=False) if r.historial.exists()
            else pd.DataFrame(columns=COLUMNAS_HISTORIAL))
    hist = pd.concat([hist, pd.DataFrame([{
        "momento": datetime.now().isoformat(timespec="seconds"), "revision": str(revision),
        "query_id": query_id, "passage_id": passage_id,
        "anterior": "sin_fila" if anterior is None else anterior, "nuevo": valor}])])
    escribir_atomico(r.historial, _csv_bytes(hist[COLUMNAS_HISTORIAL]), respaldo=False)

    meta |= {"revision": revision, "sha256": nuevo_token,
             "actualizado": datetime.now().isoformat(timespec="seconds")}
    for clave, h in (insumos or {}).items():
        meta.setdefault(clave, h)  # congelado con el primer juicio
    escribir_atomico(Path(str(r.juicios) + ".meta.json"),
                     (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
                     respaldo=False)
    return todos.reset_index(drop=True), nuevo_token


def insumos_actuales(r: Rutas | None = None) -> dict:
    """Hashes que se congelan con el primer juicio: pool (contenido) y criterio de relevancia."""
    r = r or rutas()
    return {"sha256_pool": pool.hash_pool(pool.leer_pool(r.pool)) if r.pool.exists() else "",
            "sha256_criterios": sha256_ruta(r.criterios)}


def cambios_en_insumos(r: Rutas | None = None) -> list[str]:
    """Insumos congelados al primer juicio que cambiaron después (vacía si no hay juicios)."""
    r = r or rutas()
    meta = leer_meta(r.juicios)
    if not meta:
        return []
    actual = insumos_actuales(r)
    nombres = {"sha256_pool": "el pool (salida/04_pool.csv)",
               "sha256_criterios": "el criterio (config/criterios_relevancia.md)"}
    return [f"Cambió {nombres[k]} después del primer juicio"
            for k in nombres if k in meta and meta[k] != actual[k]]


def progreso(items: pd.DataFrame, juicios: pd.DataFrame) -> pd.DataFrame:
    """Por consulta: total, juzgados (0/1), omitidos y pendientes; en el orden de los ítems."""
    hechos = juicios.set_index(["query_id", "passage_id"])["relevante"].to_dict()
    filas = []
    for q, g in items.groupby("query_id", sort=False):
        v = [hechos.get((q, pid)) for pid in g["passage_id"]]
        juzg = sum(x in ("0", "1") for x in v)
        filas.append({"query_id": q, "total": len(g), "juzgados": juzg,
                      "omitidos": sum(x == "" for x in v), "pendientes": len(g) - juzg})
    return pd.DataFrame(filas)


def siguiente_pendiente(items_q: pd.DataFrame, juicios: pd.DataFrame, desde: int,
                        incluir_actual: bool = False) -> int | None:
    """Índice (en `items_q`) del siguiente par sin 0/1 a partir de `desde`, dando la vuelta.
    None si todos están juzgados."""
    hechos = juicios.set_index(["query_id", "passage_id"])["relevante"].to_dict()
    n = len(items_q)
    ids = list(zip(items_q["query_id"], items_q["passage_id"]))
    inicio = 0 if incluir_actual else 1
    for paso in range(inicio, n + inicio):
        i = (desde + paso) % n
        if hechos.get(ids[i]) not in ("0", "1"):
            return i
    return None


# --------------------------------------------------------------------------- revisión de siglas

COLUMNAS_REVISION = ["sigla", "nombre_propuesto", "frecuencia", "ejemplo", "decision",
                     "nombre_final"]
DECISIONES = ("", "ORG", "LOC", "descartar")
"""Vacío = pendiente. La app no preselecciona ninguna decisión."""


def reglas_congeladas() -> bool:
    """¿Existe la etiqueta git `reglas-congeladas` (D15)? Si existe, la revisión no se edita."""
    import subprocess
    r = subprocess.run(["git", "tag", "-l", "reglas-congeladas"], cwd=config.RAIZ,
                       capture_output=True, text=True, check=False)
    return bool(r.stdout.strip())


def cargar_revision_siglas(r: Rutas | None = None) -> tuple[pd.DataFrame, str]:
    """Candidatas de `salida/06_siglas_candidatas.csv` unidas a las decisiones ya guardadas en
    `anotaciones/revision_siglas.csv`. Una decisión guardada nunca se pierde: si la sigla ya no
    está entre las candidatas, se conserva al final."""
    r = r or rutas()
    cand = (pd.read_csv(r.siglas_candidatas, dtype=str, keep_default_na=False)
            if r.siglas_candidatas.exists() else pd.DataFrame(columns=COLUMNAS_REVISION[:4]))
    previas = (pd.read_csv(r.revision_siglas, dtype=str, keep_default_na=False)
               if r.revision_siglas.exists() else pd.DataFrame(columns=COLUMNAS_REVISION))
    df = cand.merge(previas[["sigla", "decision", "nombre_final"]], on="sigla", how="left")
    huerfanas = previas[~previas["sigla"].isin(cand["sigla"]) & (previas["decision"] != "")]
    df = pd.concat([df, huerfanas], ignore_index=True)[COLUMNAS_REVISION].fillna("")
    return df, sha256_ruta(r.revision_siglas)


def validar_revision_siglas(df: pd.DataFrame) -> list[str]:
    errores = []
    malas = sorted(set(df["decision"]) - set(DECISIONES))
    if malas:
        errores.append(f"Decisiones no válidas: {malas}")
    if df["sigla"].duplicated().any():
        errores.append("Siglas repetidas")
    return errores


def guardar_revision_siglas(df: pd.DataFrame, token: str, r: Rutas | None = None) -> str:
    """Guarda las decisiones y reconstruye el gazetteer extendido. Rechaza la escritura si las
    reglas están congeladas, si el archivo cambió desde otra pestaña o si hay valores inválidos."""
    from mtx import reglas
    r = r or rutas()
    if reglas_congeladas():
        raise ValueError("Las reglas están congeladas (`reglas-congeladas`): la revisión ya no "
                         "se edita. Ver la skill integridad-congelacion.")
    if sha256_ruta(r.revision_siglas) != token:
        raise ConflictoEdicion("editado desde otra pestaña: recarga antes de guardar.")
    errores = validar_revision_siglas(df)
    if errores:
        raise ValueError("; ".join(errores))
    escribir_atomico(r.revision_siglas, _csv_bytes(df[COLUMNAS_REVISION]))
    ext = reglas.construir_extendido(revision=r.revision_siglas)
    escribir_atomico(r.gazetteer_extendido, _csv_bytes(ext))
    return sha256_ruta(r.revision_siglas)


def resumen_revision(df: pd.DataFrame) -> dict:
    d = df["decision"]
    return {"candidatas": len(df), "pendientes": int((d == "").sum()),
            "ORG": int((d == "ORG").sum()), "LOC": int((d == "LOC").sum()),
            "descartadas": int((d == "descartar").sum())}


# --------------------------------------------------------------------------- resaltado


def spans_terminos(texto: str, inicio_cuerpo: int, consulta: str) -> list[tuple[int, int, str]]:
    """Palabras del cuerpo cuya raíz coincide con una raíz de la consulta (mismo preprocesamiento
    que el índice). Offsets de carácter Python sobre `texto`, que no se modifica."""
    raices = set(tokenizar(consulta))
    spans = []
    for m in RE_TOKEN.finditer(texto, inicio_cuerpo):
        toks = tokenizar(m.group(0))
        if len(toks) == 1 and toks[0] in raices:
            spans.append((m.start(), m.end(), "termino"))
    return spans


def html_desde_spans(texto: str, spans: list[tuple[int, int, str]]) -> str:
    """HTML seguro desde offsets: cada tramo pasa por `html.escape` y los spans van en
    `<mark class="...">`. Spans fuera de rango, solapados o anidados lanzan `ValueError` (se
    muestran como error, nunca se ocultan)."""
    partes, fin_ant = [], 0
    for ini, fin, clase in sorted(spans):
        if not 0 <= ini < fin <= len(texto):
            raise ValueError(f"Span fuera de rango: ({ini}, {fin}) en texto de {len(texto)}")
        if ini < fin_ant:
            raise ValueError(f"Spans solapados o anidados en ({ini}, {fin})")
        partes.append(html.escape(texto[fin_ant:ini]))
        partes.append(f'<mark class="{html.escape(clase)}">{html.escape(texto[ini:fin])}</mark>')
        fin_ant = fin
    partes.append(html.escape(texto[fin_ant:]))
    return "".join(partes)


def html_pasaje(texto: str, inicio_cuerpo: int, consulta: str) -> str:
    """Pasaje completo: marca de interlocutor en gris y términos de la consulta resaltados."""
    spans = spans_terminos(texto, inicio_cuerpo, consulta)
    if inicio_cuerpo > 0:
        spans.append((0, inicio_cuerpo, "marca"))
    return html_desde_spans(texto, spans)


# --------------------------------------------------------------------------- modo ciego


def gold_cerrado(r: Rutas | None = None) -> bool:
    """Única comprobación del modo ciego: hasta que exista `anotaciones/cierre_gold.json`,
    ninguna vista muestra predicciones de la muestra gold."""
    return (r or rutas()).cierre_gold.exists()


# --------------------------------------------------------------------------- estados


PENDIENTE_HUMANO, PENDIENTE_TECNICO = "pendiente humano", "pendiente técnico"
VALIDO, OBSOLETO, ERROR = "válido", "obsoleto", "error"


def _json(ruta: Path) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8")) if Path(ruta).exists() else {}


def estados_artefactos(r: Rutas | None = None, hash_pasajes_actual: str | None = None,
                       pasajes: pd.DataFrame | None = None) -> list[dict]:
    """Estado de cada artefacto (PRD §7): un archivo existente no basta para ser "válido"; hace
    falta su validador en verde y hashes vigentes. `hash_pasajes_actual` y `pasajes` se pasan
    desde fuera para cachearlos (calcularlos tarda unos segundos)."""
    from mtx import consultas as _consultas
    from mtx import ranking as _ranking
    r = r or rutas()
    S = config.DIR_SALIDA
    out = []

    def fila(nombre, estado, detalle, siguiente=""):
        out.append({"artefacto": nombre, "estado": estado, "detalle": detalle,
                    "siguiente": siguiente})

    lim = _json(S / "01_limpieza.json")
    if not r.pasajes.exists():
        fila("Pasajes (data/pasajes.parquet)", PENDIENTE_TECNICO, "No existe", "make corpus")
    elif hash_pasajes_actual and lim.get("hash_pasajes") != hash_pasajes_actual:
        fila("Pasajes (data/pasajes.parquet)", OBSOLETO,
             "No coincide con salida/01_limpieza.json", "make corpus")
    else:
        fila("Pasajes (data/pasajes.parquet)", VALIDO, f"{lim.get('pasajes', '?'):,} pasajes")

    im = _json(config.INDICE_META)
    if not config.INDICE_META.exists() or not config.INDICE_PKL.exists():
        fila("Índice y TF-IDF (data/)", PENDIENTE_TECNICO, "No existe", "make indice")
    elif hash_pasajes_actual and im.get("sha256_pasajes") != hash_pasajes_actual:
        fila("Índice y TF-IDF (data/)", OBSOLETO, "Construido con otros pasajes", "make indice")
    else:
        fila("Índice y TF-IDF (data/)", VALIDO,
             f"N = {im.get('N', 0):,}, vocabulario {im.get('vocabulario', 0):,}")

    rk = S / "ranking.csv"
    res3 = _json(S / "03_resumen.json")
    if not rk.exists():
        fila("Rankings (ranking.csv)", PENDIENTE_TECNICO, "No existe", "make ranking")
    else:
        prob = _ranking.validar_ranking(pd.read_csv(rk, dtype=str, keep_default_na=False),
                                        _consultas.cargar())
        raiz_igual = sha256_ruta(config.RAIZ / "ranking.csv") == sha256_ruta(rk)
        if prob:
            fila("Rankings (ranking.csv)", ERROR, "; ".join(prob), "make ranking")
        elif res3.get("sha256_indice_meta") not in (None, sha256_ruta(config.INDICE_META)):
            fila("Rankings (ranking.csv)", OBSOLETO, "El índice cambió después", "make ranking")
        elif not raiz_igual:
            fila("Rankings (ranking.csv)", OBSOLETO, "La copia de la raíz no coincide",
                 "make ranking")
        else:
            fila("Rankings (ranking.csv)", VALIDO, "400 filas validadas; copia en la raíz")

    pm = _json(S / "04_pool_meta.json")
    if not r.pool.exists():
        fila("Pool (salida/04_pool.csv)", PENDIENTE_TECNICO, "No existe", "make pool")
    elif pm.get("sha256_ranking_csv") != sha256_ruta(rk):
        fila("Pool (salida/04_pool.csv)", OBSOLETO, "El ranking cambió después del pool",
             "make pool")
    else:
        fila("Pool (salida/04_pool.csv)", VALIDO, f"{pm.get('pares', '?')} pares")

    cambios = cambios_en_insumos(r)
    if not r.criterios.exists():
        fila("Criterio de relevancia (config/criterios_relevancia.md)", PENDIENTE_HUMANO,
             "Lo escribe el alumno antes del primer juicio (D07)", "Escribir el archivo")
    elif any("criterio" in c for c in cambios):
        fila("Criterio de relevancia (config/criterios_relevancia.md)", ERROR,
             "Cambió después del primer juicio", "Ver skill integridad-congelacion")
    else:
        fila("Criterio de relevancia (config/criterios_relevancia.md)", VALIDO,
             "Escrito" + (" y congelado con el primer juicio" if leer_meta(r.juicios) else ""))

    if not r.pool.exists():
        fila("Juicios (anotaciones/juicios_relevancia.csv)", PENDIENTE_TECNICO,
             "Falta el pool", "make pool")
    else:
        v = pool.validar_juicios(r.juicios, pool.leer_pool(r.pool), pasajes)
        solo_cobertura = all(e.startswith(("Cobertura incompleta", "No existe"))
                             for e in v.errores)
        textos_cambiados = [e for e in v.errores if "cambiaron de texto" in e]
        if any("pool" in c for c in cambios) or textos_cambiados:
            fila("Juicios (anotaciones/juicios_relevancia.csv)", OBSOLETO,
                 "; ".join([c for c in cambios if "pool" in c] + textos_cambiados)
                 + ". Los juicios se conservan", "Ver skill integridad-congelacion")
        elif v.ok:
            fila("Juicios (anotaciones/juicios_relevancia.csv)", VALIDO,
                 f"{v.juzgados} de {v.esperados}" + (f"; {'; '.join(v.avisos)}"
                                                     if v.avisos else ""))
        elif solo_cobertura:
            fila("Juicios (anotaciones/juicios_relevancia.csv)", PENDIENTE_HUMANO,
                 f"{v.juzgados} de {v.esperados} juzgados", "Pestaña Juicios")
        else:
            fila("Juicios (anotaciones/juicios_relevancia.csv)", ERROR, "; ".join(v.errores),
                 "Revisar el archivo")

    raiz_j = config.RAIZ / "juicios_relevancia.csv"
    if not raiz_j.exists():
        fila("Juicios exportados (juicios_relevancia.csv)", PENDIENTE_TECNICO,
             "Se exportan cuando los juicios están completos y válidos", "make validar")
    elif sha256_ruta(raiz_j) != sha256_ruta(r.juicios):
        fila("Juicios exportados (juicios_relevancia.csv)", OBSOLETO,
             "No coincide con anotaciones/", "make validar")
    else:
        fila("Juicios exportados (juicios_relevancia.csv)", VALIDO, "Copia idéntica")

    if not r.criterios_anotacion.exists():
        fila("Criterio de anotación (config/criterios_anotacion.md)", PENDIENTE_HUMANO,
             "Lo escribe el alumno antes del gold", "Escribir el archivo")
    else:
        fila("Criterio de anotación (config/criterios_anotacion.md)", VALIDO,
             "Escrito" + (" y congelado" if reglas_congeladas() else "; se congela con "
                          "`make congelar`"))

    if not r.siglas_candidatas.exists():
        fila("Revisión de siglas (anotaciones/revision_siglas.csv)", PENDIENTE_TECNICO,
             "Faltan las candidatas", "make reglas")
    else:
        from mtx import reglas as _reglas
        rev, _ = cargar_revision_siglas(r)
        res = resumen_revision(rev)
        errores = validar_revision_siglas(rev)
        hecho = res["candidatas"] - res["pendientes"]
        if errores:
            fila("Revisión de siglas (anotaciones/revision_siglas.csv)", ERROR,
                 "; ".join(errores), "Pestaña Gazetteer")
        elif res["pendientes"]:
            fila("Revisión de siglas (anotaciones/revision_siglas.csv)", PENDIENTE_HUMANO,
                 f"{hecho} de {res['candidatas']} revisadas", "Pestaña Gazetteer")
        else:
            fila("Revisión de siglas (anotaciones/revision_siglas.csv)", VALIDO,
                 f"{res['ORG']} ORG, {res['LOC']} LOC, {res['descartadas']} descartadas")
        ext_ok = (r.gazetteer_extendido.exists() and _csv_bytes(
            _reglas.construir_extendido(revision=r.revision_siglas))
            == r.gazetteer_extendido.read_bytes())
        fila("Gazetteer extendido (config/gazetteer_extendido.csv)",
             VALIDO if ext_ok else OBSOLETO,
             "Coincide con kit + manual + revisión" if ext_ok
             else "No refleja la revisión actual", "" if ext_ok else "make reglas")

    for nombre, ruta, sig in [
        ("Resultados IR (resultados_ir.csv)", config.RAIZ / "resultados_ir.csv",
         "H4: make evaluar-ir"),
        ("Muestra gold (anotaciones/muestra_gold.csv)", r.anotaciones / "muestra_gold.csv",
         "H5: make muestra-gold"),
        ("Gold (anotaciones/gold_entidades.csv)", r.anotaciones / "gold_entidades.csv",
         "H6: pestaña Gold"),
        ("Cierre del gold (anotaciones/cierre_gold.json)", r.cierre_gold, "H6: pestaña Gold"),
        ("Caché NER (data/cache_ner/)", config.DIR_DATA / "cache_ner", "H5: make ner"),
    ]:
        if not ruta.exists():
            fila(nombre, PENDIENTE_TECNICO, "Aún no existe", sig)
        else:
            fila(nombre, PENDIENTE_TECNICO, "Existe, pero su validador aún no está en la app",
                 sig)
    return out
