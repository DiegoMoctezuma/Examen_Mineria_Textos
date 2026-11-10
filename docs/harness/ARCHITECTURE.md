# Arquitectura · Sistema de recuperación y extracción de información sobre discursos presidenciales

Mapa de cómo se relacionan las piezas del sistema descrito en
`PRD_unificado_examen1_mineria_textos.md` (v3.0, 4 de noviembre de 2026). No
resume el PRD: señala componentes, flujos de datos, fronteras y las decisiones
que restringen el diseño. Cuando el código y este mapa discrepen, corrige el
mapa como parte del trabajo (ver skill `system-onboarding`).

## 1. Vista de conjunto

Dos tareas encadenadas sobre un corpus de 2,294 versiones estenográficas
(`carevies/discursos_AMLO`, 2018 a 2024):

```
corpus HF ──► limpieza ──► pasajes ──► tokens ──► índice ──► rankings (4 variantes)
                                                                  │
                                              pool ◄──────────────┘
                                                │
                                   juicios (HUMANO) ──► evaluar.py ir ──► resultados_ir.csv
                                                                              │
                                                              mejor_modelo.json (D08)
                                                                              │
                              top-10 con filtro del ganador (≤100 pasajes únicos)
                                   │                      │
                        reglas + gazetteers          NER (HF, caché)
                                   └──────► fusión ◄──────┘
                                                │
                     muestra gold (semilla 42) ──► gold (HUMANO, ciego) ──► evaluar.py ie ──► resultados_ie.csv
                                                │
                                  tablas de respuesta con evidencia ──► valoraciones (HUMANO)
                                                │
                                   reporte.pdf · láminas · demo · README
```

La unidad de recuperación es el **pasaje** (no el discurso). Cada pasaje
conserva `doc_id`, `fecha`, `posicion` y un `texto` inmutable que es la única
fuente de verdad para los offsets de entidades.

## 2. Componentes

### 2.1 Paquete `src/mtx/` (lógica) y `scripts/` (orquestación)

Regla estructural del PRD: la lógica vive en el paquete; los scripts numerados
solo importan y orquestan. Cada script produce artefactos con prefijo numérico
en `salida/` o `data/`.

