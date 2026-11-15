---
name: pool-juicios-ir
description: "Usa esta skill al construir o verificar el pool de relevancia (04_pool.py, pool.py), al preparar o validar los juicios humanos de relevancia (criterios_relevancia.md, anotaciones/juicios_relevancia.csv, validar_juicios), al evaluar IR con kit/evaluar.py (05_evaluar_ir.py, resultados_ir.csv, vista con ventana) o al fijar el mejor modelo en data/mejor_modelo.json."
---
# Pool, juicios de relevancia y evaluación de IR

Cubre los módulos `src/mtx/pool.py` y la parte IR de `src/mtx/evaluacion.py`, los scripts
`04_pool.py` y `05_evaluar_ir.py`, la pestaña "Juicios" de la app y los objetivos `make pool`,
`make validar` y `make evaluar-ir`. Fuente: PRD §3.4, §3.5, §6.5, §6.6, D06-D08, T07, T08, §13.2.

## Cuándo usarla

- Hay que generar, regenerar o auditar `salida/04_pool.csv`.
- El alumno va a empezar, continuar o cerrar los juicios de relevancia (hito H3, trabajo humano).
- Hay que correr `validar_juicios()` o exportar `juicios_relevancia.csv` a la raíz.
- Hay que producir `resultados_ir.csv`, la vista con ventana, las tablas por consulta, las figuras IR
  o `data/mejor_modelo.json` (hito H4).
- Alguien pide "elegir el mejor modelo", "completar los juicios que faltan" o "ajustar el pool":
  esta skill dice qué está permitido y qué no.

## Prerrequisitos y congelaciones que aplican

Antes de `make pool` deben existir y estar congelados (PRD §6.5, D06, D07; detalle de hashes en la
skill `integridad-congelacion`):

1. Corpus con `data/corpus_meta.json` vigente y `pasajes.parquet` sin cambios.
2. `data/consultas.csv` con las 10 consultas (Q9 y Q10 ya fijadas).
3. Configuración IR (preprocesamiento, ventana, parámetros de TF-IDF y BM25) y `ranking.csv`
   con 10 consultas × 4 variantes × 10 rangos (skill `indice-ranking`).
4. Contratos del kit verificados en H0 (`make contratos`, skill `kit-contratos`): argumentos reales
   de `kit/evaluar.py ir`, denominador de AP, columnas de salida (`relevantes_recuperados`,
   `relevantes_en_pool`, `no_juzgados`), trato de consultas sin relevantes.
5. `config/criterios_relevancia.md` escrito por el alumno (ver sección de criterio).

Regla dura: desde el primer juicio humano, corpus, consultas, configuración IR, rankings, pool y
criterio quedan congelados. Cualquier cambio del pool invalida su cierre y los juicios
asociados pasan a "inválidos hasta revisión", nunca se borran ni se reasignan en silencio.

## Construcción del pool

Reglas (PRD §6.5, D06):

1. Por consulta, pool = unión sin duplicados de los `passage_id` de los top-10 de las cuatro
   variantes (`tfidf_con_filtro`, `bm25_con_filtro`, `tfidf_sin_filtro`, `bm25_sin_filtro`).
   Tamaño esperado 15 a 40 por consulta; fuera de ese rango se avisa y se revisa el ranking.
2. Un pasaje compartido entre consultas recibe un juicio independiente por cada `(query_id,
   passage_id)` (T08). Nunca se copia un juicio de una consulta a otra.
3. `salida/04_pool.csv` con columnas exactas: `query_id, passage_id, doc_id, fecha, en_ventana,
   variantes` (separadas por `|`), `mejor_rango_tfidf, mejor_rango_bm25, texto, texto_sha256`.
   La procedencia (`variantes`, rangos) es solo para auditoría: la app no la muestra.
4. Orden de presentación: lista de IDs ordenada y después barajada con semilla 42 por consulta.
   Mismo pool, misma semilla, mismo orden siempre.
