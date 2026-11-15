# PRD v2 · Proyecto final · Recuperación y extracción de información en las mañaneras

**Versión:** 2.0 borrador · 14 de noviembre de 2026 · PV1 a PV6 confirmados el 14 de noviembre; roles
aprobados el 14 de noviembre; reglas de la sección 3 en `[VALIDAR]` por el equipo
**Base:** `PRD_unificado_examen1_mineria_textos.md` (v3.0) y la entrega `v1.0-entrega`.
**Plazo:** miércoles 25 de noviembre de 2026, antes de las 18:00 (hora de la Ciudad de México).
**Destinatarios:** el equipo Datisa (6 integrantes) y Claude Code, que trabaja en cada computadora con el arnés de este repositorio (`CLAUDE.md` y `.claude/skills/`).

---

## 0. Cómo usar este documento

### 0.1 Relación con el PRD v3.0

Este PRD es una **adenda**. Todo lo que no se modifica aquí sigue rigiendo como dice el PRD v3.0:
contratos del kit, formatos de los seis CSV, offsets, segmentación, reglas de integridad, estilo,
commits y reproducibilidad. Cuando los dos documentos choquen, gana este. Las marcas EX, DP, OP y PV
significan lo mismo que en PRD v3.0 §0.1.

### 0.2 Reglas nuevas para Claude Code

Se suman a las de PRD v3.0 §0.2; ninguna las relaja.

1. **Seis personas y seis computadoras.** Antes de empezar, Claude Code pregunta quién lo usa y en qué
   paquete de trabajo (WP, sección 5). Solo toca los archivos de ese paquete (tabla de propiedad, 6.2).
   Si la tarea exige tocar algo ajeno, se detiene y lo dice.
2. **Los insumos humanos siguen siendo humanos.** Juicios, gold, conjunto de selección, adjudicación,
   consultas Q11 a Q15, criterios y valoraciones los produce cada integrante leyendo. Claude Code
   construye la herramienta, valida formatos y nunca rellena, sugiere ni "corrige" esos valores. Si un
   integrante pide ayuda para decidir un juicio o una entidad, Claude Code se niega en una frase y
   remite al criterio escrito.
3. **v1 no se sobrescribe.** Las cifras de `v1.0-entrega` se conservan en git y en el reporte. Lo
   nuevo se escribe en rutas `v2` o en commits posteriores a la etiqueta `v2-inicio`. El reporte
   presenta la comparación v1 → v2.
4. **Reglas fijadas antes de medir.** Las reglas de agregación de juicios, del ganador, de selección
   del NER y del muestreo están en la sección 3 y quedan fijas al aprobar este PRD. Cambiarlas después
   crea una versión exploratoria documentada (integridad-congelacion, PRD v3.0 §6.12).
5. **Nada de predicciones ni rankings a la vista de quien anota.** Mientras un integrante tenga
   anotación pendiente, Claude Code no le muestra rankings, puntajes ni entidades predichas de los
   pasajes de su lote (sección 3.10).

### 0.3 Decisiones confirmadas (14 de noviembre)

| # | Tema | Valor | Nota |
| --- | --- | --- | --- |
| PV1 | Empate de la encuesta (3 por par contra los 6) | **3 jueces por par** | Confirmado. Con 6 jueces la carga por persona (~5 h) supera las 2 a 4 h que declararon 5 de 6 |
| PV2 | Juicios v1 | Los 176 juicios oficiales de v1 son de Diego Rafael; los del "otro integrante" (acuerdo 115 de 176) son de **Luis**. Arturo también tiene 176 juicios v1, todos suyos (repo propio, commit `f51f61d`). Los tres cuentan como los 3 juicios del lote 1 | Confirmado. El lote 1 queda completo sin juzgar en la app. La regla es "cuentan todos los juicios humanos del equipo sobre el pool", fijada antes de calcular el MAP v2, no elegida por el 0.615 de Luis. Ver PV12 |
| PV3 | Nombre de Leo | **Leo Yahir** Carpio Angeles | Confirmado. La portada, el README y el reporte v1 dicen "Yair"; se corrige en todo lo v2 (WP-17, WP-19) |
| PV4 | Instalación de Bruno | Instala local con ayuda (por defecto) | No hay app web de anotación antes del lunes 16 |
| PV5 | Hora de entrega del 25 | **Antes de las 18:00** | Confirmado. La etiqueta `v2.0-entrega` se pone el martes 24 |
| PV6 | Duración de la presentación y número de láminas | **15 a 20 min con demo**; láminas libres | Confirmado. El profesor no fijó límite |

---

## 1. Contexto

### 1.1 Qué cambió

El 11 de noviembre el equipo presentó `v1.0-entrega`. El profesor dio hasta el 25 de noviembre para
mejorarlo; ahora cuenta como examen **y** proyecto final. Mismos entregables (seis CSV, reporte,
presentación con demo); el número de golds, las láminas y la duración quedan libres.

### 1.2 Lo que v1 ya tiene y no se rehace

Corpus y segmentación (127,739 pasajes, ventanas 200/150/40), limpieza auditada, índice, TF-IDF y BM25
propios, filtro de fecha, pool de 176 pares, juicios de Diego, gold de 20 pasajes y 163 entidades,
reglas congeladas (`reglas-congeladas`), NER `mrm8488`, fusión, evaluación oficial con el kit, tablas
de respuesta, app Streamlit, demo en terminal, reporte, README y reproducibilidad desde clon limpio.

**No cambian:** segmentación, limpieza, Q1 a Q10, stemming de las variantes v1, criterio de relevancia
(sección 3.2), reglas de PER, ORG, LOC y MONTO. Cambiar cualquiera de ellas invalidaría los 176
juicios y el gold v1 (PRD v3.0 §11.1).

### 1.3 Retroalimentación del profesor → requisitos

