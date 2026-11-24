---
name: ner-modelo
description: "Usa esta skill al implementar, depurar o ejecutar el NER con modelo Hugging Face del proyecto (src/mtx/ner_modelo.py, scripts/07_ner.py, config/ner.yaml, caché data/cache_ner/, comparación de candidatos NER o data/modelo_ner.json)."
---
# NER con modelo (ner_modelo.py · 07_ner.py)

## Cuándo usarla
- Al escribir o modificar `src/mtx/ner_modelo.py`, `scripts/07_ner.py`, `config/ner.yaml` o `tests/test_ner_posproceso.py`.
- Al verificar técnicamente un modelo NER antes de abrir el gold (P06), o al sustituir el principal por otro NER español.
- Al tocar la caché `data/cache_ner/`, el posproceso de spans o `salida/07_uniones_spans.csv`.
- Al comparar candidatos NER (P1) o fijar `data/modelo_ner.json`.
- No la uses para reglas regex ni gazetteers (eso es `reglas-gazetteer`), ni para fusionar con reglas (`fusion-normalizacion`).

## Prerrequisitos y congelaciones que aplican
Fuente de verdad: PRD §6.8, D09, D18, P06, T12 y §2.2 (DP).

1. Hardware: laptop personal, solo CPU. El NER corre únicamente sobre los pasajes recuperados (≤100), nunca sobre el corpus completo (PRD §2.2).
2. Entrada: `salida/ranking.csv` y `data/mejor_modelo.json` ya existen (H4). Sin mejor modelo de IR no hay ámbito definido; no inventes uno.
3. D09: el NER principal se fija por criterios técnicos ANTES de abrir el gold. Ninguna decisión de modelo, mapa de etiquetas o posproceso se toma mirando `anotaciones/gold_entidades.csv`.
4. D18: `revision` fija por modelo en `config/ner.yaml`, caché versionada en git, manifiesto de ejecución con versiones y hashes.
5. `data/cache_ner/` y `anotaciones/` son "no tocar" desde `make limpiar`; nunca los borres como parte de una limpieza.
6. Lo que se versiona: `config/ner.yaml`, `data/cache_ner/`, `data/modelo_ner.json`, `salida/`. Lo que NO: pesos de modelos (`.gitignore`).
7. Toda prosa, nombres de columnas, comentarios y commits en español; Conventional Commits (D22).

## Modelos y verificación técnica previa al gold
Modelos (PRD §6.8):
- Principal (P0): `mrm8488/bert-spanish-cased-finetuned-ner` (PER, ORG, LOC, MISC).
- Candidato 2 (P1): `PlanTL-GOB-ES/roberta-base-bne-capitel-ner` (PER, ORG, LOC, OTH).
- Las métricas de las fichas de Hugging Face NO son resultados del proyecto; no las cites como tales en reporte ni láminas.

`config/ner.yaml` por modelo: `slug`, `repo_id`, `revision` (hash de commit, registrado en la primera descarga exitosa; nunca `main`), `max_length_real`, `lote` (8 por defecto), `aggregation_strategy: simple`, `device: -1`, `mapa_etiquetas`, `version_posproceso`.

Lista de verificación P06 (correr en H5, sin gold; registrar resultado en `salida/07_verificacion_ner.md` o equivalente del manifiesto):
1. Los pesos descargados son de token-classification (cabeza NER afinada). Un modelo base sin cabeza NER no vale como principal ni como reemplazo.
2. Leer el mapa real de etiquetas desde `model.config.id2label`; no asumirlo desde la ficha. Anotar qué etiquetas existen (`B-PER`, `I-LOC`, `MISC`, `OTH`...).
3. El tokenizador es rápido (`is_fast == True`) y devuelve `offset_mapping`; sin offsets no hay proyección al texto canónico.
4. Compatibilidad del entorno: `transformers`, `torch` CPU y versiones de `uv.lock`; medir memoria de la carga.
5. Funciona sobre ejemplos de desarrollo propios (frases sintéticas o pasajes que NO estén en `anotaciones/muestra_gold.csv` ni `muestra_seleccion.csv`), con invariante de offsets en verde.
6. Si falla cualquiera: elegir y verificar otro NER español (spaCy `es_core_news_lg` está permitido por el enunciado) antes de abrir el gold, registrar el motivo en `config/ner.yaml` y en decisiones, y volver a congelar.
7. Escribir `data/modelo_ner.json` provisional (`modelo, revision, criterio: "tecnico"`); se completa en la comparación P1.