5. `make pool` construye el pool si no existe; si existe, lo reconstruye en memoria y compara
   hashes. Si hay juicios en `anotaciones/juicios_relevancia.csv` y el pool cambió, se detiene con
   un mensaje que enumera las diferencias y no sobrescribe nada. Nunca sustituye un pool anotado
   sin detectar el cambio.
6. Prueba T07: cuatro rankings parcialmente solapados producen la unión exacta y la cobertura de
   juicios se verifica contra ese pool.

Lista de verificación al terminar: 10 consultas presentes; `texto_sha256` coincide con el texto
del pasaje; ningún `passage_id` ausente de `pasajes.parquet`; `en_ventana` calculado con la ventana
congelada y fecha desconocida como `False`.

## Criterio de relevancia y juicios (trabajo humano)

**Criterio (D07).** Relevancia temática: un pasaje es relevante por su contenido, sin importar su
fecha ni el modelo que lo recuperó. Lo fija el alumno en `config/criterios_relevancia.md` antes del
primer juicio `[VALIDAR]`. El texto del PRD §6.5 ("trata directamente del tema y aporta al menos
un dato sustantivo...; un saludo o una coincidencia aislada de términos no basta") es solo una
propuesta: se le ofrece al alumno, no se escribe por él. El archivo queda congelado al empezar.

**App, pestaña "Juicios" (`vista_juicios.py`, skill `app-anotacion`).**

1. Barra lateral: selector de consulta, progreso por consulta y global, botón "Guardar".
2. Cuerpo: consulta en grande, `pregunta_extraccion` como ayuda, pasaje completo con resaltado de
   términos (match por stem sobre el token original), metadatos `doc_id`, `titulo`, `interlocutor`.
   La fecha se muestra con el recordatorio en pantalla de que no cuenta para el juicio.
3. Botones: **Relevante (1)**, **No relevante (0)**, **Omitir por ahora**, **Anterior**.
   "Sin juzgar" (omitido) es un estado distinto de 0 y nunca se convierte en 0 por defecto.
4. Ciega al modelo: no muestra puntajes, rangos, variante ni `mejor_rango_*`.
5. Autoguardado atómico en `anotaciones/juicios_relevancia.csv` tras cada clic (archivo temporal
   y renombrado), con historial de revisión, reanudable y con detección de edición desde dos
   pestañas (T15).

**Prohibido para el asistente:** juzgar, sugerir, precargar, completar o "corregir" juicios;
generar juicios sintéticos que acaben en `anotaciones/`; mostrar al alumno qué variante recuperó
un pasaje mientras anota. Solo se permite un `juicios_relevancia.csv` sintético para pruebas de
contrato en H0, fuera de `anotaciones/` y nunca exportado a la raíz.

**Tiempo del alumno:** 150 a 400 pasajes × 40 s ≈ 2 a 4.5 horas. Se cronometra un primer lote
(por ejemplo una consulta completa) y se reestima. Si no alcanza, se aplica el recorte 5 de PRD
§12.4 (pool reducido a variantes con filtro, métrica condensada para las sin filtro) y se declara
antes de interpretar resultados.

## Validación de juicios

`validar_juicios()` en `pool.py`, invocada también por `make validar` (PRD §6.5, §13.2 punto 4).
Todas las comprobaciones son de solo lectura sobre los juicios:

1. Columnas exactas `query_id, doc_id, passage_id, relevante`; UTF-8 sin BOM, separador coma.
2. Cobertura 100 %: cada `(query_id, passage_id)` del pool tiene exactamente un juicio.
3. `relevante` ∈ {0, 1}; un omitido pendiente es error de cobertura, no un 0.
4. Ningún par fuera del pool; `doc_id` coherente con el `passage_id`.
5. `texto_sha256` del pool coincide con el texto actual del pasaje (detecta corpus o segmentación
   cambiados).
6. Al menos un relevante por consulta. Si una consulta tiene cero, se emite aviso ("AP indefinido
   para Qn, se discute en el reporte") y no se altera ningún juicio ni se retira la consulta.
7. Si todo pasa, exporta `juicios_relevancia.csv` a la raíz del repo con el mismo contenido.

Si falla cualquier punto 1 a 5, no se exporta y `make evaluar-ir` se niega a correr.

## Evaluación oficial y vista con ventana

`05_evaluar_ir.py` con la parte IR de `evaluacion.py` (PRD §3.4, §6.6):

1. **Cifra oficial.** `subprocess` → `python kit/evaluar.py ir juicios_relevancia.csv ranking.csv`
   con los argumentos confirmados en H0. Copia íntegra de `resultados_ir.csv` a la raíz y a
   `salida/`, sin renombrar columnas, más entrada, salida, hashes y registro de ejecución. El kit
   lee solo `query_id, modelo, rango, passage_id` del ranking y trata un no juzgado como no
   relevante; AP divide entre los relevantes del pool de la consulta (PRD §A: P@k, AP@10, MAP).
2. **Vista con ventana (complementaria).** `salida/05_juicios_con_ventana.csv` con
   `relevante_ventana = relevante AND en_ventana` (fecha desconocida no cumple la ventana) y el
   mismo evaluador sobre él → `salida/05_resultados_ir_ventana.csv`. Se rotula "complementaria":
   cambian criterio y denominador de AP. Nunca sustituye ni se mezcla con `resultados_ir.csv`.
   Se cuentan por consulta los relevantes temáticos dentro, fuera de ventana y con fecha desconocida.
3. `salida/05_ir_por_consulta.csv` en formato ancho: consulta × variante para P@5, P@10, AP,
   soporte, juzgados y no juzgados.
4. `salida/05_ir_ganador_por_consulta.csv`: ganador por AP entre las variantes con filtro,
   diferencia y etiquetas calculadas por el script, nunca a mano: longitud en tokens tras
   preprocesar (larga o corta respecto a la mediana de las diez), número de términos con df alto,
   presencia de siglas o nombre propio, sinónimos conocidos según
   `config/sinonimos_consultas.yaml` (huachicol ↔ robo de combustible; adultos mayores ↔ pensión
   del Bienestar; AIFA ↔ Santa Lucía ↔ Felipe Ángeles; Dos Bocas ↔ refinería Olmeca).
5. Figuras plotly (PNG por kaleido), estilo sobrio, una paleta, títulos en mayúscula inicial:
   `reporte/figuras/ir_map_por_modelo.png`, `ir_ap_por_consulta.png`, `ir_con_vs_sin_filtro.png`.
6. El texto del análisis (reporte, p. 2) se escribe después de ver las etiquetas y describe esta
   colección; no se presenta como generalización.

## Mejor modelo (D08)

1. `mejor_modelo = argmax MAP oficial` entre `tfidf_con_filtro` y `bm25_con_filtro`, tomado de
   `resultados_ir.csv` (filas `PROMEDIO`), nunca de la vista con ventana.
2. Empate exacto → `bm25_con_filtro`.
3. Único para las diez consultas; no se elige por consulta ni se cambia después de abrir IE.
4. Se escribe `data/mejor_modelo.json` con: modelo, MAP, alternativa, su MAP, versión (hash) de
   `ranking.csv` y de `juicios_relevancia.csv`.
5. Si `|MAP_bm25 − MAP_tfidf| < 0.01`, se añade la marca `diferencia_menor_0.01: true` y se comenta
   en el reporte; la regla no cambia.
6. Fijado antes de cualquier paso de IE (muestra gold, extracción); si rankings o juicios cambian,
   el JSON queda inválido y se regenera antes de seguir.

## Salidas y criterios de aceptación

Salidas: `salida/04_pool.csv`; `anotaciones/juicios_relevancia.csv` (humano); `juicios_relevancia.csv`
y `resultados_ir.csv` en la raíz; `salida/resultados_ir.csv`, `05_juicios_con_ventana.csv`,
`05_resultados_ir_ventana.csv`, `05_ir_por_consulta.csv`, `05_ir_ganador_por_consulta.csv`;
`data/mejor_modelo.json`; tres figuras `reporte/figuras/ir_*.png`.

Lista de aceptación (PRD §6.6, §13.2):

- [ ] `resultados_ir.csv`: 10 consultas × 4 variantes = 40 filas más 4 filas `PROMEDIO`.
- [ ] `no_juzgados == 0` en las cuatro variantes (si no, el pool no cubre los top-10: volver a pool).
- [ ] Toda consulta con cero relevantes anotados lleva nota en el reporte; juicios intactos.
- [ ] `resultados_ir.csv` se regenera con el kit y coincide con el versionado.
- [ ] Horizonte de evaluación (AP sobre top-10) documentado en el reporte.
- [ ] `data/mejor_modelo.json` fijado por D08 antes de IE; marca de diferencia < 0.01 si aplica.
- [ ] Vista con ventana rotulada como complementaria en tablas, figuras y texto.
- [ ] Tiempo real de anotación registrado; recorte 5 declarado si se aplicó.

## Skills relacionadas

- `integridad-congelacion`: hashes, cierres y qué hacer si algo cambia tras el primer juicio.
- `kit-contratos`: argumentos y columnas reales de `kit/evaluar.py ir` confirmados en H0.
- `indice-ranking`: produce el `ranking.csv` del que nace el pool.
- `app-anotacion`: implementación de la pestaña "Juicios" y del autoguardado atómico.
- `tablas-respuesta`: consume `data/mejor_modelo.json` para elegir el top-10 de la Tarea B.

## v2: varios anotadores, agregación y acuerdo (PRD v2 D24, D27, D28, D29; WP-02, WP-05, WP-06)

- **Archivos:** un CSV por persona en `anotaciones/juicios_v2/<anotador>.csv` con las mismas 4
  columnas de v1 (`validar_juicios()` sirve tal cual). Lista de anotadores y lotes en
  `config/v2/anotadores.yaml`; lógica en `src/mtx/anotadores.py`.
- **Asignación:** `make asignar-juicios LOTE=n` agrega el lote a `data/v2/asignacion_juicios.csv`
  (`lote, anotador, origen, orden, query_id, doc_id, passage_id, texto_sha256`). Cada par lo juzgan
  todos los jueces del lote. `origen = v1` = juicios v1 importados con
  `make importar-juicios ANOTADOR=x ORIGEN=ruta` (Diego, Luis y Arturo en el lote 1); no se editan.
- **Lote 1:** los 176 pares v1, completo con los juicios v1 de Diego, Luis y Arturo (importados). **Lote 2:** pares nuevos del
  pool v2 (unión de 8 variantes × 15 consultas, tope 450); Arturo, Bruno y Leo, o Luis en lugar de
  Bruno si el pool queda el domingo 15 antes de las 20:00.
- **Agregación (WP-02):** relevante = mayoría de 3 juicios válidos; un omitido no cuenta y el par
  no se cierra. `scripts/05a_agregar_juicios.py` escribe `salida/v2/05a_juicios_agregados.csv` y el
  `juicios_relevancia.csv` que lee el kit; nunca se edita a mano.
- **Acuerdo:** Fleiss global y por consulta, Cohen por pareja, acuerdo observado. Es para el
  reporte, nunca para descartar a un juez.
- **Ganador v2 (D28):** mayor MAP entre las 4 variantes con filtro (stem y lema); empate → BM25
  stem. El `ranking.csv` de la raíz conserva los 4 nombres de modelo de v1.
- **Robustez (D29):** intervalo bootstrap por consultas, prueba de permutación pareada, P@10,
  nDCG@10 y la comparación del MAP con pool v1 contra pool v2 (inflación por pool).