| ID | Comentario | Requisito v2 | WP |
| --- | --- | --- | --- |
| R01 | Presentación para venta, no de alumno a profesor | Narrativa para un cliente de gobierno: problema → solución → evidencia → demo | WP-17 |
| R02 | Color de Morena | Paleta oficial del Gobierno de México | WP-16, WP-17 |
| R03 | Explicativa; poner ejemplos | Cada lámina técnica lleva un ejemplo real tomado de `salida/` | WP-16, WP-17 |
| R04 | Quitar archivos del arnés | Sin rutas `salida/...` en las láminas; las fuentes van al guion | WP-17 |
| R05 | Enfocarse en lo positivo | Limitaciones como "siguiente paso" con su mejora | WP-17 |
| R06 | Comparar con modelo ciego | Revisión de la presentación por un LLM sin contexto | WP-18 |
| R07 | Modelo lógico; ¿por qué no booleano si el idf es alto? | Experimento booleano AND/OR y lámina con la explicación | WP-07 |
| R08 | ¿Por qué se borran los periodistas? | Argumento corregido (3.13) en lámina y guion | WP-17 |
| R09 | Explicar el índice invertido | Figura con un ejemplo de postings | WP-16 |
| R10 | Cambiar fuente | Tipografía institucional (3.12) | WP-17 |
| R11 | Demo en terminal poco amable | Demo web pública para que el profesor consulte | WP-15 |
| S2a | Verificar número de discursos | 2,294 cargados, 5 duplicados excluidos (2,289), 2,288 con pasajes | WP-16 |
| S2b | ¿Qué son las acotaciones? | Definición con ejemplos reales de `salida/01_auditoria_corpus.csv` | WP-16 |
| S3 | Íconos más claros; nombres en vez de Qn | Íconos por obra; "Pregunta 1 · Tren Maya" | WP-17 |
| S4a | Separar en varias láminas | Una lámina por etapa: limpieza, tokenización, stopwords, stemming/lema, índice, idf | WP-17 |
| S4b | Stopwords sin "quitar" | "Palabras vacías que no distinguen temas" | WP-17 |
| S4c | Cómo tokenizamos | Ejemplo de una oración real paso a paso | WP-16 |
| S4d | La tabla de idf no explica la rareza | Barra de "% de pasajes que contienen el término" con idf al lado; título "la unidad es el idf" | WP-16 |
| S4e | Hacer lematización y comparar | Variantes lematizadas en el pool y en la evaluación | WP-03 |
| S5a | Ejemplo; porcentajes | AP explicado con una consulta real; MAP también en % | WP-16 |
| S5b | MAP con los juicios de todos | Juicios de 3 integrantes por par, mayoría, kappa e intervalo de confianza | WP-01, WP-02, WP-06 |
| S6 | Colores, nombres, ejes | Figuras con ejes nombrados y nombres de consulta | WP-16 |
| S7a | ¿Está bien el F1? | F1 con referencias: techo humano, línea base trivial, intervalo de confianza | WP-12 |
| S7b | Especificación de FECHA (repo del profesor) | FECHA v2 sobre el repo del profesor | WP-11 |
| S7c | Recall y precisión | Precisión y recall por tipo y método en lámina | WP-16 |
| S8a | Que no se lea como "el modelo falló" | Errores como patrones con su causa y su arreglo | WP-17 |
| S8b | Cambiar el ID del pasaje | "Mañanera del 12 de marzo de 2021 · fragmento 3" en vez de `1122_3` | WP-15, WP-16 |
| S8c / S11c | Comparar con otros modelos | Comparación de 3 o 4 NER sobre el conjunto de selección | WP-10 |
| S9 | Gráfica ambigua; respaldado y ambiguo | Nombres de ejes y de consulta; definición de cada estado con un ejemplo | WP-16 |
| S10 | Sin comandos, sin dataframes, sin IDs; ejemplo fundamental | La demo web cubre esto; la lámina 10 muestra capturas de la web | WP-15, WP-17 |
| S11a | Lo que no se pudo, cómo se mejora | Cada limitación con su propuesta | WP-17 |
| S11b | Más golds | 20 pasajes gold nuevos y 10 de selección, con doble anotación | WP-08, WP-09 |

---

## 2. Equipo, roles y disponibilidad

### 2.1 Roles

| Integrante | Frente principal | Apoyo | Anota |
| --- | --- | --- | --- |
| **Diego** Moctezuma Ramirez | Integración, coordinación, app multianotador e IR (WP-00 a WP-07) | Diseño de láminas | Selección y gold parte A (fin de semana) |
| **Gonzalo** Mera Montiel | Presentación (líder, WP-17) | Reporte (WP-19) | Gold partes A y B (lunes 16 y martes 17) |
| **Arturo** Jaramillo Salmerón | Contenido de la presentación: ejemplos, revisión ciega (WP-18), ensayo con cronómetro | Reporte: lectura y revisión | Juicios lote 2 (lunes 16); su lote 1 viene de v1 |
| **Bruno** Ruiz Juarez | Demo web (líder, WP-15) | Reporte (WP-19) | Gold parte B y juicios lote 2 (lunes 16, miércoles 18 y viernes 20) |
| **Leo** Carpio Angeles | Reglas de FECHA (WP-11) | Demo web | **Solo juicios** lote 2 (martes 17 a jueves 19); no anota gold |
| **Luis** Ramirez Maza | Comparación de NER (WP-10) | Sección de IE del reporte, antes del 21 | Selección (fin de semana); su lote 1 viene de v1 |

Reglas de rol:

- Quien escribe reglas de FECHA (Leo) no anota gold ni selección; así las reglas no se ajustan a
  pasajes que vio anotados.
- Luis anota la selección **antes** de correr cualquier NER sobre esos pasajes.
- Quien desarrolla la demo (Bruno, Leo) trabaja con artefactos v1 hasta los cierres del 20 de
  noviembre (sección 3.10).

### 2.2 Disponibilidad declarada para anotar

| Día | Diego | Gonzalo | Arturo | Bruno | Leo | Luis |
| --- | --- | --- | --- | --- | --- | --- |
| Sáb 14 y dom 15 | ✓ | | ✓ | | | ✓ |
| Lun 16 (feriado) | | ✓ | ✓ | ✓ | | |
| Mar 17 | | ✓ | | | ✓ | |
| Mié 18 | | ✗ | | ✓ | ✓ | |
| Jue 19 | | | | | ✓ | |
| Vie 20 | | | | ✓ | | |

Restricciones: Luis no puede del 21 al 23 (examen el 23); Bruno trabaja; Gonzalo no puede el 18.

### 2.3 Carga de anotación estimada

Estimaciones de PRD v3.0 §12.3 ajustadas: 30 s por juicio, 10 min por pasaje gold, 3 min por pasaje
adjudicado. El primer lote de cada persona se mide y la tabla se corrige en `docs/decisiones.md`.

| Integrante | Tareas | Horas |
| --- | --- | --- |
| Diego | Selección (10 pasajes), gold parte A (10), adjudicación de la parte B | ~3.8 |
| Luis | Selección (10); sus juicios v1 ya cubren el lote 1 | ~1.7 |
| Arturo | Juicios lote 2 (~200), adjudicación de la selección; su lote 1 viene de v1 | ~2.1 |
| Gonzalo | Gold parte A (10), gold parte B (10) | ~3.4 |
| Bruno | Gold parte B (10), juicios lote 2 (~200), adjudicación de la parte A | ~3.8 |
| Leo | Juicios lote 2 (~200) | ~1.7 |

---

## 3. Decisiones nuevas (D23 a D36)

Quedan fijas al aprobar este PRD. Cada una indica cuándo se congela.

### 3.1 D23 · Versionado v1 → v2

- Etiqueta `v2-inicio` sobre el commit que aprueba este PRD.
- Las cifras v1 se conservan: el reporte cita `v1.0-entrega` y las cifras v2 lado a lado.
- Los seis CSV de la raíz pasan a ser los de v2 en `v2.0-entrega`; los de v1 viven en la etiqueta.

