---
name: gold-anotacion
description: "Usa esta skill cuando vayas a sortear la muestra gold o el conjunto de selección, implementar o depurar src/mtx/muestreo.py, 08b_muestra_gold.py, la pestaña Gold de vista_gold.py, validar_gold() o tests/test_muestreo.py, sustituir un pasaje gold, cerrar el gold o tocar cualquier archivo de anotaciones/ (muestra_gold.csv, gold_entidades.csv, cierre_gold.json)."
---
# Gold de evaluación y conjunto de selección (anotación en modo ciego)

Reglas ejecutables condensadas de PRD §3.5, §3.6, §6.11, U13, D10, D13, D14, D15, P04, T09 y T10.
Si algo no está aquí ni en el PRD, no se inventa: se pregunta al alumno.

## Cuándo usarla
- Al implementar o modificar `src/mtx/muestreo.py`, `scripts/08b_muestra_gold.py`, `app/vista_gold.py` o `tests/test_muestreo.py`.
- Al generar `anotaciones/muestra_gold.csv` o `anotaciones/muestra_seleccion.csv`.
- Al sustituir un pasaje de la muestra, cerrar el gold (`anotaciones/cierre_gold.json`) o corregir el gold después del cierre.
- Al correr `validar_gold()` o exportar `gold_entidades.csv` a la raíz.
- Antes de que cualquier pestaña (Gold, Demo, errores) muestre predicciones sobre la muestra.

## Prerrequisitos y congelaciones que aplican
Lista de verificación antes de abrir la pestaña Gold (todo debe cumplirse, en este orden):

1. `ranking.csv` con filtro del mejor modelo ya existe y los juicios IR están cerrados (skill `pool-juicios-ir`); el mejor modelo está decidido.
2. `config/criterios_anotacion.md` está escrito y fijado por el alumno **[VALIDAR]**: cubre los cinco tipos (tabla de §3.6), D11, D13, D14 y la marca de interlocutor. No cambia después.
3. `config/protocolo.txt` (saludos, agradecimientos, despedidas) existe: lo usa el criterio de sustitución.
4. Reglas, gazetteers y `criterios_anotacion.md` llevan la etiqueta git `reglas-congeladas` (D15). La etiqueta debe preceder al primer commit de cualquier archivo gold; `validar_gold()` lo comprueba.
5. Nadie ha visto predicciones sobre los pasajes candidatos: la muestra se sortea y se anota **antes** de mostrar predicciones (D10).

Estado: gold = P0; conjunto de selección = P1 (solo si se comparan modelos NER, skill `ner-modelo`). Tiempo estimado para el alumno: 20 a 26 pasajes × 6 a 8 min ≈ 2 a 3.5 horas; avísalo antes de empezar.

## Muestreo de gold y conjunto de selección
`src/mtx/muestreo.py` y `scripts/08b_muestra_gold.py` (PRD §6.11, D10, T09).

**Gold de evaluación (20 pasajes).**
1. Universo: top-10 **con filtro** del mejor modelo, para las 10 consultas.
2. Semilla 42 fija. Dos plazas por consulta, 20 IDs únicos en total.
3. Un pasaje puede estar en el top-10 de varias consultas: la asignación es un **emparejamiento global reproducible** (bipartito consulta→pasaje), no un sorteo independiente por consulta (ese no garantiza unicidad).
4. Distribuir rangos altos y bajos dentro del top-10 (p. ej. una plaza del rango 1-5 y otra del 6-10) para no medir solo los pasajes más evidentes.
5. Si no existe asignación completa: imprimir las consultas en conflicto, registrar la excepción en `docs/decisiones.md` y detenerse. **Nunca** ampliar al top-20 ni duplicar IDs en silencio.
6. Escribir `anotaciones/muestra_gold.csv` con columnas exactas: `query_id, passage_id, doc_id, texto_sha256, semilla, version_muestra`.
7. El hash `texto_sha256` se calcula sobre el `texto` completo e inmutable del pasaje (incluida la marca de interlocutor); congela la muestra.

**Conjunto de selección (P1, 6 pasajes).**
1. Solo si se compararán modelos NER. 6 pasajes de 6 consultas distintas, sorteados con semilla 42 entre los restantes del top-10 con filtro, **disjuntos** del gold.
2. Manifiesto `anotaciones/muestra_seleccion.csv`, mismas columnas que el gold.
3. Se anota **primero**. Sirve solo para elegir el modelo NER; sus entidades van a `anotaciones/gold_seleccion.csv` y **no entran** en `resultados_ie.csv`.

