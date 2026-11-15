---
name: entrega-reproducible
description: "Usa esta skill cuando toques el entorno (pyproject, uv.lock, requirements.txt), el Makefile, el .gitignore, el README, AGENTS.md, los commits y etiquetas, el manifiesto de ejecución, scripts/99_validar.py o tests/test_formatos.py, o cuando prepares el hito H9 (make entrega desde clon limpio y etiqueta v1.0-entrega)."
---
# Entrega reproducible: entorno, Makefile, README, commits y validación

## Cuándo usarla
- Al crear o modificar `pyproject.toml`, `uv.lock`, `requirements.txt`, `.python-version`, `Makefile` o `.gitignore`.
- Al escribir o revisar `README.md`, `AGENTS.md`, `docs/reproducibilidad.md`, `docs/guia_defensa.md` o `docs/decisiones.md`.
- Al redactar mensajes de commit, crear etiquetas (`reglas-congeladas`, `v1.0-entrega`) o decidir qué se versiona.
- Al implementar `scripts/99_validar.py`, `tests/test_formatos.py` o `salida/manifiesto_ejecucion.json`.
- En el hito H9: reconstrucción desde clon limpio, README con tiempos medidos, sección "Uso de IA" y push final.

Fuente de verdad: PRD §9, §10, §11, §13.2 y decisiones D01 y D18. Si algo no está en el PRD, no se inventa: se pregunta al alumno y se registra en `docs/decisiones.md`.

## Entorno y dependencias
Referencia: PRD §11.1 y D01.

1. `pyproject.toml` con `requires-python = ">=3.11,<3.13"`.
2. Dependencias de ejecución (exactamente estas): `pandas, numpy, scikit-learn, nltk, regex, datasets, pyarrow, transformers, torch, streamlit, python-pptx, pyyaml, rich, plotly, kaleido, pypdf`.
3. Grupo de desarrollo: `pytest, rank_bm25, ruff`. Registrar el marcador `lento` en la configuración de pytest (`[tool.pytest.ini_options] markers`).
4. `torch` solo CPU en Linux y Windows: índice `https://download.pytorch.org/whl/cpu` declarado en `[[tool.uv.index]]` y asignado en `[tool.uv.sources]` con marcadores de plataforma; en macOS el wheel por defecto ya es CPU/MPS y no se redirige.
5. `.python-version` con `3.11`. `uv.lock` siempre versionado. Tras cada cambio de dependencias, regenerar `requirements.txt` con el comando exacto:
   ```bash
   uv export --no-dev --format requirements-txt > requirements.txt
   ```
   La rúbrica nombra `requirements.txt`; `uv.lock` es la fuente y `requirements.txt` la exportación. `make validar` comprueba que coinciden (condición 14).

Lista de verificación del entorno:
- [ ] `uv sync` termina sin red adicional más allá de los índices declarados.
- [ ] `uv run python -c "import torch; print(torch.cuda.is_available())"` imprime `False` en Linux/Windows (wheel CPU).
- [ ] `uv run pytest -q` corre offline con fixtures; `uv run pytest -q -m lento` es el único que toca corpus y modelos.
- [ ] `make setup` instala stopwords de NLTK y solo advierte (no falla) si faltan `pandoc` o `xelatex`.

## Estructura del repo y qué se versiona
Referencia: PRD §9. El árbol completo está ahí; no se crean carpetas fuera de él sin registrar la decisión.

Se versiona (obligatorio):
- Raíz: `README.md`, `AGENTS.md`, `pyproject.toml`, `uv.lock`, `requirements.txt`, `Makefile`, `.gitignore`, `.python-version` y los seis CSV de entrega: `ranking.csv`, `juicios_relevancia.csv`, `resultados_ir.csv`, `entidades.csv`, `gold_entidades.csv`, `resultados_ie.csv`.
- `data/consultas.csv`, `data/corpus_meta.json`, `data/mejor_modelo.json`, `data/modelo_ner.json`, `data/cache_ner/` completa.
- Todo `anotaciones/`, todo `config/`, todo `salida/` (es pequeño y el profesor debe poder leerlo), `reporte/reporte.md`.
- `kit/` con los cuatro originales sin modificar (hashes en `docs/contratos_kit.md`), `src/mtx/`, `scripts/`, `tests/` con `tests/fixtures/`, `docs/`, `laminas/`.

