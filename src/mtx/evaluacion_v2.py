"""Evaluación IR v2 (PRD v2 D28, D29; WP-06). Lo oficial es el kit sobre los juicios agregados.

- **Insumos:** `salida/v2/juicios_relevancia.csv` (WP-02, mayoría de 3) y
  `salida/v2/ranking_8_variantes.csv` (WP-03, 8 variantes × 15 consultas). Solo corre después del
  cierre de juicios y con los juicios que registró la agregación (sha256 en `05a_acuerdo.json`).
- **Cifra oficial:** `kit/evaluar.py ir` sobre las 8 variantes → `salida/v2/05_ir_8_variantes.csv`.
- **Ganador (D28):** mayor MAP del kit entre las 4 variantes con filtro (stem y lema × TF-IDF y
  BM25); empate a 4 decimales → `bm25_con_filtro`, el ganador de v1.
- **`ranking.csv` v2:** las 4 variantes del preprocesamiento ganador con los nombres de v1, en
  `salida/v2/ranking.csv`, y su `resultados_ir.csv` del kit. La raíz conserva los archivos v1
  hasta la entrega (WP-14 los promueve), para que v1 siga reproducible.

Los complementos de D29 (bootstrap, permutación, sensibilidad, inflación, nDCG) están abajo y no
sustituyen la cifra oficial.
"""
from __future__ import annotations

import json
import math
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from mtx import adaptadores_kit, config
from mtx import consultas as consultas_mod
from mtx.evaluacion import COLUMNAS_RESULTADOS_IR, FILA_PROMEDIO, leer_resultados, map_por_modelo
from mtx.ranking import MODELOS_OFICIALES, MODELOS_V2, validar_ranking

CON_FILTRO_V2 = ("tfidf_con_filtro", "bm25_con_filtro", "tfidf_lema_con_filtro",
                 "bm25_lema_con_filtro")
DESEMPATE = "bm25_con_filtro"
DECIMALES_EMPATE = 4
K = 10


@dataclass
class RutasV2:
    juicios: Path
    agregados: Path
    acuerdo_json: Path
    cierre_juicios: Path
    ranking8: Path
    consultas: Path
    dir_salida: Path
    mejor_modelo: Path


def rutas_v2() -> RutasV2:
    from mtx import cierres_v2

    return RutasV2(juicios=config.DIR_SALIDA_V2 / "juicios_relevancia.csv",
                   agregados=config.DIR_SALIDA_V2 / "05a_juicios_agregados.csv",
                   acuerdo_json=config.DIR_SALIDA_V2 / "05a_acuerdo.json",
                   cierre_juicios=cierres_v2.ruta_cierre_juicios(),
                   ranking8=config.DIR_SALIDA_V2 / "ranking_8_variantes.csv",
                   consultas=config.CONSULTAS_CSV, dir_salida=config.DIR_SALIDA_V2,
                   mejor_modelo=config.DIR_DATA_V2 / "mejor_modelo.json")


@dataclass
class InformeV2:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    escritos: list[Path] = field(default_factory=list)
    mejor: dict | None = None

    @property
    def ok(self) -> bool:
        return not self.errores


def _sha(ruta: Path) -> str:
    return adaptadores_kit.sha256_archivo(ruta)


def _kit(juicios: Path, ranking: Path) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        return adaptadores_kit.ejecutar_evaluador("ir", juicios, ranking, Path(tmp)).read_bytes()


# --------------------------------------------------------------------------- validaciones


def validar_insumos(rp: RutasV2) -> list[str]:
    if not rp.cierre_juicios.exists():
        return ["No existe anotaciones/cierre_juicios_v2.json: primero `make cierre-juicios-v2`"]
    if not rp.acuerdo_json.exists() or not rp.juicios.exists():
        return ["Faltan los juicios agregados: corre `make agregar-juicios`"]
    reg = json.loads(rp.acuerdo_json.read_text("utf-8"))
    errores = []
    for ruta in (rp.juicios, rp.agregados):
        if not ruta.exists() or reg.get("sha256", {}).get(ruta.name) != _sha(ruta):
            errores.append(f"{ruta.name} no es el que escribió `make agregar-juicios`")
    if reg.get("cierre", {}).get("sha256") != _sha(rp.cierre_juicios):
        errores.append("La agregación se hizo con otro cierre de juicios")
    if not rp.ranking8.exists():
        errores.append("Falta salida/v2/ranking_8_variantes.csv: corre `make ranking-v2`")
    return errores


