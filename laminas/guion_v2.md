# Guion de la presentación final · Recuperación y extracción de información en las mañaneras

**Borrador del 24 de noviembre (Claude Code, WP-17).** Las láminas las diseñan Gonzalo y Arturo en
PowerPoint con las figuras de `salida/v2/figuras/`. Este guion propone qué dice cada lámina, quién
la expone y cuánto dura. Las cifras marcadas con ⟦v2⟧ todavía no existen: salen de los cierres del
24 en la noche (`make all-v2`) y se llenan aquí desde el archivo que indica cada una. Ninguna cifra
se escribe a mano.

- **Público:** el equipo de comunicación de una dependencia de gobierno (R01). Problema → solución
  → evidencia → demo.
- **Duración objetivo: 18:00**, con 3:30 de demo; margen de 2:00 hasta el máximo de 20:00 (PV6).
  Es una planificación, no un ensayo.
- **Estilo (D36):** sin rutas, comandos ni IDs en las láminas; preguntas por su nombre
  («Pregunta 3 · Dos Bocas»); ejes con nombre; porcentajes; un ejemplo real en cada lámina
  técnica; limitaciones como siguientes pasos. Las fuentes de cada lámina van solo en este guion
  (R04).
- Las indicaciones en cursiva no se leen en voz alta.

Tiempo medido: pendiente (ensayo cronometrado del 25 a las 14:00; aquí se anota «m:ss»).

## Reparto propuesto `[VALIDAR]` equipo

| Integrante | Láminas | Bloque | Tiempo |
| --- | --- | --- | --- |
| Carpio Angeles, Leo Yahir | 1 a 3 y 18 | Problema, solución y demo | 5:30 |
| Arturo | 4 a 7 | Del discurso al texto que se busca | 3:10 |
| Moctezuma Ramirez, Diego Rafael | 8 a 10 y 17 | Índice, idf, booleano y respuestas | 3:00 |
| Mera Montiel, Gonzalo Sebastian | 11 a 13, 19 y 20 | Cómo medimos la búsqueda y cierre | 3:35 |
| Ramirez Maza, Luis | 14 a 16 | Extracción de entidades | 2:45 |

*Falta el apellido completo de Arturo, igual que en la portada. PV3: «Leo Yahir» en portada y
créditos.*

## 1. Encontrar en segundos lo que se dijo en seis años de mañaneras

**Expone: Leo. Tiempo: 0:20. Acumulado: 0:20.**

Buenas tardes. Les presentamos un sistema que responde preguntas sobre lo dicho en las conferencias
matutinas, y que cada respuesta la respalda con la cita exacta de donde salió.

*Portada con los nombres del equipo. Sin escudo ni logotipos oficiales.*

## 2. El problema: miles de horas de conferencias que nadie puede releer

**Expone: Leo. Tiempo: 0:50. Acumulado: 1:10.**

Entre diciembre de 2018 y septiembre de 2024 hubo 2,294 versiones estenográficas. La mediana
tiene más de 8,500 palabras. Si alguien de comunicación necesita saber qué se dijo de la
refinería de Dos Bocas, tiene que leer cientos de conferencias. Quitamos duplicados y nos
quedaron 2,289 discursos, y 2,288 tienen al menos un fragmento útil.

*Figura `s2a_corpus.png`.*

Fuentes: `salida/01_limpieza.json` (`discursos`, `discursos_excluidos`, `discursos_con_pasajes`),
`salida/01_estadisticas_corpus.json` (`palabras.mediana` = 8,502.5).

## 3. La solución: de la pregunta a la respuesta con su cita

**Expone: Leo. Tiempo: 0:50. Acumulado: 2:00.**

El sistema hace cuatro cosas. Uno: divide cada conferencia en fragmentos. Dos: con una pregunta
como «refinería de Dos Bocas en Tabasco» y un periodo, encuentra los diez fragmentos más útiles.
Tres: en esos fragmentos marca personas, organizaciones, lugares, fechas y montos. Cuatro: arma
una tabla de respuesta donde cada dato lleva la frase que lo sostiene. Lo probamos con quince
preguntas sobre obras y programas del gobierno.

*Diagrama de cuatro pasos con el ejemplo de Dos Bocas. Lo dibuja el equipo; no hay figura
generada.*

