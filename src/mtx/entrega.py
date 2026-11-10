"""Las 15 condiciones de entrega de PRD §13.2 (`make validar`, `scripts/99_validar.py`).

Cada condición devuelve un estado:

- OK: el validador pasa con los artefactos y hashes actuales;
- PENDIENTE: falta un artefacto de un hito posterior o trabajo humano (no es un error);
- FALLA: el artefacto existe pero no cumple;
- AVISO: no bloquea (condición 10).

Nunca escribe datos humanos. El único efecto es la copia byte a byte de
`anotaciones/juicios_relevancia.csv` a la raíz cuando los juicios pasan la validación (cond. 4).
Las condiciones de hitos aún no construidos (H5 a H9) solo comprueban existencia y lo dicen.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from mtx import adaptadores_kit, config, evaluacion, pool
from mtx.ranking import COLUMNAS_RANKING, validar_ranking

OK, PENDIENTE, FALLA, AVISO = "OK", "PENDIENTE", "FALLA", "AVISO"

COLUMNAS_ENTIDADES = ["query_id", "doc_id", "passage_id", "tipo", "texto", "inicio", "fin",
                      "metodo"]
COLUMNAS_GOLD = ["passage_id", "tipo", "texto", "inicio", "fin"]
COLUMNAS_RESULTADOS_IE = ["metodo", "tipo", "precision", "recall", "f1", "tp", "predichas", "gold"]


@dataclass
class Resultado:
    numero: int
    titulo: str
    estado: str
    detalle: list[str]


@dataclass
class Contexto:
    rp: evaluacion.RutasIR
    correr_pruebas: bool = True
    _pasajes: pd.DataFrame | None = None

    @property
    def raiz(self) -> Path:
        return self.rp.dir_raiz

    def pasajes(self) -> pd.DataFrame:
        if self._pasajes is None:
            self._pasajes = pd.read_parquet(self.rp.app.pasajes, columns=["passage_id", "texto"])
        return self._pasajes


def _cabecera(ruta: Path) -> list[str]:
    with open(ruta, encoding="utf-8") as f:
        return f.readline().rstrip("\r\n").split(",")


# --------------------------------------------------------------------------- condiciones


def c01_kit_y_consultas(cx: Contexto) -> Resultado:
    det = adaptadores_kit.verificar_hashes()
    kit = pd.read_csv(adaptadores_kit.DIR_KIT / "consultas.csv", dtype=str, keep_default_na=False)
    cons = pd.read_csv(cx.rp.app.consultas, dtype=str, keep_default_na=False)
    if not cons.head(len(kit)).reset_index(drop=True).equals(kit):
        det.append("Q1 a Q8 de data/consultas.csv no coinciden con kit/consultas.csv")
    if list(cons["query_id"]) != [f"Q{i}" for i in range(1, 11)]:
        det.append(f"Se esperaban Q1 a Q10; hay {list(cons['query_id'])}")
    q910 = config.cargar_yaml("consultas_q9q10.yaml")
    if not str(q910.get("estado", "")).startswith("aprobadas"):
        det.append("Q9 y Q10 sin aprobación del alumno en config/consultas_q9q10.yaml")
    return Resultado(1, "Kit intacto; Q1-Q8 del kit; Q9 y Q10 del alumno",
                     FALLA if det else OK, det or ["hashes del kit y consultas vigentes"])


def _seis_csv(cx: Contexto) -> list[tuple[str, Path, list[str], str]]:
    s, a = cx.rp.dir_salida, cx.rp.app.anotaciones
    return [
        ("ranking.csv", s / "ranking.csv", COLUMNAS_RANKING, "H2"),
        ("juicios_relevancia.csv", a / "juicios_relevancia.csv", pool.COLUMNAS_JUICIOS,
         "H3, alumno"),
        ("resultados_ir.csv", s / "resultados_ir.csv", evaluacion.COLUMNAS_RESULTADOS_IR, "H4"),
        ("entidades.csv", s / "entidades.csv", COLUMNAS_ENTIDADES, "H7"),
        ("gold_entidades.csv", a / "gold_entidades.csv", COLUMNAS_GOLD, "H6, alumno"),
        ("resultados_ie.csv", s / "resultados_ie.csv", COLUMNAS_RESULTADOS_IE, "H7"),
    ]


def c02_seis_csv(cx: Contexto) -> Resultado:
    fallas, pendientes, bien = [], [], []
    for nombre, origen, columnas, hito in _seis_csv(cx):
        ruta = cx.raiz / nombre
        if not ruta.exists():
            pendientes.append(f"{nombre}: falta en la raíz ({hito})")
            continue
        if ruta.read_bytes().startswith(b"\xef\xbb\xbf"):
            fallas.append(f"{nombre}: tiene BOM")
        if _cabecera(ruta) != columnas:
            fallas.append(f"{nombre}: columnas {_cabecera(ruta)}; se esperan {columnas}")
        if not origen.exists():
            fallas.append(f"{nombre}: no existe su origen {origen.parent.name}/{origen.name}")
        elif origen.read_bytes() != ruta.read_bytes():
            fallas.append(f"{nombre}: no es copia de {origen.parent.name}/{origen.name}")
        else:
            bien.append(nombre)
    estado = FALLA if fallas else (PENDIENTE if pendientes else OK)
    return Resultado(2, "Seis CSV en la raíz, con columnas exactas y copia de su origen", estado,
                     fallas + pendientes + ([f"vigentes: {', '.join(bien)}"] if bien else []))


def c03_ranking(cx: Contexto) -> Resultado:
    ruta = cx.rp.ranking
    if not ruta.exists():
        return Resultado(3, "ranking.csv", PENDIENTE, ["falta: `make ranking`"])
    r = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    cons = pd.read_csv(cx.rp.app.consultas, dtype=str, keep_default_na=False)
    det = validar_ranking(r, cons)
    if len(r) != 400:
        det.append(f"{len(r)} filas; se esperan 400 (10 × 4 × 10) o excepciones registradas")
    if not pd.to_numeric(r["puntaje"], errors="coerce").map(pd.notna).all():
        det.append("Hay puntajes no finitos")
    faltan = set(r["passage_id"]) - set(cx.pasajes()["passage_id"])
    if faltan:
        det.append(f"{len(faltan)} passage_id no existen en data/pasajes.parquet")
    return Resultado(3, "ranking.csv: 10 × 4 × 10, rangos, puntajes, pasajes y ventanas",
                     FALLA if det else OK, det or ["400 filas válidas"])


def c04_juicios(cx: Contexto) -> Resultado:
    v = evaluacion.preparar_juicios(cx.rp, cx.pasajes())
    titulo = "juicios_relevancia.csv: 100 % del pool, {0, 1}, nada fuera, hashes vigentes"
    if v.ok:
        return Resultado(4, titulo, OK, [f"{v.juzgados} juicios; exportado a la raíz", *v.avisos])
    humanos = ("No existe", "Cobertura incompleta")
    estado = PENDIENTE if all(e.startswith(humanos) for e in v.errores) else FALLA
    extra = ["el alumno termina los juicios en `make app` (pestaña Juicios)"] \
        if estado == PENDIENTE else []
    return Resultado(4, titulo, estado, v.errores + extra)


def c05_resultados_ir(cx: Contexto) -> Resultado:
    rp = cx.rp
    titulo = "resultados_ir.csv se regenera con el kit; mejor modelo por D08"
    if not rp.resultados_raiz.exists():
        return Resultado(5, titulo, PENDIENTE, ["falta: `make evaluar-ir` tras los juicios"])
    if not rp.juicios_raiz.exists():
        return Resultado(5, titulo, FALLA, ["hay resultados_ir.csv sin juicios en la raíz"])
    det = []
    with tempfile.TemporaryDirectory() as tmp:
        nuevo = adaptadores_kit.ejecutar_evaluador("ir", rp.juicios_raiz, rp.ranking, Path(tmp))
        if nuevo.read_bytes() != rp.resultados_raiz.read_bytes():
            det.append("El kit no reproduce resultados_ir.csv: corre `make evaluar-ir`")
    res = evaluacion.leer_resultados(rp.resultados_raiz)
    cons = pd.read_csv(rp.app.consultas, dtype=str, keep_default_na=False)
    det += evaluacion.validar_resultados_ir(res, cons)
    if not rp.mejor_modelo.exists():
        det.append("Falta data/mejor_modelo.json")
    else:
        m = json.loads(rp.mejor_modelo.read_text(encoding="utf-8"))
        if m.get("modelo") != evaluacion.elegir_mejor_modelo(res)["modelo"]:
            det.append("data/mejor_modelo.json no sigue la regla D08 con los resultados actuales")
        for clave, ruta in (("sha256_ranking_csv", rp.ranking),
                            ("sha256_juicios_relevancia_csv", rp.juicios_raiz),
                            ("sha256_resultados_ir_csv", rp.resultados_raiz)):
            if m.get(clave) != adaptadores_kit.sha256_archivo(ruta):
                det.append(f"data/mejor_modelo.json: {clave} ya no corresponde a {ruta.name}")
    return Resultado(5, titulo, FALLA if det else OK,
                     det or ["el kit reproduce la salida versionada; D08 vigente"])


def c06_entidades(cx: Contexto) -> Resultado:
    from mtx import fusion

    titulo = "entidades.csv: método, offsets, claves, extractor congelado"
    ruta = cx.raiz / "entidades.csv"
    if not ruta.exists():
        return Resultado(6, titulo, PENDIENTE, ["falta: `make extraer` (H7)"])
    ent = pd.read_csv(ruta, dtype={"passage_id": str, "query_id": str},
                      keep_default_na=False)
    det = fusion.validar_entidades(ent, dict(zip(cx.pasajes()["passage_id"],
                                                 cx.pasajes()["texto"])))
    salida = cx.rp.dir_salida / "entidades.csv"
    if not salida.exists() or salida.read_bytes() != ruta.read_bytes():
        det.append("entidades.csv de la raíz no es copia de salida/entidades.csv")
    resumen = cx.rp.dir_salida / "08_resumen_extraccion.json"
    if resumen.exists():
        r = json.loads(resumen.read_text(encoding="utf-8"))
        if not r.get("reglas_congeladas_vigentes"):
            det.append("la extracción se corrió con reglas distintas de `reglas-congeladas`")
    else:
        det.append("falta salida/08_resumen_extraccion.json")
    return Resultado(6, titulo, FALLA if det else OK,
                     det or [f"{len(ent)} filas; contrato de 8 columnas y offsets en verde"])


def c07_gold(cx: Contexto) -> Resultado:
    from mtx import gold

    titulo = "gold_entidades.csv: 20 IDs, cerrados, offsets, cierre vigente"
    rg = gold.RutasGold(cx.rp.app.anotaciones)
    if not rg.cierre.exists():
        return Resultado(7, titulo, PENDIENTE, ["falta cerrar el gold en la pestaña Gold (H6)"])
    pas = pd.read_parquet(cx.rp.app.pasajes, columns=["passage_id", "texto", "texto_sha256"])
    v = gold.validar_gold(rg, pas)
    det = list(v.errores)
    raiz = cx.raiz / "gold_entidades.csv"
    if not raiz.exists() or raiz.read_bytes() != rg.gold.read_bytes():
        det.append("gold_entidades.csv de la raíz no es la exportación del gold cerrado")
    return Resultado(7, titulo, FALLA if det else OK,
                     det or ["validar_gold() en verde; etiqueta antes del gold"])


def c08_resultados_ie(cx: Contexto) -> Resultado:
    titulo = "resultados_ie.csv reproducible; evaluación de 20 IDs"
    ruta = cx.raiz / "resultados_ie.csv"
    comp = cx.rp.dir_salida / "09_evaluacion_20_ids.csv"
    if not ruta.exists():
        return Resultado(8, titulo, PENDIENTE, ["falta: `make evaluar-ie` (H7)"])
    det = []
    gold_raiz, ent = cx.raiz / "gold_entidades.csv", cx.raiz / "entidades.csv"
    if not (gold_raiz.exists() and ent.exists()):
        return Resultado(8, titulo, FALLA, ["hay resultados_ie.csv sin gold o sin entidades"])
    with tempfile.TemporaryDirectory() as tmp:
        nuevo = adaptadores_kit.ejecutar_evaluador("ie", gold_raiz, ent, Path(tmp))
        if nuevo.read_bytes() != ruta.read_bytes():
            det.append("El kit no reproduce resultados_ie.csv: corre `make evaluar-ie`")
    res = pd.read_csv(ruta)
    if list(res.columns) != COLUMNAS_RESULTADOS_IE:
        det.append(f"columnas de resultados_ie.csv: {list(res.columns)}")
    faltan = [m for m in ("regla", "modelo", "combinado")
              if not ((res["metodo"] == m) & (res["tipo"] == "TODOS")).any()]
    if faltan:
        det.append(f"faltan filas TODOS de {faltan}")
    if not comp.exists():
        det.append("falta salida/09_evaluacion_20_ids.csv")
    return Resultado(8, titulo, FALLA if det else OK,
                     det or ["el kit reproduce la salida versionada; complementaria presente"])


def c09_respuestas(cx: Contexto) -> Resultado:
    from mtx import respuestas

    titulo = "respuestas.csv, diez tablas y valoraciones del alumno"
    sal = cx.rp.dir_salida
    ruta, hashes = sal / "respuestas.csv", sal / "10_hashes_tablas.json"
    if not ruta.exists() or not hashes.exists():
        return Resultado(9, titulo, PENDIENTE, ["falta: `make tablas` (H8)"])
    res = pd.read_csv(ruta, dtype={"passage_id": str}, keep_default_na=False)
    det = respuestas.validar_respuestas(res, dict(zip(cx.pasajes()["passage_id"],
                                                      cx.pasajes()["texto"])))
    faltan = [q for q in (f"Q{i}" for i in range(1, 11))
              if not (sal / "tablas_respuesta" / f"{q}.md").exists()]
    if faltan:
        det.append(f"faltan tablas {faltan}")
    if det:
        return Resultado(9, titulo, FALLA, det)
    pend = respuestas.validar_valoraciones(cx.rp.app.anotaciones / "valoraciones.yaml",
                                           json.loads(hashes.read_text(encoding="utf-8")))
    if pend:
        return Resultado(9, titulo, PENDIENTE,
                         [(f"contrato en verde; valoraciones del alumno: {len(pend)} pendientes "
                          "(pestaña Valoraciones)")])
    return Resultado(9, titulo, OK, ["contrato en verde; 10 valoraciones vigentes"])


def c10_corpus(cx: Contexto) -> Resultado:
    meta = json.loads(config.CORPUS_META.read_text(encoding="utf-8"))
    cache = adaptadores_kit.DIR_KIT / "data" / "discursos.parquet"
    titulo = "Hash del corpus igual a data/corpus_meta.json (aviso)"
    if not cache.exists():
        return Resultado(10, titulo, AVISO, ["no hay kit/data/discursos.parquet: `make corpus`"])
    if adaptadores_kit.sha256_archivo(cache) != meta["sha256_parquet"]:
        return Resultado(10, titulo, AVISO, [("el snapshot descargado difiere del registrado; "
                                             "ver docs/reproducibilidad.md")])
    return Resultado(10, titulo, OK, ["snapshot idéntico al registrado"])


def c11_reporte(cx: Contexto) -> Resultado:
    pdf, md = cx.raiz / "reporte" / "reporte.pdf", cx.raiz / "reporte" / "reporte.md"
    titulo = "reporte.pdf de 4 a 6 páginas, sin código, estilo sin hallazgos"
    if not pdf.exists() or not md.exists():
        return Resultado(11, titulo, PENDIENTE, ["falta reporte/reporte.md o .pdf (H9)"])
    from pypdf import PdfReader
    det = []
    paginas = len(PdfReader(pdf).pages)
    if not 4 <= paginas <= 6:
        det.append(f"{paginas} páginas")
    if "```" in md.read_text(encoding="utf-8"):
        det.append("reporte.md contiene bloques de código")
    lint = cx.raiz / "scripts" / "lint_estilo.py"
    if lint.exists():
        p = subprocess.run([sys.executable, str(lint), str(md)], capture_output=True, text=True,
                           check=False)
        if p.returncode != 0:
            det.append("lint_estilo.py con hallazgos")
    return Resultado(11, titulo, FALLA if det else OK, det or [f"{paginas} páginas"])


RE_TIEMPO = re.compile(r"tiempo medido:\s*(\d+):(\d{2})", re.IGNORECASE)


def c12_laminas(cx: Contexto) -> Resultado:
    pptx, guion = cx.raiz / "laminas" / "laminas.pptx", cx.raiz / "laminas" / "guion.md"
    titulo = "1 a 5 láminas; guion con tiempo medido de 8 minutos o menos"
    if not pptx.exists() or not guion.exists():
        return Resultado(12, titulo, PENDIENTE, ["faltan laminas/laminas.pptx o guion.md (H9)"])
    from pptx import Presentation
    det = []
    n = len(Presentation(str(pptx)).slides)
    if not 1 <= n <= 5:
        det.append(f"{n} láminas")
    m = RE_TIEMPO.search(guion.read_text(encoding="utf-8"))
    if not m:
        det.append("el guion no registra «Tiempo medido: m:ss»")
    elif int(m.group(1)) * 60 + int(m.group(2)) > 480:
        det.append(f"tiempo medido {m.group(1)}:{m.group(2)} > 8:00")
    return Resultado(12, titulo, FALLA if det else OK, det or [f"{n} láminas"])


def c13_pruebas(cx: Contexto) -> Resultado:
    titulo = "pytest en verde; make resultados desde clon limpio"
    det, estado = [], OK
    if cx.correr_pruebas:
        p = subprocess.run(["uv", "run", "pytest", "-q"], cwd=cx.raiz, capture_output=True,
                           text=True, check=False)
        ultima = (p.stdout.strip().splitlines() or ["sin salida"])[-1]
        if p.returncode != 0:
            return Resultado(13, titulo, FALLA, [f"pytest: {ultima}"])
        det.append(f"pytest: {ultima}")
    else:
        det.append("pruebas omitidas (--sin-pruebas)")
        estado = PENDIENTE
    repro = cx.raiz / "docs" / "reproducibilidad.md"
    if not repro.exists() or "clon limpio" not in repro.read_text(encoding="utf-8"):
        det.append("falta registrar la reconstrucción desde clon limpio en "
                   "docs/reproducibilidad.md (H9)")
        estado = PENDIENTE
    return Resultado(13, titulo, estado, det)


def c14_readme(cx: Contexto) -> Resultado:
    titulo = "README de 10 secciones con Uso de IA; requirements.txt coherente con uv.lock"
    det, pend = [], []
    secciones = re.findall(r"^## (.+)$", (cx.raiz / "README.md").read_text(encoding="utf-8"),
                           re.MULTILINE)
    if len(secciones) < 10 or not any("Uso de IA" in s for s in secciones):
        pend.append(f"README con {len(secciones)} secciones; se reescribe con las 10 de PRD "
                    "§11.2 en H9")
    req = cx.raiz / "requirements.txt"
    if not req.exists():
        pend.append("falta requirements.txt: `uv export --no-dev --format requirements-txt "
                    "> requirements.txt`")
    else:
        p = subprocess.run(["uv", "export", "--no-dev", "--format", "requirements-txt",
                            "--frozen"], cwd=cx.raiz, capture_output=True, text=True,
                           check=False)
        if p.returncode != 0 or p.stdout != req.read_text(encoding="utf-8"):
            det.append("requirements.txt no coincide con `uv export` de uv.lock")
    estado = FALLA if det else (PENDIENTE if pend else OK)
    return Resultado(14, titulo, estado, det + pend or ["README y requirements.txt vigentes"])


def c15_version(cx: Contexto) -> Resultado:
    titulo = "Etiqueta v1.0-entrega, acceso del profesor y hora registrada"
    p = subprocess.run(["git", "tag", "--list", "v1.0-entrega"], cwd=cx.raiz,
                       capture_output=True, text=True, check=False)
    if "v1.0-entrega" not in p.stdout:
        return Resultado(15, titulo, PENDIENTE, ["sin etiqueta v1.0-entrega (H9)"])
    dec = (cx.raiz / "docs" / "decisiones.md").read_text(encoding="utf-8")
    if "v1.0-entrega" not in dec:
        return Resultado(15, titulo, FALLA, [("la hora de la entrega no está en "
                                             "docs/decisiones.md")])
    return Resultado(15, titulo, OK, ["etiqueta presente y registrada"])


CONDICIONES: list[Callable[[Contexto], Resultado]] = [
    c01_kit_y_consultas, c02_seis_csv, c03_ranking, c04_juicios, c05_resultados_ir,
    c06_entidades, c07_gold, c08_resultados_ie, c09_respuestas, c10_corpus, c11_reporte,
    c12_laminas, c13_pruebas, c14_readme, c15_version,
]


def validar(cx: Contexto, solo: set[int] | None = None) -> list[Resultado]:
    """Corre las condiciones en orden; una excepción se reporta como FALLA de esa condición.
    La 4 va antes que la 2 para que la exportación de juicios cuente en la comprobación de copias."""
    orden = [3, 0, 1, 2, *range(4, len(CONDICIONES))]
    out = {}
    for i in orden:
        f = CONDICIONES[i]
        if solo and i + 1 not in solo:
            continue
        try:
            out[i] = f(cx)
        except Exception as e:  # noqa: BLE001  una condición rota no oculta las demás
            out[i] = Resultado(i + 1, f.__name__, FALLA, [f"{type(e).__name__}: {e}"])
    return [out[i] for i in sorted(out)]


def codigo_salida(resultados: list[Resultado], parcial: bool) -> int:
    bloquean = {FALLA} if parcial else {FALLA, PENDIENTE}
    return 1 if any(r.estado in bloquean for r in resultados) else 0
