<!-- Revisión ciega (PRD v2 WP-18, R06). Datos de la corrida, escritos por Arturo antes de la respuesta. -->
- **LLM:** Gemini, Neon en Alto (conversación nueva, sin proyectos, memoria ni archivos del equipo)
- **Fecha y hora:** 2026-11-25, 11:01 (CDMX)
- **PDF:** Presentacion_Mineria_de_Textos_v2.pdf (20 láminas, deck del commit 773cc39)
- **Prompt:** el de `docs/revision_ciega_prompt.md`, sin cambios

La respuesta va completa y sin editar a partir de la siguiente línea.

---

# Evaluación de la presentación: *Minería de Textos*

## 1. Qué entendiste

El sistema evita leer manualmente 2,294 conferencias (2018–2024) para consultar qué se dijo sobre un tema y periodo. Limpia y divide los textos en 127,739 fragmentos, busca los 10 más relevantes, extrae entidades clave y entrega una tabla con citas textuales. Como evidencia, muestra pruebas en 15 preguntas: búsqueda con MAP de 53.6 %, extracción con F1 de 82.7 % y 248 de 375 datos respaldados. Sin explicación oral no se entiende cómo se genera esa tabla, qué significan las métricas técnicas (`idf`, `BM25`, `MAP`, `F1`, `gold`) ni cómo luce el sistema.

---

## 2. Estructura

A nivel general, la secuencia **problema (02) → solución (03–10) → evidencia (11–17) → demostración (18) → cierre (19–20)** sí se sigue, pero está seriamente desbalanceada para una reunión de 15 a 20 minutos con demostración en vivo. Descontando 5 a 7 minutos de demostración, quedan entre 10 y 13 minutos para 19 láminas (~35 segundos por lámina), y 13 de ellas (04 a 16) se consumen explicando técnicas internas de minería de textos antes de mostrar si las respuestas le sirven al cliente (lámina 17).

### Láminas que sobran (o deben moverse a un anexo técnico)
* **Láminas 06, 07, 08, 09 y 10** (*Cómo una oración se vuelve términos de búsqueda*, *Raíz o lema*, *El índice invertido*, *La unidad es el idf* y *¿Por qué no una búsqueda booleana?*): explican fundamentos de recuperación de información que no convencen a un área de comunicación; deberían condensarse en una sola lámina que contraste una búsqueda tradicional frente al buscador propuesto.
* **Lámina 12** (*Cómo se calcula la calidad: el caso Dos Bocas*): detallar la fórmula del AP/MAP es innecesario para un cliente no técnico.
* **Lámina 14** (*Extraer quién, qué, dónde, cuándo y cuánto*): la comparación de cuatro modelos de lenguaje (`XLM-RoBERTa`, `BERT`, `spaCy`) sobra en la presentación principal y pertenece a un anexo técnico.

### Láminas que faltan
* **Generación de la tabla de respuestas y validación:** existe un vacío completo entre extraer entidades sueltas (láminas 14–16) y presentar 375 datos clasificados como *respaldado*, *ambiguo* o *sin evidencia* en una tabla (lámina 17). No se explica qué proceso construye esa tabla ni cómo asigna las etiquetas.
* **Vista previa de la herramienta:** no hay ni una sola captura de pantalla de la interfaz o de una tabla real completa antes de la lámina 18, lo cual deja al cliente sin referencia visual y a la presentación sin respaldo si falla la demostración en vivo.
* **Operación y vigencia:** la presentación tiene fecha del 25 de noviembre de 2026 (lámina 01), pero el archivo de conferencias termina en septiembre de 2024 (lámina 02); falta explicar cómo se cargan conferencias nuevas, cuánto tarda una consulta y cómo se desplegaría de forma segura en la dependencia.

### Láminas o contenidos fuera de orden
* **Lámina 02** (*El problema*): inserta una gráfica de limpieza/deduplicación (`Discursos descargados / Sin duplicados / Con al menos un fragmento útil`) y un subtítulo sobre el `15.5 %` de preguntas de reporteros que pertenecen a la preparación de datos (láminas 04–05), no al problema.
* **Lámina 05** (*Fragmentos que se entienden solos*): introduce los conceptos de `índice` y `«ambiguo»` antes de explicarlos en las láminas 08 y 17, respectivamente.
* **Lámina 07** (*Raíz o lema*): reporta resultados de `MAP` (`53.6 %` frente a `50.7 %`) y $p = 0.07$ cinco láminas antes de definir qué es `MAP` (lámina 12) y antes de explicar cómo busca el sistema (láminas 08–10).
* **Lámina 08** (*El índice invertido*): muestra una columna con valores de `idf` una lámina antes de explicar qué es el `idf` (lámina 09).
* **Lámina 19** (*Siguientes pasos*): repite el diagnóstico de límites de nombres ya expuesto en la lámina 16.

