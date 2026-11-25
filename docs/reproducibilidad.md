# Reproducibilidad

## Reconstrucción v2 desde clon limpio (2026-11-24)

Misma laptop (macOS, Apple Silicon, solo CPU), sobre un `git clone` limpio de `proyecto-final` en
`5da45df` (cierres v2, `make all-v2` y raíz promovida), sin `.venv` ni salidas previas fuera de las
versionadas. El snapshot del corpus, los paquetes de `uv` y el modelo de spaCy ya estaban en las
cachés locales; en una máquina nueva `make setup` y `make corpus` además descargan.

| Paso | Tiempo medido |
| --- | ---: |
| `make setup` | 42 s |
| `make corpus` | 41 s |
| `make indice` | 19 s |
| `make indice-lema` (lematización con spaCy) | 15 min 43 s |
| `make ranking-v2` | 14 s |
| `make agregar-juicios`, `evaluar-ir-v2`, `acuerdo-gold` | 9 s |
| `make ner-v2` (caché NER versionada: 161 de 161 pasajes, sin inferencia ni red) | 2 s |
| `make extraer-v2`, `evaluar-ie-v2`, `tablas-v2`, `booleano` | 11 s |
| `make figuras-v2` | 32 s |
| `make promover-v2` | 0 s |
| Total | 18 min 33 s |

Resultado: los seis CSV de la raíz, todos los CSV de `salida/v2/`, las figuras y
`salida/v2/promocion_raiz.json` quedan idénticos byte a byte a los versionados. Solo cambian marcas
de tiempo y duraciones (`data/corpus_meta.json`, `data/indice_meta.json`,
`salida/v2/05_registro_evaluacion.json`, `salida/v2/05a_acuerdo.json`,
`salida/v2/07_registro_ner_v2.json`, `salida/v2/08_resumen_extraccion.json`), que informan y no
identifican. La prueba encontró que `salida/v2/02_comparacion_stem_lema.md` estaba versionado sin
las filas de Q11 a Q15 (se generó antes de aprobarlas); se actualizó con el regenerado.

```bash
git clone <url> limpio && cd limpio
make setup corpus indice indice-lema all-v2
make validar
```

## Reconstrucción v1 desde clon limpio (2026-11-11)

Prueba hecha en la laptop del alumno (macOS, Apple Silicon, solo CPU) sobre un `git clone` limpio
del commit con el borrador del reporte y las láminas, sin `.venv` ni salidas previas fuera de las
versionadas. El snapshot del corpus ya estaba en la caché local de Hugging Face, así que la
descarga no se midió; en una máquina nueva `make corpus` además descarga el dataset.

| Paso | Tiempo medido |
| --- | ---: |
| `make setup` | 31 s |
| `make corpus` | 33 s |
| `make indice` | 17 s |
| `make ranking` | 6 s |
| `make pool` | 1 s |
| `make evaluar-ir` | 10 s |
| `make reglas` | 10 s |
| `make ner` (caché NER versionada, sin inferencia ni red) | 0 s |
| `make extraer` | 1 s |
| `make evaluar-ie` | 6 s |
| `make tablas` | 2 s |
| Total | ≈ 2 min |

Resultado: `ranking.csv`, `resultados_ir.csv`, `entidades.csv`, `resultados_ie.csv` y
`salida/respuestas.csv` quedan idénticos byte a byte a los versionados. Las únicas diferencias son
marcas de tiempo y duraciones (`fecha_descarga`, `construido`, `ejecutado`, tiempos) en
`data/corpus_meta.json`, `data/indice_meta.json`, `salida/03_resumen.json`,
`salida/05_registro_evaluacion.json` y el manifiesto, que informan y no identifican (PRD §11.1).

La prueba encontró un falso aviso: `08_extraer.py` marcaba la corrida como exploratoria porque
`config/tablas_respuesta.yaml` y `config/excluir_tablas.yaml` se agregaron después de
`reglas-congeladas`. Se corrigió la comprobación para contar solo archivos congelados modificados,
renombrados o borrados; las entidades no cambian (ver `docs/decisiones.md`).

## Cómo repetirla

```bash
git clone <url> limpio && cd limpio
make setup corpus indice ranking pool resultados
git status --short   # solo deben aparecer archivos con marcas de tiempo
```

`make reporte` necesita además pandoc y Chrome (lo instala `make setup`).