| Módulo | Responsabilidad | Script | Entradas principales | Salidas principales |
| --- | --- | --- | --- | --- |
| `config.py` | Rutas, constantes, semillas, carga de `config/*.yaml` | todos | `config/proyecto.yaml`, `ranking.yaml`, `ner.yaml`, `limpieza.yaml` | — |
| `contratos.py` | Esquemas de los CSV, validadores de columnas y claves | 99 | — | errores de validación |
| `adaptadores_kit.py` | **Único punto de contacto con `kit/`** | 01, 05, 09 | `kit/corpus.py`, `kit/evaluar.py` | envoltorios |
| `corpus.py` | Carga, limpieza de ruido y canonización de marcas (D05), reparación de fechas, duplicados, segmentación propia (D02-D04) | 01 | corpus HF vía kit, `config/limpieza.yaml` | `data/pasajes.parquet`, `data/corpus_meta.json`, `salida/01_*` |
| `consultas.py` | `data/consultas.csv` = kit literal + Q9 + Q10 | 00b | `kit/consultas.csv`, `config/consultas_q9q10.yaml` | `data/consultas.csv` |
| `descubrimiento.py` | Señal de candidatos para Q9 y Q10 (no elige) | 00 | `pasajes.parquet`, `config/candidatos_q9q10.yaml` | `salida/00_candidatos_q9q10.md` |
| `preproceso.py` | Tokenizador, stoplist, stemmer | 02 | `pasajes.parquet`, `config/stop*.txt` | `data/tokens.parquet` |
| `indice.py` | Índice invertido a mano, postings, persistencia | 02 | `tokens.parquet` | `data/indice.pkl`, `indice_meta.json`, `salida/02_*` |
| `ranking.py` | TF-IDF (sklearn), BM25 propio, filtro de fecha, top-k, `buscar()` | 03 | índice, `data/consultas.csv` | `salida/ranking.csv` → `ranking.csv`, `salida/03_*` |
| `pool.py` | Pool de relevancia (D06), `validar_juicios()` | 04, 99 | `ranking.csv` | `salida/04_pool.csv`; valida `anotaciones/juicios_relevancia.csv` |
| `evaluacion.py` | Envoltorio de `evaluar.py ir`, vista con ventana, mejor modelo | 05 | juicios, ranking | `resultados_ir.csv`, `salida/05_*`, `data/mejor_modelo.json` |
| `evaluacion_ie.py` | Detalle IE verificado contra el kit, complementaria de 20 IDs, análisis de errores, alertas U19, figuras IE | 09 | gold, entidades | `resultados_ie.csv` (vía kit), `salida/09_*` |
| `muestreo.py` | Muestra gold y conjunto de selección con emparejamiento global | 08b | `ranking.csv`, `mejor_modelo.json` | `anotaciones/muestra_gold.csv`, `muestra_seleccion.csv` |
| `reglas.py` | Regex FECHA y MONTO, cantidades auxiliares, gazetteers, regla de marca, colisiones | 06 | `texto` canónico, `kit/gazetteer_dependencias.csv`, `config/gazetteer_*.csv` | `salida/06_*`, `salida/cantidades_auxiliares.csv` |
| `ner_modelo.py` | Pipeline HF, chunking, caché versionada, posproceso de spans | 07 | pasajes del top-10 del ganador, `config/ner.yaml` | `data/cache_ner/`, `salida/07_uniones_spans.csv` |
| `fusion.py` | Fusión reglas + modelo por span exacto (D12) | 08 | salidas de 06 y 07 | `entidades.csv`, `salida/entidades_unicas.csv`, `entidades_enriquecidas.csv` |
| `normalizacion.py` | `fecha_iso`, `valor_num`, moneda, canónicos (sin tocar spans) | 08 | entidades | columnas de `entidades_enriquecidas.csv` |
| `respuestas.py` | Tablas de respuesta con evidencia y estados (D17) | 10 | `entidades_enriquecidas.csv`, `cantidades_auxiliares.csv`, `config/tablas_respuesta.yaml` | `salida/respuestas.csv`, `salida/tablas_respuesta/*.md` |
| `manifiesto.py` | Manifiesto de ejecución y tiempos (hashes de entradas y salidas, commit) | 08, 09 | artefactos de cada script | `salida/manifiesto_ejecucion.json`, `tiempos_ejecucion.json` |
| `reporte.py` | Tablas y figuras del reporte | 11 | `salida/`, `anotaciones/valoraciones.yaml` | `reporte/figuras/`, `reporte/tablas/`, sección de resultados del README |
| `laminas.py` (P2) | Generación del pptx | 12 | figuras | `laminas/laminas.pptx` |
| `demo.py` | Demo en terminal con `rich`, sin red | 13 | artefactos cacheados | salida en terminal |
| `app/` | Streamlit: Estado, Juicios, Gold, Gazetteer, Demo (P2) | `make app` | pool, muestras, siglas candidatas | todo lo que vive en `anotaciones/` y `config/gazetteer_extendido.csv` |

### 2.2 Zonas del repositorio por quién las produce y quién las puede tocar

| Zona | Productor | ¿La toca el asistente? | Notas |
| --- | --- | --- | --- |
| `kit/` | Profesor | **Nunca** | Hashes SHA-256 en `docs/contratos_kit.md`; adaptaciones en `adaptadores_kit.py` |
| `anotaciones/` | **Alumno** (vía app) | Solo la herramienta que escribe ahí; nunca el contenido | Juicios, muestras, gold, `cierre_gold.json`, `valoraciones.yaml`. Versionada y protegida (U20) |
| `config/criterios_relevancia.md`, `config/criterios_anotacion.md` | **Alumno** | No; el asistente puede proponer, el alumno fija | Se congelan antes del primer juicio / antes del gold |
| `config/gazetteer_extendido.csv` | Asistente mina, **alumno revisa** | Solo la minería y el formato | `[VALIDAR]` |
| `config/` (resto) | Asistente | Sí | Parámetros citables por el reporte |
| `data/` | Scripts | Sí (regenerable) | Parquet/pkl/npz ignorados por git; JSON de decisiones y `cache_ner/` versionados |
| `salida/` | Scripts | Sí (regenerable) | Se versiona completo; toda cifra del reporte sale de aquí |
| Seis CSV en la raíz | Exportación validada de `salida/` y `anotaciones/` | Solo vía `make validar`/`entrega` | `ranking`, `juicios_relevancia`, `resultados_ir`, `entidades`, `gold_entidades`, `resultados_ie` |
| `reporte/reporte.md` | Asistente redacta, **alumno aprueba** sección por sección | Sí hasta aprobación; después no se regenera | D21 |
| `docs/decisiones.md` | Ambos | Sí | Registro con fecha de cada decisión y cambio post-congelación |

