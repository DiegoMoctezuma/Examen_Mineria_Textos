---
name: laminas-demo
description: "Usa esta skill cuando vayas a preparar las láminas (máximo 5), el guion medido en laminas/guion.md, la demo en terminal (make demo Q=Q3, scripts/13_demo.py, src/mtx/demo.py), la generación opcional con python-pptx (src/mtx/laminas.py, scripts/12_laminas.py) o docs/guia_defensa.md con las preguntas probables de la presentación."
---
# Láminas, guion, demo y guía de defensa

Cubre el requisito R10 (PRD §2): presentación de 8 minutos con demo en vivo y máximo 5 láminas. Fuentes: PRD §6.15 (láminas y guion), §6.16 (demo), §10 (guía de defensa), §12 (H9 y después de la entrega), §13 condición 12 y anexo C.

## Cuándo usarla

- Al escribir o modificar `src/mtx/laminas.py`, `src/mtx/demo.py`, `scripts/12_laminas.py` o `scripts/13_demo.py`.
- Al redactar `laminas/guion.md`, `laminas/laminas.pptx` o `docs/guia_defensa.md`.
- Al ensayar o medir la presentación, o al preparar la salida de contingencia de la demo.
- Entre la entrega (`v1.0-entrega`) y la presentación: solo ensayo; nada de este trabajo cambia cifras del reporte.

## Prerrequisitos

1. Corrido todo el pipeline hasta el script 11: existen `ranking.csv`, `data/mejor_modelo.json`, `entidades.csv`, `resultados_ir.csv`, `resultados_ie.csv`, `salida/respuestas.csv`, `salida/tablas_respuesta/*.md` y las figuras de `reporte/figuras/` (`ir_ap_por_consulta.png`, `ir_map_por_modelo.png`, `ie_f1_por_tipo_metodo.png`, `ie_errores_por_categoria.png`).
2. Existen `salida/02_postings.md` (postings de "huachicol") y `salida/09_resumen_errores.csv` (errores reales de IE).
3. Caché NER en `data/cache_ner/` para los pasajes del top-10 de las consultas de `data/consultas.csv`.
4. Congelación respetada: las láminas y la demo consumen artefactos, nunca los regeneran (ver `integridad-congelacion`).

Prioridades: contenido de láminas, guion, demo en terminal y guía de defensa son P0; generación automática con `python-pptx` y pestaña "Demo" de la app son P2 (PRD §6.15, §6.16).

## Láminas (máximo 5)

Patrón "concepto + artefacto" en 16:9: columna izquierda (40 %) con 3 a 5 líneas; columna derecha (60 %) con una figura o tabla REAL del proyecto. Títulos en mayúscula inicial, paleta de dos colores más gris, pie con nombre del alumno y número de lámina (PRD §6.15).

| Lámina | Concepto (izquierda) | Artefacto (derecha) |
| --- | --- | --- |
| 1 | Problema, corpus, limpieza, unidad de recuperación, pipeline en una línea | Diagrama del pipeline y cifras del corpus (`salida/01_limpieza.json`, `data/corpus_meta.json`) |
| 2 | Segmentación e índice: decisiones y qué cambió | Tabla de sensibilidad o de descartes (`salida/01_sensibilidad_segmentacion.csv` si existe) y postings de "huachicol" (`salida/02_postings.md`) |
| 3 | IR: TF-IDF frente a BM25, con y sin filtro, consulta difícil | `reporte/figuras/ir_ap_por_consulta.png` y tabla de MAP (`resultados_ir.csv`) |
| 4 | IE: reglas más modelo, fusión, errores típicos | Tabla P/R/F1 por tipo y método (`resultados_ie.csv`) y 3 ejemplos reales de error (`salida/09_resumen_errores.csv`) |
| 5 | Demo y limitaciones: qué se muestra en vivo y tabla de respuesta de una consulta | `salida/tablas_respuesta/Q3.md` y el comando `make demo Q=Q3` |

Pasos:

1. Elegir vía: a mano con las figuras de `reporte/figuras/` toma menos de una hora y es la opción por defecto; `scripts/12_laminas.py` con `python-pptx` solo si sobra tiempo (P2).
2. Insertar únicamente figuras y tablas ya producidas por los scripts; ninguna cifra se escribe a mano ni se recalcula.
3. Verificar que cada cifra de las láminas coincide con `reporte/reporte.md` (mismo MAP, mismos F1).
4. Guardar como `laminas/laminas.pptx` y pasar `[VALIDAR]` con el alumno (láminas y guion juntos).

