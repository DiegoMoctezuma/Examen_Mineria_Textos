# Sistema de recuperación y extracción de información sobre discursos presidenciales

Examen 1 de Minería de Textos (Licenciatura en Ciencia de Datos). Sistema en
Python que, sobre el corpus `carevies/discursos_AMLO` (versiones estenográficas
de conferencias y discursos de 2018 a 2024), recupera los 10 pasajes más
relevantes por consulta con TF-IDF y BM25 (con y sin filtro de fecha) y extrae
entidades PER, ORG, LOC, FECHA y MONTO combinando reglas con gazetteer y un NER
preentrenado para español.

## Estado

Hitos H0 (preparación) y H1 (datos) hechos, con Q9 y Q10 aprobadas; H2 (recuperación) con índice y rankings listos (`ranking.csv`); falta el pool para los juicios. Ya
corren `make setup`, `make contratos`, `make corpus`, `make consultas`,
`make explorar`, `make indice`, `make ranking` y `make test`. Siguen el pool de H2, H3 y H6 (juicios y
gold, trabajo humano) y el resto hasta H9. Este README se reemplaza en H9 por el
README de 10 secciones que exige el enunciado (instalación desde cero,
reproducción de resultados, flujo completo, uso de IA).

Uso mínimo hoy (Linux o macOS, Python 3.11 y `uv`):

```bash
make setup      # entorno, torch CPU, Chrome para kaleido
make contratos  # pruebas de contrato del kit (kit/ no se modifica)
make corpus     # descarga el corpus, limpia y segmenta: data/pasajes.parquet
make consultas  # data/consultas.csv = kit + Q9 + Q10
make indice     # tokens, índice invertido y TF-IDF en data/
make ranking    # ranking.csv: TF-IDF y BM25, con y sin filtro de fecha
make test       # pruebas rápidas, sin red
```

## Documentos de referencia

| Archivo | Qué es |
| --- | --- |
| `PRD_unificado_examen1_mineria_textos.md` | Especificación completa (v3.0, 4 de noviembre de 2026). Fuente de verdad del proyecto |
| `CLAUDE.md` / `AGENTS.md` | Orquestador para asistentes de programación: índice de skills, convenciones y qué no tocar |
| `docs/harness/ARCHITECTURE.md` | Mapa de componentes, flujos de datos, congelaciones e invalidación |
| `docs/harness/PROGRESS.md` | Estado del trabajo entre sesiones |
| `docs/decisiones.md` | Fase 0 y cada decisión con fecha (formato real del corpus, fechas, plotly) |
| `docs/contratos_kit.md` | Hashes y comportamiento verificado de `kit/` |
| `.claude/skills/` | Skills por hito (H0 a H9); `.agents/skills/` las expone a otros agentes |

## Entregables previstos

Seis CSV en la raíz (`ranking.csv`, `juicios_relevancia.csv`, `resultados_ir.csv`,
`entidades.csv`, `gold_entidades.csv`, `resultados_ie.csv`), reporte PDF de 4 a
6 páginas, presentación de 8 minutos con demo en vivo y `make entrega`
reproducible desde un clon limpio.
