"""Evaluación de IE (PRD §6.12): detalle por método y tipo, complementaria de 20 IDs (P04, T10) y
análisis de errores por categoría.

La cifra oficial es la del kit (`kit/evaluar.py ie`, vía `adaptadores_kit`). Aquí se reproduce su
semántica (coincidencia exacta de `(passage_id, tipo, inicio, fin)`; `regla` = regla + ambos,
`modelo` = modelo + ambos, `combinado` = todo; solo pasajes con filas en el gold) para agregar FP,
FN y estados que el kit no da, y se verifica que coincide con el kit fila por fila.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from mtx.fusion import sin_acentos

TIPOS = ("PER", "ORG", "LOC", "FECHA", "MONTO")
METODOS = ("regla", "modelo", "combinado")
USA = {"regla": {"regla", "ambos"}, "modelo": {"modelo", "ambos"},
       "combinado": {"regla", "modelo", "ambos"}}
TIPOS_MODELO = {"PER", "ORG", "LOC"}  # el NER no produce FECHA ni MONTO
COLUMNAS_DETALLE = ["metodo", "tipo", "precision", "recall", "f1", "tp", "fp", "fn", "soporte",
                    "predichas", "estado"]
COLUMNAS_ERRORES = ["passage_id", "tipo", "texto_gold", "texto_pred", "inicio", "fin", "metodo",
                    "categoria", "fuente", "contexto", "error"]
RE_SIGLA = re.compile(r"[A-ZÁÉÍÓÚÑÜ]{2,7}")


def _conj(df: pd.DataFrame) -> set[tuple]:
    return set(zip(df["passage_id"], df["tipo"], df["inicio"].astype(int),
                   df["fin"].astype(int)))


def _prf(tp: int, npred: int, ngold: int) -> tuple[float, float, float]:
    p = tp / npred if npred else 0.0
    r = tp / ngold if ngold else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def detalle(gold: pd.DataFrame, pred: pd.DataFrame, pasajes: set[str]) -> pd.DataFrame:
    """P, R, F1, TP, FP, FN y soporte por método y tipo, sobre `pasajes`.

    `estado`: `ok`; `sin_cobertura` (el NER no produce el tipo); `no_aplicable` (sin soporte gold:
    el F1 no se interpreta)."""
    g = gold[gold["passage_id"].isin(pasajes)]
    filas = []
    for metodo in METODOS:
        p = pred[pred["passage_id"].isin(pasajes) & pred["metodo"].isin(USA[metodo])]
        for tipo in (*TIPOS, "TODOS"):
            gs = _conj(g if tipo == "TODOS" else g[g["tipo"] == tipo])
            ps = _conj(p if tipo == "TODOS" else p[p["tipo"] == tipo])
            tp = len(gs & ps)
            pr, rc, f1 = _prf(tp, len(ps), len(gs))
            estado = ("sin_cobertura" if metodo == "modelo" and tipo not in TIPOS_MODELO | {"TODOS"}
                      else "no_aplicable" if not gs else "ok")
            filas.append({"metodo": metodo, "tipo": tipo, "precision": round(pr, 4),
                          "recall": round(rc, 4), "f1": round(f1, 4), "tp": tp,
                          "fp": len(ps) - tp, "fn": len(gs) - tp, "soporte": len(gs),
                          "predichas": len(ps), "estado": estado})
    return pd.DataFrame(filas, columns=COLUMNAS_DETALLE)


def coincide_con_kit(det: pd.DataFrame, kit: pd.DataFrame) -> list[str]:
    """Compara TP, predichas y gold del detalle con `resultados_ie.csv` del kit."""
    k = kit.set_index(["metodo", "tipo"])
    err = []
    for f in det.to_dict("records"):
        clave = (f["metodo"], f["tipo"])
        if clave not in k.index:
            if f["predichas"] or f["soporte"]:
                err.append(f"{clave} con datos falta en el kit")
            continue
        fk = k.loc[clave]
        for a, b in (("tp", "tp"), ("predichas", "predichas"), ("soporte", "gold")):
            if int(float(fk[b])) != f[a]:
                err.append(f"{clave}: {a} {f[a]} ≠ kit {fk[b]}")
        if abs(float(fk["f1"]) - f["f1"]) > 1e-4:
            err.append(f"{clave}: f1 {f['f1']} ≠ kit {fk['f1']}")
    return err


# --------------------------------------------------------------------------- errores

def _fuente_corta(fuentes: str) -> str:
    def una(s: str) -> str:
        return ("regex" if s.startswith("regex") else "gazetteer" if s.startswith("gazetteer")
                else s)
    return "|".join(dict.fromkeys(una(s) for s in str(fuentes).split("|") if s))


def _contexto(texto: str, ini: int, fin: int, ancho: int = 50) -> str:
    return (texto[max(0, ini - ancho):ini] + "[" + texto[ini:fin] + "]"
            + texto[fin:fin + ancho]).replace("\n", " ")


def _solapa(a: dict, b: dict) -> bool:
    return max(a["inicio"], b["inicio"]) < min(a["fin"], b["fin"])


def analizar_errores(gold: pd.DataFrame, pred: pd.DataFrame, pasajes: pd.DataFrame,
                     obras: set[str]) -> pd.DataFrame:
    """Clasifica cada FN y FP del método combinado en los pasajes del gold. Una fila por error y
    categoría (las categorías no son excluyentes). `pred` lleva `metodo` y `fuentes`;
    `pasajes` lleva `passage_id, texto, inicio_cuerpo`; `obras` son nombres de obra sin acentos."""
    info = pasajes.set_index("passage_id")
    ids = set(gold["passage_id"])
    filas = []
    for pid in sorted(ids):
        texto, ic = info.at[pid, "texto"], int(info.at[pid, "inicio_cuerpo"])
        gs = [dict(f, inicio=int(f["inicio"]), fin=int(f["fin"]))
              for f in gold[gold["passage_id"] == pid].to_dict("records")]
        ps = [dict(f, inicio=int(f["inicio"]), fin=int(f["fin"]))
              for f in pred[pred["passage_id"] == pid].to_dict("records")]
        clave_g = {(g["tipo"], g["inicio"], g["fin"]) for g in gs}
        clave_p = {(p["tipo"], p["inicio"], p["fin"]) for p in ps}

        def fila(error, cat, tipo, ini, fin, tg, tp, metodo, fuente, pid=pid, texto=texto):
            filas.append({"passage_id": pid, "tipo": tipo, "texto_gold": tg, "texto_pred": tp,
                          "inicio": ini, "fin": fin, "metodo": metodo, "categoria": cat,
                          "fuente": fuente, "contexto": _contexto(texto, ini, fin),
                          "error": error})

        for g in gs:  # falsos negativos
            if (g["tipo"], g["inicio"], g["fin"]) in clave_p:
                continue
            sol = [p for p in ps if _solapa(g, p)]
            mismo = [p for p in sol if p["tipo"] == g["tipo"]]
            exacto_otro = [p for p in sol if (p["inicio"], p["fin"]) == (g["inicio"], g["fin"])
                           and p["tipo"] != g["tipo"]]
            cats = []
            if mismo:
                dentro = [p for p in mismo if g["inicio"] <= p["inicio"] and p["fin"] <= g["fin"]]
                cats.append(("frontera", mismo[0]))
                if len(dentro) >= 2:
                    cats.append(("frontera:entidad_partida", dentro[0]))
                if g["tipo"] == "MONTO" and any(p["inicio"] == g["inicio"] and p["fin"] < g["fin"]
                                                for p in mismo):
                    cats.append(("frontera:monto_sin_unidad", mismo[0]))
            if exacto_otro:
                cats.append(("tipo", exacto_otro[0]))
                if sin_acentos(g["texto"]) in obras:
                    cats.append(("tipo:obra_LOC_vs_ORG", exacto_otro[0]))
            if RE_SIGLA.fullmatch(g["texto"]) and not any(
                    p["inicio"] <= g["inicio"] and g["fin"] <= p["fin"] for p in ps):
                cats.append(("sigla_no_reconocida", None))
            if g["fin"] <= ic:
                cats.append(("en_marca", sol[0] if sol else None))
            if not sol:
                cats.append(("omision", None))
            for cat, p in cats:
                fila("FN", cat, g["tipo"], g["inicio"], g["fin"], g["texto"],
                     p["texto"] if p else "", p["metodo"] if p else "",
                     _fuente_corta(p["fuentes"]) if p else "")

        for p in ps:  # falsos positivos
            if (p["tipo"], p["inicio"], p["fin"]) in clave_g:
                continue
            sol = [g for g in gs if _solapa(g, p)]
            mismo = [g for g in sol if g["tipo"] == p["tipo"]]
            exacto_otro = [g for g in sol if (g["inicio"], g["fin"]) == (p["inicio"], p["fin"])
                           and g["tipo"] != p["tipo"]]
            cats = []
            if mismo:
                cats.append(("frontera", mismo[0]))
                g0 = mismo[0]
                partida = [q for q in ps if q["tipo"] == g0["tipo"]
                           and g0["inicio"] <= q["inicio"] and q["fin"] <= g0["fin"]]
                if len(partida) >= 2:
                    cats.append(("frontera:entidad_partida", g0))
                if p["tipo"] == "MONTO" and any(g["inicio"] == p["inicio"] and p["fin"] < g["fin"]
                                                for g in mismo):
                    cats.append(("frontera:monto_sin_unidad", g0))
            if exacto_otro:
                cats.append(("tipo", exacto_otro[0]))
                if sin_acentos(p["texto"]) in obras:
                    cats.append(("tipo:obra_LOC_vs_ORG", exacto_otro[0]))
            if p["fin"] <= ic:
                cats.append(("en_marca", sol[0] if sol else None))
            if not sol:
                cats.append(("espuria:" + _fuente_corta(p["fuentes"]), None))
            for cat, g in cats:
                fila("FP", cat, p["tipo"], p["inicio"], p["fin"], g["texto"] if g else "",
                     p["texto"], p["metodo"], _fuente_corta(p["fuentes"]))
    return pd.DataFrame(filas, columns=COLUMNAS_ERRORES)


def resumen_errores(err: pd.DataFrame) -> pd.DataFrame:
    if err.empty:
        return pd.DataFrame(columns=["error", "categoria", "tipo", "metodo", "n"])
    return (err.assign(metodo=err["metodo"].replace("", "—"))
            .groupby(["error", "categoria", "tipo", "metodo"]).size().rename("n").reset_index()
            .sort_values(["error", "categoria", "tipo", "metodo"]).reset_index(drop=True))


def alertas_u19(det: pd.DataFrame) -> list[str]:
    """Alertas, no metas: F1 combinado TODOS < 0.30 (buscar bug) y F1 = 1.0 con más de 5
    entidades gold (revisar fuga entre gold y extractor)."""
    out = []
    t = det[(det["metodo"] == "combinado") & (det["tipo"] == "TODOS")]
    if not t.empty and float(t["f1"].iloc[0]) < 0.30:
        out.append(f"U19: F1 combinado TODOS = {float(t['f1'].iloc[0]):.3f} < 0.30")
    for f in det[(det["f1"] >= 1.0) & (det["soporte"] > 5)].to_dict("records"):
        out.append(f"U19: F1 = 1.0 en {f['metodo']} × {f['tipo']} con soporte {f['soporte']}")
    return out


# --------------------------------------------------------------------------- figuras

COLOR_METODO = {"regla": "#2a78d6", "modelo": "#eb6834", "combinado": "#1baf7a"}
COLOR_ERROR = {"FN": "#6250d6", "FP": "#eda100"}  # distintos de los colores de método
NOMBRE_METODO = {"regla": "Reglas", "modelo": "Modelo (NER)", "combinado": "Combinado"}


def figuras_ie(det: pd.DataFrame, err: pd.DataFrame, dir_figuras: Path) -> list[Path]:
    import plotly.graph_objects as go

    from mtx.evaluacion import _estilo

    dir_figuras.mkdir(parents=True, exist_ok=True)
    rutas = []
    tipos = [*TIPOS, "TODOS"]
    barras = []
    for m in METODOS:
        d = det[det["metodo"] == m].set_index("tipo")
        y = [float(d.at[t, "f1"]) if d.at[t, "estado"] == "ok" else 0.0 for t in tipos]
        txt = [f"{d.at[t, 'f1']:.2f}" if d.at[t, "estado"] == "ok"
               else ("sin cobertura" if d.at[t, "estado"] == "sin_cobertura" else "n/a")
               for t in tipos]
        barras.append(go.Bar(name=NOMBRE_METODO[m], x=tipos, y=y, marker_color=COLOR_METODO[m],
                             marker_line_color="white", marker_line_width=2, text=txt,
                             textposition="outside", textangle=0,
                             textfont={"color": "#0b0b0b", "size": 10}, cliponaxis=False))
    sop = det[det["metodo"] == "combinado"].set_index("tipo")["soporte"]
    fig = go.Figure(barras)
    fig.update_layout(barmode="group")
    _estilo(fig, "F1 por tipo y método sobre el gold de 20 pasajes (coincidencia exacta)")
    fig.update_xaxes(ticktext=[f"{t}<br>(n={int(sop[t])})" for t in tipos], tickvals=tipos)
    fig.update_yaxes(title="F1")
    rutas.append(dir_figuras / "ie_f1_por_tipo_metodo.png")
    fig.write_image(rutas[-1], scale=2)

    # un error cuenta una vez por categoría principal (la subcategoría no suma de nuevo)
    base = err.assign(cat=err["categoria"].str.split(":").str[0]).drop_duplicates(
        ["error", "passage_id", "tipo", "inicio", "fin", "cat"])
    cuenta = base.groupby(["cat", "error"]).size()
    cats = sorted(base["cat"].unique(), key=lambda c: -int(cuenta[c].sum()))
    fig = go.Figure([
        go.Bar(name="Falsos negativos" if e == "FN" else "Falsos positivos", orientation="h",
               y=cats, x=[int(cuenta.get((c, e), 0)) for c in cats],
               marker_color=COLOR_ERROR[e], marker_line_color="white", marker_line_width=2,
               text=[int(cuenta.get((c, e), 0)) for c in cats],
               textposition="outside", cliponaxis=False)
        for e in ("FN", "FP")])
    fig.update_layout(barmode="group")
    _estilo(fig, "Errores del método combinado por categoría (no excluyentes)", alto=460)
    fig.update_yaxes(range=None, autorange="reversed", showgrid=False)
    fig.update_xaxes(title="Errores", showgrid=True, gridcolor="#e8e7e3")
    rutas.append(dir_figuras / "ie_errores_por_categoria.png")
    fig.write_image(rutas[-1], scale=2)
    return rutas