## Guion medido

`laminas/guion.md` es P0 (PRD §6.15, U18). Reparto: ≈5 min de exposición, 2 min de demo, 1 min de margen; total ≤ 8 min (condición 12, PRD §13).

1. Escribir el guion por lámina: qué se dice, qué se señala en el artefacto y la transición a la siguiente (≈1 min por lámina).
2. Añadir la sección "Demo" con el comando exacto, qué parte de la salida se comenta y en qué orden (2 min).
3. Añadir la sección "Preguntas probables" con las filas del anexo C, respuesta preparada en 2 o 3 líneas y dónde está la evidencia (ver tabla más abajo).
4. Ensayar con cronómetro y registrar el tiempo medido en el guion ("Ensayo AAAA-MM-DD: X min YY s"). Si pasa de 8 min, recortar líneas de láminas, no la demo.
5. Repetir el ensayo con `docs/guia_defensa.md` a la mano entre la entrega y la presentación (PRD §12).

El tiempo medido es evidencia de la condición 12: sin ensayo registrado, el guion no está terminado.

## Demo en terminal

Comando (PRD §6.16): `make demo Q=Q3` o `uv run python scripts/13_demo.py --consulta "refinería de Dos Bocas en Tabasco" --desde 2019-01-01 --hasta 2022-12-31`.

Reglas para `src/mtx/demo.py` y `scripts/13_demo.py`:

1. Imprime con `rich`, sin red, sobre artefactos cacheados; no recalcula índices ni métricas.
2. Secciones en este orden: consulta y ventana; top-10 de TF-IDF y BM25 lado a lado (rango, `passage_id`, fecha, posición, puntaje, 100 caracteres); pasajes; entidades del top-10 del mejor modelo (`data/mejor_modelo.json`) agrupadas por pasaje con color por tipo y método; tabla de respuesta con evidencia.
3. Mide y muestra la latencia de primera carga y con caché. Meta: menos de 30 s con caché. Si no se cumple, revisar la carga de artefactos antes del ensayo.
4. Consulta libre (no está en `data/consultas.csv`): ejecuta el NER en caliente sobre los 10 pasajes (20 a 40 s en CPU), avisa en pantalla que es NER en caliente y no le atribuye métricas del experimento (ni MAP ni F1).
5. Salida de contingencia: guardar la salida de `make demo Q=Q3` en un archivo identificado como "salida guardada, no demo en vivo". Se usa solo si falla la máquina y se anuncia como tal; nunca se presenta como demo en vivo.

Ensayo de la demo: correr dos veces seguidas antes de la presentación (primera carga y caché) y apuntar ambos tiempos en `laminas/guion.md`.

## Guía de defensa y preguntas probables

`docs/guia_defensa.md` (PRD §10): por cada módulo de `src/mtx/`, 5 líneas de qué hace, un ejemplo de entrada y salida, y las fórmulas clave que el alumno estudia y puede corregir: idf de BM25, TF-IDF sublineal, coseno, AP y F1. Riesgo mitigado: "el alumno no sabe explicar el código en la demo" (PRD §13); el alumno debe poder explicar cualquier función del paquete.

Preguntas probables (PRD anexo C, condensado); cada una va al guion con respuesta preparada:

| Pregunta | Dónde está la respuesta |
| --- | --- |
| ¿Por qué pasajes y no discursos? ¿Por qué 200 palabras? ¿Qué pasa al duplicar? | D02, `salida/01_sensibilidad_segmentacion.csv` si existe, reporte sección 2 |
| ¿Qué ruido limpiaste y cuánto? | `salida/01_limpieza.json`, reporte sección 2 |
| ¿Por qué la marca de interlocutor no entra al índice si está en el texto y se anota? | D03, PRD §3.6, reporte sección 3 |
| Postings de "huachicol", su idf y por qué es alto | `salida/02_postings.md` |
| ¿Cómo se calcula idf y BM25? ¿Por qué no coincide exacto con `rank_bm25`? | PRD §6.4 y anexo A |
| Consulta más difícil y por qué | `salida/05_ir_ganador_por_consulta.csv`, reporte sección 4 |
| ¿Qué cambia con el filtro y por qué la relevancia se juzga temáticamente? | D06, D07, PRD §6.6, reporte sección 4 |
| ¿Cómo evitaste usar el gold para elegir el NER o ajustar reglas? | D09, D15, `salida/09_comparacion_ner.csv` |
| Entidad que más falló; mayúsculas y siglas | `salida/09_resumen_errores.csv`, reporte sección 6 |
| ¿Qué respuestas tienen evidencia textual y cuáles quedan incompletas? | `salida/respuestas.csv`, `anotaciones/valoraciones.yaml` |
| Con embeddings densos, ¿qué consulta mejoraría? | Reporte sección 4 (sinónimos: Q6, Q7, Q4) |
| Cualquier función del código | `docs/guia_defensa.md` |

