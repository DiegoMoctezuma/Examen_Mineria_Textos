# Estilo del deck (destilado de `referencias/original-*`)

Skill `hack-presentacion` adaptada al examen: sin `hack/PITCH.md` (el guion es `laminas/guion.md`
y va en las notas de cada diapositiva) y sin app propia (los colores salen de las referencias y
de los íconos del alumno).

## Qué se toma de cada referencia

| Referencia | Qué se toma |
| --- | --- |
| original-10729f… (barras verticales en píldora) | Barras redondeadas con el ícono en un círculo en la base; valor girado dentro de la barra → AP por consulta |
| original-9acb94… (barras con parte rayada) | Barras apiladas oscuro + claro; pastilla de dato arriba a la derecha → respuestas respaldadas y ambiguas |
| original-a3f735… y original-cc4677… (anillos) | Anillos concéntricos con pista gris y leyenda en pastillas → MAP de las cuatro variantes |
| original-b821f1… (tarjetas de cifra) | Tarjeta blanca, etiqueta gris con marcador, cifra grande en marino y unidad pequeña → corpus |
| original-d7be09… (filas de píldoras horizontales) | Filas con etiqueta a la izquierda y píldoras por categoría → F1 por tipo y método, idf por término |

## Paleta

| Uso | Color |
| --- | --- |
| Fondo de contenido | `#F6F7F9` |
| Tarjeta | `#FFFFFF`, borde `#E6E9EF`, sombra suave |
| Primario (BM25, combinado, cifras) | `#03467B` |
| Medio (modelo) | `#6792B4` |
| Claro (TF-IDF, reglas) | `#C9D8E6` |
| Pista de anillos y rejilla | `#EEF2F7` |
| Texto | `#2B2B2B`; secundario `#7C88AA` |
| Error | `#D92B3A` |

Colores por consulta: el aro de cada ícono del alumno. Q1 `#02614C`, Q2 `#012B60`, Q3 `#9E0C01`,
Q4 `#011E51`, Q5 `#024B1B`, Q6 `#A3010F`, Q7 `#5B0454`, Q8 `#013147`, Q9 `#780526`, Q10
`#02204E`. En las gráficas por consulta, el tono oscuro es BM25 o respaldado y el mismo color
aclarado es TF-IDF o ambiguo; la consulta se identifica por su ícono, no solo por el color.

## Tipografía y estructura

Arial (la sans de las referencias, DM Sans, no está garantizada en la máquina de la
presentación). Títulos de 26 pt en negrita, apoyo de 13 pt, cifras de 34 a 36 pt, notas al pie
de 9 pt con la fuente de cada cifra. Sándwich: portada, demo y cierre en marino `#03467B`, el
contenido en fondo claro. Motivo repetido: ícono en círculo blanco con el aro de su color.
