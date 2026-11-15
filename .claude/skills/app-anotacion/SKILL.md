---
name: app-anotacion
description: "Usa esta skill cuando vayas a crear, modificar o depurar la app local de anotación (src/mtx/app/: app.py, vista_estado.py, vista_juicios.py, vista_gold.py, vista_gazetteer.py, vista_demo.py, componentes.py), su alternativa CLI con input(), la persistencia atómica en anotaciones/, el resaltado desde offsets, el modo ciego, la prueba T15 o docs/pruebas_app.md."
---
# App local de anotación (Streamlit o CLI)

Reglas ejecutables condensadas de PRD §7, §3.6, D19, §6.6 (pestaña Juicios), §6.7 (pestaña Gazetteer), §6.11 (pestaña Gold), T15 y el riesgo "app lenta con selección por tokens".
Si algo no está aquí ni en el PRD, no se inventa: se pregunta al alumno.

## Cuándo usarla
- Al tocar cualquier archivo de `src/mtx/app/` o el objetivo `app` del Makefile.
- Al escribir o depurar la lectura y escritura de `anotaciones/juicios_relevancia.csv`, `anotaciones/gold_seleccion.csv`, `anotaciones/gold_entidades.csv`, `anotaciones/estado_gold.csv`, `anotaciones/cierre_gold.json` o `config/gazetteer_extendido.csv` desde la app.
- Al implementar el resaltado HTML, la búsqueda de spans o la selección por tokens en `componentes.py`.
- Al redactar `docs/pruebas_app.md` o la prueba T15.
- Antes de empezar, carga `integridad-congelacion`: la app escribe insumos humanos protegidos.

## Arranque y alternativa sin Streamlit
1. Arranque oficial: `make app` → `uv run streamlit run src/mtx/app/app.py` (PRD §7).
2. `app.py` solo registra las pestañas y delega en `vista_*.py`; la lógica de offsets, búsqueda y persistencia vive en `componentes.py` para que la CLI la reutilice sin Streamlit.
3. Alternativa sin Streamlit (PRD §2, fila `streamlit`): CLI con `input()` que ofrece las mismas tres funciones esenciales: juicios, gold y demo. Misma persistencia, mismos validadores, mismo modo ciego.
4. Pestañas en este orden: **Estado**, **Juicios**, **Gold**, **Gazetteer**, **Demo** (P2). La pestaña Demo se recorta primero si falta tiempo (PRD §12); no bloquea nada.
5. Verifica que la app arranca sin red y sin cargar el modelo NER: lee `data/pasajes.parquet`, `data/consultas.csv` y los CSV de `anotaciones/`.
6. Pestaña Demo (P2, `vista_demo.py`): envuelve `demo.py` (PRD §6.16) sobre artefactos cacheados; respeta el modo ciego para los pasajes de la muestra. Si no hay tiempo, la demo oficial es `make demo Q=Q3` en terminal.

Menú mínimo de la CLI (el PRD solo fija las tres funciones; el punto de entrada se acuerda con el alumno y se documenta en el README):
1. Juicios: muestra consulta, pregunta y pasaje; ofrece las mismas cuatro acciones que los botones (1, 0, omitir, anterior) más guardar y salir.
2. Gold: elige conjunto, pasaje, texto exacto a buscar, número de aparición cuando hay varias y tipo; acción para cerrar el pasaje.
3. Demo: delega en `demo.py` con la consulta indicada.

## Principios transversales (persistencia, offsets, modo ciego)

### Persistencia (PRD §7, D19)
- CSV bajo `anotaciones/` tras **cada** acción (clic, Agregar, borrar, cerrar); sin base de datos.
- Escritura atómica: escribir a archivo temporal en el mismo directorio, `os.replace` sobre el destino, respaldo previo del archivo anterior y número de `revision` que se incrementa en cada escritura.
- Antes de escribir, releer `revision` del disco; si no coincide con la que la sesión cargó, detener la escritura y mostrar "editado desde otra pestaña: recarga antes de guardar" (T15). Nunca sobrescribir en silencio.
- Reanudable: al reabrir, la app carga el CSV y sitúa al alumno en el primer elemento pendiente.
- UTF-8 sin BOM, separador coma, columnas exactas de PRD §3.5.

### Offsets y resaltado (PRD §3.6, §7)
- Offsets = índices de carácter Python sobre el `texto` completo e inmutable del pasaje (marca de interlocutor incluida); `inicio` inclusivo, `fin` exclusivo; invariante `0 <= inicio < fin <= len(texto)` y `texto[inicio:fin] == texto_entidad`.
- No son bytes ni unidades UTF-16. Si se introduce JavaScript para seleccionar, convertir posiciones a índices de carácter Python y probar con caracteres fuera del BMP (emoji, `𝐀`).
- Resaltado: HTML seguro generado desde offsets. Recorrer el texto por tramos `[fin_anterior, inicio)` y `[inicio, fin)`, aplicar `html.escape` (escapa `<`, `>` y `&`) a cada tramo y envolver los spans en `<mark>`. **Nunca** por `str.replace` ni regex sobre el texto: duplica apariciones y rompe offsets.
- Los spans se ordenan por `inicio` antes de renderizar; spans solapados o anidados se marcan como error visible, no se ocultan.