## 3. Flujos de datos y contratos entre componentes

### 3.1 Texto, offsets y la marca de interlocutor (D03)

El corpus real (verificado en H1) trae marcas `~~~ETIQUETA texto` y `NOMBRE, CARGO: texto` en
línea, casi sin saltos de línea; la expresión del kit no reconoce ninguna. `limpiar_ruido()` las
canoniza a una intervención por línea (`texto_canonico`) y `partir_canonico()` las separa;
`ventanas()` sí viene del kit. Ver `docs/decisiones.md`.

El contrato más delicado del sistema. Un pasaje es `f"{quien}: {trozo}"`:

- `texto[:inicio_cuerpo]` es la marca (`SECRETARIO DE SALUD, JORGE ALCOCER VARELA: `).
- `texto[inicio_cuerpo:]` es el cuerpo (`trozo`).
- **IR** indexa solo el cuerpo (`tokenizar_pasaje(texto, inicio_cuerpo)`): la marca repetida en cada ventana inflaría tf de "secretario", "salud", "presidente".
- **IE** trabaja sobre el `texto` completo, marca incluida: es fuente de PER y ORG y permite medir el efecto de las mayúsculas.
- Los offsets de toda entidad son índices de carácter Python sobre ese `texto`, `inicio` inclusivo y `fin` exclusivo; invariante `texto[inicio:fin] == texto_entidad` verificado en tests, validadores y app. Ningún preprocesamiento de IR altera el texto.

### 3.2 Cadena IR

1. `corpus.py` produce `pasajes.parquet` determinista (hash de filas ordenadas).
2. `preproceso.py` produce `tokens.parquet`; su configuración (stoplists con hash) queda congelada.
3. `indice.py` ajusta el índice **una sola vez** sobre todos los pasajes. Filtrar por fecha no recalcula N, df, idf ni avgdl.
4. `ranking.py` produce las 4 variantes (`tfidf|bm25` × `con|sin_filtro`), 10 filas por consulta, desempate `(-puntaje, doc_id, posicion)`.
5. `pool.py` une los 4 top-10 (≤40 por consulta) y lo congela junto con corpus, consultas, configuración y rankings.
6. La app recoge juicios ciegos al modelo; `validar_juicios()` exige cobertura 100 % del pool.
7. `evaluacion.py` llama a `kit/evaluar.py ir` (cifra oficial) y produce la vista con ventana (complementaria, nunca sustituye).
8. `mejor_modelo.json`: argmax MAP entre las dos variantes con filtro, empate a BM25. **Es la bisagra entre IR e IE.**

### 3.3 Cadena IE

Todo opera solo sobre los pasajes únicos del top-10 con filtro del ganador (≤100), nunca sobre el corpus completo.

1. `reglas.py` extrae sobre texto canónico; colisiones resueltas por span más largo y luego jerarquía `regex_fecha > regex_monto > gazetteer_loc > gazetteer_org > marca`. Al terminar: `make congelar` → etiqueta `reglas-congeladas` (D15).
2. `ner_modelo.py` infiere con caché `data/cache_ner/{modelo}@{rev}/{passage_id}.json` versionada en git; la inferencia puede correr antes del cierre del gold siempre que permanezca oculta al anotador.
3. `muestreo.py` sortea 20 IDs únicos (2 por consulta, emparejamiento global) y, si aplica, 6 de selección disjuntos. El manifiesto se congela con hashes de texto **antes** de mostrar predicciones.
4. El alumno anota en modo ciego; `cierre_gold.json` levanta el modo ciego.
5. Si hay conjunto de selección: comparar candidatos NER sobre él → `modelo_ner.json` **antes** de tocar `gold_entidades.csv`.
6. `fusion.py` emite `entidades.csv` (8 columnas exactas) con `metodo ∈ {regla, modelo, ambos}`; solapes parciales se conservan y cuantifican.
7. `evaluacion.py` llama a `kit/evaluar.py ie` (cifra oficial), produce la complementaria de 20 IDs y el análisis de errores por categorías.

