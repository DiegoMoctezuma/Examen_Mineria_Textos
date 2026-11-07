"""Descubrimiento guiado de Q9 y Q10 (PRD §5.2). Calcula señal; el alumno elige.

Nunca usa juicios ni gold, no reformula Q1 a Q8 y no decide por mayor conteo.
"""
from __future__ import annotations

import pandas as pd

from . import corpus


def cuerpo_normalizado(pasajes: pd.DataFrame) -> pd.Series:
    """Cuerpo del pasaje (sin la marca de interlocutor), en minúsculas y sin acentos."""
    cuerpos = [t[i:] for t, i in zip(pasajes["texto"], pasajes["inicio_cuerpo"], strict=True)]
    return pd.Series([corpus.sin_acentos(c).lower() for c in cuerpos], index=pasajes.index)


def analizar_candidato(pasajes: pd.DataFrame, norm: pd.Series, cand: dict) -> dict:
    """Conteos de un candidato, en todo el corpus y dentro de su ventana sugerida."""
    terminos = [corpus.sin_acentos(t).lower() for t in cand["terminos"]]
    coincide = pd.DataFrame({t: norm.str.contains(t, regex=False) for t in terminos})
    n_terminos = coincide.sum(axis=1)
    en_ventana = (pasajes["fecha"] >= pd.Timestamp(cand["desde"])) & (
        pasajes["fecha"] <= pd.Timestamp(cand["hasta"]))
    alguno = n_terminos >= 1
    return {
        "candidato": cand,
        "pasajes_total": int(alguno.sum()),
        "pasajes_ventana": int((alguno & en_ventana).sum()),
        "pasajes_ventana_2_terminos": int(((n_terminos >= 2) & en_ventana).sum()),
        "discursos_total": int(pasajes.loc[alguno, "doc_id"].nunique()),
        "discursos_ventana": int(pasajes.loc[alguno & en_ventana, "doc_id"].nunique()),
        "por_termino": {t: int(coincide[t].sum()) for t in terminos},
        "por_anio": pasajes.loc[alguno, "fecha"].dt.year.value_counts().sort_index().to_dict(),
        "ejemplos": _ejemplos(pasajes, n_terminos, alguno & en_ventana),
    }


def _ejemplos(pasajes: pd.DataFrame, n_terminos: pd.Series, mascara: pd.Series,
              k: int = 3, largo: int = 300) -> list[dict]:
    """Tres pasajes de la ventana con más términos distintos; desempate por orden de id."""
    sel = pasajes[mascara].assign(_n=n_terminos[mascara]).copy()
    sel["_doc"] = sel["doc_id"]
    sel["_pos"] = sel["posicion"]
    sel = sel.sort_values(["_n", "_doc", "_pos"], ascending=[False, True, True]).head(k)
    return [{"passage_id": r.passage_id, "fecha": r.fecha.date().isoformat(),
             "texto": r.texto[r.inicio_cuerpo:r.inicio_cuerpo + largo]}
            for r in sel.itertuples()]


def a_markdown(resultados: list[dict], consultas_obligatorias: pd.DataFrame) -> str:
    """Informe `salida/00_candidatos_q9q10.md`."""
    L = ["# Candidatos para Q9 y Q10", "",
         ("Señal calculada sobre `data/pasajes.parquet` (127 mil pasajes, cuerpo sin la marca de "
          "interlocutor, búsqueda sin acentos ni mayúsculas). **Esto no elige nada**: el alumno "
          "decide dos temas distintos entre sí y de Q1 a Q8, y redacta consulta, ventana y "
          "pregunta. La redacción final queda `[VALIDAR]`."), "",
         "## Consultas obligatorias (no se tocan)", ""]
    for r in consultas_obligatorias.itertuples():
        L.append(f"- {r.query_id}: {r.consulta} ({r.desde} a {r.hasta})")
    L += ["", "## Resumen", "",
          ("| Candidato | Pasajes (todo el corpus) | Pasajes en ventana | Con 2 o más términos | "
           "Discursos en ventana |"), "| --- | ---: | ---: | ---: | ---: |"]
    for r in resultados:
        c = r["candidato"]
        L.append(f"| {c['tema']} | {r['pasajes_total']:,} | {r['pasajes_ventana']:,} | "
                 f"{r['pasajes_ventana_2_terminos']:,} | {r['discursos_ventana']:,} |")
    for r in resultados:
        c = r["candidato"]
        L += ["", f"## {c['tema']}", "",
              f"- Términos semilla: {', '.join(c['terminos'])}",
              f"- Ventana sugerida: {c['desde']} a {c['hasta']}",
              f"- Pregunta sugerida: {c['pregunta']}",
              "- Pasajes por término (todo el corpus): "
              + ", ".join(f"`{t}` {n:,}" for t, n in r["por_termino"].items()),
              (f"- Discursos distintos: {r['discursos_total']:,} en todo el corpus, "
               f"{r['discursos_ventana']:,} en la ventana"),
              "- Pasajes por año: " + ", ".join(f"{a}: {n:,}" for a, n in r["por_anio"].items()),
              "", "Ejemplos (primeros 300 caracteres del cuerpo):", ""]
        for e in r["ejemplos"]:
            L.append(f"- `{e['passage_id']}` ({e['fecha']}): {e['texto']}")
        if not r["ejemplos"]:
            L.append("- (sin pasajes en la ventana)")
    return "\n".join(L) + "\n"