Fuente: `data/consultas.csv` (15 consultas).

## 4. Primero se limpia: las acotaciones no son palabras de nadie

**Expone: Arturo. Tiempo: 0:45. Acumulado: 2:45.**

Las versiones estenográficas traen notas del transcriptor entre las palabras: «inaudible», «inicia
video», «himno nacional». Nadie las dijo, así que no deben contar en la búsqueda. Quitamos 7,338.
La más común es «inaudible», con 3,471.

*Figura `s2b_acotaciones.png`. S2b: definir la acotación con los ejemplos de la figura.*

Fuente: `salida/01_limpieza.json` (`acotaciones_eliminadas`, `acotaciones_por_tipo`).

## 5. Fragmentos que se entienden solos, también las preguntas de la prensa

**Expone: Arturo. Tiempo: 0:50. Acumulado: 3:35.**

Cada conferencia se divide en fragmentos de 200 palabras. Los pasajes de reporteros se indexan: el
15.5 % del índice son preguntas, y sirven porque nombran el tema. Lo que se descarta es todo
fragmento de menos de 40 palabras, sea de quien sea, porque es demasiado corto para entenderse
solo. En las respuestas, lo que dice un reportero nunca cuenta como respaldo: queda como
«ambiguo», porque puede estar preguntando o cuestionando, no afirmando. En total quedan 127,739
fragmentos.

*R08: el argumento es el de PRD v2 §3.14, textual; no improvisar otra versión.*

Fuentes: `salida/01_limpieza.json` (`pasajes`, `pasajes_de_reporteros_pct` = 15.53),
`src/mtx/corpus.py` (`min_tokens = 40`), `src/mtx/respuestas.py` (estado de reporteros).

## 6. Cómo se convierte una oración en términos de búsqueda

**Expone: Arturo. Tiempo: 0:50. Acumulado: 4:25.**

Tomemos una oración real del primer resultado de Dos Bocas: «Vamos a ir a iniciar la etapa de
prueba de la refinería de Dos Bocas». Primero se pasa a minúsculas y se separa en palabras.
Después se quitan las palabras vacías que no distinguen temas, como «de», «la» o «a». Al final,
cada palabra se reduce a su raíz: «refinería» queda como «refin». Así, «refinería» y «refinerías»
cuentan como el mismo término.

*Figura `s4c_tokenizacion.png`. S4b: decir «palabras vacías que no distinguen temas», nunca
«quitar stopwords». Leer la oración de la figura, que puede cambiar con el ganador v2.*

Fuente: `salida/v2/figuras/figuras.json` (`s4c_tokenizacion`).

## 7. Raíz o lema: el lema no confunde «maya» con «mayo»

**Expone: Arturo. Tiempo: 0:45. Acumulado: 5:10.**

Cortar palabras a su raíz tiene un costo: «maya» y «mayo» quedan las dos como «may», y la búsqueda
del Tren Maya se mezcla con todo lo que pasó en mayo. Por eso agregamos una segunda forma, el lema,
que lleva cada palabra a su forma de diccionario: «maya» aparece en 4,344 fragmentos y «mayo» en
2,151, por separado. Probamos las dos formas en todos los modelos y el resultado decide cuál
queda. ⟦v2: ganó «raíz» o «lema»⟧.

*Figura `stem_lema.png`.*

Fuentes: `salida/v2/02_comparacion_stem_lema.md`; ⟦v2⟧ `data/v2/mejor_modelo.json`
(`preprocesamiento`).

## 8. El índice invertido: buscar es leer solo unas listas

**Expone: Diego. Tiempo: 0:45. Acumulado: 5:55.**

Para no leer 127,739 fragmentos en cada búsqueda, el sistema guarda un índice como el de un libro:
para cada término, la lista de fragmentos donde aparece y cuántas veces. «Huachicol» aparece en 714
fragmentos; «programa», en 12,803. Al buscar, solo se leen las listas de los términos de la
pregunta.

*Figura `r09_indice_invertido.png`. R09: señalar una lista completa de izquierda a derecha.*

Fuentes: `salida/02_postings.md`, `salida/v2/figuras/figuras.json`.

## 9. La unidad es el idf: entre más raro el término, más pesa