**Pruebas (`tests/test_muestreo.py`, T09):** mismo ranking y semilla → mismo manifiesto; 20 IDs únicos con exactamente 2 por consulta; colisiones artificiales (un pasaje en varios top-10) resueltas sin duplicar; caso imposible construido a mano → la función reporta inviabilidad con las consultas en conflicto en vez de ampliar o duplicar; selección disjunta del gold.

## Sustitución de pasajes (solo criterio objetivo)
U13 y PRD §6.11. Un pasaje de la muestra se sustituye **únicamente** si cumple uno de estos criterios, medibles por código:

| Criterio | Cómo se mide |
| --- | --- |
| Menos de 25 palabras de contenido | Tokens del cuerpo (sin la marca de interlocutor) tras quitar la stoplist |
| Más de la mitad de fórmulas de protocolo | Proporción de palabras presentes en `config/protocolo.txt` > 50 % |
| Causa técnica | Texto corrupto o truncado por segmentación |

Procedimiento:
1. Verificar el criterio con la función de `muestreo.py`; anotar la cifra (p. ej. "18 palabras de contenido").
2. Sustituto = el **siguiente pasaje sorteado con la misma semilla en la misma consulta**, que no esté ya en el gold ni en la selección.
3. Registrar en `docs/decisiones.md`: pasaje retirado, criterio, cifra, sustituto, fecha, y que aún no se han visto predicciones.
4. Regenerar el manifiesto incrementando `version_muestra`.

Prohibido: "no tiene entidades", "es aburrido" o "no sirve para la demo" no son motivos. Cerrar un pasaje con **cero entidades es válido** y esperado. Toda sustitución ocurre antes de ver predicciones; después del cierre no hay sustituciones.

## Convenciones de anotación y modo ciego
Fuente: PRD §3.6, D11, D13, D14, `config/criterios_anotacion.md`. Las convenciones aplican por igual al gold, al conjunto de selección y al extractor.

| Tipo | Se anota | Regla de span |
| --- | --- | --- |
| PER | Funcionarios, empresarios, periodistas | Nombre completo tal como aparece, **sin el cargo**: "secretario de Salud, Jorge Alcocer Varela" → `Jorge Alcocer Varela` |
| ORG | Dependencias, empresas, partidos, organismos, cámaras empresariales, farmacéuticas y marcas de vacuna (D14) | Nombre o sigla tal como aparece; entidad **completa** aunque contenga un lugar: `Secretaría de Salud de Tabasco` sin LOC interno; "vacuna" genérica fuera del span |
| LOC | Estados, municipios, países y **obras con nombre propio** | Tren Maya, AIFA, Dos Bocas, refinería Olmeca son LOC |
| FECHA | Absolutas y relativas resolubles | Núcleo completo **con modificador** (`próximo 15 de enero`) y **sin preposición ni artículo** (`en 2019` → `2019`); intervalo explícito = una entidad; enumeración = entidades separadas; cuatro cifras sin contexto temporal no es FECHA |
| MONTO | Dinero en pesos o dólares | Cifra + escala + moneda o símbolo: `20 mil millones de pesos`, `$1,200 millones`; el `$` **nunca se recorta**; porcentajes, dosis, litros, beneficiarios van a `salida/cantidades_auxiliares.csv` (D11), no al gold |

Reglas adicionales:
- Offsets: índices de carácter Python sobre el `texto` completo, `inicio` inclusivo, `fin` exclusivo, `texto[inicio:fin] == texto_entidad`. Nunca bytes ni UTF-16; si la app usa JavaScript, convertir posiciones y probar caracteres fuera del BMP.
- Marca de interlocutor: sus entidades se anotan igual que en el cuerpo (`SECRETARIO DE SALUD, JORGE ALCOCER VARELA:` → PER `JORGE ALCOCER VARELA`). `PREGUNTA`, `INTERLOCUTOR`, `INTERLOCUTORA` y otras marcas genéricas no contienen entidades.
- Spans que no se contienen pueden coexistir; cualquier excepción se escribe en `config/criterios_anotacion.md` antes de cerrar el gold.

**Modo ciego (D10, D19):**
1. Gold, Demo y paneles de errores **no muestran predicciones** de los pasajes de la muestra bajo ninguna circunstancia hasta que exista `anotaciones/cierre_gold.json`.
2. El cierre lo ejecuta el alumno con el botón de la app; el archivo guarda hashes de muestra, textos, protocolo y gold, más la fecha.
3. No se precargan entidades del sistema como borrador; la tabla inicia vacía para cada pasaje.
4. El alumno anota desde cero. El asistente no participa en el contenido del gold (ver Prohibiciones).