---

## 3. Se entiende sola

A continuación se detalla, lámina por lámina, lo que no se comprende sin una explicación experta:

* **Lámina 01 (Portada):** "Minería de textos" y "Recuperación y extracción de información" son términos académicos; "seis años de mañaneras" no especifica fechas (aparecen hasta la lámina 02).
* **Lámina 02 (*El problema*):** el título de la gráfica ("El 15.5 % de los fragmentos son preguntas de reporteros: se indexan porque nombran el tema") no tiene relación con las barras mostradas (conteo de discursos descargados y sin duplicados). Términos sin definir: `indexan`, `fragmento útil`, `casi duplicado` y `mediana`.
* **Lámina 03 (*La solución*):** el recuadro del paso 1 rotula `127,739 fragmentos` como "Ejemplo con Dos Bocas", cuando en realidad es el total de todo el archivo (lámina 05). No explica cómo se pasa de marcar entidades (paso 3) a construir una tabla con citas (paso 4).
* **Lámina 04 (*Primero se limpia*):** término `indexar` sin explicar. En la gráfica, la cifra de la barra superior (`«inaudible»`) aparece truncada como `3,47` en vez de `3,471`.
* **Lámina 05 (*Fragmentos que se entienden solos*):** usa `índice` y `«ambiguo»` sin definirlos. No explica cuántos fragmentos se pierden al descartar los de menos de 40 palabras ni por qué se eligió ese umbral.
* **Lámina 06 (*Cómo una oración se vuelve términos de búsqueda*):** términos sin explicar: `palabras vacías`, `Raíz (stemming, examen)` y `Lema (proyecto final)`. Tampoco se entiende por qué la palabra "mañanera" desaparece en la etapa 3.
* **Lámina 07 (*Raíz o lema*):** sigla `MAP` sin definir ni referencia de qué porcentaje es bueno o malo, estadística $p = 0.07$ sin explicación, menciones incomprensibles a `(examen)` y `(proyecto final)`, y mezcla de separador de miles (`6.504` con punto frente a `4,344` con coma).
* **Lámina 08 (*El índice invertido*):** términos `índice invertido` e `idf` sin explicar ni indicar su escala. En la última columna aparecen `Evento del...` y `Mañanera del...` sin aclarar que el archivo incluye eventos distintos a las conferencias matutinas.
* **Lámina 09 (*La unidad es el idf*):** fórmula $\text{idf} = \ln(1 + (N - \text{df} + 0.5) / (\text{df} + 0.5))$ sin definir $\ln$, $N$, $\text{df}$ ni $\text{idf}$, escrita con coma decimal (`0,5`) frente a punto decimal en las barras (`4.68 %`). Además, el título habla de `idf`, pero el eje X grafica `% de fragmentos`, por lo que el término con mayor peso (`huachicol`) aparece como la barra más corta.
* **Lámina 10 (*¿Por qué no una búsqueda booleana?*):** términos `búsqueda booleana`, `idf` y `BM25` sin explicar (`BM25` nunca se define en toda la presentación). La frase "dentro del periodo" no indica qué fechas corresponden a cada pregunta. El eje X en escala logarítmica muestra pequeñas barras visibles para el valor `0` (Banco del Bienestar y Acapulco tras Otis), lo cual resulta confuso.
* **Lámina 11 (*Tres personas juzgan cada resultado*):** no aclara quiénes fueron los jueces, cuáles son las "8 variantes del buscador" ni por qué arrojan 320 pares. `kappa de Fleiss` (`0.48`) es un término estadístico sin referencia práctica para el cliente.
* **Lámina 12 (*Cómo se calcula la calidad: el caso Dos Bocas*):** siglas y conceptos sin explicar: `BM25`, `TF-IDF`, `AP`, `MAP`, "8 relevantes conocidos" (no se indica de dónde sale el 8) e "intervalo del 95 %". En la gráfica izquierda, el eje Y dice `Fragmento recuperado` sin escala y todas las barras tienen la misma altura; las fracciones $1/2$, $2/3$, $3/6$, $4/10$ requieren explicación matemática.
* **Lámina 13 (*Pregunta por pregunta*):** siglas `AP (%)`, `TF-IDF`, `BM25` y valores $p = 0.014$ y $p = 0.07$ sin explicar. No se aclara qué significa "con filtro de fecha" frente a no usarlo.
* **Lámina 14 (*Extraer quién, qué, dónde, cuándo y cuánto*):** sigla `F1` sin definir (nunca se explica en el documento), nombres de modelos (`XLM-RoBERTa large/base`, `BERT en español · el del examen`, `spaCy`) sin contexto y frase `marca de quien habla` sin ilustrar.
* **Lámina 15 (*Qué tan bien se extrae, y comparado con qué*):** términos sin explicar: `F1 (%)`, `intervalo del 95 %`, `bootstrap sobre los pasajes del gold`, `gold` (nunca se indica cuántos pasajes totales contiene), `línea base` y `techo`. En la gráfica no se entiende por qué el sistema supera al "techo" humano en *Personas* y *Montos*, por qué el marcador humano en *Fechas* aparece sobre el `0`, ni por qué falta el marcador `Solo diccionario` en tres categorías.
* **Lámina 16 (*Cada patrón de error tiene su arreglo*):** términos `gold`, `F1`, `traslape` y `marca de quien habla` sin explicar. No se explica la diferencia entre las categorías de error más allá de la primera.
* **Lámina 17 (*Respaldado, ambiguo o sin evidencia*):** no explica de dónde salen los `375 datos` ("Valores en la tabla") ni si la clasificación en respaldado/ambiguo/sin evidencia la hace el sistema automáticamente o un equipo humano.
* **Lámina 18 (*El sistema en vivo*):** refiere a "su tabla de respuesta" sin que el público la haya visto todavía.
* **Lámina 19 (*Siguientes pasos*):** usa `gold` sin definir y reporta `vacunas (28.6 %)` sin indicar la métrica (`AP`) ni su impacto operativo.
* **Lámina 20 (*Gracias*):** la URL `examenmineriatextos-...streamlit.app` no aclara si es de acceso libre, permanente o solo una prueba temporal.

