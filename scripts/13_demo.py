"""13 · Demo en terminal (PRD §6.16). `make demo Q=Q3` o `make demo CONSULTA="..."`.

Consulta del experimento (`--q Q3`): todo sale de artefactos guardados (ranking.csv,
entidades.csv, respuestas.csv); no recalcula índices, métricas ni NER.
Consulta libre (`--consulta`, opcional `--desde/--hasta`): recupera con el índice guardado y
ejecuta reglas y NER en caliente sobre los 10 pasajes; lo avisa y no le atribuye MAP ni F1.
Sin red cuando el modelo NER ya está en la caché local de Hugging Face.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mtx import config, ranking
from mtx import reglas as R

T0 = time.perf_counter()
con = Console(width=150)
COLOR = {"PER": "magenta", "ORG": "cyan", "LOC": "green", "FECHA": "yellow", "MONTO": "red"}
ESTILO_METODO = {"regla": "", "modelo": "italic", "ambos": "bold"}


def recorte(t: str, n: int = 100) -> str:
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[: n - 1] + "…"


def tabla_lado_a_lado(tf: pd.DataFrame, bm: pd.DataFrame, pas: pd.DataFrame) -> Table:
    t = Table(title="Top-10 TF-IDF y BM25 (con filtro de fecha)", show_lines=False)
    for c in ("#", "TF-IDF pasaje", "fecha", "pos", "puntaje", "BM25 pasaje", "fecha", "pos",
              "puntaje"):
        t.add_column(c, no_wrap=True)
    for i in range(max(len(tf), len(bm))):
        fila = [str(i + 1)]
        for d in (tf, bm):
            if i < len(d):
                r = d.iloc[i]
                fila += [str(r["passage_id"]), str(r["fecha"])[:10], str(r["posicion"]),
                         f"{float(r['puntaje']):.3f}"]
            else:
                fila += ["", "", "", ""]
        t.add_row(*fila)
    return t


def mostrar_pasajes(ids: list[str], pas: pd.DataFrame, ents: pd.DataFrame, titulo: str) -> None:
    con.rule(titulo)
    for pid in ids:
        r = pas.loc[pid]
        e = ents[ents["passage_id"] == pid].sort_values("inicio")
        con.print(f"[bold]{pid}[/] · {str(r['fecha'])[:10]} · {recorte(r['interlocutor'], 60)}")
        con.print(f"   {recorte(r['texto'][r['inicio_cuerpo']:], 100)}")
        if e.empty:
            con.print("   [dim]sin entidades[/]")
            continue
        partes = [f"[{COLOR[x.tipo]} {ESTILO_METODO.get(x.metodo, '')}]{x.texto}[/] "
                  f"[dim]{x.tipo}/{x.metodo}[/]" for x in e.itertuples()]
        con.print("   " + " · ".join(partes))
    con.print("[dim]Color = tipo (PER magenta, ORG cian, LOC verde, FECHA amarillo, "
              "MONTO rojo); negrita = ambos, cursiva = solo modelo, normal = solo regla.[/]")


def tabla_respuesta(q: str) -> None:
    res = pd.read_csv(config.DIR_SALIDA / "respuestas.csv", dtype=str, keep_default_na=False)
    res = res[res["query_id"] == q]
    con.rule(f"Tabla de respuesta con evidencia · {q}")
    t = Table(show_lines=False)
    for c in ("campo", "valor", "estado", "pasaje", "cita breve"):
        t.add_column(c, overflow="fold")
    estilo = {"respaldado_en_texto": "green", "ambiguo": "yellow", "no_encontrado": "red",
              "contradictorio": "magenta"}
    for campo, g in res.groupby("campo_respuesta", sort=False):
        g = pd.concat([g[g["estado"] == "respaldado_en_texto"].head(3),
                       g[g["estado"] != "respaldado_en_texto"].head(1)])
        for x in g.itertuples():
            t.add_row(campo, x.valor or "sin evidencia en el top-10",
                      f"[{estilo.get(x.estado, '')}]{x.estado}[/]", x.passage_id,
                      recorte(x.cita, 70))
    con.print(t)
    con.print("[dim]«respaldado» significa que el texto lo afirma cerca del valor, no que sea "
              f"verdad. Tabla completa: salida/tablas_respuesta/{q}.md[/]")


def demo_consulta(q: str, pas: pd.DataFrame) -> None:
    cons = pd.read_csv(config.CONSULTAS_CSV, dtype=str, keep_default_na=False).set_index(
        "query_id")
    if q not in cons.index:
        sys.exit(f"{q} no está en data/consultas.csv")
    c = cons.loc[q]
    mejor = json.loads((config.DIR_DATA / "mejor_modelo.json").read_text())["modelo"]
    con.print(Panel(f"[bold]{q}[/] · {c['consulta']}\nVentana: {c['desde']} a {c['hasta']}\n"
                    f"Pregunta: {c['pregunta_extraccion']}\nMejor modelo (MAP): {mejor}",
                    title="Consulta del experimento (artefactos guardados)"))
    rk = pd.read_csv(config.DIR_SALIDA / "ranking.csv", dtype={"passage_id": str})
    rk = rk[rk["query_id"] == q]
    tf = rk[rk["modelo"] == "tfidf_con_filtro"].sort_values("rango")
    bm = rk[rk["modelo"] == "bm25_con_filtro"].sort_values("rango")
    con.print(tabla_lado_a_lado(tf, bm, pas))
    ent = pd.read_csv(config.RAIZ / "entidades.csv", dtype={"passage_id": str},
                      keep_default_na=False)
    ids = list(rk[rk["modelo"] == mejor].sort_values("rango")["passage_id"])
    mostrar_pasajes(ids, pas, ent[ent["query_id"] == q],
                    f"Pasajes y entidades del top-10 de {mejor}")
    tabla_respuesta(q)


def demo_libre(texto: str, desde, hasta, pas: pd.DataFrame) -> None:
    con.print(Panel(f"[bold]{texto}[/]\nVentana: {desde or 'sin inicio'} a "
                    f"{hasta or 'sin fin'}", title="Consulta libre"))
    tf, e1 = ranking.buscar(texto, desde, hasta, "tfidf")
    bm, e2 = ranking.buscar(texto, desde, hasta, "bm25")
    for a in e1["avisos"] + e2["avisos"]:
        con.print(f"[yellow]Aviso:[/] {a}")
    con.print(f"Tokens de la consulta: {e2['tokens']}")
    con.print(tabla_lado_a_lado(tf, bm, pas))
    con.print("[bold yellow]NER en caliente sobre los 10 pasajes de BM25 (20 a 40 s en CPU). "
              "Consulta fuera del experimento: sin MAP ni F1.[/]")
    from mtx import ner_modelo as N
    principal, cfgs = N.cargar_config()
    cfg = cfgs[principal]
    pipe, tok = N.construir_pipeline(cfg)
    filas = []
    for pid in bm["passage_id"]:
        r = pas.loc[pid]
        reg = {(e.tipo, e.inicio, e.fin): e for e in R.extraer_reglas(r["texto"],
                                                                      int(r["inicio_cuerpo"]))}
        mod = {}
        for e in N.posprocesar(r["texto"], N.inferir_pasaje(r["texto"], pipe, tok, cfg), cfg,
                               pid).entidades:
            mod[(e["tipo"], e["inicio"], e["fin"])] = e
        for k in reg.keys() | mod.keys():
            metodo = "ambos" if k in reg and k in mod else ("regla" if k in reg else "modelo")
            filas.append({"passage_id": pid, "tipo": k[0], "inicio": k[1], "fin": k[2],
                          "texto": r["texto"][k[1]:k[2]], "metodo": metodo})
    mostrar_pasajes(list(bm["passage_id"]), pas, pd.DataFrame(
        filas, columns=["passage_id", "tipo", "inicio", "fin", "texto", "metodo"]),
        "Pasajes y entidades del top-10 de BM25 (en caliente)")
    con.print("[dim]Las tablas de respuesta con evidencia solo existen para Q1 a Q10.[/]")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--q", help="ID de consulta del experimento (Q1 a Q10)")
    ap.add_argument("--consulta", help="texto de una consulta libre")
    ap.add_argument("--desde")
    ap.add_argument("--hasta")
    a = ap.parse_args()
    if not a.q and not a.consulta:
        a.q = "Q3"
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=[
        "passage_id", "fecha", "texto", "inicio_cuerpo", "interlocutor"]).set_index("passage_id")
    t_carga = time.perf_counter() - T0
    if a.q:
        demo_consulta(a.q.upper(), pas)
    else:
        demo_libre(a.consulta, a.desde, a.hasta, pas)
    con.print(f"\n[dim]Carga de artefactos: {t_carga:.1f} s · total: "
              f"{time.perf_counter() - T0:.1f} s[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
