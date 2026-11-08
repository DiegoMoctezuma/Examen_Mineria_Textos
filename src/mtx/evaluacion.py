"""Evaluación de IR (PRD §3.4, §6.6, D08). La parte IE se agrega en H7.

Cifra oficial: `kit/evaluar.py ir juicios_relevancia.csv ranking.csv`, sin tocar su salida. Lo
demás es complementario y nunca sustituye a `resultados_ir.csv`:

- vista con ventana: `relevante_ventana = relevante AND en_ventana` (fecha desconocida no cumple);
  cambian el criterio y el denominador de AP;
- tablas por consulta en formato ancho y ganador por consulta con etiquetas calculadas;
- mejor modelo (D08): argmax del MAP oficial entre las dos variantes con filtro; empate exacto a
  `bm25_con_filtro`.

Este módulo solo lee los juicios humanos: nunca los escribe, completa ni corrige. La exportación a
la raíz es una copia byte a byte que se hace únicamente si `validar_juicios()` pasa.
"""
from __future__ import annotations

import io
import json
import statistics
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import regex

from mtx import adaptadores_kit, config, pool
from mtx import indice as mod_indice
from mtx.app import componentes
from mtx.preproceso import tokenizar
from mtx.ranking import MODELOS_OFICIALES, validar_ranking

COLUMNAS_RESULTADOS_IR = ["query_id", "modelo", "P@5", "P@10", "AP", "relevantes_recuperados",
                          "relevantes_en_pool", "no_juzgados"]
FILA_PROMEDIO = "PROMEDIO (MAP = AP)"
CON_FILTRO = ("tfidf_con_filtro", "bm25_con_filtro")
DF_ALTO_FRACCION = 0.05
"""Un término de consulta tiene df alto si aparece en al menos el 5 % de los pasajes (idf BM25
menor o igual a ~3.0). Fijado antes de ver resultados; ver docs/decisiones.md."""
UMBRAL_MAP_ALERTA = 0.15
"""U19: un MAP oficial del ganador menor a esto obliga a buscar un bug antes de reportar."""
ARCHIVOS_INICIO_IE = ("muestra_seleccion.csv", "muestra_gold.csv", "gold_entidades.csv")
"""Si existe alguno en anotaciones/, la IE ya empezó y `mejor_modelo.json` no puede cambiar."""


# --------------------------------------------------------------------------- rutas


@dataclass
class RutasIR:
    app: componentes.Rutas
    ranking: Path
    ranking_salida: Path
    pool_meta: Path
    indice_pkl: Path
    sinonimos: Path
    dir_salida: Path
    dir_raiz: Path
    mejor_modelo: Path
    dir_figuras: Path

    @property
    def juicios_raiz(self) -> Path:
        return self.dir_raiz / "juicios_relevancia.csv"

    @property
    def resultados_raiz(self) -> Path:
        return self.dir_raiz / "resultados_ir.csv"


def rutas_ir() -> RutasIR:
    """Rutas reales del repo; las pruebas construyen `RutasIR` con carpetas temporales."""
    return RutasIR(
        app=componentes.rutas(),
        ranking=config.RAIZ / "ranking.csv",
        ranking_salida=config.DIR_SALIDA / "ranking.csv",
        pool_meta=config.DIR_SALIDA / "04_pool_meta.json",
        indice_pkl=config.INDICE_PKL,
        sinonimos=config.DIR_CONFIG / "sinonimos_consultas.yaml",
        dir_salida=config.DIR_SALIDA,
        dir_raiz=config.RAIZ,
        mejor_modelo=config.DIR_DATA / "mejor_modelo.json",
        dir_figuras=config.RAIZ / "reporte" / "figuras",
    )


def _sha(ruta: Path) -> str:
    return adaptadores_kit.sha256_archivo(ruta)


# --------------------------------------------------------------------------- juicios


