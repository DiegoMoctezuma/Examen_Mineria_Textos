# Guion de la presentación (8 minutos)

Unos 5 min 40 s de exposición en 12 diapositivas y 2 min de demo (7 min 40 s según las notas). Las notas de cada diapositiva de
`laminas/laminas.pptx` son este mismo texto: `make laminas` lo copia aquí desde el deck para que no
se desincronicen. Es un borrador: cámbialo a tus palabras (en `laminas/deck/deck.js`, `addNotes`).

Tiempo medido: PENDIENTE (ensayar con cronómetro y escribir aquí m:ss, por ejemplo 7:40)

<!-- notas:inicio -->

## 1. Recuperación y extracción de información en las mañaneras

Presentación (10 s). Buenas tardes. Presento mi sistema de recuperación y extracción de información sobre las versiones estenográficas de las mañaneras.

## 2. Seis años de mañaneras en 127,739 pasajes

Corpus (40 s). Son 2,294 versiones estenográficas de 2018 a 2024. Cada discurso dura una o dos horas, con una mediana de 8,500 palabras, así que buscar el discurso completo no sirve. Quité 7,338 acotaciones como inaudible o inicia video y 5 duplicados. Cada intervención se parte en ventanas de 200 palabras con paso 150: quedan 127,739 pasajes.

## 3. Diez preguntas sobre obras y programas

Consultas (20 s). Las ocho primeras vienen del kit del profesor; la 9 y la 10 las elegí yo: Banco del Bienestar y Tren Interoceánico. Cada una tiene una ventana de fechas y una pregunta: quién participa, dónde, cuánto, cuándo.

## 4. Del discurso a la respuesta

Pipeline (30 s). Corpus, pasajes, índice invertido, ranking con dos modelos, extracción de entidades y tablas de respuesta. Las pastillas son trabajo humano: juzgué 176 pares de relevancia, anoté un gold de 20 pasajes sin ver predicciones y valoré las diez tablas.

## 5. Huachicol es el término más discriminante

Índice (30 s). Normalizo, quito stopwords con una lista ampliada para la estenográfica y aplico stemming. Huachicol aparece en 714 pasajes, 0.56 %: su idf es el más alto, 5.19. Tren aparece en más de 5 mil pasajes y vale 3.19. La marca del interlocutor no se indexa para que presidente o secretario no dominen los rankings.

## 6. BM25 con filtro de fecha recupera mejor

IR (40 s). BM25 con filtro es el mejor: MAP 0.484 frente a 0.295 de TF-IDF con filtro. La explicación probable es que BM25 satura la frecuencia y normaliza por longitud. Los juicios los hice viendo solo el tema, sin saber qué modelo recuperó cada pasaje.

## 7. BM25 gana en 8 de 10 consultas

AP por consulta (40 s). BM25 gana en 8 de 10. En Tren Maya TF-IDF casi no encuentra nada (AP 0.025) porque el stemmer convierte Maya y mayo en la misma raíz. La más difícil es Dos Bocas: el corpus también la llama refinería Olmeca y ese nombre no está en la consulta; ahí ayudarían embeddings densos.

## 8. Reglas y modelo juntos: F1 0.78

Extracción (50 s). Combino reglas (regex de fechas y montos, gazetteers de 152 organizaciones y 102 lugares, y el nombre de la marca de interlocutor) con un BERT en español. Las reglas las congelé con una etiqueta de git antes de anotar el gold. F1 total: reglas 0.78, modelo 0.65, combinado 0.78; combinar sube el recall de 0.69 a 0.85. El modelo no detecta fechas ni montos.

## 9. El modelo parte nombres escritos en mayúsculas

Errores (30 s). El peor resultado es PER del modelo (F1 0.24): en la marca, escrita en mayúsculas, el modelo parte los nombres; de ANDRÉS MANUEL LÓPEZ OBRADOR predice MAN. También parte Pfizer-BioNTech y marca el Tren Maya como organización cuando la convención lo trata como lugar. No afirmo que la causa sean las mayúsculas: sin el experimento de capitalización solo sé dónde ocurre.

## 10. Cada respuesta cita el pasaje que la respalda

Respuestas (30 s). Para cada pregunta, un valor es respaldado si su oración contiene la relación que se pide; si no, queda ambiguo con su cita. Hay 149 valores respaldados en total. Dos campos quedaron sin evidencia en el top-10. Respaldado significa que el texto lo dice, no que sea verdad. Las diez tablas tienen mi valoración en el reporte.

## 11. Demo en vivo

Demo (2 min). Comando: make demo Q=Q3. 1) Panel con consulta, ventana y pregunta. 2) TF-IDF a la izquierda y BM25 a la derecha; en Q3 comparten 5 de 10 pasajes. 3) Entidades por pasaje: color por tipo; negrita cuando reglas y modelo coinciden; aquí se ve MAN como persona. 4) Tabla de respuesta: verde respaldado, amarillo ambiguo. Consulta libre: make demo CONSULTA="..." DESDE=... HASTA=... (NER en caliente, 20 a 40 s, sin métricas). Respaldo si falla la máquina: laminas/demo_Q3_salida_guardada.txt, anunciado como salida guardada.

## 12. Lo que falta para confiar más

Cierre (20 s). El gold es pequeño, así que las cifras de FECHA y MONTO son poco estables; el modelo falla en nombres en mayúsculas; y elegí el NER por criterio técnico sin un conjunto para comparar modelos. Todo se reproduce desde un clon limpio en unos dos minutos. Gracias.

<!-- notas:fin -->

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
