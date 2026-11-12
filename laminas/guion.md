# Guion de la presentación de Minería de Textos

Versión para las 12 diapositivas del PowerPoint final del equipo: `laminas/Presentacion_Mineria_de_Textos.pptx`.
El reparto entre integrantes es una propuesta para ensayar. Los nombres y el orden por apellido coinciden con la portada y el cierre.

**Duración objetivo: 7 minutos**, incluidos 2 minutos de demo. Queda 1 minuto de margen hasta el límite de 8 minutos. Estos tiempos son una planificación, no un ensayo medido.

Las indicaciones en cursiva no se leen en voz alta. Las fuentes sirven para preparar la defensa.

## Reparto sugerido

| Integrante | Diapositivas | Bloque | Tiempo objetivo |
| --- | --- | --- | --- |
| Carpio Angeles, Leo Yair | 1 a 3 | Presentación, corpus y consultas | 1:05 |
| Jaramillo Salmerón, Arturo | 4 y 5 | Índice y comparación de modelos | 1:00 |
| Mera Montiel, Gonzalo Sebastian | 6 y 7 | Resultados por consulta y extracción | 1:15 |
| Moctezuma Ramirez, Diego Rafael | 8 y 9 | Errores y respuestas con evidencia | 1:00 |
| Ramirez Maza, Luiz | 10 a 12 | Demo, limitaciones y agradecimiento | 2:40 |

## 1. Recuperación y extracción de información en las mañaneras

**Expone: Leo. Tiempo: 15 s. Acumulado: 0:15.**

Buenas tardes. Presentamos un sistema que busca información en las versiones estenográficas de las mañaneras. Primero recupera pasajes relevantes y después extrae entidades para construir respuestas con su evidencia textual.

*Avanza a las cifras del corpus. Los integrantes ya aparecen en la portada; no hace falta leer la lista completa.*

## 2. Seis años de mañaneras, divididos en pasajes

**Expone: Leo. Tiempo: 30 s. Acumulado: 0:45.**

El corpus reúne 2,294 discursos, de diciembre de 2018 a septiembre de 2024. Un discurso mezcla muchos temas y tiene más de 8,500 palabras de mediana. Por eso la búsqueda trabaja con pasajes: ventanas de 200 palabras y paso de 150. La limpieza eliminó 7,338 acotaciones y cinco duplicados. El índice contiene 127,739 pasajes.

*Señala la cifra de pasajes y la franja de segmentación.*

Fuentes: `salida/01_estadisticas_corpus.json`, `salida/01_limpieza.json`.

## 3. Diez temas con una ventana de fechas y una pregunta

**Expone: Leo. Tiempo: 20 s. Acumulado: 1:05.**

Las consultas cubren diez obras y programas. Las ocho primeras vienen del kit del profesor. Q9 y Q10 corresponden al Banco del Bienestar y al Tren Interoceánico. Cada consulta combina un tema, un periodo y una pregunta sobre organizaciones, personas, lugares, fechas o cantidades.

*Señala Q9 y Q10. Da paso a Arturo.*

Fuente: `data/consultas.csv`.

## 4. Huachicol es el término más discriminante

**Expone: Arturo. Tiempo: 30 s. Acumulado: 1:35.**

El preprocesamiento normaliza el texto, elimina stopwords y aplica stemming. El índice invertido guarda en qué pasajes aparece cada raíz y cuántas veces. Huachicol aparece en 714 pasajes, solo el 0.56 % del corpus, y tiene el idf más alto de estos cuatro términos: 5.19. La marca del interlocutor queda fuera del índice para evitar que sus repeticiones dominen el ranking.

*Compara la barra de huachicol con la de tren. idf mide cuánto discrimina un término dentro de esta colección.*

Fuentes: `salida/02_postings.md`, `salida/02_tokens_consultas.md`, `docs/decisiones.md` (D03).

## 5. BM25 con filtro de fecha obtiene el mayor MAP

**Expone: Arturo. Tiempo: 30 s. Acumulado: 2:05.**

La comparación usa 176 juicios manuales de relevancia. La app ocultó el modelo, el rango y el puntaje durante la anotación. BM25 con filtro obtiene MAP de 0.484, frente a 0.295 de TF-IDF con filtro. MAP resume la precisión promedio de las diez consultas. BM25 controla cuánto pesa repetir un término y normaliza por longitud; esa es una explicación probable de su ventaja.

*Señala la primera variante y el valor central de los anillos. Da paso a Gonzalo.*