---

## 4. Ejemplos

No todas las láminas técnicas cuentan con ejemplos concretos, y varias los presentan incompletos. Las láminas **04, 06, 07, 08, 09, 10 y 12** sí utilizan casos reales del corpus, aunque la **lámina 12** muestra solo la aritmética de Dos Bocas sin enseñar un fragmento relevante frente a uno no relevante.

Las láminas técnicas que **no tienen ejemplo concreto (o lo tienen incompleto)** son:

* **Lámina 05** (*Fragmentos que se entienden solos*): no muestra un fragmento real de ~200 palabras, ni un ejemplo descartado por tener menos de 40 palabras, ni una pregunta de reportero etiquetada como «ambiguo».
* **Lámina 11** (*Tres personas juzgan cada resultado*): carece de un ejemplo real de par pregunta–fragmento que ilustre qué consideraron relevante los evaluadores y en qué discreparon.
* **Lámina 13** (*Pregunta por pregunta*): solo presenta puntajes (`90 %` en Tren Maya, `25.8 %` en Dos Bocas) sin un ejemplo que muestre por qué el buscador falló en los casos bajos.
* **Lámina 14** (*Extraer quién, qué, dónde, cuándo y cuánto*): incluye ejemplo para monto (`«50 mil millones de pesos»`) y persona (`«Rocío Nahle»`), pero omite ejemplos de fecha, organización, lugar y `marca de quien habla`, así como un caso donde `XLM-RoBERTa large` acierte y los otros modelos fallen.
* **Lámina 15** (*Qué tan bien se extrae, y comparado con qué*): cero ejemplos concretos de extracción real que expliquen la brecha entre el sistema, el acuerdo humano y "solo diccionarios", o por qué fallan las fechas (`53 %`).
* **Lámina 16** (*Cada patrón de error tiene su arreglo*): solo ejemplifica el primer error (`«Santa Lucía»` frente a `«Base Aérea Militar de Santa Lucía»`), pero omite ejemplos para los otros cuatro patrones (`Tipo equivocado`, `Entidad que nadie detectó`, `Dentro de la marca de quien habla` y `Detección que no es entidad`).
* **Lámina 17** (*Respaldado, ambiguo o sin evidencia*): da un ejemplo de dato `Respaldado` (Banco del Bienestar), pero no incluye ningún ejemplo de `Ambiguo` ni de `Sin evidencia` para demostrar cómo el sistema evita afirmar datos sin sustento.

