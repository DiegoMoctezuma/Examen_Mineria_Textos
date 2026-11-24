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

## Formatos de la referencia y su equivalente en FECHA v2

El notebook lista estas variantes (en inglés) y cuatro reglas de normalización para ordenar las
notas por fecha (se califica con tau de Kendall).

| Variante del notebook | En FECHA v2 | Ejemplo inventado |
| --- | --- | --- |
| `04/20/2009`, `04/20/09`, `4/3/09` | Ya en v1, pero en orden día/mes/año (México), no mes/día | `15/12/2023`, `1/1/19` |
| `4-13-82` (guion, aparece en `dates.txt`) | Guion y punto con año de 4 cifras | `15-12-2023`, `15.12.2023` |
| `Mar-20-2009`, `Mar 20, 2009`, `March 20, 2009` | **No se adopta**: el mes antes del día no se usa en español | — |
| `20 Mar 2009`, `20 Mar. 2009`, `20 March 2009` | Día, mes abreviado y año; con el mes completo ya estaba en v1 | `15 dic 2023`, `15-dic-23` |
| `Mar 20th`, `Mar 21st`, `Mar 22nd` (ordinales) | Ordinal del día primero | `1o. de diciembre`, `1º de julio` |
| `Feb 2009`, `Sep 2009` | Mes abreviado y año; con el mes completo ya estaba en v1 | `dic. 2023`, `diciembre de 2023` |
| `6/2008`, `12/2009` | Mes/año | `12/2023` |
| `2009`, `2010` | Ya en v1, solo con contexto temporal (un número de cuatro cifras suelto no es FECHA) | `en 2019` |

| Regla del notebook | En FECHA v2 |
| --- | --- |
| `xx/xx/xx` es mes/día/año | **No se adopta**: en México es día/mes/año |
| Año de dos cifras → 19xx | **No se adopta**: el corpus va de 2018 a 2024; se conserva v1 (00 a 30 → 20xx; 31 a 99 → `ambiguo_siglo`) |
| Sin día → día 1 | **No se adopta**: se conserva la precisión `AAAA-MM`, para no inventar un día que el texto no dice |
| Sin mes → 1 de enero | **No se adopta**: se conserva la precisión `AAAA` |

No se cubren dos cosas que sí trae `dates.txt`: el guion con año de dos cifras (`4-13-82`) y los
meses mal escritos (`Janaury`, `Decemeber`).

## Formatos que agrega v2 sin equivalente en el notebook

- Día y año en palabras: `quince de enero`, `enero de dos mil veinte`, `el año dos mil diecinueve`.
- Fecha ISO: `2023-12-15`.

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

## Decisiones de Leo (2026-11-24)

1. No se adoptan las reglas de normalización del notebook (mes/día, año de dos cifras = 19xx, día 1
   y 1 de enero por omisión): no cambian la evaluación, que compara solo `(tipo, inicio, fin)`, y
   darían fechas falsas en las tablas de respuesta de un corpus mexicano de 2018 a 2024.
2. Guion con año de dos cifras y meses mal escritos quedan como no cubiertos: casi no aparecen en
   versiones estenográficas y tolerar errores de dedo arriesga falsos positivos (`mayor` → `mayo`).
3. `entre 2019 y 2024` es un intervalo, igual que `de 2019 a 2024`; `en 2019 y 2020` es una
   enumeración y da dos fechas (criterio FECHA v1).
