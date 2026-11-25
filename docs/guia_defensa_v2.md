# Guía de defensa v2

Para estudiar antes de la presentación final. Complementa `docs/guia_defensa.md` (v1), que sigue
valiendo para TF-IDF, BM25, el filtro de fecha, las reglas y la fusión. Aquí está solo lo que
cambió en v2 y las preguntas que deja la retroalimentación del profesor (PRD v2 §1.3).

**Borrador del 24 de noviembre (Claude Code, WP-17).** Las cifras marcadas con ⟦v2⟧ se llenan
después de `make all-v2`, desde el archivo indicado. Ninguna cifra se escribe a mano.

## Qué cambió de v1 a v2

| Tema | Examen (v1) | Proyecto final (v2) | Dónde |
| --- | --- | --- | --- |
| Preguntas | 10 | 15 (Q11 a Q15: Guardia Nacional, IMSS-Bienestar, reforma eléctrica, Jóvenes Construyendo el Futuro, Acapulco tras Otis) | `data/consultas.csv` |
| Variantes de búsqueda | 4 (TF-IDF y BM25, con y sin filtro) | 8 (las mismas con raíz y con lema) | `salida/v2/ranking_8_variantes.csv` |
| Juicios de relevancia | 1 persona, 176 pares | 3 personas por par, mayoría, 320 pares | `salida/v2/04_pool_meta.json`, ⟦v2⟧ `salida/v2/05a_acuerdo.json` |
| Ganador IR | BM25 con filtro, MAP 48.4 % | ⟦v2: ganador y MAP con intervalo⟧ | `data/mejor_modelo.json`, ⟦v2⟧ `data/v2/mejor_modelo.json` |
| Modelo NER | mrm8488 (criterio técnico) | XLM-RoBERTa large de Davlan, elegido por F1 sobre la selección | `data/modelo_ner.json`, `salida/v2/09_comparacion_ner.csv` |
| Gold de entidades | 20 pasajes, 1 persona | 35 pasajes: los 20 de v1 más 15 nuevos con doble anotación y adjudicación | `docs/decisiones.md` (WP-12) |
| Lectura del F1 | solo el F1 | F1 con intervalo, techo humano, línea base y F1 parcial | ⟦v2⟧ `salida/v2/09_referencias_f1.csv` |
| FECHA | reglas v1 | reglas v2 congeladas antes del gold, evaluación exploratoria | etiqueta `reglas-fecha-v2`, D33 |

## Fórmulas nuevas

| Fórmula | Expresión | Dónde |
| --- | --- | --- |
| Mayoría | relevante si al menos 2 de 3 juicios válidos dicen 1 (D24) | `acuerdo.agregar` |
| Kappa de Fleiss | κ = (P̄ − P̄e) / (1 − P̄e), con P̄ el acuerdo observado promedio por par y P̄e el esperado por azar | `acuerdo.fleiss` |
| Kappa de Cohen | κ = (po − pe) / (1 − pe), para cada pareja de jueces | `acuerdo.cohen` |
| Intervalo del MAP | 10,000 remuestreos de las consultas con reemplazo, semilla 42; percentiles 2.5 y 97.5 | `evaluacion_v2.bootstrap_map` |
| Prueba pareada | se cambia al azar el signo de la diferencia de AP por consulta, 10,000 veces; p bilateral = (extremos + 1) / (10,000 + 1) | `evaluacion_v2.permutacion_pareada` |
| nDCG@10 | Σ rel_i / log2(i + 1), dividido entre el ideal con min(relevantes, 10) arriba; binario | `evaluacion_v2.ndcg` |
| Intervalo del F1 | 10,000 remuestreos de pasajes del gold con reemplazo, F1 micro de cada muestra | `ie_v2.bootstrap_f1` |
| F1 parcial | acierto si la predicción solapa al menos un carácter con un gold del mismo tipo en el mismo pasaje | `ie_v2.f1_parcial` |
| Techo humano | F1 exacto entre los dos anotadores de las partes A y B antes de adjudicar | `ie_v2.techo_humano` |
| Línea base | solo los diccionarios de ORG y LOC, sin reglas de fecha ni modelo | `ie_v2.referencias` |

## Preguntas probables

### Búsqueda

**¿Por qué no un modelo booleano si el idf de «huachicol» es tan alto? (R07)**
Porque el booleano no ordena: devuelve un conjunto sin decir qué fragmento es mejor, trata igual a
«huachicol» (714 fragmentos, idf 5.19) que a «programa» (12,803 fragmentos, idf 2.30) y no usa
cuántas veces aparece cada palabra. Con «Y», una pregunta larga casi no devuelve nada; con «O»,
devuelve miles. ⟦pendiente WP-07: fragmentos que devuelve cada operador⟧.
Fuentes: `salida/02_postings.md`; ⟦v2⟧ `salida/v2/03b_booleano.csv`.

**¿Qué ganaron con el lema? (S4e)**
Separa palabras que la raíz junta: «maya» y «mayo» son «may» con raíz (6,504 fragmentos), y con
lema son «maya» (4,344) y «mayo» (2,151). El vocabulario pasa de 35,891 a 68,482 términos.
⟦v2: MAP de raíz contra lema con filtro, y si la diferencia es significativa⟧.
Fuentes: `salida/v2/02_comparacion_stem_lema.md`; ⟦v2⟧ `salida/v2/05_robustez.csv`.