---

## 5. Contraste y legibilidad

* **Gráficas ilegibles a distancia:**
  * **Lámina 10** (*¿Por qué no una búsqueda booleana?*): 30 barras horizontales comprimidas con etiquetas diminutas, escala logarítmica y una anotación muy pequeña sobre la línea roja (`BM25: siempre 10, ordenados`).
  * **Lámina 13** (*Pregunta por pregunta*): 60 barras muy angostas distribuidas en 15 preguntas con etiquetas diagonales pequeñas y leyenda superior apretada; difícil de seguir incluso de cerca.
  * **Lámina 17** (*Respaldado, ambiguo o sin evidencia*): 15 barras apiladas con leyenda pequeña en la parte superior derecha; los segmentos grises de `Sin evidencia` son tan estrechos que casi no se perciben.
* **Problemas de contraste y colores confusos:**
  * **Lámina 13** (*Pregunta por pregunta*): emplea dos tonos rojizos demasiado cercanos (`TF-IDF · raíz` en carmesí y `BM25 · lema` en guinda oscuro), lo que en un proyector impide distinguir rápidamente al modelo ganador del descartado.
  * **Lámina 15** (*Qué tan bien se extrae*): la barra de error sobre `Todas` es oscura sobre fondo guinda oscuro (prácticamente invisible); el rombo beige en `Fechas` queda aplastado contra el eje `0` muy cerca del texto blanco `53 %`.
  * **Láminas 12 y 14** (paneles de barras horizontales): las barras de los modelos descartados (`TF-IDF`, `BERT`, `spaCy`) usan gris verdoso claro sobre fondo crema claro, con bajo contraste bajo luz de sala.
  * **Lámina 02** (*El problema*): las tres barras tienen prácticamente la misma longitud (`2,294`, `2,289` y `2,288`), por lo que la gráfica no aporta diferenciación visual y el texto blanco dentro de la barra central se amontona junto a la cifra.
* **Recortes en gráficas:**
  * **Lámina 04** (*Primero se limpia*): el número de la primera barra se recorta a la derecha (`3,47` en lugar de `3,471`).
  * **Lámina 13** (*Pregunta por pregunta*): la etiqueta del eje X (`Pregunta`) está recortada horizontalmente por la mitad en el borde inferior de la imagen.
  * **Lámina 02** (*El problema*): la etiqueta izquierda `Con al menos un fragmento útil` roza el borde izquierdo de la gráfica.
* **Láminas sobrecargadas de texto o con letra demasiado pequeña:**
  * **Lámina 06** (*Cómo una oración se vuelve términos de búsqueda*): tabla de 5 filas con párrafos largos en tipografía pequeña, imposible de leer en menos de un minuto.
  * **Lámina 08** (*El índice invertido*): la columna derecha acumula nueve referencias extensas en letra chica.
  * **Lámina 12** (*Cómo se calcula la calidad*): condensa dos gráficas, una ecuación en el subtítulo, texto en diez columnas estrechas y un pie de página estadístico.

---

## 6. Adecuación al cliente

**Tono escolar frente a tono comercial/institucional:** el documento tiene estructura y lenguaje de **trabajo escolar**, no de propuesta para un cliente de gobierno. Se titula "MINERÍA DE TEXTOS" y "Proyecto final" (láminas 01, 18 y 20), hace referencias explícitas a evaluaciones de clase como `(stemming, examen)`, `(proyecto final)` y `BERT en español · el del examen` (láminas 06, 07 y 14), y remite a una URL llamada `examenmineriatextos-...streamlit.app` (lámina 20). Además, dedica la mayor parte del tiempo a justificar decisiones metodológicas frente a un profesor en lugar de demostrar ahorro de tiempo y control editorial para un área de comunicación.

**Limitaciones como siguientes pasos:** la intención de la **lámina 19** (*Siguientes pasos*) es correcta al emparejar cada limitación con su mejora, pero resulta insuficiente por dos razones: en la **lámina 16** se afirma que *cada* patrón de error tiene arreglo pero solo se ofrece uno de cinco, y en la **lámina 19** las mejoras se quedan en el ámbito técnico (sinónimos, diccionarios, más ejemplos de fechas) sin abordar la desactualización del corpus ni cómo reducir el tercio de datos sin respaldo.