Fuentes: `resultados_ir.csv`, `salida/04_pool_resumen.csv`, `docs/decisiones.md` (D06 a D08).

## 6. BM25 gana en ocho de las diez consultas

**Expone: Gonzalo. Tiempo: 30 s. Acumulado: 2:35.**

Con filtro de fecha, BM25 gana en ocho consultas. TF-IDF lo supera en huachicol y salario mínimo. En Tren Maya, TF-IDF obtiene AP de 0.025 y BM25 de 0.543. El stemming reduce Maya y mayo a la misma raíz, lo que introduce ruido. Dos Bocas es la consulta más difícil con filtro: el corpus también usa refinería Olmeca, un nombre ausente de la consulta.

*Señala Q1, Q6 y Q8. Las barras comparan AP por consulta, no MAP.*

Fuentes: `salida/05_ir_ganador_por_consulta.csv`, `salida/02_tokens_consultas.md`.

## 7. Reglas y modelo juntos alcanzan F1 de 0.78

**Expone: Gonzalo. Tiempo: 45 s. Acumulado: 3:20.**

La extracción compara reglas con un modelo BERT de NER en español. Las reglas usan expresiones regulares para fechas y montos, listas de organizaciones y lugares, y la marca del interlocutor. El modelo reconoce personas, organizaciones y lugares, pero no cubre fechas ni montos.

La evaluación usa un gold manual de 20 pasajes y 163 entidades. El F1 total es 0.775 con reglas, 0.651 con el modelo y 0.784 al combinarlos. La combinación aumenta el recall de 0.687 a 0.847, aunque reduce la precisión. Recupera más entidades y también introduce más falsos positivos.

*Señala la fila TOTAL y la franja de recall. Da paso a Diego.*

Fuentes: `resultados_ie.csv`, `salida/09_ie_detalle.csv`, `reporte/reporte.md`, secciones 4 y 5.

## 8. El modelo fragmenta nombres y confunde tipos

**Expone: Diego. Tiempo: 30 s. Acumulado: 3:50.**

Estos son errores reales. En el primer ejemplo, el modelo extrae MAN en lugar del nombre completo de Andrés Manuel López Obrador. También recorta Pfizer-BioNTech a Pfizer y clasifica Tren Maya como organización, aunque el criterio del gold lo trata como lugar. El peor tipo del modelo es PER, con F1 de 0.24. Sin un experimento adicional, no podemos atribuir estos fallos únicamente a las mayúsculas.

*Compara cada referencia manual con la predicción de la derecha.*

Fuente: `salida/09_analisis_errores.csv`. Ejemplos: `1122_3`, `1188_80` y `326_25`.

## 9. Cada respuesta conserva la cita que la respalda

**Expone: Diego. Tiempo: 30 s. Acumulado: 4:20.**

Las tablas conservan el valor extraído, su cita y el identificador del pasaje. Hay 149 valores respaldados y 78 ambiguos. La etiqueta respaldado indica que el texto afirma la relación según los patrones del sistema; no verifica que el hecho sea verdadero. En el top-10 faltó evidencia para montos de Q1 y organizaciones empresariales de Q8. Las valoraciones manuales también documentan relaciones mal asignadas.

*Señala la franja inferior. Da paso a Luiz para la demo.*

Fuentes: `salida/respuestas.csv`, `salida/tablas_respuesta/`, `reporte/reporte.md`, sección 6.

## 10. Dos Bocas: del ranking a una respuesta con evidencia

**Expone y opera: Luiz. Tiempo: 2 min. Acumulado: 6:20.**

Ahora vamos a recorrer Q3, sobre la refinería de Dos Bocas en Tabasco. La consulta busca organizaciones, personas responsables y montos de inversión entre 2019 y 2022. La tabla de la diapositiva es un extracto guardado; en la terminal veremos la salida completa.

### 0:00 a 0:20 — Consulta y ventana

*Cambia a la terminal, abierta en la raíz del proyecto, y ejecuta:*

```bash
make demo Q=Q3
```

Aquí están el tema, el periodo y la pregunta de extracción. BM25 con filtro define los pasajes sobre los que corre la extracción.

### 0:20 a 0:50 — Comparación del ranking

*Muestra el top-10 de los dos modelos.*

TF-IDF aparece a la izquierda y BM25 a la derecha. En esta consulta comparten cinco de los diez pasajes. Los dos primeros coinciden, pero el tercero cambia: TF-IDF devuelve 1759_60 y BM25 devuelve 2033_3.