## Pestaña Gold de la app
`app/vista_gold.py` (PRD §6.11, D19; integración general en skill `app-anotacion`).

1. Selector de conjunto: "Selección" (6, se anota primero) o "Evaluación" (20). Progreso por conjunto y por consulta en la barra lateral, con contador por tipo y las convenciones de §3.6 y `config/criterios_anotacion.md`.
2. **Modo principal, búsqueda por texto:** el alumno escribe el texto exacto; la app lo busca en el pasaje. Si aparece más de una vez, muestra cada aparición con 40 caracteres de contexto para elegir. **No** se infiere el offset por la primera coincidencia.
3. **Modo secundario, selección por tokens:** tokens de `re.finditer(r"\S+")` con offsets reales; clic en primer y último token; casilla "recortar puntuación final" activada por defecto que **nunca quita `$`**. Solo para casos difíciles (250 botones por pasaje recargan lento).
4. Selector de tipo (PER, ORG, LOC, FECHA, MONTO), botón "Agregar", tabla editable con borrar por fila y edición de tipo y límites, botón "Pasaje revisado completo" (cambia `estado` a `cerrado`, válido con cero entidades).
5. Marca de interlocutor resaltada en gris. HTML escapado y renderizado desde offsets, nunca desde texto re-tokenizado.
6. Autoguardado atómico (escribir temporal + renombrar) con respaldo y número de revisión en `anotaciones/gold_seleccion.csv`, `anotaciones/gold_entidades.csv` (`passage_id,tipo,texto,inicio,fin`, UTF-8 sin BOM) y `anotaciones/estado_gold.csv` (`passage_id, texto_sha256, estado, n_entidades, revision`).
7. Validación en vivo: invariante de offsets, duplicados `(passage_id, tipo, inicio, fin)`, anidamiento; detección de edición desde dos pestañas (comparar `revision` antes de escribir).
8. Botón "Cerrar gold" que escribe `anotaciones/cierre_gold.json` solo si `validar_gold()` pasa; a partir de ahí se desbloquean predicciones.

## Pasajes sin entidades y validador
**P04 (pasajes con cero entidades).** El evaluador del kit solo evalúa pasajes presentes en el CSV gold, así que un pasaje cerrado sin entidades no genera filas y desaparece de la métrica oficial.
1. Registrar cuántos pasajes evalúa realmente `resultados_ie.csv`; la cifra oficial se conserva sin modificar.
2. Añadir `salida/09_evaluacion_20_ids.csv`: evaluación complementaria sobre los 20 IDs del manifiesto que cuenta los falsos positivos en pasajes vacíos (skill `evaluacion-ie`).
3. Prohibido inventar una entidad centinela o sustituir el pasaje vacío por otro.

**`validar_gold()`** (bloqueante salvo donde se indica), lista de verificación:
- [ ] 20 IDs distintos con 2 por consulta **según el manifiesto** `muestra_gold.csv`, no según los IDs con filas.
- [ ] Todos los 20 en `estado_gold.csv` con `estado = cerrado`.
- [ ] Si existe `muestra_seleccion.csv`: 6 IDs disjuntos del gold.
- [ ] Invariante `0 <= inicio < fin <= len(texto)` y `texto[inicio:fin] == texto` en el 100 % de las filas de ambos CSV.
- [ ] Columnas exactas `passage_id,tipo,texto,inicio,fin`; `tipo` ∈ {PER, ORG, LOC, FECHA, MONTO}; ninguna fila con `texto` vacío; sin duplicados de clave.
- [ ] `texto_sha256` del manifiesto coincide con el texto actual de `data/pasajes.parquet`.
- [ ] La etiqueta git `reglas-congeladas` precede al primer commit de los archivos gold.
- [ ] Alerta (no bloqueo) si el F1 combinado es 1.0 en algún tipo con más de 5 entidades gold: revisar fuga entre reglas y gold (skill `integridad-congelacion`).
- [ ] Exporta `gold_entidades.csv` a la raíz del repo con el formato de §3.5.

**T10:** prueba con un pasaje cerrado sin entidades y un tipo sin soporte en el kit: el cierre es válido, el soporte real se identifica y la evaluación complementaria es coherente con la oficial.

