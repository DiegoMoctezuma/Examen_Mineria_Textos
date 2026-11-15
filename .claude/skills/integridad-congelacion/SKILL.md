---
name: integridad-congelacion
description: "Usa esta skill en toda tarea del proyecto antes de tocar juicios, gold, reglas, gazetteers, modelo NER, segmentación, consultas o cifras del reporte, y siempre que algo cambie después de una congelación, haya que recortar alcance o una métrica parezca anómala."
---
# Integridad académica y congelaciones

Reglas transversales del PRD §0.2, §4, §6.11, §6.12, §11.1, §12 y §13.2. Se aplican en cualquier
skill y en cualquier hito. Si una instrucción puntual choca con esta skill, gana esta skill y se
avisa al alumno.

## Cuándo usarla

1. Al iniciar cualquier tarea que escriba en `anotaciones/`, `config/`, `data/consultas.csv`,
   `data/modelo_ner.json` o en reglas/gazetteers de `src/mtx/`.
2. Antes de ejecutar `kit/evaluar.py` o de redactar cualquier cifra en `reporte/`, láminas o README.
3. Cuando el alumno pida "mejorar" una métrica, cambiar un parámetro o "arreglar" una anotación.
4. Cuando el plazo peligre y haya que decidir qué se recorta.
5. Cuando una métrica caiga bajo un umbral de alerta o salga sospechosamente perfecta.

## Prohibiciones absolutas

Condición del examen (EX, p. 4) y regla de integridad (PRD §0.2 regla 3). El asistente construye la
herramienta y valida formatos; estos valores los produce el alumno leyendo pasajes:

1. **Juicios de relevancia** (`anotaciones/` → `juicios_relevancia.csv`). Nunca asignar 0/1, ni
   sugerir "probablemente relevante", ni rellenar los faltantes.
2. **Gold de evaluación** (`anotaciones/gold_entidades.csv`, `estado_gold.csv`). Nunca anotar,
   precargar predicciones como borrador, completar spans ni "corregir" límites o tipos.
3. **Conjunto de selección** del NER (`anotaciones/gold_seleccion.csv`), si existe. Misma regla.
4. **Revisión de siglas** del gazetteer (hito H5). El asistente mina candidatos; aceptar o rechazar
   cada sigla es del alumno.
5. **Valoraciones** de las tablas de respuesta (`valoraciones.yaml`, 10 entradas). Redacta el alumno.

Lista de verificación antes de cualquier escritura:

- [ ] ¿El archivo destino está en `anotaciones/` o es `valoraciones.yaml`? Entonces solo lo escribe
      la app o el alumno; el asistente no lo edita a mano ni por script.
- [ ] ¿Me pidieron "ayudar a anotar", "sugerir etiquetas" o "revisar si el juicio es correcto"?
      Rechazar con una frase y ofrecer la alternativa permitida: validar formato con `make validar`.
- [ ] Modo ciego (PRD D10, §6.11): Gold, Demo y paneles de errores no muestran predicciones de la
      muestra hasta que exista `anotaciones/cierre_gold.json`. No hay excepciones "solo para ver".
- [ ] ¿Un pasaje gold "no tiene entidades"? No es motivo de sustitución (PRD U13). Se cierra con cero.
- [ ] Nunca retocar el gold ni los juicios para optimizar métricas (PRD §6.11, cambios posteriores).

## Puntos [VALIDAR]

Donde el PRD marca `[VALIDAR]` el asistente muestra el resultado completo y espera aprobación
explícita antes de continuar (PRD §0.2 regla 4, §12.2). No se avanza "mientras tanto" en nada que
dependa de ese resultado.