### Modo ciego (PRD §6.11, §7)
- Gold, Demo y cualquier panel de errores **no muestran predicciones** (entidades del sistema, `salida/entidades*.csv`, caché NER) de los pasajes de la muestra hasta que exista `anotaciones/cierre_gold.json`.
- No se precargan entidades del sistema como borrador en ningún modo.
- Juicios es ciego al modelo: sin puntajes, rangos ni variante.
- La comprobación es una sola función (`gold_cerrado()` en `componentes.py`) que lee `anotaciones/cierre_gold.json`; toda vista la consulta antes de leer predicciones.

## Pestaña Estado
1. Lista cada artefacto humano y técnico: juicios, gazetteer extendido, muestra gold, gold de selección, gold de evaluación, cierre del gold, caché NER, resultados.
2. Por artefacto asigna exactamente uno de cinco estados (PRD §7): **pendiente humano** (falta anotar), **pendiente técnico** (falta correr un script), **válido** (existe y su validador pasa con hashes vigentes), **obsoleto** (el hash del insumo cambió: corpus, pasajes, reglas, modelo) y **error** (existe pero el validador falla).
3. Nunca marcar "completado" solo porque exista el archivo: la condición es validador en verde más hash vigente.
4. Reusar `validar_juicios()` y `validar_gold()` (PRD §6.6, §6.11); no duplicar las reglas en la vista.
5. Mostrar junto a cada estado el siguiente comando o pestaña que lo desbloquea.

## Pestaña Juicios
Lista de verificación (PRD §6.6 "App de juicios"):
- [ ] Barra lateral: selector de consulta, progreso por consulta y global, botón **Guardar**.
- [ ] Cuerpo: consulta en grande; `pregunta_extraccion` como ayuda; pasaje completo con resaltado de los términos de la consulta (match por stem sobre el token original, con el mismo preprocesamiento de `indice-ranking`); metadatos `doc_id`, `titulo`, `interlocutor`.
- [ ] La fecha se muestra, pero el criterio en pantalla (extracto de `config/criterios_relevancia.md`) recuerda que la fecha y el modelo no cuentan; la ventana se aplica después, en el análisis.
- [ ] Botones: **Relevante (1)**, **No relevante (0)**, **Omitir por ahora**, **Anterior**. "Sin juzgar" (omitido) es distinto de 0: se guarda como vacío, no como 0.
- [ ] Ciego al modelo: no se muestran puntajes, rangos, variante ni qué modelo recuperó el pasaje. El orden de presentación no revela el rango.
- [ ] Autoguardado atómico en `anotaciones/juicios_relevancia.csv` tras cada clic, con historial de revisión; reanudable; detecta edición desde dos pestañas.
- [ ] Columnas exactas: `query_id,doc_id,passage_id,relevante`; clave única `(query_id, passage_id)`; solo pasajes del pool (`pool-juicios-ir`).

## Pestaña Gold
Lista de verificación (PRD §6.11 "Pestaña Gold"):
- [ ] Selector de conjunto: **Selección** (6 pasajes, se anota primero) o **Evaluación** (20). Fuente: `anotaciones/muestra_seleccion.csv` y `anotaciones/muestra_gold.csv`.
- [ ] **Modo principal, búsqueda por texto:** el alumno escribe el texto exacto; la app lo busca con `str.find` iterado sobre el texto real; si aparece más de una vez, muestra cada aparición con 40 caracteres de contexto a cada lado para elegir. Nunca se infiere el offset por la primera coincidencia.
- [ ] **Modo secundario, selección por tokens:** tokens de `re.finditer(r"\S+", texto)` con `m.start()` y `m.end()` reales; clic en el primer y en el último token; casilla "recortar puntuación final" activada por defecto que recorta `.,;:!?)"»` y **nunca** quita `$`. Solo para casos difíciles: con 250 tokens por pasaje un botón por token provoca recargas lentas (PRD §12, riesgos).
- [ ] Selector de tipo (PER, ORG, LOC, FECHA, MONTO), botón **Agregar**, tabla de anotaciones con borrar por fila y edición de tipo y límites, botón **Pasaje revisado completo** (estado `cerrado`, se permite con cero entidades).
- [ ] La marca de interlocutor se muestra resaltada en gris: sus entidades también se anotan.
- [ ] Barra lateral: convenciones (PRD §3.6 y `config/criterios_anotacion.md`), progreso por conjunto y por consulta, contador por tipo.
- [ ] Autoguardado atómico con respaldo y `revision` en `anotaciones/gold_seleccion.csv`, `anotaciones/gold_entidades.csv` (`passage_id,tipo,texto,inicio,fin`) y `anotaciones/estado_gold.csv` (`passage_id, texto_sha256, estado, n_entidades, revision`).
- [ ] Validación en vivo antes de Agregar: invariante de offsets, duplicado `(passage_id, tipo, inicio, fin)`, anidamiento o solape con otra fila. Error visible, fila rechazada.
- [ ] Botón de cierre que escribe `anotaciones/cierre_gold.json` (hashes de muestra, textos, protocolo y gold, fecha) solo cuando `validar_gold()` pasa; hasta entonces, modo ciego total.
- [ ] Sustitución de pasajes (U13) no se hace desde la app: va por `gold-anotacion` y `docs/decisiones.md`.