**¿Por qué el ganador se elige solo entre las variantes con filtro? (D28)**
Porque cada pregunta trae un periodo y el sistema siempre lo usa; las variantes sin filtro sirven
para mostrar cuánto aporta el filtro, no compiten. Si hay empate a cuatro decimales, gana BM25 con
raíz, el ganador de v1. La regla se fijó antes de ver los juicios (etiqueta `v2-inicio`).

**¿El MAP de v2 es comparable con el de v1?**
No directamente: cambiaron los juicios (tres personas en vez de una) y el pool creció de 176 a 320
pares, así que hay más relevantes conocidos y el AP de una misma lista puede bajar.
⟦v2: MAP de Q1 a Q10 solo con el pool v1 contra con el pool v2 (inflación por pool)⟧.
Fuente: ⟦v2⟧ `salida/v2/05_robustez.csv` (`inflacion_pool_v1`, `inflacion_pool_v2`).

**¿Qué pasa si se cambia la regla de mayoría? (D29)**
Lo probamos con unanimidad (3 de 3) y con al menos uno (1 de 3). ⟦v2: si el ganador cambia o no⟧.
Fuente: ⟦v2⟧ `salida/v2/05_robustez.csv` (`sensibilidad_*`).

**¿Los jueces vieron qué modelo trajo cada fragmento? (D32)**
No. La app de juicios no muestra modelo, rango ni puntaje, y cada persona juzgó en su propio
archivo sin ver los juicios de los demás. El acuerdo fue ⟦v2: kappa de Fleiss⟧.

### Extracción

**¿Está bien un F1 de ⟦v2⟧? (S7a)**
Hay que leerlo contra dos referencias: dos personas anotando el mismo texto coinciden en
⟦v2: techo humano⟧, y solo con diccionarios se obtiene ⟦v2: línea base⟧. El intervalo del 95 % es
⟦v2⟧. Con coincidencia parcial (basta con solapar), el F1 sube a ⟦v2⟧: buena parte de los errores
son de límites, no de entidades que falten.
Fuente: ⟦v2⟧ `salida/v2/09_referencias_f1.csv`.

**¿Por qué cambiaron de modelo NER? (S8c, D34)**
Comparamos cuatro modelos sobre la selección: diez fragmentos anotados por dos personas y
adjudicados, antes de evaluar el gold. Ganó XLM-RoBERTa large con F1 de 67.8 %; base, 61.3 %;
mrm8488 (el de v1), 27.1 %; spaCy, 26.2 %. mrm8488 parte el nombre del presidente en la marca de
quien habla («MANUEL LÓPEZ» en vez de «ANDRÉS MANUEL LÓPEZ OBRADOR»), y por eso acierta 0 de 8
personas en la selección.
Fuentes: `salida/v2/09_comparacion_ner.csv`, `data/modelo_ner.json`, `docs/decisiones.md`.

**¿Elegir el modelo con el gold no sería hacer trampa?**
Por eso no se hizo: la selección es un conjunto aparte, disjunto del gold, y el modelo se fijó con
commit antes del cierre del gold. `make validar` comprueba ese orden (condición 17).

**¿Qué es el techo humano y por qué no llega a 100 %?**
Es el acuerdo entre las dos personas que anotaron cada pasaje nuevo, antes de resolver
diferencias. No llega a 100 % porque los límites de una entidad son discutibles («Secretaría de
Salud» o «la Secretaría de Salud federal»). Si el sistema se acerca a ese número, ya está cerca de
lo que puede pedirse.

**¿Por qué FECHA es exploratoria? (D33)**
El repositorio de referencia del profesor llegó después del plazo, así que las reglas v2 se
escribieron y congelaron (`reglas-fecha-v2`) antes del cierre del gold, sin verlo, y se evalúan
contra un gold con el criterio de fecha de v1. ⟦v2: F1 de FECHA con reglas v1 y con reglas v2⟧.

### Respuestas y reporteros

**¿Por qué borran a los periodistas? (R08)**
No se borran. Los pasajes de reporteros se indexan: el 15.5 % del índice son preguntas, y sirven
porque nombran el tema. Lo que se descarta es todo fragmento de menos de 40 palabras, sea de quien
sea, porque es demasiado corto para entenderse solo. En las respuestas, lo que dice un reportero
nunca cuenta como respaldo: queda como «ambiguo», porque puede estar preguntando o cuestionando,
no afirmando.
Fuentes: `salida/01_limpieza.json` (`pasajes_de_reporteros_pct`), `src/mtx/corpus.py`
(`min_tokens`), `src/mtx/respuestas.py`.

**¿Qué diferencia hay entre «respaldado» y «ambiguo»? (S9)**
Respaldado: una cita textual de quien declara sostiene el dato. Ambiguo: el dato aparece, pero lo
dice un reportero o la cita no basta para afirmarlo. ⟦v2: un ejemplo de cada uno con su cita⟧.
Fuente: ⟦v2⟧ `salida/v2/respuestas.csv`.

### Proceso

**¿Cómo evitaron ver los resultados mientras anotaban? (D32)**
Las predicciones de los pasajes nuevos no se calcularon ni se subieron al repositorio hasta los
cierres. La demo de terminal y la web ocultan esos pasajes hasta el cierre del gold. Las ramas de
anotación se integraron solo cuando las dos personas de cada parte habían terminado.

**¿Cómo usaron la IA?**
⟦pendiente WP-19: lo mismo que diga la sección «Uso de IA» del README v2, con la revisión ciega⟧.