def validar_resultados_v2(res: pd.DataFrame, cons: pd.DataFrame,
                          modelos: tuple[str, ...] = MODELOS_V2) -> tuple[list[str], list[str]]:
    """(errores, avisos) sobre la salida del kit. Un pasaje sin juicio (par no cerrado) es aviso:
    el kit lo cuenta como no relevante."""
    if list(res.columns) != COLUMNAS_RESULTADOS_IR:
        return [f"Columnas {list(res.columns)}; el kit produce {COLUMNAS_RESULTADOS_IR}"], []
    por_q = res[res["query_id"] != FILA_PROMEDIO]
    prom = res[res["query_id"] == FILA_PROMEDIO]
    errores, avisos = [], []
    esperadas = {(q, m) for q in cons["query_id"] for m in modelos}
    if set(zip(por_q["query_id"], por_q["modelo"])) != esperadas or len(por_q) != len(esperadas):
        errores.append(f"Se esperaban {len(esperadas)} filas consulta × variante; hay {len(por_q)}")
    if sorted(prom["modelo"]) != sorted(modelos):
        errores.append(f"Se esperaban {len(modelos)} filas {FILA_PROMEDIO!r}; hay {len(prom)}")
    nj = por_q[por_q["no_juzgados"].astype(int) > 0]
    if len(nj):
        avisos.append(f"{int(nj['no_juzgados'].sum())} pasajes del top-10 sin juicio cerrado "
                      "(el kit los cuenta como no relevantes): "
                      + ", ".join(f"{r.query_id} {r.modelo}" for r in nj.head(5).itertuples()))
    return errores, avisos


# --------------------------------------------------------------------------- ganador (D28)


def elegir_ganador_v2(res: pd.DataFrame) -> dict:
    """Mayor MAP oficial entre las 4 con filtro; empate a 4 decimales → BM25 stem."""
    maps = map_por_modelo(res)
    cand = {m: maps[m] for m in CON_FILTRO_V2}
    red = {m: round(v, DECIMALES_EMPATE) for m, v in cand.items()}
    mejor = max(red.values())
    empatados = [m for m in CON_FILTRO_V2 if red[m] == mejor]
    modelo = DESEMPATE if DESEMPATE in empatados else empatados[0]
    resto = sorted((m for m in CON_FILTRO_V2 if m != modelo), key=lambda m: -cand[m])
    alt = resto[0]
    return {"modelo": modelo, "preprocesamiento": "lema" if "_lema_" in modelo else "stem",
            "modelo_en_ranking_csv": nombre_v1(modelo), "MAP": cand[modelo],
            "alternativa": alt, "MAP_alternativa": cand[alt],
            "diferencia": round(cand[modelo] - cand[alt], 4), "empate": len(empatados) > 1,
            "empatados": empatados, "map_con_filtro": cand,
            "regla": ("D28: mayor MAP oficial (kit, juicios agregados por mayoría) entre las 4 "
                      "variantes con filtro; empate a 4 decimales → bm25_con_filtro")}


def nombre_v1(modelo: str) -> str:
    return modelo.replace("_lema_", "_")


def ranking_raiz_v2(ranking8: pd.DataFrame, preprocesamiento: str) -> pd.DataFrame:
    """Las 4 variantes del preprocesamiento ganador con los nombres de v1 (D28)."""
    lema = ranking8["modelo"].str.contains("_lema_")
    sel = ranking8[lema] if preprocesamiento == "lema" else ranking8[~lema]
    out = sel.assign(modelo=sel["modelo"].map(nombre_v1))
    orden = {m: i for i, m in enumerate(MODELOS_OFICIALES)}
    q = out["query_id"].str[1:].astype(int)
    return (out.assign(_q=q, _m=out["modelo"].map(orden), _r=out["rango"].astype(int))
            .sort_values(["_q", "_m", "_r"]).drop(columns=["_q", "_m", "_r"])
            .reset_index(drop=True))