## Inferencia y mapa de etiquetas
1. `transformers.pipeline("token-classification", model=repo_id, revision=revision, aggregation_strategy="simple", device=-1)`.
2. Lotes de 8 pasajes (o ventanas); ajustar solo con medición registrada, nunca por intuición.
3. Mapa de etiquetas, aplicado solo si la etiqueta existe en `id2label` del modelo:
   - `PER` | `PERSON` → `PER`
   - `ORG` → `ORG`
   - `LOC` | `GPE` → `LOC`
   - `MISC` | `OTH` → se descarta pero se cuenta (contador por pasaje y total en el manifiesto; las obras suelen caer ahí y el gazetteer las recupera; va al análisis de errores).
4. El mapa NO se cambia por inspección de errores del gold. Si alguien propone "GPE a ORG porque el gold lo dice", la respuesta es no: queda como hallazgo del análisis de errores.
5. La `confianza` que devuelve el pipeline es un puntaje, no una probabilidad calibrada; se guarda pero no se interpreta como tal.
6. Cobertura: un NER limitado a PER/ORG/LOC no cubre FECHA ni MONTO; eso se muestra explícitamente en la evaluación (PRD §6.12), no se "rellena".

Flujo de `scripts/07_ner.py` (`--modelo <slug>` opcional, por defecto todos los de `config/ner.yaml`; `--forzar` opcional):
1. Leer ámbito desde `salida/ranking.csv` + `data/mejor_modelo.json`; cargar textos canónicos de `data/pasajes.parquet`.
2. Separar pasajes con caché vigente de los pendientes; cargar el pipeline solo si hay pendientes.
3. Inferir pendientes por lotes, escribir un JSON por pasaje en la caché.
4. Aplicar posproceso desde los JSON crudos y escribir `salida/entidades_{slug}.csv` y `salida/07_uniones_spans.csv`.
5. Registrar en el manifiesto: modelo, revisión, versiones, tiempos (primera carga y con caché), pasajes inferidos vs. cacheados, MISC/OTH descartadas.

## Pasajes largos (chunking) y offsets
1. Límite real = `model.config.max_position_embeddings` (o el `model_max_length` del tokenizador si es menor) menos los tokens especiales (`[CLS]`/`[SEP]` o `<s>`/`</s>`); nunca asumir 512 sin descontar.
2. Fragmentar en ventanas de subtokens con solapamiento explícito (parámetro en `config/ner.yaml`, p. ej. 64 subtokens). Partir por oraciones (`[.!?]\s+`) es una optimización previa, no la única defensa: una oración enorme también debe caber.
3. Proyectar offsets de cada ventana al texto canónico del pasaje con `offset_mapping` + desplazamiento de la ventana. El `texto` del pasaje es la única fuente de verdad (PRD §13, riesgo "offsets desalineados").
4. Verificar cobertura completa: la unión de ventanas cubre `[0, len(texto))` y el último fragmento no se pierde; si falla, error explícito, nunca truncamiento silencioso.
5. Deduplicar entidades repetidas en el traslape por span `(tipo, inicio, fin)`. Ante conflicto entre dos versiones del mismo tramo: primero la que no está cortada por un borde de ventana, después la de mayor confianza.
6. T12 es caso de prueba obligatorio: texto largo, una oración enorme y una entidad justo en el borde de ventana; resultado determinista y offsets correctos.

