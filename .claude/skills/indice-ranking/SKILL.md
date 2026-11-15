---
name: indice-ranking
description: "Usa esta skill cuando vayas a escribir, modificar o depurar el preprocesamiento, el índice invertido, TF-IDF, BM25, el filtro de fecha o el top-10 (src/mtx/preproceso.py, indice.py, ranking.py, scripts 02_indice.py y 03_ranking.py, ranking.csv)."
---
# Índice invertido y ranking (IR)

Reglas ejecutables condensadas de PRD §2.1, §2.2, §3.5, §6.2, §6.3, §6.4 y anexo A. Si algo no está aquí ni en el PRD, no se inventa: se pregunta.

## Cuándo usarla

- Vas a tocar `src/mtx/preproceso.py`, `src/mtx/indice.py`, `src/mtx/ranking.py`, `scripts/02_indice.py` o `scripts/03_ranking.py`.
- Vas a generar o validar `salida/ranking.csv` (y su copia `ranking.csv` en la raíz), `salida/03_*.csv` o `salida/02_*.md`.
- Falla una prueba de `tests/test_preproceso.py`, `tests/test_indice.py` o `tests/test_ranking.py` (T03 a T06).
- Alguien propone cambiar stoplist, stemmer, k1/b, min_df, k o el criterio de desempate.

## Prerrequisitos y congelaciones que aplican

1. Entrada congelada: `data/pasajes.parquet` (PRD §6.1) con `passage_id`, `doc_id`, `posicion`, `fecha` (puede ser NaT), `inicio_cuerpo` y `texto`. Consultas desde `data/consultas.csv` (kit + Q9 + Q10, PRD §3.2); Q1 a Q8 se usan tal cual, sin reformular.
2. Bibliotecas válidas (PRD §2.1): `pandas`, `numpy`, `scikit-learn`, `nltk`, `regex`, `rank_bm25`. Prohibido: LangChain, LlamaIndex, Haystack, Elasticsearch, Whoosh, Vespa y cualquier herramienta que construya el índice o el ranking por ti.
3. Decisión de proyecto (PRD §2.2): índice invertido a mano (dict), contrastado con scikit-learn; BM25 propio; TF-IDF con scikit-learn; `rank_bm25` solo como dependencia de desarrollo para la prueba de consistencia, nunca en la ruta de producción.
4. D03: la marca de interlocutor va al inicio de `texto` para la extracción y queda fuera de los tokens del índice vía `inicio_cuerpo`.
5. U9 (desempate numérico) y U10 (nunca rellenar top-k) están congelados; ver `integridad-congelacion` antes de cambiar cualquier parámetro de esta skill.

## Preprocesamiento

API de `src/mtx/preproceso.py` (PRD §6.2): `tokenizar(texto) -> list[str]`, `tokenizar_pasaje(texto, inicio_cuerpo) -> list[str]` (tokeniza solo `texto[inicio_cuerpo:]`) y `tokenizar_sin_stem(texto) -> list[str]` (para mostrar el efecto del stemmer).

Cadena, en este orden exacto:

1. Normalización Unicode NFC y minúsculas.
2. `RE_TOKEN = re.compile(r"[a-záéíóúñü0-9]+(?:-[a-záéíóúñü0-9]+)?", re.IGNORECASE)`. Conserva números y formas alfanuméricas como `covid-19`; la política se documenta y se prueba.
3. Stoplist = `nltk.corpus.stopwords.words("spanish")` ∪ `config/stopwords_es.txt` (respaldo versionado; si falta `nltk_data` se usa esa misma lista, nunca otra) ∪ `config/stoplist_extra.txt` (estenográfica: `presidente, pregunta, interlocutor, interlocutora, gracias, bueno, entonces, vamos, pues, ustedes, nosotros, aquí, ahora, decir, digo, va, ir, andrés, manuel, lópez, obrador, mañanera, conferencia, prensa`). Se guarda el contenido efectivo y su hash. No se retiran siglas cortas ni nombres propios de forma indiscriminada.
4. Descartar tokens de longitud ≤ 2 salvo que sean numéricos.
5. `SnowballStemmer("spanish")`. Documentar por qué stemming y no lematización: velocidad, sin dependencia de spaCy, suficiente para consultas cortas.