### 3.2 D24 · Juicios con varios anotadores

- **3 juicios por par** (PV1). En los 176 pares v1, los juicios v1 de Diego, Luis y Arturo son los
  tres (PV2); se importan sin cambios a `anotaciones/juicios_v2/` con
  `scripts/04c_importar_juicios_v1.py`, que valida las claves contra el pool y no edita valores.
- **Criterio:** `config/criterios_relevancia.md` sin cambios. Una calibración de 20 min antes del lote 2 aclara
  dudas con 10 pares de práctica **fuera del pool**. Si el equipo decide cambiar el criterio, los
  juicios v1 de Diego, Luis y Arturo dejan de contar y esos 176 pares necesitan tres jueces nuevos.
- **Archivo por anotador:** `anotaciones/juicios_v2/<anotador>.csv` con las mismas 4 columnas de
  PRD v3.0 §3.5, para reutilizar `validar_juicios()`. Quién juzgó lo dice el nombre del archivo; la
  marca de tiempo de cada cambio está en `<anotador>_historial.csv`. La app solo escribe el archivo
  de quien está anotando.
- **Asignación determinista** (`data/v2/asignacion_juicios.csv`), por lotes. Cada par lo juzgan
  todos los jueces de su lote, en el orden del pool (ya permutado con semilla 42 por consulta). Cada
  fila guarda la huella del texto; `origen = v1` marca los juicios importados, que la app no edita.
  La asignación de un lote no se reescribe una vez creada:
  - Lote 1: los 176 pares v1 → Diego, Luis y Arturo, los tres importados de v1; nadie los juzga en la app.
  - Lote 2: los pares nuevos → Arturo, Bruno y Leo. Si el pool v2 queda congelado el domingo 15 antes
    de las 20:00, Luis toma la parte de Bruno, que queda de reserva (Luis no anota del 21 al 23).
- **Ciego:** la app no muestra puntajes, rangos, variantes, juicios de otros ni el avance de los demás.
- **Agregación:** relevante = mayoría (≥ 2 de 3). Los omitidos no cuentan: un par con menos de 3
  juicios válidos no se cierra. Lo que lee el kit, `juicios_relevancia.csv`, lo genera un script desde
  los archivos humanos y nunca se edita a mano.
- **Acuerdo:** kappa de Fleiss global y por consulta, acuerdo observado y kappa de Cohen por pareja.
  Es información para el reporte, no un criterio para descartar a nadie.
- **Se congela:** antes del primer juicio del lote 1.

### 3.3 D25 · Consultas nuevas Q11 a Q15

- Cinco consultas propias con tema, ventana de fechas y pregunta de extracción, como Q9 y Q10.
- Claude Code propone candidatas con conteos del corpus (`descubrimiento.py`); el equipo (Diego y
  Arturo) elige y redacta. `[VALIDAR]`
- Requisito de diversidad: al menos una con nombre alterno (como Dos Bocas y refinería Olmeca) y temas
  distintos de Q1 a Q10.
- **Se congela:** domingo 15 a mediodía, antes de construir el pool v2.

### 3.4 D26 · Lematización

- **Lematizador:** spaCy `es_core_news_md` con versión fija en `uv.lock`; solo el lematizador
  (`disable=["parser", "ner"]`). Si no instala en las 6 máquinas, se usa `simplemma` con versión fija,
  y se registra.
- **Mismo pipeline salvo el paso de raíz:** normalización, tokenizador y stoplist iguales; lema en vez
  de stem; consultas con el mismo tratamiento. El índice lematizado se ajusta una sola vez sobre los
  127,739 pasajes.
- **Ocho variantes:** `{tfidf, bm25} × {con, sin}_filtro × {stem, lema}`. Nombres en `ranking.csv`:
  `bm25_con_filtro` (v1, stem) y `bm25_lema_con_filtro`, etcétera.
- **Se congela:** antes del pool v2.

### 3.5 D27 · Pool v2

- Unión de los top-10 de las 8 variantes para Q1 a Q15. Incluye por construcción los 176 pares v1.
- El pool v2 se congela con hashes, igual que en PRD v3.0 §6.5.
- **Tope:** si supera 450 pares, las variantes lematizadas sin filtro salen del pool. Se evalúan con la
  métrica condensada y se declara (recorte 5 de PRD v3.0 §12.4).

### 3.6 D28 · Ganador IR v2

- Mayor MAP oficial (kit) entre las **4 variantes con filtro** (stem y lema × TF-IDF y BM25), con los
  juicios agregados.
- Empate a 4 decimales: gana BM25 stem, la variante ganadora de v1.
- `ranking.csv` de la raíz lleva las 4 variantes (TF-IDF y BM25, con y sin filtro) del preprocesamiento
  ganador, con los nombres de v1. Las 8 variantes quedan en `salida/v2/ranking_8_variantes.csv`.
- **Se congela:** al aprobar este PRD.

### 3.7 D29 · Robustez de la evaluación IR

Complementan la cifra oficial; no la sustituyen.

1. **Intervalo de confianza al 95 %** del MAP por bootstrap sobre consultas: 10,000 remuestreos,
   semilla 42.
2. **Prueba de permutación pareada** por consulta entre el ganador y cada rival: 10,000 permutaciones.
3. **Sensibilidad a la agregación:** MAP con unanimidad y con "al menos 1 de 3".
4. **Inflación por pool:** MAP de Q1 a Q10 con el pool v1 frente al pool v2. Explica por qué v1 parecía
   alto: el kit divide entre los relevantes del pool (`docs/contratos_kit.md`).
5. **P@10 y nDCG@10** binario junto al MAP.

### 3.8 D30 · Modelo booleano como contraste (exploratorio)

- AND y OR sobre el índice stem, con los tokens de cada consulta y el filtro de fecha.
- Salida: número de pasajes que devuelve cada operador por consulta, y un ejemplo de cómo trata igual
  a "huachicol" que a "programa".
- No entra al pool ni compite por el ganador. Responde R07 con evidencia: el booleano no ordena,
  descarta el idf y la tf, y con AND la consulta larga queda vacía.

### 3.9 D31 · Gold v2 y conjunto de selección

- **Tamaños:** 20 pasajes gold nuevos y 10 de selección. Con los 20 de v1, la evaluación oficial v2
  usa **40 pasajes**.
- **De dónde salen:** del pool con filtro, nunca del ganador, para no esperar a los juicios. También se
  excluye todo pasaje que ya tuvo predicciones visibles en v1 (el ámbito IE de v1, 99 pasajes, y los 20
  gold).
  - Selección: 1 por consulta de Q1 a Q10 (10).
  - Gold parte A: 1 por consulta de Q1 a Q10 (10).
  - Gold parte B: 2 por consulta de Q11 a Q15 (10).
  - Semilla 42, emparejamiento global como en `muestreo.py`; selección, A y B disjuntas.