## Posproceso de spans
Versión propia (`version_posproceso` en `config/ner.yaml`) para poder cambiarla sin reinferir. Reglas U15 (PRD §6.8):
1. Recortar espacios y puntuación en los extremos del span; conservar caracteres semánticos (`$` se conserva; también dígitos y letras con acento).
2. Unión intrapalabra (`fin_1 == inicio_2`, mismo tipo): siempre, sin registro aparte.
3. Unión interpalabra: spans adyacentes del mismo tipo separados por un solo espacio (`López` + `Obrador`). Es un posproceso documentado:
   - se guarda la predicción cruda y la unida;
   - cada unión se registra en `salida/07_uniones_spans.csv` (`passage_id, tipo, inicio_1, fin_1, inicio_2, fin_2, inicio_union, fin_union, texto_union, confianza_1, confianza_2`);
   - el reporte mide el efecto (F1 con y sin unión) en vez de asumirlo.
4. Invariante por fila, tras cada etapa (crudo, recorte, unión): `texto[inicio:fin] == texto_entidad`. Si falla, la fila se rechaza con error, no se corrige a mano.
5. No eliminar entidades por "parecer ruido": el filtrado por tipo (MISC/OTH) es el único descarte y ya está contado.

## Caché versionada
Ruta: `data/cache_ner/{modelo_slug}@{revision_corta}/{passage_id}.json` (PRD §6.8, D18).
1. Clave de caché = hash de: `texto_sha256` del pasaje canónico, `repo_id`, `revision`, identificador del tokenizador, parámetros de fragmentación (longitud de ventana, solapamiento, partición por oraciones) y parámetros de inferencia (`aggregation_strategy`, `lote` no entra porque no cambia el resultado).
2. El JSON guarda: la clave, los parámetros anteriores, las entidades crudas con offsets y confianza, el contador de MISC/OTH descartadas, tiempos de inferencia y `version_transformers`.
3. El posproceso NO se cachea con la inferencia: se recalcula desde lo crudo con su `version_posproceso`; cambiar el posproceso nunca obliga a reinferir.
4. Nunca reinferir un pasaje cuya clave coincide. `--forzar` invalida y sobrescribe; sin esa bandera, la inferencia es solo para claves ausentes.
5. Si la clave guardada no coincide con la calculada (p. ej. cambió la revisión), se trata como ausente y se escribe en el nuevo directorio `{slug}@{revision_corta}`; no se borra el anterior a mano.
6. La caché se versiona en git (≤100 pasajes × 2 modelos, unos cientos de KB). Verificar: `make resultados` desde un clon limpio no descarga modelos ni requiere red. Si lo hace, es un defecto.
7. `make limpiar` nunca toca `data/cache_ner/`.

## Ámbito, tiempos y comparación de candidatos
Ámbito (PRD §6.8):
1. Solo pasajes únicos del top-10 con filtro del mejor modelo de IR (`data/mejor_modelo.json`, D08): ≤100 pasajes. Incluyen los del gold y los del conjunto de selección por construcción.
2. La inferencia puede correr antes del cierre del gold si permanece oculta al anotador: no mostrar predicciones en la app ni en archivos que el anotador abra; `data/cache_ner/` queda fuera de su vista hasta `cierre_gold.json`.
3. Tiempos: medir por separado primera carga (descarga + carga de pesos + inferencia) y corrida con caché; registrar ambos en el manifiesto. Esperado en CPU: 1 a 3 minutos por modelo. Si excede mucho, revisar lote y fragmentación antes de cambiar de modelo (riesgo "modelos BERT lentos", PRD §13).

Comparación y selección (P1, D09):
1. Para cada candidato producir `salida/entidades_{slug}.csv` solo con `metodo == modelo`, mismas 8 columnas que `entidades.csv`.
2. Evaluar contra `anotaciones/gold_seleccion.csv` (6 pasajes disjuntos del gold, PRD §6.11) con `python kit/evaluar.py ie anotaciones/gold_seleccion.csv salida/entidades_{slug}.csv`.
3. Gana el mayor F1 en `metodo == modelo, tipo == TODOS`; empate exacto al principal.
4. Escribir `data/modelo_ner.json` con `modelo, revision, f1_seleccion, f1_seleccion_alternativa, criterio` ANTES de que cualquier script lea `anotaciones/gold_entidades.csv`. Verificar orden con fechas del manifiesto y commit.
5. `salida/09_comparacion_ner.csv`: F1 por tipo en selección (decide) y en gold de 20 (solo informativo; la elección ya está hecha y no cambia).
6. Sin conjunto de selección: se usa el principal, `criterio: "tecnico"` y el reporte declara que la elección fue técnica.

