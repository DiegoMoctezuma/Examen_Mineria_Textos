"""Cierres humanos de v2: `cierre_juicios_v2.json` y `cierre_gold_v2.json` (PRD v2 §4, D24, D31,
D32 y §9 criterio 5).

Un cierre comprueba que el trabajo humano está completo y es coherente, y deja una constancia
con hashes de todo lo que se cerró y del commit en que estaba. No produce, sugiere ni cambia
ningún juicio ni ninguna entidad: lee lo que escribieron las personas.

- **Juicios:** cada par de `data/v2/asignacion_juicios.csv` con sus 3 jueces y 3 juicios válidos
  (0 o 1; un omitido no cuenta, D24). Cada archivo de `anotaciones/juicios_v2/` pasa
  `validar_juicios()` contra los pares que tiene asignados. La agregación por mayoría es de WP-02.
- **Gold:** `validar_gold_v2()` con las dos pasadas; `reglas-fecha-v2` y `data/modelo_ner.json` v2
  en commits anteriores (D33, D34). Escribe además `anotaciones/gold_v2/adjudicado.csv`, el gold
  oficial consolidado de las partes (`gold_oficial()`).

Los dos exigen que los insumos estén commiteados (el hash del cierre debe corresponder a un
commit) y no se reescriben: un cambio posterior se registra en `docs/decisiones.md`.
Los mensajes solo dan conteos e IDs, nunca valores de juicio ni entidades.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from mtx import anotadores as A
from mtx import config, pool
from mtx import gold_v2 as V
from mtx.app import componentes as C

NOMBRE_CIERRE_JUICIOS = "cierre_juicios_v2.json"
NOMBRE_CIERRE_GOLD = "cierre_gold_v2.json"
NOMBRE_ADJUDICADO = "adjudicado.csv"
JUECES_POR_PAR = 3
ETIQUETA_INICIO = "v2-inicio"
MODELO_NER = config.DIR_DATA / "modelo_ner.json"
VALIDOS = ("0", "1")


@dataclass
class Revision:
    """Resultado de revisar un cierre. `ok` = se puede cerrar."""
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    resumen: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errores


# =========================================================================== git


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=config.RAIZ, capture_output=True, text=True,
                          check=False)


def _rel(ruta: Path) -> str | None:
    try:
        return str(Path(ruta).resolve().relative_to(config.RAIZ.resolve()))
    except ValueError:
        return None  # fuera del repo (pruebas)


def sin_commitear(rutas: list[Path]) -> list[str]:
    """Rutas del repo con cambios sin commitear o sin versionar. Las que están fuera del repo
    (carpetas temporales de las pruebas) no se revisan."""
    rel = [r for r in (_rel(x) for x in rutas) if r]
    if not rel:
        return []
    salida = _git("status", "--porcelain", "--untracked-files=all", "--", *rel).stdout
    return sorted({linea[3:].strip() for linea in salida.splitlines() if linea.strip()})


def commit_actual() -> str:
    return _git("rev-parse", "HEAD").stdout.strip()


def commit_de_etiqueta(nombre: str) -> str | None:
    r = _git("rev-list", "-n", "1", nombre)
    return r.stdout.strip() or None if r.returncode == 0 else None


def ultimo_commit_de(ruta: str) -> str | None:
    return _git("log", "-n", "1", "--format=%H", "--", ruta).stdout.strip() or None


def es_ancestro(a: str, b: str) -> bool:
    """`a` es ancestro de `b` (o el mismo commit)."""
    return _git("merge-base", "--is-ancestor", a, b).returncode == 0


def _sha(ruta: Path) -> str:
    return C.sha256_ruta(ruta)


def _json(d: dict) -> bytes:
    return (json.dumps(d, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _ruta_repo(ruta: Path) -> str:
    return _rel(ruta) or Path(ruta).name


# =========================================================================== juicios


def ruta_cierre_juicios(dir_anot: Path | None = None) -> Path:
    return Path(dir_anot or V.dir_anotaciones()) / NOMBRE_CIERRE_JUICIOS


def juicios_cerrados(dir_anot: Path | None = None) -> bool:
    """D32: hasta este cierre nadie del lote 2 ve resultados con lema ni de Q11 a Q15."""
    return ruta_cierre_juicios(dir_anot).exists()


def _leer_juicios(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        return pd.DataFrame(columns=pool.COLUMNAS_JUICIOS, dtype=str)
    return pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def revisar_juicios_v2(asignacion: pd.DataFrame, pasajes: pd.DataFrame,
                       dir_anot: Path | None = None,
                       aceptar_incompletos: bool = False) -> Revision:
    """¿Se pueden cerrar los juicios v2? `pasajes`: `passage_id, texto`.

    Errores: un juez sin archivo o con un archivo que no pasa `validar_juicios()` contra sus pares
    asignados (formato, valores, duplicados, pares fuera de su asignación, texto cambiado), un par
    con un número de jueces asignados distinto de 3 y, salvo `aceptar_incompletos`, un par con
    menos de 3 juicios válidos. Con `aceptar_incompletos` esos pares se listan y quedan sin
    cerrar: la agregación (WP-02) no los cuenta (D24)."""
    dir_anot = Path(dir_anot or V.dir_anotaciones())
    rev = Revision()
    errores_asig = A.validar_asignacion(asignacion)
    rev.errores += errores_asig
    jueces = sorted(set(asignacion["anotador"]))
    validos: dict[tuple[str, str], int] = {}
    por_juez = {}
    for a in jueces:
        asig = asignacion[asignacion["anotador"] == a]
        ruta = A.ruta_juicios(dir_anot, a)
        if not ruta.exists():
            rev.errores.append(f"{a}: no existe {ruta.name}")
            continue
        v = pool.validar_juicios(ruta, asig[["query_id", "doc_id", "passage_id",
                                             "texto_sha256"]], pasajes)
        # La cobertura se revisa par por par abajo, con los tres jueces juntos.
        rev.errores += [f"{a}: {e}" for e in v.errores
                        if not e.startswith("Cobertura incompleta")]
        j = _leer_juicios(ruta)
        claves = set(zip(asig["query_id"], asig["passage_id"]))
        hechos = {k for k, x in zip(zip(j["query_id"], j["passage_id"]), j["relevante"])
                  if x in VALIDOS and k in claves}
        for k in hechos:
            validos[k] = validos.get(k, 0) + 1
        por_juez[a] = {"archivo": _ruta_repo(ruta), "sha256": _sha(ruta),
                       "lotes": sorted(set(asig["lote"]), key=int), "asignados": len(asig),
                       "juzgados": len(hechos), "sin_juicio": len(asig) - len(hechos)}

    n_jueces = asignacion.groupby(["query_id", "passage_id"])["anotador"].nunique()
    malos = n_jueces[n_jueces != JUECES_POR_PAR]
    if len(malos):
        rev.errores.append(f"{len(malos)} pares sin {JUECES_POR_PAR} jueces asignados: "
                           f"{[f'{q}/{p}' for q, p in malos.index[:5]]}")
    incompletos = sorted(k for k in n_jueces.index if validos.get(k, 0) < JUECES_POR_PAR)
    if incompletos:
        msg = (f"{len(incompletos)} de {len(n_jueces)} pares con menos de {JUECES_POR_PAR} "
               f"juicios válidos: {[f'{q}/{p}' for q, p in incompletos[:5]]}")
        (rev.avisos if aceptar_incompletos else rev.errores).append(
            msg + (" (quedan sin cerrar y la agregación no los cuenta)" if aceptar_incompletos
                   else ""))
    lotes = {lote: int(g[["query_id", "passage_id"]].drop_duplicates().shape[0])
             for lote, g in asignacion.groupby("lote")}
    rev.resumen = {
        "pares": int(len(n_jueces)), "pares_por_lote": lotes,
        "pares_cerrados": int(len(n_jueces) - len(incompletos)),
        "pares_sin_cerrar": [{"query_id": q, "passage_id": p} for q, p in incompletos],
        "juicios_por_par": JUECES_POR_PAR, "jueces": por_juez,
    }
    return rev


def cerrar_juicios_v2(asignacion: pd.DataFrame, pasajes: pd.DataFrame,
                      ruta_asignacion: Path, ruta_anotadores: Path, ruta_criterios: Path,
                      meta_pool: dict | None, dir_anot: Path | None = None,
                      aceptar_incompletos: bool = False) -> dict:
    """Escribe `anotaciones/cierre_juicios_v2.json` si `revisar_juicios_v2()` pasa, todos los
    insumos están commiteados y aún no hay cierre. `meta_pool`: `salida/v2/04_pool_meta.json`."""
    dir_anot = Path(dir_anot or V.dir_anotaciones())
    destino = ruta_cierre_juicios(dir_anot)
    if destino.exists():
        raise ValueError(f"Ya existe {destino.name}: un cierre no se reescribe (registra el "
                         "cambio en docs/decisiones.md)")
    rev = revisar_juicios_v2(asignacion, pasajes, dir_anot, aceptar_incompletos)
    archivos = [A.ruta_juicios(dir_anot, a) for a in sorted(set(asignacion["anotador"]))]
    sucios = sin_commitear(archivos + [ruta_asignacion, ruta_anotadores, ruta_criterios])
    if sucios:
        rev.errores.append(f"Sin commitear: {sucios[:5]}")
    if not rev.ok:
        raise ValueError("No se pueden cerrar los juicios v2:\n- " + "\n- ".join(rev.errores))
    cierre = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "commit": commit_actual(),
        "sha256_asignacion": _sha(ruta_asignacion),
        "sha256_anotadores": _sha(ruta_anotadores),
        "sha256_criterios_relevancia": _sha(ruta_criterios),
        "sha256_pool_v2": (meta_pool or {}).get("sha256_pool", ""),
        "sha256_pool_v2_csv": (meta_pool or {}).get("sha256_pool_csv", ""),
        "aceptar_incompletos": aceptar_incompletos,
        **rev.resumen,
        "avisos": rev.avisos,
    }
    C.escribir_atomico(destino, _json(cierre), respaldo=False)
    return cierre


# =========================================================================== gold


def ruta_cierre_gold(dir_anot: Path | None = None) -> Path:
    return Path(dir_anot or V.dir_anotaciones()) / NOMBRE_CIERRE_GOLD


def ruta_adjudicado(dir_anot: Path | None = None) -> Path:
    return Path(dir_anot or V.dir_anotaciones()) / V.SUBDIR / NOMBRE_ADJUDICADO


def gold_cerrado(dir_anot: Path | None = None) -> bool:
    """D32: hasta este cierre nadie ve predicciones de los pasajes nuevos del gold v2."""
    return ruta_cierre_gold(dir_anot).exists()


def _archivos_gold(cfg: V.ConfigGold, dir_anot: Path) -> list[Path]:
    personas = sorted({a for p in cfg.partes.values() for a in p.anotadores})
    adjs = sorted({p.adjudicador for p in cfg.partes.values() if p.adjudicador})
    return ([f(dir_anot, a) for a in personas for f in (V.ruta_gold, V.ruta_estado)]
            + [f(dir_anot, a) for a in adjs for f in (V.ruta_adj, V.ruta_estado_adj)]
            + [p.manifiesto for p in cfg.partes.values()])


def revisar_orden_gold() -> list[str]:
    """Criterio 5 de PRD v2 §9: `reglas-fecha-v2` (D33) y `data/modelo_ner.json` v2 (D34) ya
    commiteados, después de `v2-inicio`, antes de cerrar el gold."""
    err = []
    inicio = commit_de_etiqueta(ETIQUETA_INICIO)
    fecha = commit_de_etiqueta(V.ETIQUETA_FECHA)
    if not fecha:
        err.append(f"Falta la etiqueta `{V.ETIQUETA_FECHA}`: las reglas FECHA v2 se congelan "
                   "antes del cierre del gold (D33, recorte 3)")
    elif inicio and not es_ancestro(inicio, fecha):
        err.append(f"`{V.ETIQUETA_FECHA}` no desciende de `{ETIQUETA_INICIO}`")
    nombre = _ruta_repo(MODELO_NER)
    ner = ultimo_commit_de(nombre)
    if sin_commitear([MODELO_NER]):
        err.append(f"`{nombre}` tiene cambios sin commitear")
    elif not ner or (inicio and (ner == inicio or not es_ancestro(inicio, ner))):
        err.append(f"`{nombre}` no tiene un commit v2 (posterior a `{ETIQUETA_INICIO}`): "
                   "el NER v2 se fija antes de cerrar el gold (D34)")
    return err


def revisar_gold_v2(cfg: V.ConfigGold, pasajes: pd.DataFrame, dir_anot: Path | None = None,
                    excluir_v1: set[str] | None = None) -> Revision:
    """¿Se puede cerrar el gold v2? Las dos pasadas terminadas y adjudicadas (`validar_gold_v2`).
    Las comprobaciones de git (orden y commits) se hacen en `cerrar_gold_v2`."""
    dir_anot = Path(dir_anot or V.dir_anotaciones())
    v = V.validar_gold_v2(cfg, pasajes, dir_anot, pasadas=(1, 2), excluir_v1=excluir_v1)
    rev = Revision(list(v.errores), list(v.avisos))
    of = V.gold_oficial(cfg, dir_anot)
    partes = {}
    for p in cfg.partes.values():
        m = V.manifiesto(p)
        f = of[of["parte"] == p.id]
        partes[p.id] = {
            "nombre": p.nombre, "anotadores": list(p.anotadores), "adjudicador": p.adjudicador,
            "manifiesto": _ruta_repo(p.manifiesto), "sha256_manifiesto": _sha(p.manifiesto),
            "textos": dict(zip(m["passage_id"], m["texto_sha256"])) if m is not None else {},
            "pasajes": 0 if m is None else len(m),
            "pasajes_con_entidades": int(f["passage_id"].nunique()),
            "entidades": int(len(f)),
            "entidades_por_tipo": {t: int(n) for t, n in f["tipo"].value_counts().sort_index()
                                   .items()},
        }
    rev.resumen = {"partes": partes, "entidades": int(len(of)),
                   "pasada_2_sin_etiqueta": cfg.pasada_2_sin_etiqueta}
    return rev


def pasajes_bloqueados_v2(dir_anot: Path | None = None) -> set[str]:
    """D32: los pasajes de la muestra v2 (selección, A y B) mientras no exista
    `cierre_gold_v2.json`; vacío después. La demo no les muestra texto ni predicciones."""
    if gold_cerrado(dir_anot):
        return set()
    cfg = V.cargar_config(dir_anot=dir_anot)
    ids: set[str] = set()
    for parte in cfg.partes.values():
        m = V.manifiesto(parte)
        if m is not None:
            ids |= set(m["passage_id"])
    return ids


def adjudicado_consolidado(cfg: V.ConfigGold, dir_anot: Path | None = None) -> pd.DataFrame:
    """El gold oficial de las partes v2 en un solo archivo (`parte` + columnas del gold)."""
    of = V.gold_oficial(cfg, dir_anot)
    return of.sort_values(["parte", "passage_id", "inicio", "fin", "tipo"]).reset_index(drop=True)


def cerrar_gold_v2(cfg: V.ConfigGold, pasajes: pd.DataFrame, ruta_anotadores: Path,
                   ruta_criterios: Path, ruta_muestreo: Path, dir_anot: Path | None = None,
                   excluir_v1: set[str] | None = None) -> dict:
    """Escribe `anotaciones/gold_v2/adjudicado.csv` y `anotaciones/cierre_gold_v2.json` si
    `revisar_gold_v2()` y `revisar_orden_gold()` pasan, los insumos están commiteados y aún no
    hay cierre. Desde aquí se levanta el modo ciego de los pasajes nuevos (D32)."""
    dir_anot = Path(dir_anot or V.dir_anotaciones())
    destino = ruta_cierre_gold(dir_anot)
    if destino.exists():
        raise ValueError(f"Ya existe {destino.name}: un cierre no se reescribe (registra el "
                         "cambio en docs/decisiones.md)")
    rev = revisar_gold_v2(cfg, pasajes, dir_anot, excluir_v1)
    rev.errores += revisar_orden_gold()
    sucios = sin_commitear(_archivos_gold(cfg, dir_anot)
                           + [ruta_anotadores, ruta_criterios, ruta_muestreo])
    if sucios:
        rev.errores.append(f"Sin commitear: {sucios[:5]}")
    if not rev.ok:
        raise ValueError("No se puede cerrar el gold v2:\n- " + "\n- ".join(rev.errores))
    adj = ruta_adjudicado(dir_anot)
    C.escribir_atomico(adj, V._csv(adjudicado_consolidado(cfg, dir_anot)), respaldo=False)
    archivos = {_ruta_repo(r): _sha(r) for r in _archivos_gold(cfg, dir_anot)
                if r.exists() and r.parent.name == V.SUBDIR}
    modelo = json.loads(MODELO_NER.read_text(encoding="utf-8"))
    cierre = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "commit": commit_actual(),
        "commit_reglas_fecha_v2": commit_de_etiqueta(V.ETIQUETA_FECHA),
        "commit_modelo_ner": ultimo_commit_de(_ruta_repo(MODELO_NER)),
        "modelo_ner": modelo.get("modelo"), "revision_modelo_ner": modelo.get("revision"),
        "sha256_anotadores": _sha(ruta_anotadores),
        "sha256_criterios_anotacion": _sha(ruta_criterios),
        "sha256_muestreo_v2": _sha(ruta_muestreo),
        "sha256_adjudicado": _sha(adj),
        "archivos": archivos,
        **rev.resumen,
        "avisos": rev.avisos,
    }
    C.escribir_atomico(destino, _json(cierre), respaldo=False)
    return cierre