# --------------------------------------------------------------------------- tubería oficial


def ejecutar_ir_v2(rp: RutasV2 | None = None, con_robustez: bool = True) -> InformeV2:
    """No escribe nada si los insumos no son los cerrados o el kit no da lo esperado."""
    rp = rp or rutas_v2()
    inf = InformeV2()
    inf.errores += validar_insumos(rp)
    if not inf.ok:
        return inf
    cons = pd.read_csv(rp.consultas, dtype=str, keep_default_na=False)
    r8 = pd.read_csv(rp.ranking8, dtype=str, keep_default_na=False)
    inf.errores += [f"ranking_8_variantes.csv: {p}" for p in validar_ranking(r8, cons, MODELOS_V2)]
    if not inf.ok:
        return inf

    oficial8 = _kit(rp.juicios, rp.ranking8)
    res8 = leer_resultados(oficial8)
    err, av = validar_resultados_v2(res8, cons)
    inf.errores += [f"05_ir_8_variantes.csv: {e}" for e in err]
    inf.avisos += av
    if not inf.ok:
        return inf
    mejor = elegir_ganador_v2(res8)

    rp.dir_salida.mkdir(parents=True, exist_ok=True)
    ruta8 = rp.dir_salida / "05_ir_8_variantes.csv"
    ruta8.write_bytes(oficial8)
    ruta_rk = rp.dir_salida / "ranking.csv"
    ranking_raiz_v2(r8, mejor["preprocesamiento"]).to_csv(ruta_rk, index=False,
                                                         lineterminator="\n")
    ruta_res = rp.dir_salida / "resultados_ir.csv"
    oficial4 = _kit(rp.juicios, ruta_rk)
    err4, _ = validar_resultados_v2(leer_resultados(oficial4), cons, MODELOS_OFICIALES)
    if err4:
        inf.errores += [f"resultados_ir.csv v2: {e}" for e in err4]
        return inf
    ruta_res.write_bytes(oficial4)
    inf.escritos += [ruta8, ruta_rk, ruta_res]

    mejor |= {"sha256_ranking_8_variantes_csv": _sha(rp.ranking8),
              "sha256_ranking_csv_v2": _sha(ruta_rk),
              "sha256_juicios_relevancia_csv_v2": _sha(rp.juicios),
              "sha256_05_ir_8_variantes_csv": _sha(ruta8)}
    contenido = json.dumps(mejor, ensure_ascii=False, indent=2) + "\n"
    if rp.mejor_modelo.exists() and rp.mejor_modelo.read_text("utf-8") != contenido:
        inf.errores.append("data/v2/mejor_modelo.json ya existe con otro contenido y los insumos "
                           "están cerrados: no se sobrescribe (ver integridad-congelacion)")
        return inf
    rp.mejor_modelo.parent.mkdir(parents=True, exist_ok=True)
    rp.mejor_modelo.write_text(contenido, encoding="utf-8")
    inf.escritos.append(rp.mejor_modelo)
    inf.mejor = mejor

    if con_robustez:
        juicios = pd.read_csv(rp.juicios, dtype=str, keep_default_na=False)
        agr = pd.read_csv(rp.agregados, dtype=str, keep_default_na=False)
        ruta_rob = rp.dir_salida / "05_robustez.csv"
        robustez(res8, r8, juicios, agr, mejor["modelo"]).to_csv(ruta_rob, index=False,
                                                                 lineterminator="\n")
        inf.escritos.append(ruta_rob)

    registro = {
        "ejecutado": datetime.now().isoformat(timespec="seconds"),
        "comando_oficial": ("python kit/evaluar.py ir salida/v2/juicios_relevancia.csv "
                            "salida/v2/ranking_8_variantes.csv"),
        "consultas": len(cons), "map_oficial_8_variantes": map_por_modelo(res8),
        "mejor_modelo": mejor["modelo"], "avisos": inf.avisos,
        "sha256": {"kit/evaluar.py": _sha(adaptadores_kit.DIR_KIT / "evaluar.py"),
                   **{p.name: _sha(p) for p in (rp.juicios, rp.ranking8, ruta8, ruta_rk,
                                                ruta_res)}},
    }
    ruta_reg = rp.dir_salida / "05_registro_evaluacion.json"
    ruta_reg.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    inf.escritos.append(ruta_reg)
    return inf