- **Doble anotación:** cada pasaje nuevo lo anotan 2 personas por separado, en modo ciego.
  - Selección: Diego y Luis.
  - Parte A: Diego y Gonzalo.
  - Parte B: Gonzalo y Bruno.
- **Adjudicación humana:** un tercero que no anotó el pasaje resuelve los desacuerdos en una pestaña
  nueva. Ve las dos anotaciones y nunca predicciones. El resultado es el gold oficial del pasaje.
  Adjudicadores: Arturo la selección, Bruno la parte A y Diego la parte B.
- **Acuerdo entre anotadores antes de adjudicar:** F1 exacto entre los dos, por tipo. Es el **techo
  humano** contra el que se lee el F1 del sistema (S7a).
- **Gold v1:** los 20 pasajes no se reanotan, salvo FECHA si cambia el criterio (D32).
- **Cierre:** `anotaciones/cierre_gold_v2.json` levanta el modo ciego de los 30 pasajes nuevos.
- **Se congela:** el muestreo y sus manifiestos, antes de mostrar el primer pasaje.

### 3.10 D32 · Separación entre anotación y predicciones

- Hasta el cierre de los juicios, ningún anotador del lote 2 ve rankings con las variantes
  lematizadas ni de Q11 a Q15.
- Hasta `cierre_gold_v2.json`, nadie ve predicciones de los 30 pasajes nuevos.
- La demo web se desarrolla con artefactos v1 y se publica con datos v2 solo después de ambos cierres.
- `make demo` y la pestaña Demo bloquean los pasajes de la muestra v2 mientras no exista el cierre.

### 3.11 D33 · FECHA v2

- **Base:** el repo que compartirá el profesor (PV: fecha de llegada y licencia). Se registra su origen
  en `docs/decisiones.md` y en "Uso de IA y fuentes" del README.
- **Primero el criterio:** `config/criterios_anotacion.md` v2, solo la sección FECHA, la escribe el
  equipo (Gonzalo y Diego) con el repo del profesor como referencia. `[VALIDAR]`
- **Anotación en dos pasadas** para no bloquear el gold:
  - Pasada 1: PER, ORG, LOC y MONTO, en cuanto haya muestra.
  - Pasada 2: solo FECHA, con el criterio v2, sobre los 50 pasajes (20 v1 y 30 nuevos), por los mismos
    anotadores de cada pasaje. La FECHA de los 20 de v1 la reanota Diego, que es su autor.
- **Reglas FECHA v2** (Leo): se congelan con la etiqueta `reglas-fecha-v2` antes del primer commit de
  la pasada 2. Las cifras de FECHA con las reglas v1 se conservan.
- **Recorte:** si el repo llega después del jueves 19, la pasada 2 usa el criterio v1. FECHA v2 queda
  como evaluación exploratoria de las reglas, sobre el gold con criterio v1, y se declara.

### 3.12 D34 · Selección del NER

- **Candidatos:** `mrm8488/bert-spanish-cased-finetuned-ner` (v1) y 2 o 3 más. Cada uno se verifica en
  Hugging Face con revisión fija (PV) antes de entrar: etiquetas, licencia y tamaño. Sugeridos para
  revisar:
  - un RoBERTa de la familia BNE/CAPITEL que siga publicado;
  - spaCy `es_core_news_lg`;
  - un XLM-R multilingüe de NER;
  - GLiNER multilingüe sin entrenamiento previo, que además puede proponer FECHA y MONTO.
- **Criterio:** F1 micro exacto en PER, ORG y LOC **del modelo solo** sobre el conjunto de selección
  adjudicado. Empate a 3 decimales: gana `mrm8488`.
- **Se congela:** `data/modelo_ner.json` v2 se escribe antes de evaluar el gold v2. El gold nunca elige.

### 3.13 D35 · Lectura del F1 (S7a)

El F1 oficial (kit, exacto) se reporta junto a:

1. el techo humano (D31);
2. una línea base trivial: solo gazetteer, sin regex ni modelo;
3. un intervalo de confianza del 95 % por bootstrap sobre pasajes;
4. F1 con coincidencia parcial (solape de al menos un carácter y mismo tipo), como complementaria
   etiquetada.

La conclusión se escribe en términos de distancia al techo y a la línea base, no como "bien" o "mal".

### 3.14 D36 · Presentación, demo y argumento de reporteros

- **Paleta:** Gobierno de México. Guinda `#9F2241` y `#691C32`, dorado `#BC955C` y `#DDC9A3`, gris
  `#98989A`; verificar con el manual vigente (PV).
- **Tipografía:** Montserrat para títulos y Noto Sans para texto (PV, mismo manual).
- **Estilo de venta:** sin rutas ni comandos; ejemplos reales; nombres de consulta en vez de Qn; ejes
  nombrados; porcentajes donde ayuden. Número de láminas libre; duración de 15 a 20 min con demo (PV6).
- **Argumento de reporteros** (R08), versión que coincide con el sistema:
  > Los pasajes de reporteros se indexan: el 15.5 % del índice son preguntas, y sirven porque nombran
  > el tema. Lo que se descarta es todo fragmento de menos de 40 palabras, sea de quien sea, porque
  > es demasiado corto para entenderse solo. En las respuestas, lo que dice un reportero nunca cuenta
  > como respaldo: queda como "ambiguo", porque puede estar preguntando o cuestionando, no afirmando.
- **Demo web pública** (R11): consulta libre con fechas; TF-IDF y BM25 lado a lado con una explicación
  breve; entidades resaltadas por tipo con leyenda; respuesta en tarjetas con su cita; pasajes
  identificados por fecha, título e interlocutor, nunca por ID; ejemplo guiado precargado (Dos Bocas).

---

## 4. Congelaciones e invalidación v2

| Momento | Qué se congela | Mecanismo | Fecha objetivo |
| --- | --- | --- | --- |
| Aprobación de este PRD | D23 a D36, reglas de agregación, ganador y selección | Etiqueta `v2-inicio` | Sáb 14 |
| Antes del lote 1 | Criterio de relevancia, asignación del lote 1 | `data/v2/asignacion_juicios.csv` (lote 1) | Sáb 14 |
| Antes del muestreo | Exclusión del ámbito v1, semillas, tamaños | Manifiestos con hash en `anotaciones/v2/` | Sáb 14 (selección y A) y dom 15 (B) |
| Antes del pool v2 | Q11 a Q15, lematizador, 8 variantes | `data/consultas.csv` v2, `salida/v2/ranking_8_variantes.csv` | Dom 15 |
| Antes del lote 2 | Pool v2, asignación del lote 2 | Hash en `salida/v2/04_pool.csv` | Dom 15 en la noche |
| Antes de la pasada 2 | Criterio FECHA v2, reglas FECHA v2 | `reglas-fecha-v2` | Cuando llegue el repo (≤ jue 19) |
| Antes de evaluar el gold v2 | NER v2 | `data/modelo_ner.json` v2 | Jue 19 |
| Cierres humanos | Juicios v2, gold v2 | `cierre_juicios_v2.json`, `cierre_gold_v2.json` | Vie 20 |
| Entrega | Todo | `v2.0-entrega` | Mar 24 |