**Riesgos y señales de falta de seriedad para un cliente de gobierno:**

* **Falta de neutralidad política (Lámina 20):** cerrar con una caricatura política del expresidente formando un corazón con las manos es inaceptable para una dependencia gubernamental; un equipo de comunicación lo percibiría como falta de profesionalismo y riesgo institucional.
* **Riesgo de desinformación en prensa (Láminas 12, 13 y 17):** que 1 de cada 3 datos en las tablas no esté respaldado (`127 de 375` en lámina 17), que en `Acapulco tras Otis` dominen los datos ambiguos (lámina 17) y que en `Dos Bocas` 6 de los primeros 10 resultados no sean relevantes (lámina 12) prende alertas rojas en comunicación social. Incluso el ejemplo destacado en la lámina 17 (`262 sucursales` del Banco del Bienestar) puede inducir a error si la tabla no aclara que la cita se refiere solo a **Oaxaca** y no al total nacional.
* **Pruebas demasiado pequeñas (Láminas 03, 14 y 15):** seleccionar el modelo con apenas 10 fragmentos anotados (lámina 14), medir fechas con solo 8 casos (lámina 15) y evaluar únicamente 15 preguntas (lámina 03) genera dudas sobre el rigor para uso institucional.
* **Corpus desactualizado y alojamiento informal (Láminas 01, 02 y 20):** presentar en noviembre de 2026 un repositorio cerrado en septiembre de 2024 y alojado en una dirección gratuita de `streamlit.app` con la palabra `examen` transmite la imagen de un prototipo pasajero.
* **Elección arriesgada para la demo (Lámina 18):** iniciar la demostración guiada con `Dos Bocas`, justo uno de los temas con peor desempeño reportado (láminas 12, 13 y 19), debilita la persuasión desde el inicio.

---

## 7. Las 5 preguntas más difíciles que haría este cliente al terminar

1. **Sobre confiabilidad editorial (Láminas 12, 13 y 17):** "Si en sus propias pruebas 1 de cada 3 datos de la tabla no está respaldado (127 de 375 en la lámina 17) y en Dos Bocas 6 de los 10 primeros resultados no son relevantes (lámina 12), ¿qué nos garantiza que mi equipo no va a publicar una cifra equivocada o fuera de contexto, como esas 262 sucursales que en realidad eran solo de Oaxaca?"
2. **Sobre actualización y vigencia (Láminas 01 y 02):** "Estamos en noviembre de 2026 y su base corta en septiembre de 2024. ¿Cómo se cargan las conferencias recientes o las de nuestra propia dependencia, con qué retraso quedan listas y quién administra ese proceso?"
3. **Sobre el tamaño real de la validación (Láminas 03, 11, 14 y 15):** "Eligieron el modelo de lenguaje con 10 fragmentos (lámina 14), midieron fechas con apenas 8 casos (lámina 15), entre los evaluadores hubo un acuerdo apenas moderado (`kappa` de 0.48 en lámina 11) y solo probaron 15 temas. ¿Qué respaldo real tenemos de que aguantará preguntas urgentes e imprevistas de los medios?"
4. **Sobre la "caja negra" de la tabla de respuestas (Láminas 03 y 17):** "Explicaron cómo buscan palabras y detectan nombres, pero nunca dijeron cómo se llena la tabla final ni quién decide si un dato es *respaldado*, *ambiguo* o *sin evidencia*. ¿El sistema usa IA generativa que puede inventar cifras o cómo se construye esa tabla?"
5. **Sobre seriedad institucional, seguridad y soporte (Láminas 01 y 20):** "La liga pública dice `examenmineriatextos` y cierran con una caricatura política. ¿Esto es un ejercicio académico o un sistema que puede operar en gobierno? ¿Dónde residen los datos, qué control de acceso tiene y cuánto cuesta mantenerlo?"

---

## 8. Los 5 cambios con más impacto (de mayor a menor)