| Punto | Hito | Qué se muestra |
| --- | --- | --- |
| Q9 y Q10 | H1 | Consultas propuestas con conteos del corpus; el alumno elige |
| `config/criterios_relevancia.md` | H3 | Texto completo de criterios antes del primer juicio |
| Gazetteer extendido y siglas | H5 | Candidatos minados con frecuencia y contexto |
| `config/criterios_anotacion.md` | H5 | Convenciones completas antes de `make congelar` |
| Prosa del reporte | H9 | Sección por sección, tres cortes |
| Láminas y guion | H9 | Máximo 5 láminas, guion con tiempo medido |

Procedimiento:

1. Generar el artefacto y guardarlo en su ruta del PRD.
2. Mostrarlo íntegro (no un resumen) y pedir "aprobado" o cambios.
3. Registrar la aprobación con fecha en `docs/decisiones.md`.
4. Solo entonces ejecutar el paso siguiente del hito.

## Congelaciones y qué hacer si algo cambia después

Orden de congelación (PRD §4, regla 7 de §0.2): antes de una congelación se puede revisar con motivo
documentado; después, nunca se cambian parámetros repetidamente para mejorar la cifra final.

| Momento | Decisiones | Qué queda fijo |
| --- | --- | --- |
| Antes de rankings y juicios | D02, D03, D04 | Segmentación (ventana 200/150/40), `inicio_cuerpo`, reporteros indexados |
| Antes de segmentar | D05 | Limpieza de ruido auditada |
| Antes del primer juicio | D06, D07 | Pool = unión de top-10 de 4 variantes; relevancia temática sin fecha |
| Antes de evaluar IR | D08 | Regla del ganador: mayor MAP entre `*_con_filtro`, empate a BM25 |
| Antes de abrir el gold | D09, D11, D13, D14, D15 | NER principal, MONTO = dinero, span de FECHA, farmacéuticas = ORG, reglas y gazetteers |
| Antes de mostrar predicciones | D10 | Muestra gold (semilla 42, `anotaciones/muestra_gold.csv`) |
| Antes de evaluar IE | D12 | Fusión por `(tipo, inicio, fin)` exacto |
| Antes de resultados oficiales | D01, D18 | `uv.lock`, revisiones de modelo, hashes, manifiesto |

Lista de verificación al congelar (hito H5, PRD D15):

- [ ] `config/criterios_anotacion.md`, reglas y gazetteers aprobados en `[VALIDAR]`.
- [ ] `make congelar` crea la etiqueta git `reglas-congeladas`; debe preceder al primer commit de
      cualquier archivo gold (lo comprueba `validar_gold()`).
- [ ] `data/modelo_ner.json` fijado por criterios técnicos, sin usar el gold (PRD D09, P06).
- [ ] Muestras sorteadas y manifiestos con hashes escritos antes de ver predicciones.
- [ ] El cierre del gold lo hace el alumno con el botón que escribe `anotaciones/cierre_gold.json`.

Si algo cambia después de su congelación, en este orden:

1. **Detenerse** y avisar al alumno qué decisión se está rompiendo y por qué.
2. **No sobrescribir**: la cifra previa se conserva tal cual en `salida/` y en el reporte.
3. **Versión experimental nueva**: nuevo commit con el cambio; `salida/09_cambios_post_congelamiento.csv`
   guarda F1 antes y después con el commit (PRD §6.12 punto 4). El reporte presenta ambas cifras y
   marca la segunda como exploratoria.
4. **Documentar** en `docs/decisiones.md`: fecha, decisión afectada, motivo, qué invalida, y si el
   alumno ya había visto predicciones.
5. **Gold o juicios**: corregir un error humano exige revisión explícita del alumno, motivo y nueva
   versión (campo `revision`); nunca lo hace el asistente por iniciativa propia.
6. Sustitución de pasaje gold (PRD U13): solo por menos de 25 palabras de contenido, más de la mitad
   en `config/protocolo.txt` o texto corrupto; el sustituto es el siguiente sorteado con la misma
   semilla; se registra en `docs/decisiones.md` antes de ver predicciones.
7. Entre la entrega (`v1.0-entrega`) y la presentación no se cambia código que afecte cifras.