## Cambios posteriores al cierre
Solo para corregir un error humano evidente (PRD §6.11, D15):
1. Revisión explícita del alumno, en texto propio, con el motivo.
2. Declarar si ya había visto predicciones para ese pasaje.
3. Nueva versión: incrementar `revision` en `estado_gold.csv`, regenerar `cierre_gold.json` y anotar el cambio en `docs/decisiones.md`.
4. Conservar el F1 anterior en el reporte y marcar el nuevo como exploratorio si las reglas o el gold cambiaron después de `reglas-congeladas`.

Nunca se retoca el gold para optimizar métricas, ni para "alinear" convenciones con lo que el extractor produce.

## Prohibiciones para el asistente
- **Prohibido anotar, sugerir, completar o corregir entidades del gold o del conjunto de selección**, aunque el alumno lo pida: el gold es trabajo humano desde cero. Puedes explicar una convención de §3.6, no aplicarla a un pasaje concreto.
- No mostrar, imprimir ni resumir predicciones del sistema sobre pasajes de la muestra antes de que exista `cierre_gold.json`.
- No precargar salidas del extractor en la app ni en archivos de `anotaciones/`.
- No sustituir pasajes por falta de entidades ni ampliar al top-20; no duplicar IDs.
- No cambiar `config/criterios_anotacion.md`, reglas ni gazetteers después de `reglas-congeladas` sin seguir la skill `integridad-congelacion`.
- No editar `anotaciones/*.csv` a mano ni con scripts: solo la app escribe ahí.

## Skills relacionadas
- `integridad-congelacion`: etiqueta `reglas-congeladas`, qué hacer si algo cambia después de una congelación, métricas anómalas.
- `pool-juicios-ir`: juicios y mejor modelo que definen el universo top-10 con filtro.
- `app-anotacion`: estructura general de la app Streamlit donde vive `vista_gold.py`.
- `evaluacion-ie`: `resultados_ie.csv`, `salida/09_evaluacion_20_ids.csv` y consumo del gold exportado.
- `ner-modelo`: uso del conjunto de selección para elegir el modelo NER.

## v2: gold doble, adjudicación y pasadas (PRD v2 D31, D32, D33; WP-08, WP-09)

- **Tamaños:** selección 10 (1 por consulta Q1 a Q10), parte A 10 (1 por consulta Q1 a Q10),
  parte B 10 (2 por consulta Q11 a Q15). Se evalúa sobre 40: los 20 de v1 más A y B.
- **Muestreo:** del pool con filtro, excluyendo el ámbito IE de v1 (99 pasajes) y el gold v1, con
  semilla 42 y manifiesto con hash antes de ver predicciones.
- **Doble anotación:** selección Diego y Luis; A Diego y Gonzalo; B Gonzalo y Bruno. Cada quien en
  `anotaciones/gold_v2/<anotador>.csv`, sin ver el del otro.
- **Adjudicación humana:** Arturo la selección, Bruno la A, Diego la B (`vista_adjudicacion.py`).
  El F1 entre anotadores antes de adjudicar es el "techo humano".
- **Pasadas:** la 1 anota todo menos FECHA; la 2 solo FECHA, cuando exista el criterio FECHA v2
  (`reglas-fecha-v2`). Leo no anota gold ni selección.
- **Cierre:** `anotaciones/cierre_gold_v2.json` el viernes 20; hasta entonces, modo ciego total
  para quien anota (D32).
- **Implementación (14 nov):** `make muestra-gold-v2 PARTES=seleccion,a` (sáb) y `PARTES=b` (dom,
  con el pool v2) escriben `anotaciones/v2/muestra_*.csv` y `muestreo_v2.json`. Lógica en
  `src/mtx/gold_v2.py`; papeles en `config/v2/anotadores.yaml` (`gold:`). Archivos:
  `anotaciones/gold_v2/<id>.csv` y `<id>_estado.csv` por anotador; `adjudicado_<id>.csv` y
  `adjudicado_<id>_estado.csv` por adjudicador (uno por persona, para que las ramas no choquen).
  Pestañas "Gold" y "Adjudicación"; la v1 queda como "Gold v1", intacta. Techo humano:
  `make acuerdo-gold` → `salida/v2/09_acuerdo_gold.csv`. El adjudicador solo incluye o excluye lo
  propuesto; no agrega entidades. Pruebas: `tests/test_gold_v2.py` y la parte v2 de
  `tests/test_muestreo.py`.