# --------------------------------------------------------------------------- robustez (D29, P1)


def relevancias(ranking: pd.DataFrame, juicios: pd.DataFrame) -> dict[tuple[str, str], list[int]]:
    """Por (consulta, modelo): relevancia binaria del top-10 en orden; sin juicio = 0 (como el kit)."""
    rel = {(q, p): int(v) for q, p, v in zip(juicios["query_id"], juicios["passage_id"],
                                             juicios["relevante"])}
    out = {}
    for (q, m), g in ranking.sort_values(["query_id", "modelo", "rango"]).groupby(
            ["query_id", "modelo"], sort=False):
        out[(q, m)] = [rel.get((q, p), 0) for p in g["passage_id"]]
    return out


def ap(rel: list[int], total: int) -> float:
    """AP del kit: suma de precisiones en cada acierto del top-k entre los relevantes del pool."""
    if total == 0:
        return 0.0
    aciertos, s = 0, 0.0
    for i, r in enumerate(rel, 1):
        if r:
            aciertos += 1
            s += aciertos / i
    return s / total


def ndcg(rel: list[int], total: int, k: int = K) -> float:
    """nDCG@k binario; el ideal pone min(total, k) relevantes arriba."""
    dcg = sum(r / math.log2(i + 1) for i, r in enumerate(rel[:k], 1))
    ideal = sum(1 / math.log2(i + 1) for i in range(1, min(total, k) + 1))
    return dcg / ideal if ideal else 0.0


def metricas_por_consulta(ranking: pd.DataFrame, juicios: pd.DataFrame) -> pd.DataFrame:
    total = juicios[juicios["relevante"].astype(str) == "1"].groupby("query_id").size()
    filas = []
    for (q, m), rel in relevancias(ranking, juicios).items():
        t = int(total.get(q, 0))
        filas.append({"query_id": q, "modelo": m, "AP": ap(rel, t),
                      "P@10": sum(rel[:K]) / K, "nDCG@10": ndcg(rel, t)})
    return pd.DataFrame(filas)


def bootstrap_map(ap_por_consulta: pd.Series, n: int = 10_000, semilla: int = 42) -> tuple:
    """Intervalo de confianza al 95 % del MAP remuestreando consultas con reemplazo."""
    x = np.asarray(ap_por_consulta, dtype=float)
    rng = np.random.default_rng(semilla)
    medias = x[rng.integers(0, len(x), size=(n, len(x)))].mean(axis=1)
    return float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))


