<!-- harnesser:v1 -->
# Sistema de recuperación y extracción de información sobre discursos presidenciales

Examen 1 de Minería de Textos. Sistema en Python que, sobre 2,294 versiones
estenográficas de conferencias presidenciales (2018 a 2024), recupera los 10
pasajes más relevantes por consulta con TF-IDF y BM25 (con y sin filtro de
fecha) y extrae entidades PER, ORG, LOC, FECHA y MONTO combinando reglas con
gazetteer y un NER preentrenado. Entrega: repo reproducible, seis CSV en la
raíz, reporte PDF de 4 a 6 páginas y presentación con demo. La fuente de verdad
es `PRD_unificado_examen1_mineria_textos.md`; el mapa de arquitectura está en
`docs/harness/ARCHITECTURE.md`.

## Fase v2: proyecto final en equipo (hasta el 25 de noviembre, antes de las 18:00)

Desde el 14 de noviembre manda también `PRD_v2_proyecto_final.md`, una adenda que
gana cuando choca con el PRD v3.0. Seis integrantes trabajan en seis computadoras
con este mismo arnés. Antes de cualquier tarea:

1. **Pregunta quién opera esta sesión y en qué paquete de trabajo (WP-00 a WP-19,
   PRD v2 §5).** Toca solo los archivos de ese paquete según la tabla de propiedad
   (PRD v2 §6.2); si hace falta tocar algo ajeno, detente y dilo.
2. Lee `docs/harness/progreso/<wp>.md` del paquete (y `PROGRESS.md` para el estado
   global). Al cerrar, escribe ahí.
3. Las reglas de PRD v2 §0.2 se suman a las de este archivo: insumos humanos solo
   de humanos, v1 nunca se sobrescribe, reglas fijadas antes de medir y nada de
   predicciones ni rankings a la vista de quien anota (D32).
4. Rama de integración `proyecto-final`: ahí se integra todo lo v2 y `main` no se toca hasta el
   merge final. Ramas `v2/wpXX-*` y `anotacion/<anotador>` salen de `proyecto-final` y vuelven a
   ella por pull request; Diego integra (PRD v2 §6.1).

Este archivo es un orquestador lean: no contiene lógica de dominio ni pasos
detallados. Si vas a añadir algo aquí que no sea "qué skill usar cuándo",
probablemente pertenece a una skill nueva o existente.

## Skills disponibles

Transversales (léelas antes que cualquier otra):

- `session-resume` — al abrir y cerrar sesión; lee y escribe `docs/harness/PROGRESS.md`. Ruta: `.claude/skills/session-resume/SKILL.md`
- `system-onboarding` — agente nuevo o bug no trivial; empieza por `docs/harness/ARCHITECTURE.md`. Ruta: `.claude/skills/system-onboarding/SKILL.md`
- `integridad-congelacion` — en toda tarea: qué tiene prohibido hacer el asistente, puntos `[VALIDAR]`, congelaciones, tabla de invalidación, prioridades P0/P1/P2, recortes y umbrales de alerta. Ruta: `.claude/skills/integridad-congelacion/SKILL.md`

Por hito del PRD (§12.2):