Reglas:

- Pasajes se indexan con `tokenizar_pasaje` (D03); consultas con `tokenizar`. TF-IDF y BM25 usan los mismos tokens. Sin expansión por sinónimos en consultas oficiales.
- Persistir `data/tokens.parquet` (`passage_id, tokens`) con la configuración congelada y su hash.
- Una consulta que quede sin tokens produce un aviso explícito, no un ranking engañoso.

Lista de verificación bloqueante (`tests/test_preproceso.py`; `02_indice.py` escribe `salida/02_tokens_consultas.md` con tokens originales y finales de las diez consultas):

- [ ] Sobreviven "dos" y "bocas" (Q3), "santa" y "lucía" (Q4), "sembrando" y "vida" (Q5), "huachicol" (Q6), "mínimo" (Q8). Si un término clave cae en la stoplist, se quita de la stoplist y se documenta ("dos" está en la stoplist de NLTK: caso típico).
- [ ] `tokenizar_pasaje(texto, inicio_cuerpo) == tokenizar(texto[inicio_cuerpo:])`.
- [ ] Ningún token del índice proviene solo de la marca de interlocutor.
- [ ] `covid-19` se conserva como un solo token; `19` sobrevive como numérico aunque mida 2 caracteres.

## Índice invertido

Estructura (`src/mtx/indice.py`, PRD §6.3): `dict[str, dict[int, int]]` término → {índice interno de pasaje → tf}, más `df[termino]`, `N`, `longitud[pasaje]` (tokens del cuerpo), `avgdl` y mapa estable `idx ↔ passage_id`.

1. Ajustar el índice una sola vez sobre todos los pasajes congelados. Filtrar por fecha no recalcula N, df, idf ni avgdl: el filtro cambia el conjunto elegible, no la definición de los modelos.
2. Persistir `data/indice.pkl` (pickle protocolo 5) y `data/indice_meta.json` con N, tamaño del vocabulario, avgdl, fecha de construcción y hash de `data/tokens.parquet` para invalidar la caché. Si el hash no coincide, se reconstruye; nunca se usa un índice viejo con tokens nuevos.
3. Verificación cruzada obligatoria: `CountVectorizer(analyzer=identidad)` sobre los mismos tokens, donde `identidad` es una función definida a nivel de módulo (`def identidad(tokens): return tokens`), no un lambda, para que el pickle sea cargable en otro proceso.
4. `tests/test_indice.py` (T03): para 50 términos aleatorios y para conteos conocidos de un fixture sintético, df y suma de tf del dict coinciden con la matriz de scikit-learn, incluidos nombres que aparecen solo en marcas (deben tener df = 0 en ambos).
5. Salidas del script `02_indice.py`:
   - `salida/02_postings.md`: `tren`, `vacuna`, `refinería`, `huachicol` en su forma stemmed, indicando el stem; por término: df, idf (fórmula BM25), top-15 pasajes por tf con `passage_id`, `fecha` y 80 caracteres de contexto, con la nota de que es una muestra y la lista completa vive en el índice.
   - `salida/02_vocabulario_top.csv`: 200 términos más frecuentes por df, para la discusión de la stoplist.
   - `salida/02_tokens_consultas.md` (ver sección anterior).

## TF-IDF y BM25

**TF-IDF con coseno (scikit-learn).** `TfidfVectorizer(analyzer=identidad, sublinear_tf=True, smooth_idf=True, min_df=1, norm="l2")` sobre los tokens del cuerpo; puntaje = `cosine_similarity(vec.transform([q_tokens]), X)`. Fórmula para tf > 0:

$$w_{t,p} = (1 + \ln tf_{t,p}) \cdot \left(\ln\frac{1 + N}{1 + df_t} + 1\right)$$

- Por qué `min_df=1`: TF-IDF y BM25 deben ver el mismo vocabulario. Con `min_df=2`, un término de consulta con df = 1 desaparecería de TF-IDF y seguiría puntuando en BM25; la comparación entre modelos quedaría sesgada.
- Un vector de consulta nulo produce similitud cero, nunca NaN.
- Persistir `data/tfidf.pkl` y `data/tfidf_X.npz`; probar que se cargan en un proceso nuevo (por eso `identidad` no puede ser lambda).