Invalidación: rige PRD v3.0 §11.1. Casos nuevos:

- **Cambiar el lematizador después del pool v2:** invalida pool, asignación y juicios del lote 2.
- **Cambiar Q11 a Q15 después del pool:** invalida sus juicios, su gold parte B y sus tablas.
- **Cambiar el criterio de relevancia después del lote 1:** los juicios v1 de Diego, Luis y Arturo dejan de
  contar.
- **Cambiar el NER después de evaluar el gold v2:** la cifra nueva es exploratoria.

---

## 5. Paquetes de trabajo de Claude Code

Cada paquete dice qué skill del arnés cargar, qué archivos toca, qué prueba lo cierra y de qué depende.
El dueño es quien opera Claude Code para ese paquete. P0 bloquea la entrega; P1 mejora la defensa;
P2 se recorta primero.

### WP-00 · Arnés v2 (Diego · P0 · sáb 14)

- `CLAUDE.md`: este PRD como fuente de verdad junto al v3.0; tabla de propiedad (6.2); regla de
  preguntar quién opera y qué WP.
- Skills a actualizar:
  - `session-resume`: progreso por paquete en `docs/harness/progreso/<wp>.md`, consolidado en
    `PROGRESS.md`.
  - `integridad-congelacion`: sección 4 de este PRD.
  - `pool-juicios-ir`: varios anotadores y agregación.
  - `gold-anotacion`: doble anotación, adjudicación, muestra v2 y pasadas.
  - `ner-modelo`: varios candidatos.
  - `laminas-demo`: estilo de venta.
  - `entrega-reproducible`: `v2.0-entrega`.
- Skill nueva `demo-web`.
- `docs/harness/ARCHITECTURE.md`: diagrama v2.
- `docs/decisiones.md`: entrada de aprobación de este PRD y del número de 6 integrantes.
- **Cierra con:** `make test` verde y la etiqueta `v2-inicio`.

### WP-01 · App multianotador (Diego · P0 · bloqueante, sáb 14 antes de las 16:00)

- **Skill:** `app-anotacion`.
- **Archivos:** `src/mtx/app/app.py`, `componentes.py`, `vista_juicios.py`, `vista_estado.py`,
  `cli.py`; módulo nuevo `src/mtx/anotadores.py`; `config/v2/anotadores.yaml` (id, nombre, lotes).
- **Comportamiento:**
  - Al abrir pide quién anota (lista cerrada en `config/v2/anotadores.yaml`, sin contraseña) y lo
    recuerda en la sesión y en la URL (`?anotador=arturo`).
  - Muestra solo los pares asignados a esa persona.
  - Escribe de forma atómica en `anotaciones/juicios_v2/<anotador>.csv`.
  - Nunca muestra juicios de otros.
  - La pestaña Estado muestra el avance propio y, solo al coordinador, el avance por persona sin los
    valores.
- **Alternativa CLI:** `make app-cli ANOTADOR=luis`, con la misma persistencia.
- **Pruebas:** extender T15 (`tests/test_app*.py`). Dos anotadores sobre el mismo par escriben
  archivos distintos; un par no asignado no aparece; la app no lee archivos ajenos.
- **Cierra con:** la app pide anotador y muestra solo los pares asignados; los juicios v1 de Diego, Arturo y de
  Luis quedan importados en `anotaciones/juicios_v2/`.

### WP-02 · Asignación, agregación y acuerdo (Diego · P0 · sáb 14 y vie 20)

- **Skill:** `pool-juicios-ir`.
- **Archivos:** `src/mtx/acuerdo.py` (Fleiss, Cohen, mayoría), `scripts/04b_asignar_juicios.py`,
  `scripts/05a_agregar_juicios.py`, `tests/test_acuerdo.py`.
- **Asignación:** reparte por lotes con la carga de 2.3, con semilla 42. Escribe
  `data/v2/asignacion_juicios.csv`; no cambia si se vuelve a correr.
- **Agregación:**
  - Lee `anotaciones/juicios_v2/*.csv` y los juicios v1 de Diego.
  - Valida cobertura (3 juicios válidos por par), claves únicas y pares fuera del pool.
  - Escribe `salida/v2/05a_juicios_agregados.csv` y exporta `juicios_relevancia.csv`.
- **Acuerdo:** escribe `salida/v2/05a_acuerdo.csv` y `.json`.
- **Pruebas:** kappa contra un ejemplo calculado a mano; mayoría con omitidos; cobertura incompleta
  que falla con mensaje claro.

### WP-03 · Lematización y ocho variantes (Diego · P0 · sáb 14 y dom 15)

- **Skill:** `indice-ranking`.
- **Archivos:** `src/mtx/preproceso.py` (`lematizar`, `tokenizar_pasaje(..., raiz="stem"|"lema")`),
  `src/mtx/indice.py`, `src/mtx/ranking.py` (`variantes_v2`), `scripts/02_indice.py --raiz lema`,
  `scripts/03_ranking.py --v2`, `pyproject.toml` (spaCy y el modelo con versión fija).
- **Rendimiento:** `nlp.pipe` por lotes con varios procesos. Lemas guardados en
  `data/v2/tokens_lema.parquet`, ignorado por git, con hash en el manifiesto.
- **Salidas:**
  - `salida/v2/ranking_8_variantes.csv`;
  - `salida/v2/02_comparacion_stem_lema.md`: vocabulario, ejemplos como "maya" frente a "mayo", y el
    idf de los términos de cada consulta.
- **Pruebas:**
  - las 4 variantes stem coinciden byte a byte con `ranking.csv` v1;
  - el lema de "vacunas" es "vacuna";
  - "Maya" y "mayo" no comparten lema;
  - mismas fórmulas que v1 (T03 a T06).

### WP-04 · Consultas Q11 a Q15 (Diego con Arturo · P0 · sáb 14 y dom 15)

- **Skill:** `corpus-segmentacion` (descubrimiento).
- **Archivos:** `config/v2/candidatos_q11q15.yaml`, `config/v2/consultas_q11q15.yaml`,
  `scripts/00_descubrir_consultas.py --v2`, `scripts/00b_consultas.py`.
- **Proceso:**
  - Claude Code propone 10 a 12 candidatas con conteos por año y ejemplos de pasaje.
  - Diego y Arturo eligen 5 y redactan tema, ventana y pregunta. `[VALIDAR]`
  - Después se agregan sus campos a `config/tablas_respuesta.yaml`.