### 0:50 a 1:20 — Entidades por pasaje

*Baja a las entidades del pasaje `2033_3`.*

El color distingue el tipo de entidad y el método indica si viene de reglas, del modelo o de ambos. Aquí el modelo etiqueta MAN como persona: es un fragmento del nombre, del mismo tipo que vimos en el análisis de errores.

### 1:20 a 1:50 — Tabla y evidencia

*Muestra un valor respaldado, su pasaje y su cita. Contrástalo con uno ambiguo.*

La tabla permite volver al texto que originó cada valor. Esta cita es lo que podemos revisar para decidir si la relación responde a la pregunta. Los casos ambiguos conservan su evidencia y requieren revisión.

### 1:50 a 2:00 — Regreso a la presentación

*Regresa al PowerPoint y avanza a limitaciones.*

El recorrido conecta el ranking con las entidades y, finalmente, con una respuesta que conserva su fuente.

### Contingencia

Si falla la ejecución, abre `laminas/demo_Q3_salida_guardada.txt` y anuncia:

> Esta es una salida guardada de la consulta Q3, no una ejecución en vivo. La usaremos para recorrer las mismas secciones.

La búsqueda libre queda para preguntas, si sobra tiempo:

```bash
make demo CONSULTA="refinería de Dos Bocas en Tabasco" DESDE=2019-01-01 HASTA=2022-12-31
```

Si la app la trata como consulta libre, ejecuta NER en caliente y no le atribuyan las métricas de la evaluación oficial. No es necesario ejecutarla durante los dos minutos de demo.

Fuentes: `laminas/demo_Q3_salida_guardada.txt`, `salida/03_solape_modelos.csv`, `README.md`.

## 11. Lo que falta para confiar más en los resultados

**Expone: Luiz. Tiempo: 30 s. Acumulado: 6:50.**

El gold tiene solo 20 pasajes, con seis fechas y tres montos, así que esas métricas tienen poco soporte. Además, el mínimo de 40 palabras descarta el 64.94 % de las intervenciones de reporteros. El NER se eligió por criterio técnico, sin un conjunto para comparar modelos. Por último, los patrones de respuesta todavía aceptan algunas relaciones incorrectas. Estas limitaciones acotan lo que podemos concluir.

*Señala los tres bloques y la franja inferior.*

Fuentes: `salida/01_limpieza.json`, `resultados_ie.csv`, `docs/decisiones.md` (D02, D09), `reporte/reporte.md`, secciones 6 y 7.

## 12. Gracias por escuchar

**Expone: Luiz. Tiempo: 10 s. Acumulado: 7:00.**

Gracias por escuchar. Quedamos atentos a sus preguntas y comentarios.

*Mantén esta diapositiva durante las preguntas. Cualquier integrante puede complementar las respuestas.*

## Preguntas probables