1. **Eliminar todo lenguaje escolar y la caricatura política para proyectar seriedad institucional (Láminas 01, 06, 07, 14, 18 y 20).** Retirar la caricatura de la lámina 20, borrar las etiquetas "Proyecto final", "Minería de textos", `(examen)` y `(proyecto final)` en las láminas 01, 06, 07, 14, 18 y 20, y publicar la demo en una URL limpia con el nombre del proyecto/equipo en lugar de `examenmineriatextos`. Es el ajuste que evita un rechazo inmediato por falta de neutralidad o madurez.
2. **Compactar la teoría técnica y añadir las piezas clave que hoy faltan (Láminas 03, 06–10, 12, 17 y 19).** Sustituir las seis láminas de teoría de recuperación de información (06 a 10 y 12) por una o dos láminas en lenguaje claro (moviendo el resto a un anexo), y usar ese tiempo y espacio para explicar cómo se construye y valida la tabla de la lámina 17, mostrar una captura real de la interfaz antes de la demo y detallar en la lámina 19 cómo se actualizarían conferencias posteriores a septiembre de 2024.
3. **Traducir las métricas a resultados de negocio y reforzar con ejemplos concretos (Láminas 05, 07, 11–17).** Explicar el desempeño en términos comprensibles para comunicación social (en cuántas consultas la respuesta útil sale en los primeros resultados, cuánto tiempo ahorra frente a la revisión manual) en lugar de depender de `MAP`, `F1` y `kappa`. Incluir ejemplos faltantes en las láminas 05, 11, 14, 15 y 16, corregir el ejemplo de las 262 sucursales en la lámina 17 para aclarar su alcance estatal (Oaxaca) y añadir allí un ejemplo real de dato `Ambiguo` y `Sin evidencia` para demostrar cómo el sistema protege al usuario.
4. **Corregir errores de datos, orden lógico y legibilidad en las gráficas (Láminas 02, 04, 07, 08, 09, 10, 13 y 15).** Alinear título y gráfica en la lámina 02 (o mover la limpieza a la lámina 04); corregir la cifra recortada `3,47` en la lámina 04 y la etiqueta cortada `Pregunta` en la lámina 13; simplificar las gráficas saturadas de 30 y 60 barras en las láminas 10 y 13 (mostrando promedios y 3 o 4 casos representativos, sin barras en `0` sobre escala logarítmica); aclarar las anomalías visuales del "techo" humano en la lámina 15; y asegurar que ningún término (`MAP`, `idf`, `ambiguo`) aparezca antes de definirse.
5. **Replantear el arranque de la demostración y orientar los siguientes pasos a adopción operativa (Láminas 18 y 19).** En la lámina 18, abrir el recorrido guiado con un caso sólido (como `Tren Maya` o `Banco del Bienestar` con alcance bien acotado) y usar `Dos Bocas` después para mostrar con transparencia cómo el sistema advierte cuando la evidencia es ambigua; en la lámina 19, sumar pasos de operación real (carga periódica de nuevas conferencias, diccionarios de la dependencia y flujo de revisión editorial).

---

<!-- Lo que sigue lo escribe el equipo; la respuesta del LLM termina en la línea anterior. -->

## Qué tomamos y qué no

Deck regenerado sobre el de 773cc39 con los cambios de Arturo (`laminas/` es de Gonzalo y Arturo, PRD v2 §6.2). Lo que toca la demo (Leo) o el guion aprobado (Diego y el equipo) no se cambió aquí: se les avisa. Las figuras (`figuras_v2.py`) las corrigió Gonzalo en 3f73f42; se regeneraron con las mismas fuentes en ff53959 y el deck las usa desde b8fdac5.

**Seriedad (§6, §8.1)**
- Caricatura del cierre (20) → tomada: se quitó.
- «MINERÍA DE TEXTOS» y «Proyecto final» en 01, 18 y 20 → tomada: dicen «DATISA» y ya no hay etiqueta arriba a la derecha.
- Portada con jerga académica (01) → tomada: subtítulo «Un buscador con respuestas y citas para equipos de comunicación».
- «BERT en español · el del examen» (14) → tomada: «el de la versión anterior».
- `(stemming, examen)` y `(proyecto final)` en 06 y 07 → tomada por Gonzalo: `s4c` y `stem_lema` dicen solo «Raíz» y «Lema».
- URL con «examen» (20) → de Leo: es la dirección de la demo.

