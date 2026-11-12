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

## Convenciones de este repo

- **No tocar**: `kit/` (hashes en `docs/contratos_kit.md`), `anotaciones/` (solo la app escribe ahí), `data/cache_ner/`, `config/criterios_relevancia.md` y `config/criterios_anotacion.md` (los escribe el alumno), `reporte/reporte.md` una vez aprobado.
- **Trabajo humano que el asistente jamás produce ni sugiere**: juicios de relevancia, gold, conjunto de selección, revisión de siglas, valoraciones. Construye la herramienta y valida formatos.
- **Orden**: hitos H0 → H9 del PRD §12.2; ningún P1 antes de cerrar los P0; recortes solo en el orden de PRD §12.4 y avisando.
- **Código**: Python 3.11 con `uv`; lógica en `src/mtx/`, orquestación en `scripts/NN_*.py`; identificadores en español sin acentos; docstrings, mensajes y docs en español; `make test` sin red.
- **Cifras**: toda cifra del reporte, README o láminas proviene de un archivo en `salida/`; lo que falte se declara pendiente.
- **Commits**: Conventional Commits con tipo en inglés y descripción en español (`feat(ranking): ...`, `data(juicios): ...`); uno por unidad probada. Etiquetas `reglas-congeladas` antes del gold y `v1.0-entrega` al final.
- **Decisiones**: cada decisión y cada cambio posterior a una congelación se registra con fecha en `docs/decisiones.md`.
- **PRD**: pesa ~58k tokens y la lectura lo trunca. Léelo por secciones con el mapa de líneas de `docs/harness/ARCHITECTURE.md` §9; cada skill cita las secciones que le tocan.
- **Remote**: `origin` es GitHub (`DiegoMoctezuma/Examen_Mineria_Textos`) desde el 2026-11-11; antes vivía en GitLab. Se registra en `docs/decisiones.md`; `AGENTS.md` de este repo es symlink a este archivo y cumple PRD §11.4.

## Retomar trabajo

Antes de empezar cualquier tarea, usa la skill `session-resume` para saber en
qué quedó el trabajo. Al cerrar la sesión (o al terminar una tarea grande),
vuelve a usarla para dejar el estado actualizado.
