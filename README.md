# Sistema de recuperación y extracción de información sobre discursos presidenciales

Proyecto final v2 · Equipo Datisa: Carpio Angeles Leo Yahir, Jaramillo Salmerón Arturo, Mera
Montiel Gonzalo Sebastian, Moctezuma Ramirez Diego Rafael y Ramirez Maza Luis.

Repositorio: https://github.com/DiegoMoctezuma/Examen_Mineria_Textos (etiquetas `v1.0-entrega`
para el examen y `v2.0-entrega` para el proyecto final).

Demo web pública: https://datisa.streamlit.app (datos v2; la primera carga tarda si la app estaba
dormida).

## 1. Qué hace el sistema

Sobre 2,294 versiones estenográficas de conferencias presidenciales (2018 a 2024), el sistema
parte cada discurso en 127,739 pasajes, construye un índice invertido propio y recupera los 10
pasajes más relevantes para cada una de 15 consultas (Q1 a Q10 del examen y Q11 a Q15 del proyecto
final) con TF-IDF y BM25, con y sin filtro de fecha, y con dos preprocesamientos (raíz con el
stemmer Snowball y lema con spaCy). Sobre esos pasajes extrae entidades PER, ORG, LOC, FECHA y
MONTO combinando reglas con gazetteer y un NER preentrenado, las evalúa contra un gold anotado a
mano y arma tablas de respuesta con evidencia textual.

- Reporte v2: [`reporte/reporte_v2.pdf`](reporte/reporte_v2.pdf) (el del examen sigue en
  [`reporte/reporte.pdf`](reporte/reporte.pdf)).
- Presentación final: [`laminas/v2/Presentacion_Datisa_v2.html`](laminas/v2/Presentacion_Datisa_v2.html)
  (archivo único, funciona sin red; abrir en Chrome o Edge) y su PDF
  [`laminas/v2/Presentacion_v2.pdf`](laminas/v2/Presentacion_v2.pdf). Guion en
  [`laminas/guion_v2.md`](laminas/guion_v2.md).

## 2. Requisitos