### 3.4 Cadena de respuesta y documentos

1. `respuestas.py` filtra entidades en la marca y variantes del nombre del presidente (U14), aplica el mapa consulta → campos de `config/tablas_respuesta.yaml`, busca evidencia de relación en ±60 caracteres y emite `respuestas.csv` con estados `respaldado_en_texto | ambiguo | contradictorio | no_encontrado`.
2. El alumno escribe `anotaciones/valoraciones.yaml` (10 entradas).
3. `reporte.py` genera tablas y figuras desde `salida/`; la prosa se redacta en tres cortes `[VALIDAR]` y una vez aprobada no se regenera.
4. `demo.py` lee solo artefactos cacheados; una consulta libre ejecuta NER en caliente y lo avisa.

## 4. Decisiones del PRD que restringen el diseño

| Decisión | Efecto arquitectónico |
| --- | --- |
| EX: dos modelos de ranking y dos enfoques de IE, o se pierde el rubro completo | `ranking.py` y `fusion.py` tienen criterios de aceptación bloqueantes; nunca se recortan |
| EX: el kit no se modifica; `evaluar.py` tal cual | `adaptadores_kit.py` es la única frontera; una incompatibilidad se resuelve con adaptador, nunca editando el kit |
| EX: juicios y gold los hace el alumno leyendo | La app nunca precarga ni sugiere; el asistente no escribe en `anotaciones/` |
| D02/D03: pasaje = ventana 200/150/40 con marca reinyectada y `inicio_cuerpo` | Toda la cadena depende de `pasajes.parquet`; cambiarla después de juicios crea una versión experimental nueva |
| D06/D07: pool de 4 variantes, relevancia temática | Un solo juicio por `(query_id, passage_id)` sirve a las 4 variantes; la ventana se analiza aparte |
| D08: ganador único por MAP con filtro, empate a BM25 | `mejor_modelo.json` se escribe una vez y alimenta muestreo, NER, fusión y tablas |
| D09/D15: NER fijado y reglas congeladas antes del gold; selección con conjunto disjunto | El gold de 20 nunca elige ni ajusta nada; cambios posteriores conservan cifras previas |
| D10: muestra ciega de 20 con semilla 42 y emparejamiento global | `muestreo.py` es determinista y se ejecuta antes de que exista `cierre_gold.json` |
| D11: MONTO = dinero; porcentajes y cantidades van a auxiliares | Dos salidas distintas: `entidades.csv` (evaluada) y `cantidades_auxiliares.csv` (para tablas) |
| D12/D16: fusión por span exacto; 8 columnas exactas | Enriquecimiento y normalización viven en un CSV aparte |
| D17: tablas con evidencia y estados | `respuestas.py` nunca afirma una relación sin cita con offsets |
| D18: hashes, revisiones fijas, caché versionada, manifiesto | `manifiesto.py` registra entradas y salidas de cada script; `make validar` compara hashes |
| D20: P0 → P1 → P2 | No se empieza un P1 con un P0 pendiente; la lista de recortes está ordenada (PRD §12.4) |

## 5. Puntos de congelación (en orden cronológico)

| Momento | Qué se congela | Mecanismo |
| --- | --- | --- |
| Antes de rankings | Segmentación (D02-D04), limpieza (D05), consultas Q1-Q10 | `pasajes.parquet` determinista, `data/consultas.csv` |
| Antes del primer juicio | Configuración IR, rankings, pool, criterio de relevancia (D06, D07) | Hashes en `04_pool.csv`; `config/criterios_relevancia.md` |
| Antes de evaluar IR | Regla del ganador (D08) | `mejor_modelo.json` |
| Antes del gold | Reglas, gazetteers, NER principal, convenciones de anotación (D09, D11, D13-D15) | `make congelar` → etiqueta git `reglas-congeladas`; `config/criterios_anotacion.md`; manifiestos de muestra |
| Cierre del gold | Gold y selección | `anotaciones/cierre_gold.json` (levanta el modo ciego) |
| Antes de resultados oficiales | Entorno y dependencias (D01, D18) | `uv.lock`, `requirements.txt`, manifiesto |
| Entrega | Todo | Etiqueta `v1.0-entrega`; no se cambia código que afecte cifras entre entrega y presentación |

## 6. Tabla de invalidación (PRD §11.1)

