# Sistema de recuperación y extracción de información sobre discursos presidenciales

Examen 1 de Minería de Textos · Diego Moctezuma.

## 1. Qué hace el sistema

Sobre 2,294 versiones estenográficas de conferencias presidenciales (2018 a 2024), el sistema
parte cada discurso en pasajes, construye un índice invertido propio y recupera los 10 pasajes
más relevantes por consulta con TF-IDF y BM25, con y sin filtro de fecha. Sobre esos pasajes
extrae entidades PER, ORG, LOC, FECHA y MONTO combinando reglas con gazetteer y un NER
preentrenado, las evalúa contra un gold anotado a mano y arma tablas de respuesta con evidencia
textual. Reporte: [`reporte/reporte.pdf`](reporte/reporte.pdf).

## 2. Requisitos

Python 3.11 y [`uv`](https://docs.astral.sh/uv/) para reproducir las cifras. Para el PDF:
`pandoc` y Chrome (lo instala `make setup` para kaleido). El PRD pide XeLaTeX; como no estaba
disponible, el PDF se imprime con Chrome sin ventana desde el HTML de pandoc (ruta documentada en
`docs/decisiones.md`).

| SO | Instalación |
| --- | --- |
| macOS | `brew install uv pandoc` |
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` y `sudo apt install pandoc` |
| Windows | `winget install astral-sh.uv` y `winget install JohnMacFarlane.Pandoc`; sin `make`, correr `uv run python scripts/NN_*.py` en el orden de la sección 5 |

Para regenerar las láminas (`make laminas`): Node 20 y `npm install` dentro de `laminas/deck/`.

`requirements.txt` se exporta de `uv.lock` (`uv export --no-dev --format requirements-txt`) para
quien use `pip install -r requirements.txt`.

## 3. Instalación desde cero

```bash
git clone <url-del-repositorio> && cd text-mining-ir-er
make setup      # uv sync, stopwords de NLTK y Chrome para kaleido
make contratos  # pruebas de contrato del kit del profesor (kit/ no se modifica)
make corpus     # descarga carevies/discursos_AMLO, limpia y segmenta: data/pasajes.parquet
```

`make corpus` compara el hash del snapshot con `data/corpus_meta.json`; si no coincide, avisa y
el resto de las cifras deja de ser comparable con el reporte (el dataset cambió en Hugging Face).
Tiempos medidos en `docs/reproducibilidad.md`.

## 4. Reproducir resultados

```bash
make indice ranking pool   # índice, ranking.csv y pool
make resultados            # evaluar-ir, evaluar-ie y tablas con los insumos humanos versionados
make reporte               # tablas del reporte, sección 8 de este README y reporte.pdf
make validar               # 15 condiciones de entrega
make demo Q=Q3             # demo en terminal; también CONSULTA="..." DESDE=AAAA-MM-DD HASTA=...
```

Los juicios, el gold, la revisión de siglas y las valoraciones viven en `anotaciones/` y la caché
del NER en `data/cache_ner/`, ambos versionados: `make resultados` no descarga modelos ni pide
anotar nada.

## 5. Flujo completo con pasos humanos

`make explorar` → el alumno elige Q9 y Q10 → `make corpus indice ranking pool` → `make app`
(juicios, humano) → `make evaluar-ir` → `make reglas` → `make app` (revisión de siglas, humano)
→ `make congelar` → `make ner muestra-gold` → `make app` (gold en modo ciego, humano) →
`make extraer evaluar-ie tablas` → `make app` (valoraciones, humano) → `make reporte laminas`.

## 6. Mapa del repositorio

```text
kit/            kit del profesor, sin modificar (hashes en docs/contratos_kit.md)
config/         consultas Q9-Q10, stoplist, gazetteers, NER, criterios del alumno, mapa de tablas
src/mtx/        paquete: corpus, preproceso, indice, ranking, pool, evaluacion, reglas,
                ner_modelo, fusion, normalizacion, muestreo, gold, evaluacion_ie, respuestas,
                manifiesto, entrega; app/ es la app Streamlit de anotación
scripts/        00 a 13 y 99: un script por paso del pipeline (los llama el Makefile)
anotaciones/    insumos humanos: juicios, revisión de siglas, gold, valoraciones (solo la app escribe)
data/           pasajes, índice, caché NER, mejor modelo, modelo NER
salida/         todo lo calculado; manifiesto_ejecucion.json con hashes y versiones
reporte/        reporte.md, figuras y reporte.pdf
laminas/        láminas, guion y salida guardada de la demo
docs/           decisiones, contratos del kit, reproducibilidad, guía de defensa
tests/          pytest sin red (433 pruebas)
```

Los seis CSV de entrega están en la raíz: `ranking.csv`, `juicios_relevancia.csv`,
`resultados_ir.csv`, `entidades.csv`, `gold_entidades.csv` y `resultados_ie.csv`.

## 7. Decisiones de diseño y limitaciones

Registro completo con fecha en [`docs/decisiones.md`](docs/decisiones.md). Las principales:
pasajes por intervención en ventanas de 200 palabras con paso 150 y mínimo 40 (D02); la marca de
interlocutor se reinyecta al texto para extraer, pero no se indexa (D03); reporteros indexados
como cualquier intervención (D04); relevancia juzgada por tema, con la ventana aplicada después
(D07); el mejor modelo por MAP define el ámbito de la extracción (D08); NER elegido por criterio
técnico antes del gold (D09); reglas congeladas con la etiqueta `reglas-congeladas` antes del gold
(D15); fusión por span exacto (D12); porcentajes y cantidades fuera de MONTO (D11).

Limitaciones: el 64.94 % de las intervenciones de reporteros se descarta por cortas; el gold
tiene 20 pasajes y poco soporte en FECHA (6) y MONTO (3); no hubo conjunto de selección para
comparar modelos NER; el NER fragmenta nombres en mayúsculas dentro de la marca; algunos patrones
de las tablas de respuesta dejan pasar valores sin la relación pedida.

## 8. Resultados principales

<!-- resultados:inicio -->
MAP por variante (`resultados_ir.csv`, relevancia temática):

| Variante | MAP |
| --- | --- |
| TF-IDF sin filtro | 0.287 |
| TF-IDF con filtro | 0.295 |
| BM25 sin filtro | 0.469 |
| BM25 con filtro | 0.484 |

F1 del método combinado por tipo (`resultados_ie.csv`, 20 pasajes gold):

| Tipo | F1 |
| --- | --- |
| PER | 0.679 |
| ORG | 0.725 |
| LOC | 0.854 |
| FECHA | 0.364 |
| MONTO | 1.000 |
| TODOS | 0.784 |
<!-- resultados:fin -->

## 9. Uso de IA

- Asistente: Claude Code (modelo Claude Opus 5.5). Escribió o coescribió todo el código de
  `src/mtx/`, `scripts/`, `tests/`, la app de anotación, el `Makefile`, los documentos de `docs/`,
  este README, el reporte, las láminas y el guion, a partir de los resultados reales y del PRD.
- Autoría de la prosa: el reporte, el README y el guion los redactó el asistente; el alumno los
  revisó y corrigió. [VALIDAR alumno: indicar qué secciones modificó de forma sustancial.]
- Decisiones y trabajo del alumno: fase 0 (plazos, repositorio, utilerías con el profesor),
  criterios de relevancia y de anotación, elección de Q9 y Q10, los 176 juicios de relevancia,
  la revisión de las 104 siglas candidatas, el gold de 20 pasajes y sus convenciones para casos no
  previstos, y las 10 valoraciones de las tablas.
- El alumno consultó a Gemini como tutor para dudas de criterio durante el gold y las
  valoraciones, con indicaciones de no redactar anotaciones ni valoraciones.
- Los juicios de relevancia y el gold se hicieron a mano en la app leyendo cada pasaje, en modo
  ciego para el gold (sin predicciones visibles hasta el cierre); el asistente no generó ni sugirió
  ninguno de esos valores. Lo mismo vale para la revisión de siglas y las valoraciones.
- Verificación del código: 433 pruebas de pytest sin red (contratos del kit, fórmulas de TF-IDF y
  BM25 contra implementaciones de referencia, reglas, fusión, app), validadores de formato de cada
  CSV y `make validar` con 15 condiciones; el alumno leyó el código para la defensa.
- Para la demo el alumno debe poder explicar cualquier función del paquete; la guía está en
  [`docs/guia_defensa.md`](docs/guia_defensa.md).

## 10. Dependencias y por qué

| Biblioteca | Papel | Origen |
| --- | --- | --- |
| pandas, numpy | tablas y vectores | enunciado |
| scikit-learn | TF-IDF (`TfidfVectorizer`) | enunciado |
| nltk | stopwords y stemmer Snowball | enunciado |
| regex | expresiones de FECHA y MONTO | enunciado |
| datasets | descarga del corpus | enunciado |
| transformers, torch (CPU) | NER preentrenado | enunciado; torch lo exige transformers |
| rank_bm25 (desarrollo) | comparar el BM25 propio en pruebas | enunciado |
| pyarrow | pasajes en Parquet | utilería |
| streamlit | app local de anotación, sin sugerencias | utilería |
| plotly, kaleido | figuras PNG (el profesor pidió no usar matplotlib) | utilería |
| pypdf | contar páginas del PDF | utilería |
| python-pptx | láminas | utilería |
| pyyaml, rich | configuración y demo en terminal | utilería |
| pytest, ruff (desarrollo) | pruebas y estilo | utilería |

El alumno consultó al profesor por las utilerías (mensaje en `docs/mensaje_profesor_utilerias.md`);
la respuesta fue que todas estaban bien excepto matplotlib, por eso las figuras usan plotly. El
índice invertido y BM25 están escritos a mano.