`.gitignore` excluye exactamente:
```gitignore
data/*.parquet
data/*.pkl
data/*.npz
kit/data/
.venv/
__pycache__/
# pesos de modelos (caché de Hugging Face, *.bin, *.safetensors fuera del repo)
```
Regla: un recurso excluido que no pueda reconstruirse desde la fuente lleva instrucciones y hash para recuperarlo en `docs/reproducibilidad.md`. Nunca se añaden `anotaciones/` ni `data/cache_ner/` al `.gitignore`.

Nota sobre este repo: el `README.md` actual es la plantilla que GitLab genera al crear el proyecto; se reemplaza por completo en H9 con las 10 secciones de PRD §11.2. El remote `origin` apunta a GitLab aunque el PRD hable de GitHub (§1, Fase 0 punto 3, §2). Registrar la decisión en `docs/decisiones.md` con fecha, motivo y efecto (acceso del profesor comprobado sobre GitLab; condición 15).

## Makefile: objetivos y reglas
Referencia: PRD §10. Cada objetivo tiene dependencias reales sobre archivos, no órdenes sueltas.

| Objetivo | Equivalente sin `make` (va en el README) | Regla clave |
| --- | --- | --- |
| `setup` | `uv sync` + descarga de stopwords NLTK | Comprueba `pandoc` y `xelatex`; advierte, no falla |
| `contratos` | `uv run pytest -q tests/test_contratos_kit.py` | Escribe `docs/contratos_kit.md` |
| `explorar` | `uv run python scripts/00_descubrir_consultas.py` | Candidatos Q9 y Q10 |
| `corpus` | `uv run python scripts/01_corpus_y_pasajes.py` | Descarga, limpieza auditada, segmentación, sensibilidad OP |
| `indice` / `ranking` | `uv run python scripts/02_indice.py` / `03_ranking.py` | |
| `pool` | `uv run python scripts/04_pool.py` | Construye o verifica; nunca sustituye un pool anotado sin detectar el cambio |
| `app` | `uv run streamlit run ...` | Estado, juicios, gold, gazetteer, demo |
| `evaluar-ir` | `uv run python scripts/05_evaluar_ir.py` | Exige juicios validados; escribe `data/mejor_modelo.json` |
| `reglas` | `uv run python scripts/06_reglas.py` | Minería de siglas y suite de regex |
| `congelar` | `git tag reglas-congeladas` | Antes de abrir el gold |
| `ner` | `uv run python scripts/07_ner.py` | No infiere si `data/cache_ner/` ya existe |
| `muestra-gold` | `uv run python scripts/08b_muestra_gold.py` | Muestra gold y, si aplica, selección |
| `extraer` | `uv run python scripts/08_extraer.py` | Fusión, `entidades.csv`, enriquecidas, auxiliares |
| `evaluar-ie` | `uv run python scripts/09_evaluar_ie.py` | Exige gold cerrado y compatible |
| `tablas` | `uv run python scripts/10_tablas.py` | Respuestas con evidencia |
| `resultados` | cifras, tablas y figuras | NO requiere pandoc ni TeX |
| `reporte` | `uv run python scripts/11_reporte.py` | md -> pdf, conteo de páginas, lint; requiere pandoc y TeX |
| `laminas` / `demo` | `12_laminas.py` / `13_demo.py Q=Q3` o `CONSULTA="texto"` | |
| `test` / `test-lento` | `uv run pytest -q` / `uv run pytest -q -m lento` | Rápidas offline con fixtures |
| `validar` | `uv run python scripts/99_validar.py` | Las 15 condiciones de §13.2 |
| `entrega` | contratos + resultados + reporte + laminas + validar + copia de CSV a la raíz | |
| `all` | alias exacto de `entrega` | Sin pasos extra ni distintos |
| `limpiar` | borra solo artefactos regenerables | Muestra alcance; nunca toca `anotaciones/` ni `data/cache_ner/` |

Reglas de comportamiento:
1. Si faltan juicios, gold o textos humanos (`criterios_*.md`, `valoraciones.yaml`), el objetivo imprime la tarea pendiente y el comando `make app`, y se detiene con código distinto de cero. Nunca genera datos ficticios ni valores por omisión.
2. El reinicio continúa desde los artefactos válidos (dependencias por marca de tiempo y hash); no se reconstruye lo que no cambió.
3. `make resultados` es la ruta sin TeX para que el profesor reproduzca cifras (condición 13); `make entrega` añade PDF y láminas.
4. La tabla objetivo → `uv run python scripts/...` del README se mantiene sincronizada con el Makefile (Windows no trae `make`).