def preparar_juicios(rp: RutasIR, pasajes: pd.DataFrame | None = None,
                     exportar: bool = True) -> pool.Validacion:
    """Valida `anotaciones/juicios_relevancia.csv` y, si pasa, lo copia a la raíz.

    Además de `validar_juicios()` exige que exista el criterio, que el pool y el criterio no hayan
    cambiado desde el primer juicio y que el pool corresponda al `ranking.csv` actual.
    """
    r = rp.app
    previos: list[str] = []
    if not r.criterios.exists():
        previos.append(f"Falta {r.criterios.name}: lo escribe el alumno antes del primer juicio")
    if not r.pool.exists():
        v = pool.Validacion(errores=previos + ["Falta salida/04_pool.csv: corre `make pool`"])
        return v
    previos += componentes.cambios_en_insumos(r)
    if rp.pool_meta.exists() and rp.ranking.exists():
        meta = json.loads(rp.pool_meta.read_text(encoding="utf-8"))
        if meta.get("sha256_ranking_csv") not in (None, _sha(rp.ranking)):
            previos.append("El pool se construyó con otro ranking.csv: ver skill "
                           "integridad-congelacion antes de seguir")
    v = pool.validar_juicios(r.juicios, pool.leer_pool(r.pool), pasajes)
    v.errores[:0] = previos
    if v.ok and exportar:
        destino = rp.juicios_raiz
        if not destino.exists() or destino.read_bytes() != r.juicios.read_bytes():
            pool.exportar_juicios(r.juicios, destino, v)
    return v


def juicios_con_ventana(juicios: pd.DataFrame, pool_csv: pd.DataFrame) -> pd.DataFrame:
    """Vista complementaria. `relevante` (la columna que lee el kit) = `relevante_ventana`."""
    p = pool_csv[["query_id", "passage_id", "fecha", "en_ventana"]]
    j = juicios[["query_id", "doc_id", "passage_id", "relevante"]].merge(
        p, on=["query_id", "passage_id"], how="left", validate="one_to_one")
    if j["en_ventana"].isna().any():
        raise ValueError("Hay juicios fuera del pool: valida los juicios antes")
    tem = j["relevante"].astype(int)
    ven = j["en_ventana"].astype(int)
    return pd.DataFrame({
        "query_id": j["query_id"], "doc_id": j["doc_id"], "passage_id": j["passage_id"],
        "fecha": j["fecha"], "en_ventana": ven, "relevante_tematico": tem,
        "relevante_ventana": tem & ven, "relevante": tem & ven,
    })


def relevantes_por_ventana(jv: pd.DataFrame, orden: list[str]) -> pd.DataFrame:
    """Por consulta: relevantes temáticos dentro y fuera de la ventana y con fecha desconocida."""
    filas = []
    for q in orden:
        g = jv[(jv["query_id"] == q) & (jv["relevante_tematico"] == 1)]
        sin_fecha = g["fecha"] == ""
        filas.append({"query_id": q, "relevantes_tematicos": len(g),
                      "dentro_de_ventana": int(g["en_ventana"].sum()),
                      "fuera_de_ventana": int(((g["en_ventana"] == 0) & ~sin_fecha).sum()),
                      "fecha_desconocida": int(sin_fecha.sum())})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- resultados


def leer_resultados(fuente: Path | bytes) -> pd.DataFrame:
    if isinstance(fuente, bytes):
        fuente = io.BytesIO(fuente)
    return pd.read_csv(fuente, keep_default_na=False, na_values=[""])


def validar_resultados_ir(res: pd.DataFrame, cons: pd.DataFrame) -> list[str]:
    """Criterios de aceptación de PRD §6.6 sobre la salida del kit (lista vacía si cumple)."""
    if list(res.columns) != COLUMNAS_RESULTADOS_IR:
        return [f"Columnas {list(res.columns)}; el kit produce {COLUMNAS_RESULTADOS_IR}"]
    problemas = []
    por_q = res[res["query_id"] != FILA_PROMEDIO]
    prom = res[res["query_id"] == FILA_PROMEDIO]
    esperadas = {(q, m) for q in cons["query_id"] for m in MODELOS_OFICIALES}
    if set(zip(por_q["query_id"], por_q["modelo"])) != esperadas or len(por_q) != len(esperadas):
        problemas.append(f"Se esperaban {len(esperadas)} filas consulta × variante; hay "
                         f"{len(por_q)}")
    if sorted(prom["modelo"]) != sorted(MODELOS_OFICIALES):
        problemas.append(f"Se esperaban 4 filas {FILA_PROMEDIO!r}; hay {len(prom)}")
    nj = por_q[por_q["no_juzgados"] > 0]
    if len(nj):
        problemas.append("Hay pasajes del top-10 sin juicio (el pool no cubre el ranking): "
                         + ", ".join(f"{r.query_id} {r.modelo}: {int(r.no_juzgados)}"
                                     for r in nj.itertuples(index=False)))
    return problemas


def map_por_modelo(res: pd.DataFrame) -> dict[str, float]:
    prom = res[res["query_id"] == FILA_PROMEDIO]
    return dict(zip(prom["modelo"], prom["AP"].astype(float)))