**BM25 propio.** Clase `BM25(k1=1.5, b=0.75)` sobre el índice invertido, variante con idf positivo:

$$\mathrm{idf}(t) = \ln\left(1 + \frac{N - df_t + 0.5}{df_t + 0.5}\right)$$

$$\mathrm{score}(q, p) = \sum_{t \in q} \mathrm{idf}(t) \cdot \frac{tf_{t,p}\,(k_1 + 1)}{tf_{t,p} + k_1\left(1 - b + b \cdot \frac{|p|}{\mathrm{avgdl}}\right)}$$

- La suma recorre los términos únicos de la consulta: los repetidos cuentan una vez; los ausentes del vocabulario aportan cero.
- `|p|` es `longitud[pasaje]` en tokens del cuerpo; `avgdl` el promedio sobre los N pasajes congelados.

Validación obligatoria (`tests/test_ranking.py`, T04):

1. Corpus sintético pequeño con puntajes TF-IDF y BM25 calculados a mano; ceros sin NaN.
2. Consistencia con `rank_bm25`: `BM25Okapi` usa `ln((N - df + 0.5)/(df + 0.5))` con un piso epsilon para términos con df > N/2, así que comparar rankings directos puede fallar sin que haya bug. Definir una subclase de `BM25Okapi` que sobrescriba `_calc_idf` con la fórmula propia y comparar puntajes sobre 200 pasajes y 5 consultas con tolerancia absoluta 1e-6. Documentar que, sin la subclase, la diferencia se concentra en términos con df > N/2.
3. `rank_bm25` va solo en el grupo de desarrollo de las dependencias; `ranking.py` no lo importa.

## Filtro de fecha, top-k y desempates

Filtro de fecha (PRD §6.4, T05):

1. Ventana con días inclusivos: `desde <= fecha <= hasta`.
2. Ambos límites ausentes = sin filtro; uno ausente deja ese lado abierto; `desde > hasta` o límite inválido = error de entrada con mensaje claro.
3. `fecha` NaT queda fuera con filtro y dentro sin filtro, identificada como fecha desconocida.
4. Primero se seleccionan los pasajes elegibles, después se puntúan y ordenan. Nunca rellenar con pasajes excluidos, con `-inf` ni con ceros (U10). Reportar cuántos pasajes excluye el filtro por consulta.

Top-k y desempates (U9):

1. `k = 10`. Orden por la tupla `(-puntaje, doc_id, posicion)` con `doc_id` y `posicion` enteros, nunca por `passage_id` como cadena (`10_2` quedaría antes que `9_1`).
2. No redondear antes de ordenar; el CSV guarda 6 decimales.
3. Consultas oficiales devuelven `min(10, n_elegibles)`; cualquier excepción a 400 filas se registra con conteo y motivo.
4. Puntaje cero se marca `sin_senal_lexica = 1` en el detalle y no se presenta como evidencia de relevancia.
5. Consulta libre vacía (sin tokens tras preprocesar) devuelve estado explicativo y ninguna fila.

Pruebas T06: cero, tres y diez candidatos, y términos desconocidos. Nunca se cuelan excluidos; tamaños, rangos y estados consistentes.

## Salidas

`scripts/03_ranking.py` produce, en una sola corrida, las cuatro variantes por consulta:

| `modelo` | `variante` |
|---|---|
| `tfidf_con_filtro` | `con_filtro` |
| `bm25_con_filtro` | `con_filtro` |
| `tfidf_sin_filtro` | `sin_filtro` |
| `bm25_sin_filtro` | `sin_filtro` |