## Manifiesto y reconstrucción desde clon limpio
Referencia: PRD §11.1, D18, §8 (fila de `salida/manifiesto_ejecucion.json` y `salida/tiempos_ejecucion.json`), T16.

`salida/manifiesto_ejecucion.json` contiene: commit del código; hashes del kit, del snapshot del corpus y del orden de IDs; consultas; configuración (`config/*.yaml`); stopwords; gazetteers; muestras; juicios; gold; versión del protocolo; modelo y tokenizador con `revision` fija; dependencias; semillas; esquemas y parámetros. Las marcas de tiempo informan, no identifican: dos corridas con los mismos insumos deben coincidir en todo salvo las marcas de tiempo.

`salida/tiempos_ejecucion.json` registra la duración por script; de ahí salen los tiempos de `docs/reproducibilidad.md` y del README.

Procedimiento de reconstrucción (H9, obligatorio antes de etiquetar):
1. `git clone <remote> /ruta/otra_carpeta && cd /ruta/otra_carpeta` (sin cachés de `uv`, sin `.venv/`, sin `data/*.parquet`).
2. `make setup && make entrega`. Medir el tiempo total y por script; anotarlos en `docs/reproducibilidad.md`.
3. Comparar contra la copia original:
   - igualdad exacta para IDs, textos, etiquetas, spans y conteos (seis CSV, `salida/*.csv`);
   - tolerancia absoluta `1e-8` para puntajes (`puntaje` de `ranking.csv`, métricas);
   - `reporte/reporte.pdf` y `laminas/laminas.pptx` no requieren igualdad byte a byte; sí el conteo de páginas y láminas.
4. Si el hash del corpus no coincide con `data/corpus_meta.json`, el README dice qué hacer (aviso, condición 10) y `docs/reproducibilidad.md` explica cómo recuperar el snapshot.
5. Tiempos: solo los medidos en la laptop del alumno. Nunca se escribe "tarda unos minutos" sin la medición correspondiente.

## README de 10 secciones y sección Uso de IA
Referencia: PRD §11.2 y §11.3. Orden obligatorio; `make validar` lo comprueba (condición 14).

1. Qué hace el sistema (5 líneas) y enlace a `reporte/reporte.pdf`.
2. Requisitos: Python 3.11 y `uv` para cifras; `pandoc` y TeX solo para el PDF. Instrucciones por SO: macOS (`brew install uv pandoc`, `brew install --cask basictex`, `sudo tlmgr install collection-fontsrecommended booktabs`); Windows (`winget install astral-sh.uv`, `winget install JohnMacFarlane.Pandoc`, `winget install MiKTeX.MiKTeX`, tabla de comandos sin `make`); Linux (`curl -LsSf https://astral.sh/uv/install.sh | sh`, `sudo apt install pandoc texlive-xetex texlive-fonts-recommended texlive-latex-extra`).
3. Instalación desde cero: `git clone`, `make setup`, `make contratos`, `make corpus` con tamaño y tiempo medidos de la descarga y qué hacer si el hash no coincide con `data/corpus_meta.json`.
4. Reproducir resultados: `make resultados` (sin TeX) o `make entrega` (con TeX), usando CSV humanos y caché NER versionados.
5. Flujo completo con pasos humanos: `make explorar` → elegir Q9 y Q10 → `make corpus indice ranking pool` → `make app` (juicios) → `make evaluar-ir` → `make reglas` → `make app` (gazetteer) → `make congelar` → `make ner muestra-gold` → `make app` (selección y gold) → `make evaluar-ie tablas` → editar `anotaciones/valoraciones.yaml` → `make reporte laminas`.
6. Mapa del repo (árbol comentado, coherente con PRD §9).
7. Decisiones de diseño (resumen de PRD §4 con enlace a `docs/decisiones.md`) y limitaciones conocidas.
8. Resultados principales: MAP por variante y F1 combinado por tipo, autogenerados por `scripts/11_reporte.py` entre `<!-- resultados:inicio -->` y `<!-- resultados:fin -->`. No se editan a mano.
9. Uso de IA (abajo).
10. Dependencias y por qué: tabla con el papel de cada biblioteca, cuáles están en el enunciado, cuáles son utilerías y la respuesta del profesor sobre ellas.