## Tabla de invalidación

PRD §11.1. Antes de aceptar un cambio, identificar la fila y listar al alumno qué se tendrá que
regenerar. **Nunca se borran anotaciones para resolver una invalidación**: se versionan y se conservan.

| Cambio en | Invalida |
| --- | --- |
| Snapshot del corpus o segmentación | Todo |
| Tokenización o ranker | Ranking, pool, ganador y selección de pasajes IE |
| Consultas | Sus rankings y sus juicios |
| Juicios | Métricas IR y ganador; si cambia el ganador, revisión explícita de muestra gold e IE |
| Modelo NER, reglas o fusión | Extracción, evaluación IE, tablas y documentos |
| Gold o protocolo | Evaluación IE y documentos |

Procedimiento:

1. Nombrar la fila afectada y los productos de `salida/` que caducan.
2. Comprobar si hay insumos humanos en juego (`anotaciones/`). Si los hay, aplicar la sección anterior.
3. Regenerar solo lo invalidado con los scripts numerados; conservar las versiones previas.
4. Actualizar `salida/manifiesto_ejecucion.json` y anotar el cambio en `docs/decisiones.md`.

## Prioridades y recortes

PRD D20, §12.1 y §12.4. No se empieza un P1 mientras falte un P0; P2 solo con P1 terminado.

- **P0 (núcleo)**: contratos del kit, limpieza y segmentación, índice, ambos rankings con filtro,
  pool y juicios, evaluación IR, regex y gazetteers con suite, un NER, fusión, gold, evaluación IE con
  análisis de errores, tablas con evidencia, reporte de 4 a 6 páginas, README, `requirements.txt`,
  guion y demo en terminal.
- **P1**: segundo NER con conjunto de selección, sensibilidad de segmentación, vista con ventana
  completa, figuras completas.
- **P2**: fechas relativas, vínculo de personas, lint de estilo, láminas con `python-pptx`, pestaña
  Demo, `AGENTS.md`, experimento de capitalización.

Si el plazo peligra, recortar en este orden y avisar al alumno antes de cada paso:

1. Todo lo P2 (láminas a mano; `AGENTS.md` reducido a cinco líneas en el README).
2. Comparación de dos NER: se usa el principal y el reporte lo declara.
3. Experimento de sensibilidad de segmentación (se justifica la base con los conteos de §6.1).
4. Figuras reducidas a dos: MAP por variante y F1 por tipo.
5. Pool reducido a variantes con filtro, métrica condensada para las demás, declarado en el reporte.
6. Tablas Q9 y Q10 resumidas en el reporte, completas en el repo.

Nunca se recorta: dos modelos de ranking, dos enfoques de extracción, limpieza de ruido, los seis
CSV de entrega, congelamiento antes del gold, modo ciego, README reproducible, reporte de 4 a 6
páginas, máximo 5 láminas. Si se reduce un requisito EX, el estado final dice qué falta; una
limitación escrita en el reporte no se convierte en cumplimiento.

## Umbrales de alerta

PRD §13.2 (U19). Son alertas, no metas. Al dispararse, buscar bug antes de reportar la cifra:

| Señal | Qué revisar primero |
| --- | --- |
| MAP oficial del ganador < 0.15 | Tokens de consulta, filtro de fechas, orden de IDs, formato de `ranking.csv` |
| F1 combinado TODOS < 0.30 | Offsets (invariante `texto == pasaje[inicio:fin]`), mapa de etiquetas, fusión |
| F1 = 1.0 en un tipo con más de 5 entidades gold | Gold copiado del sistema; verificar `cierre_gold.json` y que no se mostraron predicciones |

Reglas de reporte de cifras (PRD §0.2 regla 6):

1. Toda cifra y todo ejemplo del reporte proviene de un archivo en `salida/` (o `anotaciones/`
   versionado). Citar la ruta junto al número.