- **Cierra con:** `data/consultas.csv` con 15 filas; Q1 a Q10 sin cambios byte a byte.

### WP-05 · Pool v2 (Diego · P0 · dom 15)

- **Skill:** `pool-juicios-ir`.
- **Archivos:** `src/mtx/pool.py` (unión de 8 variantes), `scripts/04_pool.py --v2`.
- **Salidas:** `salida/v2/04_pool.csv` y `salida/v2/04_pool_resumen.csv`.
- **Pruebas:**
  - el pool v2 contiene los 176 pares v1;
  - el tope de 450 se aplica como dice D27;
  - el hash se recalcula igual.

### WP-06 · Evaluación IR v2 y robustez (Diego · P0 lo oficial, P1 lo demás · vie 20 y sáb 21)

- **Skill:** `pool-juicios-ir`.
- **Archivos:** `src/mtx/evaluacion.py` (bootstrap, permutación, sensibilidad, nDCG),
  `scripts/05_evaluar_ir.py --v2`.
- **Salidas:**
  - `resultados_ir.csv` (kit) y `salida/v2/05_ir_8_variantes.csv` (kit sobre las 8);
  - `salida/v2/05_robustez.csv`: intervalos, valores p, sensibilidad e inflación;
  - `data/mejor_modelo.json` v2.
- **Pruebas:** bootstrap y permutación con semilla reproducible; la inflación v1 contra v2 coincide con
  el kit en un ejemplo sintético.

### WP-07 · Booleano exploratorio (Diego · P1 · dom 15 a lun 16)

- **Skill:** `indice-ranking`.
- **Archivos:** `src/mtx/booleano.py`, `scripts/03b_booleano.py`.
- **Salidas:** `salida/v2/03b_booleano.csv` (consulta, operador, pasajes devueltos, dentro de la
  ventana) y `salida/v2/03b_ejemplo_huachicol.md`.
- **Pruebas:** AND y OR sobre un índice de juguete.

### WP-08 · Muestreo v2 (Diego · P0 · sáb 14 para selección y A, dom 15 para B)

- **Skill:** `gold-anotacion`.
- **Archivos:** `src/mtx/muestreo.py` (exclusión del ámbito v1, partes), `scripts/08b_muestra_gold.py --v2`.
- **Salidas:** `anotaciones/v2/muestra_seleccion.csv`, `muestra_gold_a.csv`, `muestra_gold_b.csv`,
  con hashes de texto.
- **Pruebas:**
  - disjuntas entre sí, con el gold v1 y con el ámbito v1;
  - una por consulta en selección y A, dos por consulta en B;
  - mismo resultado al volver a correr.

### WP-09 · Gold doble, pasadas y adjudicación (Diego · P0 · sáb 14)

- **Skill:** `gold-anotacion` y `app-anotacion`.
- **Archivos:** `src/mtx/app/vista_gold.py`, pestaña nueva `vista_adjudicacion.py`, `src/mtx/gold.py`
  (`validar_gold_v2`, F1 entre anotadores), `tests/test_gold.py`.
- **Comportamiento:**
  - Gold por anotador en `anotaciones/gold_v2/<anotador>.csv`, con columna `pasada` (1 o 2).
  - La pasada 1 oculta FECHA; la pasada 2 solo permite FECHA.
  - La adjudicación muestra las dos anotaciones, marca los desacuerdos y guarda la decisión del
    adjudicador en `anotaciones/gold_v2/adjudicado.csv`.
  - El adjudicador no puede ser anotador del pasaje.
  - Nunca se muestran predicciones.
- **Salida:** `salida/v2/09_acuerdo_gold.csv`, el techo humano por tipo.
- **Cierra con:** Diego y Luis anotan la selección el sábado.

### WP-10 · Comparación de NER (Luis · P0 · sáb 14 a jue 19)

- **Skill:** `ner-modelo`.
- **Archivos:** `config/ner.yaml` (candidatos con revisión fija), `src/mtx/ner_modelo.py` (adaptador
  para spaCy y GLiNER si entran), `scripts/07_ner.py --modelo <id>`, `scripts/09_comparacion_ner.py`.
- **Proceso:**
  - Verificar cada candidato y registrarlo en `salida/v2/07_candidatos_ner.md`.
  - Inferir con caché por modelo en `data/cache_ner/`; corre antes del cierre, oculto.
  - Comparar sobre la selección adjudicada → `salida/v2/09_comparacion_ner.csv`.
  - Escribir `data/modelo_ner.json` v2 antes del gold.
- **Orden:** Luis anota la selección antes de inferir sobre esos pasajes.
- **Pruebas:** mocks sin red para cada adaptador; offsets con la invariante
  `texto[inicio:fin] == texto_entidad`.

### WP-11 · FECHA v2 (Leo · P0 si el repo llega a tiempo · cuando llegue el repo, ≤ jue 19)

- **Skill:** `reglas-gazetteer`.
- **Archivos:** `src/mtx/reglas.py` (bloque FECHA), `tests/test_reglas.py`,
  `docs/fecha_v2_origen.md` (qué se tomó del repo del profesor y bajo qué licencia).
- **Restricción:** no mira `anotaciones/gold_v2/` ni el gold v1. Desarrolla con ejemplos del repo del
  profesor y frases inventadas en las pruebas.
- **Cierra con:** suite verde y `reglas-fecha-v2`. Las cifras de FECHA con reglas v1 se conservan como
  comparación.

### WP-12 · Evaluación IE v2 con referencias (Luis hasta el 20; Diego después · P0 lo oficial, P1 lo demás · vie 20 y sáb 21)

- **Skill:** `evaluacion-ie` y `fusion-normalizacion`.
- **Archivos:** `scripts/08_extraer.py --v2` (ámbito = top-10 del ganador v2 ∪ los 40 gold),
  `src/mtx/evaluacion_ie.py` (bootstrap, parcial, línea base de solo gazetteer),
  `scripts/09_evaluar_ie.py --v2`.
- **Salidas:**
  - `entidades.csv` y `resultados_ie.csv` (kit, 40 pasajes);
  - `salida/v2/09_referencias_f1.csv`: techo, línea base, intervalo y parcial;
  - `salida/v2/09_analisis_errores.csv`.

### WP-13 · Tablas de respuesta v2 (Diego · P0 · sáb 21)

- **Skill:** `tablas-respuesta`.
- **Archivos:** `config/tablas_respuesta.yaml` (Q11 a Q15), `scripts/10_tablas.py`.
- **Humano:** valoraciones de las 15 tablas, repartidas entre Gonzalo, Arturo y Bruno el sábado 21 y el
  domingo 22.

### WP-14 · Reproducibilidad v2 (Diego · P0 · lun 23 y mar 24)

- **Skill:** `entrega-reproducible`.
- **Alcance:**
  - `make all-v2` encadena los scripts v2.
  - `make validar` agrega condiciones v2: cobertura de 3 juicios, cierres, disjunción de muestras,
    etiquetas en orden y cifras del reporte presentes en `salida/v2/`.
  - Clon limpio y etiqueta `v2.0-entrega`.

