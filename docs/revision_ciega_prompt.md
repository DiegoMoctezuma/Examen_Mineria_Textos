# Revisión ciega de la presentación (PRD v2 WP-18, R06)

Instrucción para que un modelo de lenguaje **sin contexto del proyecto** revise la presentación,
como lo haría alguien que la ve por primera vez. Responde al comentario del profesor «comparar con
un modelo ciego».

## Cómo se usa (Arturo)

1. Exporta la presentación final a PDF, con las láminas tal como se van a proyectar.
2. Abre una **conversación nueva** en un LLM (sin proyectos, memoria ni archivos previos del
   equipo). Anota cuál usaste, con su versión, y la fecha.
3. Adjunta el PDF y pega el texto del recuadro de abajo, sin cambios y sin explicar nada más.
4. Guarda la respuesta completa, sin editar, en `docs/revision_ciega_respuesta.md`. Al inicio pon
   el LLM, la fecha, la hora y el nombre del PDF.
5. El equipo decide qué cambios toma y registra la decisión al final de ese archivo, en una
   sección «Qué tomamos y qué no», con una línea por sugerencia.

No le des al LLM el reporte, el repositorio, el guion ni ninguna explicación: la revisión vale
porque solo ve lo mismo que verá el público.

## Texto para pegar

```text
Eres un consultor que evalúa presentaciones de proyectos de análisis de datos para dependencias
del gobierno. Te adjunto el PDF de una presentación. No tienes ningún otro contexto: evalúala solo
con lo que se ve en las láminas, como si fueras el cliente que la recibe por primera vez.

El público objetivo es un equipo de comunicación de una dependencia de gobierno que quiere
consultar lo que se ha dicho en conferencias de prensa. La presentación debe convencerlos de que
el sistema les sirve y de que sus resultados son confiables. Dura entre 15 y 20 minutos e incluye
una demostración en vivo.

Responde en español, con estas secciones y en este orden:

1. Qué entendiste. En 5 líneas como máximo: qué problema resuelve el sistema, cómo lo resuelve y
   qué evidencia muestra de que funciona. Si algo no se entiende sin explicación oral, dilo.
2. Estructura. ¿La secuencia problema → solución → evidencia → demostración se sigue? Señala las
   láminas que sobran, las que faltan y las que están fuera de orden.
3. Se entiende sola. Por lámina, lo que no se entiende sin un experto: términos técnicos sin
   explicar, siglas, cifras sin unidad o sin referencia, gráficas sin ejes o sin nombres.
4. Ejemplos. ¿Cada lámina técnica tiene un ejemplo concreto? Señala las que no lo tienen.
5. Contraste y legibilidad. Texto demasiado pequeño, colores que no contrastan, gráficas difíciles
   de leer de lejos, láminas con demasiado texto.
6. Adecuación al cliente. ¿El tono es de venta a un cliente o de un trabajo escolar? ¿Las
   limitaciones se presentan como siguientes pasos con su mejora? ¿Hay algo que un cliente de
   gobierno vería como riesgo o como falta de seriedad?
7. Las 5 preguntas más difíciles que haría este cliente al terminar.
8. Los 5 cambios con más impacto, ordenados de mayor a menor, cada uno con la lámina que afecta.

Sé específico: cita el número o el título de la lámina en cada observación. No inventes contenido
que no esté en el PDF.
```