**Expone: Diego. Tiempo: 0:40. Acumulado: 6:35.**

No todas las palabras valen igual. En la pregunta de huachicol, «robo» aparece en el 4.68 % de los
fragmentos y «huachicol» solo en el 0.56 %. Un fragmento que dice «huachicol» casi seguro trata del
tema; uno que dice «robo» puede tratar de cualquier cosa. El idf mide esa rareza: 5.19 para
huachicol y 3.06 para robo.

*Figura `s4d_idf.png`. S4d: el título de la lámina es «la unidad es el idf».*

Fuente: `salida/v2/figuras/figuras.json` (`s4d_idf`); `salida/02_tokens_consultas.md`.

## 10. ¿Por qué no una búsqueda booleana?

**Expone: Diego. Tiempo: 0:45. Acumulado: 7:20.**

Una búsqueda booleana solo dice sí o no. Con «Y» exige todas las palabras: en Banco del Bienestar
y en Acapulco tras Otis no devuelve ningún fragmento dentro del periodo. Con «O» acepta cualquiera
y devuelve miles: 1,485 para huachicol, y 1,261 de ellos ni siquiera dicen «huachicol», porque
para el booleano «robo» vale lo mismo. Y en ningún caso dice cuál leer primero. BM25 siempre
entrega diez, ordenados, y los diez de huachicol sí hablan de huachicol.

*R07. Figura `r07_booleano.png`; el ejemplo de huachicol va en voz.*

Fuentes: `salida/v2/03b_booleano.csv` (`en_ventana`), `salida/v2/03b_ejemplo_huachicol.md`.

## 11. Cómo sabemos que la búsqueda funciona: tres personas juzgan cada resultado

**Expone: Gonzalo. Tiempo: 0:50. Acumulado: 8:10.**

Para medir, juntamos los diez mejores resultados de ocho variantes del buscador: 320 pares de
pregunta y fragmento. Tres personas del equipo juzgaron por separado cada par, sin ver de qué
modelo venía ni en qué lugar quedó. Un fragmento es relevante si al menos dos de tres dicen que sí.
El acuerdo entre jueces fue ⟦v2: kappa de Fleiss y su lectura⟧.

*S5b. Sin figura generada; basta una frase con el número de pares y el kappa.*

Fuentes: `salida/v2/04_pool_meta.json` (`pares` = 320); ⟦v2⟧ `salida/v2/05a_acuerdo.json`.

## 12. Cómo se calcula la calidad: un ejemplo con Dos Bocas

**Expone: Gonzalo. Tiempo: 1:00. Acumulado: 9:10.**

En la pregunta de Dos Bocas, el mejor modelo pone fragmentos relevantes en los lugares
⟦v2: posiciones⟧. En cada acierto medimos qué proporción de lo visto hasta ahí era relevante, y
promediamos: eso es la precisión promedio, ⟦v2: AP en %⟧ en esta pregunta. El promedio de las
quince preguntas es el MAP: ⟦v2: MAP del ganador en %⟧, con un intervalo de confianza del 95 % de
⟦v2: intervalo⟧. ⟦v2: nombre legible del ganador⟧ fue el mejor de los cuatro modelos con filtro de
fecha.

*Figuras `s5a_ap_explicado.png` y `s5a_map_por_modelo.png`. S5a: decir los porcentajes.*

Fuentes: ⟦v2⟧ `salida/v2/resultados_ir.csv`, `salida/v2/05_ir_8_variantes.csv`,
`salida/v2/05_robustez.csv` (`map_ic95_bootstrap`), `data/v2/mejor_modelo.json`.

## 13. Pregunta por pregunta

**Expone: Gonzalo. Tiempo: 0:40. Acumulado: 9:50.**

La calidad cambia con la pregunta. ⟦v2: la pregunta con mayor AP y por qué⟧. ⟦v2: la de menor AP y
por qué⟧. Comparar modelos en las mismas preguntas nos dice si la diferencia es real:
⟦v2: p-valor de la prueba pareada del ganador contra el segundo⟧.

*Figura `s6_ap_por_consulta.png`. S6: nombres de pregunta en el eje, no Qn.*

Fuentes: ⟦v2⟧ `salida/v2/05_ir_8_variantes.csv`, `salida/v2/05_robustez.csv`
(`permutacion_pareada`).

