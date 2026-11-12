# Objetivos del PRD §10. Los que dependen de insumos humanos se detienen con un mensaje claro.
PY := uv run python
.PHONY: consultas setup contratos corpus explorar indice ranking pool app app-cli evaluar-ir reglas congelar ner \
        muestra-gold extraer evaluar-ie tablas resultados reporte laminas demo test test-lento \
        validar entrega all limpiar

setup:
	uv sync
	-uv run python -c "import nltk; nltk.download('stopwords', download_dir='.nltk_data', quiet=True)" 2>/dev/null || echo "AVISO: NLTK no descargó stopwords; se usa config/stopwords_es.txt (respaldo versionado)"
	-uv run plotly_get_chrome -y >/dev/null 2>&1 || echo "AVISO: no se instaló Chrome para kaleido; las figuras PNG no se podrán exportar"
	@command -v pandoc >/dev/null || echo "AVISO: falta pandoc (solo 'make reporte' lo necesita)"
	@command -v xelatex >/dev/null || echo "AVISO: falta xelatex (solo 'make reporte' lo necesita)"

contratos:
	uv run pytest tests/test_contratos_kit.py -q

consultas:
	$(PY) scripts/00b_consultas.py
explorar:
	$(PY) scripts/00_descubrir_consultas.py
corpus:
	$(PY) scripts/01_corpus_y_pasajes.py
indice:
	$(PY) scripts/02_indice.py
ranking:
	$(PY) scripts/03_ranking.py
pool:
	$(PY) scripts/04_pool.py
app:
	uv run streamlit run src/mtx/app/app.py
app-cli:
	$(PY) -m mtx.app.cli juicios
evaluar-ir:
	$(PY) scripts/05_evaluar_ir.py
reglas:
	$(PY) scripts/06_reglas.py

# Etiqueta git que debe preceder a cualquier commit del gold (PRD D15).
congelar:
	@git diff --quiet && git diff --cached --quiet || { echo "Hay cambios sin commitear: haz commit antes de congelar."; exit 1; }
	git tag -a reglas-congeladas -m "Reglas, gazetteers y convenciones congelados antes del gold"

ner:
	$(PY) scripts/07_ner.py
muestra-gold:
	$(PY) scripts/08b_muestra_gold.py
extraer:
	$(PY) scripts/08_extraer.py
evaluar-ie:
	$(PY) scripts/09_evaluar_ie.py
tablas:
	$(PY) scripts/10_tablas.py

# Todas las cifras, tablas y figuras; no requiere pandoc ni TeX.
resultados: evaluar-ir evaluar-ie tablas

reporte:
	$(PY) scripts/11_reporte.py
laminas:
	@echo "La presentación final (laminas/Presentacion_Mineria_de_Textos.pptx) y el guion los hizo el equipo a mano; no se regeneran."
laminas-generadas:
	$(PY) scripts/12_laminas.py  # deck automático anterior; escribe laminas/laminas.pptx
demo:
	$(PY) scripts/13_demo.py $(if $(Q),--q $(Q),) $(if $(CONSULTA),--consulta "$(CONSULTA)",) $(if $(DESDE),--desde $(DESDE),) $(if $(HASTA),--hasta $(HASTA),)

test:
	uv run pytest -q
test-lento:
	uv run pytest -q -m "lento or not lento"

validar:
	$(PY) scripts/99_validar.py

entrega: contratos resultados reporte laminas validar
	@echo "Copia de los seis CSV a la raíz: la hace scripts/99_validar.py tras validar."
all: entrega

# Borra solo artefactos regenerables; nunca anotaciones/ ni data/cache_ner/.
limpiar:
	@echo "Se borrarán: data/*.parquet data/*.pkl data/*.npz y salida/"
	rm -f data/*.parquet data/*.pkl data/*.npz
	rm -rf salida/*
