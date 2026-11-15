---
name: demo-web
description: "Usa esta skill al construir, probar o publicar la demo web pública del proyecto final (src/mtx/web/, src/mtx/presentacion.py, scripts/14_publicar_demo.py, Dockerfile o archivos del Space de Hugging Face), donde el profesor escribe consultas y ve pasajes y entidades, o al decidir con qué artefactos corre (v1 hasta los cierres del 20, v2 después)."
---
# Demo web pública (PRD v2 WP-15, D32, D36)

Dueños: Bruno (líder) y Leo. Reemplaza a la demo de terminal: el profesor pidió una página a la
que pueda conectarse y hacer sus propias consultas. Carga antes `integridad-congelacion`.

## Cuándo usarla
- Al tocar `src/mtx/web/`, `src/mtx/presentacion.py`, `scripts/14_publicar_demo.py` o los archivos
  de despliegue.
- Al elegir la tecnología o el hospedaje, o al cambiar los artefactos que la demo carga.

## Decisiones fijas
1. **Tecnología:** la deciden Bruno y Leo antes del lunes 16 y se registra en `docs/decisiones.md`.
   Recomendación: Streamlit que reusa `ranking.buscar()` y `mtx.app.componentes`
   (`html_desde_spans`, resaltado desde offsets), en un Space de Hugging Face. Los artefactos pesan
   unos 200 MB (pasajes 70, índice 45, TF-IDF 67): verificar memoria y límites del plan gratuito
   antes de comprometerse (PV9). Streamlit Community Cloud probablemente no alcanza.
2. **Datos (D32):** hasta los cierres del viernes 20 la demo usa **solo artefactos v1**
   (`ranking.csv`, `entidades.csv`, `respuestas.csv` de `v1.0-entrega`). Bruno y Leo juzgan y Bruno
   anota gold: no deben ver rankings lematizados, de Q11 a Q15 ni predicciones de su lote. Desde el
   sábado 21, datos v2.
3. **Nada del arnés a la vista:** sin `passage_id`, rutas, comandos, nombres de variantes ni tablas
   con formato de dataframe. Cada pasaje se presenta con `presentacion.py`, por ejemplo
   "Mañanera del 12 de marzo de 2021 · fragmento 3".
4. **Estilo (D36):** paleta del Gobierno de México (guinda `#9F2241` y `#691C32`, dorado `#BC955C`
   y `#DDC9A3`, gris `#98989A`), Montserrat y Noto Sans; confirmar con el manual vigente (PV8).
   Nombres de consulta en vez de Qn.
5. **Funciones:** las 15 consultas precalculadas con su tabla de respuesta y evidencia; consulta
   libre con TF-IDF o BM25 y filtro de fechas opcional; entidades resaltadas por tipo. La consulta
   libre avisa cuando corre NER en caliente y muestra el tiempo de respuesta. Si la memoria no
   alcanza, se recorta a las 15 precalculadas (PRD v2 §8), nunca la demo entera.
6. **Sin red en las pruebas:** `make test` no descarga modelos ni llama al Space.

## Pruebas mínimas
- `presentacion.py` con fechas y títulos reales (incluye fecha desconocida).
- La vista no muestra `passage_id` ni rutas (buscar en el HTML generado).
- Consulta libre sin resultados o fuera del corpus responde sin error.
- Resaltado con `<`, `&` y caracteres fuera del BMP respeta offsets (reusar T15).

## Publicación
- `scripts/14_publicar_demo.py` empaqueta los artefactos permitidos según la fecha (v1 o v2) y
  escribe un manifiesto con sus hashes; no sube nada sin que el dueño lo pida.
- El enlace público va al README y a la lámina de demo. El repo del Space no guarda credenciales.

## Skills relacionadas
- `app-anotacion`: componentes de resaltado reutilizables.
- `indice-ranking`: `ranking.buscar()` y el filtro de fechas.
- `tablas-respuesta`: tablas de respuesta con evidencia.
- `laminas-demo`: la lámina de demo y el guion v2.
