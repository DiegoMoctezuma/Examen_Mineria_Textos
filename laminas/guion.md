# Guion de la presentación (8 minutos)

Reparto: unos 5 minutos de exposición (1 por lámina), 2 de demo y 1 de margen. Es un borrador:
cámbialo a tus palabras. Las cifras salen de `salida/` y coinciden con el reporte.

Tiempo medido: PENDIENTE (ensayar con cronómetro y escribir aquí m:ss, por ejemplo 7:40)

## Lámina 1 · Problema, corpus y pipeline (≈1 min)

- "Trabajé con 2,294 versiones estenográficas de las mañaneras, de 2018 a 2024. Cada discurso dura
  una o dos horas, así que buscar el discurso completo no sirve: la unidad es el pasaje."
- Señala el diagrama: corpus, pasajes, índice, dos modelos de ranking, juicios humanos y MAP;
  después reglas más NER, gold humano y F1, y al final tablas de respuesta.
- "Los dos bloques naranjas son trabajo humano: 176 juicios de relevancia y un gold de 20
  pasajes. Lo anoté yo a mano en una app local, sin ver lo que predecía el sistema."
- Transición: "Primero cómo partí el texto."

## Lámina 2 · Segmentación e índice (≈1 min)

- "Cada intervención se parte en ventanas de 200 palabras con paso 150; quedaron 127,739 pasajes."
- "El nombre de quien habla lo pego al inicio del pasaje para poder extraer personas, pero no lo
  indexo: si no, presidente y secretario dominarían todos los rankings."
- "Costo: el 65 % de las intervenciones de reporteros son cortas y se pierden."
- Señala la tabla: "huachicol aparece en 714 pasajes, 0.56 %: su idf es el más alto, 5.19; tren
  aparece en 5,261 y vale 3.19."
- Transición: "Con ese índice comparé TF-IDF y BM25."

## Lámina 3 · Recuperación (≈1 min)

- "BM25 con filtro de fecha es el mejor: MAP 0.484 frente a 0.295 de TF-IDF, y gana en 8 de 10."
- Señala Q1 en la figura: "TF-IDF casi no encuentra nada en Tren Maya porque el stemmer convierte
  Maya y mayo en la misma raíz."
- "La consulta más difícil es Dos Bocas: el corpus también la llama refinería Olmeca y ese nombre
  no está en la consulta. Ahí unos embeddings ayudarían."
- Transición: "Sobre los 10 pasajes de BM25 extraje entidades."

## Lámina 4 · Extracción (≈1 min)

- "Combino reglas, que son regex de fechas y montos más gazetteers, con un BERT en español. Las
  reglas las congelé con una etiqueta de git antes de anotar el gold, para no ajustarlas viendo
  el resultado."
- "F1 total: reglas 0.78, modelo 0.65, combinado 0.78; la combinación sube el recall a 0.85."
- Señala los errores: "El modelo parte los nombres escritos en mayúsculas: de ANDRÉS MANUEL
  LÓPEZ OBRADOR predice MAN. También parte Pfizer-BioNTech y confunde el Tren Maya como
  organización."
- Transición: "Con esas entidades armo respuestas con evidencia; lo muestro en vivo."

## Lámina 5 · Demo y limitaciones (≈1 min + demo)

- "Respaldado quiere decir que el texto lo afirma junto al valor, no que sea verdad."
- Limitaciones: gold pequeño, NER elegido sin conjunto de selección, patrones laxos.

## Demo (2 min)

Comando: `make demo Q=Q3` (tarda menos de 1 s con los artefactos guardados).

1. Panel de arriba: consulta, ventana de fechas y pregunta.
2. Tabla lado a lado: "a la izquierda TF-IDF, a la derecha BM25; en Q3 comparten 5 de los 10 pasajes".
3. Pasajes con entidades: "verde LOC, cian ORG; negrita es que reglas y modelo coinciden. Aquí
   se ve el error de mayúsculas: MAN como persona."
4. Tabla de respuesta: "respaldados en verde, ambiguos en amarillo, con el pasaje de la cita".

Si el profesor pide una consulta libre: `make demo CONSULTA="vacunas Pfizer" DESDE=2021-01-01
HASTA=2021-12-31`. Avisa que corre el NER en caliente (20 a 40 s) y que no tiene MAP ni F1.
Contingencia, solo si falla la máquina: `laminas/demo_Q3_salida_guardada.txt`, anunciándolo como
salida guardada.

## Preguntas probables (respuestas cortas)

| Pregunta | Respuesta | Evidencia |
| --- | --- | --- |
| ¿Por qué pasajes y no discursos? | Un discurso de 8,500 palabras habla de muchos temas; el pasaje concentra el tema y la extracción corre sobre 10 pasajes | D02, reporte §1 |
| ¿Qué limpiaste? | 7,338 acotaciones entre corchetes y 5 duplicados; todo auditado | salida/01_limpieza.json |
| ¿Por qué la marca no se indexa? | Se repite en cada ventana e inflaría el tf de presidente o secretario; sí se usa para extraer PER | D03 |
| idf de huachicol | ln(1 + (N − df + 0.5)/(df + 0.5)) con N = 127,739 y df = 714 → 5.19 | salida/02_postings.md |
| ¿Por qué tu BM25 no coincide exacto con rank_bm25? | rank_bm25 usa otro idf (con piso epsilon para términos frecuentes); las pruebas comparan contra una subclase con mi idf | tests/test_ranking.py |
| ¿Qué cambia con el filtro? | Quita pasajes fuera del periodo; en Q6 9 y 10 de los 10 sin filtro estaban fuera | salida/03_excluidos_por_filtro.csv |
| ¿Por qué juzgar el tema y no la fecha? | Para que el juicio no dependa del modelo; la ventana se aplica después en una segunda vista | D07 |
| ¿Cómo evitaste usar el gold para elegir el NER? | El NER se fijó por criterio técnico y se guardó en un commit anterior al gold; las reglas se congelaron con una etiqueta | D09, D15, git log |
| ¿Qué entidad falló más? | PER del modelo (F1 0.24) por fragmentos en la marca en mayúsculas | salida/09_resumen_errores.csv |
| ¿Qué respuestas tienen evidencia? | Las tablas marcan respaldado o ambiguo; Q1 montos y Q8 organizaciones empresariales quedaron sin evidencia | salida/respuestas.csv |
| Con embeddings, ¿qué mejoraría? | Consultas con sinónimos: Q3 (refinería Olmeca), Q4 (AIFA), Q6 (robo de combustible), Q7 (pensión del Bienestar) | reporte §3 |