def _orden_q(qids) -> list[str]:
    return sorted(set(qids), key=lambda q: int(q[1:]))


def por_consulta_ancho(res: pd.DataFrame, ranking: pd.DataFrame) -> pd.DataFrame:
    """Consulta × variante: P@5, P@10, AP, soporte (relevantes del pool), juzgados, no juzgados."""
    r = res[res["query_id"] != FILA_PROMEDIO].copy()
    n = ranking.groupby(["query_id", "modelo"]).size().rename("recuperados").reset_index()
    r = r.merge(n, on=["query_id", "modelo"], how="left")
    r["soporte"] = r["relevantes_en_pool"].astype(int)
    r["no_juzgados"] = r["no_juzgados"].astype(int)
    r["juzgados"] = r["recuperados"] - r["no_juzgados"]
    metricas = ["P@5", "P@10", "AP", "soporte", "juzgados", "no_juzgados"]
    filas = []
    for q in _orden_q(r["query_id"]):
        fila = {"query_id": q}
        g = r[r["query_id"] == q].set_index("modelo")
        for m in MODELOS_OFICIALES:
            for c in metricas:
                fila[f"{m}_{c}"] = g.at[m, c]
        filas.append(fila)
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- etiquetas


RE_SIGLA = regex.compile(r"\b\p{Lu}{2,}(?:-\d+)?\b")
RE_PALABRA = regex.compile(r"\b\p{L}+\b")


def etiquetas_consultas(cons: pd.DataFrame, df: dict[str, int], n_pasajes: int,
                        sinonimos: dict[str, list[str]]) -> pd.DataFrame:
    """Etiquetas calculadas (PRD §6.6 punto 3); ninguna se asigna a mano."""
    toks = {q: tokenizar(c) for q, c in zip(cons["query_id"], cons["consulta"])}
    mediana = statistics.median(len(t) for t in toks.values())
    filas = []
    for q, consulta in zip(cons["query_id"], cons["consulta"]):
        t = toks[q]
        altos = [x for x in dict.fromkeys(t) if df.get(x, 0) / n_pasajes >= DF_ALTO_FRACCION]
        siglas = RE_SIGLA.findall(consulta)
        palabras = [m.group() for m in RE_PALABRA.finditer(consulta)]
        propios = [w for i, w in enumerate(palabras)
                   if i > 0 and w[0].isupper() and not w.isupper()]
        grupos, ausentes = [], []
        for nombre, formas in sinonimos.items():
            presentes = [f for f in formas if set(tokenizar(f)) <= set(t)]
            if presentes:
                grupos.append(nombre)
                ausentes += [f for f in formas if f not in presentes]
        filas.append({
            "query_id": q, "tokens": " ".join(t), "n_tokens": len(t),
            "longitud": "larga" if len(t) > mediana else "corta",
            "n_terminos_df_alto": len(altos), "terminos_df_alto": " ".join(altos),
            "tiene_sigla": int(bool(siglas)), "tiene_nombre_propio": int(bool(propios)),
            "siglas_y_nombres": " | ".join(siglas + propios),
            "grupo_sinonimos": " | ".join(grupos), "sinonimos_ausentes_en_consulta":
                " | ".join(ausentes),
        })
    return pd.DataFrame(filas)


def ganador_por_consulta(res: pd.DataFrame, etiquetas: pd.DataFrame) -> pd.DataFrame:
    """Ganador por AP entre las variantes con filtro; `diferencia` = AP BM25 − AP TF-IDF."""
    r = res[res["query_id"] != FILA_PROMEDIO]
    ap = r.pivot(index="query_id", columns="modelo", values="AP").astype(float)
    filas = []
    for q in _orden_q(ap.index):
        t, b = ap.at[q, "tfidf_con_filtro"], ap.at[q, "bm25_con_filtro"]
        ganador = "empate" if t == b else ("bm25_con_filtro" if b > t else "tfidf_con_filtro")
        filas.append({"query_id": q, "ganador_con_filtro": ganador,
                      "AP_tfidf_con_filtro": t, "AP_bm25_con_filtro": b,
                      "diferencia_bm25_menos_tfidf": round(b - t, 4),
                      "AP_tfidf_sin_filtro": ap.at[q, "tfidf_sin_filtro"],
                      "AP_bm25_sin_filtro": ap.at[q, "bm25_sin_filtro"]})
    return pd.DataFrame(filas).merge(etiquetas, on="query_id", how="left")


