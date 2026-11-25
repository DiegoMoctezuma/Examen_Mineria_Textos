# Objetivos del PRD §10. Los que dependen de insumos humanos se detienen con un mensaje claro.
PY := uv run python
.PHONY: consultas consultas-v2 setup contratos corpus explorar explorar-v2 indice indice-lema ranking ranking-v2 pool pool-v2 app app-cli asignar-juicios importar-juicios evaluar-ir agregar-juicios evaluar-ir-v2 reglas congelar ner \
        muestra-gold muestra-gold-v2 acuerdo-gold revisar-cierres-v2 cierre-juicios-v2 cierre-gold-v2 verificar-ner-v2 inferir-seleccion comparacion-ner fijar-ner-v2 ner-v2 extraer-v2 evaluar-ie-v2 extraer evaluar-ie tablas tablas-v2 figuras-v2 resultados reporte laminas demo test test-lento \
        validar entrega all all-v2 limpiar

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
consultas-v2:
	$(PY) scripts/00b_consultas.py --v2
explorar:
	$(PY) scripts/00_descubrir_consultas.py
explorar-v2:
	$(PY) scripts/00_descubrir_consultas.py --v2
corpus:
	$(PY) scripts/01_corpus_y_pasajes.py
indice:
	$(PY) scripts/02_indice.py
indice-lema:
	$(PY) scripts/02_indice.py --raiz lema
ranking:
	$(PY) scripts/03_ranking.py
ranking-v2:
	$(PY) scripts/03_ranking.py --v2
pool:
	$(PY) scripts/04_pool.py
pool-v2:
	$(PY) scripts/04_pool.py --v2
app:
	uv run streamlit run src/mtx/app/app.py
app-cli:
	$(PY) -m mtx.app.cli juicios --anotador "$(ANOTADOR)"
asignar-juicios:
	$(PY) scripts/04b_asignar_juicios.py --lote $(LOTE)
importar-juicios:
	$(PY) scripts/04c_importar_juicios_v1.py --anotador $(ANOTADOR) --origen "$(ORIGEN)"
# WP-02 (D24): mayoría y acuerdo de los juicios v2, después de `make cierre-juicios-v2`.
agregar-juicios:
	$(PY) scripts/05a_agregar_juicios.py
# WP-06 (D28, D29): evaluación IR v2 sobre los juicios agregados; no toca la raíz.
evaluar-ir-v2:
	$(PY) scripts/05_evaluar_ir.py --v2
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
muestra-gold-v2:
	$(PY) scripts/08b_muestra_gold.py --v2 --partes $(PARTES)
acuerdo-gold:
	$(PY) scripts/09c_acuerdo_gold.py
# Cierres humanos v2 (PRD v2 §4): con todas las ramas de anotación integradas y commiteadas.
revisar-cierres-v2:
	$(PY) scripts/09d_cierres_v2.py revisar
cierre-juicios-v2:
	$(PY) scripts/09d_cierres_v2.py juicios $(if $(INCOMPLETOS),--aceptar-incompletos)
cierre-gold-v2:
	$(PY) scripts/09d_cierres_v2.py gold
# WP-10 (D34): candidatos NER sobre la selección v2; el grupo ner-v2 trae XLM-R y spaCy lg.
PY_NER := uv run --group ner-v2 python
verificar-ner-v2:
	$(PY_NER) scripts/09_comparacion_ner.py verificar
inferir-seleccion:
	$(PY_NER) scripts/09_comparacion_ner.py inferir
comparacion-ner:
	$(PY_NER) scripts/09_comparacion_ner.py comparar
fijar-ner-v2:
	$(PY_NER) scripts/09_comparacion_ner.py comparar --fijar
# WP-12 (D31, D33 a D35): IE v2, solo después de cierre_gold_v2.json; salidas en salida/v2/.
ner-v2:
	$(PY_NER) scripts/07_ner.py --v2
extraer-v2:
	$(PY_NER) scripts/08_extraer.py --v2
evaluar-ie-v2:
	$(PY) scripts/09_evaluar_ie.py --v2
extraer:
	$(PY) scripts/08_extraer.py
evaluar-ie:
	$(PY) scripts/09_evaluar_ie.py
# WP-13: tablas de respuesta de las 15 consultas con artefactos v2, en salida/v2/.
tablas-v2:
	$(PY) scripts/10_tablas.py --v2
tablas:
	$(PY) scripts/10_tablas.py

# Todas las cifras, tablas y figuras; no requiere pandoc ni TeX.
resultados: evaluar-ir evaluar-ie tablas

reporte:
	$(PY) scripts/11_reporte.py
laminas:
	@echo "La presentación final (laminas/Presentacion_Mineria_de_Textos.pptx) y el guion los hizo el equipo a mano; no se regeneran."
# WP-16: figuras v2 para láminas y reporte; v1 hasta que existan las salidas v2 (lo dicen en el subtítulo).
figuras-v2:
	$(PY) scripts/11b_figuras_v2.py $(if $(SOLO),--solo $(SOLO),)
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
# WP-14: cadena v2 desde los insumos congelados, después de los dos cierres y de fijar el NER v2
# (los cierres y `make fijar-ner-v2` se corren una sola vez y no forman parte de la cadena).
all-v2: ranking-v2 agregar-juicios evaluar-ir-v2 acuerdo-gold ner-v2 extraer-v2 evaluar-ie-v2 tablas-v2 figuras-v2
	$(PY) scripts/99_validar.py --parcial --sin-pruebas
all: entrega

# Borra solo artefactos regenerables; nunca anotaciones/ ni data/cache_ner/.
limpiar:
	@echo "Se borrarán: data/*.parquet data/*.pkl data/*.npz y salida/"
	rm -f data/*.parquet data/*.pkl data/*.npz
	rm -rf salida/*