Experimento de capitalización (OP, P2): correr el modelo sobre el pasaje con la marca en capitalización de título y medir el cambio en PER/ORG dentro de la marca. Exige mapa de offsets o verificación explícita de correspondencia; no suponer que la longitud se conserva. Sin el experimento, el reporte describe dónde ocurren los errores en la marca pero no afirma causalidad de las mayúsculas.

## Pruebas
`tests/test_ner_posproceso.py`, rápidas, sin red, con mocks del pipeline HF (`monkeypatch` sobre la función que construye el pipeline; el mock devuelve listas de dicts `{entity_group, score, word, start, end}`). Deben cubrir:
1. Mapa de etiquetas: `PERSON→PER`, `GPE→LOC`, `MISC` descartado y contado; etiqueta inexistente en `id2label` no se mapea.
2. Recorte de extremos: puntuación y espacios fuera, `$` dentro; invariante `texto[inicio:fin] == texto_entidad` en cada fila.
3. Unión intrapalabra siempre; unión interpalabra registrada con fila en `07_uniones_spans.csv`; crudo y unido conservados.
4. T12: texto largo con una oración enorme; cobertura completa de ventanas; entidad en el borde deduplicada con prioridad a la no cortada y después confianza; sin truncamiento silencioso.
5. Caché: misma clave → cero llamadas al pipeline mock; cambio de revisión o fragmentación → clave distinta; `--forzar` reinfiere; cambio de `version_posproceso` NO reinfiere.
6. Selección: con dos CSV de F1 sintéticos, gana el mayor y el empate va al principal; `modelo_ner.json` tiene las cinco claves.
Comando: `uv run pytest tests/test_ner_posproceso.py`. El módulo no se da por terminado hasta verde. Los ejemplos de prueba son sintéticos y no se presentan como anotaciones del corpus.

## Skills relacionadas
- `integridad-congelacion`: orden de congelaciones (D09, D15, D18), `data/modelo_ner.json` antes del gold, manifiesto de ejecución.
- `indice-ranking`: de dónde salen `salida/ranking.csv` y `data/mejor_modelo.json` que definen el ámbito del NER.
- `reglas-gazetteer`: la otra fuente de entidades (`metodo == regla`), que recupera lo que cae en MISC/OTH.
- `fusion-normalizacion`: consume la salida del NER y la fusiona con reglas en `entidades.csv` (D12, D16).
- `evaluacion-ie`: `kit/evaluar.py ie`, `salida/09_comparacion_ner.csv`, análisis de errores por método y tipo.

## v2: comparación de candidatos (PRD v2 D34; WP-10, dueño Diego desde el 21)

- Candidatos: `mrm8488` (principal v1) y 3 o 4 más, por ejemplo RoBERTa BNE o CAPITEL, spaCy
  `es_core_news_lg`, XLM-R y GLiNER, cada uno con revisión fija en `config/ner.yaml`. Verificar
  en Hugging Face que sigan publicados (PV10).
- **Criterio fijo:** F1 micro solo del modelo en PER, ORG y LOC sobre la selección v2 adjudicada;
  empate → `mrm8488`. Luis anota la selección **antes** de inferir sobre esos pasajes.
- `data/modelo_ner.json` v2 se escribe el jueves 19, con commit anterior a `cierre_gold_v2.json`.
- Cachés por modelo y revisión en `data/cache_ner/`; nunca se reutiliza la caché de otro modelo.
- Implementado el 24: `candidatos_v2` en `config/ner.yaml`, motor `spacy` en `ner_modelo.py`,
  `comparacion_ner.py` y `scripts/09_comparacion_ner.py` (`make verificar-ner-v2`,
  `inferir-seleccion`, `comparacion-ner`, `fijar-ner-v2`, todos con el grupo `ner-v2` de uv).
  Las predicciones de la selección no se commitean hasta que el adjudicador la cierre.