Sección "Uso de IA" (la redacta el asistente con trazabilidad real):
- [ ] Qué asistente se usó y para qué módulos: lista real de archivos escritos o coescritos (`src/mtx/*.py`, `scripts/*.py`, `tests/*.py`, `Makefile`, etc.), obtenida del historial, no de memoria.
- [ ] Autoría de la prosa: reporte, README y guion redactados por el asistente a partir de resultados reales; el alumno los revisó sección por sección e indicó cuáles modificó de forma sustancial.
- [ ] Qué revisó, modificó o decidió el alumno: Fase 0, criterios de relevancia y anotación, Q9 y Q10, gazetteer, valoraciones, correcciones al reporte.
- [ ] Declaración de juicios, selección y gold hechos a mano en la app, en modo ciego para el gold, sin que el asistente generara ni sugiriera valores: SOLO si ocurrió así. Si no ocurrió así, se describe lo que sí pasó. No se añade una declaración de integridad ficticia para cumplir una plantilla.
- [ ] Cómo se verificó el código generado: pruebas, validadores, lectura del alumno.
- [ ] `docs/guia_defensa.md` generado con 5 líneas por módulo, un ejemplo y las fórmulas clave (idf de BM25, TF-IDF sublineal, coseno, AP, F1); el alumno lo estudia y puede corregirlo.

`AGENTS.md` (PRD §11.4, una página): propósito; "no tocar" (`kit/`, `anotaciones/`, `data/cache_ner/`, `config/criterios_*.md`, `reporte/reporte.md` aprobado); mapa paquete → script → salida; cómo correr pruebas; convenciones; dónde registrar decisiones; tabla de invalidación de §11.1. Referencia el PRD, no lo duplica.

## Commits y etiquetas
Referencia: PRD §11.5.

- Conventional Commits: tipo en inglés, descripción en español. Un commit por unidad probada (código + su prueba verde).
- Tipo `data` para los CSV humanos (`anotaciones/`, `config/criterios_*.md`, `valoraciones.yaml`).
- Ejemplos válidos:
  - `feat(corpus): limpieza de ruido y segmentación con marca reinyectada`
  - `feat(ranking): tf-idf, bm25 y filtro de fecha`
  - `data(juicios): juicios de relevancia Q1-Q10`
  - `test(reglas): casos de fecha y monto`
  - `docs(reporte): borrador completo` / `chore: dependencias`
- Etiquetas:
  1. `reglas-congeladas` sobre el commit que fija reglas, gazetteers y `config/criterios_anotacion.md`, antes de abrir el gold (D15; `make congelar`).
  2. `v1.0-entrega` sobre el commit final, con la hora real registrada en `docs/reproducibilidad.md` y en `docs/decisiones.md` (condición 15). Comprobar que el profesor tiene acceso al remote antes de registrarla.
- No se publica ni se cambia la versión entregada bajo una autorización destinada a otra cosa (por ejemplo, "revisa el documento"). Entre la entrega y la presentación no se cambia código que afecte cifras del reporte (PRD §12).

## make validar: las 15 condiciones de entrega
Referencia: PRD §13.2. `scripts/99_validar.py` imprime cada condición con estado y causa; sale con código distinto de cero si alguna bloqueante falla. Lista de verificación:

1. [ ] Kit sin cambios (hashes de `docs/contratos_kit.md`); Q1-Q8 coinciden con el kit; `data/consultas.csv` tiene Q9 y Q10 del alumno.
2. [ ] Seis CSV en la raíz con columnas y claves exactas de PRD §3.5 (`tests/test_formatos.py`); son exportaciones de `salida/` y `anotaciones/` con la misma versión.
3. [ ] `ranking.csv`: 10 consultas × 4 variantes × 10 rangos (o excepciones justificadas); rangos consecutivos; puntajes finitos; `passage_id` existen en `data/pasajes.parquet`; con filtro, toda `fecha` cae en la ventana.
4. [ ] `juicios_relevancia.csv`: 100 % del pool de cuatro variantes; valores en {0, 1}; nada fuera del pool; hashes vigentes.
5. [ ] `resultados_ir.csv` se regenera con `kit/evaluar.py` y coincide con el versionado; ganador fijado con D08 antes de IE.
6. [ ] `entidades.csv`: `metodo` ∈ {regla, modelo, ambos}; invariante de offsets (`texto == pasaje[inicio:fin]`) en el 100 %; sin duplicados en `(query_id, passage_id, tipo, inicio, fin)`; corresponde al extractor congelado.
7. [ ] `gold_entidades.csv`: 20 IDs distintos del manifiesto, 2 por consulta, todos cerrados, invariante 100 %, todos en el top-10 con filtro del mejor modelo; `gold_seleccion.csv` disjunto si existe; `reglas-congeladas` precede a ambos; `cierre_gold.json` vigente.
8. [ ] `resultados_ie.csv` se regenera con `kit/evaluar.py` y coincide; existe `salida/09_evaluacion_20_ids.csv`; ejemplos de error reales.
9. [ ] `respuestas.csv` y las diez tablas existen; cada valor respaldado cita offsets válidos; `anotaciones/valoraciones.yaml` tiene 10 entradas del alumno.
10. [ ] Hash del corpus coincide con `data/corpus_meta.json` (si no, aviso, no bloqueo).
11. [ ] `reporte/reporte.pdf` entre 4 y 6 páginas; sin bloques de código en el Markdown; `scripts/lint_estilo.py` sin hallazgos.
12. [ ] Entre 1 y 5 láminas; `laminas/guion.md` con tiempo medido ≤ 8 minutos.
13. [ ] `uv run pytest -q` verde; `make resultados` desde clon limpio reproduce las cifras sin TeX.
14. [ ] README con las 10 secciones de §11.2 en orden; `requirements.txt` coherente con `uv.lock`; sección de IA exacta.
15. [ ] Versión entregada identificada (`v1.0-entrega`), acceso del profesor comprobado y hora real registrada.