# --------------------------------------------------------------------------- mejor modelo


def elegir_mejor_modelo(res: pd.DataFrame) -> dict:
    """D08: argmax del MAP oficial entre las variantes con filtro; empate exacto a BM25."""
    maps = map_por_modelo(res)
    t, b = maps["tfidf_con_filtro"], maps["bm25_con_filtro"]
    modelo, alt = ("tfidf_con_filtro", "bm25_con_filtro") if t > b else CON_FILTRO[::-1]
    dif = round(abs(b - t), 4)
    return {"modelo": modelo, "MAP": maps[modelo], "alternativa": alt,
            "MAP_alternativa": maps[alt], "diferencia": dif, "empate": t == b,
            "diferencia_menor_0.01": dif < 0.01,
            "regla": "D08: argmax del MAP oficial (resultados_ir.csv, filas PROMEDIO) entre "
                     "tfidf_con_filtro y bm25_con_filtro; empate exacto → bm25_con_filtro; "
                     "único para las diez consultas"}


def ie_iniciada(dir_anotaciones: Path) -> list[str]:
    return [n for n in ARCHIVOS_INICIO_IE if (Path(dir_anotaciones) / n).exists()]


# --------------------------------------------------------------------------- figuras

COLOR = {"tfidf": "#2a78d6", "bm25": "#eb6834"}
NOMBRE = {"tfidf_con_filtro": "TF-IDF con filtro", "tfidf_sin_filtro": "TF-IDF sin filtro",
          "bm25_con_filtro": "BM25 con filtro", "bm25_sin_filtro": "BM25 sin filtro"}
ORDEN_FIG = ["tfidf_con_filtro", "tfidf_sin_filtro", "bm25_con_filtro", "bm25_sin_filtro"]


def _estilo(fig, titulo: str, alto: int = 420):
    fig.update_layout(
        title={"text": titulo, "x": 0.01, "xref": "container", "xanchor": "left",
               "font": {"size": 16}},
        template="simple_white", font={"family": "Helvetica, Arial, sans-serif", "size": 13,
                                       "color": "#0b0b0b"},
        width=900, height=alto, bargap=0.28, bargroupgap=0.08,
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0, "title": None},
        margin={"l": 60, "r": 20, "t": 90, "b": 50}, paper_bgcolor="white", plot_bgcolor="white")
    fig.update_yaxes(range=[0, 1.05], gridcolor="#e8e7e3", showgrid=True, zeroline=False,
                     linecolor="#b5b4ae", tickfont={"color": "#52514e"})
    fig.update_xaxes(linecolor="#b5b4ae", tickfont={"color": "#52514e"})
    return fig


def _barra(go, modelo: str, x, y, texto: bool):
    fam = modelo.split("_")[0]
    return go.Bar(name=NOMBRE[modelo], x=x, y=y, marker_color=COLOR[fam],
                  marker_line_color="white", marker_line_width=2,
                  marker_pattern_shape="/" if modelo.endswith("sin_filtro") else "",
                  marker_pattern_fgcolor="white", marker_pattern_solidity=0.35,
                  text=[f"{v:.3f}" for v in y] if texto else None, textposition="outside",
                  textfont={"color": "#0b0b0b", "size": 11}, cliponaxis=False)


def figuras_ir(res: pd.DataFrame, res_ventana: pd.DataFrame, dir_figuras: Path) -> list[Path]:
    """Tres PNG sobrios con una sola paleta (TF-IDF azul, BM25 naranja; sin filtro rayado)."""
    import plotly.graph_objects as go

    dir_figuras.mkdir(parents=True, exist_ok=True)
    prom = res[res["query_id"] == FILA_PROMEDIO].set_index("modelo")
    rutas = []

    fig = go.Figure([_barra(go, m, ["MAP", "P@5", "P@10"],
                            [float(prom.at[m, c]) for c in ("AP", "P@5", "P@10")], True)
                     for m in ORDEN_FIG])
    fig.update_layout(barmode="group")
    _estilo(fig, "Promedio de las diez consultas por variante (vista oficial, AP sobre top-10)")
    fig.update_yaxes(title="Valor promedio")
    rutas.append(dir_figuras / "ir_map_por_modelo.png")
    fig.write_image(rutas[-1], scale=2)

    r = res[res["query_id"] != FILA_PROMEDIO]
    qs = _orden_q(r["query_id"])
    ap = r.pivot(index="query_id", columns="modelo", values="AP").astype(float)
    fig = go.Figure([_barra(go, m, qs, [ap.at[q, m] for q in qs], False) for m in CON_FILTRO])
    fig.update_layout(barmode="group")
    _estilo(fig, "AP por consulta en las variantes con filtro (vista oficial)")
    fig.update_yaxes(title="AP")
    rutas.append(dir_figuras / "ir_ap_por_consulta.png")
    fig.write_image(rutas[-1], scale=2)

    vistas = ["Vista oficial (relevancia temática)", "Vista con ventana (complementaria)"]
    m_of, m_ve = map_por_modelo(res), map_por_modelo(res_ventana)
    fig = go.Figure([_barra(go, m, vistas, [m_of[m], m_ve[m]], True) for m in ORDEN_FIG])
    fig.update_layout(barmode="group")
    _estilo(fig, "MAP con y sin filtro de fecha en las dos vistas")
    fig.update_yaxes(title="MAP")
    rutas.append(dir_figuras / "ir_con_vs_sin_filtro.png")
    fig.write_image(rutas[-1], scale=2)
    return rutas