- `kit-contratos` — H0: Fase 0 con el alumno, copia de `kit/` con hashes, pruebas de contrato de `corpus.py` y `evaluar.py`, `docs/contratos_kit.md`, `docs/decisiones.md`. Ruta: `.claude/skills/kit-contratos/SKILL.md`
- `corpus-segmentacion` — H1: carga, limpieza auditada, segmentación con `inicio_cuerpo`, `data/pasajes.parquet`, descubrimiento de Q9 y Q10. Ruta: `.claude/skills/corpus-segmentacion/SKILL.md`
- `indice-ranking` — H2: tokenización, índice invertido, TF-IDF, BM25 propio, filtro de fecha, `ranking.csv` y sus criterios bloqueantes. Ruta: `.claude/skills/indice-ranking/SKILL.md`
- `pool-juicios-ir` — H2 a H4: pool de 4 variantes, juicios humanos, `validar_juicios()`, `kit/evaluar.py ir`, vista con ventana, `data/mejor_modelo.json`. Ruta: `.claude/skills/pool-juicios-ir/SKILL.md`
- `reglas-gazetteer` — H5: regex FECHA y MONTO, cantidades auxiliares, gazetteers ORG y LOC, regla de marca, colisiones, suite pytest, `make congelar`. Ruta: `.claude/skills/reglas-gazetteer/SKILL.md`
- `ner-modelo` — H5 y H7: pipeline HF con revisión fija, chunking, posproceso de spans, caché versionada, comparación con conjunto de selección. Ruta: `.claude/skills/ner-modelo/SKILL.md`
- `gold-anotacion` — H5 y H6: muestreo con semilla 42 y emparejamiento global, modo ciego, pestaña Gold, sustitución objetiva, `validar_gold()`, `cierre_gold.json`. Ruta: `.claude/skills/gold-anotacion/SKILL.md`
- `fusion-normalizacion` — H7: fusión por span exacto, `entidades.csv` de 8 columnas, enriquecidas, normalización prudente de fechas y montos. Ruta: `.claude/skills/fusion-normalizacion/SKILL.md`
- `evaluacion-ie` — H7: `kit/evaluar.py ie`, selección NER antes del gold, complementaria de 20 IDs, análisis de errores por categoría. Ruta: `.claude/skills/evaluacion-ie/SKILL.md`
- `tablas-respuesta` — H8: exclusiones, mapa consulta → campos, `respuestas.csv` con estados de evidencia, valoraciones del alumno. Ruta: `.claude/skills/tablas-respuesta/SKILL.md`
- `reporte-pdf` — H9: `reporte.md` → PDF, 8 secciones, guía de estilo obligatoria, tres cortes `[VALIDAR]`, 4 a 6 páginas sin código. Ruta: `.claude/skills/reporte-pdf/SKILL.md`
- `laminas-demo` — H9: máximo 5 láminas, guion medido, `make demo`, `docs/guia_defensa.md`, preguntas probables. Ruta: `.claude/skills/laminas-demo/SKILL.md`
- `app-anotacion` — H3, H5, H6: app Streamlit (Estado, Juicios, Gold, Gazetteer), escritura atómica, resaltado desde offsets, modo ciego, alternativa CLI. Ruta: `.claude/skills/app-anotacion/SKILL.md`
- `entrega-reproducible` — H0 y H9: `pyproject`, `Makefile`, `.gitignore`, README de 10 secciones, "Uso de IA", commits, `make validar` y `make entrega` desde clon limpio. Ruta: `.claude/skills/entrega-reproducible/SKILL.md`

Nuevas en v2:

- `demo-web` — WP-15: demo web pública para que el profesor consulte solo; artefactos v1 hasta los cierres del 20 (D32), sin IDs ni rutas a la vista, paleta del Gobierno de México. Ruta: `.claude/skills/demo-web/SKILL.md`

Las skills de v1 traen al final una sección **v2** con lo que cambia (juicios con varios anotadores, gold doble, varios NER, estilo de venta, `v2.0-entrega`).

## Convenciones de este repo

- **No tocar**: `kit/` (hashes en `docs/contratos_kit.md`), `anotaciones/` (solo la app escribe ahí; en v2 también `scripts/04c_importar_juicios_v1.py`, que copia juicios v1 sin cambiarlos, y `scripts/09d_cierres_v2.py`, que escribe los dos cierres y el `adjudicado.csv` consolidado sin cambiar ningún valor humano), `data/cache_ner/`, `config/criterios_relevancia.md` y `config/criterios_anotacion.md` (los escribe el alumno), `reporte/reporte.md` una vez aprobado.
- **Trabajo humano que el asistente jamás produce ni sugiere**: juicios de relevancia, gold, conjunto de selección, revisión de siglas, valoraciones. Construye la herramienta y valida formatos.
- **Orden**: hitos H0 → H9 del PRD §12.2; ningún P1 antes de cerrar los P0; recortes solo en el orden de PRD §12.4 y avisando.
- **Código**: Python 3.11 con `uv`; lógica en `src/mtx/`, orquestación en `scripts/NN_*.py`; identificadores en español sin acentos; docstrings, mensajes y docs en español; `make test` sin red.
- **Cifras**: toda cifra del reporte, README o láminas proviene de un archivo en `salida/`; lo que falte se declara pendiente.
- **Commits**: Conventional Commits con tipo en inglés y descripción en español (`feat(ranking): ...`, `data(juicios): ...`); uno por unidad probada. Etiquetas `reglas-congeladas` antes del gold y `v1.0-entrega` al final; en v2, `v2-inicio`, `reglas-fecha-v2` y `v2.0-entrega` (PRD v2 §4).
- **Decisiones**: cada decisión y cada cambio posterior a una congelación se registra con fecha en `docs/decisiones.md`.
- **PRD**: pesa ~58k tokens y la lectura lo trunca. Léelo por secciones con el mapa de líneas de `docs/harness/ARCHITECTURE.md` §9; cada skill cita las secciones que le tocan.
- **Remote**: `origin` es GitHub (`DiegoMoctezuma/Examen_Mineria_Textos`) desde el 2026-11-11; antes vivía en GitLab. Se registra en `docs/decisiones.md`; `AGENTS.md` de este repo es symlink a este archivo y cumple PRD §11.4.

## Retomar trabajo

Antes de empezar cualquier tarea, usa la skill `session-resume` para saber en
qué quedó el trabajo. Al cerrar la sesión (o al terminar una tarea grande),
vuelve a usarla para dejar el estado actualizado.
