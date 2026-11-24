# Origen de las reglas FECHA v2 (WP-11)

Autor de las reglas: Leo Yahir Carpio Angeles, con Claude Code. Código en `src/mtx/fecha_v2.py`,
pruebas en `tests/test_fecha_v2.py`. Las reglas se escribieron **sin ver el gold** (ni el v1 ni
`anotaciones/gold_v2/`) y sin desarrollar sobre pasajes del corpus: todos los ejemplos de las pruebas
son frases inventadas. La única prueba que lee pasajes reales verifica offsets y no muestra contenido.

## Referencia del profesor

Material que compartió el profesor el sábado 21 de noviembre (PV7, `docs/decisiones.md`): el notebook
"Assignment 1" (versión 1.0) del curso de Coursera de minería de textos en Python y `dates.txt`
(500 notas médicas en inglés). Está en `extra/` y no se versiona, porque es material de un curso sin
licencia abierta declarada. Aquí solo se describen las ideas que se tomaron; no se copia código ni
datos del notebook.

> Pendiente: Leo confirma esta lista con el notebook en la mano (está en `extra/` de la máquina de
> Diego). Esta versión se escribió a partir de la descripción registrada en `docs/decisiones.md`.

## Qué se tomó y cómo se adaptó al español

| Idea de la referencia | Adaptación en FECHA v2 | Ejemplo inventado |
| --- | --- | --- |
| Muchos formatos para una misma fecha | Día ordinal, día en palabras, año en palabras | `1o. de diciembre de 2018`, `quince de enero`, `enero de dos mil veinte` |
| Mes abreviado | `ene` a `dic` con día y año, o con punto o guion y año | `15 dic 2023`, `15-dic-23`, `dic. 2023` |
| Separadores numéricos variados | Guion y punto (día-mes-año), ISO y mes/año | `15-12-2023`, `15.12.2023`, `2023-12-15`, `12/2023` |
| Año de dos dígitos → siglo fijo | Se conserva la regla de v1 por el rango del corpus (2018 a 2024): 00 a 30 → 20xx; 31 a 99 → `ambiguo_siglo` | `15-dic-23` → 2023-12-15 |
| Sin día → día 1; sin mes → 1 de enero | **No se adopta**: se conserva la precisión (`AAAA-MM`, `AAAA`), como en v1, para no inventar un día que el texto no dice | `dic. 2023` → `2023-12` |
| Normalizar todo a una forma comparable | `normalizar_fecha_v2` lleva cada forma nueva a la que entiende `normalizar_fecha` de v1 | `1º de julio de 2019` → 2019-07-01 |

## Lo que agrega v2 por su cuenta (criterio FECHA v1)

- Intervalos explícitos como una sola entidad, como pide `config/criterios_anotacion.md`: días entre
  meses (`15 de enero al 3 de febrero de 2021`), meses (`enero a marzo de 2021`) y años (`2019 a
  2024`, `entre 2019 y 2024`). En v1, `de 2019 a 2024` daba dos fechas sueltas (caso "no cubierto").
  Una enumeración sin "entre" (`en 2019 y 2020`) sigue dando fechas separadas.
- Con el día en palabras, el mes tiene que ir en minúscula: `cinco de mayo` es FECHA y
  `Cinco de Mayo` (avenida, festividad) no lo es.
- `de 2000 a 3000 personas` ya no da la FECHA `2000`, que v1 sí emitía.

## Lo que no cambia

`reglas.py` y `normalizacion.py` siguen como en `reglas-congeladas`. FECHA v2 vive en un módulo
aparte para que `make extraer` con las reglas v1 reproduzca las cifras v1 y no se marque como
exploratoria. MONTO, gazetteers, marca, auxiliares y colisiones son los de v1:
`extraer_reglas_v2()` solo cambia la parte de FECHA.

## Cómo se usa

```python
from mtx import fecha_v2
fecha_v2.extraer_reglas_v2(texto, inicio_cuerpo)     # en lugar de reglas.extraer_reglas
fecha_v2.normalizar_fecha_v2(texto_fecha, ancla)     # en lugar de normalizacion.normalizar_fecha
```

Se integra en `scripts/08_extraer.py --v2` (WP-12, Diego). Según D33 y el recorte 3, la evaluación de
FECHA v2 contra el gold (anotado con el criterio v1) es exploratoria y se reporta junto a la de v1.