**Datos y orden**
- Subtítulo del 15.5 % sin relación con las barras (02) → tomada: se quitó de la figura.
- Fórmula del idf con coma decimal (09) → tomada: se quitó el subtítulo con la fórmula; las tarjetas dan el idf.
- Fórmula del AP en el subtítulo (12) → tomada: se quitó.
- Ejemplo del paso 1 que no es de Dos Bocas (03) → tomada: «Mañanera del 27 de junio de 2022, fragmento 68» (primer resultado de Dos Bocas) y el total de 127,739 pasa al texto del paso.
- Cómo se arma la tabla (03, 17) → tomada: el paso 4 dice que la arman reglas con lo extraído, sin IA generativa, y el mensaje de la 17 dice que el sistema clasifica con reglas (columna `regla_relacion` de `salida/v2/respuestas.csv`).
- 262 sucursales sin aclarar que son de Oaxaca (17) → tomada: «262 sucursales en Oaxaca».
- Sin ejemplo de ambiguo ni de sin evidencia (17) → tomada: Q3, «Soy Yesenia Peralta, de Business Energy, Tabasco.» (pregunta de reportero, 27 de septiembre de 2022) y Q1, montos del Tren Maya (`no_encontrado`).
- `MAP` antes de definirse (07) → tomada: el apoyo de las tarjetas dice «Calidad de búsqueda».
- Separador de miles con punto (07) → no: la tabla de la figura usa coma (6,504).
- Eje del idf en % de fragmentos (09) → no: es la figura de Gonzalo y las tarjetas dan el idf de cada palabra.
- `índice`, `indexar` y `«ambiguo»` antes de definirse (04 y 05) → abierto: láminas de Arturo, no entró en esta ronda.
- Umbral de 40 palabras y fragmentos descartados (05) → abierto: láminas de Arturo, no entró en esta ronda.

**Jerga**
- `BM25` sin definir (10, 12) → tomada: «con BM25, nuestro buscador» y la nota «BM25 y TF-IDF: dos fórmulas para ordenar fragmentos».
- `kappa de Fleiss` sin referencia (11) → tomada: «va de 0 (azar) a 1 (acuerdo total)».
- `MAP` sin decir qué mide (12) → tomada: el panel se llama «MAP: calidad promedio».
- p = 0.014 sin explicar (13) → tomada: «la diferencia no es casualidad (p = 0.014)».
- `F1` sin definir (14) → tomada: «combina qué tanto acierta y qué tanto encuentra; 100 % es perfecto».
- `gold` (15, 16, 19) → tomada en el texto de las láminas: «anotación manual». El subtítulo de la figura `s7a` (15) también, corregido por Gonzalo: «pasajes anotados a mano».
- `vacunas (28.6 %)` sin métrica (19) → tomada: «precisión promedio de 25.8 % y 28.6 %».

**Contraste y legibilidad (§5)**
- Barras grises de los modelos descartados (12, 14) → tomada: más oscuras (`6E9482`).
- Etiqueta izquierda pegada al borde (02) → tomada: las figuras llevan margen blanco.
- Barras de la 02 casi iguales → abierto, de Gonzalo (figura `s2a`, opcional: lo ve en el ensayo).
- `3,47` recortado (04) → tomada por Gonzalo: `s2b` muestra 3,471 completo.
- Dos rojos parecidos y etiqueta `Pregunta` recortada (13) → tomada por Gonzalo: `s6` con un color por modelo y el eje completo.
- Barra de error invisible y rombo contra el eje (15) → tomada por Gonzalo: `s7a` con la barra visible solo en «Todas» y sin rombo en Fechas (no hay referencia humana para fechas).
- Leyenda chica (17) → tomada por Gonzalo: `s9` con la leyenda más grande, abajo.
- 30 barras en escala logarítmica (10) → abierto, de Gonzalo (figura `r07`, opcional: lo ve en el ensayo).
- Tabla de 06 y columna de 08 con letra chica → no: las figuras se quedan como están.

**Estructura y demo (§2, §8.2, §8.5)**
- Pasar 06–10 y 12 a un anexo y condensar la teoría → del equipo: cambia el guion que aprobó Diego.
- Captura de la herramienta antes de la demo → del equipo y de Leo.
- Operación: cargar conferencias nuevas, tiempos y despliegue (19) → del equipo.
- Empezar la demo con un caso fuerte en lugar de Dos Bocas (18) → de Leo.
- Métricas como resultados de negocio y más ejemplos en 05, 11, 13, 15 y 16 → del equipo: no entra antes de la entrega sin cambiar el guion.
