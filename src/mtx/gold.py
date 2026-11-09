"""Gold de evaluación (PRD §6.11, §3.6, D10, D15, P04, T10): persistencia, búsqueda de spans,
validación en vivo, cierre por pasaje, `validar_gold()` y cierre del gold.

Solo la app escribe en `anotaciones/`. Nada aquí lee predicciones del sistema: el modo ciego se
garantiza porque este módulo no conoce `salida/entidades*.csv` ni `data/cache_ner/`.

Archivos:
- `anotaciones/gold_entidades.csv`: `passage_id,tipo,texto,inicio,fin` (UTF-8 sin BOM).
- `anotaciones/estado_gold.csv`: `passage_id,texto_sha256,estado,n_entidades,revision`.
- `anotaciones/cierre_gold.json`: hashes de muestra, textos, protocolo, criterio y gold, y fecha.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from mtx import config
from mtx.app import componentes as C

TIPOS = ("PER", "ORG", "LOC", "FECHA", "MONTO")
COLUMNAS_GOLD = ["passage_id", "tipo", "texto", "inicio", "fin"]
COLUMNAS_ESTADO = ["passage_id", "texto_sha256", "estado", "n_entidades", "revision"]
ABIERTO, CERRADO = "abierto", "cerrado"
PUNTUACION_FINAL = set('.,;:!?)"»”’')
PUNTUACION_INICIAL = set('("«“‘¿¡')
"""Se recortan en el modo por tokens; `$` nunca se recorta."""
CONTEXTO = 40


@dataclass(frozen=True)
class RutasGold:
    anotaciones: Path

    @property
    def muestra(self) -> Path:
        return self.anotaciones / "muestra_gold.csv"

    @property
    def seleccion(self) -> Path:
        return self.anotaciones / "muestra_seleccion.csv"

    @property
    def gold(self) -> Path:
        return self.anotaciones / "gold_entidades.csv"

    @property
    def estado(self) -> Path:
        return self.anotaciones / "estado_gold.csv"

    @property
    def cierre(self) -> Path:
        return self.anotaciones / "cierre_gold.json"


def rutas_gold() -> RutasGold:
    return RutasGold(C.rutas().anotaciones)


# =========================================================================== búsqueda y spans


def buscar_apariciones(texto: str, buscado: str) -> list[dict]:
    """Todas las apariciones exactas de `buscado` (`str.find` iterado), cada una con 40
    caracteres de contexto a cada lado. Nunca se elige sola la primera."""
    if not buscado:
        return []
    out, i = [], texto.find(buscado)
    while i != -1:
        f = i + len(buscado)
        out.append({"inicio": i, "fin": f, "antes": texto[max(0, i - CONTEXTO):i],
                    "despues": texto[f:f + CONTEXTO]})
        i = texto.find(buscado, i + 1)
    return out


def tokens(texto: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", texto)]


def recortar_puntuacion(texto: str, ini: int, fin: int) -> tuple[int, int]:
    """Quita puntuación de apertura al inicio y de cierre al final; nunca quita `$`."""
    while ini < fin and texto[ini] in PUNTUACION_INICIAL:
        ini += 1
    while fin > ini and texto[fin - 1] in PUNTUACION_FINAL:
        fin -= 1
    return ini, fin


def errores_span(texto: str, filas_pasaje: pd.DataFrame, tipo: str, ini: int, fin: int,
                 ignorar: int | None = None) -> list[str]:
    """Validación en vivo antes de agregar o editar: tipo, invariante de offsets, duplicado y
    solape o anidamiento con otra fila del mismo pasaje (`ignorar`: índice de la fila editada)."""
    err = []
    if tipo not in TIPOS:
        err.append(f"Tipo no válido: {tipo}")
    if not (0 <= ini < fin <= len(texto)):
        err.append(f"Offsets fuera de rango: ({ini}, {fin})")
        return err
    if not texto[ini:fin].strip():
        err.append("El span está vacío")
    if texto[ini:fin] != texto[ini:fin].strip():
        err.append("El span empieza o termina con espacio")
    for idx, f in filas_pasaje.iterrows():
        if ignorar is not None and idx == ignorar:
            continue
        a, b = int(f["inicio"]), int(f["fin"])
        if (a, b, f["tipo"]) == (ini, fin, tipo):
            err.append("Duplicado: ya existe esa entidad")
        elif ini < b and a < fin:
            err.append(f"Se solapa o anida con «{f['texto']}» ({f['tipo']}, {a}-{b})")
    return err


# =========================================================================== persistencia


def _csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, lineterminator="\n").encode("utf-8")


def token(r: RutasGold) -> str:
    return C.sha256_ruta(r.gold) + C.sha256_ruta(r.estado)


def cargar(r: RutasGold) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    gold = (pd.read_csv(r.gold, dtype={"passage_id": str, "tipo": str, "texto": str},
                        keep_default_na=False)
            if r.gold.exists() else pd.DataFrame(columns=COLUMNAS_GOLD))
    estado = (pd.read_csv(r.estado, dtype={"passage_id": str, "texto_sha256": str,
                                           "estado": str}, keep_default_na=False)
              if r.estado.exists() else pd.DataFrame(columns=COLUMNAS_ESTADO))
    for c in ("inicio", "fin"):
        gold[c] = gold[c].astype(int)
    for c in ("n_entidades", "revision"):
        estado[c] = estado[c].astype(int)
    return gold[COLUMNAS_GOLD], estado[COLUMNAS_ESTADO], token(r)


def _guardar(r: RutasGold, gold: pd.DataFrame, estado: pd.DataFrame, tok: str,
             pid: str, sha: str, nuevo_estado: str | None) -> str:
    if r.cierre.exists():
        raise ValueError("El gold ya está cerrado (`cierre_gold.json`). Un cambio exige revisión "
                         "explícita del alumno y nueva versión (skill gold-anotacion).")
    if not C.reglas_congeladas():
        raise ValueError("Falta `reglas-congeladas` (D15): el gold no se abre antes de congelar.")
    if token(r) != tok:
        raise C.ConflictoEdicion("editado desde otra pestaña: recarga antes de guardar.")
    gold = gold.sort_values(["passage_id", "inicio", "fin", "tipo"]).reset_index(drop=True)
    n = int((gold["passage_id"] == pid).sum())
    previo = estado[estado["passage_id"] == pid]
    rev = int(previo["revision"].iloc[0]) + 1 if len(previo) else 1
    est = nuevo_estado or (previo["estado"].iloc[0] if len(previo) else ABIERTO)
    if nuevo_estado is None and est == CERRADO:
        est = ABIERTO  # cualquier cambio reabre el pasaje: hay que volver a revisarlo completo
    fila = pd.DataFrame([{"passage_id": pid, "texto_sha256": sha, "estado": est,
                          "n_entidades": n, "revision": rev}])
    estado = pd.concat([estado[estado["passage_id"] != pid], fila], ignore_index=True)
    estado = estado.sort_values("passage_id").reset_index(drop=True)[COLUMNAS_ESTADO]
    C.escribir_atomico(r.gold, _csv(gold[COLUMNAS_GOLD]))
    C.escribir_atomico(r.estado, _csv(estado))
    return token(r)


def agregar(r: RutasGold, tok: str, pid: str, texto: str, sha: str, tipo: str, ini: int,
            fin: int) -> str:
    gold, estado, _ = cargar(r)
    err = errores_span(texto, gold[gold["passage_id"] == pid], tipo, ini, fin)
    if err:
        raise ValueError("; ".join(err))
    fila = pd.DataFrame([{"passage_id": pid, "tipo": tipo, "texto": texto[ini:fin],
                          "inicio": ini, "fin": fin}])
    return _guardar(r, pd.concat([gold, fila], ignore_index=True), estado, tok, pid, sha, None)


def reemplazar_pasaje(r: RutasGold, tok: str, pid: str, texto: str, sha: str,
                      filas: list[dict]) -> str:
    """Edición de la tabla (tipo, límites, borrado): valida todas las filas del pasaje juntas."""
    gold, estado, _ = cargar(r)
    nuevas = pd.DataFrame(columns=COLUMNAS_GOLD)
    for f in filas:
        ini, fin = int(f["inicio"]), int(f["fin"])
        err = errores_span(texto, nuevas, f["tipo"], ini, fin)
        if err:
            raise ValueError("; ".join(err))
        nuevas = pd.concat([nuevas, pd.DataFrame([{"passage_id": pid, "tipo": f["tipo"],
                                                   "texto": texto[ini:fin], "inicio": ini,
                                                   "fin": fin}])], ignore_index=True)
    gold = pd.concat([gold[gold["passage_id"] != pid], nuevas], ignore_index=True)
    return _guardar(r, gold, estado, tok, pid, sha, None)


def marcar(r: RutasGold, tok: str, pid: str, sha: str, cerrado: bool) -> str:
    """"Pasaje revisado completo" (válido con cero entidades) o reabrir."""
    gold, estado, _ = cargar(r)
    return _guardar(r, gold, estado, tok, pid, sha, CERRADO if cerrado else ABIERTO)


def estado_de(estado: pd.DataFrame, pid: str) -> str:
    f = estado[estado["passage_id"] == pid]
    return f["estado"].iloc[0] if len(f) else ABIERTO


# =========================================================================== validación y cierre


@dataclass
class ValidacionGold:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    cerrados: int = 0
    esperados: int = 0
    pasajes_con_entidades: int = 0

    @property
    def ok(self) -> bool:
        return not self.errores


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=config.RAIZ, capture_output=True, text=True,
                          check=False)


def etiqueta_precede_al_gold(ruta_gold: Path) -> str | None:
    """Error si `reglas-congeladas` no existe o no es ancestro del primer commit que agregó el
    archivo gold. Sin commits del gold todavía, basta con que la etiqueta exista."""
    if not _git("tag", "-l", "reglas-congeladas").stdout.strip():
        return "Falta la etiqueta `reglas-congeladas` (D15)"
    try:
        rel = str(Path(ruta_gold).resolve().relative_to(config.RAIZ))
    except ValueError:
        return None  # archivo fuera del repo (pruebas): no hay historia que revisar
    primeros = _git("log", "--diff-filter=A", "--format=%H", "--", rel).stdout.split()
    if not primeros:
        return None
    etiqueta = _git("rev-list", "-n", "1", "reglas-congeladas").stdout.strip()
    if etiqueta == primeros[-1] or _git("merge-base", "--is-ancestor", etiqueta,
                                        primeros[-1]).returncode != 0:
        return "La etiqueta `reglas-congeladas` no precede al primer commit del gold"
    return None


def validar_gold(r: RutasGold, pasajes: pd.DataFrame, por_consulta: int = 2,
                 n_consultas: int = 10) -> ValidacionGold:
    """PRD §6.11. `pasajes`: `passage_id, texto, texto_sha256` (al menos los de la muestra)."""
    v = ValidacionGold()
    if not r.muestra.exists():
        v.errores.append("No existe anotaciones/muestra_gold.csv (make muestra-gold)")
        return v
    man = pd.read_csv(r.muestra, dtype={"passage_id": str, "texto_sha256": str})
    v.esperados = len(man)
    if not man["passage_id"].is_unique:
        v.errores.append("El manifiesto tiene IDs repetidos")
    if len(man) != por_consulta * n_consultas or not man["query_id"].value_counts().eq(
            por_consulta).all() or man["query_id"].nunique() != n_consultas:
        v.errores.append(f"El manifiesto no tiene {por_consulta} pasajes por cada una de las "
                         f"{n_consultas} consultas")
    info = pasajes.set_index("passage_id")
    for pid, sha in zip(man["passage_id"], man["texto_sha256"]):
        if pid not in info.index:
            v.errores.append(f"{pid} no existe en data/pasajes.parquet")
        elif info.at[pid, "texto_sha256"] != sha:
            v.errores.append(f"{pid}: el texto cambió desde el sorteo (hash distinto)")
    if r.seleccion.exists():
        sel = pd.read_csv(r.seleccion, dtype={"passage_id": str})
        if set(sel["passage_id"]) & set(man["passage_id"]):
            v.errores.append("La selección no es disjunta del gold")

    gold, estado, _ = cargar(r)
    if r.gold.exists() and list(pd.read_csv(r.gold, nrows=0).columns) != COLUMNAS_GOLD:
        v.errores.append(f"Columnas de gold_entidades.csv distintas de {COLUMNAS_GOLD}")
    if r.gold.exists() and r.gold.read_bytes()[:3] == b"\xef\xbb\xbf":
        v.errores.append("gold_entidades.csv tiene BOM")
    fuera = sorted(set(gold["passage_id"]) - set(man["passage_id"]))
    if fuera:
        v.errores.append(f"Entidades de pasajes fuera de la muestra: {fuera[:5]}")
    if gold.duplicated(["passage_id", "tipo", "inicio", "fin"]).any():
        v.errores.append("Filas duplicadas en la clave (passage_id, tipo, inicio, fin)")
    malos = sorted(set(gold["tipo"]) - set(TIPOS))
    if malos:
        v.errores.append(f"Tipos no válidos: {malos}")
    rotas = 0
    for f in gold.itertuples(index=False):
        t = info.at[f.passage_id, "texto"] if f.passage_id in info.index else ""
        if not f.texto or not (0 <= f.inicio < f.fin <= len(t)) or t[f.inicio:f.fin] != f.texto:
            rotas += 1
    if rotas:
        v.errores.append(f"{rotas} filas rompen el invariante de offsets")
    for pid, g in gold.groupby("passage_id"):
        g = g.sort_values(["inicio", "fin"])
        if (g["inicio"].to_numpy()[1:] < g["fin"].to_numpy()[:-1]).any():
            v.errores.append(f"{pid}: entidades solapadas o anidadas")

    est = estado.set_index("passage_id")
    v.cerrados = int(sum(est.at[p, "estado"] == CERRADO for p in man["passage_id"]
                         if p in est.index))
    if v.cerrados < len(man):
        v.errores.append(f"Pasajes cerrados: {v.cerrados} de {len(man)}")
    for pid, sha in zip(man["passage_id"], man["texto_sha256"]):
        if pid in est.index and est.at[pid, "texto_sha256"] != sha:
            v.errores.append(f"{pid}: estado_gold.csv con otro hash de texto")
    v.pasajes_con_entidades = int(gold["passage_id"].nunique())
    vacios = len(man) - v.pasajes_con_entidades
    if vacios:
        v.avisos.append(f"{vacios} pasajes cerrados sin entidades: el kit no los evalúa (P04); "
                        "la evaluación complementaria de 20 IDs sí los cuenta")
    e = etiqueta_precede_al_gold(r.gold)
    if e:
        v.errores.append(e)
    return v


def _sha(ruta: Path) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest() if Path(ruta).exists() else ""


def cerrar_gold(r: RutasGold, pasajes: pd.DataFrame, raiz: Path = config.RAIZ) -> dict:
    """Escribe `cierre_gold.json` y exporta `gold_entidades.csv` a la raíz, solo si
    `validar_gold()` pasa. A partir de aquí se desbloquean las predicciones en la app."""
    v = validar_gold(r, pasajes)
    if not v.ok:
        raise ValueError("No se puede cerrar el gold: " + "; ".join(v.errores))
    man = pd.read_csv(r.muestra, dtype={"passage_id": str, "texto_sha256": str})
    cierre = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "sha256_muestra_gold": _sha(r.muestra),
        "sha256_muestra_seleccion": _sha(r.seleccion),
        "textos": dict(zip(man["passage_id"], man["texto_sha256"])),
        "sha256_protocolo": _sha(config.DIR_CONFIG / "protocolo.txt"),
        "sha256_criterios_anotacion": _sha(config.DIR_CONFIG / "criterios_anotacion.md"),
        "sha256_gold_entidades": _sha(r.gold),
        "sha256_estado_gold": _sha(r.estado),
        "pasajes": len(man), "pasajes_con_entidades": v.pasajes_con_entidades,
        "entidades": len(cargar(r)[0]), "avisos": v.avisos,
    }
    C.escribir_atomico(r.cierre, (json.dumps(cierre, ensure_ascii=False, indent=2) + "\n")
                       .encode("utf-8"), respaldo=False)
    destino = Path(raiz) / "gold_entidades.csv"
    if not r.gold.exists():  # 20 pasajes sin entidades: se exporta solo la cabecera
        C.escribir_atomico(destino, _csv(pd.DataFrame(columns=COLUMNAS_GOLD)), respaldo=False)
    else:
        C.escribir_atomico(destino, r.gold.read_bytes(), respaldo=False)
    return cierre


# =========================================================================== resaltado


def spans_para_mostrar(gold_pasaje: pd.DataFrame, inicio_cuerpo: int) -> list[tuple[int, int, str]]:
    """Entidades del gold (clase = tipo) y la marca de interlocutor en gris en los huecos que no
    cubre ninguna entidad, para que no se solapen al renderizar desde offsets."""
    ents = sorted((int(f.inicio), int(f.fin), f"gold {f.tipo}")
                  for f in gold_pasaje.itertuples(index=False))
    spans, cursor = [], 0
    for ini, fin, _ in ents:
        if cursor < min(ini, inicio_cuerpo):
            spans.append((cursor, min(ini, inicio_cuerpo), "marca"))
        cursor = max(cursor, fin)
    if cursor < inicio_cuerpo:
        spans.append((cursor, inicio_cuerpo, "marca"))
    return sorted(spans + ents)
