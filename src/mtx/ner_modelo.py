"""NER con modelo preentrenado (PRD §6.8, D09, D18, U15, T12).

Flujo por pasaje: ventanas de subtokens con solapamiento → pipeline HF `token-classification`
(`aggregation_strategy="simple"`, CPU) → entidades crudas con offsets proyectados al `texto`
canónico → caché JSON versionada. El posproceso (mapa de etiquetas, recorte de extremos y uniones)
se recalcula siempre desde lo crudo con su propia versión: cambiarlo nunca obliga a reinferir.

Offsets: índices de carácter Python sobre el `texto` completo; se verifica
`texto[inicio:fin] == texto_entidad` tras cada etapa.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from mtx import config

RUTA_CONFIG = config.DIR_CONFIG / "ner.yaml"
DIR_CACHE = config.DIR_DATA / "cache_ner"
COLUMNAS_ENTIDADES = ["query_id", "doc_id", "passage_id", "tipo", "texto", "inicio", "fin",
                      "metodo"]
COLUMNAS_UNIONES = ["passage_id", "tipo", "inicio_1", "fin_1", "inicio_2", "fin_2",
                    "inicio_union", "fin_union", "texto_union", "confianza_1", "confianza_2"]
RECORTABLES = set(" \t\n\r.,;:!?¿¡()[]{}\"'«»“”‘’-–—…/*")
"""Caracteres que se quitan de los extremos de un span. `$`, dígitos y letras nunca se quitan."""


@dataclass(frozen=True)
class ConfigModelo:
    slug: str
    repo_id: str
    revision: str
    max_length_real: int
    ventana: int
    solape: int
    lote: int = 8
    aggregation_strategy: str = "simple"
    device: int = -1
    mapa_etiquetas: dict = field(default_factory=dict)
    descartadas: tuple = ()
    version_posproceso: int = 1

    @property
    def revision_corta(self) -> str:
        return self.revision[:8]

    def parametros_inferencia(self) -> dict:
        """Lo que entra en la clave de caché: modelo, revisión, tokenizador, fragmentación e
        inferencia. El lote y el posproceso no cambian lo crudo y quedan fuera."""
        return {"repo_id": self.repo_id, "revision": self.revision,
                "tokenizador": f"{self.repo_id}@{self.revision}",
                "max_length_real": self.max_length_real, "ventana": self.ventana,
                "solape": self.solape, "aggregation_strategy": self.aggregation_strategy}


def cargar_config(ruta: Path = RUTA_CONFIG) -> tuple[str, dict[str, ConfigModelo]]:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    modelos = {}
    for slug, d in datos["modelos"].items():
        d = dict(d)
        d["descartadas"] = tuple(d.get("descartadas", ()))
        if not d.get("revision") or d["revision"] in ("main", "master"):
            raise ValueError(f"{slug}: la revisión debe ser un commit fijo, no '{d.get('revision')}'")
        if d["ventana"] > d["max_length_real"] or d["solape"] >= d["ventana"]:
            raise ValueError(f"{slug}: ventana y solape incoherentes con max_length_real")
        modelos[slug] = ConfigModelo(slug=slug, **d)
    return datos["principal"], modelos


# =========================================================================== ventanas


def _inicio_palabra(offs: list[tuple[int, int]], i: int) -> int:
    """Retrocede hasta un subtoken que empieza palabra (no pegado al anterior)."""
    while 0 < i < len(offs) and offs[i][0] == offs[i - 1][1]:
        i -= 1
    return i


def ventanas(offs: list[tuple[int, int]], largo_texto: int, ventana: int,
             solape: int) -> list[tuple[int, int]]:
    """Tramos de caracteres `[ini, fin)` que cubren todo el texto, cada uno con a lo más
    `ventana` subtokens, cortados en inicio de palabra y con `solape` subtokens compartidos.
    Error explícito si la cobertura no es completa (nunca truncamiento silencioso)."""
    n = len(offs)
    if n == 0:
        return [(0, largo_texto)] if largo_texto else []
    tramos, i = [], 0
    while True:
        j = min(i + ventana, n)
        if j < n:
            j2 = _inicio_palabra(offs, j)
            j = j2 if j2 > i else j  # una palabra más larga que la ventana se corta por subtoken
        ini = 0 if i == 0 else offs[i][0]
        fin = largo_texto if j == n else offs[j][0]
        tramos.append((ini, fin))
        if j == n:
            break
        sig = _inicio_palabra(offs, max(j - solape, i + 1))
        i = sig if sig > i else j
    if tramos[0][0] != 0 or tramos[-1][1] != largo_texto or any(
            b[0] > a[1] for a, b in itertools.pairwise(tramos)):
        raise ValueError(f"Las ventanas no cubren el texto: {tramos}")
    return tramos


# =========================================================================== inferencia y caché


def clave_cache(cfg: ConfigModelo, texto_sha256: str) -> str:
    datos = json.dumps({"texto_sha256": texto_sha256, **cfg.parametros_inferencia()},
                       sort_keys=True)
    return hashlib.sha256(datos.encode()).hexdigest()


def dir_cache(cfg: ConfigModelo, raiz: Path = DIR_CACHE) -> Path:
    return Path(raiz) / f"{cfg.slug}@{cfg.revision_corta}"


def leer_cache(cfg: ConfigModelo, passage_id: str, texto_sha256: str,
               raiz: Path = DIR_CACHE) -> dict | None:
    ruta = dir_cache(cfg, raiz) / f"{passage_id}.json"
    if not ruta.exists():
        return None
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos if datos.get("clave") == clave_cache(cfg, texto_sha256) else None


def construir_pipeline(cfg: ConfigModelo):
    """Pipeline HF y tokenizador con la revisión fija. Se importa aquí para que el resto del
    módulo (posproceso, caché) no dependa de transformers ni de la red."""
    from transformers import AutoTokenizer, pipeline

    tok = AutoTokenizer.from_pretrained(cfg.repo_id, revision=cfg.revision)
    if not tok.is_fast:
        raise ValueError(f"{cfg.repo_id}: el tokenizador no es rápido; no hay offset_mapping")
    pipe = pipeline("token-classification", model=cfg.repo_id, revision=cfg.revision,
                    tokenizer=tok, aggregation_strategy=cfg.aggregation_strategy,
                    device=cfg.device)
    return pipe, tok


def inferir_pasaje(texto: str, pipe, tok, cfg: ConfigModelo) -> list[dict]:
    """Entidades crudas (etiqueta original del modelo) con offsets sobre `texto`. En el traslape
    de ventanas se deduplica por span; ante conflicto gana la no cortada por un borde y después
    la de mayor confianza (un puntaje, no una probabilidad calibrada)."""
    enc = tok(texto, add_special_tokens=False, return_offsets_mapping=True)
    tramos = ventanas([tuple(o) for o in enc["offset_mapping"]], len(texto), cfg.ventana,
                      cfg.solape)
    subtextos = [texto[a:b] for a, b in tramos]
    for s in subtextos:
        n = len(tok(s, add_special_tokens=True)["input_ids"])
        if n > cfg.max_length_real + 2:
            raise ValueError(f"Ventana de {n} subtokens excede el límite del modelo")
    salidas = pipe(subtextos, batch_size=cfg.lote)
    if subtextos and isinstance(salidas, list) and salidas and isinstance(salidas[0], dict):
        salidas = [salidas]  # una sola ventana: algunas versiones no anidan
    cand = []
    for k, ((a, b), ents) in enumerate(zip(tramos, salidas)):
        for e in ents:
            ini, fin = a + int(e["start"]), a + int(e["end"])
            cortada = (int(e["start"]) == 0 and a > 0) or (int(e["end"]) >= b - a
                                                            and b < len(texto))
            cand.append({"etiqueta": str(e["entity_group"]), "inicio": ini, "fin": fin,
                         "texto": texto[ini:fin], "confianza": round(float(e["score"]), 6),
                         "ventana": k, "cortada": cortada})
    return deduplicar(cand)


def deduplicar(cand: list[dict]) -> list[dict]:
    aceptadas: list[dict] = []
    for c in sorted(cand, key=lambda c: (c["cortada"], -c["confianza"], c["inicio"])):
        if not any(c["inicio"] < x["fin"] and x["inicio"] < c["fin"] for x in aceptadas):
            aceptadas.append(c)
    return sorted(aceptadas, key=lambda c: (c["inicio"], c["fin"]))


@dataclass
class Registro:
    inferidos: int = 0
    cacheados: int = 0
    segundos_carga: float = 0.0
    segundos_inferencia: float = 0.0
    ventanas: int = 0


def ejecutar(cfg: ConfigModelo, pasajes, forzar: bool = False, raiz: Path = DIR_CACHE,
             constructor: Callable = construir_pipeline) -> tuple[dict[str, dict], Registro]:
    """Devuelve el JSON crudo por `passage_id`. Solo carga el modelo si hay pasajes sin caché
    vigente (o con `forzar`). `pasajes`: DataFrame con `passage_id, texto, texto_sha256`."""
    reg, crudos, pendientes = Registro(), {}, []
    for pid, texto, sha in zip(pasajes["passage_id"], pasajes["texto"], pasajes["texto_sha256"]):
        c = None if forzar else leer_cache(cfg, pid, sha, raiz)
        if c is None:
            pendientes.append((pid, texto, sha))
        else:
            crudos[pid] = c
            reg.cacheados += 1
    if not pendientes:
        return crudos, reg
    t0 = time.perf_counter()
    pipe, tok = constructor(cfg)
    reg.segundos_carga = round(time.perf_counter() - t0, 2)
    try:
        import transformers
        version_tf = transformers.__version__
    except ImportError:
        version_tf = ""
    destino = dir_cache(cfg, raiz)
    destino.mkdir(parents=True, exist_ok=True)
    for pid, texto, sha in pendientes:
        t1 = time.perf_counter()
        ents = inferir_pasaje(texto, pipe, tok, cfg)
        dur = round(time.perf_counter() - t1, 3)
        datos = {"clave": clave_cache(cfg, sha), "passage_id": pid, "texto_sha256": sha,
                 "parametros": cfg.parametros_inferencia(), "entidades_crudas": ents,
                 "segundos": dur, "version_transformers": version_tf}
        (destino / f"{pid}.json").write_text(
            json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        crudos[pid] = datos
        reg.inferidos += 1
        reg.segundos_inferencia += dur
        reg.ventanas += len({e["ventana"] for e in ents}) or 1
    reg.segundos_inferencia = round(reg.segundos_inferencia, 2)
    return crudos, reg


# =========================================================================== posproceso


def etiqueta_base(etiqueta: str) -> str:
    """`B-PER` → `PER`; con `aggregation_strategy` ya llega sin prefijo."""
    return etiqueta.split("-", 1)[1] if etiqueta[:2] in ("B-", "I-") else etiqueta


def _verificar(texto: str, filas: list[dict], etapa: str) -> None:
    for f in filas:
        if not (0 <= f["inicio"] < f["fin"] <= len(texto)) or texto[f["inicio"]:f["fin"]] != f["texto"]:
            raise ValueError(f"Invariante de offsets roto en la etapa '{etapa}': {f}")


def recortar(texto: str, ini: int, fin: int) -> tuple[int, int]:
    while ini < fin and texto[ini] in RECORTABLES:
        ini += 1
    while fin > ini and texto[fin - 1] in RECORTABLES:
        fin -= 1
    return ini, fin


@dataclass
class Posproceso:
    entidades: list[dict]          # tras recorte y uniones
    sin_union_interpalabra: list[dict]
    uniones: list[dict]
    descartadas: Counter


def posprocesar(texto: str, crudas: list[dict], cfg: ConfigModelo,
                passage_id: str = "") -> Posproceso:
    """U15: mapa de etiquetas (solo las del modelo), recorte de extremos, unión intrapalabra
    siempre y unión interpalabra (un solo espacio, mismo tipo) registrada."""
    _verificar(texto, crudas, "crudo")
    descartadas: Counter = Counter()
    filas = []
    for e in crudas:
        base = etiqueta_base(e["etiqueta"])
        if base in cfg.descartadas:
            descartadas[base] += 1
            continue
        tipo = cfg.mapa_etiquetas.get(base)
        if tipo is None:
            descartadas[base] += 1
            continue
        ini, fin = recortar(texto, e["inicio"], e["fin"])
        if ini >= fin:
            descartadas["vacia_tras_recorte"] += 1
            continue
        filas.append({"tipo": tipo, "inicio": ini, "fin": fin, "texto": texto[ini:fin],
                      "confianza": e["confianza"]})
    filas.sort(key=lambda f: (f["inicio"], f["fin"]))
    _verificar(texto, filas, "recorte")

    def unir(filas: list[dict], separador: str | None, registrar: list | None) -> list[dict]:
        out: list[dict] = []
        for f in filas:
            p = out[-1] if out else None
            pegada = p is not None and p["tipo"] == f["tipo"] and (
                p["fin"] == f["inicio"] if separador is None
                else texto[p["fin"]:f["inicio"]] == separador)
            if pegada:
                u = {"tipo": p["tipo"], "inicio": p["inicio"], "fin": f["fin"],
                     "texto": texto[p["inicio"]:f["fin"]],
                     "confianza": min(p["confianza"], f["confianza"])}
                if registrar is not None:
                    registrar.append({"passage_id": passage_id, "tipo": p["tipo"],
                                      "inicio_1": p["inicio"], "fin_1": p["fin"],
                                      "inicio_2": f["inicio"], "fin_2": f["fin"],
                                      "inicio_union": u["inicio"], "fin_union": u["fin"],
                                      "texto_union": u["texto"],
                                      "confianza_1": p["confianza"],
                                      "confianza_2": f["confianza"]})
                out[-1] = u
            else:
                out.append(dict(f))
        return out

    intra = unir(filas, None, None)
    _verificar(texto, intra, "union_intrapalabra")
    uniones: list[dict] = []
    final = unir(intra, " ", uniones)
    _verificar(texto, final, "union_interpalabra")
    return Posproceso(final, intra, uniones, descartadas)


def modelo_ner_json(cfg: ConfigModelo, criterio: str = "tecnico", f1: float | None = None,
                    f1_alt: float | None = None) -> dict:
    """`data/modelo_ner.json` (D09): se fija antes de leer el gold."""
    return {"modelo": cfg.repo_id, "slug": cfg.slug, "revision": cfg.revision,
            "f1_seleccion": f1, "f1_seleccion_alternativa": f1_alt, "criterio": criterio}


def registro_dict(reg: Registro) -> dict:
    return asdict(reg)
