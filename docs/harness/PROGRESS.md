# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

- Arnés (`/harnesser`): CLAUDE.md, AGENTS.md, 17 skills, `docs/harness/`.
- H0 cerrado (2026-11-04): entorno `uv` (Python 3.11, torch CPU, plotly y kaleido), `Makefile`, kit copiado a `kit/` con hashes, `src/mtx/adaptadores_kit.py`, 42 pruebas de contrato, `docs/contratos_kit.md`, `docs/decisiones.md`. Alumno: Diego Moctezuma (nombre corregido el 2026-11-07). Plazo: entrega y presentación el 11 de noviembre de 2026, presentación a las 20:00 (CDMX). Repo de entrega: este GitLab.
- H1 (2026-11-04): `src/mtx/corpus.py` (limpieza, canonización de marcas, fechas, duplicados, segmentación), `config/limpieza.yaml`, `scripts/01_corpus_y_pasajes.py`, `make corpus` verde: 127,739 pasajes, 5 discursos excluidos, 10 fechas reparadas. Descubrimiento de Q9 y Q10 (`make explorar`, `salida/00_candidatos_q9q10.md`). `data/consultas.csv` con Q1 a Q10 (`make consultas`). 79 pruebas rápidas verdes.

- H2 (2026-11-07), índice y ranking cerrados: `tests/test_indice.py` (T03) y `tests/test_ranking.py` (T04 a T06, D03, formato, evaluador del kit con juicios sintéticos, prueba lenta de contenido), `scripts/02_indice.py` y `scripts/03_ranking.py`. `make indice ranking` produce `ranking.csv` (400 filas, validado, copia en la raíz) y `salida/02_*` y `salida/03_*`, deterministas. `ranking.buscar()` listo para la demo y la app. 137 pruebas rápidas y la lenta, en verde.
- Q9 y Q10 aprobadas por el alumno sin cambios (2026-11-07); `[VALIDAR]` cerrado y registrado en `docs/decisiones.md`. Ya se pueden generar rankings.
- Entorno macOS arm64 listo (2026-11-07): `uv`, `make setup`, `make corpus` (mismo hash de pasajes que en Linux) y `make test` con 94 pruebas verdes.

## Pendiente

1. Cierre de H2 (skills `pool-juicios-ir` e `indice-ranking`): `src/mtx/pool.py` y `scripts/04_pool.py` (pool de las 4 variantes para los juicios).
2. H3 (alumno): `config/criterios_relevancia.md` `[VALIDAR]` y juicios en la app. Luego H4 a H9 (PRD §12.2).
3. Alumno: verificar que el profesor tenga acceso a este repo de GitLab (el enunciado habla de GitHub).

## Decisiones

Ver `docs/decisiones.md`. Las no obvias: el corpus real tiene otro formato de marcas que el PRD (parser propio); acotaciones por lista y no por mayúsculas (se conservan siglas como `(IMSS)`); candidatas de fecha fuera de rango se descartan; el 65 % de las intervenciones de reporteros queda bajo 40 palabras y el reporte debe discutirlo (costo de D02); plotly en lugar de matplotlib por indicación del profesor.

## Bloqueos

- Falta `xelatex` en la Mac (solo para `make reporte`, H9): instalar BasicTeX o MacTeX antes del reporte.
- Kaleido necesita el Chrome que instala `plotly_get_chrome` (`make setup` lo hace); los Chromium de snap fallan.