# --------------------------------------------------------------------------- orquestación


@dataclass
class InformeIR:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    escritos: list[Path] = field(default_factory=list)
    mejor: dict | None = None

    @property
    def ok(self) -> bool:
        return not self.errores


def _evaluar_en_temporal(referencia: Path, ranking: Path) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        return adaptadores_kit.ejecutar_evaluador("ir", referencia, ranking, Path(tmp)).read_bytes()


def ejecutar_ir(rp: RutasIR | None = None, pasajes: pd.DataFrame | None = None,
                figuras: bool = True) -> InformeIR:
    """Todo H4. No escribe nada si los juicios o el ranking no son válidos."""
    rp = rp or rutas_ir()
    inf = InformeIR()
    cons = pd.read_csv(rp.app.consultas, dtype=str, keep_default_na=False)

    if not rp.ranking.exists():
        inf.errores.append("Falta ranking.csv en la raíz: corre `make ranking`")
        return inf
    if rp.ranking_salida.exists() and rp.ranking_salida.read_bytes() != rp.ranking.read_bytes():
        inf.errores.append("ranking.csv de la raíz no es copia de salida/ranking.csv")
    ranking = pd.read_csv(rp.ranking, dtype=str, keep_default_na=False)
    inf.errores += [f"ranking.csv: {p}" for p in validar_ranking(ranking, cons)]
    if pasajes is None:
        pasajes = pd.read_parquet(rp.app.pasajes, columns=["passage_id", "texto"])
    v = preparar_juicios(rp, pasajes)
    inf.errores += v.errores
    inf.avisos += v.avisos
    if not inf.ok:
        return inf

    # 1. Cifra oficial, íntegra.
    oficial = _evaluar_en_temporal(rp.juicios_raiz, rp.ranking)
    res = leer_resultados(oficial)
    problemas = validar_resultados_ir(res, cons)
    if problemas:
        inf.errores += [f"resultados_ir.csv: {p}" for p in problemas]
        return inf
    rp.dir_salida.mkdir(parents=True, exist_ok=True)
    for destino in (rp.dir_salida / "resultados_ir.csv", rp.resultados_raiz):
        destino.write_bytes(oficial)
        inf.escritos.append(destino)

    # 2. Vista con ventana (complementaria).
    juicios = pd.read_csv(rp.juicios_raiz, dtype=str, keep_default_na=False)
    pool_csv = pool.leer_pool(rp.app.pool)
    jv = juicios_con_ventana(juicios, pool_csv)
    ruta_jv = rp.dir_salida / "05_juicios_con_ventana.csv"
    jv.to_csv(ruta_jv, index=False)
    ruta_rv = rp.dir_salida / "05_resultados_ir_ventana.csv"
    ruta_rv.write_bytes(_evaluar_en_temporal(ruta_jv, rp.ranking))
    res_v = leer_resultados(ruta_rv)
    orden = _orden_q(cons["query_id"])
    ruta_rel = rp.dir_salida / "05_relevantes_por_ventana.csv"
    relevantes_por_ventana(jv, orden).to_csv(ruta_rel, index=False)
    inf.escritos += [ruta_jv, ruta_rv, ruta_rel]

    # 3. Tablas por consulta y ganador con etiquetas.
    ruta_ancho = rp.dir_salida / "05_ir_por_consulta.csv"
    por_consulta_ancho(res, ranking).to_csv(ruta_ancho, index=False)
    ind = mod_indice.cargar(rp.indice_pkl)
    sin = config.cargar_yaml(rp.sinonimos.name, rp.sinonimos.parent)["grupos"]
    ruta_gan = rp.dir_salida / "05_ir_ganador_por_consulta.csv"
    ganador_por_consulta(res, etiquetas_consultas(cons, ind.df, ind.N, sin)).to_csv(
        ruta_gan, index=False)
    inf.escritos += [ruta_ancho, ruta_gan]

    # 4. Mejor modelo (D08), fijo una vez que empieza la IE.
    mejor = elegir_mejor_modelo(res) | {
        "sha256_ranking_csv": _sha(rp.ranking),
        "sha256_juicios_relevancia_csv": _sha(rp.juicios_raiz),
        "sha256_resultados_ir_csv": _sha(rp.resultados_raiz)}
    contenido = json.dumps(mejor, ensure_ascii=False, indent=2) + "\n"
    previo = rp.mejor_modelo.read_text(encoding="utf-8") if rp.mejor_modelo.exists() else None
    if previo is not None and previo != contenido:
        iniciada = ie_iniciada(rp.app.anotaciones)
        if iniciada:
            inf.errores.append(f"data/mejor_modelo.json cambiaría y la IE ya empezó ({iniciada}):"
                               " no se sobrescribe; ver skill integridad-congelacion")
            return inf
        inf.avisos.append("data/mejor_modelo.json cambió (rankings o juicios distintos); "
                          "se regenera porque la IE aún no empieza")
    if previo != contenido:
        rp.mejor_modelo.parent.mkdir(parents=True, exist_ok=True)
        rp.mejor_modelo.write_text(contenido, encoding="utf-8")
    inf.escritos.append(rp.mejor_modelo)
    inf.mejor = mejor
    if mejor["MAP"] < UMBRAL_MAP_ALERTA:
        inf.avisos.append(f"U19: MAP oficial del ganador {mejor['MAP']:.4f} < "
                          f"{UMBRAL_MAP_ALERTA}: busca un bug (tokens de consulta, pool) antes de "
                          "reportar")
    if mejor["diferencia_menor_0.01"]:
        inf.avisos.append("La diferencia de MAP entre TF-IDF y BM25 con filtro es menor a 0.01: "
                          "se comenta en el reporte; la regla D08 no cambia")

    # 5. Figuras.
    if figuras:
        try:
            inf.escritos += figuras_ir(res, res_v, rp.dir_figuras)
        except Exception as e:  # noqa: BLE001  kaleido sin Chrome no debe tumbar las cifras
            inf.avisos.append(f"No se exportaron las figuras PNG ({type(e).__name__}: {e}); "
                              "corre `make setup` para instalar Chrome de kaleido")

    # 6. Registro de ejecución.
    registro = {
        "ejecutado": datetime.now().isoformat(timespec="seconds"),
        "comando_oficial": "python kit/evaluar.py ir juicios_relevancia.csv ranking.csv",
        "comando_ventana": "python kit/evaluar.py ir salida/05_juicios_con_ventana.csv "
                           "ranking.csv  (lee la columna `relevante` = relevante_ventana)",
        "horizonte": "P@5, P@10 y AP sobre el top-10; AP divide entre los relevantes del pool "
                     "de la consulta (kit); un pasaje no juzgado cuenta como no relevante",
        "sha256": {"kit/evaluar.py": _sha(adaptadores_kit.DIR_KIT / "evaluar.py"),
                   "juicios_relevancia.csv": _sha(rp.juicios_raiz),
                   "ranking.csv": _sha(rp.ranking), "resultados_ir.csv": _sha(rp.resultados_raiz),
                   "salida/04_pool.csv": _sha(rp.app.pool),
                   "salida/05_juicios_con_ventana.csv": _sha(ruta_jv),
                   "salida/05_resultados_ir_ventana.csv": _sha(ruta_rv)},
        "juicios": {"pares": v.juzgados,
                    "relevantes": int((juicios["relevante"] == "1").sum())},
        "map_oficial": map_por_modelo(res), "map_ventana_complementaria": map_por_modelo(res_v),
        "mejor_modelo": mejor["modelo"], "avisos": inf.avisos,
    }
    ruta_reg = rp.dir_salida / "05_registro_evaluacion.json"
    ruta_reg.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    inf.escritos.append(ruta_reg)
    return inf