## 14. Extraer quién, qué, dónde, cuándo y cuánto

**Expone: Luis. Tiempo: 0:55. Acumulado: 10:45.**

En los fragmentos recuperados marcamos personas, organizaciones, lugares, fechas y montos. Las
fechas y los montos se reconocen con reglas; las personas, organizaciones y lugares, con
diccionarios, con la marca de quien habla y con un modelo de lenguaje. Para elegir el modelo comparamos cuatro sobre diez fragmentos anotados
por dos personas, antes de ver los resultados finales. Ganó XLM-RoBERTa large, con 67.8 % de F1;
el modelo del examen, 27.1 %.

*S8c. Puede ser una tabla de cuatro filas con el F1 de cada modelo.*

Fuentes: `salida/v2/09_comparacion_ner.csv` (filas `TODOS`), `data/modelo_ner.json`.

## 15. Qué tan bien se extrae cada tipo, y comparado con qué

**Expone: Luis. Tiempo: 1:00. Acumulado: 11:45.**

Combinando reglas y modelo, el F1 total es ⟦v2: F1 combinado TODOS en %⟧. Para saber si eso es
bueno, lo comparamos con dos referencias: dos personas anotando el mismo texto coinciden en
⟦v2: techo humano TODOS en %⟧, y usar solo diccionarios da ⟦v2: línea base TODOS en %⟧.
⟦v2: el tipo más fuerte y el más débil, con precisión y recall⟧.

*Figuras `s7a_f1_con_referencias.png` (S7a) y `s7c_prf_por_tipo.png` (S7c).*

Fuentes: ⟦v2⟧ `salida/v2/09_referencias_f1.csv`, `salida/v2/resultados_ie.csv`.

## 16. Los errores tienen patrones, y cada patrón tiene arreglo

**Expone: Luis. Tiempo: 0:50. Acumulado: 12:35.**

⟦v2: el patrón más frecuente y cuántos errores explica⟧. Su causa es ⟦v2: causa⟧ y se corrige con
⟦v2: arreglo⟧. ⟦v2: segundo patrón, causa y arreglo⟧.

*Figura `s8_errores_patrones.png`. S8a: no decir «el modelo falló»; cada patrón con su causa y su
arreglo, sacados de `salida/v2/09_analisis_errores.csv`.*

Fuentes: ⟦v2⟧ `salida/v2/09_resumen_errores.csv`, `salida/v2/09_analisis_errores.csv`.

## 17. Respuestas con evidencia: respaldado, ambiguo o sin evidencia

**Expone: Diego. Tiempo: 0:50. Acumulado: 13:25.**

Cada dato de una tabla de respuesta tiene un estado. «Respaldado» quiere decir que una cita
textual de quien declara lo sostiene. «Ambiguo», que lo dijo un reportero o que la cita no basta.
«Sin evidencia», que ningún fragmento lo menciona. ⟦v2: porcentaje respaldado del total y un
ejemplo con su cita⟧.

*Figura `s9_estados_respuesta.png`. S9: leer la definición de cada estado.*

Fuentes: ⟦v2⟧ `salida/v2/respuestas.csv`, `salida/v2/tablas_respuesta/`.

## 18. Demo: el sistema en vivo

**Expone: Leo. Tiempo: 3:30. Acumulado: 16:55.**

*Demo web pública (R11, S10). Orden sugerido: el recorrido guiado de Dos Bocas; una de las quince
preguntas con su respuesta y su cita; una consulta libre con fechas propuesta por el público.
Tener abierta la versión local (`make demo-web`) por si falla la red; no mostrar la terminal.*

## 19. Siguientes pasos

**Expone: Gonzalo. Tiempo: 0:50. Acumulado: 17:45.**

⟦v2: tres limitaciones con su mejora, tomadas de los resultados de las láminas 13, 15 y 16⟧.

*R05 y S11a: cada limitación se dice como siguiente paso con su mejora, nunca como falla.*

## 20. Gracias

**Expone: Gonzalo. Tiempo: 0:15. Acumulado: 18:00.**

Gracias. La demo queda abierta para que la prueben con sus propias preguntas.

*Créditos con «Leo Yahir» (PV3) y la dirección de la demo web.*