`tests/test_formatos.py` fija, para cada uno de los seis CSV, el encabezado exacto (PRD §3.5), la unicidad de la clave, los dominios (`tipo`, `metodo`, `relevante`), UTF-8 sin BOM, separador coma y fechas ISO. `ranking.csv` tiene columnas `query_id,modelo,variante,rango,passage_id,doc_id,fecha,posicion,puntaje` y dos claves únicas: `(query_id, modelo, rango)` y `(query_id, modelo, passage_id)`. `entidades.csv` tiene exactamente 8 columnas en el orden `query_id,doc_id,passage_id,tipo,texto,inicio,fin,metodo`. Los `resultados_*.csv` conservan la salida íntegra del evaluador sin renombrar columnas.

Los validadores técnicos no certifican que las decisiones humanas sean correctas (PRD §13.2, U19).

## Lo que nunca se recorta
Referencia: PRD §12, H9 y §13.2. Ante presión de tiempo se recorta lo opcional (comparación de NER, sensibilidad OP, figuras extra), nunca esto:
- Dos rankers (TF-IDF y BM25) con y sin filtro de fecha, y dos enfoques de IE (reglas y modelo) fusionados.
- Limpieza de ruido auditada antes de segmentar (D05).
- Los seis CSV de la raíz con formato exacto.
- Congelamiento con `reglas-congeladas` antes del gold y modo ciego en la anotación.
- README reproducible con tiempos medidos, reporte de 4 a 6 páginas y máximo 5 láminas.

Cualquier recorte se registra en `docs/decisiones.md` con fecha, motivo y efecto, y pasa primero por la skill `integridad-congelacion`.

## Skills relacionadas
- `integridad-congelacion`: antes de tocar juicios, gold, reglas o cifras ya congeladas; tabla de invalidación y recortes de alcance.
- `kit-contratos`: hito H0, `make contratos`, hashes del kit y `docs/contratos_kit.md` (condición 1).
- `reporte-pdf`: `make reporte`, conteo de páginas, lint de estilo y resultados autogenerados del README (condiciones 11 y 14).
- `laminas-demo`: `make laminas` y `make demo`, guion con tiempo medido (condición 12).
- `session-resume`: estado del repo y hito actual al retomar una sesión antes de correr `make entrega`.

## v2: entrega final (PRD v2 §4, §9; WP-14)

- Etiquetas: `v2-inicio` (aprobación del PRD v2), `reglas-fecha-v2` y `v2.0-entrega` el martes
  24; la entrega es el miércoles 25 antes de las 18:00. `v1.0-entrega` no se mueve.
- `make all-v2` reconstruye todo lo v2 desde un clon limpio; `make validar` agrega condiciones v2
  (3 juicios por par, cierres, tiempo medido entre 15:00 y 20:00, láminas sin rutas).
- README: equipo de 6 con "Leo Yahir", cifras v2, enlace a la demo web y "Uso de IA" actualizado.
- Integración en `proyecto-final`; `main` no se toca hasta el merge final. Ramas `v2/wpXX-*` y
  `anotacion/<anotador>` desde `proyecto-final`, pull request a ella; Diego integra.