2. Lo que no exista todavía se declara "pendiente"; no se estima ni se redondea de memoria.
3. Los ejemplos de error son filas reales de `salida/09_analisis_errores.csv`; si una categoría
   del enunciado no apareció, se dice que no apareció. No se inventan errores para llegar a una cuota.
4. Los validadores técnicos no certifican que las decisiones humanas sean correctas; no afirmarlo.

## Skills relacionadas

- `gold-anotacion`: modo ciego, muestra, cierre y validador del gold (PRD §6.11).
- `pool-juicios-ir`: pool congelado y juicios humanos (PRD D06, D07, H3).
- `reglas-gazetteer`: `make congelar` y la etiqueta `reglas-congeladas` (PRD D15).
- `evaluacion-ie`: `09_cambios_post_congelamiento.csv` y análisis de errores (PRD §6.12).
- `entrega-reproducible`: `make validar`, manifiesto e invalidación (PRD §11, §13.2).

## v2: congelaciones, separación y casos nuevos (PRD v2 §3.10 y §4)

Siguen todas las reglas de arriba; en v2 se suman:

- **Insumos humanos de v2:** juicios en `anotaciones/juicios_v2/<anotador>.csv`, gold doble y
  adjudicación en `anotaciones/gold_v2/`, conjunto de selección v2, Q11 a Q15 y valoraciones. Los
  produce cada integrante; si alguien pide ayuda para decidir un valor, niégate en una frase y
  remite al criterio escrito. La única escritura por script en `anotaciones/` es
  `scripts/04c_importar_juicios_v1.py`, que copia juicios v1 sin cambiar valores.
- **v1 no se sobrescribe:** `anotaciones/juicios_relevancia.csv`, el gold v1 y las cifras de
  `v1.0-entrega` se conservan; lo nuevo va a rutas `v2` o después de `v2-inicio`.
- **Separación (D32):** mientras alguien tenga anotación pendiente, no le muestres rankings,
  puntajes ni entidades predichas de los pasajes de su lote. Quien hace la demo (Bruno, Leo) usa
  artefactos v1 hasta los cierres del 20. Quien escribe reglas FECHA (Leo) no anota gold.
- **Reglas fijadas antes de medir:** agregación por mayoría de 3, ganador entre las 4 variantes
  con filtro (stem y lema), selección del NER y muestreo (PRD v2 §3). Cambiarlas después crea una
  versión exploratoria.

| Momento | Qué se congela | Mecanismo |
| --- | --- | --- |
| Aprobación del PRD v2 | D23 a D36 | Etiqueta `v2-inicio` |
| Antes del lote 1 | Criterio de relevancia, asignación del lote 1 | `data/v2/asignacion_juicios.csv` |
| Antes del muestreo v2 | Exclusión del ámbito v1, semillas, tamaños | Manifiestos con hash |
| Antes del pool v2 | Q11 a Q15, lematizador, 8 variantes | `data/consultas.csv` v2 |
| Antes del lote 2 | Pool v2, asignación del lote 2 | Hash del pool v2 |
| Antes de la pasada 2 | Criterio y reglas FECHA v2 | Etiqueta `reglas-fecha-v2` |
| Antes de evaluar gold v2 | NER v2 | `data/modelo_ner.json` v2 |
| Cierres humanos | Juicios y gold v2 | `cierre_juicios_v2.json`, `cierre_gold_v2.json` |
| Entrega | Todo | `v2.0-entrega` (mar 24) |

Invalidación nueva: cambiar el lematizador tras el pool v2 invalida pool, asignación y lote 2;
cambiar Q11 a Q15 tras el pool invalida sus juicios, su gold B y sus tablas; cambiar el criterio
de relevancia tras el lote 1 anula los juicios v1 de Diego, Luis y Arturo; cambiar el NER tras evaluar
el gold v2 vuelve exploratoria la cifra nueva. La asignación de un lote no se reescribe:
`agregar_asignacion()` lo impide.
