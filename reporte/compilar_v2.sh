#!/usr/bin/env bash
# Requiere Python 3, Pandoc, XeLaTeX, TeX Gyre Pagella y Liberation Sans.
set -euo pipefail
base="$(cd -- "$(dirname -- "$0")" && pwd -P)"
cd "$base"
export TMPDIR="$PWD/render"
python3 render/preparar.py
pandoc \
    render/entrada.md -f markdown -t latex --standalone --metadata title= --metadata lang=es-MX \
    -V papersize=letter -V geometry:margin=2.2cm -V fontsize=10pt \
    -V mainfont="TeX Gyre Pagella" -V linestretch=1.07 -V documentclass=article \
    --include-in-header=render/estilo.tex -o render/pandoc_original.tex
python3 render/ajustar_tex.py
for pasada in 1 2; do
    xelatex -no-shell-escape -halt-on-error -interaction=nonstopmode \
        -output-directory=render render/reporte_v2.tex > render/compilacion.log
done
cp render/reporte_v2.pdf reporte_v2.pdf