1. `salida/ranking.csv` → copia idéntica en la raíz `ranking.csv`. Exactamente 9 columnas en este orden: `query_id,modelo,variante,rango,passage_id,doc_id,fecha,posicion,puntaje`. Claves únicas: `(query_id, modelo, rango)` y `(query_id, modelo, passage_id)`. UTF-8 sin BOM, separador coma, fecha ISO `AAAA-MM-DD` o campo vacío si NaT, `puntaje` con 6 decimales. Ejemplo de fila: `Q1,bm25_con_filtro,con_filtro,1,1532_7,1532,2021-06-14,7,18.421300`.
2. `salida/03_ranking_detalle.csv`: las 9 columnas más `interlocutor`, `es_reportero`, `titulo`, `sin_senal_lexica` y `texto` recortado a 400 caracteres.
3. `salida/03_solape_modelos.csv`: por consulta, intersección de top-10 entre TF-IDF y BM25 con filtro; entre con y sin filtro por modelo; discursos (`doc_id`) distintos por top-10.
4. `salida/03_excluidos_por_filtro.csv`: por consulta, cuántos pasajes del top-10 sin filtro caen fuera de la ventana o tienen fecha desconocida, con sus fechas.
5. `buscar(consulta, desde=None, hasta=None, modelo="bm25", k=10) -> tuple[pd.DataFrame, dict]` en `ranking.py`, para la demo y la app: devuelve resultados y un `dict` de estado (tokens de la consulta, excluidos por filtro, avisos como consulta vacía).

Antes de copiar a la raíz, validar el CSV contra `kit-contratos` (columnas, claves, tipos).

## Criterios de aceptación bloqueantes

No se cierra la fase de IR mientras falte uno (PRD §6.4):

- [ ] Las cuatro variantes producen 10 filas por consulta para las 10 consultas (400 filas), o la excepción está justificada con conteo y motivo.
- [ ] En BM25 con filtro: el top-10 de Q3 contiene al menos un pasaje con "refinería" o "Pemex"; el de Q1 al menos uno con "Tren Maya"; el de Q6 al menos uno con "huachicol" (prueba lenta en `tests/test_ranking.py`).
- [ ] TF-IDF y BM25 no producen rankings idénticos en todas las consultas. Un ranking igual en alguna consulta se investiga; no es por sí mismo una prueba automática de error.
- [ ] Modificar solo la marca de interlocutor de un pasaje no altera puntajes ni orden para un cuerpo fijo (D03).
- [ ] T03 (conteos contra `CountVectorizer`), T04 (fórmulas y subclase de `rank_bm25`, tolerancia 1e-6), T05 (fecha en límites exactos, ausente, ventana abierta e invertida) y T06 (cero, tres y diez candidatos; términos desconocidos) en verde.
- [ ] `python kit/evaluar.py ir juicios_relevancia.csv ranking.csv` corre contra `ranking.csv` con un `juicios_relevancia.csv` sintético sin lanzar excepción.
- [ ] `salida/02_tokens_consultas.md`, `salida/02_postings.md`, `salida/02_vocabulario_top.csv`, `data/indice_meta.json` y los tres `salida/03_*.csv` existen y se regeneran desde cero con `02_indice.py` y `03_ranking.py`.

## Skills relacionadas

- `corpus-segmentacion`: produce `data/pasajes.parquet` e `inicio_cuerpo`; cualquier cambio ahí invalida `tokens.parquet` y el índice.
- `integridad-congelacion`: U9, U10, D03 y los parámetros (k1, b, min_df, stoplist) están congelados; consultar antes de cambiarlos.
- `kit-contratos`: formato exacto de `ranking.csv` y uso de `kit/evaluar.py ir`.
- `pool-juicios-ir`: consume el top-10 de las cuatro variantes para armar el pool de juicios de relevancia.
- `tablas-respuesta`: toma `03_solape_modelos.csv` y `03_excluidos_por_filtro.csv` para la comparación TF-IDF vs. BM25 y con vs. sin filtro del reporte.

## v2: lematización y ocho variantes (PRD v2 D26; WP-03)

- `preproceso.lematizar` con spaCy `es_core_news_md` (alternativa `simplemma`), y
  `tokenizar_pasaje(..., raiz="stem" | "lema")`. `scripts/02_indice.py --raiz lema` y
  `scripts/03_ranking.py --v2` producen las 8 variantes {tfidf, bm25} × {con, sin}_filtro ×
  {stem, lema} en `salida/v2/ranking_8_variantes.csv`.
- Prueba bloqueante: las variantes stem son idénticas byte a byte a las de v1.