## Pestaña Gazetteer
1. Cargar `salida/06_siglas_candidatas.csv` (`sigla, nombre_propuesto, frecuencia, ejemplo`) y `kit/gazetteer_dependencias.csv` como base de solo lectura.
2. Por candidato: **aceptar**, **corregir** tipo (ORG, LOC) y nombre, o **descartar**. Mostrar `ejemplo` como evidencia.
3. Escribir `config/gazetteer_extendido.csv` con columnas `nombre, variantes, siglas, tipo, etiqueta (ORG|LOC), origen (kit|minado|manual), evidencia`; escritura atómica igual que `anotaciones/`.
4. Contador de entradas base, nuevas y rechazadas en la barra lateral (se reporta en resultados, sin cuota).
5. Si las reglas ya están congeladas (`reglas-congeladas`), la pestaña muestra aviso y bloquea la escritura: ver `integridad-congelacion`.

## Pruebas (T15 y prueba manual)
T15 (PRD §13, `tests/`): "cambio de texto, modelo o regla; interrupción; dos pestañas" → invalidación correcta, reanudación y protección de datos humanos.
1. Escribir una anotación, cambiar el `texto` del pasaje en un parquet de prueba: Estado pasa a **obsoleto** y la fila no se borra.
2. Simular interrupción tras el escrito del temporal y antes de `os.replace`: el CSV original sigue íntegro y el respaldo existe.
3. Cargar el CSV en dos sesiones, guardar en una, intentar guardar en la otra: la segunda se rechaza por `revision` desfasada.
4. Cerrar y reabrir: la app retoma en el primer pendiente con el mismo conteo.
5. Resaltado: pasaje con `<`, `&` y un carácter fuera del BMP antes de la entidad; el HTML escapa y los offsets siguen cumpliendo el invariante.
6. Modo ciego: sin `cierre_gold.json`, ninguna vista expone predicciones de la muestra aunque exista `salida/entidades.csv`.

`docs/pruebas_app.md`: lista de exactamente 10 pasos que el alumno recorre una vez (PRD §7), cada uno con acción y resultado esperado: arranque, Estado sin "completado" falso, juicio 1/0/omitir/anterior, reapertura, dos pestañas, búsqueda con desambiguación, selección por tokens con `$`, validación de duplicado, gazetteer, cierre del gold.

## Prohibiciones
- La app **nunca** sugiere, autocompleta ni precarga juicios ni gold; tampoco "ayuda" con un valor por defecto en Relevante o un tipo preseleccionado a partir del texto.
- El asistente construye la herramienta y valida formatos; no anota, no corrige anotaciones ni rellena pendientes "para avanzar" (PRD §12: nunca se autocompleta).
- Sin reemplazo de texto para resaltar; sin offsets calculados desde HTML renderizado o desde una primera coincidencia.
- Sin predicciones visibles en Gold, Demo o paneles de errores antes de `anotaciones/cierre_gold.json`.
- Sin puntajes, rangos ni variante en Juicios.
- Sin base de datos, sin escritura no atómica, sin sobrescribir una `revision` ajena.
- Sin tocar `kit/`, `anotaciones/` fuera de la app ni `config/criterios_*.md` desde el código.

## Skills relacionadas
- `integridad-congelacion`: qué invalida qué; bloqueo tras `reglas-congeladas`.
- `pool-juicios-ir`: pool, `validar_juicios()` y formato de `juicios_relevancia.csv`.
- `gold-anotacion`: muestra, `validar_gold()`, sustitución U13 y cierre del gold.
- `reglas-gazetteer`: minado de siglas y uso de `config/gazetteer_extendido.csv`.
- `indice-ranking`: stems para el resaltado de términos de la consulta.

## v2: varios anotadores (PRD v2 D24; WP-01)

- La pestaña Juicios pide quién juzga (lista cerrada de `config/v2/anotadores.yaml`, sin
  contraseña) y lo recuerda en la sesión y en la URL (`?anotador=arturo`). Sin elegir, no muestra
  pasajes ni botones.
- `C.rutas(anotador)` apunta a `anotaciones/juicios_v2/<anotador>.csv` y a su historial;
  `C.cargar_items(r)` devuelve solo los pares asignados con `origen = app`, con texto de
  `data/pasajes.parquet`. Si la huella del texto difiere de la asignada, se bloquea
  (`textos_cambiados`).
- La app nunca lee el archivo de otro anotador; la pestaña Estado muestra conteos (no valores):
  el propio a cada quien y el de todos al coordinador.
- El archivo v1 `anotaciones/juicios_relevancia.csv` ya no se edita desde la app.
- CLI: `make app-cli ANOTADOR=<id>`.
- Pruebas: `tests/test_anotadores.py` y las de `tests/test_app.py` que usan `entorno_v2`.
