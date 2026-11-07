"""Alternativa sin Streamlit (PRD §7): `uv run python -m mtx.app.cli juicios` o `make app-cli`.

Misma persistencia, mismo validador y mismo modo ciego que la app. Por ahora ofrece juicios;
gold y demo se agregan en H5 y H6.

Teclas: 1 = relevante, 0 = no relevante, o = omitir por ahora, a = anterior,
c = cambiar de consulta, g = comprobar guardado, s = salir.
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from mtx import consultas
from mtx.app import componentes as C

AYUDA = "[1] relevante  [0] no relevante  [o] omitir  [a] anterior  [c] consulta  [g] guardado  [s] salir"


def _texto_rich(texto: str, inicio_cuerpo: int, consulta: str) -> Text:
    """Mismo resaltado que la app, desde offsets (sin reemplazo de texto)."""
    t = Text(texto)
    if inicio_cuerpo:
        t.stylize("dim italic", 0, inicio_cuerpo)
    for ini, fin, _ in C.spans_terminos(texto, inicio_cuerpo, consulta):
        t.stylize("bold black on yellow", ini, fin)
    return t


def juicios(entrada=input, consola: Console | None = None) -> None:
    con = consola or Console()
    r = C.rutas()
    if not r.pool.exists():
        con.print("Falta el pool: corre `make pool`.")
        return
    if not r.criterios.exists():
        con.print("Falta config/criterios_relevancia.md: el alumno lo escribe antes del primer "
                  "juicio (D07).")
        return
    cambios = C.cambios_en_insumos(r)
    if cambios:
        con.print(*cambios, "No se puede seguir juzgando: ver skill integridad-congelacion.",
                  sep="\n")
        return
    items = C.cargar_items(r)
    cons = consultas.cargar().set_index("query_id")
    juicios_df, token = C.cargar_juicios(r)
    qids = list(dict.fromkeys(items["query_id"]))
    pos = {}

    def elegir_consulta() -> str:
        prog = C.progreso(items, juicios_df).set_index("query_id")
        for q in qids:
            con.print(f"  {q}: {prog.at[q, 'juzgados']}/{prog.at[q, 'total']}  "
                      f"{cons.at[q, 'consulta']}")
        while True:
            q = entrada("Consulta (por ejemplo Q1): ").strip().upper()
            if q in qids:
                return q

    q = elegir_consulta()
    while True:
        g = items[items["query_id"] == q].reset_index(drop=True)
        if q not in pos:
            pos[q] = C.siguiente_pendiente(g, juicios_df, 0, incluir_actual=True) or 0
        i = pos[q]
        it = g.iloc[i]
        valor = C.valor_actual(juicios_df, q, it["passage_id"])
        con.rule(f"{q}: {cons.at[q, 'consulta']}")
        con.print(f"Pregunta (ayuda): {cons.at[q, 'pregunta_extraccion']}", style="dim")
        con.print(f"Pasaje {i + 1} de {len(g)} · {C.ETIQUETAS[valor]} · doc_id {it['doc_id']} · "
                  f"{it['interlocutor'] or '(sin marca)'} · fecha {it['fecha'] or 'desconocida'}"
                  " (no cuenta)")
        con.print(Panel(_texto_rich(it["texto"], int(it["inicio_cuerpo"]),
                                    cons.at[q, "consulta"]), title=it["titulo"][:90]))
        tecla = entrada(AYUDA + "\n> ").strip().lower()
        if tecla == "s":
            return
        if tecla == "c":
            q = elegir_consulta()
            continue
        if tecla == "a":
            pos[q] = max(0, i - 1)
            continue
        if tecla == "g":
            ok = C.sha256_ruta(r.juicios) == token
            con.print("Todo guardado." if ok else "El archivo cambió desde otro proceso.")
            continue
        if tecla not in ("1", "0", "o"):
            continue
        if tecla == "o" and valor in ("0", "1"):
            pos[q] = min(i + 1, len(g) - 1)
            continue
        try:
            juicios_df, token = C.guardar_juicio(items, juicios_df, token, q, it["passage_id"],
                                                 "" if tecla == "o" else tecla, r,
                                                 C.insumos_actuales(r))
        except C.ConflictoEdicion as e:
            con.print(f"[red]{e}[/red] Sal y vuelve a entrar.")
            continue
        sig = C.siguiente_pendiente(g, juicios_df, i)
        if sig is None:
            con.print(f"{q} completa.")
        else:
            pos[q] = sig


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    modo = argv[0] if argv else "juicios"
    if modo == "juicios":
        juicios()
    elif modo in ("gold", "demo"):
        print(f"`{modo}` se agrega en H5 y H6; mientras tanto, la demo es `make demo Q=Q3`.")
    else:
        print("Uso: python -m mtx.app.cli [juicios|gold|demo]")


if __name__ == "__main__":
    main()