| Si cambia… | Se invalida… | Nunca |
| --- | --- | --- |
| Snapshot del corpus o segmentación | Todo | Reasignar anotaciones por posición |
| Tokenización o ranker | Ranking, pool, ganador, selección de pasajes IE | Reutilizar juicios de un pool distinto sin detectarlo |
| Consultas | Sus rankings y juicios | Reformular Q1-Q8 |
| Juicios | Métricas IR y ganador (si cambia el ganador: revisión explícita de muestra e IE) | Autocompletar juicios |
| Modelo, reglas o fusión | Extracción, evaluación IE, tablas, documentos | Ajustar con el gold sin registrarlo como exploratorio |
| Gold o protocolo | Evaluación IE y documentos | Retocar el gold para mejorar métricas |

No se borran anotaciones para resolver una invalidación. La pestaña Estado de la app distingue pendiente humano, pendiente técnico, válido, obsoleto (hash cambió) y error.

## 7. Hitos y dependencias humanas

```
H0 preparación ─► H1 datos y consultas ─► H2 recuperación ─► H3 JUICIOS (humano, 2-4.5 h)
      ─► H4 evaluación IR ─► H5 preparación IE (+ revisión de siglas, humano) ─► H6 GOLD (humano, 2-3.5 h)
      ─► H7 IE final ─► H8 respuestas (+ valoraciones, humano) ─► H9 entrega
```

Mientras el alumno anota (H3, H6), el asistente avanza en lo que no depende de esa anotación (reglas, NER, app, reporte esqueleto). Nada de lo humano se simula.

## 8. Mapa de pruebas (PRD §13.1)

| Rango | Qué cubren | Sin red | Marcador |
| --- | --- | --- | --- |
| T01 | Contratos del kit sobre fixtures | Sí | — |
| T02-T06 | Segmentación, índice, fórmulas, filtro, top-k | Sí | — |
| T07-T09 | Pool, pasaje compartido, muestreo con colisiones | Sí | — |
| T10-T13 | Gold vacío, regex, chunking, fusión | Sí (mocks HF) | — |
| T14-T15 | Tablas con evidencia, invalidación y app | Sí | — |
| T16 y pruebas con corpus/modelos reales | Reconstrucción desde clon limpio | No | `lento` |

`make test` corre solo las rápidas; `make test-lento` incluye corpus y modelos.

## 9. Referencias cruzadas

- PRD completo: `PRD_unificado_examen1_mineria_textos.md` (fuente de verdad; este mapa no lo sustituye).
- Estructura del repo y `.gitignore`: PRD §9. Makefile: PRD §10. Formatos exactos de los seis CSV: PRD §3.5.
- Skills del arnés: ver `CLAUDE.md` (índice) y `.claude/skills/*/SKILL.md`.

### Mapa del PRD por líneas (v3.0; léelo por secciones, no entero)

| Sección | Líneas | Sección | Líneas |
| --- | --- | --- | --- |
| §0 Uso del documento y reglas del asistente | 11-66 | §6.9-6.10 Fusión y normalización | 586-607 |
| §1 Contexto, rúbrica, Fase 0 | 68-115 | §6.11 Gold y selección | 608-635 |
| §2 Restricciones y herramientas | 117-150 | §6.12 Evaluación IE y errores | 636-653 |
| §3 Kit, contratos, formatos, offsets | 152-248 | §6.13 Tablas de respuesta | 654-677 |
| §4 Decisiones D01-D22 y PV | 251-291 | §6.14-6.16 Reporte, láminas, demo | 678-716 |
| §5 Consultas y Q9/Q10 | 294-331 | §7 App local | 719-729 |
| §6 Módulos (lista) | 334-368 | §8 Esquemas de datos | 732-760 |
| §6.1 Corpus y segmentación | 370-400 | §9 Estructura del repo | 763-862 |
| §6.2-6.4 Preproceso, índice, ranking | 401-469 | §10 Makefile | 865-896 |
| §6.5-6.6 Pool, juicios, evaluación IR | 470-500 | §11 Reproducibilidad, README, IA, commits | 899-939 |
| §6.7 Reglas y gazetteers | 501-565 | §12 Hitos, prioridades, recortes | 942-985 |
| §6.8 NER | 566-585 | §13-§15 Validación, riesgos, anexos | 988-1146 |
