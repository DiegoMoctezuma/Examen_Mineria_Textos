# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

- Arnés (`/harnesser`): CLAUDE.md, AGENTS.md, 17 skills, `docs/harness/`.
- H0 cerrado (2026-11-04): entorno `uv` (Python 3.11, torch CPU, plotly y kaleido), `Makefile`, kit copiado a `kit/` con hashes, `src/mtx/adaptadores_kit.py`, 42 pruebas de contrato, `docs/contratos_kit.md`, `docs/decisiones.md`. Alumno: Diego Moctezuma (nombre corregido el 2026-11-07). Plazo: entrega y presentación el 11 de noviembre de 2026, presentación a las 20:00 (CDMX). Repo de entrega: este GitLab.
- H1 (2026-11-04): `src/mtx/corpus.py` (limpieza, canonización de marcas, fechas, duplicados, segmentación), `config/limpieza.yaml`, `scripts/01_corpus_y_pasajes.py`, `make corpus` verde: 127,739 pasajes, 5 discursos excluidos, 10 fechas reparadas. Descubrimiento de Q9 y Q10 (`make explorar`, `salida/00_candidatos_q9q10.md`). `data/consultas.csv` con Q1 a Q10 (`make consultas`). 79 pruebas rápidas verdes.

- H2 en curso (2026-11-04): `src/mtx/preproceso.py` con 12 pruebas verdes, `config/stopwords_es.txt` (copia exacta de las 313 palabras de NLTK) y `config/stoplist_extra.txt`. Escritos pero **sin probar y sin scripts**: `src/mtx/indice.py` (índice a mano, persistencia, `matriz_conteos`) y `src/mtx/ranking.py` (BM25, Tfidf, filtro, `top_k`, `Buscador`, `variantes_oficiales`). Total: 94 pruebas rápidas verdes.
- Q9 y Q10 aprobadas por el alumno sin cambios (2026-11-07); `[VALIDAR]` cerrado y registrado en `docs/decisiones.md`. Ya se pueden generar rankings.

## Pendiente

1. **Entorno en macOS arm64**: instalar `uv` (no está en esta máquina), correr `make setup` y revisar que torch CPU y kaleido funcionen en Mac (el `pyproject` solo fija el índice de torch para Linux y Windows). Después, `make corpus` para regenerar `data/pasajes.parquet` (no está versionado) y `make test` para confirmar las 94 pruebas.
2. H2 (empezar aquí, skill `indice-ranking`): escribir `tests/test_indice.py` (T03, contra `CountVectorizer`), `tests/test_ranking.py` (T04 a T06: fórmulas a mano, subclase de `rank_bm25` con tolerancia 1e-6, fecha, 0/3/10 candidatos, marca sin efecto), `scripts/02_indice.py` (tokens.parquet, índice, `02_postings.md`, `02_vocabulario_top.csv`, `02_tokens_consultas.md`) y `scripts/03_ranking.py`, luego `pool.py` y `04_pool.py`. Probar `indice.py` y `ranking.py` ya escritos; no asumir que funcionan.
3. H3 (alumno): `config/criterios_relevancia.md` `[VALIDAR]` y juicios en la app. Luego H4 a H9 (PRD §12.2).
4. Alumno: verificar que el profesor tenga acceso a este repo de GitLab (el enunciado habla de GitHub).

## Decisiones

Ver `docs/decisiones.md`. Las no obvias: el corpus real tiene otro formato de marcas que el PRD (parser propio); acotaciones por lista y no por mayúsculas (se conservan siglas como `(IMSS)`); candidatas de fecha fuera de rango se descartan; el 65 % de las intervenciones de reporteros queda bajo 40 palabras y el reporte debe discutirlo (costo de D02); plotly en lugar de matplotlib por indicación del profesor.

## Bloqueos

- `uv` no está instalado en la Mac actual: `make` no corre (punto 1 de Pendiente).
- NLTK no descarga stopwords aquí (validación de rutas); `preproceso.py` debe usar `config/stopwords_es.txt`, que hay que crear versionado en H2.
- Kaleido necesita el Chrome que instala `plotly_get_chrome` (`make setup` lo hace); los Chromium de snap fallan.