### WP-15 · Demo web pública (Bruno y Leo · P0 · lun 16 a dom 22)

- **Skill:** `demo-web`, creada en WP-00.
- **Tecnología:** la deciden Bruno y Leo antes del lunes 16 y se registra. Recomendación: Streamlit que
  reusa `ranking.buscar()` y los componentes de la app, publicado en un Space de Hugging Face (PV:
  verificar límites del plan gratuito). Los artefactos pesan unos 200 MB: pasajes 70, índice 45 y
  TF-IDF 67. Streamlit Community Cloud probablemente no alcanza en memoria (PV).
- **Archivos:** `src/mtx/web/` (vistas), `src/mtx/presentacion.py` (pasaje →
  "Mañanera del 12 de marzo de 2021 · fragmento 3"), `scripts/14_publicar_demo.py`, `Dockerfile` o
  archivo del Space.
- **Requisitos:** los de D36, más un aviso cuando la consulta libre corre NER en caliente y el tiempo
  de respuesta visible.
- **Restricción D32:** datos v1 hasta los cierres del 20; datos v2 desde el sábado 21.
- **Pruebas:**
  - `presentacion.py` con fechas y títulos reales;
  - la vista no muestra `passage_id`;
  - la consulta libre fuera del corpus responde sin error.

### WP-16 · Figuras y ejemplos para láminas y reporte (Gonzalo con Diego · P0 · lun 16 a dom 22)

- **Skill:** `reporte-pdf`.
- **Archivos:** `src/mtx/figuras_v2.py`, `scripts/11b_figuras_v2.py`, `config/v2/estilo.yaml` (paleta y
  tipografía).
- **Figuras:**
  - corpus con la verificación de conteos (S2a);
  - acotaciones con ejemplos (S2b);
  - tokenización paso a paso (S4c);
  - idf como "% de pasajes que lo contienen" (S4d);
  - stem contra lema;
  - índice invertido con postings de ejemplo (R09);
  - AP explicado con una consulta y MAP en % con intervalo (S5a);
  - AP por consulta con nombres y ejes (S6);
  - P, R y F1 por tipo con techo y línea base (S7);
  - errores como patrones (S8);
  - estados de respuesta con definición (S9);
  - booleano contra BM25 (R07).
- Con datos v1 desde el lunes y regeneradas con v2 el sábado 21.
- **Pruebas:** cada figura se genera desde `salida/` y lleva título y ejes.

### WP-17 · Presentación de venta (Gonzalo con Arturo · P0 · lun 16 a mar 24)

- **Skill:** `laminas-demo`.
- Láminas a mano en PowerPoint con las figuras de WP-16, siguiendo D36 y la tabla 1.3.
- Claude Code escribe `laminas/guion_v2.md` y `docs/guia_defensa_v2.md` con fuentes, y verifica que
  cada cifra exista en `salida/`. No diseña las láminas.
- Duración objetivo de 15 a 20 min con demo (PV6). El guion asigna minutos por lámina y por persona;
  `make validar` comprueba que `Tiempo medido` quede entre 15:00 y 20:00.
- Portada y créditos con "Leo Yahir" (PV3).

### WP-18 · Revisión ciega de la presentación (Arturo · P1 · dom 22 y lun 23)

- Claude Code escribe `docs/revision_ciega_prompt.md`: una instrucción para un LLM sin contexto del
  proyecto que evalúe estructura, si se entiende sola, contraste y adecuación a un cliente de gobierno.
- Arturo exporta la presentación a PDF, la pasa a un LLM en una conversación nueva y guarda la
  respuesta en `docs/revision_ciega_respuesta.md`.
- El equipo decide qué cambios toma.

### WP-19 · Reporte y README v2 (Gonzalo y Bruno; Luis la sección IE antes del 21 · P0 · sáb 21 a mar 24)

- **Skill:** `reporte-pdf`.
- `reporte/reporte_v2.md` con las 8 secciones, comparación v1 → v2 y los tres cortes `[VALIDAR]`.
- README: equipo de 6, cifras v2, demo web y "Uso de IA" actualizado, con la revisión ciega y el repo
  del profesor.
- Nombres del equipo con "Leo Yahir" en README, reporte v2 y `docs/harness/PROGRESS.md` (PV3).

---

## 6. Flujo de trabajo en equipo con el arnés

### 6.1 Ramas y commits

- **Rama de integración `proyecto-final`**, creada desde `main` en `84ab69d`. `main` queda como está
  (v1) hasta el merge final, después de `v2.0-entrega`.
- Una rama por paquete desde `proyecto-final`: `v2/wp03-lema`, `v2/wp15-demo`, etc. Pull request a
  `proyecto-final`; Diego integra.
- Anotaciones: cada persona en `anotacion/<anotador>`, con commits que solo tocan su archivo en
  `anotaciones/juicios_v2/` o `anotaciones/gold_v2/`. Se integran a diario.
- Conventional Commits como en v1, por ejemplo `data(juicios-v2): lote 1 de luis`. Un commit por
  unidad probada.
- Los datos regenerables (`data/*.parquet`, `*.pkl`, `*.npz`) no van a git. Cada máquina los
  reconstruye con `make corpus indice ranking`, unos 2 min. Los lemas solo los necesita quien opera
  WP-03 y la demo.

### 6.2 Propiedad de archivos

| Zona | Dueño | Otros |
| --- | --- | --- |
| `src/mtx/app/`, `anotadores.py`, `acuerdo.py`, `pool.py`, `muestreo.py`, `gold.py`, `preproceso.py`, `indice.py`, `ranking.py`, `evaluacion.py`, `booleano.py` | Diego | Solo lectura |
| `src/mtx/ner_modelo.py`, `config/ner.yaml` | Luis | Solo lectura |
| `src/mtx/reglas.py` (bloque FECHA), `tests/test_reglas.py` | Leo | Solo lectura |
| `src/mtx/web/`, `presentacion.py`, archivos del Space | Bruno y Leo | Solo lectura |
| `src/mtx/figuras_v2.py`, `config/v2/estilo.yaml` | Gonzalo (con Diego) | Solo lectura |
| `laminas/` | Gonzalo y Arturo | Solo lectura |
| `reporte/`, `README.md` | Gonzalo y Bruno | Luis la sección IE |
| `anotaciones/juicios_v2/<x>.csv`, `anotaciones/gold_v2/<x>.csv` | La app, por la persona `x` | Nadie más |
| `CLAUDE.md`, `.claude/skills/`, `docs/decisiones.md`, `docs/harness/PROGRESS.md` | Diego | Proponen por pull request |

### 6.3 Progreso entre sesiones

- Cada Claude Code escribe al cerrar en `docs/harness/progreso/<wp>.md`: completado, pendiente,
  decisiones y bloqueos.