| Pregunta | Respuesta breve | Evidencia |
| --- | --- | --- |
| ¿Por qué pasajes y no discursos completos? | Un discurso mezcla muchos temas. El pasaje concentra el contexto que usa el ranking y reduce el texto que recibe la extracción. | D02; `reporte/reporte.md`, sección 1 |
| ¿Por qué ventanas de 200 palabras y paso de 150? | Es la configuración base del kit. El solapamiento conserva contexto entre ventanas. No se hizo un experimento de sensibilidad para afirmar que sea la mejor configuración. | D02; `salida/01_limpieza.json` |
| ¿Qué ruido eliminaron? | 7,338 acotaciones de transcripción, cuatro duplicados exactos y uno casi duplicado. La auditoría conserva las eliminaciones. | `salida/01_limpieza.json`; `salida/01_auditoria_corpus.csv` |
| ¿Por qué no indexan la marca del interlocutor? | Repetir nombres y cargos en cada ventana inflaría su frecuencia. La marca sí se conserva para extraer personas. | D03 |
| ¿Qué es el índice invertido? | Un mapa de cada raíz a los pasajes donde aparece, con su frecuencia. Evita recorrer todo el corpus para cada consulta. | `salida/02_postings.md`; `src/mtx/indice.py` |
| ¿Cómo obtienen el idf de huachicol? | `ln(1 + (N − df + 0.5)/(df + 0.5))`, con `N = 127,739` y `df = 714`, da aproximadamente 5.19. | `salida/02_postings.md` |
| ¿Por qué BM25 puede superar a TF-IDF? | BM25 satura el efecto de repetir un término y normaliza por longitud. Es una explicación probable de estos resultados, no una garantía para otros corpus. | `src/mtx/ranking.py`; `resultados_ir.csv` |
| ¿Por qué no coincide exactamente con `rank_bm25`? | La implementación usa un idf positivo con `1 +`. La librería utiliza otro idf y un piso epsilon; las pruebas comparan una subclase con la misma fórmula. | `tests/test_ranking.py`; `docs/guia_defensa.md` |
| ¿Qué diferencia hay entre AP y MAP? | AP resume la precisión en las posiciones relevantes de una consulta. MAP promedia la AP de las consultas evaluadas. | `kit/evaluar.py`; `docs/guia_defensa.md` |
| ¿Qué cambia con el filtro de fecha? | Excluye pasajes fuera del periodo solicitado. En Q6, sin filtro, quedan fuera de su ventana nueve de los diez de TF-IDF y los diez de BM25. | `salida/03_excluidos_por_filtro.csv` |
| ¿Por qué juzgar el tema sin usar la fecha? | Se fijó la relevancia temática independientemente del modelo. La evaluación complementaria exige además que el pasaje esté dentro de la ventana. | D07; `salida/05_juicios_con_ventana.csv` |
| ¿Cuál fue la consulta más difícil? | Dos Bocas, según el mejor AP con filtro por tema. El nombre alterno refinería Olmeca no aparece en la consulta. | `salida/05_ir_ganador_por_consulta.csv` |
| ¿Cómo evitaron usar el gold para ajustar el sistema? | El modelo se fijó por criterio técnico antes del gold y las reglas se congelaron con una etiqueta de Git. No hubo un conjunto independiente para comparar modelos NER. | D09, D15; historial de Git |
| ¿Qué cuenta como acierto en extracción? | Deben coincidir el pasaje, el tipo y los límites exactos del fragmento. Detectar solo una parte del nombre no cuenta como acierto. | `kit/evaluar.py`; `salida/09_ie_detalle.csv` |
| ¿Por qué combinar no mejora mucho el F1? | El recall sube de 0.6871 a 0.8466, pero la precisión baja de 0.8889 a 0.7302. El F1 pasa de 0.7751 a 0.7841. | `resultados_ie.csv`, tipo TODOS |
| ¿Las mayúsculas causan la fragmentación? | Los errores aparecen en marcas escritas en mayúsculas, pero no hubo un experimento de capitalización que permita atribuirles la causa. | `salida/09_analisis_errores.csv`; `reporte/reporte.md`, sección 5 |
| ¿F1 de 1.000 en MONTO significa que el sistema es perfecto? | No. El gold contiene solo tres montos. Esa muestra no permite generalizar el resultado. | `resultados_ie.csv` |
| ¿Respaldado equivale a respuesta correcta? | Es una etiqueta automática de evidencia textual. Puede aceptar relaciones incorrectas y no verifica la verdad del hecho; las valoraciones manuales señalan estos problemas. | `salida/respuestas.csv`; `reporte/reporte.md`, sección 6 |
| ¿Qué quedó sin evidencia? | Montos para Q1 y organizaciones empresariales para Q8, dentro del top-10 utilizado. Eso no prueba que falten en todo el corpus. | `salida/respuestas.csv` |
| ¿Qué podrían mejorar los embeddings? | Vale la pena probarlos en nombres alternos y sinónimos, como Dos Bocas y refinería Olmeca. Esa mejora todavía no está medida. | `salida/05_ir_ganador_por_consulta.csv`; `reporte/reporte.md`, sección 3 |

## Registro del ensayo

No se ha registrado un ensayo cronometrado de este guion.

| Ensayo | Fecha | Tiempo real | Estado |
| --- | --- | --- | --- |
| Exposición completa con cambios de integrante | Sin registrar | Sin medir | Pendiente |
| Demo: primera carga | Sin registrar | Sin medir | Pendiente |
| Demo: segunda ejecución, con caché | Sin registrar | Sin medir | Pendiente |

Durante el ensayo, ajusten las pausas y los relevos. Si superan ocho minutos, recorten ejemplos secundarios y la lectura de cifras; conserven los dos minutos de demo y la explicación de las limitaciones.

## Nota de edición

Este guion acompaña el PowerPoint final del equipo y es una versión manual. Sus secciones no llevan los marcadores que usa el generador anterior para copiar las notas de `laminas/laminas.pptx`, de modo que ese proceso no sustituya este orden por el del deck anterior. El PowerPoint final y sus notas no se modifican en esta edición.
