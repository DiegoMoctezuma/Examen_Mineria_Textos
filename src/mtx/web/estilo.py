"""Estilo de la demo web: identidad vigente de gob.mx sin escudo ni logotipo (docs/decisiones.md,
2026-11-24). Colores medidos en la captura de referencia; títulos con remates (Noto Serif) y texto
en Noto Sans.
"""
from __future__ import annotations

import streamlit as st

GUINDA = "#591932"
GUINDA_OSCURO = "#350F1E"
DORADO = "#BC955C"
TEXTO = "#404041"
GRIS = "#6F6F71"
FONDO_SUAVE = "#F6F3F4"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&family=Noto+Serif:wght@600;700&display=swap');

:root {{ --guinda:{GUINDA}; --guinda-osc:{GUINDA_OSCURO}; --dorado:{DORADO}; --texto:{TEXTO};
         --gris:{GRIS}; --suave:{FONDO_SUAVE}; }}
html, body, .stApp, [data-testid="stAppViewContainer"] {{ background:#fff; color:var(--texto);
  font-family:'Noto Sans', system-ui, sans-serif; }}
header[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer
  {{ display:none !important; }}
.block-container {{ padding-top:0 !important; max-width:1180px; }}
.stApp p, .stApp li, .stApp label {{ color:var(--texto); }}
.stMarkdown .resp-fuente, .stMarkdown .nota, .stMarkdown .habla, .stMarkdown .inicio-texto,
.stMarkdown .ctx-tit {{ font-size:.88rem !important; line-height:1.45; }}
.stMarkdown .inicio-texto {{ font-size:.93rem !important; }}

/* Franjas a todo lo ancho con una sombra que desborda el contenedor centrado */
.franja, .st-key-menu {{ box-shadow:0 0 0 100vmax var(--bg); clip-path:inset(0 -100vmax);
  background:var(--bg); }}
.franja {{ --bg:var(--guinda); padding:1.05rem 0; margin-top:-1rem; }}
.marca {{ display:flex; align-items:baseline; gap:1rem; flex-wrap:wrap; }}
.marca-nombre {{ font-family:'Noto Serif', Georgia, serif; font-weight:700; font-size:1.9rem;
  color:#fff; letter-spacing:.01em; }}
.marca-lema {{ color:#fff; opacity:.9; font-size:1.05rem; }}
.st-key-menu {{ --bg:var(--guinda-osc); padding:.35rem 0; gap:.4rem; justify-content:flex-end;
  flex-wrap:wrap; }}
.st-key-menu a, .st-key-menu a p, .st-key-menu a span {{ color:#fff !important; font-size:1.05rem; }}
.st-key-menu a {{ background:transparent !important; border-radius:0; padding:.35rem .8rem; }}
.st-key-menu a:hover {{ background:rgba(255,255,255,.08) !important; }}
.st-key-menu a[aria-current="page"], .st-key-menu a[data-active="true"]
  {{ box-shadow:inset 0 -3px 0 var(--dorado); }}

.migas {{ margin:1.1rem 0 1.4rem; font-size:1.05rem; color:var(--texto); }}
.migas .casa {{ color:#b9b9bb; }} .migas .sep {{ margin:0 .55rem; font-weight:700; }}
.migas .actual {{ font-weight:700; }}

.etiqueta-fila {{ display:flex; align-items:stretch; border:1px solid #e3e3e3; margin:.4rem 0 1.2rem; }}
.etiqueta {{ background:var(--guinda); color:#fff; padding:.55rem 2.4rem .55rem 1rem;
  clip-path:polygon(0 0, calc(100% - 1.4rem) 0, 100% 50%, calc(100% - 1.4rem) 100%, 0 100%);
  font-size:1rem; margin:-1px 0 -1px -1px; }}

.titulo {{ font-family:'Noto Serif', Georgia, serif; font-weight:700; color:var(--texto);
  font-size:2.6rem; line-height:1.2; margin:.2rem 0 1rem; padding:0; }}
.entrada {{ font-family:'Noto Serif', Georgia, serif; font-weight:700; font-size:1.35rem;
  line-height:1.6; color:var(--texto); max-width:46rem; }}
.meta {{ color:var(--gris); font-size:1.05rem; margin:.4rem 0 1.4rem; }}

.pasaje-tarjeta {{ border:1px solid #e6e1e3; border-radius:10px; padding:1rem 1.2rem 1.1rem;
  margin:0 0 1rem; background:#fff; }}
.pasaje-tarjeta header {{ display:flex; gap:.8rem; align-items:flex-start; }}
.pasaje-tarjeta h3 {{ font-family:'Noto Serif', Georgia, serif; font-size:1.12rem; color:var(--texto);
  margin:0; padding:0; line-height:1.35; }}
.rango {{ flex:0 0 auto; width:2rem; height:2rem; border-radius:50%; background:var(--guinda);
  color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; }}
.habla {{ color:var(--gris); margin:.15rem 0 .5rem !important; font-size:.95rem; }}
.habla.prensa {{ color:#8a5a00 !important; }}
.nota {{ font-size:.9rem; color:var(--gris) !important; margin:.2rem 0 .4rem; }}
.pasaje-texto {{ line-height:1.7; font-size:1.02rem; max-height:15em; overflow:auto;
  padding-right:.4rem; white-space:pre-wrap; }}
mark.termino {{ background:#FFE08A; color:#1a1a1a; font-weight:700; padding:.02em .15em;
  border-radius:3px; }}
.paso {{ display:flex; gap:1.1rem; position:relative; padding-bottom:1.6rem; }}
.paso::before {{ content:""; position:absolute; left:1.05rem; top:2.4rem; bottom:0;
  border-left:2px solid #e3d5da; }}
.paso:last-of-type::before {{ display:none; }}
.paso-num {{ flex:0 0 auto; width:2.2rem; height:2.2rem; border-radius:50%;
  background:var(--guinda); color:#fff; font-weight:700; display:flex; align-items:center;
  justify-content:center; font-size:1.05rem; z-index:1; }}
.paso-cuerpo {{ flex:1; min-width:0; }}
.paso-cuerpo h2 {{ font-family:'Noto Serif', Georgia, serif; font-size:1.45rem; margin:.1rem 0 .5rem;
  padding:0; color:var(--texto); }}
.paso-cuerpo > p {{ line-height:1.6; }}
.buscador {{ display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; border:2px solid
  var(--guinda); border-radius:999px; padding:.55rem 1rem; margin:.4rem 0 .6rem; }}
.buscador .lupa {{ color:var(--guinda); font-size:1.3rem; line-height:1; }}
.buscador .q {{ flex:1; font-size:1.1rem; font-weight:600; min-width:12rem; }}
.buscador .filtro {{ font-size:.85rem; background:var(--suave); border-radius:999px;
  padding:.15rem .7rem; color:var(--texto); }}
.raiz {{ display:inline-block; font-family:ui-monospace, Menlo, monospace; background:#FFE08A;
  border-radius:4px; padding:.05rem .45rem; margin:0 .3rem .3rem 0; font-size:.92rem; }}
.embudo {{ display:flex; gap:.6rem; flex-wrap:wrap; margin:.4rem 0 .8rem; }}
.embudo div {{ background:var(--suave); border-radius:8px; padding:.5rem .8rem; min-width:9rem; }}
.embudo strong {{ display:block; font-size:1.3rem; color:var(--guinda); }}
.embudo span {{ font-size:.85rem; color:var(--gris); }}
details.contexto, details.mas {{ margin-top:.6rem; }}
details.contexto > summary, details.mas > summary {{ cursor:pointer; color:var(--guinda);
  font-weight:600; font-size:.93rem; }}
.ctx {{ border-left:3px solid var(--dorado); background:var(--suave); padding:.5rem .8rem;
  margin:.5rem 0; border-radius:0 6px 6px 0; }}
.ctx-tit {{ font-size:.85rem; color:var(--gris) !important; margin:0 0 .3rem !important;
  font-weight:600; }}
.ctx-texto {{ font-size:.95rem; line-height:1.65; white-space:pre-wrap; max-height:13em;
  overflow:auto; }}
.ctx-aqui {{ text-align:center; font-size:.8rem; color:var(--gris); margin:.2rem 0; }}

.pasaje-tarjeta.mini {{ padding:.75rem 1rem .8rem; margin-bottom:.7rem; }}
.pasaje-tarjeta.mini h3 {{ font-size:1rem; }}
.pasaje-tarjeta.mini .rango {{ width:1.7rem; height:1.7rem; font-size:.9rem; }}
.pasaje-tarjeta.comun {{ border-color:var(--dorado); }}
.en-ambos {{ color:#7a5b26; font-weight:600; }}
.inicio-texto {{ font-size:.93rem; color:var(--texto); margin:.1rem 0 0 !important; }}

.campo-tarjeta {{ border:1px solid #e6e1e3; border-top:4px solid var(--guinda);
  border-radius:8px; padding:.9rem 1.2rem 1rem; margin:0 0 1.1rem; }}
.campo-tarjeta h3 {{ font-family:'Noto Serif', Georgia, serif; font-size:1.25rem; margin:0 0 .4rem;
  padding:0; color:var(--texto); }}
.resp-renglon {{ padding:.65rem 0; border-top:1px solid #eee; }}
.resp-renglon:first-of-type {{ border-top:none; }}
.resp-valor {{ display:flex; justify-content:space-between; gap:.8rem; align-items:baseline;
  font-weight:700; font-size:1.05rem; }}
.unidad {{ font-weight:400; color:var(--gris); font-size:.9rem; }}
.estado {{ flex:0 0 auto; font-size:.78rem; font-weight:600; padding:.1rem .55rem;
  border-radius:999px; }}
.estado.ok {{ background:#DDEFE0; color:#1E5E2B; }}
.estado.amb {{ background:#F7EBCF; color:#7A5300; }}
.estado.contra {{ background:#F6DADA; color:#8E1C1C; }}
.estado.nada {{ background:#EEE; color:#444; }}
.resp-renglon blockquote {{ margin:.35rem 0 .2rem; padding:.1rem 0 .1rem .8rem;
  border-left:3px solid #e2d6da; color:var(--texto); font-size:.95rem; line-height:1.55; }}
.resp-fuente {{ font-size:.85rem; color:var(--gris) !important; margin:0 !important; }}

.stTabs [data-baseweb="tab-list"] {{ gap:.2rem; border-bottom:1px solid #e3e3e3; }}
.stTabs [data-baseweb="tab"] p {{ font-size:1.02rem; }}
.stTabs [aria-selected="true"] p {{ color:var(--guinda) !important; font-weight:700; }}
.stTabs [data-baseweb="tab-highlight"] {{ background:var(--guinda); }}
.explica {{ background:var(--suave); border-radius:8px; padding:.8rem 1rem; margin:.2rem 0 1rem;
  font-size:.97rem; line-height:1.6; }}
.col-tit {{ font-family:'Noto Serif', Georgia, serif; font-weight:700; font-size:1.2rem;
  margin:.2rem 0 .6rem; color:var(--texto); }}
.col-tit .gana {{ font-family:'Noto Sans', sans-serif; font-size:.75rem; font-weight:600;
  background:var(--guinda); color:#fff; padding:.1rem .5rem; border-radius:999px;
  margin-left:.4rem; vertical-align:middle; }}

mark.ent, span.ent {{ color:#1a1a1a; padding:.03em .2em; border-radius:3px;
  box-decoration-break:clone; -webkit-box-decoration-break:clone; border-bottom:2px solid; }}
.e-PER {{ background:#F6DCCB; border-color:#C9774A; }}
.e-ORG {{ background:#D6E4F3; border-color:#4C7DB5; }}
.e-LOC {{ background:#D9ECD5; border-color:#4E9A47; }}
.e-FECHA {{ background:#EADFF4; border-color:#8B5CB8; }}
.e-MONTO {{ background:#F4E6BF; border-color:#B08A2E; }}
.leyenda {{ display:flex; flex-wrap:wrap; gap:.45rem; align-items:center; margin:.2rem 0 1rem; }}
.leyenda-tit {{ color:var(--gris); margin-right:.2rem; }}
.leyenda .ent {{ font-size:.9rem; font-weight:600; }}

.tarjeta-guinda {{ background:var(--guinda); color:#fff; border-radius:8px; overflow:hidden; }}
.tg-tit {{ padding:.75rem 1rem; border-bottom:1px solid rgba(255,255,255,.35); }}
.tg-cuerpo {{ padding:1.1rem 1.2rem 1.3rem; line-height:1.6; }}
.tg-cuerpo, .tg-cuerpo p, .tg-cuerpo li {{ color:#fff !important; }}

.pie {{ margin-top:3rem; padding:1.4rem 0; color:#fff; font-size:.92rem; line-height:1.6;
  --bg:var(--guinda-osc); background:var(--bg); box-shadow:0 0 0 100vmax var(--bg);
  clip-path:inset(0 -100vmax); }}
.pie strong {{ color:#fff; }}

.stButton button[kind="primary"], .stFormSubmitButton button {{ background:var(--guinda);
  border-color:var(--guinda); color:#fff; }}

@media (max-width: 700px) {{
  .titulo {{ font-size:1.9rem; }} .entrada {{ font-size:1.12rem; }}
  .marca-nombre {{ font-size:1.5rem; }}
}}
</style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
