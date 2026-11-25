"""Figuras v2 para láminas y reporte (PRD v2 WP-16, `make figuras-v2`).

Lee solo archivos de `salida/` (y el índice y los pasajes para los ejemplos de tokenización y
postings) y escribe `salida/v2/figuras/*.png` y `salida/v2/figuras/figuras.json`, con la versión
de datos y el sha256 de cada fuente.

Cada bloque usa v2 en cuanto existen sus salidas (después de los cierres y `make all-v2`); antes
usa v1 y la figura lo dice en el subtítulo. Así se pueden armar las láminas hoy y regenerarlas con
v2 en la noche sin tocar nada. Nunca lee `anotaciones/` ni predicciones de la muestra v2 (D32).

    uv run python scripts/11b_figuras_v2.py [--solo ap,map]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

from mtx import config
from mtx import evaluacion_v2 as E
from mtx import figuras_v2 as F
from mtx import indice as I
from mtx import preproceso as P
from mtx.evaluacion import FILA_PROMEDIO

S, S2, D2 = config.DIR_SALIDA, config.DIR_SALIDA_V2, config.DIR_DATA_V2
DIR_FIGURAS = S2 / "figuras"


def _sha(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _rel(ruta: Path) -> str:
    return str(ruta.relative_to(config.RAIZ))


def _csv(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def fuentes_ir() -> dict:
    v2 = {"ranking": S2 / "ranking.csv", "juicios": S2 / "juicios_relevancia.csv",
          "resultados": S2 / "resultados_ir.csv", "mejor": D2 / "mejor_modelo.json",
          "ocho": S2 / "05_ir_8_variantes.csv", "robustez": S2 / "05_robustez.csv"}
    if all(p.exists() for p in v2.values()):
        return {"version": "v2", **v2}
    return {"version": "v1", "ranking": config.RAIZ / "ranking.csv",
            "juicios": config.RAIZ / "juicios_relevancia.csv",
            "resultados": config.RAIZ / "resultados_ir.csv",
            "mejor": config.DIR_DATA / "mejor_modelo.json"}


def fuentes_ie() -> dict:
    v2 = {"resultados": S2 / "resultados_ie.csv", "referencias": S2 / "09_referencias_f1.csv",
          "errores": S2 / "09_resumen_errores.csv"}
    if all(p.exists() for p in v2.values()):
        return {"version": "v2", **v2}
    return {"version": "v1", "resultados": config.RAIZ / "resultados_ie.csv",
            "errores": S / "09_resumen_errores.csv"}


def fuentes_respuestas() -> dict:
    v2 = S2 / "respuestas.csv"
    return ({"version": "v2", "respuestas": v2} if v2.exists()
            else {"version": "v1", "respuestas": S / "respuestas.csv"})


class Contexto:
    """Carga perezosa de lo pesado (índices, pasajes) y registro de fuentes por figura."""

    def __init__(self):
        self.est = F.cargar_estilo()
        self.consultas = _csv(config.CONSULTAS_CSV).set_index("query_id")
        self._ind, self._ind_lema, self._pas = None, None, None

    @property
    def ind(self):
        if self._ind is None:
            self._ind = I.cargar(config.INDICE_PKL)
        return self._ind

    @property
    def ind_lema(self):
        if self._ind_lema is None:
            self._ind_lema = I.cargar(config.INDICE_LEMA_PKL)
        return self._ind_lema

    @property
    def pasajes(self):
        if self._pas is None:
            self._pas = pd.read_parquet(config.PASAJES_PARQUET,
                                        columns=["passage_id", "doc_id", "fecha", "titulo",
                                                 "posicion", "texto", "inicio_cuerpo"]
                                        ).set_index("passage_id")
        return self._pas

    def etiqueta(self, pid: str) -> str:
        p = self.pasajes.loc[pid]
        return F.etiqueta_pasaje(p["fecha"], p["posicion"], p["titulo"])


# --------------------------------------------------------------------------- figuras


def _ganador(fi: dict) -> tuple[str, str]:
    """(nombre en ranking.csv, nombre para mostrar)."""
    m = json.loads(fi["mejor"].read_text(encoding="utf-8"))
    if fi["version"] == "v2":
        return m["modelo_en_ranking_csv"], m["modelo"]
    return m["modelo"], m["modelo"]


def f_corpus(cx):
    lim = json.loads((S / "01_limpieza.json").read_text(encoding="utf-8"))
    return F.fig_corpus(lim, cx.est), "corpus", [S / "01_limpieza.json"]


def f_acotaciones(cx):
    lim = json.loads((S / "01_limpieza.json").read_text(encoding="utf-8"))
    return F.fig_acotaciones(lim, cx.est), "corpus", [S / "01_limpieza.json"]


def f_tokenizacion(cx):
    fi = fuentes_ir()
    q = cx.est.ejemplos.get("tokenizacion_consulta", "Q3")
    en_rk, _ = _ganador(fi)
    rk = _csv(fi["ranking"])
    pid = rk[(rk["query_id"] == q) & (rk["modelo"] == en_rk) & (rk["rango"] == "1")
             ]["passage_id"].iloc[0]
    p = cx.pasajes.loc[pid]
    cuerpo = p["texto"][int(p["inicio_cuerpo"]):]
    oracion = F.oracion_ejemplo(cuerpo, set(P.tokenizar(cx.consultas.at[q, "consulta"])))
    pasos = F.pasos_tokenizacion(oracion, P.tokenizar(oracion, "lema"))
    fuente = (f"Oración real: {cx.etiqueta(pid)}, primer resultado de "
              f"«{F.nombre_consulta(cx.est, q, True)}»")
    return F.fig_tokenizacion(pasos, fuente, cx.est, fi["version"]), fi["version"], [fi["ranking"]]


def f_idf(cx):
    q = cx.est.ejemplos.get("idf_consulta", "Q6")
    t = F.terminos_idf(cx.consultas.at[q, "consulta"], cx.ind.df, cx.ind.N)
    return F.fig_idf(t, F.nombre_consulta(cx.est, q, True), cx.ind.N, cx.est), "corpus", []


def f_stem_lema(cx):
    filas = []
    for palabra in cx.est.ejemplos.get("stem_lema", []):
        stem = P.tokenizar(palabra)
        lema = P.tokenizar(palabra, "lema")
        if not stem or not lema:
            continue
        filas.append({"palabra": palabra, "stem": stem[0], "df_stem": cx.ind.df.get(stem[0], 0),
                      "lema": lema[0], "df_lema": cx.ind_lema.df.get(lema[0], 0)})
    return F.fig_stem_lema(pd.DataFrame(filas), cx.est), "v2", []


def f_indice(cx):
    postings = []
    for palabra in cx.est.ejemplos.get("postings", []):
        raiz = P.tokenizar(palabra)[0]
        fila = cx.ind.postings.get(raiz, {})
        top = sorted(((tf, cx.ind.ids[i]) for i, tf in fila.items()),
                     key=lambda x: (-x[0], x[1]))[:3]
        postings.append({"palabra": palabra, "raiz": raiz, "df": cx.ind.df.get(raiz, 0),
                         "idf": cx.ind.idf_bm25(raiz),
                         "top": [(cx.etiqueta(pid), tf) for tf, pid in top]})
    return F.fig_indice(postings, cx.ind.N, cx.est), "corpus", []


def f_booleano(cx):
    ruta = S2 / "03b_booleano.csv"
    if not ruta.exists():
        return None, "v2", []
    t = _csv(ruta)
    t["en_ventana"] = t["en_ventana"].astype(int)
    return F.fig_booleano(t, cx.est), "v2", [ruta]


def f_ap(cx):
    fi = fuentes_ir()
    q = cx.est.ejemplos.get("ap_consulta", "Q3")
    en_rk, mostrar = _ganador(fi)
    rk, ju, res = _csv(fi["ranking"]), _csv(fi["juicios"]), _csv(fi["resultados"])
    top = rk[(rk["query_id"] == q) & (rk["modelo"] == en_rk)].assign(
        _r=lambda d: d["rango"].astype(int)).sort_values("_r")
    rel_de = dict(zip(ju[ju["query_id"] == q]["passage_id"], ju[ju["query_id"] == q]["relevante"]))
    rel = [int(rel_de.get(p, "0") == "1") for p in top["passage_id"]]
    fila = res[(res["query_id"] == q) & (res["modelo"] == en_rk)].iloc[0]
    total, ap_kit = int(float(fila["relevantes_en_pool"])), float(fila["AP"])
    if abs(E.ap(rel, total) - ap_kit) > 5e-4:
        raise SystemExit(f"El AP recalculado de {q} no coincide con el del kit: corre la evaluación.")
    fig = F.fig_ap(rel, total, ap_kit, F.nombre_consulta(cx.est, q), F.nombre_modelo(mostrar),
                   cx.est, fi["version"])
    return fig, fi["version"], [fi["ranking"], fi["juicios"], fi["resultados"]]


def _maps(fi: dict) -> tuple[pd.DataFrame, str]:
    _, ganador = _ganador(fi)
    if fi["version"] == "v2":
        ocho = _csv(fi["ocho"])
        prom = ocho[ocho["query_id"] == FILA_PROMEDIO]
        rob = _csv(fi["robustez"])
        ic = rob[rob["analisis"] == "map_ic95_bootstrap"].set_index("modelo")
        m = pd.DataFrame({"modelo": prom["modelo"], "map": prom["AP"].astype(float)})
        m["inf"] = m["modelo"].map(ic["ic95_inf"]).astype(float)
        m["sup"] = m["modelo"].map(ic["ic95_sup"]).astype(float)
        return m, ganador
    res = _csv(fi["resultados"])
    prom = res[res["query_id"] == FILA_PROMEDIO]
    return pd.DataFrame({"modelo": prom["modelo"], "map": prom["AP"].astype(float),
                         "inf": float("nan"), "sup": float("nan")}), ganador


def f_map(cx):
    fi = fuentes_ir()
    m, ganador = _maps(fi)
    usadas = [fi["resultados"]] + ([fi["ocho"], fi["robustez"]] if fi["version"] == "v2" else [])
    return F.fig_map(m, ganador, cx.est, fi["version"]), fi["version"], usadas


def f_ap_consulta(cx):
    fi = fuentes_ir()
    if fi["version"] == "v2":
        ap = _csv(fi["ocho"])
        modelos = [m for m in E.MODELOS_V2 if m.endswith("con_filtro")]
        usadas = [fi["ocho"]]
    else:
        ap = _csv(fi["resultados"])
        modelos = ["bm25_con_filtro", "tfidf_con_filtro"]
        usadas = [fi["resultados"]]
    ap = ap[ap["query_id"] != FILA_PROMEDIO]
    return F.fig_ap_consulta(ap, modelos, cx.est, fi["version"]), fi["version"], usadas


def f_prf(cx):
    fe = fuentes_ie()
    return F.fig_prf(_csv(fe["resultados"]), cx.est, fe["version"]), fe["version"], [
        fe["resultados"]]


def f_f1_referencias(cx):
    fe = fuentes_ie()
    if fe["version"] != "v2":
        return None, "v1", []
    ref = _csv(fe["referencias"]).replace("", float("nan"))
    for c in ("f1", "ic95_inf", "ic95_sup"):
        ref[c] = ref[c].astype(float)
    res = _csv(fe["resultados"])
    for c in ("f1", "gold"):
        res[c] = res[c].astype(float)
    return F.fig_f1_referencias(ref, res, cx.est, "v2"), "v2", [fe["referencias"],
                                                                 fe["resultados"]]


def f_errores(cx):
    fe = fuentes_ie()
    r = _csv(fe["errores"])
    r["n"] = r["n"].astype(int)
    return F.fig_errores(r, cx.est, fe["version"]), fe["version"], [fe["errores"]]


def f_estados(cx):
    fr = fuentes_respuestas()
    return (F.fig_estados(_csv(fr["respuestas"]), cx.est, fr["version"]), fr["version"],
            [fr["respuestas"]])


FIGURAS = {
    "s2a_corpus": f_corpus, "s2b_acotaciones": f_acotaciones, "s4c_tokenizacion": f_tokenizacion,
    "s4d_idf": f_idf, "stem_lema": f_stem_lema, "r09_indice_invertido": f_indice,
    "r07_booleano": f_booleano,
    "s5a_ap_explicado": f_ap, "s5a_map_por_modelo": f_map, "s6_ap_por_consulta": f_ap_consulta,
    "s7c_prf_por_tipo": f_prf, "s7a_f1_con_referencias": f_f1_referencias,
    "s8_errores_patrones": f_errores, "s9_estados_respuesta": f_estados,
}
FUENTES_FIJAS = {"s4c_tokenizacion": [config.PASAJES_PARQUET],
                 "s4d_idf": [config.INDICE_PKL, config.CONSULTAS_CSV],
                 "stem_lema": [config.INDICE_PKL, config.INDICE_LEMA_PKL],
                 "r09_indice_invertido": [config.INDICE_PKL, config.PASAJES_PARQUET]}


def _titulo_plano(fig) -> str:
    return re.sub(r"<[^>]+>", " ", fig.layout.title.text).split("  ")[0].strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solo", help="figuras separadas por coma (por defecto, todas)")
    args = ap.parse_args()
    nombres = args.solo.split(",") if args.solo else list(FIGURAS)
    desconocidas = sorted(set(nombres) - set(FIGURAS))
    if desconocidas:
        print(f"Figuras desconocidas: {', '.join(desconocidas)}", file=sys.stderr)
        return 1
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    ruta_reg = DIR_FIGURAS / "figuras.json"
    registro = json.loads(ruta_reg.read_text(encoding="utf-8")) if ruta_reg.exists() else {}
    cx = Contexto()
    for nombre in nombres:
        t0 = time.perf_counter()
        fig, version, usadas = FIGURAS[nombre](cx)
        if fig is None:
            registro[nombre] = {"archivo": None, "datos": version,
                                "nota": "pendiente: faltan sus salidas (make all-v2 o make booleano)"}
            print(f"  pendiente  {nombre}: necesita datos v2")
            continue
        if F.tiene_id_o_ruta(fig):
            raise SystemExit(f"{nombre}: la figura muestra un ID de pasaje o una ruta (S8b, R04).")
        ruta = DIR_FIGURAS / f"{nombre}.png"
        fig.write_image(ruta, scale=2)
        fuentes = [*usadas, *FUENTES_FIJAS.get(nombre, [])]
        registro[nombre] = {"archivo": _rel(ruta), "titulo": _titulo_plano(fig), "datos": version,
                            "fuentes": {_rel(p): _sha(p) for p in fuentes if p.exists()}}
        print(f"  {version}  {_rel(ruta)}  ({time.perf_counter() - t0:.1f} s)")
    ruta_reg.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"Registro: {_rel(ruta_reg)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