Las D## son decisiones registradas en `docs/decisiones.md`.

## Lista de verificación

Condición de entrega 12 (PRD §13): entre 1 y 5 láminas; guion con tiempo medido ≤ 8 minutos.

- [ ] `laminas/laminas.pptx` tiene entre 1 y 5 láminas, 16:9, patrón 40/60, pie con nombre y número.
- [ ] Toda figura y tabla de las láminas proviene de `reporte/figuras/`, `reporte/tablas/` o `salida/`, y sus cifras coinciden con `reporte/reporte.md`.
- [ ] `laminas/guion.md` tiene exposición, demo, preguntas del anexo C con respuesta y tiempo de ensayo registrado ≤ 8 min.
- [ ] `make demo Q=Q3` corre sin red, muestra las cinco secciones y tarda menos de 30 s con caché (tiempos anotados).
- [ ] Consulta libre avisa NER en caliente y no muestra métricas del experimento.
- [ ] Existe salida de contingencia marcada como salida guardada.
- [ ] `docs/guia_defensa.md` cubre todos los módulos de `src/mtx/` con ejemplo y las cinco fórmulas.
- [ ] `[VALIDAR]` de láminas y guion hecho con el alumno.
- [ ] Después de `v1.0-entrega` no se tocó código que afecte cifras del reporte; solo ensayo.

## Skills relacionadas

- `integridad-congelacion`: la demo y las láminas consumen artefactos congelados; cualquier cambio posterior a la entrega pasa por ahí.
- `reporte-pdf`: origen de `reporte/figuras/` y de las cifras que las láminas deben repetir sin alterar.
- `tablas-respuesta`: produce `salida/tablas_respuesta/Q3.md` y `salida/respuestas.csv` que muestra la lámina 5 y la demo.
- `pool-juicios-ir`: fija `data/mejor_modelo.json`, el modelo cuyas entidades muestra la demo.
- `entrega-reproducible`: `make entrega` y la etiqueta `v1.0-entrega` que marcan el inicio del periodo de solo ensayo.

## v2: presentación de venta (PRD v2 D36 y tabla 1.3; WP-16, WP-17, WP-18)

- La regla de "máximo 5 láminas" ya no aplica: número libre, **15 a 20 min con demo** (PV6).
- Público: cliente de gobierno. Problema → solución → evidencia → demo; limitaciones como
  "siguiente paso" con su mejora.
- Sin rutas, comandos, `passage_id` ni tablas con formato de dataframe; nombres de consulta en vez
  de Qn ("Pregunta 1 · Tren Maya"); ejes nombrados; porcentajes donde ayuden; un ejemplo real por
  lámina técnica.
- Paleta del Gobierno de México (guinda `#9F2241` y `#691C32`, dorado `#BC955C` y `#DDC9A3`, gris
  `#98989A`) y Montserrat con Noto Sans, a confirmar con el manual vigente (PV8).
- Argumento de reporteros: el corregido de PRD v2 §3.14, textual.
- Las láminas las diseña el equipo (Gonzalo y Arturo). Claude Code escribe `laminas/guion_v2.md`
  con minutos por lámina y persona y `docs/guia_defensa_v2.md`, y verifica cada cifra en
  `salida/`. El ensayo registra `Tiempo medido: m:ss` entre 15:00 y 20:00.
- Revisión ciega (WP-18): `docs/revision_ciega_prompt.md` para un LLM sin contexto.
- La demo de terminal se sustituye por la demo web (skill `demo-web`).