Python 3.11 y [`uv`](https://docs.astral.sh/uv/) para reproducir las cifras; `uv` instala también
el modelo de spaCy `es_core_news_md`. Para el PDF: `pandoc` y Chrome (lo instala `make setup` para
kaleido). El PRD pide XeLaTeX; como no estaba disponible en todas las máquinas, el PDF se imprime
con Chrome sin ventana desde el HTML de pandoc (ruta documentada en `docs/decisiones.md`).

| SO | Instalación |
| --- | --- |
| macOS | `brew install uv pandoc` |
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` y `sudo apt install pandoc` |
| Windows | `winget install astral-sh.uv` y `winget install JohnMacFarlane.Pandoc`; sin `make`, correr `uv run python scripts/NN_*.py` en el orden de la sección 5 |

La presentación HTML no necesita instalar nada. Para regenerarla, ver `laminas/v2/LEEME.txt`.

`requirements.txt` se exporta de `uv.lock` (`uv export --no-dev --format requirements-txt`) para
quien use `pip install -r requirements.txt`.

## 3. Instalación desde cero

```bash
git clone https://github.com/DiegoMoctezuma/Examen_Mineria_Textos.git text-mining-ir-er
cd text-mining-ir-er
make setup      # uv sync, stopwords de NLTK y Chrome para kaleido
make contratos  # pruebas de contrato del kit del profesor (kit/ no se modifica)
make corpus     # descarga carevies/discursos_AMLO, limpia y segmenta: data/pasajes.parquet
```

`make corpus` compara el hash del snapshot con `data/corpus_meta.json`; si no coincide, avisa y
el resto de las cifras deja de ser comparable con el reporte (el dataset cambió en Hugging Face).

## 4. Reproducir resultados

```bash
make indice indice-lema    # índices con raíz y con lema (la lematización tarda unos 16 min)
make all-v2                # ranking, juicios agregados, evaluación IR e IE, tablas, figuras y raíz
make validar               # 22 condiciones de entrega (incluye pytest)
make reporte-v2            # reporte/reporte_v2.md → reporte/reporte_v2.pdf
make demo Q=Q3             # demo en terminal; también CONSULTA="..." DESDE=AAAA-MM-DD HASTA=...
make demo-web              # la demo web en local, http://localhost:8502
```

Los juicios, el gold, la revisión de siglas y las valoraciones viven en `anotaciones/` y la caché
del NER en `data/cache_ner/`, ambos versionados: `make all-v2` no descarga modelos ni pide anotar
nada. Desde un clon limpio la cadena completa tardó 18 min 33 s y dejó los seis CSV de la raíz,
`salida/v2/` y las figuras idénticos byte a byte a los versionados (`docs/reproducibilidad.md`).

La raíz tiene los seis CSV de v2 (D28). v1 no se perdió: sus CSV siguen en `salida/` y
`anotaciones/`, y se reproduce desde su etiqueta (`git worktree add ../v1 v1.0-entrega`); los
objetivos de v1 que escriben en la raíz (`make ranking`, `make evaluar-ir`, `make extraer`,
`make evaluar-ie`) se niegan a correr.

## 5. Flujo completo con pasos humanos

`make explorar-v2` → el equipo elige Q11 a Q15 → `make corpus indice indice-lema ranking-v2 pool-v2`
→ `make app` (juicios, 3 jueces por par, humanos) → `make cierre-juicios-v2` → reglas FECHA v2
con la etiqueta `reglas-fecha-v2` → `make muestra-gold-v2` → `make app` (gold en modo ciego, 2
anotadores por parte y un tercero que adjudica, humanos) → `make fijar-ner-v2` → `make cierre-gold-v2`
→ `make all-v2` → `make app` (valoraciones, humano) → `make tablas-v2 reporte-v2`.

## 6. Mapa del repositorio

```text
kit/            kit del profesor, sin modificar (hashes en docs/contratos_kit.md)
config/         consultas, stoplist, gazetteers, NER, criterios, mapa de tablas; config/v2/ lo de v2
src/mtx/        paquete: corpus, preproceso, indice, ranking, pool, evaluacion, reglas,
                ner_modelo, fusion, normalizacion, muestreo, gold, evaluacion_ie, respuestas,
                figuras_v2, promocion, entrega; app/ es la app de anotación y web/ la demo web
scripts/        00 a 14b y 99: un script por paso del pipeline (los llama el Makefile)
anotaciones/    insumos humanos: juicios, revisión de siglas, gold, valoraciones (solo la app escribe)
data/           pasajes, índices, caché NER, mejor modelo, modelo NER
salida/         todo lo calculado de v1; salida/v2/ lo de v2, con figuras/
reporte/        reporte.md (v1), reporte_v2.md, figuras y PDF
laminas/        guion v1 y v2, decks PowerPoint y v2/ con la presentación HTML final
docs/           decisiones, contratos del kit, reproducibilidad, guías de defensa, revisión ciega
tests/          pytest sin red (743 pruebas)
```

Los seis CSV de entrega están en la raíz: `ranking.csv`, `juicios_relevancia.csv`,
`resultados_ir.csv`, `entidades.csv`, `gold_entidades.csv` y `resultados_ie.csv`.

## 7. Decisiones de diseño y limitaciones

Registro completo con fecha en [`docs/decisiones.md`](docs/decisiones.md). Las principales:
pasajes por intervención en ventanas de 200 palabras con paso 150 y mínimo 40 (D02); la marca de
interlocutor se reinyecta al texto para extraer, pero no se indexa (D03); relevancia juzgada por
tema, con la ventana aplicada después (D07); NER elegido por criterio técnico antes del gold (D09);
fusión por span exacto (D12); porcentajes y cantidades fuera de MONTO (D11). En v2: relevancia por
mayoría de 3 jueces (D24); ganador por MAP entre las 4 variantes con filtro (D28); gold de 34
pasajes, con las partes nuevas anotadas por dos personas en modo ciego y adjudicadas por un
tercero (D31); NER elegido sobre un conjunto de selección antes del cierre del gold (D34).

Limitaciones: el acuerdo entre jueces es moderado (κ de Fleiss 0.4753); el gold v2 tiene poco
soporte en FECHA (8) y MONTO (12); el lema no supera a la raíz (MAP 0.5070 contra 0.5356); el NER
v2 no cabe en la nube gratuita, así que la consulta libre de la demo web usa solo reglas; algunos
patrones de las tablas de respuesta dejan pasar valores sin la relación pedida.

## 8. Resultados principales

<!-- resultados:inicio -->

### Recuperación de información (IR), v2

MAP de las 8 variantes sobre las 15 consultas (`salida/v2/05_ir_8_variantes.csv`; juicios
agregados por mayoría de 3, 320 pares). Ganador: BM25 con raíz y filtro
(`data/v2/mejor_modelo.json`); es el que lleva `resultados_ir.csv` de la raíz.

| Variante | Raíz | Lema |
| --- | ---: | ---: |
| TF-IDF sin filtro | 0.3313 | 0.3371 |
| TF-IDF con filtro | 0.3521 | 0.3493 |
| BM25 sin filtro | 0.5274 | 0.5153 |
| BM25 con filtro | **0.5356** | 0.5070 |

En v1 (10 consultas, juicios de una persona; `salida/resultados_ir.csv`) el mejor fue BM25 con
filtro, MAP 0.484.

### Selección del modelo NER

Davlan XLM-R large obtuvo F1 micro exacto 0.678 en el conjunto de selección v2 (10 pasajes,
`data/modelo_ner.json`). Es la cifra para elegir el modelo, no la evaluación final del extractor.

### Evaluación de extracción (IE), v2

Gold v2 de 34 pasajes (`resultados_ie.csv` de la raíz, copia de `salida/v2/resultados_ie.csv`):

| Tipo | Precisión | Recall | F1 combinado |
| --- | ---: | ---: | ---: |
| PER | 0.9000 | 1.0000 | 0.9474 |
| ORG | 0.6806 | 0.8033 | 0.7368 |
| LOC | 0.8425 | 0.8699 | 0.8560 |
| FECHA | 0.5714 | 0.5000 | 0.5333 |
| MONTO | 0.8333 | 0.8333 | 0.8333 |
| TODOS | 0.7984 | 0.8583 | **0.8273** |

Referencias (`salida/v2/09_referencias_f1.csv`): IC95 del F1 combinado de 0.7714 a 0.8818; techo
humano (acuerdo entre los dos anotadores antes de adjudicar) 0.8533; línea base solo con gazetteer
0.6543; con coincidencia parcial, 0.9259. En v1 (gold de 20 pasajes, `salida/resultados_ie.csv`)
el F1 combinado fue 0.784.

<!-- resultados:fin -->

## 9. Uso de IA

- **Claude Code** escribió el código, las pruebas, la app de anotación, la demo web y las figuras,
  y los borradores del reporte, el guion y la guía de defensa, a partir de las especificaciones y
  decisiones del equipo. El equipo revisó esos materiales, las decisiones metodológicas y la
  interpretación de resultados.
- Claude Code propuso 12 consultas candidatas (`config/v2/candidatos_q11q15.yaml`); Diego y Arturo
  eligieron y redactaron Q11 a Q15.
- **Codex** hizo la presentación HTML final (`laminas/v2/`) a partir del deck de Arturo, sin cambiar
  su texto ni sus cifras, y unificó la paleta de las figuras. Las ilustraciones de P11 a P15 se
  generaron con el generador de imágenes de Codex (prompts en
  `laminas/v2/img/generacion_p11_p15.json`); las de P1 a P10 son las del deck del examen.
- **Gemini** hizo la revisión ciega del deck (Arturo); qué se tomó y qué no está en
  `docs/revision_ciega_respuesta.md`.
- Ningún insumo humano lo produjo ni lo sugirió una IA: los 960 juicios de relevancia v2 (320 pares
  con 3 juicios), la selección de Q11 a Q15, el gold y sus adjudicaciones (en modo ciego, sin
  predicciones a la vista hasta el cierre), la revisión de siglas y las 15 valoraciones v2 (Luis)
  se hicieron a mano en la app leyendo cada pasaje.
- Verificación: 743 pruebas de pytest sin red (contratos del kit, fórmulas de TF-IDF y BM25 contra
  implementaciones de referencia, reglas, fusión, app y demo web), validadores de formato de cada
  CSV y `make validar` con 22 condiciones.
- En v1, Diego consultó a Gemini como tutor para dudas de criterio durante el gold y las
  valoraciones, con indicaciones de no redactar anotaciones ni valoraciones.
- Para la defensa el equipo debe poder explicar cualquier función del paquete; la guía está en
  [`docs/guia_defensa_v2.md`](docs/guia_defensa_v2.md).

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
| spacy, es-core-news-md | lematización (variante lema de v2) | utilería |
| pyarrow | pasajes en Parquet | utilería |
| streamlit | app local de anotación, sin sugerencias, y demo web | utilería |
| plotly, kaleido | figuras PNG (el profesor pidió no usar matplotlib) | utilería |
| pypdf | contar páginas del PDF | utilería |
| python-pptx | láminas | utilería |
| pyyaml, rich | configuración y demo en terminal | utilería |
| pytest, ruff (desarrollo) | pruebas y estilo | utilería |

El equipo consultó al profesor por las utilerías (mensaje en `docs/mensaje_profesor_utilerias.md`);
la respuesta fue que todas estaban bien excepto matplotlib, por eso las figuras usan plotly. El
índice invertido y BM25 están escritos a mano.