def permutacion_pareada(a: pd.Series, b: pd.Series, n: int = 10_000, semilla: int = 42) -> float:
    """Valor p bilateral de la diferencia de MAP intercambiando al azar el AP de cada consulta."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    obs = abs(d.mean())
    rng = np.random.default_rng(semilla)
    signos = rng.choice([-1.0, 1.0], size=(n, len(d)))
    extremos = (np.abs((signos * d).mean(axis=1)) >= obs - 1e-12).sum()
    return float((extremos + 1) / (n + 1))


def juicios_con_regla(agregados: pd.DataFrame, minimo: int) -> pd.DataFrame:
    """Juicios de sensibilidad (D29.3): relevante con al menos `minimo` votos de 3 (3 =
    unanimidad, 1 = al menos uno). Solo pares cerrados."""
    c = agregados[agregados["cerrado"].astype(str).isin(["True", "true", "1"])]
    rel = (c["votos_relevante"].astype(int) >= minimo).astype(int).astype(str)
    return c.assign(relevante=rel)[["query_id", "doc_id", "passage_id", "relevante"]]


COLUMNAS_ROBUSTEZ = ["analisis", "modelo", "comparado_con", "consultas", "valor", "ic95_inf",
                     "ic95_sup", "p_valor", "nota"]


def _kit_df(juicios: pd.DataFrame, ranking: pd.DataFrame) -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as tmp:
        rj, rr = Path(tmp) / "juicios.csv", Path(tmp) / "ranking.csv"
        juicios.to_csv(rj, index=False, lineterminator="\n")
        ranking.to_csv(rr, index=False, lineterminator="\n")
        return leer_resultados(_kit(rj, rr))


def _ap_por_consulta(res: pd.DataFrame, modelo: str) -> pd.Series:
    r = res[(res["query_id"] != FILA_PROMEDIO) & (res["modelo"] == modelo)]
    return r.set_index("query_id")["AP"].astype(float).sort_index()


def robustez(res8: pd.DataFrame, ranking8: pd.DataFrame, juicios: pd.DataFrame,
             agregados: pd.DataFrame, ganador: str, n: int = 10_000,
             semilla: int = 42) -> pd.DataFrame:
    """D29 (complementario): IC95 bootstrap del MAP de las 8, permutación pareada ganador contra
    cada rival, sensibilidad a la regla de agregación, inflación por pool en Q1 a Q10 y P@10 y
    nDCG@10. Las cifras con AP salen del kit; nDCG lo calcula este módulo."""
    filas = []

    def fila(analisis, modelo, valor, comparado="", consultas=None, inf=None, sup=None, p=None,
             nota=""):
        filas.append({"analisis": analisis, "modelo": modelo, "comparado_con": comparado,
                      "consultas": consultas, "valor": None if valor is None else round(valor, 4),
                      "ic95_inf": None if inf is None else round(inf, 4),
                      "ic95_sup": None if sup is None else round(sup, 4),
                      "p_valor": None if p is None else round(p, 4), "nota": nota})

    for m in MODELOS_V2:
        a = _ap_por_consulta(res8, m)
        lo, hi = bootstrap_map(a, n, semilla)
        fila("map_ic95_bootstrap", m, a.mean(), consultas=len(a), inf=lo, sup=hi,
             nota=f"{n} remuestreos de consultas, semilla {semilla}")
    ag = _ap_por_consulta(res8, ganador)
    for m in MODELOS_V2:
        if m != ganador:
            b = _ap_por_consulta(res8, m).reindex(ag.index)
            fila("permutacion_pareada", ganador, ag.mean() - b.mean(), comparado=m,
                 consultas=len(ag), p=permutacion_pareada(ag, b, n, semilla),
                 nota=f"diferencia de MAP; {n} permutaciones, semilla {semilla}, bilateral")
    for nombre, minimo in (("unanimidad", 3), ("al_menos_1_de_3", 1)):
        r = _kit_df(juicios_con_regla(agregados, minimo), ranking8)
        for m, v in map_por_modelo(r).items():
            fila(f"sensibilidad_{nombre}", m, v, consultas=15,
                 nota=f"relevante con al menos {minimo} de 3 votos (kit)")
    v1q = ranking8["query_id"].isin(consultas_mod.CONSULTAS_V1)
    rk_v1 = ranking8[v1q & ranking8["modelo"].isin(MODELOS_OFICIALES)]
    j_v1q = juicios[juicios["query_id"].isin(consultas_mod.CONSULTAS_V1)]
    lote1 = agregados[agregados["lote"].astype(str) == "1"][["query_id", "passage_id"]]
    j_pool_v1 = j_v1q.merge(lote1, on=["query_id", "passage_id"])
    m_pool_v1 = map_por_modelo(_kit_df(j_pool_v1, rk_v1))
    m_pool_v2 = map_por_modelo(_kit_df(j_v1q, rk_v1))
    for m in MODELOS_OFICIALES:
        fila("inflacion_pool_v1", m, m_pool_v1[m], consultas=10,
             nota="Q1 a Q10, juicios agregados solo sobre los pares del pool v1 (lote 1)")
        fila("inflacion_pool_v2", m, m_pool_v2[m], comparado="inflacion_pool_v1", consultas=10,
             nota="Q1 a Q10, juicios agregados sobre todo el pool v2; el kit divide entre "
                  "los relevantes del pool")
    met = metricas_por_consulta(ranking8, juicios)
    for m in MODELOS_V2:
        g = met[met["modelo"] == m]
        fila("p_at_10", m, g["P@10"].mean(), consultas=len(g))
        fila("ndcg_at_10", m, g["nDCG@10"].mean(), consultas=len(g),
             nota="binario, ideal con min(relevantes del pool, 10)")
    return pd.DataFrame(filas, columns=COLUMNAS_ROBUSTEZ)