- Diego consolida en `PROGRESS.md` una vez al día.
- Las decisiones van a `docs/decisiones.md` por pull request, con fecha y autor.

### 6.4 Instalación (sáb 14, antes de anotar)

Llamada con Leo, Luis y Bruno: `git clone`, `uv`, `make setup`, `make corpus indice ranking pool`,
`make app`. `docs/reproducibilidad.md` sirve de guion. Si una máquina no puede, esa persona anota con
`make app-cli` en otra computadora, con su propio identificador.

---

## 7. Calendario

| Día | Claude Code y técnica | Humano | Puerta |
| --- | --- | --- | --- |
| **Sáb 14** | WP-00, WP-01, WP-02 (asignación), WP-08 (selección y A), WP-09; arranca WP-03; Luis arranca WP-10 | Aprobación del PRD; instalación; lote 1 completo con juicios v1 (Diego, Luis y Arturo); **selección** (Diego y Luis); Luis entrega su archivo de juicios v1 | `v2-inicio`; app multianotador en 3 máquinas |
| **Dom 15** | WP-03 termina; WP-04; WP-05; WP-08 (B); asignación del lote 2; WP-07 | Q11 a Q15 `[VALIDAR]` a mediodía; calibración de 20 min antes del lote 2; **gold A** (Diego) | Pool v2 congelado en la noche |
| **Lun 16** | WP-10 (inferencia oculta); WP-15 y WP-16 con datos v1 | Gold A (Gonzalo); **gold B** (Gonzalo y Bruno); **lote 2** (Arturo y Bruno); adjudicación de la selección (Arturo) | Tecnología de la demo decidida |
| **Mar 17** | WP-10 compara sobre la selección; WP-15, WP-16 y WP-17 | Gold B (Gonzalo); lote 2 (Leo) | — |
| **Mié 18** | WP-11 si llegó el repo; WP-15 a WP-17 | Lote 2 (Leo y Bruno); gold B (Bruno) | — |
| **Jue 19** | `modelo_ner.json` v2; `reglas-fecha-v2` | Lote 2 (Leo); pasada 2 de FECHA si hay criterio | NER v2 fijado |
| **Vie 20** | WP-02 (agregación), WP-06 oficial | Lote 2 y gold B terminan (Bruno); adjudicación A (Bruno) y B (Diego); cierres | `cierre_juicios_v2`, `cierre_gold_v2` |
| **Sáb 21** | WP-06 robustez, WP-12, WP-13; figuras con datos v2; demo con datos v2 | Valoraciones (Gonzalo, Arturo y Bruno) | Cifras v2 en `salida/v2/` |
| **Dom 22** | WP-16 final; demo publicada; guion v2 | Láminas; reporte, corte 1 | Demo pública |
| **Lun 23** | WP-14; WP-18 | Revisión ciega; reporte, cortes 2 y 3 | — |
| **Mar 24** | `make entrega` desde clon limpio | Ensayo cronometrado con `Tiempo medido: m:ss` | `v2.0-entrega` |
| **Mié 25** | Solo correcciones sin cifras | Entrega antes de las 18:00 | — |

La pasada 2 de FECHA no tiene día fijo: se asigna cuando llegue el criterio, a los mismos anotadores
de cada pasaje (D33).

---

## 8. Prioridades y recortes v2

**P0:**

- WP-00 a WP-06 (la parte oficial de WP-06), WP-08 a WP-10, WP-11 (si el repo llega a tiempo);
- WP-12 oficial, WP-13 a WP-17 y WP-19.

**P1:**

- la robustez de WP-06, WP-07 y las referencias de WP-12 (línea base, parcial e intervalos);
- WP-18.

**P2:** segundo anotador para el gold v1, nDCG, todo lo P2 de v3.0.

Si el plazo peligra, se recorta en este orden y se avisa al equipo:

1. Todo lo P2.
2. Parte B del gold → 5 pasajes (1 por consulta) en lugar de 10, decidido **antes** de sortear.
3. FECHA v2 como evaluación exploratoria (D33).
4. Línea base trivial y F1 parcial.
5. Consultas Q11 a Q15 reducidas a 3, decidido **antes** del pool v2.
6. Demo web sin consulta libre: solo las 15 consultas precalculadas.

**Nunca se recorta:**

- los 3 juicios por par con mayoría;
- la selección del NER antes del gold;
- la doble anotación de las partes nuevas;
- el modo ciego y la separación de D32;
- las cifras v1 conservadas;
- los seis CSV, el reporte y el README reproducible;
- la demo web pública con las 15 consultas.

---

## 9. Criterios de terminado

1. `make validar` con todas las condiciones v1 y v2 en OK, o con una excepción registrada.
2. `juicios_relevancia.csv` generado por agregación con 3 juicios válidos por par; acuerdo reportado.
3. `resultados_ir.csv` v2 con intervalo de confianza y prueba pareada en `salida/v2/05_robustez.csv`.
4. `resultados_ie.csv` v2 sobre 40 pasajes, con techo humano y línea base.
5. `modelo_ner.json` v2 con commit anterior al de `cierre_gold_v2.json`; `reglas-fecha-v2` anterior a
   la pasada 2.
6. Demo web pública que responde las 15 consultas y una libre, sin IDs a la vista.
7. Láminas sin rutas, con ejemplos, ejes nombrados y nombres de consulta; revisión ciega registrada.
8. Reporte v2 con la comparación v1 → v2; toda cifra rastreable a `salida/`.
9. Ensayo cronometrado registrado en `laminas/guion_v2.md`, entre 15:00 y 20:00.
10. `v2.0-entrega` desde clon limpio, con margen antes del plazo.

---

## 10. Pendientes de verificar (PV)

| PV | Qué | Quién | Antes de |
| --- | --- | --- | --- |
| PV1 a PV6 | Sección 0.3 | Equipo | Confirmados el 14 de noviembre (PV4 por defecto) |
| PV7 | Repo de FECHA del profesor: fecha y licencia | Diego pregunta | Jue 19 |
| PV8 | Paleta y tipografía del manual vigente del Gobierno de México | Gonzalo | Lun 16 |
| PV9 | Límites del plan gratuito de Hugging Face Spaces y Streamlit Cloud | Bruno | Lun 16 |
| PV10 | Disponibilidad y revisión de cada candidato NER en Hugging Face | Luis | Lun 16 |
| PV11 | spaCy `es_core_news_md` instalable en las 6 máquinas (macOS, Windows y Linux) | Diego | Dom 15 |
| PV12 | Luis y Arturo confirman que juzgaron con el criterio de relevancia, sin ver puntajes ni rangos ni los juicios de otros. Luis: que su Excel no traía rangos, puntajes ni variantes. **Cerrado el 14 de noviembre** (confirmado por medio de Diego); CSV importados | Luis y Arturo | Sáb 14 |
